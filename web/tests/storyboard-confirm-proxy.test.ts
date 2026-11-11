import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { POST } from "../app/api/projects/[projectId]/pages/[pageNumber]/storyboard/confirm/route";

const url = "http://localhost:3000/api/projects/demo/pages/1/storyboard/confirm";
const body = JSON.stringify({ requestVersion: 1, expectedSource: { state: "Reviewed", page_design: {}, review: {} }, confirmed: true, panels: [] });

function request(overrides: Record<string, string> = {}, content = body, requestUrl = url): NextRequest {
  return new NextRequest(requestUrl, { method: "POST", body: content, headers: {
    host: "localhost:3000", origin: "http://localhost:3000", referer: "http://localhost:3000/projects/demo/pages/1",
    "sec-fetch-site": "same-origin", "sec-fetch-mode": "cors", "sec-fetch-dest": "empty",
    "x-forwarded-host": "localhost:3000", "x-forwarded-port": "3000", "x-forwarded-proto": "http", "x-forwarded-for": "127.0.0.1",
    "content-type": "application/json", accept: "application/json", "content-length": String(Buffer.byteLength(content)), ...overrides
  } });
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
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toBe("http://127.0.0.1:8000/projects/demo/pages/1/storyboard/confirm");
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
    [{ "content-type": "application/json; charset=utf-8, text/plain" }],
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
});
