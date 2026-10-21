"""Local-only FastAPI workflow delivery with presentation-specific DTOs."""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal, cast
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from manga_director._version import __version__
from manga_director.application.approved_asset_download import (
    ApprovedAssetDownloadUnavailable,
    approved_asset_download_for,
)
from manga_director.application.evidence_linked_approval import (
    EvidenceLinkedApprovalUnavailable,
    evidence_linked_approval_for,
)
from manga_director.application.generated_asset_presentation import (
    GeneratedAssetPresentationUnavailable,
    generated_asset_presentation_for,
)
from manga_director.application.human_visual_review_evidence import (
    HumanVisualReviewEvidencePersistenceUnavailable,
    HumanVisualReviewEvidenceUnavailable,
    human_visual_review_evidence_for,
)
from manga_director.application.human_visual_review_evidence_history import (
    HumanVisualReviewEvidenceHistoryPersistenceUnavailable,
    HumanVisualReviewEvidenceHistoryUnavailable,
    human_visual_review_evidence_history_for,
)
from manga_director.application.human_visual_review_readiness import (
    HumanVisualReviewReadinessUnavailable,
    ReviewChecklistDecision,
    ReviewCriterion,
    ReviewOutcome,
    ReviewOverallJudgment,
    human_visual_review_readiness_for,
)
from manga_director.application.workflow import WorkflowApplicationService
from manga_director.domain.exceptions import (
    ProjectAlreadyExistsError,
    ProjectNotFoundError,
    StateTransitionError,
    ValidationError,
)
from manga_director.domain.project import Chapter, Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.workflow.contracts import WorkflowStatus
from manga_director.workflow.hierarchy_contracts import ChapterContext, ProjectContext

LOGGER = logging.getLogger(__name__)
LOCAL_WEB_ORIGINS = ("http://127.0.0.1:3000", "http://localhost:3000")
_GENERATED_ASSET_HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
}
_APPROVED_ASSET_DOWNLOAD_HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
}
_APPROVED_ASSET_DOWNLOAD_REJECTED_HEADERS = (
    "range",
    "if-range",
    "if-match",
    "if-none-match",
    "if-modified-since",
    "if-unmodified-since",
)
_VISUAL_REVIEW_HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
}
_VISUAL_REVIEW_SUFFIX = "/visual-review-readiness"
_VISUAL_REVIEW_EVIDENCE_SUFFIX = "/visual-review-evidence"
_EVIDENCE_LINKED_APPROVAL_SUFFIX = "/evidence-linked-approval"
_VISUAL_REVIEW_SUFFIXES = (
    _VISUAL_REVIEW_SUFFIX,
    _VISUAL_REVIEW_EVIDENCE_SUFFIX,
    _EVIDENCE_LINKED_APPROVAL_SUFFIX,
)
_VISUAL_REVIEW_MAX_CONTENT_LENGTH = 32_768
_VISUAL_REVIEW_HISTORY_MAX_RESPONSE_BYTES = 1_048_576
_VISUAL_REVIEW_HISTORY_REJECTED_HEADERS = (
    "range",
    "if-range",
    "if-match",
    "if-none-match",
    "if-modified-since",
    "if-unmodified-since",
)
_VISUAL_REVIEW_REQUIRED_CRITERIA = {
    "character_identity",
    "face",
    "costume",
    "props",
    "pose",
    "gaze",
    "emotion",
    "screen_direction",
    "location",
    "time",
    "composition",
    "panel_intent",
    "visible_corruption",
    "truncation",
    "watermark",
    "unsafe_content",
    "unintended_text",
    "continuity_comparison",
}
_VISUAL_REVIEW_OPTIONAL_CRITERIA = {"props", "continuity_comparison"}
_VISUAL_REVIEW_SECRET_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "endpoint",
    "password",
    "secret",
    "token",
)


class _HttpModel(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)


class _ClosedHttpModel(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="forbid")


class _ClosedHttpRequestModel(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=False, extra="forbid")


class WorkflowAction(StrEnum):
    DESIGN = "design"
    REVIEW = "review"
    STORYBOARD = "storyboard"
    DIALOGUE = "dialogue"
    PROMPT = "prompt"
    GENERATE = "generate"
    QUALITY = "quality"
    CONTINUITY = "continuity"
    APPROVE = "approve"


class HealthDTO(_HttpModel):
    status: str = "ok"


