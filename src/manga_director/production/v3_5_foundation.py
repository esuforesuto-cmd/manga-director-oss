"""v3.5 read-only foundations for unified creative intelligence.

These Application and logical Knowledge-layer projections use only existing
Repository and one-page workflow evidence. They never persist a graph, mutate a
project, execute or change a workflow, generate content, approve a Page,
schedule, allocate, deploy, or publish. The StateMachine remains the sole
authority for legal workflow transitions.
"""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import Field

from manga_director.domain.state_machine import PageState
from manga_director.production.director import DirectorModel
from manga_director.repositories.protocols import ProjectRepository
from manga_director.workflow.contracts import WorkflowContext


class KnowledgeNodeDTO(DirectorModel):
    node_id: str
    category: str
    source: str
    persisted: bool = False


class KnowledgeEdgeDTO(DirectorModel):
    source_id: str
    target_id: str
    relation: str
    persisted: bool = False


class KnowledgeGraphDTO(DirectorModel):
    graph_id: str
    nodes: tuple[KnowledgeNodeDTO, ...] = ()
    edges: tuple[KnowledgeEdgeDTO, ...] = ()
    repository_read_only: bool = True


class KnowledgeContextDTO(DirectorModel):
    project_id: str
    page_reference: str
    observed_artifact_count: int = Field(ge=0)
    context_applied: bool = False


class KnowledgeTraceDTO(DirectorModel):
    trace_id: str
    source_reference: str
    provenance_available: bool = True
    persisted: bool = False


class KnowledgeGraphSummary(DirectorModel):
    node_count: int = Field(ge=0)
    edge_count: int = Field(ge=0)
    automatic_action_taken: bool = False


class KnowledgeGraphReport(DirectorModel):
    graph: KnowledgeGraphDTO
    context: KnowledgeContextDTO
    traces: tuple[KnowledgeTraceDTO, ...] = ()
    summary: KnowledgeGraphSummary
    analysis_only: bool = True


class CreativeMetricDTO(DirectorModel):
    metric_name: str
    observed_count: int = Field(ge=0)
    score_computed: bool = False


class StoryAnalysisDTO(DirectorModel):
    page_reference: str
    observed_history_count: int = Field(ge=0)
    story_changed: bool = False


class CharacterAnalysisDTO(DirectorModel):
    observed_character_reference_count: int = Field(ge=0)
    character_changed: bool = False


class PageQualityDTO(DirectorModel):
    current_state: PageState
    quality_review_completed: bool = False
    approval_granted: bool = False


class CreativeSummaryDTO(DirectorModel):
    project_id: str
    observation_count: int = Field(ge=0)
    recommendation_applied: bool = False


class CreativeIntelligenceReport(DirectorModel):
    metrics: tuple[CreativeMetricDTO, ...] = ()
    story: StoryAnalysisDTO
    character: CharacterAnalysisDTO
    page_quality: PageQualityDTO
    summary: CreativeSummaryDTO
    analysis_only: bool = True


class ProductionMetricDTO(DirectorModel):
    metric_name: str
    observed_value: int = Field(ge=0)
    metric_persisted: bool = False


class PipelineInsightDTO(DirectorModel):
    current_state: PageState
    observed_history_count: int = Field(ge=0)
    pipeline_changed: bool = False


class CapacitySummaryDTO(DirectorModel):
    observed_page_count: int = Field(ge=0)
    observed_chapter_count: int = Field(ge=0)
    capacity_allocated: bool = False


class DeliveryForecastDTO(DirectorModel):
    basis: str
    forecast_committed: bool = False
    schedule_changed: bool = False


class ProductionHealthDTO(DirectorModel):
    current_state: PageState
    health_computed: bool = False
    remediation_started: bool = False


class ProductionExecutiveSummary(DirectorModel):
    project_id: str
    observation_count: int = Field(ge=0)
    deployment_started: bool = False
    automatic_action_taken: bool = False


