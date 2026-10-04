"""v3.4 analysis-only knowledge, operations, organization, and release insights.

This module turns v3.4 Foundation DTOs into bounded immutable advisory reports.
It does not execute or alter a workflow, mutate Repository data, score people,
assign work, schedule, allocate resources, deploy, tag, sign, publish, approve,
or remediate. The existing StateMachine remains the only workflow authority.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.domain.state_machine import PageState
from manga_director.production.director import DirectorModel
from manga_director.production.v3_4_foundation import V34FoundationService
from manga_director.repositories.protocols import ProjectRepository
from manga_director.workflow.contracts import WorkflowContext


class KnowledgeInsightDTO(DirectorModel):
    category: Literal["catalog", "relationship", "quality", "coverage", "recommendation"]
    message: str
    action_applied: bool = False


class KnowledgeDependencyAnalysis(DirectorModel):
    relationship_count: int = Field(ge=0)
    relation_types: tuple[str, ...] = ()
    dependency_resolved: bool = False


class KnowledgeQualityReport(DirectorModel):
    observed_entry_count: int = Field(ge=0)
    provenance_available: bool
    quality_score_computed: bool = False
    correction_applied: bool = False


class KnowledgeCoverageReport(DirectorModel):
    classification_count: int = Field(ge=0)
    populated_classification_count: int = Field(ge=0)
    coverage_computed: bool = False


class KnowledgeRecommendationReport(DirectorModel):
    recommendations: tuple[str, ...] = ()
    recommendation_applied: bool = False


class KnowledgeIntelligenceSummary(DirectorModel):
    insight_count: int = Field(ge=0)
    relationship_count: int = Field(ge=0)
    repository_mutated: bool = False
    automatic_action_taken: bool = False


class KnowledgeIntelligenceReport(DirectorModel):
    insights: tuple[KnowledgeInsightDTO, ...] = ()
    dependencies: KnowledgeDependencyAnalysis
    quality: KnowledgeQualityReport
    coverage: KnowledgeCoverageReport
    recommendations: KnowledgeRecommendationReport
    summary: KnowledgeIntelligenceSummary
    analysis_only: bool = True


class ProductionEfficiencyDTO(DirectorModel):
    current_state: PageState
    observed_page_count: int = Field(ge=0)
    observed_history_count: int = Field(ge=0)
    efficiency_scored: bool = False


class CapacityOptimizationReport(DirectorModel):
    observed_page_count: int = Field(ge=0)
    recommendations: tuple[str, ...] = ()
    capacity_plan_applied: bool = False


class ResourceAllocationAnalysis(DirectorModel):
    observed_chapter_count: int = Field(ge=0)
    resource_allocated: bool = False
    allocation_rebalanced: bool = False


class OperationsBottleneckReport(DirectorModel):
    current_state: PageState
    bottleneck: str | None = None
    remediation_applied: bool = False


class ProductionOptimizationSummary(DirectorModel):
    recommendation_count: int = Field(ge=0)
    workflow_modified: bool = False
    automatic_action_taken: bool = False


class ProductionOptimizationReport(DirectorModel):
    efficiency: ProductionEfficiencyDTO
    capacity: CapacityOptimizationReport
    allocation: ResourceAllocationAnalysis
    bottleneck: OperationsBottleneckReport
    summary: ProductionOptimizationSummary
    analysis_only: bool = True


class OrganizationTrendDTO(DirectorModel):
    observed_state: PageState
    observed_history_count: int = Field(ge=0)
    trend_computed: bool = False


class TeamProductivityReport(DirectorModel):
    observed_page_count: int = Field(ge=0)
    productivity_score_computed: bool = False
    personnel_action_taken: bool = False


class CollaborationAnalysis(DirectorModel):
    observed_handoff_count: int = Field(ge=0)
    collaboration_scored: bool = False
    notification_sent: bool = False


class RoleUtilizationReport(DirectorModel):
    observed_role_count: int = Field(ge=0)
    utilization_computed: bool = False
    role_changed: bool = False


class OrganizationForecast(DirectorModel):
    forecast: Literal["not_computed"] = "not_computed"
    assumptions: tuple[str, ...] = ()
    delivery_committed: bool = False


class OrganizationAnalyticsSummary(DirectorModel):
    observation_count: int = Field(ge=0)
    recommendations_applied: bool = False
    automatic_action_taken: bool = False


class OrganizationAnalyticsReport(DirectorModel):
    trend: OrganizationTrendDTO
    productivity: TeamProductivityReport
    collaboration: CollaborationAnalysis
    role_utilization: RoleUtilizationReport
    forecast: OrganizationForecast
    summary: OrganizationAnalyticsSummary
    analysis_only: bool = True


class ReleaseTrendDTO(DirectorModel):
    release_version: str
    observed_history_count: int = Field(ge=0)
    trend_computed: bool = False


class DeploymentAnalyticsReport(DirectorModel):
    deployment_evidence_count: int = Field(ge=0)
    analytics_collected_remotely: bool = False
    deployment_started: bool = False


class RegressionTrendReport(DirectorModel):
    observed_history_count: int = Field(ge=0)
    regression_detected: bool = False
    remediation_applied: bool = False


class CompatibilityAnalytics(DirectorModel):
    baseline_count: int = Field(ge=0)
    compatibility_scored: bool = False
    public_api_changed: bool = False


class ReleaseForecast(DirectorModel):
    forecast: Literal["not_computed"] = "not_computed"
    assumptions: tuple[str, ...] = ()
    release_authorized: bool = False


class ReleaseAnalyticsSummary(DirectorModel):
    observation_count: int = Field(ge=0)
    tag_created: bool = False
    publication_started: bool = False
    automatic_action_taken: bool = False


class ReleaseAnalyticsReport(DirectorModel):
    trend: ReleaseTrendDTO
    deployment: DeploymentAnalyticsReport
    regression: RegressionTrendReport
    compatibility: CompatibilityAnalytics
    forecast: ReleaseForecast
    summary: ReleaseAnalyticsSummary
    analysis_only: bool = True


class KnowledgeIntelligenceDashboardDTO(DirectorModel):
    report: KnowledgeIntelligenceReport
    automatic_action_taken: bool = False


class ProductionOptimizationDashboardDTO(DirectorModel):
    report: ProductionOptimizationReport
    automatic_action_taken: bool = False


class OrganizationAnalyticsDashboardDTO(DirectorModel):
    report: OrganizationAnalyticsReport
    automatic_action_taken: bool = False


class ReleaseAnalyticsDashboardDTO(DirectorModel):
    report: ReleaseAnalyticsReport
    automatic_action_taken: bool = False


class V34InsightsService:
    """Compose v3.4 insights through existing read-only Repository boundaries."""

    def __init__(self, foundation: V34FoundationService, repository: ProjectRepository) -> None:
        self._foundation = foundation
        self._repository = repository

    def knowledge_intelligence(
        self, project_id: str, context: WorkflowContext
    ) -> KnowledgeIntelligenceReport:
        platform = self._foundation.knowledge_platform(project_id, context)
        relationship_types = tuple(sorted({item.relation for item in platform.relationships}))
        populated = sum(item.entry_count > 0 for item in platform.classifications)
        insights = (
            KnowledgeInsightDTO(
                category="catalog",
                message="Catalog observations use the existing Repository port only.",
            ),
            KnowledgeInsightDTO(
                category="relationship",
                message="Relationships are observed evidence and are never persisted by this report.",
            ),
            KnowledgeInsightDTO(
                category="quality",
                message="Knowledge quality remains advisory and no score or correction is applied.",
            ),
            KnowledgeInsightDTO(
                category="coverage",
                message="Coverage reports describe supplied classifications without remote search.",
            ),
            KnowledgeInsightDTO(
                category="recommendation",
                message="Recommendations require a human-directed follow-up through existing workflows.",
            ),
        )
        recommendations = (
            "Review provenance and redacted catalog evidence before a human knowledge decision.",
        )
        return KnowledgeIntelligenceReport(
            insights=insights,
            dependencies=KnowledgeDependencyAnalysis(
                relationship_count=len(platform.relationships), relation_types=relationship_types
            ),
            quality=KnowledgeQualityReport(
                observed_entry_count=platform.quality.observed_entry_count,
                provenance_available=platform.quality.provenance_available,
            ),
            coverage=KnowledgeCoverageReport(
                classification_count=len(platform.classifications),
                populated_classification_count=populated,
            ),
            recommendations=KnowledgeRecommendationReport(recommendations=recommendations),
            summary=KnowledgeIntelligenceSummary(
                insight_count=len(insights), relationship_count=len(platform.relationships)
            ),
        )

    def production_optimization(
        self, project_id: str, context: WorkflowContext
    ) -> ProductionOptimizationReport:
        operations = self._foundation.production_operations(project_id, context)
        bottleneck = "human_approval" if context.state is PageState.QUALITY_CHECKED else None
        recommendations = (
            "Use the existing StateMachine command only after its required evidence exists.",
        )
        return ProductionOptimizationReport(
            efficiency=ProductionEfficiencyDTO(
                current_state=context.state,
                observed_page_count=operations.capacity.observed_page_count,
                observed_history_count=operations.status.observed_history_count,
            ),
            capacity=CapacityOptimizationReport(
                observed_page_count=operations.capacity.observed_page_count,
                recommendations=recommendations,
            ),
            allocation=ResourceAllocationAnalysis(
                observed_chapter_count=operations.capacity.observed_chapter_count
            ),
            bottleneck=OperationsBottleneckReport(
                current_state=context.state, bottleneck=bottleneck
            ),
            summary=ProductionOptimizationSummary(recommendation_count=len(recommendations)),
        )

    def organization_analytics(
        self, project_id: str, context: WorkflowContext
    ) -> OrganizationAnalyticsReport:
        organization = self._foundation.organization_intelligence(project_id, context)
        operations = self._foundation.production_operations(project_id, context)
        return OrganizationAnalyticsReport(
            trend=OrganizationTrendDTO(
                observed_state=context.state,
                observed_history_count=operations.status.observed_history_count,
            ),
            productivity=TeamProductivityReport(
                observed_page_count=operations.capacity.observed_page_count
            ),
            collaboration=CollaborationAnalysis(
                observed_handoff_count=organization.collaboration.observed_handoff_count
            ),
            role_utilization=RoleUtilizationReport(observed_role_count=len(organization.roles)),
            forecast=OrganizationForecast(
                assumptions=("local one-page evidence only", "no delivery commitment"),
            ),
            summary=OrganizationAnalyticsSummary(
                observation_count=len(organization.roles)
                + organization.collaboration.observed_handoff_count
            ),
        )

    def release_analytics(
        self, project_id: str, context: WorkflowContext
    ) -> ReleaseAnalyticsReport:
        release = self._foundation.release_intelligence(project_id, context)
        baseline_count = len(release.compatibility.preserved_baselines)
        return ReleaseAnalyticsReport(
            trend=ReleaseTrendDTO(
                release_version=release.health.release_version,
                observed_history_count=release.regression.observed_history_count,
            ),
            deployment=DeploymentAnalyticsReport(
                deployment_evidence_count=release.deployment.deployment_evidence_count
            ),
            regression=RegressionTrendReport(
                observed_history_count=release.regression.observed_history_count
            ),
            compatibility=CompatibilityAnalytics(baseline_count=baseline_count),
            forecast=ReleaseForecast(
                assumptions=("local evidence only", "hosted release gates remain required"),
            ),
            summary=ReleaseAnalyticsSummary(observation_count=baseline_count + 3),
        )

    def knowledge_intelligence_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> KnowledgeIntelligenceDashboardDTO:
        return KnowledgeIntelligenceDashboardDTO(
            report=self.knowledge_intelligence(project_id, context)
        )

    def production_optimization_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> ProductionOptimizationDashboardDTO:
        return ProductionOptimizationDashboardDTO(
            report=self.production_optimization(project_id, context)
        )

    def organization_analytics_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> OrganizationAnalyticsDashboardDTO:
        return OrganizationAnalyticsDashboardDTO(
            report=self.organization_analytics(project_id, context)
        )

    def release_analytics_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> ReleaseAnalyticsDashboardDTO:
        return ReleaseAnalyticsDashboardDTO(report=self.release_analytics(project_id, context))