class ApiErrorDTO(_HttpModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class ProgressDTO(_HttpModel):
    completed: int
    total: int


class WorkflowStatusDTO(_HttpModel):
    current_state: PageState | None = Field(alias="currentState")
    current_step: str | None = Field(alias="currentStep")
    completed_steps: list[str] = Field(alias="completedSteps")
    available_actions: list[str] = Field(alias="availableActions")
    history: list[dict[str, Any]]


class ChapterSummaryDTO(_HttpModel):
    id: str
    title: str
    page_count: int = Field(alias="pageCount")
    approved_pages: int = Field(alias="approvedPages")


class PageSummaryDTO(_HttpModel):
    page_number: int = Field(alias="pageNumber")
    state: PageState
    quality_passed: bool | None = Field(alias="qualityPassed")
    approved: bool


class ProjectSummaryDTO(_HttpModel):
    id: str
    title: str
    current_state: PageState | None = Field(alias="currentState")
    updated_at: str = Field(alias="updatedAt")
    progress: ProgressDTO


class ProjectDetailDTO(ProjectSummaryDTO):
    current_chapter: str | None = Field(alias="currentChapter")
    current_page: int | None = Field(alias="currentPage")
    chapters: list[ChapterSummaryDTO]
    workflow: WorkflowStatusDTO


class ChapterDetailDTO(ChapterSummaryDTO):
    pages: list[PageSummaryDTO]


class PageDetailDTO(PageSummaryDTO):
    workflow: WorkflowStatusDTO
    input: dict[str, Any] | None = None
    artifacts: dict[str, Any]
    messages: list[str]
    errors: list[ApiErrorDTO]
    execution_time_ms: int | None = Field(alias="executionTimeMs")
    approval_required: bool = Field(alias="approvalRequired")


class CreateProjectRequest(_HttpModel):
    id: str = Field(min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
    title: str = Field(min_length=1)
    page_number: int = Field(default=1, ge=1, alias="pageNumber")
    metadata: dict[str, Any] = Field(default_factory=dict)


class PageActionRequest(_HttpModel):
    metadata: dict[str, Any] = Field(default_factory=dict)
    approved_by: str | None = Field(default=None, min_length=1, alias="approvedBy")


class EvidenceLinkedApprovalRequest(_ClosedHttpRequestModel):
    approved_by: str = Field(min_length=1, max_length=200, alias="approvedBy")
    review_id: str = Field(min_length=1, max_length=200, alias="reviewId")

    @field_validator("approved_by", "review_id")
    @classmethod
    def _validate_reference(cls, value: str) -> str:
        if (
            value != value.strip()
            or any(character.isspace() or ord(character) < 32 for character in value)
            or value.startswith(("/", "\\"))
            or "/" in value
            or "\\" in value
            or "://" in value
            or "@" in value
        ):
            raise ValueError("approval references must be bounded logical references")
        return value


class VisualReviewChecklistItemRequest(_ClosedHttpRequestModel):
    criterion: ReviewCriterion
    outcome: ReviewOutcome
    rationale: str = Field(min_length=1, max_length=500)

    @field_validator("rationale")
    @classmethod
    def _validate_rationale(cls, value: str) -> str:
        return _safe_visual_review_text(value, "rationale")


class VisualReviewReadinessRequest(_ClosedHttpRequestModel):
    reviewer_id: str = Field(min_length=1, max_length=200, alias="reviewerId")
    reviewed_at: datetime = Field(alias="reviewedAt")
    checklist: tuple[VisualReviewChecklistItemRequest, ...] = Field(
        min_length=18,
        max_length=18,
    )
    overall_judgment: ReviewOverallJudgment = Field(alias="overallJudgment")
    rationale: str = Field(min_length=1, max_length=500)

    @field_validator("reviewer_id")
    @classmethod
    def _validate_reviewer_id(cls, value: str) -> str:
        if any(character.isspace() or ord(character) < 32 for character in value):
            raise ValueError("reviewerId must be a logical reference")
        return _safe_visual_review_text(value, "reviewerId")

    @field_validator("reviewed_at")
    @classmethod
    def _require_timezone_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("reviewedAt must be timezone-aware")
        return value

    @field_validator("rationale")
    @classmethod
    def _validate_rationale(cls, value: str) -> str:
        return _safe_visual_review_text(value, "rationale")

    @model_validator(mode="after")
    def _validate_complete_checklist(self) -> VisualReviewReadinessRequest:
        criteria = [item.criterion for item in self.checklist]
        if set(criteria) != _VISUAL_REVIEW_REQUIRED_CRITERIA or len(set(criteria)) != len(
            criteria
        ):
            raise ValueError("checklist must contain every criterion exactly once")
        if any(
            item.outcome == "not_applicable"
            and item.criterion not in _VISUAL_REVIEW_OPTIONAL_CRITERIA
            for item in self.checklist
        ):
            raise ValueError("not_applicable is not permitted for this criterion")
        return self


class VisualReviewFindingDTO(_ClosedHttpModel):
    code: str
    status: Literal["needs_review", "blocked"]
    message: str
    criterion: str = ""


class VisualReviewReadinessResponse(_ClosedHttpModel):
    status: Literal["ready", "needs_review", "blocked"]
    ready: bool
    page_state: PageState = Field(alias="pageState")
    findings: tuple[VisualReviewFindingDTO, ...]
    missing_prerequisites: tuple[str, ...] = Field(alias="missingPrerequisites")
    analysis_only: Literal[True] = Field(alias="analysisOnly")


class VisualReviewEvidenceResponse(VisualReviewReadinessResponse):
    evidence_recorded: Literal[True] = Field(alias="evidenceRecorded")
    idempotent_replay: bool = Field(alias="idempotentReplay")


class VisualReviewHistoryChecklistItemDTO(_ClosedHttpModel):
    criterion: ReviewCriterion
    outcome: ReviewOutcome
    rationale: str


class VisualReviewHistoryRecordDTO(_ClosedHttpModel):
    review_id: str = Field(alias="reviewId")
    output_asset_id: str = Field(alias="outputAssetId")
    reviewer_id: str = Field(alias="reviewerId")
    reviewed_at: datetime = Field(alias="reviewedAt")
    page_state: Literal["Generated", "QualityChecked"] = Field(alias="pageState")
    checklist: tuple[VisualReviewHistoryChecklistItemDTO, ...]
    overall_judgment: ReviewOverallJudgment = Field(alias="overallJudgment")
    rationale: str
    status: Literal["ready", "needs_review", "blocked"]
    ready: bool
    findings: tuple[VisualReviewFindingDTO, ...]
    missing_prerequisites: tuple[str, ...] = Field(alias="missingPrerequisites")
    analysis_only: Literal[True] = Field(alias="analysisOnly")


class VisualReviewEvidenceHistoryResponse(_ClosedHttpModel):
    page_number: int = Field(alias="pageNumber")
    record_count: int = Field(alias="recordCount")
    complete: Literal[True]
    read_only: Literal[True] = Field(alias="readOnly")
    analysis_only: Literal[True] = Field(alias="analysisOnly")
    records: tuple[VisualReviewHistoryRecordDTO, ...]


def create_workflow_app(application: WorkflowApplicationService) -> Any:
    """Create a localhost CORS-scoped workflow API without importing MCP."""

    try:
        from fastapi import FastAPI
        from fastapi.exceptions import RequestValidationError
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.responses import JSONResponse, Response
        from starlette.background import BackgroundTask
        from starlette.exceptions import HTTPException as StarletteHTTPException
        from starlette.requests import Request
    except ImportError as exc:  # pragma: no cover - depends on optional extra.
        raise RuntimeError("Install manga-director[api] to enable workflow HTTP routes.") from exc

    app = FastAPI(title="manga-director workflow", version=__version__)
    _register_visual_review_request_guard(app, json_response=JSONResponse)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(LOCAL_WEB_ORIGINS),
        allow_methods=["GET", "POST"],
        allow_headers=["accept", "content-type"],
    )
    _register_error_handlers(
        app,
        request_validation_error_type=RequestValidationError,
        http_exception_type=StarletteHTTPException,
        json_response=JSONResponse,
    )
    _register_routes(
        app,
        application,
        request_type=Request,
        response_type=Response,
        json_response=JSONResponse,
        background_task_type=BackgroundTask,
    )
    return app


def _register_visual_review_request_guard(app: Any, *, json_response: Any) -> None:
    async def reject_unbounded_visual_review_request(request: Any, call_next: Any) -> Any:
        evidence_linked_approval = (
            request.method == "POST"
            and request.url.path.endswith(_EVIDENCE_LINKED_APPROVAL_SUFFIX)
        )
        content_length = (
            _single_request_header(request, "content-length")
            if evidence_linked_approval
            else request.headers.get("content-length")
        )
        if (
            request.method == "POST"
            and request.url.path.endswith(_VISUAL_REVIEW_SUFFIXES)
            and (
                request.query_params
                or "transfer-encoding" in request.headers
                or not _bounded_content_length(content_length)
            )
        ):
            return _visual_review_error(json_response, 422, "invalid_input")
        if evidence_linked_approval:
            try:
                value = json.loads(
                    await request.body(),
                    object_pairs_hook=_closed_json_members,
                    parse_constant=lambda _value: (_ for _ in ()).throw(
                        ValueError("non-finite JSON value")
                    ),
                )
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                return _visual_review_error(json_response, 422, "invalid_input")
            if not isinstance(value, dict):
                return _visual_review_error(json_response, 422, "invalid_input")
        return await call_next(request)

    app.middleware("http")(reject_unbounded_visual_review_request)


def _closed_json_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON member")
        result[key] = value
    return result


def _register_error_handlers(
    app: Any,
    *,
    request_validation_error_type: type[Exception],
    http_exception_type: type[Exception],
    json_response: Any,
) -> None:
    def error_response(
        status_code: int,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        payload = ApiErrorDTO(code=code, message=message, details=details)
        return json_response(
            status_code=status_code,
            content=payload.model_dump(mode="json", by_alias=True, exclude_none=True),
            headers=headers,
        )

    async def request_validation_error(request: Any, error: Any) -> Any:
        issues = [
            {
                "location": [str(part) for part in item.get("loc", ())],
                "type": item.get("type", "invalid"),
            }
            for item in error.errors()
        ]
        return error_response(
            422,
            "invalid_input",
            "Request validation failed.",
            {"issues": issues},
            headers=_visual_review_headers_for(request),
        )

    async def project_not_found(_request: Any, error: ProjectNotFoundError) -> Any:
        return error_response(404, "not_found", str(error))

    async def project_exists(_request: Any, error: ProjectAlreadyExistsError) -> Any:
        return error_response(409, "already_exists", str(error))

    async def invalid_transition(_request: Any, error: StateTransitionError) -> Any:
        return error_response(409, "invalid_transition", str(error))

    async def invalid_domain_input(_request: Any, error: ValidationError) -> Any:
        return error_response(422, "invalid_input", str(error))

    async def http_error(request: Any, error: Any) -> Any:
        code, message = _http_error_content(error.status_code)
        return error_response(
            error.status_code,
            code,
            message,
            headers=_visual_review_headers_for(request),
        )

    async def unexpected_error(request: Any, error: Exception) -> Any:
        LOGGER.error(
            "Unhandled workflow HTTP error",
            exc_info=(type(error), error, error.__traceback__),
        )
        return error_response(
            500,
            "internal_error",
            "An internal error occurred.",
            headers=_visual_review_headers_for(request),
        )

    app.add_exception_handler(request_validation_error_type, request_validation_error)
    app.add_exception_handler(ProjectNotFoundError, project_not_found)
    app.add_exception_handler(ProjectAlreadyExistsError, project_exists)
    app.add_exception_handler(StateTransitionError, invalid_transition)
    app.add_exception_handler(ValidationError, invalid_domain_input)
    app.add_exception_handler(http_exception_type, http_error)
    app.add_exception_handler(Exception, unexpected_error)


def _http_error_content(status_code: int) -> tuple[str, str]:
    if status_code == 404:
        return "not_found", "Not found."
    if status_code == 405:
        return "method_not_allowed", "Method not allowed."
    return "http_error", "HTTP request failed."


def _visual_review_headers_for(request: Any) -> dict[str, str] | None:
    path = getattr(getattr(request, "url", None), "path", "")
    return _VISUAL_REVIEW_HEADERS if path.endswith(_VISUAL_REVIEW_SUFFIXES) else None


def _register_routes(
    app: Any,
    application: WorkflowApplicationService,
    *,
    request_type: type[Any],
    response_type: Any,
    json_response: Any,
    background_task_type: Any,
) -> None:

    def health() -> HealthDTO:
        return HealthDTO()

    def list_projects() -> list[ProjectSummaryDTO]:
        return [_project_summary(project) for project in application.list_projects()]

    def create_project(body: CreateProjectRequest) -> ProjectDetailDTO:
        application.create_project(body.id, body.title, body.page_number, body.metadata)
        return _project_detail(application, body.id)

    def get_project(project_id: str) -> ProjectDetailDTO:
        return _project_detail(application, _validated_project_id(project_id))

    def run_project(project_id: str) -> ProjectDetailDTO:
        project_id = _validated_project_id(project_id)
        application.run_project(project_id)
        return _project_detail(application, project_id)

    def resume_project(project_id: str) -> ProjectDetailDTO:
        project_id = _validated_project_id(project_id)
        application.resume_project(project_id)
        return _project_detail(application, project_id)

    def get_chapter(project_id: str, chapter_id: str) -> ChapterDetailDTO:
        project_id = _validated_project_id(project_id)
        context = cast(ChapterContext, application.get_chapter_status(project_id, chapter_id))
        return _chapter_detail(context.chapter, context.pages)

    def run_chapter(project_id: str, chapter_id: str) -> ChapterDetailDTO:
        project_id = _validated_project_id(project_id)
        application.run_chapter(project_id, chapter_id)
        return get_chapter(project_id, chapter_id)

    def get_page(project_id: str, page_number: int) -> PageDetailDTO:
        return _page_detail(
            application,
            _validated_project_id(project_id),
            _validated_page_number(page_number),
        )

    get_generated_asset = _generated_asset_route(
        application,
        request_type=request_type,
        response_type=response_type,
        json_response=json_response,
        background_task_type=background_task_type,
    )
    get_approved_asset_download = _approved_asset_download_route(
        application,
        request_type=request_type,
        response_type=response_type,
        json_response=json_response,
        background_task_type=background_task_type,
    )
    reject_invalid_approved_asset_download_path = (
        _invalid_approved_asset_download_path_route(json_response)
    )
    assess_visual_review = _visual_review_readiness_route(
        application,
        request_type=request_type,
        json_response=json_response,
    )
    record_visual_review_evidence = _visual_review_evidence_route(
        application,
        request_type=request_type,
        json_response=json_response,
    )
    read_visual_review_evidence_history = _visual_review_evidence_history_route(
        application,
        request_type=request_type,
        json_response=json_response,
    )
    approve_with_evidence = _evidence_linked_approval_route(
        application,
        request_type=request_type,
        json_response=json_response,
    )

    def execute_page(
        project_id: str,
        page_number: int,
        action: WorkflowAction,
        body: PageActionRequest,
    ) -> PageDetailDTO:
        project_id = _validated_project_id(project_id)
        page_number = _validated_page_number(page_number)
        _execute_action(application, project_id, page_number, action, body)
        return _page_detail(application, project_id, page_number)

    app.get("/health", response_model=HealthDTO)(health)
    app.get("/projects", response_model=list[ProjectSummaryDTO])(list_projects)
    app.post("/projects", response_model=ProjectDetailDTO, status_code=201)(create_project)
    app.get("/projects/{project_id}", response_model=ProjectDetailDTO)(get_project)
    app.post("/projects/{project_id}/run", response_model=ProjectDetailDTO)(run_project)
    app.post("/projects/{project_id}/resume", response_model=ProjectDetailDTO)(resume_project)
    app.get(
        "/projects/{project_id}/chapters/{chapter_id}", response_model=ChapterDetailDTO
    )(get_chapter)
    app.post(
        "/projects/{project_id}/chapters/{chapter_id}/run", response_model=ChapterDetailDTO
    )(run_chapter)
    app.get(
        "/projects/{project_id}/pages/{page_number}", response_model=PageDetailDTO
    )(get_page)
    app.get("/projects/{project_id}/pages/{page_number}/generated-asset")(
        get_generated_asset
    )
    app.get(
        "/projects/{project_id}/pages/{page_number}/approved-asset-download"
    )(get_approved_asset_download)
    app.get(
        "/projects/{project_id}/pages/{page_number}/approved-asset-download/"
        "{invalid_path:path}",
        include_in_schema=False,
    )(reject_invalid_approved_asset_download_path)
    app.post(
        "/projects/{project_id}/pages/{page_number}/visual-review-readiness",
        response_model=VisualReviewReadinessResponse,
    )(assess_visual_review)
    app.post(
        "/projects/{project_id}/pages/{page_number}/visual-review-evidence",
        response_model=VisualReviewEvidenceResponse,
    )(record_visual_review_evidence)
    app.get(
        "/projects/{project_id}/pages/{page_number}/visual-review-evidence",
        response_model=VisualReviewEvidenceHistoryResponse,
    )(read_visual_review_evidence_history)
    app.post(
        "/projects/{project_id}/pages/{page_number}/evidence-linked-approval",
        response_model=PageDetailDTO,
    )(approve_with_evidence)
    app.post(
        "/projects/{project_id}/pages/{page_number}/{action}", response_model=PageDetailDTO
    )(execute_page)


def _evidence_linked_approval_route(
    application: WorkflowApplicationService,
    *,
    request_type: type[Any],
    json_response: Any,
) -> Any:
    def approve_with_evidence(
        project_id: str,
        page_number: str,
        body: EvidenceLinkedApprovalRequest,
        request: Any,
    ) -> Any:
        content_length = _single_request_header(request, "content-length")
        if (
            request.query_params
            or "transfer-encoding" in request.headers
            or not _bounded_content_length(content_length)
            or any(
                name in request.headers
                for name in _VISUAL_REVIEW_HISTORY_REJECTED_HEADERS
            )
            or not _evidence_linked_approval_admission(request)
        ):
            return _visual_review_error(json_response, 422, "invalid_input")
        try:
            project_id = _validated_project_id(project_id)
            raw_page_number = _raw_evidence_linked_approval_page_number(
                request,
                project_id,
                page_number,
            )
            validated_page_number = _validated_download_page_number(raw_page_number)
        except ValidationError:
            return _visual_review_error(json_response, 422, "invalid_input")
        service = evidence_linked_approval_for(application)
        if service is None:
            return _visual_review_error(json_response, 404, "not_found")
        try:
            service.approve(
                project_id,
                validated_page_number,
                approved_by=body.approved_by,
                review_id=body.review_id,
            )
        except EvidenceLinkedApprovalUnavailable:
            return _visual_review_error(json_response, 409, "approval_unavailable")
        detail = _page_detail(application, project_id, validated_page_number)
        return json_response(
            status_code=200,
            content=detail.model_dump(mode="json", by_alias=True),
            headers=_VISUAL_REVIEW_HEADERS,
        )

    approve_with_evidence.__annotations__["request"] = request_type
    return approve_with_evidence


def _visual_review_readiness_route(
    application: WorkflowApplicationService,
    *,
    request_type: type[Any],
    json_response: Any,
) -> Any:
    def assess_visual_review(
        project_id: str,
        page_number: int,
        body: VisualReviewReadinessRequest,
        request: Any,
    ) -> Any:
        content_length = request.headers.get("content-length")
        if (
            request.query_params
            or "transfer-encoding" in request.headers
            or not _bounded_content_length(content_length)
        ):
            return _visual_review_error(json_response, 422, "invalid_input")
        try:
            project_id = _validated_project_id(project_id)
            page_number = _validated_page_number(page_number)
        except ValidationError:
            return _visual_review_error(json_response, 422, "invalid_input")
        service = human_visual_review_readiness_for(application)
        if service is None:
            return _visual_review_error(json_response, 404, "not_found")
        try:
            result = service.assess(
                project_id,
                page_number,
                reviewer_id=body.reviewer_id,
                reviewed_at=body.reviewed_at,
                checklist=tuple(
                    ReviewChecklistDecision(
                        criterion=item.criterion,
                        outcome=item.outcome,
                        rationale=item.rationale,
                    )
                    for item in body.checklist
                ),
                overall_judgment=body.overall_judgment,
                rationale=body.rationale,
            )
        except HumanVisualReviewReadinessUnavailable:
            return _visual_review_error(json_response, 404, "not_found")
        response = VisualReviewReadinessResponse(
            status=result.status,
            ready=result.ready,
            pageState=PageState(result.page_state),
            findings=tuple(
                VisualReviewFindingDTO(
                    code=item.code,
                    status=cast(Literal["needs_review", "blocked"], item.status),
                    message=item.message,
                    criterion=item.criterion,
                )
                for item in result.findings
            ),
            missingPrerequisites=result.missing_prerequisites,
            analysisOnly=True,
        )
        return json_response(
            status_code=200,
            content=response.model_dump(mode="json", by_alias=True),
            headers=_VISUAL_REVIEW_HEADERS,
        )

    assess_visual_review.__annotations__["request"] = request_type
    return assess_visual_review


def _visual_review_evidence_route(
    application: WorkflowApplicationService,
    *,
    request_type: type[Any],
    json_response: Any,
) -> Any:
    def record_visual_review_evidence(
        project_id: str,
        page_number: str,
        body: VisualReviewReadinessRequest,
        request: Any,
    ) -> Any:
        content_length = request.headers.get("content-length")
        if (
            request.query_params
            or "transfer-encoding" in request.headers
            or not _bounded_content_length(content_length)
            or not _visual_review_evidence_admission(request)
        ):
            return _visual_review_error(json_response, 422, "invalid_input")
        try:
            project_id = _validated_project_id(project_id)
            raw_page_number = _raw_visual_review_evidence_page_number(
                request,
                project_id,
                page_number,
            )
            validated_page_number = _validated_download_page_number(raw_page_number)
        except ValidationError:
            return _visual_review_error(json_response, 422, "invalid_input")
        service = human_visual_review_evidence_for(application)
        if service is None:
            return _visual_review_error(json_response, 404, "not_found")
        try:
            result = service.record(
                project_id,
                validated_page_number,
                reviewer_id=body.reviewer_id,
                reviewed_at=body.reviewed_at,
                checklist=tuple(
                    ReviewChecklistDecision(
                        criterion=item.criterion,
                        outcome=item.outcome,
                        rationale=item.rationale,
                    )
                    for item in body.checklist
                ),
                overall_judgment=body.overall_judgment,
                rationale=body.rationale,
            )
        except HumanVisualReviewEvidenceUnavailable:
            return _visual_review_error(json_response, 404, "not_found")
        except HumanVisualReviewEvidencePersistenceUnavailable:
            return _visual_review_persistence_error(json_response)
        response = VisualReviewEvidenceResponse(
            status=result.status,
            ready=result.ready,
            pageState=PageState(result.page_state),
            findings=tuple(
                VisualReviewFindingDTO(
                    code=item.code,
                    status=cast(Literal["needs_review", "blocked"], item.status),
                    message=item.message,
                    criterion=item.criterion,
                )
                for item in result.findings
            ),
            missingPrerequisites=result.missing_prerequisites,
            evidenceRecorded=True,
            idempotentReplay=result.idempotent_replay,
            analysisOnly=True,
        )
        return json_response(
            status_code=200,
            content=response.model_dump(mode="json", by_alias=True),
            headers=_VISUAL_REVIEW_HEADERS,
        )

    record_visual_review_evidence.__annotations__["request"] = request_type
    return record_visual_review_evidence


def _visual_review_evidence_history_route(
    application: WorkflowApplicationService,
    *,
    request_type: type[Any],
    json_response: Any,
) -> Any:
    def read_visual_review_evidence_history(
        project_id: str,
        page_number: str,
        request: Any,
    ) -> Any:
        if not _visual_review_evidence_history_admission(request):
            return _visual_review_error(json_response, 422, "invalid_input")
        try:
            project_id = _validated_project_id(project_id)
            raw_page_number = _raw_visual_review_evidence_page_number(
                request,
                project_id,
                page_number,
            )
            validated_page_number = _validated_download_page_number(raw_page_number)
        except ValidationError:
            return _visual_review_error(json_response, 422, "invalid_input")
        service = human_visual_review_evidence_history_for(application)
        if service is None:
            return _visual_review_error(json_response, 404, "not_found")
        try:
            result = service.get(project_id, validated_page_number)
        except HumanVisualReviewEvidenceHistoryUnavailable:
            return _visual_review_error(json_response, 404, "not_found")
        except HumanVisualReviewEvidenceHistoryPersistenceUnavailable:
            return _visual_review_history_unavailable(json_response)
        response = VisualReviewEvidenceHistoryResponse(
            pageNumber=result.page_number,
            recordCount=len(result.records),
            complete=True,
            readOnly=True,
            analysisOnly=True,
            records=tuple(
                VisualReviewHistoryRecordDTO(
                    reviewId=record.review_id,
                    outputAssetId=record.output_asset_id,
                    reviewerId=record.reviewer_id,
                    reviewedAt=record.reviewed_at,
                    pageState=record.page_state,
                    checklist=tuple(
                        VisualReviewHistoryChecklistItemDTO(
                            criterion=item.criterion,
                            outcome=item.outcome,
                            rationale=item.rationale,
                        )
                        for item in record.checklist
                    ),
                    overallJudgment=record.overall_judgment,
                    rationale=record.rationale,
                    status=record.status,
                    ready=record.ready,
                    findings=tuple(
                        VisualReviewFindingDTO(
                            code=item.code,
                            status=item.status,
                            message=item.message,
                            criterion=item.criterion,
                        )
                        for item in record.findings
                    ),
                    missingPrerequisites=record.missing_prerequisites,
                    analysisOnly=True,
                )
                for record in result.records
            ),
        )
        content = response.model_dump(mode="json", by_alias=True)
        encoded = json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
        if len(encoded) > _VISUAL_REVIEW_HISTORY_MAX_RESPONSE_BYTES:
            return _visual_review_history_unavailable(json_response)
        return json_response(
            status_code=200,
            content=content,
            headers=_VISUAL_REVIEW_HEADERS,
        )

    read_visual_review_evidence_history.__annotations__["request"] = request_type
    return read_visual_review_evidence_history


def _bounded_content_length(value: str | None) -> bool:
    if value is None:
        return False
    try:
        length = int(value)
    except ValueError:
        return False
    return 0 < length <= _VISUAL_REVIEW_MAX_CONTENT_LENGTH


def _safe_visual_review_text(value: str, label: str) -> str:
    lowered = value.lower()
    if (
        value != value.strip()
        or not value
        or any(unicodedata.category(character) == "Cc" for character in value)
        or "/" in value
        or "\\" in value
        or re.match(r"^[A-Za-z]:", value)
        or "://" in value
        or "@" in value
        or any(part in lowered for part in _VISUAL_REVIEW_SECRET_PARTS)
    ):
        raise ValueError(f"{label} must be bounded local text")
    return value


def _visual_review_error(json_response: Any, status_code: int, code: str) -> Any:
    message = "Not found." if status_code == 404 else "Request validation failed."
    return json_response(
        status_code=status_code,
        content={"code": code, "message": message},
        headers=_VISUAL_REVIEW_HEADERS,
    )


def _visual_review_persistence_error(json_response: Any) -> Any:
    return json_response(
        status_code=503,
        content={
            "code": "persistence_unavailable",
            "message": "Persistence unavailable.",
        },
        headers=_VISUAL_REVIEW_HEADERS,
    )


def _visual_review_history_unavailable(json_response: Any) -> Any:
    return json_response(
        status_code=503,
        content={
            "code": "history_unavailable",
            "message": "History unavailable.",
        },
        headers=_VISUAL_REVIEW_HEADERS,
    )


def _generated_asset_route(
    application: WorkflowApplicationService,
    *,
    request_type: type[Any],
    response_type: Any,
    json_response: Any,
    background_task_type: Any,
) -> Any:
    def get_generated_asset(
        project_id: str,
        page_number: int,
        request: Any,
    ) -> Any:
        content_length = request.headers.get("content-length")
        if (
            request.query_params
            or (content_length is not None and content_length != "0")
            or "transfer-encoding" in request.headers
            or any(
                name in request.headers
                for name in ("range", "if-none-match", "if-modified-since")
            )
        ):
            return _generated_asset_error(json_response, 422, "invalid_input")
        try:
            project_id = _validated_project_id(project_id)
            page_number = _validated_page_number(page_number)
        except ValidationError:
            return _generated_asset_error(json_response, 422, "invalid_input")
        presentation = generated_asset_presentation_for(application)
        if presentation is None:
            return _generated_asset_error(json_response, 404, "not_found")
        try:
            result = presentation.get(project_id, page_number)
        except GeneratedAssetPresentationUnavailable:
            return _generated_asset_error(json_response, 404, "not_found")
        return response_type(
            content=result.image_bytes,
            status_code=200,
            media_type="image/png",
            headers=_GENERATED_ASSET_HEADERS,
            background=background_task_type(result.release),
        )

    get_generated_asset.__annotations__["request"] = request_type
    return get_generated_asset


def _generated_asset_error(json_response: Any, status_code: int, code: str) -> Any:
    message = "Not found." if status_code == 404 else "Request validation failed."
    return json_response(
        status_code=status_code,
        content={"code": code, "message": message},
        headers=_GENERATED_ASSET_HEADERS,
    )


def _approved_asset_download_route(
    application: WorkflowApplicationService,
    *,
    request_type: type[Any],
    response_type: Any,
    json_response: Any,
    background_task_type: Any,
) -> Any:
    def get_approved_asset_download(
        project_id: str,
        page_number: str,
        request: Any,
    ) -> Any:
        content_length = request.headers.get("content-length")
        if (
            request.query_params
            or (content_length is not None and content_length != "0")
            or "transfer-encoding" in request.headers
            or any(name in request.headers for name in _APPROVED_ASSET_DOWNLOAD_REJECTED_HEADERS)
            or not _approved_download_browser_admission(request)
        ):
            return _approved_asset_download_error(json_response, 422, "invalid_input")
        try:
            raw_page_number = _raw_download_page_number(request, project_id, page_number)
            project_id = _validated_project_id(project_id)
            validated_page_number = _validated_download_page_number(raw_page_number)
        except ValidationError:
            return _approved_asset_download_error(json_response, 422, "invalid_input")
        service = approved_asset_download_for(application)
        if service is None:
            return _approved_asset_download_error(json_response, 404, "not_found")
        try:
            result = service.get(project_id, validated_page_number)
        except ApprovedAssetDownloadUnavailable:
            return _approved_asset_download_error(json_response, 404, "not_found")
        return response_type(
            content=result.image_bytes,
            status_code=200,
            media_type="image/png",
            headers={
                **_APPROVED_ASSET_DOWNLOAD_HEADERS,
                "Content-Disposition": (
                    f'attachment; filename="page-{validated_page_number}.png"'
                ),
            },
            background=background_task_type(result.release),
        )

    get_approved_asset_download.__annotations__["request"] = request_type
    return get_approved_asset_download


def _invalid_approved_asset_download_path_route(json_response: Any) -> Any:
    def reject_invalid_approved_asset_download_path(
        project_id: str,
        page_number: str,
        invalid_path: str,
    ) -> Any:
        del project_id, page_number, invalid_path
        return _approved_asset_download_error(json_response, 422, "invalid_input")

    return reject_invalid_approved_asset_download_path


def _approved_download_browser_admission(request: Any) -> bool:
    referer = _single_request_header(request, "referer")
    if referer is None or not _allowed_local_referer(referer):
        return False
    return all(
        _single_request_header(request, name) == value
        for name, value in (
            ("sec-fetch-mode", "navigate"),
            ("sec-fetch-dest", "document"),
            ("sec-fetch-user", "?1"),
        )
    )


def _single_request_header(request: Any, name: str) -> str | None:
    encoded_name = name.encode("ascii")
    values = [
        value.decode("latin-1")
        for key, value in request.scope.get("headers", ())
        if key.lower() == encoded_name
    ]
    return values[0] if len(values) == 1 else None


def _visual_review_evidence_admission(request: Any) -> bool:
    content_type = _single_request_header(request, "content-type")
    origin = _single_request_header(request, "origin")
    return bool(
        content_type is not None
        and content_type.split(";", 1)[0].strip().lower() == "application/json"
        and origin is not None
        and _allowed_local_origin(origin)
    )


def _visual_review_evidence_history_admission(request: Any) -> bool:
    if (
        request.query_params
        or "transfer-encoding" in request.headers
        or any(name in request.headers for name in _VISUAL_REVIEW_HISTORY_REJECTED_HEADERS)
    ):
        return False
    content_length = _single_request_header(request, "content-length")
    origin = _single_request_header(request, "origin")
    referer = _single_request_header(request, "referer")
    accept = _single_request_header(request, "accept")
    if content_length not in {None, "0"}:
        return False
    return bool(
        origin is not None
        and _allowed_local_origin(origin)
        and referer is not None
        and _allowed_local_referer(referer)
        and _single_request_header(request, "sec-fetch-mode") == "cors"
        and _single_request_header(request, "sec-fetch-dest") == "empty"
        and accept is not None
        and any(
            item.split(";", 1)[0].strip().lower() == "application/json"
            for item in accept.split(",")
        )
    )


def _evidence_linked_approval_admission(request: Any) -> bool:
    content_type = _single_request_header(request, "content-type")
    accept = _single_request_header(request, "accept")
    origin = _single_request_header(request, "origin")
    referer = _single_request_header(request, "referer")
    if (
        content_type is None
        or content_type.split(";", 1)[0].strip().lower() != "application/json"
        or accept is None
        or not any(
            item.split(";", 1)[0].strip().lower() == "application/json"
            for item in accept.split(",")
        )
        or origin is None
        or not _allowed_local_origin(origin)
        or referer is None
        or not _allowed_local_referer(referer)
        or _referer_origin(referer) != origin
    ):
        return False
    return all(
        _single_request_header(request, name) == value
        for name, value in (
            ("sec-fetch-site", "same-origin"),
            ("sec-fetch-mode", "cors"),
            ("sec-fetch-dest", "empty"),
        )
    )


def _allowed_local_origin(value: str) -> bool:
    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme != "http"
            or parsed.hostname is None
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path
            or parsed.query
            or parsed.fragment
        ):
            return False
        port = parsed.port
    except ValueError:
        return False
    return f"http://{parsed.hostname}:{port}" in LOCAL_WEB_ORIGINS


def _allowed_local_referer(value: str) -> bool:
    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme != "http"
            or parsed.hostname is None
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
        ):
            return False
        port = parsed.port
    except ValueError:
        return False
    return f"http://{parsed.hostname}:{port}" in LOCAL_WEB_ORIGINS


