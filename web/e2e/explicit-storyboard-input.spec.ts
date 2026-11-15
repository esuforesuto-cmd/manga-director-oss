import { execFileSync, spawn, type ChildProcess } from "node:child_process";
import { randomUUID } from "node:crypto";
import { cpSync, existsSync, mkdtempSync, readFileSync, realpathSync, rmSync } from "node:fs";
import { createServer, request as httpRequest, type IncomingHttpHeaders, type Server } from "node:http";
import { tmpdir } from "node:os";
import { basename, dirname, join, resolve } from "node:path";

import { expect, test, type Page, type TestInfo } from "@playwright/test";

const chromePath = "C:/Program Files/Google/Chrome/Application/chrome.exe";
if (process.platform === "win32" && existsSync(chromePath)) {
  test.use({ launchOptions: { executablePath: chromePath, headless: true } });
}

let apiServer: Server;
let browserProxy: Server;
let nextProcess: ChildProcess;
let isolatedWebRoot = "";
let appUrl = "";
let browserProxyUrl = "";
let browserProxyServerUrl = "";
let appPort = 0;
let confirmationRequests = 0;
let mockPostRequests = 0;
let nextStdout = "";
let nextStderr = "";
let filesystemDebugTail = "";
let unrelatedDebugSeen = false;
let requestLogProbe: { needles: string[]; stdoutTail: string; stderrTail: string; found: boolean } | undefined;
let debugHeaderProbe: { needle: string; stdoutTail: string; stderrTail: string; found: boolean } | undefined;
let traceProbe: { rejectedPaths: string[]; rejectedMarkers: string[]; controlPath: string; querylessPath: string } | undefined;
let nextProcessClosed = false;
let nextSpawnErrorCode = "";
let lastHttpStatus: number | null = null;
let lastFailure = "no_response_received";
let updateLatestPageSource: (source: string) => void = () => {};
let submittedExpectedSource: { state: string; page_design: Record<string, unknown>; review: Record<string, unknown> } | null = null;
let submittedPanelValues: Array<{
  characters: string[];
  continuity_bindings: string[];
  constraints: string[];
}> = [];

const maxCapturedOutputChars = 8_000;

function appendBoundedOutput(current: string, chunk: Buffer, stream: "stdout" | "stderr"): string {
  const chunkText = chunk.toString("utf8");
  const filesystemScan = filesystemDebugTail + chunkText;
  if (filesystemScan.includes("next:router-server:filesystem")) unrelatedDebugSeen = true;
  filesystemDebugTail = filesystemScan.slice(-"next:router-server:filesystem".length);
  const output = current + chunkText;
  if (requestLogProbe) {
    const tail = stream === "stdout" ? requestLogProbe.stdoutTail : requestLogProbe.stderrTail;
    const scan = tail + chunkText;
    if (requestLogProbe.needles.some((needle) => scan.includes(needle))) requestLogProbe.found = true;
    const nextTail = scan.slice(-Math.max(1, ...requestLogProbe.needles.map((needle) => needle.length)));
    if (stream === "stdout") requestLogProbe.stdoutTail = nextTail;
    else requestLogProbe.stderrTail = nextTail;
  }
  if (debugHeaderProbe) {
    const tail = stream === "stdout" ? debugHeaderProbe.stdoutTail : debugHeaderProbe.stderrTail;
    const scan = tail + chunkText;
    if (scan.includes(debugHeaderProbe.needle)) debugHeaderProbe.found = true;
    const nextTail = scan.slice(-Math.max(1, debugHeaderProbe.needle.length));
    if (stream === "stdout") debugHeaderProbe.stdoutTail = nextTail;
    else debugHeaderProbe.stderrTail = nextTail;
  }
  return output.slice(-maxCapturedOutputChars);
}

function rawHttpRequest(path: string, method: string, body?: string, headers?: IncomingHttpHeaders): Promise<{ status: number; headers: IncomingHttpHeaders; body: string }> {
  return new Promise((resolveRequest, rejectRequest) => {
    const target = new URL(appUrl);
    const request = httpRequest({
      hostname: target.hostname,
      port: Number(target.port),
      path,
      method,
      headers: {
        ...(body === undefined ? {} : {
          host: "127.0.0.1:3000",
          origin: "http://127.0.0.1:3000",
          referer: "http://127.0.0.1:3000/projects/demo/pages/1",
          "sec-fetch-site": "same-origin",
          "sec-fetch-mode": "cors",
          "sec-fetch-dest": "empty",
          "x-forwarded-port": "3000",
          accept: "application/json"
        }),
        ...(body === undefined ? {} : { "content-type": "application/json", "content-length": Buffer.byteLength(body) }),
        ...headers
      }
    }, (response) => {
      const chunks: Buffer[] = [];
      response.on("data", (chunk: Buffer) => chunks.push(Buffer.from(chunk)));
      response.on("end", () => resolveRequest({
        status: response.statusCode ?? 0,
        headers: response.headers,
        body: Buffer.concat(chunks).toString("utf8")
      }));
    });
    request.once("error", rejectRequest);
    if (body !== undefined) request.write(body);
    request.end();
  });
}

