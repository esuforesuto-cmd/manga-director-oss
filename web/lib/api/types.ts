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

export type PageAction =
  | "design"
  | "review"
  | "storyboard"
  | "dialogue"
  | "prompt"
  | "generate"
  | "quality"
  | "continuity"
  | "approve";

export type ProjectAction = "run" | "resume";
export type WorkflowAction = PageAction | ProjectAction;

export type HumanVisualCriterion =
  | "character_identity"
  | "face"
  | "costume"
  | "props"
  | "pose"
  | "gaze"
  | "emotion"
  | "screen_direction"
  | "location"
  | "time"
  | "composition"
  | "panel_intent"
  | "visible_corruption"
  | "truncation"
  | "watermark"
  | "unsafe_content"
  | "unintended_text"
  | "continuity_comparison";

export type HumanVisualOutcome =
  | "acceptable"
  | "needs_review"
  | "blocked"
  | "not_applicable";

export type OverallHumanJudgment =
  | "acceptable_for_approval_consideration"
  | "further_review_required"
  | "blocked";

export interface HumanVisualChecklistDecision {
  criterion: HumanVisualCriterion;
  outcome: HumanVisualOutcome;
  rationale: string;
}

export interface VisualReviewReadinessRequest {
  reviewerId: string;
  reviewedAt: string;
  checklist: HumanVisualChecklistDecision[];
  overallJudgment: OverallHumanJudgment;
  rationale: string;
}

export interface VisualReviewFinding {
  code: string;
  status: "needs_review" | "blocked";
  message: string;
  criterion: string;
}

export interface VisualReviewReadinessResponse {
  status: "ready" | "needs_review" | "blocked";
  ready: boolean;
  pageState: PageState;
  findings: VisualReviewFinding[];
  missingPrerequisites: string[];
  analysisOnly: true;
}

export interface VisualReviewEvidenceResponse extends VisualReviewReadinessResponse {
  evidenceRecorded: true;
  idempotentReplay: boolean;
}