def _referer_origin(value: str) -> str | None:
    try:
        parsed = urlsplit(value)
        if parsed.scheme != "http" or parsed.hostname is None:
            return None
        port = parsed.port
    except ValueError:
        return None
    return f"http://{parsed.hostname}:{port}"


def _raw_download_page_number(
    request: Any,
    project_id: str,
    page_number: str,
) -> str:
    raw_path = request.scope.get("raw_path")
    if not isinstance(raw_path, bytes):
        raise ValidationError("pageNumber is invalid.")
    parts = raw_path.split(b"/")
    try:
        raw_project_id = parts[2].decode("ascii")
        raw_page_number = parts[4].decode("ascii")
    except (IndexError, UnicodeDecodeError) as error:
        raise ValidationError("pageNumber is invalid.") from error
    if (
        len(parts) != 6
        or parts[1] != b"projects"
        or parts[3] != b"pages"
        or parts[5] != b"approved-asset-download"
        or raw_project_id != project_id
        or raw_page_number != page_number
    ):
        raise ValidationError("pageNumber is invalid.")
    return raw_page_number


def _raw_visual_review_evidence_page_number(
    request: Any,
    project_id: str,
    page_number: str,
) -> str:
    raw_path = request.scope.get("raw_path")
    if not isinstance(raw_path, bytes):
        raise ValidationError("pageNumber is invalid.")
    parts = raw_path.split(b"/")
    try:
        raw_project_id = parts[2].decode("ascii")
        raw_page_number = parts[4].decode("ascii")
    except (IndexError, UnicodeDecodeError) as error:
        raise ValidationError("pageNumber is invalid.") from error
    if (
        len(parts) != 6
        or parts[1] != b"projects"
        or parts[3] != b"pages"
        or parts[5] != b"visual-review-evidence"
        or raw_project_id != project_id
        or raw_page_number != page_number
    ):
        raise ValidationError("pageNumber is invalid.")
    return raw_page_number


