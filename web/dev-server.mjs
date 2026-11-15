import { createServer } from "node:http";

const args = process.argv.slice(2);
const options = new Map();
let production = false;
for (let index = 0; index < args.length; index++) {
  const argument = args[index];
  if (argument === "--production") {
    if (production) throw new Error("Invalid development server arguments.");
    production = true;
    continue;
  }
  const separator = argument.indexOf("=");
  const rawName = separator < 0 ? argument : argument.slice(0, separator);
  const name = rawName === "-H" ? "--hostname" : rawName === "-p" ? "--port" : rawName;
  if (name !== "--hostname" && name !== "--port" && name !== "--keepAliveTimeout") {
    throw new Error("Invalid development server arguments.");
  }
  const value = separator < 0 ? args[++index] : argument.slice(separator + 1);
  if (!value || value.startsWith("-")) throw new Error("Invalid development server arguments.");
  options.set(name, value);
}

const hostname = options.get("--hostname") ?? "127.0.0.1";
const portValue = options.get("--port") ?? process.env.PORT ?? "3000";
const port = Number(portValue);
const keepAliveTimeout = options.has("--keepAliveTimeout") ? Number(options.get("--keepAliveTimeout")) : undefined;
if (!["127.0.0.1", "localhost", "::1"].includes(hostname)) {
  throw new Error("Development server must bind to a loopback hostname.");
}
if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error("Invalid development server port.");
if (keepAliveTimeout !== undefined && (!Number.isInteger(keepAliveTimeout) || keepAliveTimeout < 0)) {
  throw new Error("Invalid keep-alive timeout.");
}
if (production) process.env.NODE_ENV = "production";
const suppressedDebugNamespaces = ["-next:router-server:main", "-next:router-server:resolve-routes"];
process.env.DEBUG = [...(process.env.DEBUG ?? "").split(",").map((namespace) => namespace.trim()).filter(Boolean), ...suppressedDebugNamespaces].join(",");
const { default: next } = await import("next");
const app = next({ dev: !production, hostname, port });
const handle = app.getRequestHandler();