function safeOutputSummary(output: string): string {
  const safeLines = output.split(/\r?\n/).flatMap((line) => {
    if (/^\s*> next dev\s*$/.test(line)) return ["> next dev"];
    if (/^\s*▲ Next\.js [\d.]+\s*$/.test(line)) return ["▲ Next.js started"];
    if (/^\s*[-✓] Ready in [\d.]+\s*(?:ms|s)\s*$/.test(line)) return ["Ready message observed"];
    if (/^\s*○ Compiling \/projects\/(?:demo|\[projectId\])\/pages\/(?:1|\[pageNumber\])(?:\/page)?(?: \(\/projects\/demo\/pages\/1\))?\s*\.\.\.\s*$/.test(line)) return ["Target page compilation started"];
    if (/^\s*✓ Compiled \/projects\/(?:demo|\[projectId\])\/pages\/(?:1|\[pageNumber\])(?:\/page)? in [\d.]+\s*(?:ms|s)(?: \(\d+ modules\))?\s*$/.test(line)) return ["Target page compilation completed"];
    if (/EADDRINUSE/.test(line) || line === "Web server port is already in use.") {
      return ["Startup error category: address already in use"];
    }
    if (/ERR_MODULE_NOT_FOUND|Cannot find module/.test(line)) return ["Startup error category: module unavailable"];
    if (/Module not found/.test(line)) return ["Compilation error category: module unavailable"];
    if (/Failed to compile|Build Error/.test(line)) return ["Compilation error category: compilation failed"];
    if (/SyntaxError/.test(line)) return ["Compilation error category: syntax error"];
    if (/TypeError/.test(line)) return ["Runtime error category: type error"];
    return [];
  });
  return safeLines.length ? safeLines.join("; ") : output.length ? "[captured output withheld by safety filter]" : "[no output captured]";
}

function serverDiagnostics(reason: string, lastHttpStatus: number | null, lastFailure: string): string {
  const processState = !nextProcess
    ? "not started"
    : nextProcess.exitCode !== null
      ? `exited with code ${nextProcess.exitCode}`
      : nextProcess.signalCode !== null
        ? `exited with signal ${nextProcess.signalCode}`
        : "still running";
  const spawnError = nextSpawnErrorCode ? `; spawn error code ${nextSpawnErrorCode}` : "";
  return [
    `${reason} (process ${processState}${spawnError}; last HTTP status ${lastHttpStatus ?? "none"}; last readiness probe ${lastFailure})`,
    `Child output (bounded to ${maxCapturedOutputChars} characters per stream): stdout=${safeOutputSummary(nextStdout)}; stderr=${safeOutputSummary(nextStderr)}`
  ].join(". ");
}

async function fillStoryboardPanel(page: Page, index = 0): Promise<void> {
  await page.getByLabel("Narrative intent").nth(index).fill("The courier waits beneath the station clock.");
  await page.getByLabel("Character IDs, comma separated").nth(index).fill("courier-1, station-clerk");
  await page.getByLabel("Continuity bindings, one per line").nth(index).fill("blue coat, visible in the window\nmap, folded at the corner");
  await page.getByRole("textbox", { name: "Action" }).nth(index).fill("The courier checks the timetable.");
  await page.getByLabel("Background").nth(index).fill("A small station at dusk.");
  await page.getByLabel("Composition").nth(index).fill("The clock frames the waiting courier.");
  await page.getByLabel("Constraints, one per line").nth(index).fill("No readable text, including signs.\nKeep the map, even near the edge.");
}

function listen(server: Server, port = 0): Promise<number> {
  return new Promise((resolveListen, reject) => {
    server.once("error", reject);
    server.listen(port, "127.0.0.1", () => {
      const address = server.address();
      if (!address || typeof address === "string") return reject(new Error("Local test server did not bind."));
      resolveListen(address.port);
    });
  });
}

async function availablePort(): Promise<number> {
  const server = createServer();
  const port = await listen(server);
  await new Promise<void>((resolveClose, reject) => server.close((error) => error ? reject(error) : resolveClose()));
  return port;
}

async function startBrowserProxy(appPort: number): Promise<void> {
  browserProxy = createServer((incoming, outgoing) => {
    let target: URL;
    try {
      target = new URL(incoming.url ?? "/", "http://127.0.0.1:3000");
      if (target.origin !== "http://127.0.0.1:3000") {
        outgoing.writeHead(400).end();
        return;
      }
    } catch {
      outgoing.writeHead(400).end();
      return;
    }
    const headers: IncomingHttpHeaders = { ...incoming.headers, host: "127.0.0.1:3000" };
    headers["x-forwarded-port"] = "3000";
    delete headers["proxy-connection"];
    delete headers["proxy-authorization"];
    const forward = httpRequest({
      hostname: "127.0.0.1", port: appPort, path: `${target.pathname}${target.search}`,
      method: incoming.method, headers
    }, (response) => {
      outgoing.writeHead(response.statusCode ?? 502, response.headers);
      response.pipe(outgoing);
    });
    forward.once("error", () => { if (!outgoing.headersSent) outgoing.writeHead(502); outgoing.end(); });
    incoming.pipe(forward);
  });
  const port = await listen(browserProxy);
  browserProxyUrl = "http://127.0.0.1:3000";
  browserProxyServerUrl = `http://127.0.0.1:${port}`;
}

