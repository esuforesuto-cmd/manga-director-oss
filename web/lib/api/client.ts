import type {
  ApiError,
  ChapterDetail,
  EvidenceLinkedApprovalRequest,
  PageAction,
  PageDetail,
  PanelAwareGenerationRequest,
  PanelAwareGenerationResponse,
  StoryboardConfirmationRequest,
  StoryboardConfirmationResponse,
  ProjectDetail,
  ProjectSummary,
  VisualReviewEvidenceHistoryResponse,
  VisualReviewEvidenceResponse,
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

export function apiBaseUrl(): string {
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
  baseUrl: string = apiBaseUrl(),
  preserveStoryboardSource = false
): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers: { Accept: "application/json", ...init.headers },
    cache: "no-store"
  });
  const raw = await response.text();
  let value: unknown;
  try { value = JSON.parse(raw); } catch (error) {
    if (response.ok) throw error;
    value = undefined;
  }
  if (!response.ok) {
    const payload = value as ApiError | undefined;
    throw new ApiClientError(payload?.message ?? `API request failed (${response.status}).`, response.status, payload);
  }
  if (preserveStoryboardSource && value && typeof value === "object" && !Array.isArray(value)) {
    const page = value as Record<string, unknown>;
    const artifacts = page.artifacts;
    const pageDesign = artifacts && typeof artifacts === "object" && !Array.isArray(artifacts)
      ? (artifacts as Record<string, unknown>).pageDesign : undefined;
    const review = artifacts && typeof artifacts === "object" && !Array.isArray(artifacts)
      ? (artifacts as Record<string, unknown>).review : undefined;
    if (page.state !== "Reviewed" || !pageDesign || typeof pageDesign !== "object" || Array.isArray(pageDesign)
      || !review || typeof review !== "object" || Array.isArray(review)) return value as T;
    const rawPageDesign = rawJsonValueAt(raw, ["artifacts", "pageDesign"]);
    const rawReview = rawJsonValueAt(raw, ["artifacts", "review"]);
    return {
      ...value,
      __storyboardExpectedSourceJson: `{"state":"Reviewed","page_design":${rawPageDesign},"review":${rawReview}}`
    } as T;
  }
  return value as T;
}

function skipJsonWhitespace(source: string, start: number): number {
  let index = start;
  while (/\s/.test(source[index] ?? "")) index += 1;
  return index;
}

function jsonStringEnd(source: string, start: number): number {
  if (source[start] !== '"') throw new TypeError("Expected a JSON string.");
  let index = start + 1;
  while (index < source.length) {
    if (source[index] === "\\") { index += 2; continue; }
    if (source[index] === '"') return index + 1;
    index += 1;
  }
  throw new TypeError("Incomplete JSON string.");
}

function jsonValueEnd(source: string, start: number): number {
  const first = source[start];
  if (first === '"') return jsonStringEnd(source, start);
  if (first !== "{" && first !== "[") {
    let index = start;
    while (index < source.length && !/[\s,}\]]/.test(source[index])) index += 1;
    return index;
  }
  const stack = [first === "{" ? "}" : "]"];
  let index = start + 1;
  while (index < source.length && stack.length) {
    const character = source[index];
    if (character === '"') { index = jsonStringEnd(source, index); continue; }
    if (character === "{") stack.push("}");
    else if (character === "[") stack.push("]");
    else if (character === stack[stack.length - 1]) stack.pop();
    index += 1;
  }
  if (stack.length) throw new TypeError("Incomplete JSON value.");
  return index;
}

