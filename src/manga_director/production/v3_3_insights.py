"""v3.3 analysis-only production, quality, asset, and operations insights.

This module turns the Iteration 1 DTO foundations into bounded, immutable
advisory reports.  It does not execute or alter a workflow, approve work,
persist an asset change, schedule work, allocate resources, or make a delivery
commitment.  The existing StateMachine remains the only workflow authority.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from pydantic import Field

from manga_director.domain.state_machine import PageState
from manga_director.production.director import DirectorModel
from manga_director.production.v3_3_foundation import V33FoundationService
from manga_director.repositories.protocols import ProjectRepository
from manga_director.workflow.contracts import WorkflowContext


class ProductionInsightDTO(DirectorModel):
    category: Literal["pipeline", "quality", "timeline", "optimization"]
    message: str
    action_applied: bool = False


class PipelineEfficiencyDTO(DirectorModel):
    observed_stage_count: int = Field(ge=0)
    observed_history_count: int = Field(ge=0)
    current_state: PageState
    efficiency_scored: bool = False


class StageBottleneckReport(DirectorModel):
    current_state: PageState
    suggested_next_command: str | None = None
    bottleneck: str | None = None
    remediation_applied: bool = False


class ExecutionTimelineAnalysis(DirectorModel):
    observed_events: tuple[str, ...] = ()
    event_count: int = Field(ge=0)
    execution_replayed: bool = False


class PipelineOptimizationReport(DirectorModel):
    recommendations: tuple[str, ...] = ()
    workflow_modified: bool = False
    optimization_applied: bool = False


class ProductionIntelligenceSummary(DirectorModel):
    insight_count: int = Field(ge=0)
    current_state: PageState
    next_command: str | None = None
    automatic_action_taken: bool = False


class ProductionIntelligenceReport(DirectorModel):
    insights: tuple[ProductionInsightDTO, ...] = ()
    efficiency: PipelineEfficiencyDTO
    bottleneck: StageBottleneckReport
    timeline: ExecutionTimelineAnalysis
    optimization: PipelineOptimizationReport
    summary: ProductionIntelligenceSummary
    analysis_only: bool = True


class QualityTrendDTO(DirectorModel):
    observed_state: PageState
    quality_evidence_present: bool
    trend: Literal["evidence_present", "review_pending"]
    score_computed: bool = False


class QualityRegressionReport(DirectorModel):
    baseline_available: bool = False
    regression_detected: bool = False
    remediation_applied: bool = False


class ReviewCoverageReport(DirectorModel):
    review_evidence_present: bool
    observed_history_count: int = Field(ge=0)
    coverage_computed: bool = False


class ConsistencyAnalysis(DirectorModel):
    storyboard_evidence_present: bool
    consistent: bool | None = None
    correction_applied: bool = False


class QualityExecutiveSummary(DirectorModel):
    findings_count: int = Field(ge=0)
    human_quality_review_required: bool = True
    approval_authorized: bool = False


class QualityAnalyticsReport(DirectorModel):
    trend: QualityTrendDTO
    regression: QualityRegressionReport
    coverage: ReviewCoverageReport
    consistency: ConsistencyAnalysis
    executive: QualityExecutiveSummary
    analysis_only: bool = True


class AssetUsageAnalytics(DirectorModel):
    asset_count: int = Field(ge=0)
    referenced_page_count: int = Field(ge=0)
    usage_collected_remotely: bool = False


class AssetDependencyAnalysis(DirectorModel):
    dependency_count: int = Field(ge=0)
    relation_types: tuple[str, ...] = ()
    dependency_resolved: bool = False


class AssetConsistencyReport(DirectorModel):
    assets_with_history: int = Field(ge=0)
    consistency_verified: bool = False
    repair_applied: bool = False


class AssetRecommendationReport(DirectorModel):
    recommendations: tuple[str, ...] = ()
    recommendation_applied: bool = False


class AssetHealthScore(DirectorModel):
    score_computed: bool = False
    health: Literal["observed"] = "observed"


class AssetIntelligenceSummary(DirectorModel):
    asset_count: int = Field(ge=0)
    recommendation_count: int = Field(ge=0)
    repository_mutated: bool = False
    values_redacted: bool = True


class AssetIntelligenceReport(DirectorModel):
    usage: AssetUsageAnalytics
    dependencies: AssetDependencyAnalysis
    consistency: AssetConsistencyReport
    recommendations: AssetRecommendationReport
    health: AssetHealthScore
    summary: AssetIntelligenceSummary
    analysis_only: bool = True


class ProjectOperationsDTO(DirectorModel):
    project_id: str
    current_state: PageState
    operation: Literal["observe", "review", "forecast"]
    operation_started: bool = False


class MilestoneProgressReport(DirectorModel):
    milestone_count: int = Field(ge=0)
    reached_count: int = Field(ge=0)
    progress_computed: bool = False


class ResourceUtilizationReport(DirectorModel):
    declared_resource_count: int = Field(ge=0)
    utilization_computed: bool = False
    resource_allocated: bool = False


class DeliveryForecastReport(DirectorModel):
    forecast: Literal["not_computed"] = "not_computed"
    assumptions: tuple[str, ...] = ()
    delivery_committed: bool = False


class OperationalRiskReport(DirectorModel):
    risks: tuple[str, ...] = ()
    risk_count: int = Field(ge=0)
    mitigation_applied: bool = False


class ProjectOperationsSummary(DirectorModel):
    project_id: str
    observation_count: int = Field(ge=0)
    scheduling_changed: bool = False
    automatic_action_taken: bool = False


class ProjectOperationsReport(DirectorModel):
    operations: ProjectOperationsDTO
    milestone_progress: MilestoneProgressReport
    resource_utilization: ResourceUtilizationReport
    delivery_forecast: DeliveryForecastReport
    risks: OperationalRiskReport
    summary: ProjectOperationsSummary
    analysis_only: bool = True


class ProductionIntelligenceDashboardDTO(DirectorModel):
    report: ProductionIntelligenceReport
    automatic_action_taken: bool = False


class QualityAnalyticsDashboardDTO(DirectorModel):
    report: QualityAnalyticsReport
    automatic_action_taken: bool = False


class AssetIntelligenceDashboardDTO(DirectorModel):
    report: AssetIntelligenceReport
    automatic_action_taken: bool = False


class ProjectOperationsDashboardDTO(DirectorModel):
    report: ProjectOperationsReport
    automatic_action_taken: bool = False


class V33InsightsService:
    """Compose v3.3 insights through existing read-only Repository boundaries."""

    def __init__(self, foundation: V33FoundationService, repository: ProjectRepository) -> None:
        self._foundation = foundation
        self._repository = repository

    def production_intelligence(
        self, project_id: str, context: WorkflowContext
    ) -> ProductionIntelligenceReport:
        pipeline = self._foundation.production_pipeline(project_id, context)
        history = _history_labels(context)
        bottleneck = "human_approval" if context.state is PageState.QUALITY_CHECKED else None
        next_command = pipeline.summary.next_command
        insights = (
            ProductionInsightDTO(
                category="pipeline",
                message="Pipeline state is observed from the existing StateMachine.",
            ),
            ProductionInsightDTO(
                category="quality",
                message="Human quality review and approval remain explicit workflow guards.",
            ),
            ProductionInsightDTO(
                category="timeline",
                message="Timeline analysis uses supplied workflow history only.",
            ),
            ProductionInsightDTO(
                category="optimization",
                message="Optimization recommendations are advisory and are never applied.",
            ),
        )
        return ProductionIntelligenceReport(
            insights=insights,
            efficiency=PipelineEfficiencyDTO(
                observed_stage_count=pipeline.summary.stage_count,
                observed_history_count=len(history),
                current_state=context.state,
            ),
            bottleneck=StageBottleneckReport(
                current_state=context.state,
                suggested_next_command=next_command,
                bottleneck=bottleneck,
            ),
            timeline=ExecutionTimelineAnalysis(observed_events=history, event_count=len(history)),
            optimization=PipelineOptimizationReport(
                recommendations=(
                    "Use only the suggested StateMachine command after its required evidence exists.",
                )
            ),
            summary=ProductionIntelligenceSummary(
                insight_count=len(insights), current_state=context.state, next_command=next_command
            ),
        )

    def quality_analytics(self, context: WorkflowContext) -> QualityAnalyticsReport:
        quality = self._foundation.quality_intelligence(context)
        history = _history_labels(context)
        quality_present = quality.dashboard.quality_review_completed
        storyboard_present = any(
            rule.rule_id == "storyboard_before_generation" and rule.observed
            for rule in quality.rules
        )
        return QualityAnalyticsReport(
            trend=QualityTrendDTO(
                observed_state=context.state,
                quality_evidence_present=quality_present,
                trend="evidence_present" if quality_present else "review_pending",
            ),
            regression=QualityRegressionReport(),
            coverage=ReviewCoverageReport(
                review_evidence_present=quality_present, observed_history_count=len(history)
            ),
            consistency=ConsistencyAnalysis(storyboard_evidence_present=storyboard_present),
            executive=QualityExecutiveSummary(findings_count=quality.summary.finding_count),
        )

    def asset_intelligence(
        self, project_id: str, context: WorkflowContext
    ) -> AssetIntelligenceReport:
        lifecycle = self._foundation.asset_lifecycle(project_id, context)
        assets = lifecycle.assets
        dependencies = lifecycle.dependencies
        relation_types = tuple(sorted({dependency.relation for dependency in dependencies}))
        recommendations = (
            "Inspect redacted lifecycle evidence before any human-directed asset decision.",
        )
        return AssetIntelligenceReport(
            usage=AssetUsageAnalytics(
                asset_count=len(assets),
                referenced_page_count=len({dependency.target_reference for dependency in dependencies}),
            ),
            dependencies=AssetDependencyAnalysis(
                dependency_count=len(dependencies), relation_types=relation_types
            ),
            consistency=AssetConsistencyReport(assets_with_history=len(lifecycle.history)),
            recommendations=AssetRecommendationReport(recommendations=recommendations),
            health=AssetHealthScore(),
            summary=AssetIntelligenceSummary(
                asset_count=len(assets), recommendation_count=len(recommendations)
            ),
        )

    def project_operations(
        self, project_id: str, context: WorkflowContext
    ) -> ProjectOperationsReport:
        project = self._repository.load(project_id)
        intelligence = self._foundation.project_intelligence(project_id, context)
        risks = intelligence.risks.risks
        milestones = intelligence.milestones
        return ProjectOperationsReport(
            operations=ProjectOperationsDTO(
                project_id=project.id, current_state=context.state, operation="observe"
            ),
            milestone_progress=MilestoneProgressReport(
                milestone_count=len(milestones),
                reached_count=sum(milestone.reached for milestone in milestones),
            ),
            resource_utilization=ResourceUtilizationReport(
                declared_resource_count=intelligence.resources.declared_resource_count
            ),
            delivery_forecast=DeliveryForecastReport(
                assumptions=("local evidence only", "no scheduling or delivery commitment"),
            ),
            risks=OperationalRiskReport(risks=risks, risk_count=len(risks)),
            summary=ProjectOperationsSummary(project_id=project.id, observation_count=5),
        )

    def production_intelligence_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> ProductionIntelligenceDashboardDTO:
        return ProductionIntelligenceDashboardDTO(
            report=self.production_intelligence(project_id, context)
        )

    def quality_analytics_dashboard(
        self, context: WorkflowContext
    ) -> QualityAnalyticsDashboardDTO:
        return QualityAnalyticsDashboardDTO(report=self.quality_analytics(context))

    def asset_intelligence_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> AssetIntelligenceDashboardDTO:
        return AssetIntelligenceDashboardDTO(report=self.asset_intelligence(project_id, context))

    def project_operations_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> ProjectOperationsDashboardDTO:
        return ProjectOperationsDashboardDTO(report=self.project_operations(project_id, context))


def _history_labels(context: WorkflowContext) -> tuple[str, ...]:
    history = context.metadata.get("workflow_history", ())
    if not isinstance(history, list | tuple):
        return ()
    return tuple(
        str(entry.get("step", entry.get("to", "workflow")))
        for entry in history
        if isinstance(entry, Mapping)
    )