def _raw_evidence_linked_approval_page_number(
    request: Any,
    project_id: str,
    page_number: str,
) -> str:
    raw_path = request.scope.get("raw_path")
    if not isinstance(raw_path, bytes):
        raise ValidationError("pageNumber is invalid.")
    parts = raw_path.split(b"/")
    try:
        raw_project_id = parts[2].decode("ascii")
        raw_page_number = parts[4].decode("ascii")
    except (IndexError, UnicodeDecodeError) as error:
        raise ValidationError("pageNumber is invalid.") from error
    if (
        len(parts) != 6
        or parts[1] != b"projects"
        or parts[3] != b"pages"
        or parts[5] != b"evidence-linked-approval"
        or raw_project_id != project_id
        or raw_page_number != page_number
    ):
        raise ValidationError("pageNumber is invalid.")
    return raw_page_number


def _approved_asset_download_error(
    json_response: Any,
    status_code: int,
    code: str,
) -> Any:
    message = "Not found." if status_code == 404 else "Request validation failed."
    return json_response(
        status_code=status_code,
        content={"code": code, "message": message},
        headers=_APPROVED_ASSET_DOWNLOAD_HEADERS,
    )


def _execute_action(
    application: WorkflowApplicationService,
    project_id: str,
    page_number: int,
    action: WorkflowAction,
    body: PageActionRequest,
) -> None:
    if action in (WorkflowAction.DIALOGUE, WorkflowAction.CONTINUITY):
        application.execute_support(action.value, project_id, page_number, body.metadata)
        return
    if action is WorkflowAction.APPROVE:
        approved_by = (body.approved_by or "").strip()
        if not approved_by:
            raise ValidationError("approvedBy is required for explicit approval.")
        application.approve_page(project_id, page_number, approved_by, body.metadata)
        return
    application.execute_page(action.value, project_id, page_number, body.metadata)


