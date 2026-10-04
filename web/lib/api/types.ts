/** Intended REST DTOs; kept explicit until a compatible OpenAPI service is shipped. */
export type PageState =
  | "Draft"
  | "Designed"
  | "Reviewed"
  | "Storyboarded"
  | "PromptBuilt"
  | "Generated"
  | "QualityChecked"
  | "Approved";

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface ProjectSummary {
  id: string;
  title: string;
  currentState: PageState | null;
  updatedAt: string;
  progress: { completed: number; total: number };
}

export interface WorkflowStatus {
  currentState: PageState;
  currentStep: string | null;
  completedSteps: string[];
  availableActions: WorkflowAction[];
  history: Array<Record<string, unknown>>;
}

export interface ProjectDetail extends ProjectSummary {
  currentChapter: string | null;
  currentPage: number | null;
  chapters: ChapterSummary[];
  workflow: WorkflowStatus;
}

export interface ChapterSummary {
  id: string;
  title: string;
  pageCount: number;
  approvedPages: number;
}

export interface ChapterDetail extends ChapterSummary {
  pages: PageSummary[];
}

export interface PageSummary {
  pageNumber: number;
  state: PageState;
  qualityPassed: boolean | null;
  approved: boolean;
}

export interface PageDetail extends PageSummary {
  workflow: WorkflowStatus;
  input?: Record<string, unknown>;
  artifacts: Record<string, unknown>;
  messages: string[];
  errors: ApiError[];
  executionTimeMs: number | null;
  approvalRequired: boolean;
}

export type WorkflowAction =
  | "design"
  | "review"
  | "storyboard"
  | "dialogue"
  | "prompt"
  | "generate"
  | "quality"
  | "continuity"
  | "approve"
  | "run"
  | "resume"
  | "retry";