function jsonObjectPropertyStart(source: string, start: number, property: string): number {
  let index = skipJsonWhitespace(source, start);
  if (source[index] !== "{") throw new TypeError("Expected a JSON object.");
  index = skipJsonWhitespace(source, index + 1);
  let found: number | undefined;
  while (source[index] !== "}") {
    const keyEnd = jsonStringEnd(source, index);
    const key = JSON.parse(source.slice(index, keyEnd)) as string;
    index = skipJsonWhitespace(source, keyEnd);
    if (source[index] !== ":") throw new TypeError("Expected a JSON property separator.");
    const valueStart = skipJsonWhitespace(source, index + 1);
    if (key === property) found = valueStart;
    index = skipJsonWhitespace(source, jsonValueEnd(source, valueStart));
    if (source[index] === ",") index = skipJsonWhitespace(source, index + 1);
    else if (source[index] !== "}") throw new TypeError("Expected a JSON object delimiter.");
  }
  if (found !== undefined) return found;
  throw new TypeError("Required JSON property is missing.");
}

function rawJsonValueAt(source: string, path: string[]): string {
  let start = 0;
  for (const property of path) start = jsonObjectPropertyStart(source, start, property);
  return source.slice(start, jsonValueEnd(source, start));
}

function encoded(value: string | number): string {
  return encodeURIComponent(String(value));
}

export const STORYBOARD_CONFIRMATION_MAX_BODY_BYTES = 32_768;

export function serializeStoryboardConfirmationRequestBody(
  body: StoryboardConfirmationRequest,
  expectedSourceJson?: string
): string {
  return expectedSourceJson
    ? `{"requestVersion":1,"expectedSource":${expectedSourceJson},"confirmed":true,"panels":${JSON.stringify(body.panels)}}`
    : JSON.stringify(body);
}

export function isStoryboardConfirmationBodyWithinLimit(serializedBody: string): boolean {
  return new TextEncoder().encode(serializedBody).byteLength <= STORYBOARD_CONFIRMATION_MAX_BODY_BYTES;
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
      request<PageDetail>(`/projects/${encoded(projectId)}/pages/${encoded(pageNumber)}`, {}, apiBaseUrl(), true),
    generatePanels: (projectId: string, pageNumber: number, body: PanelAwareGenerationRequest) =>
      request<PanelAwareGenerationResponse>(`/api/projects/${encoded(projectId)}/pages/${encoded(pageNumber)}/panel-aware-generation`, {
        method: "POST", body: JSON.stringify(body), headers: { "Content-Type": "application/json" }
      }, ""),
    confirmStoryboard: (
      projectId: string,
      pageNumber: number,
      body: StoryboardConfirmationRequest,
      expectedSourceJson?: string,
      serializedBody?: string
    ) => request<StoryboardConfirmationResponse>(`/api/projects/${encoded(projectId)}/pages/${encoded(pageNumber)}/storyboard/confirm`, {
      method: "POST",
      body: serializedBody ?? serializeStoryboardConfirmationRequestBody(body, expectedSourceJson),
      headers: { "Content-Type": "application/json" }
    }, ""),
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
    recordVisualReviewEvidence: (
      projectId: string,
      pageNumber: number,
      body: VisualReviewReadinessRequest
    ) =>
      request<VisualReviewEvidenceResponse>(
        `/projects/${encoded(projectId)}/pages/${encoded(pageNumber)}/visual-review-evidence`,
        {
          method: "POST",
          body: JSON.stringify(body),
          headers: { "Content-Type": "application/json" }
        },
        loopbackApiBaseUrl()
      ),
    getVisualReviewEvidenceHistory: (
      projectId: string,
      pageNumber: number
    ) =>
      request<VisualReviewEvidenceHistoryResponse>(
        `/projects/${encoded(projectId)}/pages/${encoded(pageNumber)}/visual-review-evidence`,
        { method: "GET" },
        loopbackApiBaseUrl()
      ),
    approveWithReviewEvidence: (
      projectId: string,
      pageNumber: number,
      body: EvidenceLinkedApprovalRequest
    ) =>
      request<PageDetail>(
        `/projects/${encoded(projectId)}/pages/${encoded(pageNumber)}/evidence-linked-approval`,
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
