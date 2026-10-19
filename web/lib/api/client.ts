import type {
  ApiError,
  ChapterDetail,
  PageAction,
  PageDetail,
  ProjectDetail,
  ProjectSummary,
  VisualReviewReadinessRequest,
  VisualReviewReadinessResponse,
  WorkflowStatus
} from "@/lib/api/types";

export class ApiClientError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly payload?: ApiError
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

function apiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_MANGA_DIRECTOR_API_URL
    ?? process.env.MANGA_DIRECTOR_API_URL
    ?? "http://127.0.0.1:8000";
  const parsed = new URL(configured);
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    throw new ApiClientError("API URL must use HTTP or HTTPS.", 0);
  }
  return parsed.toString().replace(/\/$/, "");
}

function loopbackApiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_MANGA_DIRECTOR_API_URL
    ?? process.env.MANGA_DIRECTOR_API_URL
    ?? "http://127.0.0.1:8000";
  const parsed = new URL(configured);
  const port = Number(parsed.port);
  if (
    parsed.protocol !== "http:"
    || parsed.hostname !== "127.0.0.1"
    || !Number.isInteger(port)
    || port < 1
    || port > 65535
    || parsed.username !== ""
    || parsed.password !== ""
    || parsed.pathname !== "/"
    || parsed.search !== ""
    || parsed.hash !== ""
  ) {
    throw new ApiClientError("This operation must use the local API.", 0);
  }
  return `http://127.0.0.1:${parsed.port}`;
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  baseUrl: string = apiBaseUrl()
): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers: { Accept: "application/json", ...init.headers },
    cache: "no-store"
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => undefined)) as ApiError | undefined;
    throw new ApiClientError(payload?.message ?? `API request failed (${response.status}).`, response.status, payload);
  }
  return (await response.json()) as T;
}

function encoded(value: string | number): string {
  return encodeURIComponent(String(value));
}

export const api = {
  health: () => request<{ status: string }>("/health"),
  projects: {
    list: () => request<ProjectSummary[]>("/projects"),
    get: (projectId: string) => request<ProjectDetail>(`/projects/${encoded(projectId)}`),
    create: (body: { id: string; title: string }) =>
      request<ProjectDetail>("/projects", { method: "POST", body: JSON.stringify(body), headers: { "Content-Type": "application/json" } }),
    run: (projectId: string) => request<ProjectDetail>(`/projects/${encoded(projectId)}/run`, { method: "POST" }),
    resume: (projectId: string) => request<ProjectDetail>(`/projects/${encoded(projectId)}/resume`, { method: "POST" })
  },
  chapters: {
    get: (projectId: string, chapterId: string) =>
      request<ChapterDetail>(`/projects/${encoded(projectId)}/chapters/${encoded(chapterId)}`),
    run: (projectId: string, chapterId: string) =>
      request<ChapterDetail>(`/projects/${encoded(projectId)}/chapters/${encoded(chapterId)}/run`, { method: "POST" })
  },
  pages: {
    get: (projectId: string, pageNumber: number) =>
      request<PageDetail>(`/projects/${encoded(projectId)}/pages/${encoded(pageNumber)}`),
    generatedAssetUrl: (projectId: string, pageNumber: number) =>
      `${loopbackApiBaseUrl()}/projects/${encoded(projectId)}/pages/${encoded(pageNumber)}/generated-asset`,
    approvedAssetDownloadUrl: (projectId: string, pageNumber: number) =>
      `${loopbackApiBaseUrl()}/projects/${encoded(projectId)}/pages/${encoded(pageNumber)}/approved-asset-download`,
    assessVisualReview: (
      projectId: string,
      pageNumber: number,
      body: VisualReviewReadinessRequest
    ) =>
      request<VisualReviewReadinessResponse>(
        `/projects/${encoded(projectId)}/pages/${encoded(pageNumber)}/visual-review-readiness`,
        {
          method: "POST",
          body: JSON.stringify(body),
          headers: { "Content-Type": "application/json" }
        },
        loopbackApiBaseUrl()
      ),
    execute: (projectId: string, pageNumber: number, action: PageAction, metadata: Record<string, unknown> = {}) =>
      request<PageDetail>(`/projects/${encoded(projectId)}/pages/${encoded(pageNumber)}/${encoded(action)}`, {
        method: "POST",
        body: JSON.stringify({ metadata }),
        headers: { "Content-Type": "application/json" }
      }),
    approve: (projectId: string, pageNumber: number, approvedBy: string, metadata: Record<string, unknown> = {}) =>
      request<PageDetail>(`/projects/${encoded(projectId)}/pages/${encoded(pageNumber)}/approve`, {
        method: "POST",
        body: JSON.stringify({ approvedBy, metadata }),
        headers: { "Content-Type": "application/json" }
      })
  },
  workflow: {
    status: async (projectId: string, pageNumber: number): Promise<WorkflowStatus> =>
      (await request<PageDetail>(`/projects/${encoded(projectId)}/pages/${encoded(pageNumber)}`)).workflow,
    execute: (projectId: string, pageNumber: number, action: PageAction, metadata: Record<string, unknown> = {}) =>
      request<PageDetail>(`/projects/${encoded(projectId)}/pages/${encoded(pageNumber)}/${encoded(action)}`, {
        method: "POST",
        body: JSON.stringify({ metadata }),
        headers: { "Content-Type": "application/json" }
      }),
    approve: (projectId: string, pageNumber: number, approvedBy: string, metadata: Record<string, unknown> = {}) =>
      request<PageDetail>(`/projects/${encoded(projectId)}/pages/${encoded(pageNumber)}/approve`, {
        method: "POST",
        body: JSON.stringify({ approvedBy, metadata }),
        headers: { "Content-Type": "application/json" }
      })
  }
};