class ProductionIntelligenceReport(DirectorModel):
    metrics: tuple[ProductionMetricDTO, ...] = ()
    pipeline: PipelineInsightDTO
    capacity: CapacitySummaryDTO
    delivery: DeliveryForecastDTO
    health: ProductionHealthDTO
    executive: ProductionExecutiveSummary
    analysis_only: bool = True


class PlatformHealthDTO(DirectorModel):
    component_count: int = Field(ge=0)
    health_checked: bool = False
    monitoring_started: bool = False


class AnalyticsDashboardDTO(DirectorModel):
    dashboard_id: str
    report_count: int = Field(ge=0)
    presentation_bound: bool = False


class TrendSummaryDTO(DirectorModel):
    observed_history_count: int = Field(ge=0)
    trend_persisted: bool = False
    regression_action_taken: bool = False


class HistoricalAnalysisDTO(DirectorModel):
    evidence_count: int = Field(ge=0)
    remote_collection_performed: bool = False


class ExecutiveKPIDTO(DirectorModel):
    metric_name: str
    observed_value: int = Field(ge=0)
    target_enforced: bool = False


class PlatformAnalyticsReport(DirectorModel):
    health: PlatformHealthDTO
    dashboard: AnalyticsDashboardDTO
    trend: TrendSummaryDTO
    history: HistoricalAnalysisDTO
    kpis: tuple[ExecutiveKPIDTO, ...] = ()
    analysis_only: bool = True


class KnowledgeGraphDashboardDTO(DirectorModel):
    report: KnowledgeGraphReport
    automatic_action_taken: bool = False


class CreativeIntelligenceDashboardDTO(DirectorModel):
    report: CreativeIntelligenceReport
    automatic_action_taken: bool = False


class ProductionIntelligenceDashboardDTO(DirectorModel):
    report: ProductionIntelligenceReport
    automatic_action_taken: bool = False


class PlatformAnalyticsDashboardDTO(DirectorModel):
    report: PlatformAnalyticsReport
    automatic_action_taken: bool = False