test.beforeAll(async () => {
  test.setTimeout(120_000);

  let pageDetail = {
    pageNumber: 1,
    state: "Reviewed",
    qualityPassed: null,
    approved: false,
    workflow: { currentState: "Reviewed", currentStep: null, completedSteps: [], availableActions: [], history: [] },
    input: { page_number: 1 },
    artifacts: {
      pageDesign: { page_purpose: "A courier reaches a quiet station." },
      review: { decision: "Ready for an explicit storyboard." }
    },
    messages: [],
    errors: [],
    executionTimeMs: 1,
    approvalRequired: false
  };
  updateLatestPageSource = (source: string) => {
    pageDetail = {
      ...pageDetail,
      artifacts: {
        ...pageDetail.artifacts,
        pageDesign: { page_purpose: source }
      }
    };
  };

  apiServer = createServer((request, response) => {
    if (request.method === "POST") mockPostRequests += 1;
    const pathname = new URL(request.url ?? "/", "http://127.0.0.1").pathname;
    response.setHeader("content-type", "application/json");
    if (request.method === "GET" && pathname === "/projects/demo/pages/1") {
      response.writeHead(200).end(JSON.stringify(pageDetail));
      return;
    }
    if (request.method === "POST" && pathname === "/projects/demo/pages/1/storyboard/confirm") {
      confirmationRequests += 1;
      response.writeHead(200).end(JSON.stringify({ status: "storyboarded" }));
      return;
    }
    response.writeHead(404).end(JSON.stringify({ code: "not_found", message: "Not found." }));
  });
  let apiPort: number;
  try {
    apiPort = await listen(apiServer, 8000);
  } catch (error) {
    const code = error && typeof error === "object" && "code" in error ? error.code : undefined;
    throw new Error(code === "EADDRINUSE"
      ? "Local mock backend port 8000 is already in use."
      : "Local mock backend could not start.");
  }

  const sourceWebRoot = resolve(process.cwd());
  isolatedWebRoot = mkdtempSync(join(tmpdir(), "manga-director-ui-e2e-"));
  cpSync(sourceWebRoot, isolatedWebRoot, {
    recursive: true,
    filter: (source) => !["node_modules", ".next", ".git", "e2e", "e2e-real", "tests", "test-results", "playwright-report"].includes(source.split(/[\\/]/).at(-1) ?? "")
  });
  cpSync(join(sourceWebRoot, "node_modules"), join(isolatedWebRoot, "node_modules"), { recursive: true });

  appPort = await availablePort();
  appUrl = `http://127.0.0.1:${appPort}`;
  nextProcess = spawn(process.execPath, [
    join(isolatedWebRoot, "dev-server.mjs"), "--hostname", "127.0.0.1", "--port", String(appPort)
  ], {
    cwd: isolatedWebRoot,
    env: {
      ...process.env,
      DEBUG: "*",
      NEXT_PUBLIC_MANGA_DIRECTOR_API_URL: `http://127.0.0.1:${apiPort}`,
      MANGA_DIRECTOR_API_URL: `http://127.0.0.1:${apiPort}`
    },
    stdio: ["ignore", "pipe", "pipe"]
  });
  nextProcess.stdout?.on("data", (chunk: Buffer) => { nextStdout = appendBoundedOutput(nextStdout, chunk, "stdout"); });
  nextProcess.stderr?.on("data", (chunk: Buffer) => { nextStderr = appendBoundedOutput(nextStderr, chunk, "stderr"); });
  nextProcess.once("error", (error: NodeJS.ErrnoException) => {
    const code = error.code;
    nextSpawnErrorCode = code && ["ENOENT", "EACCES", "EPERM", "EADDRINUSE", "UNKNOWN"].includes(code) ? code : "other";
  });
  nextProcess.once("close", () => { nextProcessClosed = true; });

  const deadline = Date.now() + 50_000;
  while (Date.now() < deadline) {
    if (nextProcess.exitCode !== null || nextProcess.signalCode !== null) {
      throw new Error(serverDiagnostics("Isolated Next.js server stopped before readiness", lastHttpStatus, lastFailure));
    }
    try {
      const requestTimeoutMs = Math.max(1, deadline - Date.now());
      const response = await fetch(`${appUrl}/projects/demo/pages/1`, {
        signal: AbortSignal.timeout(requestTimeoutMs)
      });
      lastHttpStatus = response.status;
      if (!response.ok) {
        lastFailure = "http_response_not_successful";
      } else if ((await response.text()).includes("Confirm storyboard input")) {
        lastFailure = "readiness_confirmed";
        await startBrowserProxy(appPort);
        return;
      } else {
        lastFailure = "expected_page_text_missing";
      }
    } catch (error) {
      lastFailure = error instanceof Error && error.name === "TimeoutError"
        ? "request_timeout"
        : error instanceof TypeError
          ? "request_type_error"
          : error instanceof Error
            ? "request_error"
            : "request_failed";
    }
    const delayMs = Math.min(250, Math.max(0, deadline - Date.now()));
    if (delayMs > 0) await new Promise((resolveDelay) => setTimeout(resolveDelay, delayMs));
  }
  throw new Error(serverDiagnostics("Isolated Next.js server did not become ready within 50 seconds", lastHttpStatus, lastFailure));
});

