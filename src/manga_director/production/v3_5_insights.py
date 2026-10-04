"""v3.5 analysis-only intelligence reports built from foundation DTOs.

The service consumes supplied Foundation and Repository evidence only. It does
not persist insights, alter creative inputs, apply recommendations, schedule,
allocate, remediate, deploy, collect remotely, or authorize an approval.
"""

from __future__ import annotations

from pydantic import Field

from manga_director.production.director import DirectorModel
from manga_director.production.v3_5_foundation import V35FoundationService
from manga_director.repositories.protocols import ProjectRepository
from manga_director.workflow.contracts import WorkflowContext


class KnowledgeInsightDTO(DirectorModel):
    insight_id: str
    observed_node_count: int = Field(ge=0)
    applied: bool = False


class KnowledgeCoverageReport(DirectorModel):
    observed_category_count: int = Field(ge=0)
    coverage_persisted: bool = False


class KnowledgeRelationshipAnalysis(DirectorModel):
    observed_edge_count: int = Field(ge=0)
    graph_changed: bool = False


class KnowledgeRecommendationReport(DirectorModel):
    recommendation_count: int = Field(ge=0)
    recommendation_applied: bool = False


class KnowledgeHealthSummary(DirectorModel):
    observed_trace_count: int = Field(ge=0)
    health_enforced: bool = False


class KnowledgeAnalyticsReport(DirectorModel):
    insight: KnowledgeInsightDTO
    coverage: KnowledgeCoverageReport
    relationships: KnowledgeRelationshipAnalysis
    recommendations: KnowledgeRecommendationReport
    health: KnowledgeHealthSummary
    analysis_only: bool = True


class StoryAnalyticsDTO(DirectorModel):
    observed_history_count: int = Field(ge=0)
    story_changed: bool = False


class CharacterAnalyticsDTO(DirectorModel):
    observed_reference_count: int = Field(ge=0)
    character_changed: bool = False


class PageQualityAnalysis(DirectorModel):
    current_state: str
    quality_completed: bool = False
    approval_granted: bool = False


class CreativeTrendReport(DirectorModel):
    observed_metric_count: int = Field(ge=0)
    trend_persisted: bool = False


class CreativeRecommendationSummary(DirectorModel):
    recommendation_count: int = Field(ge=0)
    recommendation_applied: bool = False


class CreativeAnalyticsReport(DirectorModel):
    story: StoryAnalyticsDTO
    character: CharacterAnalyticsDTO
    page_quality: PageQualityAnalysis
    trend: CreativeTrendReport
    recommendations: CreativeRecommendationSummary
    analysis_only: bool = True


class PipelineEfficiencyAnalysis(DirectorModel):
    observed_history_count: int = Field(ge=0)
    pipeline_changed: bool = False


class CapacityForecast(DirectorModel):
    observed_page_count: int = Field(ge=0)
    forecast_committed: bool = False
    capacity_allocated: bool = False


class DeliveryRiskAnalysis(DirectorModel):
    risk_count: int = Field(ge=0)
    mitigation_applied: bool = False


class ProductionOptimizationReport(DirectorModel):
    observed_metric_count: int = Field(ge=0)
    optimization_applied: bool = False
    deployment_started: bool = False


class ProductionExecutiveDashboard(DirectorModel):
    project_id: str
    observation_count: int = Field(ge=0)
    schedule_changed: bool = False


class ProductionAnalyticsReport(DirectorModel):
    efficiency: PipelineEfficiencyAnalysis
    capacity: CapacityForecast
    delivery_risk: DeliveryRiskAnalysis
    optimization: ProductionOptimizationReport
    executive: ProductionExecutiveDashboard
    analysis_only: bool = True


class CrossPlatformKPI(DirectorModel):
    metric_name: str
    observed_value: int = Field(ge=0)
    target_enforced: bool = False


class HistoricalTrendAnalysis(DirectorModel):
    observed_evidence_count: int = Field(ge=0)
    history_persisted: bool = False


class RegressionTrend(DirectorModel):
    regression_detected: bool = False
    remediation_applied: bool = False


class ExecutiveAnalyticsReport(DirectorModel):
    dashboard_id: str
    report_count: int = Field(ge=0)
    release_authorized: bool = False


class PlatformHealthDashboard(DirectorModel):
    component_count: int = Field(ge=0)
    monitoring_started: bool = False
    external_action_taken: bool = False


class PlatformIntelligenceReport(DirectorModel):
    kpis: tuple[CrossPlatformKPI, ...] = ()
    history: HistoricalTrendAnalysis
    regression: RegressionTrend
    executive: ExecutiveAnalyticsReport
    health: PlatformHealthDashboard
    analysis_only: bool = True


