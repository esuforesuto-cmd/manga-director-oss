"""v3.2 read-only foundations for Studio, Assets, Profiles, and Analytics.

This module intentionally projects existing Project and one-page Workflow
contexts into immutable Application DTOs.  It has no authority to save,
transition, dispatch, approve, or generate.  The StateMachine remains the
sole source of truth for the *suggested* next workflow command.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, cast

from pydantic import Field

from manga_director.domain.project import Project
from manga_director.domain.state_machine import PageState, StateMachine
from manga_director.production.director import DirectorModel
from manga_director.repositories.protocols import ProjectRepository
from manga_director.workflow.contracts import WorkflowContext


class StudioWorkspaceDTO(DirectorModel):
    workspace_id: str
    project_id: str
    page_reference: str
    mode: Literal["creative_studio"] = "creative_studio"
    persisted: bool = False
    workflow_execution_enabled: bool = False


class CreativeSessionDTO(DirectorModel):
    session_id: str
    workspace: StudioWorkspaceDTO
    current_state: PageState
    objective: str
    active: bool = False
    agent_execution_enabled: bool = False


class WorkspaceLayoutDTO(DirectorModel):
    sections: tuple[str, ...] = ("project", "story", "page", "review")
    layout_applied: bool = False


class ProjectDashboardDTO(DirectorModel):
    project_id: str
    project_title: str
    chapter_count: int = Field(ge=0)
    page_count: int = Field(ge=0)
    selected_page_reference: str
    workflow_execution_started: bool = False


class CreativeActivityDTO(DirectorModel):
    labels: tuple[str, ...] = ()
    activity_count: int = Field(ge=0)
    persistence_mutated: bool = False
    approval_granted: bool = False


class StudioSummary(DirectorModel):
    workspace_count: int = Field(ge=0)
    current_state: PageState
    next_command: str | None = None
    advisory_only: bool = True
    automatic_action_taken: bool = False


class WorkspaceReport(DirectorModel):
    workspace: StudioWorkspaceDTO
    session: CreativeSessionDTO
    layout: WorkspaceLayoutDTO
    dashboard: ProjectDashboardDTO
    activity: CreativeActivityDTO
    summary: StudioSummary
    workflow_modified: bool = False


class AssetCategoryDTO(DirectorModel):
    name: Literal["storyboard", "prompt", "image", "quality", "reference"]
    display_name: str


class AssetMetadataDTO(DirectorModel):
    metadata_keys: tuple[str, ...] = ()
    values_redacted: bool = True
    source: Literal["repository_projection", "workflow_projection"]


class AssetDTO(DirectorModel):
    asset_id: str
    category: AssetCategoryDTO
    page_reference: str | None = None
    metadata: AssetMetadataDTO
    persisted: bool = False


class AssetRelationshipDTO(DirectorModel):
    source_asset_id: str
    target_reference: str
    relation: Literal["belongs_to_page", "derived_from_workflow"]
    relationship_created: bool = False


class AssetIndex(DirectorModel):
    assets: tuple[AssetDTO, ...] = ()
    relationships: tuple[AssetRelationshipDTO, ...] = ()
    repository_read_only: bool = True


class AssetSummary(DirectorModel):
    asset_count: int = Field(ge=0)
    category_count: int = Field(ge=0)
    values_redacted: bool = True
    index_persisted: bool = False


class AssetIntelligenceReport(DirectorModel):
    index: AssetIndex
    summary: AssetSummary
    external_lookup_started: bool = False
    persistence_mutated: bool = False


class StageProfileDTO(DirectorModel):
    state: PageState
    command: str | None = None
    current: bool = False
    execution_started: bool = False


class PipelineProfileDTO(DirectorModel):
    name: str = "page_workflow"
    stages: tuple[StageProfileDTO, ...] = ()
    transition_validated: bool = False
    pipeline_changed: bool = False


class ExecutionProfileDTO(DirectorModel):
    current_state: PageState
    suggested_command: str | None = None
    one_page_scope: bool = True
    execution_enabled: bool = False


class WorkflowProfileDTO(DirectorModel):
    profile_id: str
    pipeline: PipelineProfileDTO
    execution: ExecutionProfileDTO
    workflow_modified: bool = False


class WorkflowProfileReport(DirectorModel):
    profile: WorkflowProfileDTO
    messages: tuple[str, ...] = ()
    analysis_only: bool = True


class PipelineSummary(DirectorModel):
    stage_count: int = Field(ge=0)
    current_state: PageState
    next_command: str | None = None
    automatic_transition: bool = False


class ProjectAnalyticsDTO(DirectorModel):
    project_count: int = Field(ge=0)
    chapter_count: int = Field(ge=0)
    page_count: int = Field(ge=0)
    aggregation_only: bool = True


class WorkflowAnalyticsDTO(DirectorModel):
    current_state: PageState
    history_entries: int = Field(ge=0)
    artifact_count: int = Field(ge=0)
    workflow_executed: bool = False


class ReviewAnalyticsDTO(DirectorModel):
    review_evidence_present: bool
    quality_evidence_present: bool
    approval_granted: bool = False
    review_executed: bool = False


class QualityAnalyticsDTO(DirectorModel):
    quality_evidence_present: bool
    approved_state: bool
    quality_score_computed: bool = False
    approval_authorized: bool = False


class AnalyticsSummary(DirectorModel):
    report_count: int = Field(ge=0)
    recommendations: tuple[str, ...] = ()
    runtime_automation_started: bool = False


class ProductionAnalyticsReport(DirectorModel):
    project: ProjectAnalyticsDTO
    workflow: WorkflowAnalyticsDTO
    review: ReviewAnalyticsDTO
    quality: QualityAnalyticsDTO
    summary: AnalyticsSummary
    analysis_only: bool = True


class CreativeStudioDashboardDTO(DirectorModel):
    report: WorkspaceReport
    automatic_action_taken: bool = False


class AssetIntelligenceDashboardDTO(DirectorModel):
    report: AssetIntelligenceReport
    automatic_action_taken: bool = False


class WorkflowProfileDashboardDTO(DirectorModel):
    report: WorkflowProfileReport
    summary: PipelineSummary
    automatic_action_taken: bool = False


class ProductionAnalyticsDashboardDTO(DirectorModel):
    report: ProductionAnalyticsReport
    automatic_action_taken: bool = False


class V32FoundationService:
    """Build v3.2 DTO projections without changing any Core workflow behaviour."""

    def __init__(self, repository: ProjectRepository) -> None:
        self._repository = repository

    def creative_studio(self, project_id: str, context: WorkflowContext) -> WorkspaceReport:
        project = self._repository.load(project_id)
        page_reference = _page_reference(context)
        workspace = StudioWorkspaceDTO(
            workspace_id=f"studio:{project.id}:{page_reference}",
            project_id=project.id,
            page_reference=page_reference,
        )
        activity_labels = _history_labels(context)
        suggested = _next_command(context.state)
        return WorkspaceReport(
            workspace=workspace,
            session=CreativeSessionDTO(
                session_id=f"session:{project.id}:{page_reference}:{context.state.value}",
                workspace=workspace,
                current_state=context.state,
                objective="Plan and inspect one existing Page without executing it.",
            ),
            layout=WorkspaceLayoutDTO(),
            dashboard=_dashboard(project, page_reference),
            activity=CreativeActivityDTO(
                labels=activity_labels, activity_count=len(activity_labels)
            ),
            summary=StudioSummary(
                workspace_count=1,
                current_state=context.state,
                next_command=suggested,
            ),
        )

    def asset_intelligence(
        self, project_id: str, context: WorkflowContext
    ) -> AssetIntelligenceReport:
        project = self._repository.load(project_id)
        page_reference = _page_reference(context)
        assets = tuple(
            _asset(project, context, page_reference, key) for key in _asset_keys(project, context)
        )
        relationships = tuple(
            AssetRelationshipDTO(
                source_asset_id=asset.asset_id,
                target_reference=page_reference,
                relation="belongs_to_page" if asset.page_reference else "derived_from_workflow",
            )
            for asset in assets
        )
        return AssetIntelligenceReport(
            index=AssetIndex(assets=assets, relationships=relationships),
            summary=AssetSummary(
                asset_count=len(assets),
                category_count=len({asset.category.name for asset in assets}),
            ),
        )

    def workflow_profiles(
        self, context: WorkflowContext
    ) -> tuple[WorkflowProfileReport, PipelineSummary]:
        next_command = _next_command(context.state)
        stages = tuple(
            StageProfileDTO(
                state=state,
                command=_command_for_state(state),
                current=state is context.state,
            )
            for state in PageState
        )
        profile = WorkflowProfileDTO(
            profile_id=f"page-workflow:{context.state.value}",
            pipeline=PipelineProfileDTO(stages=stages),
            execution=ExecutionProfileDTO(
                current_state=context.state, suggested_command=next_command
            ),
        )
        return (
            WorkflowProfileReport(
                profile=profile,
                messages=(
                    "Profiles describe the existing StateMachine; they never transition it.",
                ),
            ),
            PipelineSummary(
                stage_count=len(stages), current_state=context.state, next_command=next_command
            ),
        )

    def production_analytics(self, context: WorkflowContext) -> ProductionAnalyticsReport:
        projects = tuple(self._repository.list())
        history = context.metadata.get("workflow_history", ())
        history_count = len(history) if isinstance(history, list | tuple) else 0
        quality = _mapping(context.artifacts.get("quality", context.page.get("quality")))
        review = _mapping(context.artifacts.get("review", context.page.get("review")))
        return ProductionAnalyticsReport(
            project=ProjectAnalyticsDTO(
                project_count=len(projects),
                chapter_count=sum(len(project.chapters) for project in projects),
                page_count=sum(len(project.pages) for project in projects),
            ),
            workflow=WorkflowAnalyticsDTO(
                current_state=context.state,
                history_entries=history_count,
                artifact_count=len(context.artifacts),
            ),
            review=ReviewAnalyticsDTO(
                review_evidence_present=bool(review) or context.state is not PageState.DRAFT,
                quality_evidence_present=bool(quality)
                or context.state in {PageState.QUALITY_CHECKED, PageState.APPROVED},
            ),
            quality=QualityAnalyticsDTO(
                quality_evidence_present=bool(quality)
                or context.state in {PageState.QUALITY_CHECKED, PageState.APPROVED},
                approved_state=context.state is PageState.APPROVED,
            ),
            summary=AnalyticsSummary(
                report_count=4,
                recommendations=(
                    "Use the current StateMachine command only after required evidence exists.",
                ),
            ),
        )

    def creative_studio_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> CreativeStudioDashboardDTO:
        return CreativeStudioDashboardDTO(report=self.creative_studio(project_id, context))

    def asset_intelligence_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> AssetIntelligenceDashboardDTO:
        return AssetIntelligenceDashboardDTO(report=self.asset_intelligence(project_id, context))

    def workflow_profile_dashboard(self, context: WorkflowContext) -> WorkflowProfileDashboardDTO:
        report, summary = self.workflow_profiles(context)
        return WorkflowProfileDashboardDTO(report=report, summary=summary)

    def production_analytics_dashboard(
        self, context: WorkflowContext
    ) -> ProductionAnalyticsDashboardDTO:
        return ProductionAnalyticsDashboardDTO(report=self.production_analytics(context))


def _dashboard(project: Project, page_reference: str) -> ProjectDashboardDTO:
    return ProjectDashboardDTO(
        project_id=project.id,
        project_title=project.title,
        chapter_count=len(project.chapters),
        page_count=len(project.pages),
        selected_page_reference=page_reference,
    )


def _asset_keys(project: Project, context: WorkflowContext) -> tuple[str, ...]:
    known = (*project.metadata.keys(), *context.artifacts.keys())
    allowed = {"storyboard", "prompt", "image", "quality", "reference"}
    return tuple(sorted({str(key) for key in known if str(key).lower() in allowed}))


def _asset(project: Project, context: WorkflowContext, page_reference: str, key: str) -> AssetDTO:
    category_name: Literal["storyboard", "prompt", "image", "quality", "reference"] = (
        cast(Literal["storyboard", "prompt", "image", "quality"], key.lower())
        if key.lower() in {"storyboard", "prompt", "image", "quality"}
        else "reference"
    )
    source: Literal["repository_projection", "workflow_projection"] = (
        "workflow_projection" if key in context.artifacts else "repository_projection"
    )
    metadata = (
        context.artifacts.get(key) if source == "workflow_projection" else project.metadata.get(key)
    )
    return AssetDTO(
        asset_id=f"asset:{project.id}:{page_reference}:{category_name}",
        category=AssetCategoryDTO(
            name=category_name, display_name=category_name.replace("_", " ").title()
        ),
        page_reference=page_reference,
        metadata=AssetMetadataDTO(
            metadata_keys=tuple(sorted(str(item) for item in _mapping(metadata))), source=source
        ),
    )


def _history_labels(context: WorkflowContext) -> tuple[str, ...]:
    history = context.metadata.get("workflow_history", ())
    if not isinstance(history, list | tuple):
        return ()
    return tuple(
        str(entry.get("step", entry.get("to", "workflow")))
        for entry in history
        if isinstance(entry, Mapping)
    )


def _page_reference(context: WorkflowContext) -> str:
    return str(context.page.get("id", context.page.get("page_number", "page")))


def _next_command(state: PageState) -> str | None:
    try:
        return StateMachine().next_command(state)
    except Exception:
        return None


def _command_for_state(state: PageState) -> str | None:
    return _next_command(state)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