const confirmationFailures = new WeakMap<TestInfo, { browserPostCount: number; backendPostCount: number }>();

function readConfirmationForm(page: Page) {
  return page.evaluate((expectedFields) => {
    const section = document.querySelector('section[aria-labelledby="explicit-storyboard-heading"]');
    const panel = section?.querySelector("fieldset");
    const checkbox = section?.querySelector<HTMLInputElement>('input[type="checkbox"]');
    const button = section?.querySelector<HTMLButtonElement>('button[type="button"]');
    const buttonText = button?.textContent?.trim();
    const buttonState = buttonText === "Confirm storyboard" ? "confirm"
      : buttonText === "Saving…" ? "saving"
        : buttonText === "Reload before trying again" ? "reload"
          : button ? "other" : "missing";
    const fieldsMatch = Object.fromEntries(Object.entries(expectedFields).map(([name, expected]) => {
      const label = Array.from(panel?.querySelectorAll("label") ?? []).find((item) => item.textContent?.startsWith(name));
      const field = label?.querySelector<HTMLInputElement | HTMLTextAreaElement>("input, textarea");
      return [name, field ? field.value === expected : null];
    }));
    return {
      checkboxChecked: checkbox?.checked ?? null,
      checkboxDisabled: checkbox?.disabled ?? null,
      validationAlert: section ? Boolean(section.querySelector('[role="alert"]')) : null,
      buttonState,
      buttonDisabled: button?.disabled ?? null,
      fieldsMatch
    };
  }, {
    "Narrative intent": "The courier waits beneath the station clock.",
    "Character IDs, comma separated": "courier-1, station-clerk",
    "Continuity bindings, one per line": "blue coat, visible in the window\nmap, folded at the corner",
    "Action": "The courier checks the timetable.",
    "Background": "A small station at dusk.",
    "Composition": "The clock frames the waiting courier.",
    "Constraints, one per line": "No readable text, including signs.\nKeep the map, even near the edge."
  });
}

async function logConfirmationFailure(page: Page, counts: { browserPostCount: number; backendPostCount: number }) {
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    const deadline = new Promise<{ capture: "timed_out"; form: null }>((resolve) => {
      timer = setTimeout(() => resolve({ capture: "timed_out", form: null }), 1_000);
    });
    const snapshot = Promise.resolve().then(() => readConfirmationForm(page)).then(
      (form) => ({ capture: "captured", form }),
      () => ({ capture: "unavailable", form: null })
    );
    const result = await Promise.race([snapshot, deadline]);
    console.error("Storyboard confirmation diagnostic:", JSON.stringify({ ...result, ...counts }));
  } finally {
    clearTimeout(timer);
  }
}

test.afterEach(async ({ page }, testInfo) => {
  if (testInfo.status === testInfo.expectedStatus) return;
  await testInfo.attach("server-diagnostics.txt", {
    body: serverDiagnostics("Post-readiness browser test failed", lastHttpStatus, lastFailure),
    contentType: "text/plain"
  });
  const counts = confirmationFailures.get(testInfo);
  if (counts) await logConfirmationFailure(page, counts);
});

test.afterAll(async () => {
  let taskkillFailed = false;
  try {
    if (nextProcess && !nextProcessClosed) {
      if (nextProcess.exitCode === null && nextProcess.signalCode === null) {
        if (process.platform === "win32" && nextProcess.pid !== undefined) {
          try {
            execFileSync("taskkill.exe", ["/PID", String(nextProcess.pid), "/T", "/F"], { stdio: "ignore" });
          } catch {
            taskkillFailed = true;
          }
        } else if (nextProcess.pid !== undefined) {
          nextProcess.kill("SIGTERM");
        }
      }
      if (!nextProcessClosed) await new Promise<void>((resolveClose, rejectClose) => {
        const timeoutMessage = taskkillFailed
          ? "Windows process stop failed and Next.js did not close; preserving its temporary root."
          : "Isolated Next.js process did not close; preserving its temporary root.";
        const timeout = setTimeout(() => rejectClose(new Error(timeoutMessage)), 5_000);
        nextProcess.once("close", () => { clearTimeout(timeout); nextProcessClosed = true; resolveClose(); });
      });
    }
  } finally {
    if (browserProxy?.listening) await new Promise<void>((resolveClose) => browserProxy.close(() => resolveClose()));
    if (apiServer?.listening) await new Promise<void>((resolveClose) => apiServer.close(() => resolveClose()));
  }
  if (!isolatedWebRoot) return;
  const cleanupRoot = realpathSync(isolatedWebRoot);
  if (dirname(cleanupRoot) !== realpathSync(tmpdir()) || !basename(cleanupRoot).startsWith("manga-director-ui-e2e-")) {
    throw new Error("Isolated Next.js directory is outside the expected temporary root.");
  }
  try {
    if (traceProbe) {
      expect(requestLogProbe?.found === false, "A rejected query, URL, or credential marker appeared in Next.js output").toBe(true);
      expect(debugHeaderProbe?.found === false, "A harmless request header appeared in Next.js debug output").toBe(true);
      expect(unrelatedDebugSeen, "Wildcard DEBUG should continue emitting the unrelated filesystem namespace").toBe(true);
      let trace: string;
      try {
        trace = readFileSync(join(cleanupRoot, ".next", "trace"), "utf8");
      } catch {
        throw new Error("Next.js trace could not be read after server shutdown.");
      }
      expect(trace.includes(traceProbe.controlPath), "Expected the ordinary positive control in the Next.js trace").toBe(true);
      expect(trace.includes(traceProbe.querylessPath), "Expected the queryless confirmation request in the Next.js trace").toBe(true);
      expect(traceProbe.rejectedPaths.some((path) => trace.includes(path)), "A rejected confirmation request reached the Next.js trace").toBe(false);
      expect(traceProbe.rejectedMarkers.some((marker) => trace.includes(marker)), "A rejected query or credential marker reached the Next.js trace").toBe(false);
    }
  } finally {
    rmSync(cleanupRoot, { recursive: true, force: true });
  }
});

