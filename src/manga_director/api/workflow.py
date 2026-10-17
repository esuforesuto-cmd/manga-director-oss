"""Local-only FastAPI workflow delivery with presentation-specific DTOs."""

from __future__ import annotations

import logging
import re
from enum import StrEnum
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field

from manga_director._version import __version__
from manga_director.application.generated_asset_presentation import (
    GeneratedAssetPresentationUnavailable,
    generated_asset_presentation_for,
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


class _HttpModel(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)


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
    ) -> Any:
        payload = ApiErrorDTO(code=code, message=message, details=details)
        return json_response(
            status_code=status_code,
            content=payload.model_dump(mode="json", by_alias=True, exclude_none=True),
        )

    async def request_validation_error(_request: Any, error: Any) -> Any:
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
        )

    async def project_not_found(_request: Any, error: ProjectNotFoundError) -> Any:
        return error_response(404, "not_found", str(error))

    async def project_exists(_request: Any, error: ProjectAlreadyExistsError) -> Any:
        return error_response(409, "already_exists", str(error))

    async def invalid_transition(_request: Any, error: StateTransitionError) -> Any:
        return error_response(409, "invalid_transition", str(error))

    async def invalid_domain_input(_request: Any, error: ValidationError) -> Any:
        return error_response(422, "invalid_input", str(error))

    async def http_error(_request: Any, error: Any) -> Any:
        code, message = _http_error_content(error.status_code)
        return error_response(error.status_code, code, message)

    async def unexpected_error(_request: Any, error: Exception) -> Any:
        LOGGER.error(
            "Unhandled workflow HTTP error",
            exc_info=(type(error), error, error.__traceback__),
        )
        return error_response(500, "internal_error", "An internal error occurred.")

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
    app.post(
        "/projects/{project_id}/pages/{page_number}/{action}", response_model=PageDetailDTO
    )(execute_page)


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
