import type {
  ApiError,
  ChapterDetail,
  PageDetail,
  ProjectDetail,
  ProjectSummary,
  WorkflowAction,
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

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${apiBaseUrl()}${path}`, {
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
    remove: (projectId: string) => request<void>(`/projects/${encoded(projectId)}`, { method: "DELETE" }),
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
    execute: (projectId: string, pageNumber: number, action: WorkflowAction, metadata: Record<string, unknown> = {}) =>
      request<PageDetail>(`/projects/${encoded(projectId)}/pages/${encoded(pageNumber)}/${encoded(action)}`, {
        method: "POST",
        body: JSON.stringify({ metadata }),
        headers: { "Content-Type": "application/json" }
      })
  },
  workflow: {
    status: async (projectId: string, pageNumber: number): Promise<WorkflowStatus> =>
      (await request<PageDetail>(`/projects/${encoded(projectId)}/pages/${encoded(pageNumber)}`)).workflow,
    execute: (projectId: string, pageNumber: number, action: WorkflowAction, metadata: Record<string, unknown> = {}) =>
      request<PageDetail>(`/projects/${encoded(projectId)}/pages/${encoded(pageNumber)}/${encoded(action)}`, {
        method: "POST",
        body: JSON.stringify({ metadata }),
        headers: { "Content-Type": "application/json" }
      })
  }
};