class V35FoundationService:
    """Build v3.5 DTO projections without workflow or operational authority."""

    def __init__(self, repository: ProjectRepository) -> None:
        self._repository = repository

    def knowledge_graph(self, project_id: str, context: WorkflowContext) -> KnowledgeGraphReport:
        project = self._repository.load(project_id)
        page_reference = _page_reference(context)
        categories = _knowledge_categories(project.metadata, context)
        nodes = tuple(
            KnowledgeNodeDTO(
                node_id=f"knowledge:{project.id}:{page_reference}:{category}",
                category=category,
                source="repository_projection",
            )
            for category in categories
        )
        page_node = f"page:{project.id}:{page_reference}"
        edges = tuple(
            KnowledgeEdgeDTO(
                source_id=node.node_id,
                target_id=page_node,
                relation="observed_for_page",
            )
            for node in nodes
        )
        traces = tuple(
            KnowledgeTraceDTO(
                trace_id=f"trace:{project.id}:{page_reference}:{node.category}",
                source_reference=node.source,
            )
            for node in nodes
        )
        return KnowledgeGraphReport(
            graph=KnowledgeGraphDTO(
                graph_id=f"knowledge-graph:{project.id}:{page_reference}", nodes=nodes, edges=edges
            ),
            context=KnowledgeContextDTO(
                project_id=project.id,
                page_reference=page_reference,
                observed_artifact_count=len(context.artifacts),
            ),
            traces=traces,
            summary=KnowledgeGraphSummary(node_count=len(nodes), edge_count=len(edges)),
        )

    def creative_intelligence(
        self, project_id: str, context: WorkflowContext
    ) -> CreativeIntelligenceReport:
        project = self._repository.load(project_id)
        history = _history_labels(context)
        metadata_references = len(project.metadata)
        return CreativeIntelligenceReport(
            metrics=(
                CreativeMetricDTO(metric_name="workflow_evidence", observed_count=len(history)),
                CreativeMetricDTO(metric_name="artifact_evidence", observed_count=len(context.artifacts)),
            ),
            story=StoryAnalysisDTO(
                page_reference=_page_reference(context), observed_history_count=len(history)
            ),
            character=CharacterAnalysisDTO(observed_character_reference_count=metadata_references),
            page_quality=PageQualityDTO(current_state=context.state),
            summary=CreativeSummaryDTO(
                project_id=project.id,
                observation_count=len(history) + len(context.artifacts) + metadata_references,
            ),
        )

    def production_intelligence(
        self, project_id: str, context: WorkflowContext
    ) -> ProductionIntelligenceReport:
        project = self._repository.load(project_id)
        history = _history_labels(context)
        observation_count = len(history) + len(context.artifacts)
        return ProductionIntelligenceReport(
            metrics=(
                ProductionMetricDTO(metric_name="workflow_history", observed_value=len(history)),
                ProductionMetricDTO(metric_name="artifacts", observed_value=len(context.artifacts)),
            ),
            pipeline=PipelineInsightDTO(
                current_state=context.state, observed_history_count=len(history)
            ),
            capacity=CapacitySummaryDTO(
                observed_page_count=len(project.pages), observed_chapter_count=len(project.chapters)
            ),
            delivery=DeliveryForecastDTO(basis="local_one_page_observation"),
            health=ProductionHealthDTO(current_state=context.state),
            executive=ProductionExecutiveSummary(
                project_id=project.id, observation_count=observation_count + 1
            ),
        )

    def platform_analytics(
        self, project_id: str, context: WorkflowContext
    ) -> PlatformAnalyticsReport:
        self._repository.load(project_id)
        history = _history_labels(context)
        evidence_count = len(history) + len(context.artifacts)
        return PlatformAnalyticsReport(
            health=PlatformHealthDTO(component_count=4),
            dashboard=AnalyticsDashboardDTO(
                dashboard_id=f"platform-analytics:{project_id}:{_page_reference(context)}",
                report_count=4,
            ),
            trend=TrendSummaryDTO(observed_history_count=len(history)),
            history=HistoricalAnalysisDTO(evidence_count=evidence_count),
            kpis=(
                ExecutiveKPIDTO(metric_name="workflow_evidence", observed_value=len(history)),
                ExecutiveKPIDTO(metric_name="artifact_evidence", observed_value=len(context.artifacts)),
            ),
        )

    def knowledge_graph_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> KnowledgeGraphDashboardDTO:
        return KnowledgeGraphDashboardDTO(report=self.knowledge_graph(project_id, context))

    def creative_intelligence_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> CreativeIntelligenceDashboardDTO:
        return CreativeIntelligenceDashboardDTO(
            report=self.creative_intelligence(project_id, context)
        )

    def production_intelligence_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> ProductionIntelligenceDashboardDTO:
        return ProductionIntelligenceDashboardDTO(
            report=self.production_intelligence(project_id, context)
        )

    def platform_analytics_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> PlatformAnalyticsDashboardDTO:
        return PlatformAnalyticsDashboardDTO(report=self.platform_analytics(project_id, context))


def _page_reference(context: WorkflowContext) -> str:
    return str(context.page.get("id", context.page.get("page_number", "page")))


def _history_labels(context: WorkflowContext) -> tuple[str, ...]:
    history = context.metadata.get("workflow_history", ())
    if not isinstance(history, list | tuple):
        return ()
    return tuple(
        str(entry.get("step", entry.get("to", "workflow")))
        for entry in history
        if isinstance(entry, Mapping)
    )


def _knowledge_categories(metadata: Mapping[str, object], context: WorkflowContext) -> tuple[str, ...]:
    categories = ["project"]
    if metadata:
        categories.append("project_metadata")
    if context.artifacts:
        categories.append("artifact")
    if _history_labels(context):
        categories.append("workflow")
    return tuple(categories)