function confirmationRoute(rawUrl) {
  const pathEnd = rawUrl.search(/[?#]/);
  let rawPath = (pathEnd < 0 ? rawUrl : rawUrl.slice(0, pathEnd)) || "/";
  rawPath = rawPath.replace(/^https?:\/\/[^/]+/i, "") || "/";
  const matchesConfirmation = (path) => /^\/api\/projects\/[^/]+\/pages\/[^/]+\/storyboard\/confirm\/?$/.test(
    path.replace(/\\/g, "/").replace(/\/+/g, "/")
  );
  const normalize = (path) => {
    const segments = path.replace(/\\/g, "/").split("/");
    const normalized = [];
    for (const segment of segments) {
      if (!segment || segment === ".") continue;
      if (segment === "..") normalized.pop();
      else normalized.push(segment);
    }
    return `/${normalized.join("/")}`;
  };
  if (matchesConfirmation(rawPath)) return true;
  const rawNormalized = normalize(rawPath);
  if (matchesConfirmation(rawNormalized)) return true;
  let decodedNormalized = rawNormalized;
  try {
    const decodedPath = decodeURIComponent(rawPath);
    if (matchesConfirmation(decodedPath)) return true;
    decodedNormalized = normalize(decodedPath);
  } catch {
    // The raw normalized form still catches structural route variants with invalid escapes.
  }
  return matchesConfirmation(decodedNormalized);
}

function hasUnsafeReferer(request) {
  const referers = [];
  for (let index = 0; index < request.rawHeaders.length; index += 2) {
    if (request.rawHeaders[index].toLowerCase() === "referer") {
      referers.push(request.rawHeaders[index + 1]);
    }
  }
  if (referers.length === 0) return false;
  if (referers.length !== 1) return true;

  const referer = referers[0];
  let parsed;
  try {
    parsed = new URL(referer);
  } catch {
    return true;
  }
  if (
    parsed.protocol !== "http:"
    || parsed.hostname === ""
    || parsed.username !== ""
    || parsed.password !== ""
    || parsed.hash !== ""
    || referer.includes("?")
    || !["http://127.0.0.1:3000", "http://localhost:3000"].includes(parsed.origin)
    || /,\s/.test(referer)
  ) {
    return true;
  }

  const rawAuthority = referer.match(/^http:\/\/([^/?#]*)/i)?.[1];
  return !rawAuthority || rawAuthority.includes("@") || rawAuthority.toLowerCase() !== parsed.host.toLowerCase();
}

const allowedConfirmationHeaders = new Set([
  "host", "connection", "content-length", "content-type", "accept", "accept-language", "accept-encoding",
  "user-agent", "origin", "referer", "sec-fetch-site", "sec-fetch-mode", "sec-fetch-dest",
  "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform", "priority", "dnt", "sec-gpc", "x-forwarded-port",
  "pragma", "cache-control"
]);

function hasUnsafeConfirmationHeaders(request) {
  const seen = new Set();
  for (let index = 0; index < request.rawHeaders.length; index += 2) {
    const name = request.rawHeaders[index].toLowerCase();
    if (seen.has(name) || !allowedConfirmationHeaders.has(name)) return true;
    if ((name === "pragma" || name === "cache-control") && request.rawHeaders[index + 1] !== "no-cache") return true;
    seen.add(name);
  }
  const headers = request.headers;
  const origin = headers.origin;
  const referer = headers.referer;
  let refererUrl;
  try {
    refererUrl = new URL(referer);
  } catch {
    return true;
  }
  const originUrl = typeof origin === "string" && ["http://127.0.0.1:3000", "http://localhost:3000"].includes(origin)
    ? new URL(origin) : null;
  const host = headers.host;
  const contentType = headers["content-type"];
  const accept = headers.accept;
  const contentLength = headers["content-length"];
  return !originUrl || !referer || !host || !contentType || !accept
    || originUrl.host !== host || refererUrl.origin !== origin || refererUrl.search !== "" || referer.includes("?")
    || refererUrl.hash !== "" || /,\s/.test(referer)
    || headers["sec-fetch-site"] !== "same-origin" || headers["sec-fetch-mode"] !== "cors"
    || headers["sec-fetch-dest"] !== "empty" || contentType.includes(",")
    || contentType.split(";")[0].trim().toLowerCase() !== "application/json"
    || accept.includes(",") || accept.trim().toLowerCase() !== "application/json"
    || (headers.dnt !== undefined && !["0", "1"].includes(headers.dnt))
    || (headers["sec-gpc"] !== undefined && headers["sec-gpc"] !== "1")
    || (headers["x-forwarded-port"] !== undefined && headers["x-forwarded-port"] !== originUrl.port)
    || !contentLength || !/^[1-9][0-9]*$/.test(contentLength) || Number(contentLength) > 32 * 1024;
}

function rejectConfirmationRequest(request, response) {
  if (request.method === "OPTIONS") {
    response.writeHead(204, { allow: "OPTIONS, POST" }).end();
    return;
  }
  if (request.method !== "POST") {
    response.writeHead(["GET", "HEAD", "PUT", "DELETE", "PATCH"].includes(request.method ?? "") ? 405 : 400).end();
    return;
  }
  const body = JSON.stringify({ code: "invalid_input", message: "Request validation failed." });
  response.writeHead(422, {
    "cache-control": "no-store",
    "content-type": "application/json",
    "content-length": Buffer.byteLength(body),
    "x-content-type-options": "nosniff"
  }).end(body);
}

await app.prepare();
const server = createServer((request, response) => {
  const rawUrl = request.url ?? "/";
  const isConfirmationRoute = confirmationRoute(rawUrl);
  const hasCredentials = Object.hasOwn(request.headers, "authorization")
    || Object.hasOwn(request.headers, "cookie")
    || Object.hasOwn(request.headers, "proxy-authorization");
  if (isConfirmationRoute && (rawUrl.includes("?") || rawUrl.includes("#") || hasCredentials || hasUnsafeReferer(request)
    || (request.method === "POST" && hasUnsafeConfirmationHeaders(request)))) {
    rejectConfirmationRequest(request, response);
    return;
  }
  void handle(request, response).catch(() => {
    if (response.headersSent) response.destroy();
    else response.writeHead(500, { "content-type": "text/plain; charset=utf-8", "content-length": "21" }).end("Internal Server Error");
  });
});
if (keepAliveTimeout !== undefined) server.keepAliveTimeout = keepAliveTimeout;
const activeSockets = new Set();
const upgradedSockets = new Set();
server.on("connection", (socket) => {
  activeSockets.add(socket);
  socket.once("close", () => activeSockets.delete(socket));
});
if (production) {
  server.on("upgrade", (_request, socket) => {
    if (shuttingDown || server.listenerCount("upgrade") === 1) {
      socket.destroy();
      return;
    }
    upgradedSockets.add(socket);
    socket.once("close", () => upgradedSockets.delete(socket));
  });
}
let shuttingDown = false;
let shutdownExitCode = 0;

function shutdown(exitCode = 0) {
  if (exitCode !== 0) shutdownExitCode = 1;
  if (shuttingDown) return;
  shuttingDown = true;
  const forcedExit = !production || !server.listening || exitCode !== 0
    ? setTimeout(() => process.exit(1), 5_000)
    : undefined;
  const serverClosed = new Promise((resolveClose) => server.close(() => resolveClose()));
  if (production) {
    for (const socket of upgradedSockets) socket.destroy();
    void serverClosed.then(async () => {
      await Promise.allSettled([app.close()]);
      if (forcedExit) clearTimeout(forcedExit);
      process.exit(shutdownExitCode);
    });
    return;
  }
  for (const socket of activeSockets) socket.destroy();
  void Promise.allSettled([app.close(), serverClosed]).then(() => {
    clearTimeout(forcedExit);
    process.exit(shutdownExitCode);
  });
}

function onStartupListening() {
  server.removeListener("error", onStartupError);
}

function onStartupError(error) {
  server.removeListener("listening", onStartupListening);
  console.error(error?.code === "EADDRINUSE"
    ? "Web server port is already in use."
    : "Web server failed to start.");
  shutdown(1);
}

server.once("listening", onStartupListening);
server.once("error", onStartupError);
for (const signal of ["SIGINT", "SIGTERM"]) {
  process.once(signal, () => {
    if (shuttingDown) return;
    shutdown();
  });
}
server.listen(port, hostname);
