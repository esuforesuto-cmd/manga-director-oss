import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { POST } from "../app/api/projects/[projectId]/pages/[pageNumber]/panel-aware-generation/route";

const url = "http://localhost:3000/api/projects/demo/pages/1/panel-aware-generation";
const body = '{"requestVersion":1,"authorizedBy":"editor","checkpointName":"local","layoutProfileId":"md-page-compositor-v1","layoutProfileVersion":1,"rectangles":[]}';

function request(overrides: Record<string, string> = {}, target = url, omittedHeaders: string[] = []): NextRequest {
  const headers: Record<string, string> = {
    host: "localhost:3000", origin: "http://localhost:3000", referer: "http://localhost:3000/projects/demo/pages/1",
    "sec-fetch-site": "same-origin", "sec-fetch-mode": "cors", "sec-fetch-dest": "empty",
    "x-forwarded-host": "localhost:3000", "x-forwarded-port": "3000", "x-forwarded-proto": "http", "x-forwarded-for": "127.0.0.1",
    "content-type": "application/json", accept: "application/json", "content-length": String(Buffer.byteLength(body)),
  };
  for (const name of omittedHeaders) delete headers[name];
  return new NextRequest(target, { method: "POST", body, headers: { ...headers, ...overrides } });
}

describe("panel-aware generation same-origin proxy", () => {
  afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); });

  it("forwards exact body bytes only to the fixed loopback API, with a bounded response", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response('{"status":"generated"}', { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const response = await POST(request(), { params: Promise.resolve({ projectId: "demo", pageNumber: "1" }) });
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ status: "generated" });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [target, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(target).toBe("http://127.0.0.1:8000/projects/demo/pages/1/panel-aware-generation");
    expect(init.method).toBe("POST");
    expect(init.redirect).toBe("error");
    expect(Buffer.from(init.body as Uint8Array).toString("utf8")).toBe(body);
    expect(Object.keys(init.headers as Record<string, string>).sort()).toEqual([
      "accept", "content-length", "content-type", "origin", "referer", "sec-fetch-dest", "sec-fetch-mode", "sec-fetch-site"
    ]);
  });

  it.each([
    [{ origin: "https://attacker.invalid" }],
    [{ host: "attacker.invalid" }],
    [{ referer: "http://attacker.invalid/projects/demo/pages/1" }],
    [{ "sec-fetch-site": "cross-site" }],
    [{ "sec-fetch-mode": "navigate" }],
    [{ "sec-fetch-dest": "iframe" }],
    [{ cookie: "session=secret" }],
    [{ authorization: "Bearer secret" }],
    [{ "x-forwarded-host": "attacker.invalid" }],
    [{ "x-forwarded-port": "8000" }],
    [{ "x-forwarded-port": "03000" }],
    [{ "x-forwarded-proto": "https" }],
    [{ "x-forwarded-proto": "HTTP" }],
    [{ "x-forwarded-for": "192.0.2.1" }],
    [{ "x-forwarded-for": "not-an-ip" }],
    [{ "x-forwarded-host": "localhost:3000,attacker.invalid" }],
    [{ "x-forwarded-for": "127.0.0.1,192.0.2.1" }],
    [{ "x-forwarded-prefix": "/unexpected" }],
    [{ forwarded: "for=127.0.0.1;host=localhost:3000;proto=http" }],
    [{ "x-real-ip": "127.0.0.1" }],
    [{ via: "1.1 proxy" }],
    [{ "content-length": "999999" }]
  ])("rejects untrusted request headers without contacting the API", async (headers) => {
    const fetchMock = vi.fn(); vi.stubGlobal("fetch", fetchMock);
    const response = await POST(request(headers), { params: Promise.resolve({ projectId: "demo", pageNumber: "1" }) });
    expect(response.status).toBe(422);
    expect(await response.json()).toEqual({ code: "invalid_input", message: "Request validation failed." });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it.each(["x-forwarded-host", "x-forwarded-port", "x-forwarded-proto", "x-forwarded-for"])(
    "rejects a missing Next-generated %s header", async (name) => {
      const fetchMock = vi.fn(); vi.stubGlobal("fetch", fetchMock);
      const response = await POST(request({}, url, [name]), { params: Promise.resolve({ projectId: "demo", pageNumber: "1" }) });
      expect(response.status).toBe(422);
      expect(fetchMock).not.toHaveBeenCalled();
    }
  );

  it("rejects repeated forwarded values after Headers coalesces them", async () => {
    const headers = new Headers(request().headers);
    headers.append("x-forwarded-host", "attacker.invalid");
    expect(headers.get("x-forwarded-host")).toContain(",");
    const fetchMock = vi.fn(); vi.stubGlobal("fetch", fetchMock);
    const duplicateRequest = new NextRequest(url, { method: "POST", body, headers });
    const response = await POST(duplicateRequest, { params: Promise.resolve({ projectId: "demo", pageNumber: "1" }) });
    expect(response.status).toBe(422);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("does not expose upstream details or follow redirects", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("provider secret and internal path", { status: 302, headers: { location: "http://remote.invalid" } }));
    vi.stubGlobal("fetch", fetchMock);
    const response = await POST(request(), { params: Promise.resolve({ projectId: "demo", pageNumber: "1" }) });
    expect(response.status).toBe(503);
    expect(await response.text()).not.toMatch(/provider|secret|internal|remote/);
    expect(fetchMock.mock.calls[0][1].redirect).toBe("error");
  });

  it("maps contradictory upstream status and error code pairs to fixed uncertain failure", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ code: "invalid_input", message: "secret" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const response = await POST(request(), { params: Promise.resolve({ projectId: "demo", pageNumber: "1" }) });
    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({ code: "activation_unavailable", message: "Generation is unavailable." });
  });

  it("rejects a non-canonical encoded alias before contacting the API", async () => {
    const fetchMock = vi.fn(); vi.stubGlobal("fetch", fetchMock);
    const response = await POST(request({}, url.replace("/demo/", "/%64emo/")), { params: Promise.resolve({ projectId: "demo", pageNumber: "1" }) });
    expect(response.status).toBe(422);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("rejects payloads over 32 KiB before upstream activation", async () => {
    const oversized = "x".repeat(32 * 1024 + 1);
    const fetchMock = vi.fn(); vi.stubGlobal("fetch", fetchMock);
    const response = await POST(new NextRequest(url, { method: "POST", body: oversized, headers: {
      ...Object.fromEntries(request().headers), "content-length": String(Buffer.byteLength(oversized))
    }}), { params: Promise.resolve({ projectId: "demo", pageNumber: "1" }) });
    expect(response.status).toBe(422);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
