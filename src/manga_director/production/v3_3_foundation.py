"""v3.3 read-only foundations for pipeline, quality, assets, and projects.

The services in this module project existing Repository and one-page workflow
evidence into immutable DTOs. They do not save, transition, dispatch, generate,
approve, archive, publish, schedule, or allocate resources. The StateMachine
remains the sole authority for legal workflow transitions.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from pydantic import Field

from manga_director.domain.project import Project
from manga_director.domain.state_machine import PageState, StateMachine
from manga_director.production.director import DirectorModel
from manga_director.repositories.protocols import ProjectRepository
from manga_director.workflow.contracts import WorkflowContext


class PipelineStageDTO(DirectorModel):
    state: PageState
    command: str | None = None
    current: bool = False
    execution_started: bool = False


class PipelineTransitionDTO(DirectorModel):
    from_state: PageState
    suggested_command: str | None = None
    transition_applied: bool = False


class ApprovalStageDTO(DirectorModel):
    quality_review_completed: bool = False
    human_approval_required: bool = True
    approval_granted: bool = False


class ProductionSessionDTO(DirectorModel):
    session_id: str
    project_id: str
    page_reference: str
    current_state: PageState
    active: bool = False
    workflow_execution_enabled: bool = False


class PipelineTimelineDTO(DirectorModel):
    labels: tuple[str, ...] = ()
    observed_stage_count: int = Field(ge=0)
    timeline_persisted: bool = False


class PipelineSummary(DirectorModel):
    stage_count: int = Field(ge=0)
    current_state: PageState
    next_command: str | None = None
    automatic_action_taken: bool = False


class ProductionPipelineReport(DirectorModel):
    session: ProductionSessionDTO
    stages: tuple[PipelineStageDTO, ...]
    transition: PipelineTransitionDTO
    approval: ApprovalStageDTO
    timeline: PipelineTimelineDTO
    summary: PipelineSummary
    analysis_only: bool = True


class QualityMetricDTO(DirectorModel):
    name: Literal["artifact_count", "history_count", "quality_evidence"]
    observed_value: int = Field(ge=0)
    score_computed: bool = False


class QualityRuleDTO(DirectorModel):
    rule_id: Literal["quality_before_approval", "storyboard_before_generation"]
    observed: bool
    enforced_by_report: bool = False


class QualityFindingDTO(DirectorModel):
    finding_id: str
    category: Literal["quality", "workflow"]
    message: str
    remediation_applied: bool = False


class QualityDashboardDTO(DirectorModel):
    metrics: tuple[QualityMetricDTO, ...] = ()
    findings: tuple[QualityFindingDTO, ...] = ()
    quality_review_completed: bool = False
    approval_granted: bool = False
    automatic_action_taken: bool = False


class QualitySummary(DirectorModel):
    metric_count: int = Field(ge=0)
    finding_count: int = Field(ge=0)
    advisory_only: bool = True


class QualityIntelligenceReport(DirectorModel):
    dashboard: QualityDashboardDTO
    rules: tuple[QualityRuleDTO, ...] = ()
    summary: QualitySummary
    analysis_only: bool = True


class AssetLifecycleDTO(DirectorModel):
    asset_id: str
    lifecycle_state: Literal["observed", "quality_evidence", "storyboard_evidence"]
    persisted: bool = False
    lifecycle_managed: bool = False


class AssetVersionDTO(DirectorModel):
    asset_id: str
    version_label: str = "observed"
    version_created: bool = False


class AssetHistoryDTO(DirectorModel):
    asset_id: str
    event_labels: tuple[str, ...] = ()
    history_loaded_selectively: bool = True


class AssetArchiveDTO(DirectorModel):
    asset_id: str
    archive_eligible: bool = False
    archive_performed: bool = False


class AssetDependencyDTO(DirectorModel):
    asset_id: str
    target_reference: str
    relation: Literal["belongs_to_page", "derived_from_workflow"]
    dependency_persisted: bool = False


class LifecycleSummary(DirectorModel):
    asset_count: int = Field(ge=0)
    dependency_count: int = Field(ge=0)
    repository_read_only: bool = True
    automatic_action_taken: bool = False


class AssetLifecycleReport(DirectorModel):
    assets: tuple[AssetLifecycleDTO, ...] = ()
    versions: tuple[AssetVersionDTO, ...] = ()
    history: tuple[AssetHistoryDTO, ...] = ()
    archive: tuple[AssetArchiveDTO, ...] = ()
    dependencies: tuple[AssetDependencyDTO, ...] = ()
    summary: LifecycleSummary
    analysis_only: bool = True


class ProjectHealthDTO(DirectorModel):
    project_id: str
    chapter_count: int = Field(ge=0)
    page_count: int = Field(ge=0)
    observed_state: PageState
    health_computed: bool = False


class MilestoneDTO(DirectorModel):
    milestone_id: str
    label: str
    reached: bool = False
    milestone_updated: bool = False


class ResourceSummaryDTO(DirectorModel):
    declared_resource_count: int = Field(ge=0)
    resource_allocated: bool = False


class ScheduleAnalysisDTO(DirectorModel):
    known_schedule_entries: int = Field(ge=0)
    schedule_modified: bool = False
    delivery_commitment_created: bool = False


class RiskSummaryDTO(DirectorModel):
    risk_count: int = Field(ge=0)
    risks: tuple[str, ...] = ()
    remediation_applied: bool = False


class ProjectExecutiveSummary(DirectorModel):
    project_id: str
    current_state: PageState
    recommendations: tuple[str, ...] = ()
    automatic_action_taken: bool = False


class ProjectIntelligenceReport(DirectorModel):
    health: ProjectHealthDTO
    milestones: tuple[MilestoneDTO, ...] = ()
    resources: ResourceSummaryDTO
    schedule: ScheduleAnalysisDTO
    risks: RiskSummaryDTO
    executive: ProjectExecutiveSummary
    analysis_only: bool = True


class ProductionPipelineDashboardDTO(DirectorModel):
    report: ProductionPipelineReport
    automatic_action_taken: bool = False


class QualityIntelligenceDashboardDTO(DirectorModel):
    report: QualityIntelligenceReport
    automatic_action_taken: bool = False


class AssetLifecycleDashboardDTO(DirectorModel):
    report: AssetLifecycleReport
    automatic_action_taken: bool = False


class ProjectIntelligenceDashboardDTO(DirectorModel):
    report: ProjectIntelligenceReport
    automatic_action_taken: bool = False


class V33FoundationService:
    """Build v3.3 DTO projections without changing Core workflow behaviour."""

    def __init__(self, repository: ProjectRepository) -> None:
        self._repository = repository

    def production_pipeline(
        self, project_id: str, context: WorkflowContext
    ) -> ProductionPipelineReport:
        project = self._repository.load(project_id)
        page_reference = _page_reference(context)
        next_command = _next_command(context.state)
        history = _history_labels(context)
        quality_completed = context.state in {PageState.QUALITY_CHECKED, PageState.APPROVED}
        return ProductionPipelineReport(
            session=ProductionSessionDTO(
                session_id=f"pipeline:{project.id}:{page_reference}:{context.state.value}",
                project_id=project.id,
                page_reference=page_reference,
                current_state=context.state,
            ),
            stages=tuple(
                PipelineStageDTO(
                    state=state,
                    command=_next_command(state),
                    current=state is context.state,
                )
                for state in PageState
            ),
            transition=PipelineTransitionDTO(
                from_state=context.state, suggested_command=next_command
            ),
            approval=ApprovalStageDTO(
                quality_review_completed=quality_completed,
                approval_granted=context.state is PageState.APPROVED,
            ),
            timeline=PipelineTimelineDTO(labels=history, observed_stage_count=len(history)),
            summary=PipelineSummary(
                stage_count=len(PageState), current_state=context.state, next_command=next_command
            ),
        )

    def quality_intelligence(self, context: WorkflowContext) -> QualityIntelligenceReport:
        history = _history_labels(context)
        quality_completed = context.state in {PageState.QUALITY_CHECKED, PageState.APPROVED}
        storyboard_present = bool(context.artifacts.get("storyboard") or context.page.get("storyboard"))
        metrics = (
            QualityMetricDTO(name="artifact_count", observed_value=len(context.artifacts)),
            QualityMetricDTO(name="history_count", observed_value=len(history)),
            QualityMetricDTO(name="quality_evidence", observed_value=int(quality_completed)),
        )
        findings = () if quality_completed else (
            QualityFindingDTO(
                finding_id="quality-review-pending",
                category="quality",
                message="Quality review remains an explicit prerequisite for approval.",
            ),
        )
        return QualityIntelligenceReport(
            dashboard=QualityDashboardDTO(
                metrics=metrics,
                findings=findings,
                quality_review_completed=quality_completed,
                approval_granted=context.state is PageState.APPROVED,
            ),
            rules=(
                QualityRuleDTO(
                    rule_id="quality_before_approval", observed=quality_completed
                ),
                QualityRuleDTO(
                    rule_id="storyboard_before_generation", observed=storyboard_present
                ),
            ),
            summary=QualitySummary(metric_count=len(metrics), finding_count=len(findings)),
        )

    def asset_lifecycle(self, project_id: str, context: WorkflowContext) -> AssetLifecycleReport:
        project = self._repository.load(project_id)
        page_reference = _page_reference(context)
        history = _history_labels(context)
        keys = _asset_keys(project, context)
        assets = tuple(
            AssetLifecycleDTO(
                asset_id=f"asset:{project.id}:{page_reference}:{key}",
                lifecycle_state=(
                    "quality_evidence"
                    if key == "quality"
                    else "storyboard_evidence"
                    if key == "storyboard"
                    else "observed"
                ),
            )
            for key in keys
        )
        versions = tuple(AssetVersionDTO(asset_id=asset.asset_id) for asset in assets)
        asset_history = tuple(
            AssetHistoryDTO(asset_id=asset.asset_id, event_labels=history) for asset in assets
        )
        archive = tuple(AssetArchiveDTO(asset_id=asset.asset_id) for asset in assets)
        dependencies = tuple(
            AssetDependencyDTO(
                asset_id=asset.asset_id,
                target_reference=page_reference,
                relation="belongs_to_page",
            )
            for asset in assets
        )
        return AssetLifecycleReport(
            assets=assets,
            versions=versions,
            history=asset_history,
            archive=archive,
            dependencies=dependencies,
            summary=LifecycleSummary(asset_count=len(assets), dependency_count=len(dependencies)),
        )

    def project_intelligence(
        self, project_id: str, context: WorkflowContext
    ) -> ProjectIntelligenceReport:
        project = self._repository.load(project_id)
        page_reference = _page_reference(context)
        history = _history_labels(context)
        risks: tuple[str, ...] = () if history else ("No observed workflow history for this Page.",)
        return ProjectIntelligenceReport(
            health=ProjectHealthDTO(
                project_id=project.id,
                chapter_count=len(project.chapters),
                page_count=len(project.pages),
                observed_state=context.state,
            ),
            milestones=(
                MilestoneDTO(
                    milestone_id=f"page:{page_reference}",
                    label="Current Page evidence",
                    reached=context.state is PageState.APPROVED,
                ),
            ),
            resources=ResourceSummaryDTO(declared_resource_count=len(project.metadata)),
            schedule=ScheduleAnalysisDTO(known_schedule_entries=len(history)),
            risks=RiskSummaryDTO(risk_count=len(risks), risks=risks),
            executive=ProjectExecutiveSummary(
                project_id=project.id,
                current_state=context.state,
                recommendations=(
                    "Use the current StateMachine command only after required evidence exists.",
                ),
            ),
        )

    def production_pipeline_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> ProductionPipelineDashboardDTO:
        return ProductionPipelineDashboardDTO(report=self.production_pipeline(project_id, context))

    def quality_intelligence_dashboard(
        self, context: WorkflowContext
    ) -> QualityIntelligenceDashboardDTO:
        return QualityIntelligenceDashboardDTO(report=self.quality_intelligence(context))

    def asset_lifecycle_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> AssetLifecycleDashboardDTO:
        return AssetLifecycleDashboardDTO(report=self.asset_lifecycle(project_id, context))

    def project_intelligence_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> ProjectIntelligenceDashboardDTO:
        return ProjectIntelligenceDashboardDTO(report=self.project_intelligence(project_id, context))


def _page_reference(context: WorkflowContext) -> str:
    return str(context.page.get("id", context.page.get("page_number", "page")))


def _next_command(state: PageState) -> str | None:
    try:
        return StateMachine().next_command(state)
    except Exception:
        return None


def _history_labels(context: WorkflowContext) -> tuple[str, ...]:
    history = context.metadata.get("workflow_history", ())
    if not isinstance(history, list | tuple):
        return ()
    return tuple(
        str(entry.get("step", entry.get("to", "workflow")))
        for entry in history
        if isinstance(entry, Mapping)
    )


def _asset_keys(project: Project, context: WorkflowContext) -> tuple[str, ...]:
    allowed = {"storyboard", "prompt", "image", "quality", "reference"}
    keys = (*project.metadata.keys(), *context.artifacts.keys())
    return tuple(sorted({str(key).lower() for key in keys if str(key).lower() in allowed}))