test("query-bearing storyboard confirmation requests are rejected before Next.js logging", async () => {
  test.setTimeout(60_000);
  const basePath = "/api/projects/demo/pages/1/storyboard/confirm";
  const trailingPath = `${basePath}/`;
  const repeatedSlashPath = "//api//projects/demo/pages/1//storyboard/confirm";
  const variants = [basePath, trailingPath, repeatedSlashPath].flatMap((path) => [
    { path: `${path}?testMarker=${randomUUID()}` },
    { path: `${path}?` }
  ]);
  const controlPath = `/projects/demo/pages/1?accessLogControl=${randomUUID()}`;
  const authorizationMarker = randomUUID();
  const cookieMarker = randomUUID();
  const ordinaryHeaderMarker = randomUUID();
  const refererMarker = randomUUID();
  const unknownHeaderMarker = randomUUID();
  const acceptMarker = randomUUID();
  const pragmaMarker = randomUUID();
  const cacheControlMarker = randomUUID();
  const initialConfirmationRequests = confirmationRequests;
  const queryMethodTargets = [
    { path: `${basePath}?methodOptions=${randomUUID()}`, method: "OPTIONS" },
    { path: `${trailingPath}?methodGet=${randomUUID()}`, method: "GET" },
    { path: `${basePath}?methodOther=${randomUUID()}`, method: "PROPFIND" }
  ];
  const unsafeHeaderTargets = [
    { path: `/api/projects/probe-${randomUUID()}/pages/1/storyboard/confirm`, headers: { authorization: `Bearer ${authorizationMarker}` } },
    { path: `/api/projects/probe-${randomUUID()}/pages/1/storyboard/confirm`, headers: { cookie: `session=${cookieMarker}` } },
    { path: `/api/projects/probe-${randomUUID()}/pages/1/storyboard/confirm`, headers: { referer: `http://127.0.0.1:3000/projects/demo/pages/1?probe=${refererMarker}` } },
    { path: `/api/projects/probe-${randomUUID()}/pages/1/storyboard/confirm`, headers: { "x-e2e-unexpected": unknownHeaderMarker } },
    { path: `/api/projects/probe-${randomUUID()}/pages/1/storyboard/confirm`, headers: { accept: `text/html;probe=${acceptMarker}` } },
    { path: `/api/projects/probe-${randomUUID()}/pages/1/storyboard/confirm`, headers: { pragma: pragmaMarker } },
    { path: `/api/projects/probe-${randomUUID()}/pages/1/storyboard/confirm`, headers: { "cache-control": cacheControlMarker } },
    { path: `/api/projects/probe-${randomUUID()}/pages/1/storyboard/confirm`, headers: { pragma: ["no-cache", "no-cache"] } },
    { path: `/api/projects/probe-${randomUUID()}/pages/1/storyboard/confirm`, headers: { "cache-control": ["no-cache", "no-cache"] } }
  ];
  const rejectedPaths = [
    ...variants.map(({ path }) => path),
    ...queryMethodTargets.map(({ path }) => path),
    ...unsafeHeaderTargets.map(({ path }) => path)
  ];
  const rejectedMarkers = [
    ...rejectedPaths.flatMap((path) => path.includes("?") && path.split("?")[1]
      ? [path.split("?")[1].split("=").at(-1) ?? ""] : []),
    authorizationMarker,
    cookieMarker,
    refererMarker,
    unknownHeaderMarker,
    acceptMarker,
    pragmaMarker,
    cacheControlMarker
  ];
  const logNeedles = [...rejectedPaths, ...rejectedMarkers];
  requestLogProbe = { needles: logNeedles, stdoutTail: "", stderrTail: "", found: false };
  debugHeaderProbe = { needle: ordinaryHeaderMarker, stdoutTail: "", stderrTail: "", found: false };
  traceProbe = { rejectedPaths, rejectedMarkers, controlPath, querylessPath: basePath };
  for (const { path } of variants) {
    const rejected = await rawHttpRequest(path, "POST", "{}");
    expect(rejected.status === 422, "Queried POST should return the bounded validation response without redirecting").toBe(true);
    expect(rejected.headers["cache-control"] === "no-store", "Queried POST should retain the no-store header").toBe(true);
    expect(typeof rejected.headers["content-type"] === "string" && rejected.headers["content-type"]?.startsWith("application/json"), "Queried POST should retain the JSON content type").toBe(true);
    expect(rejected.headers["x-content-type-options"] === "nosniff", "Queried POST should retain the nosniff header").toBe(true);
    expect(rejected.headers.location === undefined && rejected.headers.refresh === undefined, "Queried POST should not redirect").toBe(true);
    expect(rejected.body === JSON.stringify({ code: "invalid_input", message: "Request validation failed." })
      && Number(rejected.headers["content-length"]) === Buffer.byteLength(rejected.body)
      && !rejectedMarkers.some((marker) => rejected.body.includes(marker))
      && !rejected.body.includes("testMarker"), "Queried POST response should be bounded and contain no query value").toBe(true);
  }

  const initialMockPostRequests = mockPostRequests;
  for (const { path, headers } of unsafeHeaderTargets) {
    const rejected = await rawHttpRequest(path, "POST", "{}", headers);
    expect(rejected.status === 422, "Unsafe queryless POST should return the bounded validation response without redirecting").toBe(true);
    expect(rejected.headers["cache-control"] === "no-store", "Unsafe POST should retain the no-store header").toBe(true);
    expect(typeof rejected.headers["content-type"] === "string" && rejected.headers["content-type"]?.startsWith("application/json"), "Unsafe POST should retain the JSON content type").toBe(true);
    expect(rejected.headers["x-content-type-options"] === "nosniff", "Unsafe POST should retain the nosniff header").toBe(true);
    expect(rejected.headers.location === undefined && rejected.headers.refresh === undefined, "Unsafe POST should not redirect").toBe(true);
    expect(rejected.body === JSON.stringify({ code: "invalid_input", message: "Request validation failed." })
      && Number(rejected.headers["content-length"]) === Buffer.byteLength(rejected.body)
      && !rejectedMarkers.some((marker) => rejected.body.includes(marker))
      && !Object.values(rejected.headers).flat().some((value) => typeof value === "string"
        && rejectedMarkers.some((marker) => value.includes(marker))), "Unsafe POST response should be bounded and contain no marker").toBe(true);
  }
  expect(mockPostRequests === initialMockPostRequests, "Unsafe POST requests must not reach the mock API").toBe(true);

  for (const { path, method } of queryMethodTargets) {
    const result = await rawHttpRequest(path, method);
    const expected = method === "OPTIONS" ? 204 : method === "GET" ? 405 : 400;
    expect(result.status === expected, "Queried non-POST method should retain its bounded route response").toBe(true);
    if (method === "OPTIONS") expect(result.headers.allow === "OPTIONS, POST", "Queried OPTIONS should retain its allow header").toBe(true);
    expect(result.headers.location === undefined && result.headers.refresh === undefined, "Queried non-POST method should not redirect").toBe(true);
  }

    const querylessPost = await rawHttpRequest(basePath, "POST", "{}");
    expect(querylessPost.status === 422 && querylessPost.headers["cache-control"] === "no-store"
      && querylessPost.headers["x-content-type-options"] === "nosniff"
      && querylessPost.body.includes("invalid_input"), "Queryless POST should retain the existing proxy validation behavior").toBe(true);
    expect(confirmationRequests === initialConfirmationRequests, "Rejected requests must not reach the mock upstream").toBe(true);

    const querylessOptions = await rawHttpRequest(basePath, "OPTIONS");
    expect(querylessOptions.status === 204 && querylessOptions.headers.allow === "OPTIONS, POST").toBe(true);
    const querylessGet = await rawHttpRequest(basePath, "GET");
    expect(querylessGet.status === 405).toBe(true);
    const querylessOther = await rawHttpRequest(basePath, "PROPFIND");
    expect(querylessOther.status === 400).toBe(true);

    const ordinary = await rawHttpRequest(controlPath, "GET", undefined, { "x-e2e-debug-header": ordinaryHeaderMarker });
    expect(ordinary.status).toBe(200);
    expect(!ordinary.body.includes(ordinaryHeaderMarker), "Ordinary response should not echo the request header marker").toBe(true);
    await expect.poll(
      () => nextStdout.includes(`GET ${controlPath} `),
      { message: "Expected an ordinary page request to appear in the Next.js access log" }
    ).toBe(true);
    expect(requestLogProbe.found, "A rejected query, URL, or credential marker appeared in Next.js output").toBe(false);

    // Next.js batches trace events. Let the worker write a batch before Windows teardown stops it.
    for (let batch = 0; batch < 7; batch++) {
      await Promise.all(Array.from({ length: 8 }, async () => {
        const response = await fetch(`${appUrl}/projects/demo/pages/1`);
        expect(response.status, "Trace flush request failed").toBe(200);
        await response.arrayBuffer();
      }));
    }
});