def _project_detail(
    application: WorkflowApplicationService, project_id: str
) -> ProjectDetailDTO:
    context = cast(ProjectContext, application.get_project_status(project_id))
    project = context.project
    current_state = _current_state(project, context.current_page)
    workflow = _project_workflow(application, context, current_state)
    return ProjectDetailDTO(
        **_project_summary(project, current_state=current_state).model_dump(),
        currentChapter=context.current_chapter,
        currentPage=context.current_page,
        chapters=[_chapter_summary(chapter, project) for chapter in context.chapters],
        workflow=workflow,
    )


def _project_summary(
    project: Project, *, current_state: PageState | None = None
) -> ProjectSummaryDTO:
    state = _current_state(project, None) if current_state is None else current_state
    return ProjectSummaryDTO(
        id=project.id,
        title=project.title,
        currentState=state,
        updatedAt=project.updated_at.isoformat(),
        progress=ProgressDTO(
            completed=sum(page.state is PageState.APPROVED for page in project.pages),
            total=len(project.pages),
        ),
    )


def _project_workflow(
    application: WorkflowApplicationService,
    context: ProjectContext,
    current_state: PageState | None,
) -> WorkflowStatusDTO:
    if context.current_page is not None:
        status = cast(
            WorkflowStatus,
            application.get_page_status(context.project.id, context.current_page),
        )
        return _workflow_status(status, project_actions=["run", "resume"])
    return WorkflowStatusDTO(
        currentState=current_state,
        currentStep=None,
        completedSteps=[],
        availableActions=[],
        history=list(context.history),
    )


