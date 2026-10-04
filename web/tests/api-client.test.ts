import { describe, expect, it, vi } from "vitest";

import { ApiClientError, api } from "@/lib/api/client";

describe("REST API client", () => {
  it("encodes project IDs and sends action metadata through the API client", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ pageNumber: 1 }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await api.pages.execute("my project", 1, "design", { page_design: { purpose: "hook" } });

    expect(fetchMock.mock.calls[0][0]).toContain("my%20project/pages/1/design");
    expect(fetchMock.mock.calls[0][1].body).toContain("page_design");
  });

  it("maps a failed API response to a structured client error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ message: "Invalid state" }), { status: 409 })));

    await expect(api.projects.run("demo")).rejects.toBeInstanceOf(ApiClientError);
  });
});
