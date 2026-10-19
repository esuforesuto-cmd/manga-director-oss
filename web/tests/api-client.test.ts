import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiClientError, api } from "@/lib/api/client";
import type { HumanVisualCriterion, VisualReviewReadinessRequest } from "@/lib/api/types";

const visualCriteria: HumanVisualCriterion[] = [
  "character_identity", "face", "costume", "props", "pose", "gaze",
  "emotion", "screen_direction", "location", "time", "composition",
  "panel_intent", "visible_corruption", "truncation", "watermark",
  "unsafe_content", "unintended_text", "continuity_comparison"
];

describe("REST API client", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

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

  it("sends the explicit approver with the presentation DTO name", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ pageNumber: 1 }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await api.pages.approve("demo", 1, "editor");

    expect(fetchMock.mock.calls[0][1].body).toContain('"approvedBy":"editor"');
    expect("remove" in api.projects).toBe(false);
  });

  it("derives the generated image route from only project and page identity", () => {
    expect(api.pages.generatedAssetUrl("my project", 7)).toBe(
      "http://127.0.0.1:8000/projects/my%20project/pages/7/generated-asset"
    );
    expect(api.pages.approvedAssetDownloadUrl("my project", 7)).toBe(
      "http://127.0.0.1:8000/projects/my%20project/pages/7/approved-asset-download"
    );
  });

  it("posts only explicit human judgment to the fixed visual readiness route", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      status: "ready",
      ready: true,
      pageState: "QualityChecked",
      findings: [],
      missingPrerequisites: [],
      analysisOnly: true
    }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const body: VisualReviewReadinessRequest = {
      reviewerId: "reviewer:local",
      reviewedAt: "2026-10-18T12:00:00Z",
      checklist: visualCriteria.map((criterion) => ({
        criterion,
        outcome: "acceptable",
        rationale: "Reviewed directly"
      })),
      overallJudgment: "acceptable_for_approval_consideration",
      rationale: "Complete local visual review"
    };

    await api.pages.assessVisualReview("my project", 7, body);

    expect(fetchMock.mock.calls[0][0]).toBe(
      "http://127.0.0.1:8000/projects/my%20project/pages/7/visual-review-readiness"
    );
    expect(fetchMock.mock.calls[0][1].method).toBe("POST");
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual(body);
    expect(fetchMock.mock.calls[0][1].body).not.toMatch(
      /assetId|attemptId|provider|digest|path|storageName|root|url|approvedBy/
    );
  });

  it.each([
    "https://127.0.0.1:8000",
    "http://localhost:8000",
    "http://remote.example:8000",
    "http://127.0.0.1",
    "http://user@127.0.0.1:8000",
    "http://127.0.0.1:8000/proxy",
    "http://127.0.0.1:8000?asset=other",
    "http://127.0.0.1:8000#asset"
  ])("fails closed for a non-canonical generated image base: %s", (configured) => {
    vi.stubEnv("NEXT_PUBLIC_MANGA_DIRECTOR_API_URL", configured);

    expect(() => api.pages.generatedAssetUrl("demo", 1)).toThrow(ApiClientError);
    expect(() => api.pages.approvedAssetDownloadUrl("demo", 1)).toThrow(ApiClientError);
  });

  it.each([
    "https://127.0.0.1:8000",
    "http://localhost:8000",
    "http://remote.example:8000",
    "http://127.0.0.1",
    "http://user@127.0.0.1:8000",
    "http://127.0.0.1:8000/proxy"
  ])("fails closed before visual review can contact a non-canonical base: %s", async (configured) => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    vi.stubEnv("NEXT_PUBLIC_MANGA_DIRECTOR_API_URL", configured);
    const body: VisualReviewReadinessRequest = {
      reviewerId: "reviewer:local",
      reviewedAt: "2026-10-18T12:00:00Z",
      checklist: visualCriteria.map((criterion) => ({
        criterion,
        outcome: "acceptable",
        rationale: "Reviewed directly"
      })),
      overallJudgment: "acceptable_for_approval_consideration",
      rationale: "Complete local visual review"
    };

    expect(() => api.pages.assessVisualReview("demo", 1, body)).toThrow(ApiClientError);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