def _chapter_summary(chapter: Chapter, project: Project) -> ChapterSummaryDTO:
    pages = [project.page(number) for number in chapter.page_numbers]
    return ChapterSummaryDTO(
        id=chapter.id,
        title=chapter.title,
        pageCount=len(pages),
        approvedPages=sum(page.state is PageState.APPROVED for page in pages),
    )


def _chapter_detail(chapter: Chapter, pages: list[Page]) -> ChapterDetailDTO:
    summary = ChapterSummaryDTO(
        id=chapter.id,
        title=chapter.title,
        pageCount=len(pages),
        approvedPages=sum(page.state is PageState.APPROVED for page in pages),
    )
    return ChapterDetailDTO(
        **summary.model_dump(),
        pages=[_page_summary(page) for page in pages],
    )


def _page_detail(
    application: WorkflowApplicationService, project_id: str, page_number: int
) -> PageDetailDTO:
    project = cast(Project, application.get_project(project_id))
    page = project.page(page_number)
    status = cast(WorkflowStatus, application.get_page_status(project_id, page_number))
    summary = _page_summary(page)
    artifacts = {
        name: value
        for name, value in (
            ("pageDesign", page.page_design),
            ("review", page.review),
            ("storyboard", page.storyboard),
            ("dialogue", page.dialogue),
            ("prompt", page.prompt),
            ("image", page.image),
            ("quality", page.quality),
            ("continuity", page.continuity),
            ("approval", page.approval),
        )
        if value is not None
    }
    return PageDetailDTO(
        **summary.model_dump(),
        workflow=_workflow_status(status),
        input={"projectId": project.id, "pageNumber": page.page_number},
        artifacts=artifacts,
        messages=[],
        errors=[],
        executionTimeMs=None,
        approvalRequired=page.state is PageState.QUALITY_CHECKED,
    )


