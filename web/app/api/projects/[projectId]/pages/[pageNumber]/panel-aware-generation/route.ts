import { NextRequest, NextResponse } from "next/server";

const MAX_BODY_BYTES = 32 * 1024;
const ALLOWED_ORIGINS = new Set(["http://127.0.0.1:3000", "http://localhost:3000"]);
const SAFE_CODES = new Set(["not_found", "invalid_input", "revision_conflict", "recovery_required", "generation_incomplete", "generation_blocked", "activation_unavailable"]);

function safeError(status: number, code: string): NextResponse {
  const messages: Record<string, string> = {
    not_found: "Not found.", invalid_input: "Request validation failed.",
    revision_conflict: "The Page changed and generation was not started.",
    recovery_required: "Generation requires recovery before another attempt.",
    generation_incomplete: "Generation did not complete.",
    generation_blocked: "Generation is unavailable.", activation_unavailable: "Generation is unavailable."
  };
  return NextResponse.json({ code, message: messages[code] ?? messages.activation_unavailable }, {
    status, headers: { "cache-control": "no-store", "x-content-type-options": "nosniff" }
  });
}

function upstreamBase(): string | null {
  const configured = process.env.MANGA_DIRECTOR_API_URL ?? "http://127.0.0.1:8000";
  try {
    const url = new URL(configured);
    const testPort = process.env.NODE_ENV !== "production" && url.port === "4010";
    if (url.protocol !== "http:" || url.hostname !== "127.0.0.1" || !(url.port === "8000" || testPort)
      || url.username || url.password || url.pathname !== "/" || url.search || url.hash) return null;
    return `http://127.0.0.1:${url.port}`;
  } catch { return null; }
}

async function readLimited(body: ReadableStream<Uint8Array> | null): Promise<Uint8Array | null> {
  if (!body) return new Uint8Array();
  const reader = body.getReader(); const chunks: Uint8Array[] = []; let size = 0;
  try {
    while (true) {
      const { done, value } = await reader.read(); if (done) break;
      size += value.byteLength; if (size > MAX_BODY_BYTES) { await reader.cancel(); return null; }
      chunks.push(value);
    }
  } catch { return null; }
  const result = new Uint8Array(size); let offset = 0;
  for (const chunk of chunks) { result.set(chunk, offset); offset += chunk.byteLength; }
  return result;
}

export async function POST(request: NextRequest, { params }: { params: Promise<{ projectId: string; pageNumber: string }> }): Promise<NextResponse> {
  const { projectId, pageNumber } = await params;
  const rawPathname = new URL(request.url).pathname;
  const expectedPathname = `/api/projects/${encodeURIComponent(projectId)}/pages/${pageNumber}/panel-aware-generation`;
  if (!/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(projectId) || !/^[1-9][0-9]{0,8}$/.test(pageNumber)
    || rawPathname !== expectedPathname || request.nextUrl.search || request.nextUrl.hash) return safeError(422, "invalid_input");
  const origin = request.headers.get("origin"); const referer = request.headers.get("referer");
  const fetchSite = request.headers.get("sec-fetch-site"); const fetchMode = request.headers.get("sec-fetch-mode");
  const fetchDest = request.headers.get("sec-fetch-dest"); const host = request.headers.get("host");
  let refererOrigin = ""; try { refererOrigin = referer ? new URL(referer).origin : ""; } catch { /* fail closed */ }
  const originUrl = origin && ALLOWED_ORIGINS.has(origin) ? new URL(origin) : null;
  const requestProtocol = new URL(request.url).protocol;
  const allowedForwarded = new Set(["x-forwarded-host", "x-forwarded-port", "x-forwarded-proto", "x-forwarded-for"]);
  const deniedForwardingHeaders = new Set(["forwarded", "via", "x-real-ip", "x-original-host", "x-original-url", "x-rewrite-url"]);
  const unexpectedForwarded = [...request.headers.keys()].some(
    (key) => deniedForwardingHeaders.has(key) || (key.startsWith("x-forwarded-") && !allowedForwarded.has(key))
  );
  const forwardedMatchesLocalRequest = Boolean(originUrl)
    && request.headers.get("x-forwarded-host") === host
    && request.headers.get("x-forwarded-port") === originUrl?.port
    && request.headers.get("x-forwarded-proto") === originUrl?.protocol.slice(0, -1)
    && request.headers.get("x-forwarded-for") === "127.0.0.1";
  // Next normalizes loopback request URLs to "localhost"; the incoming Host must
  // still exactly match the browser's allowlisted Origin and the request scheme.
  if (!originUrl || originUrl.protocol !== requestProtocol
    || !referer || refererOrigin !== origin || fetchSite !== "same-origin" || fetchMode !== "cors" || fetchDest !== "empty"
    || host !== originUrl.host || request.headers.has("cookie") || request.headers.has("authorization")
    || unexpectedForwarded || !forwardedMatchesLocalRequest) return safeError(422, "invalid_input");
  if (request.headers.get("content-type")?.split(";")[0].trim().toLowerCase() !== "application/json"
    || !request.headers.get("accept")?.split(",").some((item) => item.trim().split(";")[0] === "application/json")
    || request.headers.has("transfer-encoding") || request.headers.has("content-encoding")) return safeError(422, "invalid_input");
  const declared = request.headers.get("content-length");
  if (declared === null || !/^(0|[1-9][0-9]*)$/.test(declared) || Number(declared) > MAX_BODY_BYTES) return safeError(422, "invalid_input");
  const body = await readLimited(request.body);
  if (!body || body.byteLength !== Number(declared)) return safeError(422, "invalid_input");
  try { const value: unknown = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(body)); if (!value || typeof value !== "object" || Array.isArray(value)) return safeError(422, "invalid_input"); }
  catch { return safeError(422, "invalid_input"); }
  const base = upstreamBase(); if (!base) return safeError(503, "activation_unavailable");
  const target = `${base}/projects/${encodeURIComponent(projectId)}/pages/${pageNumber}/panel-aware-generation`;
  try {
    const upstream = await fetch(target, { method: "POST", body, redirect: "error", cache: "no-store", headers: {
      "content-type": "application/json", "content-length": String(body.byteLength), accept: "application/json", origin: origin!, referer: referer!,
      "sec-fetch-site": fetchSite!, "sec-fetch-mode": fetchMode!, "sec-fetch-dest": fetchDest!
    }});
    const raw = await readLimited(upstream.body); if (!raw) return safeError(503, "activation_unavailable");
    let result: unknown; try { result = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(raw)); } catch { return safeError(503, "activation_unavailable"); }
    if (upstream.status === 200 && result && typeof result === "object" && (result as Record<string, unknown>).status === "generated"
      && Object.keys(result as object).length === 1) return NextResponse.json({ status: "generated" }, { status: 200, headers: { "cache-control": "no-store", "x-content-type-options": "nosniff" } });
    const candidate = result && typeof result === "object" ? (result as Record<string, unknown>).code : undefined;
    const expectedStatuses: Record<string, number> = {
      not_found: 404, invalid_input: 422, revision_conflict: 409, recovery_required: 409,
      generation_incomplete: 409, generation_blocked: 409, activation_unavailable: 503
    };
    const code = String(candidate);
    if (SAFE_CODES.has(code) && expectedStatuses[code] === upstream.status) return safeError(upstream.status, code);
    return safeError(503, "activation_unavailable");
  } catch { return safeError(503, "activation_unavailable"); }
}
