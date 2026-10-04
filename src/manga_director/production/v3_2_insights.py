"""v3.2 analysis-only Workspace, Asset, Workflow, and Production insights.

The service composes immutable Application DTOs from the existing Repository
port and one Page ``WorkflowContext``.  It never schedules, transitions,
persists, approves, generates, or invokes an Agent or Provider.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from pydantic import Field

from manga_director.domain.state_machine import PageState, StateMachine
from manga_director.production.director import DirectorModel
from manga_director.production.v3_2_foundation import V32FoundationService
from manga_director.repositories.protocols import ProjectRepository
from manga_director.workflow.contracts import WorkflowContext


class WorkspaceSessionDTO(DirectorModel):
    session_id: str
    page_reference: str
    current_state: PageState
    review_only: bool = True
    workflow_execution_enabled: bool = False


class WorkspaceTimelineEntryDTO(DirectorModel):
    label: str
    state: PageState
    source: Literal["workflow_history", "workspace_projection"]
    event_dispatched: bool = False


class WorkspaceTimelineDTO(DirectorModel):
    entries: tuple[WorkspaceTimelineEntryDTO, ...] = ()
    timeline_persisted: bool = False


class CreativeTaskDTO(DirectorModel):
    task_id: str
    label: str
    status: Literal["observed", "human_review_required", "complete"] = "observed"
    assigned: bool = False
    automatically_started: bool = False


class WorkspaceActivityTimeline(DirectorModel):
    activities: tuple[str, ...] = ()
    activity_count: int = Field(ge=0)
    repository_mutated: bool = False


class CreativeProgressReport(DirectorModel):
    current_state: PageState
    completed_stage_count: int = Field(ge=0)
    total_stage_count: int = Field(ge=0)
    next_command: str | None = None
    workflow_advanced: bool = False


class WorkspaceInsightReport(DirectorModel):
    session: WorkspaceSessionDTO
    timeline: WorkspaceTimelineDTO
    tasks: tuple[CreativeTaskDTO, ...] = ()
    activity: WorkspaceActivityTimeline
    progress: CreativeProgressReport
    messages: tuple[str, ...] = ()
    analysis_only: bool = True


class AssetUsageMetrics(DirectorModel):
    asset_count: int = Field(ge=0)
    referenced_page_count: int = Field(ge=0)
    usage_collected_remotely: bool = False


class AssetDependencyMetrics(DirectorModel):
    relationship_count: int = Field(ge=0)
    dependency_count: int = Field(ge=0)
    dependency_resolved: bool = False


class AssetQualityMetrics(DirectorModel):
    assets_with_metadata: int = Field(ge=0)
    quality_evidence_present: bool
    quality_scored: bool = False


class AssetRelationshipAnalysis(DirectorModel):
    relationship_count: int = Field(ge=0)
    relationship_types: tuple[str, ...] = ()
    graph_persisted: bool = False


class AssetAnalyticsReport(DirectorModel):
    usage: AssetUsageMetrics
    dependencies: AssetDependencyMetrics
    quality: AssetQualityMetrics
    relationships: AssetRelationshipAnalysis
    values_redacted: bool = True
    repository_mutated: bool = False


class AssetIntelligenceSummary(DirectorModel):
    asset_count: int = Field(ge=0)
    insight_count: int = Field(ge=0)
    recommendation: str
    automatic_action_taken: bool = False


class WorkflowEfficiencyAnalysis(DirectorModel):
    completed_stage_count: int = Field(ge=0)
    remaining_stage_count: int = Field(ge=0)
    artifact_count: int = Field(ge=0)
    execution_measured: bool = False


class PipelineBottleneckReport(DirectorModel):
    current_state: PageState
    bottleneck: str | None = None
    requires_human_review: bool = False
    remediation_applied: bool = False


class V32WorkflowRecommendation(DirectorModel):
    message: str
    next_command: str | None = None
    workflow_changed: bool = False


class ExecutionTimelineAnalysis(DirectorModel):
    observed_event_count: int = Field(ge=0)
    stages: tuple[str, ...] = ()
    execution_replayed: bool = False


class V32WorkflowHealthReport(DirectorModel):
    status: Literal["healthy", "attention"]
    checks: tuple[str, ...] = ()
    health_check_changed_workflow: bool = False


class WorkflowIntelligenceSummary(DirectorModel):
    current_state: PageState
    next_command: str | None = None
    diagnostics_only: bool = True
    automatic_transition: bool = False


class WorkflowIntelligenceInsightReport(DirectorModel):
    efficiency: WorkflowEfficiencyAnalysis
    bottleneck: PipelineBottleneckReport
    recommendation: V32WorkflowRecommendation
    timeline: ExecutionTimelineAnalysis
    health: V32WorkflowHealthReport
    summary: WorkflowIntelligenceSummary
    analysis_only: bool = True


class ProductionInsightDTO(DirectorModel):
    category: Literal["quality", "review", "productivity", "forecast"]
    message: str
    action_applied: bool = False


class QualityTrendAnalysis(DirectorModel):
    quality_evidence_present: bool
    observed_state: PageState
    trend: Literal["insufficient_evidence", "evidence_present"]
    quality_scored: bool = False


class ReviewEfficiencyReport(DirectorModel):
    review_evidence_present: bool
    history_entries: int = Field(ge=0)
    review_executed: bool = False


class ProductivityInsight(DirectorModel):
    project_count: int = Field(ge=0)
    page_count: int = Field(ge=0)
    one_page_scope: bool = True
    workflow_started: bool = False


class ProductionForecastReport(DirectorModel):
    forecast: Literal["not_computed"] = "not_computed"
    basis: tuple[str, ...] = ()
    automation_started: bool = False


class AnalyticsExecutiveSummary(DirectorModel):
    insights: tuple[ProductionInsightDTO, ...] = ()
    human_review_required: bool = True
    release_authorized: bool = False


class ProductionInsightsReport(DirectorModel):
    quality: QualityTrendAnalysis
    review: ReviewEfficiencyReport
    productivity: ProductivityInsight
    forecast: ProductionForecastReport
    executive: AnalyticsExecutiveSummary
    analysis_only: bool = True


class CreativeWorkspaceDashboardDTO(DirectorModel):
    report: WorkspaceInsightReport
    automatic_action_taken: bool = False


class AssetAnalyticsDashboardDTO(DirectorModel):
    report: AssetAnalyticsReport
    summary: AssetIntelligenceSummary
    automatic_action_taken: bool = False


class WorkflowIntelligenceDashboardDTO(DirectorModel):
    report: WorkflowIntelligenceInsightReport
    automatic_action_taken: bool = False


class ProductionInsightsDashboardDTO(DirectorModel):
    report: ProductionInsightsReport
    automatic_action_taken: bool = False


class V32InsightsService:
    """Compose v3.2 analysis DTOs without workflow or repository authority."""

    def __init__(self, foundation: V32FoundationService, repository: ProjectRepository) -> None:
        self._foundation = foundation
        self._repository = repository

    def creative_workspace(
        self, project_id: str, context: WorkflowContext
    ) -> WorkspaceInsightReport:
        studio = self._foundation.creative_studio(project_id, context)
        timeline = _workspace_timeline(context)
        tasks = tuple(
            CreativeTaskDTO(
                task_id=f"task:{index}:{entry.label}",
                label=entry.label,
                status="human_review_required"
                if entry.state is PageState.QUALITY_CHECKED
                else "observed",
            )
            for index, entry in enumerate(timeline.entries, start=1)
        )
        return WorkspaceInsightReport(
            session=WorkspaceSessionDTO(
                session_id=f"workspace:{studio.session.session_id}",
                page_reference=studio.workspace.page_reference,
                current_state=context.state,
            ),
            timeline=timeline,
            tasks=tasks,
            activity=WorkspaceActivityTimeline(
                activities=tuple(task.label for task in tasks), activity_count=len(tasks)
            ),
            progress=CreativeProgressReport(
                current_state=context.state,
                completed_stage_count=_completed_stages(context.state),
                total_stage_count=len(PageState),
                next_command=_next_command(context.state),
            ),
            messages=("Workspace insights are advisory; human review remains required.",),
        )

    def asset_analytics(
        self, project_id: str, context: WorkflowContext
    ) -> tuple[AssetAnalyticsReport, AssetIntelligenceSummary]:
        report = self._foundation.asset_intelligence(project_id, context)
        assets = report.index.assets
        relationships = report.index.relationships
        analytics = AssetAnalyticsReport(
            usage=AssetUsageMetrics(
                asset_count=len(assets),
                referenced_page_count=len(
                    {asset.page_reference for asset in assets if asset.page_reference}
                ),
            ),
            dependencies=AssetDependencyMetrics(
                relationship_count=len(relationships), dependency_count=len(relationships)
            ),
            quality=AssetQualityMetrics(
                assets_with_metadata=sum(bool(asset.metadata.metadata_keys) for asset in assets),
                quality_evidence_present=any(asset.category.name == "quality" for asset in assets),
            ),
            relationships=AssetRelationshipAnalysis(
                relationship_count=len(relationships),
                relationship_types=tuple(
                    sorted({relationship.relation for relationship in relationships})
                ),
            ),
        )
        return analytics, AssetIntelligenceSummary(
            asset_count=len(assets),
            insight_count=4,
            recommendation="Inspect metadata keys before any human-directed asset review.",
        )

    def workflow_intelligence(self, context: WorkflowContext) -> WorkflowIntelligenceInsightReport:
        profile, pipeline = self._foundation.workflow_profiles(context)
        history = _history_entries(context)
        next_command = pipeline.next_command
        current = context.state
        requires_human = current is PageState.QUALITY_CHECKED
        return WorkflowIntelligenceInsightReport(
            efficiency=WorkflowEfficiencyAnalysis(
                completed_stage_count=_completed_stages(current),
                remaining_stage_count=max(len(PageState) - _completed_stages(current), 0),
                artifact_count=len(context.artifacts),
            ),
            bottleneck=PipelineBottleneckReport(
                current_state=current,
                bottleneck="human_approval" if requires_human else None,
                requires_human_review=requires_human,
            ),
            recommendation=V32WorkflowRecommendation(
                message=(
                    "Human approval is the only valid next action."
                    if requires_human
                    else "Use the existing StateMachine command only when its guards are satisfied."
                ),
                next_command=next_command,
            ),
            timeline=ExecutionTimelineAnalysis(
                observed_event_count=len(history),
                stages=tuple(entry.get("to", entry.get("step", "workflow")) for entry in history),
            ),
            health=V32WorkflowHealthReport(
                status="healthy"
                if profile.analysis_only and not profile.profile.workflow_modified
                else "attention",
                checks=("one_page_scope", "state_machine_authority", "no_auto_transition"),
            ),
            summary=WorkflowIntelligenceSummary(current_state=current, next_command=next_command),
        )

    def production_insights(self, context: WorkflowContext) -> ProductionInsightsReport:
        analytics = self._foundation.production_analytics(context)
        quality_present = analytics.quality.quality_evidence_present
        review_present = analytics.review.review_evidence_present
        projects = tuple(self._repository.list())
        insight_messages = (
            ProductionInsightDTO(
                category="quality",
                message="Quality evidence is available."
                if quality_present
                else "Quality evidence is not yet available.",
            ),
            ProductionInsightDTO(
                category="review",
                message="Review evidence is available."
                if review_present
                else "Review evidence is not yet available.",
            ),
            ProductionInsightDTO(
                category="productivity",
                message="Project totals are a read-only local projection.",
            ),
            ProductionInsightDTO(
                category="forecast",
                message="Forecasting is intentionally diagnostic-only and not computed.",
            ),
        )
        return ProductionInsightsReport(
            quality=QualityTrendAnalysis(
                quality_evidence_present=quality_present,
                observed_state=context.state,
                trend="evidence_present" if quality_present else "insufficient_evidence",
            ),
            review=ReviewEfficiencyReport(
                review_evidence_present=review_present,
                history_entries=analytics.workflow.history_entries,
            ),
            productivity=ProductivityInsight(
                project_count=len(projects),
                page_count=sum(len(project.pages) for project in projects),
            ),
            forecast=ProductionForecastReport(
                basis=("local_workflow_evidence", "no_remote_collection"),
            ),
            executive=AnalyticsExecutiveSummary(insights=insight_messages),
        )

    def creative_workspace_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> CreativeWorkspaceDashboardDTO:
        return CreativeWorkspaceDashboardDTO(report=self.creative_workspace(project_id, context))

    def asset_analytics_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> AssetAnalyticsDashboardDTO:
        report, summary = self.asset_analytics(project_id, context)
        return AssetAnalyticsDashboardDTO(report=report, summary=summary)

    def workflow_intelligence_dashboard(
        self, context: WorkflowContext
    ) -> WorkflowIntelligenceDashboardDTO:
        return WorkflowIntelligenceDashboardDTO(report=self.workflow_intelligence(context))

    def production_insights_dashboard(
        self, context: WorkflowContext
    ) -> ProductionInsightsDashboardDTO:
        return ProductionInsightsDashboardDTO(report=self.production_insights(context))


def _workspace_timeline(context: WorkflowContext) -> WorkspaceTimelineDTO:
    entries = tuple(
        WorkspaceTimelineEntryDTO(
            label=str(entry.get("step", entry.get("to", "workflow"))),
            state=_state_from_history(entry, context.state),
            source="workflow_history",
        )
        for entry in _history_entries(context)
    )
    return WorkspaceTimelineDTO(entries=entries)


def _history_entries(context: WorkflowContext) -> tuple[Mapping[str, Any], ...]:
    history = context.metadata.get("workflow_history", ())
    if not isinstance(history, list | tuple):
        return ()
    return tuple(entry for entry in history if isinstance(entry, Mapping))


def _state_from_history(entry: Mapping[str, Any], fallback: PageState) -> PageState:
    value = entry.get("to", entry.get("state"))
    try:
        return PageState(str(value))
    except ValueError:
        return fallback


def _completed_stages(state: PageState) -> int:
    return tuple(PageState).index(state) + 1


def _next_command(state: PageState) -> str | None:
    try:
        return StateMachine().next_command(state)
    except Exception:
        return None
