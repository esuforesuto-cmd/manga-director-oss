import type { TLSSocket } from "node:tls";
import type { NextApiRequest, NextApiResponse } from "next";

import { apiBaseUrl } from "@/lib/api/client";

export const config = { api: { bodyParser: false } };

const MAX_BODY_BYTES = 32 * 1024;
// The standard Node HTTP server can truncate the list at 1,000 fields.
const HEADER_COUNT_LIMIT = 1_000;
const ALLOWED_ORIGINS = new Set(["http://127.0.0.1:3000", "http://localhost:3000"]);
const OTHER_APP_ROUTE_METHODS = new Set(["GET", "HEAD", "PUT", "DELETE", "PATCH"]);
const ALLOWED_FORWARDED = new Set(["x-forwarded-host", "x-forwarded-port", "x-forwarded-proto", "x-forwarded-for"]);
const DENIED_FORWARDING = new Set(["forwarded", "via", "x-real-ip", "x-original-host", "x-original-url", "x-rewrite-url"]);
const errors = {
  not_found: { status: 404, message: "Not found." },
  invalid_input: { status: 422, message: "Request validation failed." },
  confirmation_conflict: { status: 409, message: "The Page changed. Reload and review it before confirming again." },
  activation_unavailable: { status: 503, message: "Storyboard confirmation is unavailable. Reload and inspect the Page before taking another action." }
} as const;
type ErrorCode = keyof typeof errors;
type ConfirmationResponse = { status: "storyboarded" } | { code: ErrorCode; message: string };

function sendJson(response: NextApiResponse<ConfirmationResponse>, status: number, value: ConfirmationResponse): void {
  // Write the response directly to preserve its status under conditional requests.
  const body = JSON.stringify(value);
  response.setHeader("content-type", "application/json");
  response.setHeader("content-length", Buffer.byteLength(body));
  response.status(status).end(body);
}

function reject(response: NextApiResponse<ConfirmationResponse>, code: ErrorCode): void {
  const { status, message } = errors[code];
  sendJson(response, status, { code, message });
}

function uniqueHeaders(rawHeaders: string[]): Map<string, string> | null {
  if (rawHeaders.length % 2 !== 0 || rawHeaders.length >= HEADER_COUNT_LIMIT * 2) return null;
  const headers = new Map<string, string>();
  for (let index = 0; index < rawHeaders.length; index += 2) {
    const name = rawHeaders[index].toLowerCase();
    if (headers.has(name)) return null;
    headers.set(name, rawHeaders[index + 1]);
  }
  return headers;
}

async function readRequest(request: NextApiRequest, declared: number): Promise<Buffer | null> {
  const chunks: Buffer[] = [];
  let size = 0;
  try {
    for await (const chunk of request.iterator({ destroyOnReturn: false })) {
      if (!Buffer.isBuffer(chunk)) return null;
      size += chunk.byteLength;
      if (size > declared) return null;
      chunks.push(chunk);
    }
    return request.complete && size === declared ? Buffer.concat(chunks, size) : null;
  } catch {
    return null;
  }
}

async function readResponse(body: ReadableStream<Uint8Array> | null): Promise<Buffer | null> {
  if (!body) return Buffer.alloc(0);
  const reader = body.getReader();
  const chunks: Uint8Array[] = [];
  let size = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) return Buffer.concat(chunks, size);
      size += value.byteLength;
      if (size > MAX_BODY_BYTES) {
        await reader.cancel();
        return null;
      }
      chunks.push(value);
    }
  } catch {
    return null;
  }
}

function upstreamBase(): string | null {
  const configured = process.env.MANGA_DIRECTOR_API_URL ?? "http://127.0.0.1:8000";
  try {
    const url = new URL(configured);
    const testPort = process.env.NODE_ENV !== "production" && url.port === "4010";
    if (url.protocol !== "http:" || url.hostname !== "127.0.0.1" || !(url.port === "8000" || testPort)
      || url.username || url.password || url.pathname !== "/" || url.search || url.hash) return null;
    const base = "http://127.0.0.1:" + url.port;
    return apiBaseUrl() === base ? base : null;
  } catch {
    return null;
  }
}