test("a real browser confirmation reaches the Web proxy and mock backend", async ({ browser }) => {
  const context = await browser.newContext({ proxy: { server: browserProxyServerUrl, bypass: "<-loopback>" } });
  try {
    const page = await context.newPage();
    await page.goto(`${browserProxyUrl}/projects/demo/pages/1`);
    await expect(page.getByLabel("Narrative intent").nth(0)).toBeEnabled();
    await fillStoryboardPanel(page);
    await page.getByRole("checkbox", { name: "I reviewed these exact panel details and confirm them." }).check();

    const confirmationPath = "/api/projects/demo/pages/1/storyboard/confirm";
    const initialConfirmationRequests = confirmationRequests;
    const initialMockPostRequests = mockPostRequests;
    const responsePromise = page.waitForResponse((response) =>
      response.request().method() === "POST" && new URL(response.url()).pathname === confirmationPath
    );
    await page.getByRole("button", { name: "Confirm storyboard" }).click();
    const response = await responsePromise;
    expect(response.status()).toBe(200);
    await expect(page.getByText("Storyboard saved. Reload the page to inspect the result.")).toBeVisible();
    expect(confirmationRequests).toBe(initialConfirmationRequests + 1);
    expect(mockPostRequests).toBe(initialMockPostRequests + 1);
  } finally {
    await context.close();
  }
});