def _page_summary(page: Page) -> PageSummaryDTO:
    quality_passed: bool | None = None
    if page.quality is not None and isinstance(page.quality.get("passed"), bool):
        quality_passed = cast(bool, page.quality["passed"])
    return PageSummaryDTO(
        pageNumber=page.page_number,
        state=page.state,
        qualityPassed=quality_passed,
        approved=page.state is PageState.APPROVED,
    )


def _workflow_status(
    status: WorkflowStatus, *, project_actions: list[str] | None = None
) -> WorkflowStatusDTO:
    available = project_actions or ([status.executable_step] if status.executable_step else [])
    return WorkflowStatusDTO(
        currentState=status.current_state,
        currentStep=status.current_step,
        completedSteps=list(status.completed_steps),
        availableActions=available,
        history=list(status.workflow_history),
    )


def _current_state(project: Project, current_page: int | None) -> PageState | None:
    if current_page is not None:
        return project.page(current_page).state
    ordered = sorted(project.pages, key=lambda item: item.page_number)
    incomplete = next((page.state for page in ordered if page.state is not PageState.APPROVED), None)
    if incomplete is not None:
        return incomplete
    return PageState.APPROVED if ordered else None


def _validated_project_id(project_id: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", project_id) is None:
        raise ValidationError(
            "Project ID may contain only letters, numbers, hyphens, and underscores."
        )
    return project_id


def _validated_page_number(page_number: int) -> int:
    if page_number < 1:
        raise ValidationError("pageNumber must be at least 1.")
    return page_number


def _validated_download_page_number(page_number: str) -> int:
    if re.fullmatch(r"[1-9][0-9]{0,9}", page_number) is None:
        raise ValidationError("pageNumber is invalid.")
    value = int(page_number)
    if value > 2_147_483_647:
        raise ValidationError("pageNumber is invalid.")
    return value
