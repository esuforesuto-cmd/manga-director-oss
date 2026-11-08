import { NextRequest, NextResponse } from "next/server";

const MAX_BODY_BYTES = 32 * 1024;
const ALLOWED_ORIGINS = new Set(["http://127.0.0.1:3000", "http://localhost:3000"]);
const HEADERS = { "cache-control": "no-store", "x-content-type-options": "nosniff" };
const messages: Record<string, string> = {
  not_found: "Not found.",
  invalid_input: "Request validation failed.",
  confirmation_conflict: "The Page changed. Reload and review it before confirming again.",
  activation_unavailable: "Storyboard confirmation is unavailable. Reload and inspect the Page before taking another action."
};

function safeError(status: number, code: string): NextResponse {
  return NextResponse.json({ code, message: messages[code] ?? messages.workflow_unavailable }, { status, headers: HEADERS });
}

async function readLimited(body: ReadableStream<Uint8Array> | null): Promise<Uint8Array | null> {
  if (!body) return new Uint8Array();
  const reader = body.getReader(); const chunks: Uint8Array[] = []; let size = 0;
  try {
    while (true) { const { done, value } = await reader.read(); if (done) break; size += value.byteLength; if (size > MAX_BODY_BYTES) { await reader.cancel(); return null; } chunks.push(value); }
  } catch { return null; }
  const result = new Uint8Array(size); let offset = 0;
  for (const chunk of chunks) { result.set(chunk, offset); offset += chunk.byteLength; }
  return result;
}

function upstreamBase(): string | null {
  const configured = process.env.MANGA_DIRECTOR_API_URL ?? "http://127.0.0.1:8000";
  try { const url = new URL(configured); const testPort = process.env.NODE_ENV !== "production" && url.port === "4010";
    if (url.protocol !== "http:" || url.hostname !== "127.0.0.1" || !(url.port === "8000" || testPort) || url.username || url.password || url.pathname !== "/" || url.search || url.hash) return null;
    return `http://127.0.0.1:${url.port}`;
  } catch { return null; }
}

export async function POST(request: NextRequest, { params }: { params: Promise<{ projectId: string; pageNumber: string }> }): Promise<NextResponse> {
  const { projectId, pageNumber } = await params;
  const expectedPath = `/api/projects/${encodeURIComponent(projectId)}/pages/${pageNumber}/storyboard/confirm`;
  if (!/^[A-Za-z0-9][A-Za-z0-9_-]*$/.test(projectId) || !/^[1-9][0-9]{0,9}$/.test(pageNumber)
    || Number(pageNumber) > 2_147_483_647
    || new URL(request.url).pathname !== expectedPath || request.nextUrl.search || request.nextUrl.hash) return safeError(422, "invalid_input");
  const origin = request.headers.get("origin"); const referer = request.headers.get("referer"); const host = request.headers.get("host");
  let refererOrigin = ""; try { refererOrigin = referer ? new URL(referer).origin : ""; } catch { /* fail closed */ }
  const originUrl = origin && ALLOWED_ORIGINS.has(origin) ? new URL(origin) : null;
  const allowedForwarded = new Set(["x-forwarded-host", "x-forwarded-port", "x-forwarded-proto", "x-forwarded-for"]);
  const deniedForwarding = new Set(["forwarded", "via", "x-real-ip", "x-original-host", "x-original-url", "x-rewrite-url"]);
  const unexpectedForwarded = [...request.headers.keys()].some((key) => deniedForwarding.has(key) || (key.startsWith("x-forwarded-") && !allowedForwarded.has(key)));
  const forwardedMatches = Boolean(originUrl) && request.headers.get("x-forwarded-host") === host
    && request.headers.get("x-forwarded-port") === originUrl?.port
    && request.headers.get("x-forwarded-proto") === originUrl?.protocol.slice(0, -1)
    && request.headers.get("x-forwarded-for") === "127.0.0.1";
  if (!originUrl || originUrl.protocol !== new URL(request.url).protocol || !referer || /,\s/.test(referer) || refererOrigin !== origin
    || request.headers.get("sec-fetch-site") !== "same-origin" || request.headers.get("sec-fetch-mode") !== "cors"
    || request.headers.get("sec-fetch-dest") !== "empty" || host !== originUrl.host
    || request.headers.has("cookie") || request.headers.has("authorization") || unexpectedForwarded || !forwardedMatches) return safeError(422, "invalid_input");
  const declared = request.headers.get("content-length");
  const contentType = request.headers.get("content-type");
  if (!contentType || contentType.includes(",") || contentType.split(";")[0].trim().toLowerCase() !== "application/json"
    || !request.headers.get("accept")?.split(",").some((item) => item.trim().split(";")[0] === "application/json")
    || request.headers.has("transfer-encoding") || request.headers.has("content-encoding")
    || declared === null || !/^(0|[1-9][0-9]*)$/.test(declared) || Number(declared) < 1 || Number(declared) > MAX_BODY_BYTES) return safeError(422, "invalid_input");
  const body = await readLimited(request.body); if (!body || body.byteLength !== Number(declared)) return safeError(422, "invalid_input");
  try {
    const value: unknown = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(body));
    if (!value || typeof value !== "object" || Array.isArray(value) || Object.keys(value).sort().join(",") !== "confirmed,expectedSource,panels,requestVersion") return safeError(422, "invalid_input");
  } catch { return safeError(422, "invalid_input"); }
  const base = upstreamBase(); if (!base) return safeError(503, "activation_unavailable");
  const target = `${base}/projects/${encodeURIComponent(projectId)}/pages/${pageNumber}/storyboard/confirm`;
  try {
    const upstream = await fetch(target, { method: "POST", body, redirect: "error", cache: "no-store", headers: {
      "content-type": "application/json", "content-length": String(body.byteLength), accept: "application/json", origin: origin!, referer: referer!,
      "sec-fetch-site": "same-origin", "sec-fetch-mode": "cors", "sec-fetch-dest": "empty"
    } });
    const raw = await readLimited(upstream.body); if (!raw) return safeError(503, "activation_unavailable");
    let result: unknown; try { result = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(raw)); } catch { return safeError(503, "activation_unavailable"); }
    const validSuccess = result && typeof result === "object" && !Array.isArray(result)
      && Object.keys(result).length === 1
      && (result as Record<string, unknown>).status === "storyboarded";
    if (upstream.status === 200 && validSuccess) return NextResponse.json(result, { status: 200, headers: HEADERS });
    const candidate = result && typeof result === "object" ? (result as Record<string, unknown>).code : undefined;
    const status = upstream.status; const code = typeof candidate === "string" && messages[candidate] && ({ not_found: 404, invalid_input: 422, confirmation_conflict: 409, activation_unavailable: 503 } as Record<string, number>)[candidate] === status ? candidate : "activation_unavailable";
    return safeError(code === "activation_unavailable" ? 503 : status, code);
  } catch { return safeError(503, "activation_unavailable"); }
}