test("storyboard controls stay disabled until hydration", async ({ page }) => {
  await page.route((url) => url.pathname.endsWith(".js"), (route) => route.abort());
  await page.goto(`${appUrl}/projects/demo/pages/1`);

  await expect(page.getByLabel("Narrative intent").nth(0)).toBeDisabled();
  await expect(page.getByLabel("Panel count")).toBeDisabled();
  await expect(page.getByRole("checkbox", { name: "I reviewed these exact panel details and confirm them." })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Confirm storyboard" })).toBeDisabled();
});

test("editing or changing panel count revokes confirmation and prevents submission", async ({ page }, testInfo) => {
  confirmationRequests = 0;
  submittedPanelValues = [];
  await page.goto(`${appUrl}/projects/demo/pages/1`);
  const submit = page.getByRole("button", { name: "Confirm storyboard" });
  const confirmation = page.getByRole("checkbox", { name: "I reviewed these exact panel details and confirm them." });
  const confirmationPath = "/api/projects/demo/pages/1/storyboard/confirm";
  const browserPosts: Array<{ method: string; url: string }> = [];
  let nextOutcome: "success" | "conflict" | "uncertain" = "success";

  page.on("request", (request) => {
    if (new URL(request.url()).pathname === confirmationPath && request.method() === "POST") {
      browserPosts.push({ method: request.method(), url: request.url() });
    }
  });
  await page.route(`**${confirmationPath}`, async (route) => {
    if (route.request().method() !== "POST") {
      await route.continue();
      return;
    }
    if (nextOutcome === "uncertain") {
      await route.abort("failed");
      return;
    }
    if (nextOutcome === "conflict") {
      await route.fulfill({
        status: 409,
        contentType: "application/json",
        body: JSON.stringify({ code: "confirmation_conflict", message: "The Page source changed." })
      });
      return;
    }
    if (nextOutcome === "success") {
      const body = route.request().postDataJSON() as {
        panels: typeof submittedPanelValues;
        expectedSource: typeof submittedExpectedSource;
      };
      submittedPanelValues = body.panels;
      submittedExpectedSource = body.expectedSource;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ status: "storyboarded" })
    });
  });

  await expect(page.getByLabel("Narrative intent").nth(0)).toBeEnabled();
  await fillStoryboardPanel(page);

  await confirmation.check();
  try {
    await expect(submit).toBeEnabled();
  } catch (error) {
    confirmationFailures.set(testInfo, {
      browserPostCount: browserPosts.length,
      backendPostCount: confirmationRequests
    });
    throw error;
  }
  await page.getByRole("textbox", { name: "Action" }).fill("The courier folds the timetable.");
  await expect(confirmation).not.toBeChecked();
  await expect(submit).toBeDisabled();
  await submit.evaluate((button) => (button as HTMLButtonElement).click());
  expect(confirmationRequests).toBe(0);
  expect(browserPosts).toEqual([]);

  await confirmation.check();
  await expect(submit).toBeEnabled();
  await page.getByLabel("Panel count").selectOption("2");
  await expect(confirmation).not.toBeChecked();
  await expect(submit).toBeDisabled();
  await submit.evaluate((button) => (button as HTMLButtonElement).click());
  expect(confirmationRequests).toBe(0);
  expect(browserPosts).toEqual([]);

  await fillStoryboardPanel(page, 1);
  await confirmation.check();
  const successResponse = page.waitForResponse((response) =>
    response.request().method() === "POST" && new URL(response.url()).pathname === confirmationPath
  );
  await submit.click();
  expect((await successResponse).status()).toBe(200);
  await expect(page.getByText("Storyboard saved. Reload the page to inspect the result.")).toBeVisible();
  expect(browserPosts).toEqual([{ method: "POST", url: `${appUrl}${confirmationPath}` }]);
  expect(submittedPanelValues.map(({ characters, continuity_bindings, constraints }) => ({
    characters,
    continuity_bindings,
    constraints
  }))).toEqual([
    {
      characters: ["courier-1", "station-clerk"],
      continuity_bindings: ["blue coat, visible in the window", "map, folded at the corner"],
      constraints: ["No readable text, including signs.", "Keep the map, even near the edge."]
    },
    {
      characters: ["courier-1", "station-clerk"],
      continuity_bindings: ["blue coat, visible in the window", "map, folded at the corner"],
      constraints: ["No readable text, including signs.", "Keep the map, even near the edge."]
    }
  ]);

  nextOutcome = "conflict";
  await page.reload();
  await page.getByLabel("Panel count").selectOption("2");
  await fillStoryboardPanel(page, 0);
  await fillStoryboardPanel(page, 1);
  await confirmation.check();
  const conflictResponse = page.waitForResponse((response) =>
    response.request().method() === "POST" && new URL(response.url()).pathname === confirmationPath
  );
  await submit.click();
  expect((await conflictResponse).status()).toBe(409);
  await expect(page.getByText(/Page source changed/)).toBeVisible();
  const loadLatest = page.getByRole("button", { name: "Load latest state" });
  await expect(loadLatest).toBeEnabled();
  await expect(page.getByRole("button", { name: "Reload before trying again" })).toBeDisabled();
  expect(browserPosts).toHaveLength(2);
  expect(browserPosts[1]).toEqual({ method: "POST", url: `${appUrl}${confirmationPath}` });

  updateLatestPageSource("Latest source from server after conflict.");
  const refreshedPage = page.waitForNavigation();
  await loadLatest.click();
  await refreshedPage;
  await page.getByText("Reviewed source captured for this confirmation").click();
  const refreshedPageDesign = page.locator("details pre").first();
  await expect(refreshedPageDesign).toBeVisible();
  await expect(refreshedPageDesign).toContainText("Latest source from server after conflict.");
  await expect(confirmation).not.toBeChecked();
  await expect(page.getByLabel("Panel count")).toHaveValue("1");
  await expect(page.getByLabel("Narrative intent")).toHaveValue("");
  expect(browserPosts).toHaveLength(2);

  nextOutcome = "success";
  await fillStoryboardPanel(page);
  await confirmation.check();
  const refreshedSourceResponse = page.waitForResponse((response) =>
    response.request().method() === "POST" && new URL(response.url()).pathname === confirmationPath
  );
  await submit.click();
  expect((await refreshedSourceResponse).status()).toBe(200);
  expect(submittedExpectedSource).toEqual({
    state: "Reviewed",
    page_design: { page_purpose: "Latest source from server after conflict." },
    review: { decision: "Ready for an explicit storyboard." }
  });
  expect(browserPosts).toHaveLength(3);

  nextOutcome = "uncertain";
  await page.reload();
  await fillStoryboardPanel(page);
  await confirmation.check();
  await submit.click();
  await expect(page.getByText("The result may be uncertain. Reload the Page and inspect its state before taking another action.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Reload before trying again" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Load latest state" })).toHaveCount(0);
  expect(browserPosts).toHaveLength(4);
  expect(browserPosts[3]).toEqual({ method: "POST", url: `${appUrl}${confirmationPath}` });
});

