import { Readable } from "node:stream";
import type { NextApiRequest, NextApiResponse } from "next";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import confirm, { config } from "../pages/api/projects/[projectId]/pages/[pageNumber]/storyboard/confirm";

const url = "http://localhost:3000/api/projects/demo/pages/1/storyboard/confirm";
const body = JSON.stringify({ requestVersion: 1, expectedSource: { state: "Reviewed", page_design: {}, review: {} }, confirmed: true, panels: [] });

function request(overrides: Record<string, string> = {}, content = body, requestUrl = url): NextApiRequest {
  const headers = {
    host: "localhost:3000", origin: "http://localhost:3000", referer: "http://localhost:3000/projects/demo/pages/1",
    "sec-fetch-site": "same-origin", "sec-fetch-mode": "cors", "sec-fetch-dest": "empty",
    "content-type": "application/json", accept: "application/json", "content-length": String(Buffer.byteLength(content)), ...overrides
  };
  return Object.assign(Readable.from([Buffer.from(content)]), {
    method: "POST",
    complete: true,
    url: requestUrl.slice("http://localhost:3000".length),
    socket: {},
    rawHeaders: Object.entries(headers).flat(),
    headers: {
      "x-forwarded-host": "localhost:3000", "x-forwarded-port": "3000",
      "x-forwarded-proto": "http", "x-forwarded-for": "127.0.0.1", ...headers
    }
  }) as unknown as NextApiRequest;
}

async function POST(req: NextApiRequest, { params }: { params: Promise<{ projectId: string; pageNumber: string }> }): Promise<Response> {
  req.query = await params;
  const headers = new Headers();
  let status = 200;
  let result: string | null = null;
  const response = {
    setHeader(name: string, value: string | number) { headers.set(name, String(value)); return response; },
    status(code: number) { status = code; return response; },
    end(value?: string) { result = value ?? null; }
  };
  await confirm(req, response as unknown as NextApiResponse);
  return new Response(result, { status, headers });
}