class KnowledgeInsightsDashboardDTO(DirectorModel):
    report: KnowledgeAnalyticsReport
    automatic_action_taken: bool = False


class CreativeAnalyticsDashboardDTO(DirectorModel):
    report: CreativeAnalyticsReport
    automatic_action_taken: bool = False


class ProductionAnalyticsDashboardDTO(DirectorModel):
    report: ProductionAnalyticsReport
    automatic_action_taken: bool = False


class ExecutiveAnalyticsDashboardDTO(DirectorModel):
    report: PlatformIntelligenceReport
    automatic_action_taken: bool = False


class V35InsightsService:
    """Compose v3.5 intelligence analysis without applying any decision."""

    def __init__(self, foundation: V35FoundationService, repository: ProjectRepository) -> None:
        self._foundation = foundation
        self._repository = repository

    def knowledge_analytics(self, project_id: str, context: WorkflowContext) -> KnowledgeAnalyticsReport:
        graph = self._foundation.knowledge_graph(project_id, context)
        return KnowledgeAnalyticsReport(
            insight=KnowledgeInsightDTO(
                insight_id=f"knowledge-insight:{project_id}:{graph.context.page_reference}",
                observed_node_count=len(graph.graph.nodes),
            ),
            coverage=KnowledgeCoverageReport(
                observed_category_count=len({node.category for node in graph.graph.nodes})
            ),
            relationships=KnowledgeRelationshipAnalysis(observed_edge_count=len(graph.graph.edges)),
            recommendations=KnowledgeRecommendationReport(recommendation_count=0),
            health=KnowledgeHealthSummary(observed_trace_count=len(graph.traces)),
        )

    def creative_analytics(self, project_id: str, context: WorkflowContext) -> CreativeAnalyticsReport:
        creative = self._foundation.creative_intelligence(project_id, context)
        return CreativeAnalyticsReport(
            story=StoryAnalyticsDTO(observed_history_count=creative.story.observed_history_count),
            character=CharacterAnalyticsDTO(
                observed_reference_count=creative.character.observed_character_reference_count
            ),
            page_quality=PageQualityAnalysis(current_state=creative.page_quality.current_state.value),
            trend=CreativeTrendReport(observed_metric_count=len(creative.metrics)),
            recommendations=CreativeRecommendationSummary(recommendation_count=0),
        )

    def production_analytics(
        self, project_id: str, context: WorkflowContext
    ) -> ProductionAnalyticsReport:
        production = self._foundation.production_intelligence(project_id, context)
        risk_count = int(production.pipeline.observed_history_count == 0)
        return ProductionAnalyticsReport(
            efficiency=PipelineEfficiencyAnalysis(
                observed_history_count=production.pipeline.observed_history_count
            ),
            capacity=CapacityForecast(observed_page_count=production.capacity.observed_page_count),
            delivery_risk=DeliveryRiskAnalysis(risk_count=risk_count),
            optimization=ProductionOptimizationReport(observed_metric_count=len(production.metrics)),
            executive=ProductionExecutiveDashboard(
                project_id=production.executive.project_id,
                observation_count=production.executive.observation_count,
            ),
        )

    def platform_intelligence(
        self, project_id: str, context: WorkflowContext
    ) -> PlatformIntelligenceReport:
        platform = self._foundation.platform_analytics(project_id, context)
        self._repository.load(project_id)
        return PlatformIntelligenceReport(
            kpis=tuple(
                CrossPlatformKPI(metric_name=item.metric_name, observed_value=item.observed_value)
                for item in platform.kpis
            ),
            history=HistoricalTrendAnalysis(observed_evidence_count=platform.history.evidence_count),
            regression=RegressionTrend(),
            executive=ExecutiveAnalyticsReport(
                dashboard_id=platform.dashboard.dashboard_id,
                report_count=platform.dashboard.report_count,
            ),
            health=PlatformHealthDashboard(component_count=platform.health.component_count),
        )

    def knowledge_insights_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> KnowledgeInsightsDashboardDTO:
        return KnowledgeInsightsDashboardDTO(report=self.knowledge_analytics(project_id, context))

    def creative_analytics_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> CreativeAnalyticsDashboardDTO:
        return CreativeAnalyticsDashboardDTO(report=self.creative_analytics(project_id, context))

    def production_analytics_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> ProductionAnalyticsDashboardDTO:
        return ProductionAnalyticsDashboardDTO(report=self.production_analytics(project_id, context))

    def executive_analytics_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> ExecutiveAnalyticsDashboardDTO:
        return ExecutiveAnalyticsDashboardDTO(report=self.platform_intelligence(project_id, context))