test("oversized storyboard input stays editable and can be submitted after correction", async ({ page }) => {
  await page.goto(`${appUrl}/projects/demo/pages/1`);
  const submit = page.getByRole("button", { name: "Confirm storyboard" });
  const confirmation = page.getByRole("checkbox", { name: "I reviewed these exact panel details and confirm them." });
  const confirmationPath = "/api/projects/demo/pages/1/storyboard/confirm";
  const oversizedText = "漢".repeat(4_000);
  const browserPosts: string[] = [];

  page.on("request", (request) => {
    if (new URL(request.url()).pathname === confirmationPath && request.method() === "POST") {
      browserPosts.push(request.postData() ?? "");
    }
  });
  await page.route(`**${confirmationPath}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ status: "storyboarded" })
    });
  });

  await fillStoryboardPanel(page);
  await page.getByLabel("Narrative intent").fill(oversizedText);
  await page.getByRole("textbox", { name: "Action" }).fill(oversizedText);
  await page.getByLabel("Background").fill(oversizedText);
  await page.getByLabel("Composition").fill(oversizedText);
  await confirmation.check();
  await submit.click();

  await expect(page.getByText(/exceeds the 32 KiB request limit/)).toBeVisible();
  await expect(page.getByLabel("Narrative intent")).toHaveValue(oversizedText);
  await expect(page.getByRole("textbox", { name: "Action" })).toHaveValue(oversizedText);
  await expect(page.getByLabel("Background")).toHaveValue(oversizedText);
  await expect(page.getByLabel("Composition")).toHaveValue(oversizedText);
  await expect(confirmation).toBeChecked();
  await expect(submit).toBeEnabled();
  expect(browserPosts).toEqual([]);

  await page.getByRole("textbox", { name: "Action" }).fill("The courier folds the timetable.");
  await page.getByLabel("Background").fill("A small station at dusk.");
  await page.getByLabel("Composition").fill("Wide shot across the platform.");
  await expect(confirmation).not.toBeChecked();
  await confirmation.check();
  const response = page.waitForResponse((item) =>
    item.request().method() === "POST" && new URL(item.url()).pathname === confirmationPath
  );
  await submit.click();

  expect((await response).status()).toBe(200);
  expect(browserPosts).toHaveLength(1);
  const submittedBody = JSON.parse(browserPosts[0]) as {
    panels: Array<{ narrative_intent: string; action: string; background: string; composition: string }>;
  };
  expect(submittedBody.panels[0]).toMatchObject({
    narrative_intent: oversizedText,
    action: "The courier folds the timetable.",
    background: "A small station at dusk.",
    composition: "Wide shot across the platform."
  });
});