describe("storyboard confirmation same-origin proxy", () => {
  beforeEach(() => {
    vi.stubEnv("NEXT_PUBLIC_MANGA_DIRECTOR_API_URL", undefined);
    vi.stubEnv("MANGA_DIRECTOR_API_URL", undefined);
  });
  afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); });

  it("forwards the exact closed request to the fixed loopback confirmation route", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: "storyboarded" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const response = await POST(request(), { params: Promise.resolve({ projectId: "demo", pageNumber: "1" }) });
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ status: "storyboarded" });
    expect(config.api.bodyParser).toBe(false);
    expect(response.headers.get("cache-control")).toBe("no-store");
    expect(response.headers.get("x-content-type-options")).toBe("nosniff");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toBe("http://127.0.0.1:8000/projects/demo/pages/1/storyboard/confirm");
    expect(fetchMock.mock.calls[0][1]).toMatchObject({ redirect: "error" });
    expect(Buffer.from(fetchMock.mock.calls[0][1].body as Uint8Array).toString("utf8")).toBe(body);
  });

  it.each([
    ["http://127.0.0.1:4010", undefined],
    ["http://127.0.0.1:8000", "http://127.0.0.1:4010"],
    ["invalid API URL", "http://127.0.0.1:8000"]
  ])("returns 503 without forwarding when the Page API %s does not match the confirmation API %s", async (pageApi, confirmationApi) => {
    vi.stubEnv("NEXT_PUBLIC_MANGA_DIRECTOR_API_URL", pageApi);
    vi.stubEnv("MANGA_DIRECTOR_API_URL", confirmationApi);
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const response = await POST(request(), { params: Promise.resolve({ projectId: "demo", pageNumber: "1" }) });

    expect(response.status).toBe(503);
    expect(await response.json()).toMatchObject({ code: "activation_unavailable" });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("forwards once when both settings resolve to the same development loopback API", async () => {
    vi.stubEnv("NEXT_PUBLIC_MANGA_DIRECTOR_API_URL", "http://127.0.0.1:4010/");
    vi.stubEnv("MANGA_DIRECTOR_API_URL", "http://127.0.0.1:4010");
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: "storyboarded" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const response = await POST(request(), { params: Promise.resolve({ projectId: "demo", pageNumber: "1" }) });

    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toBe("http://127.0.0.1:4010/projects/demo/pages/1/storyboard/confirm");
  });

  it("keeps the development loopback port blocked in production even if both settings match", async () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("NEXT_PUBLIC_MANGA_DIRECTOR_API_URL", "http://127.0.0.1:4010");
    vi.stubEnv("MANGA_DIRECTOR_API_URL", "http://127.0.0.1:4010");
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const response = await POST(request(), { params: Promise.resolve({ projectId: "demo", pageNumber: "1" }) });

    expect(response.status).toBe(503);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("accepts the backend's canonical ten-digit Page range and rejects overflow", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: "storyboarded" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const maxPage = "2147483647";
    const accepted = await POST(
      request({}, body, `http://localhost:3000/api/projects/demo/pages/${maxPage}/storyboard/confirm`),
      { params: Promise.resolve({ projectId: "demo", pageNumber: maxPage }) }
    );
    expect(accepted.status).toBe(200);
    expect(fetchMock.mock.calls[0][0]).toBe(`http://127.0.0.1:8000/projects/demo/pages/${maxPage}/storyboard/confirm`);

    const rejected = await POST(
      request({}, body, "http://localhost:3000/api/projects/demo/pages/2147483648/storyboard/confirm"),
      { params: Promise.resolve({ projectId: "demo", pageNumber: "2147483648" }) }
    );
    expect(rejected.status).toBe(422);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("allows a single Referer URL with a comma in its query", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: "storyboarded" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const response = await POST(
      request({ referer: "http://localhost:3000/projects/demo/pages/1?note=a,b" }),
      { params: Promise.resolve({ projectId: "demo", pageNumber: "1" }) }
    );
    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it.each([
    [409, "confirmation_conflict"],
    [422, "invalid_input"],
    [503, "activation_unavailable"]
  ])("preserves the RFC error class for %s responses", async (status, code) => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ code, message: "private detail" }), { status }));
    vi.stubGlobal("fetch", fetchMock);
    const response = await POST(request(), { params: Promise.resolve({ projectId: "demo", pageNumber: "1" }) });
    expect(response.status).toBe(status);
    const responseText = await response.text();
    expect(JSON.parse(responseText).code).toBe(code);
    expect(responseText).not.toContain("private detail");
  });

  it.each([
    [{ origin: "https://attacker.invalid" }],
    [{ referer: "http://localhost:3000/projects/demo/pages/1, http://localhost:3000/projects/demo/pages/1" }],
    [{ referer: "http://user:password@localhost:3000/projects/demo/pages/1" }],
    [{ referer: "http://@localhost:3000/projects/demo/pages/1" }],
    [{ referer: "http:\\localhost:3000/projects/demo/pages/1" }],
    [{ referer: "http://localhost:3000/projects/demo/pages/1#panel" }],
    [{ "content-type": "application/json; charset=utf-8, text/plain" }],
    [{ accept: "application/json, text/html" }],
    [{ accept: "application/json;q=0" }],
    [{ accept: "application/json;profile=anything" }],
    [{ authorization: "Bearer secret" }],
    [{ "sec-fetch-site": "cross-site" }],
    [{ "x-forwarded-for": "192.0.2.1" }],
    [{ "content-length": "999999" }]
  ])("rejects an unsafe proxy request before forwarding", async (headers) => {
    const fetchMock = vi.fn(); vi.stubGlobal("fetch", fetchMock);
    const response = await POST(request(headers), { params: Promise.resolve({ projectId: "demo", pageNumber: "1" }) });
    expect(response.status).toBe(422);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("rejects coalesced Accept values before replacing them for the API", async () => {
    const fetchMock = vi.fn(); vi.stubGlobal("fetch", fetchMock);
    const coalescedRequest = request({ accept: "application/json, application/json" });
    const response = await POST(coalescedRequest, { params: Promise.resolve({ projectId: "demo", pageNumber: "1" }) });

    expect(response.status).toBe(422);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it.each(["Referer", "Content-Type", "Origin", "Accept", "Content-Length", "X-Forwarded-Host", "X-Test"])(
    "rejects a repeated %s field before reading or forwarding",
    async (name) => {
      const fetchMock = vi.fn();
      vi.stubGlobal("fetch", fetchMock);
      const req = request();
      const lower = name.toLowerCase();
      const index = req.rawHeaders.indexOf(lower);
      const value = index < 0 ? "test" : req.rawHeaders[index + 1];
      if (index < 0) req.rawHeaders.push(lower, value);
      req.rawHeaders.push(name, value);
      const iterator = vi.spyOn(req, "iterator");

      const response = await POST(req, { params: Promise.resolve({ projectId: "demo", pageNumber: "1" }) });

      expect(response.status).toBe(422);
      expect(await response.json()).toMatchObject({ code: "invalid_input" });
      expect(iterator).not.toHaveBeenCalled();
      expect(fetchMock).not.toHaveBeenCalled();
    }
  );

  it.each([999, 1000, 1001])("checks the completeness limit for %i fields", async (count) => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: "storyboarded" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const req = request();
    for (let index = req.rawHeaders.length / 2; index < count; index += 1) {
      req.rawHeaders.push("x-test-" + index, "test");
    }
    const iterator = vi.spyOn(req, "iterator");

    const response = await POST(req, { params: Promise.resolve({ projectId: "demo", pageNumber: "1" }) });

    if (count < 1000) {
      expect(response.status).toBe(200);
      expect(fetchMock).toHaveBeenCalledOnce();
    } else {
      expect(response.status).toBe(422);
      expect(iterator).not.toHaveBeenCalled();
      expect(fetchMock).not.toHaveBeenCalled();
    }
  });

  it.each([1, Buffer.byteLength(body) + 1])("rejects a body that does not match the declared length %i", async (length) => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const req = request({ "content-length": String(length) });
    const response = await POST(req, { params: Promise.resolve({ projectId: "demo", pageNumber: "1" }) });

    expect(response.status).toBe(422);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it.each([
    [200, { status: "storyboarded" }],
    [404, { code: "not_found", message: "Not found." }],
    [409, { code: "confirmation_conflict", message: "The Page changed. Reload and review it before confirming again." }],
    [422, { code: "invalid_input", message: "Request validation failed." }],
    [503, { code: "activation_unavailable", message: "Storyboard confirmation is unavailable. Reload and inspect the Page before taking another action." }]
  ])("writes the fixed %i JSON response for a conditional request", async (status, expected) => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(expected), { status }));
    vi.stubGlobal("fetch", fetchMock);
    const req = request({ "if-none-match": "*" });

    const response = await POST(req, { params: Promise.resolve({ projectId: "demo", pageNumber: "1" }) });

    const content = await response.text();
    expect(response.status).toBe(status);
    expect(content).toBe(JSON.stringify(expected));
    expect(response.headers.get("content-type")).toBe("application/json");
    expect(response.headers.get("content-length")).toBe(String(Buffer.byteLength(content)));
    expect(response.headers.get("cache-control")).toBe("no-store");
    expect(response.headers.get("x-content-type-options")).toBe("nosniff");
    expect(response.headers.has("etag")).toBe(false);
    expect(fetchMock).toHaveBeenCalledOnce();
  });

  it.each([["OPTIONS", 204, "OPTIONS, POST"], ["GET", 405, null], ["TRACE", 400, null]])(
    "answers %s without reading the body",
    async (method, status, allow) => {
      const fetchMock = vi.fn();
      vi.stubGlobal("fetch", fetchMock);
      const req = request();
      req.method = method;
      const iterator = vi.spyOn(req, "iterator");

      const response = await POST(req, { params: Promise.resolve({ projectId: "demo", pageNumber: "1" }) });

      expect(response.status).toBe(status);
      expect(response.headers.get("allow")).toBe(allow);
      expect(await response.text()).toBe("");
      expect(iterator).not.toHaveBeenCalled();
      expect(fetchMock).not.toHaveBeenCalled();
    }
  );
});