export default async function confirm(request: NextApiRequest, response: NextApiResponse<ConfirmationResponse>): Promise<void> {
  if (request.method === "OPTIONS") {
    response.setHeader("allow", "OPTIONS, POST");
    response.status(204).end();
    return;
  }
  if (request.method !== "POST") {
    response.status(OTHER_APP_ROUTE_METHODS.has(request.method ?? "") ? 405 : 400).end();
    return;
  }
  response.setHeader("cache-control", "no-store");
  response.setHeader("x-content-type-options", "nosniff");

  const { projectId, pageNumber } = request.query;
  if (typeof projectId !== "string" || !/^[A-Za-z0-9][A-Za-z0-9_-]*$/.test(projectId)
    || typeof pageNumber !== "string" || !/^[1-9][0-9]{0,9}$/.test(pageNumber)
    || Number(pageNumber) > 2_147_483_647
    || request.url !== "/api/projects/" + projectId + "/pages/" + pageNumber + "/storyboard/confirm") {
    return reject(response, "invalid_input");
  }

  const headers = uniqueHeaders(request.rawHeaders);
  if (!headers) return reject(response, "invalid_input");
  const origin = headers.get("origin");
  const referer = headers.get("referer");
  const host = headers.get("host");
  let refererUrl: URL | undefined;
  try {
    if (referer) refererUrl = new URL(referer);
  } catch {
    return reject(response, "invalid_input");
  }
  const refererAuthority = referer?.match(/^http:\/\/([^/?#]*)/i)?.[1];
  const originUrl = origin && ALLOWED_ORIGINS.has(origin) ? new URL(origin) : null;
  const protocol = (request.socket as TLSSocket).encrypted ? "https:" : "http:";
  // Next adds these fields to headers after Node receives the original list.
  const forwarded = request.headers;
  const unexpectedForwarded = [...headers.keys()].some((name) =>
    DENIED_FORWARDING.has(name) || (name.startsWith("x-forwarded-") && !ALLOWED_FORWARDED.has(name)));
  if (!origin || !originUrl || originUrl.protocol !== protocol || !referer || !refererUrl
    || !refererAuthority || /,\s/.test(referer) || refererAuthority.includes("@")
    || refererUrl.username || refererUrl.password || refererAuthority.toLowerCase() !== refererUrl.host.toLowerCase()
    || refererUrl.hash || refererUrl.origin !== origin || host !== originUrl.host
    || headers.get("sec-fetch-site") !== "same-origin" || headers.get("sec-fetch-mode") !== "cors"
    || headers.get("sec-fetch-dest") !== "empty" || headers.has("cookie") || headers.has("authorization")
    || unexpectedForwarded || forwarded["x-forwarded-host"] !== host
    || forwarded["x-forwarded-port"] !== originUrl.port
    || forwarded["x-forwarded-proto"] !== originUrl.protocol.slice(0, -1)
    || forwarded["x-forwarded-for"] !== "127.0.0.1") return reject(response, "invalid_input");

  const declared = headers.get("content-length");
  const contentType = headers.get("content-type");
  const accept = headers.get("accept");
  if (!contentType || contentType.includes(",") || contentType.split(";")[0].trim().toLowerCase() !== "application/json"
    || !accept || accept.includes(",") || accept.trim().toLowerCase() !== "application/json"
    || headers.has("transfer-encoding") || headers.has("content-encoding")
    || !declared || !/^[1-9][0-9]*$/.test(declared) || Number(declared) > MAX_BODY_BYTES) {
    return reject(response, "invalid_input");
  }
  const body = await readRequest(request, Number(declared));
  if (!body) return reject(response, "invalid_input");
  try {
    const value: unknown = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(body));
    if (!value || typeof value !== "object" || Array.isArray(value)
      || Object.keys(value).sort().join(",") !== "confirmed,expectedSource,panels,requestVersion") {
      return reject(response, "invalid_input");
    }
  } catch {
    return reject(response, "invalid_input");
  }

  const base = upstreamBase();
  if (!base) return reject(response, "activation_unavailable");
  try {
    const target = base + "/projects/" + projectId + "/pages/" + pageNumber + "/storyboard/confirm";
    const upstream = await fetch(target, {
      method: "POST", body, redirect: "error", cache: "no-store",
      headers: {
        "content-type": "application/json", "content-length": String(body.byteLength),
        accept: "application/json", origin, referer,
        "sec-fetch-site": "same-origin", "sec-fetch-mode": "cors", "sec-fetch-dest": "empty"
      }
    });
    const raw = await readResponse(upstream.body);
    if (!raw) return reject(response, "activation_unavailable");
    const result: unknown = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(raw));
    if (result && typeof result === "object" && !Array.isArray(result)) {
      if (upstream.status === 200 && Object.keys(result).length === 1
        && "status" in result && result.status === "storyboarded") {
        sendJson(response, 200, { status: "storyboarded" });
        return;
      }
      if ("code" in result && typeof result.code === "string" && Object.hasOwn(errors, result.code)) {
        const code = result.code as ErrorCode;
        if (upstream.status === errors[code].status) return reject(response, code);
      }
    }
  } catch {
    return reject(response, "activation_unavailable");
  }
  return reject(response, "activation_unavailable");
}
