"""v4.8 Unified Platform intelligence DTOs without service orchestration.

These Application-layer reports analyze only the v4.8 caller-supplied
foundation descriptors. They provide deterministic counts, references, and
human-review requirements; they do not route, invoke, schedule, activate, or
replace services, change Runtime behavior, mutate lifecycle state, collect
telemetry, or execute a workflow. The StateMachine remains authoritative.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.production.director import DirectorModel
from manga_director.production.v4_8_unified_foundation import (
    LifecycleManagerFoundationReport,
    ModularRuntimeFoundationReport,
    OperationalIntelligenceFoundationReport,
    ServiceRegistryFoundationReport,
    UnifiedPlatformFoundationReport,
    V48PlatformScopeDTO,
    V48UnifiedPlatformFoundationService,
)
from manga_director.workflow.contracts import WorkflowContext


class V48PlatformAnalyticsDTO(DirectorModel):
    analytics_id: str
    project_id: str
    page_reference: str
    page_count: Literal[1] = 1
    service_count: int = Field(default=0, ge=0)
    module_count: int = Field(default=0, ge=0)
    core_dependency_direction_preserved: bool = True
    integration_analyzed: bool = True
    api_surface_changed: bool = False
    runtime_reconfigured: bool = False


class V48PlatformAnalyticsSummary(DirectorModel):
    supplied_report_count: int = Field(default=2, ge=0)
    coverage_assessed: bool = True
    evidence_persisted: bool = False
    automatic_optimization_applied: bool = False


class UnifiedPlatformAnalyticsReport(DirectorModel):
    platform: UnifiedPlatformFoundationReport
    runtime: ModularRuntimeFoundationReport
    analytics: V48PlatformAnalyticsDTO
    summary: V48PlatformAnalyticsSummary
    planning_only: bool = True


class V48ServiceOrchestrationDTO(DirectorModel):
    orchestration_id: str
    service_ids: tuple[str, ...]
    page_count: Literal[1] = 1
    order_is_advisory: bool = True
    human_review_required: bool = True
    service_invoked: bool = False
    runtime_route_changed: bool = False
    workflow_mutated: bool = False


class V48ServiceOrchestrationSummary(DirectorModel):
    service_count: int = Field(default=0, ge=0)
    compatibility_checked: bool = True
    delegation_created: bool = False
    automatic_action_taken: bool = False


class ServiceOrchestrationReport(DirectorModel):
    registry: ServiceRegistryFoundationReport
    orchestration: V48ServiceOrchestrationDTO
    summary: V48ServiceOrchestrationSummary
    planning_only: bool = True


class V48OperationalInsightDTO(DirectorModel):
    insight_id: str
    domain: str
    status: Literal["unknown", "advisory"] = "unknown"
    evidence_missing: bool = True
    human_review_required: bool = True
    telemetry_collected: bool = False
    operational_action_taken: bool = False


class V48OperationalInsightsSummary(DirectorModel):
    insight_count: int = Field(default=0, ge=0)
    missing_evidence_count: int = Field(default=0, ge=0)
    monitoring_started: bool = False
    alert_sent: bool = False
    optimization_applied: bool = False


class OperationalInsightsReport(DirectorModel):
    operational_intelligence: OperationalIntelligenceFoundationReport
    insights: tuple[V48OperationalInsightDTO, ...]
    summary: V48OperationalInsightsSummary
    planning_only: bool = True


class V48LifecycleAnalyticsDTO(DirectorModel):
    analytics_id: str
    project_id: str
    page_reference: str
    page_count: Literal[1] = 1
    reference_count: int = Field(default=0, ge=0)
    source_module_count: int = Field(default=0, ge=0)
    lifecycle_analyzed: bool = True
    lifecycle_persisted: bool = False
    state_transitioned: bool = False


class V48LifecycleAnalyticsSummary(DirectorModel):
    stage_coverage_assessed: bool = True
    retention_enforced: bool = False
    recovery_attempted: bool = False
    record_mutated: bool = False


class LifecycleAnalyticsReport(DirectorModel):
    lifecycle: LifecycleManagerFoundationReport
    analytics: V48LifecycleAnalyticsDTO
    summary: V48LifecycleAnalyticsSummary
    planning_only: bool = True


class V48UnifiedDashboardDTO(DirectorModel):
    dashboard_id: str
    project_id: str
    page_reference: str
    page_count: Literal[1] = 1
    platform_analytics: UnifiedPlatformAnalyticsReport
    orchestration: ServiceOrchestrationReport
    operational_insights: OperationalInsightsReport
    lifecycle_analytics: LifecycleAnalyticsReport
    public_api_additive: bool = True
    presentation_dependency: bool = False
    dashboard_persisted: bool = False
    dashboard_published: bool = False


class V48UnifiedDashboardSummary(DirectorModel):
    report_count: int = Field(default=4, ge=0)
    human_review_required: bool = True
    cross_domain_action_taken: bool = False
    telemetry_collected: bool = False
    monitoring_started: bool = False


class UnifiedDashboardReport(DirectorModel):
    dashboard: V48UnifiedDashboardDTO
    summary: V48UnifiedDashboardSummary
    planning_only: bool = True


class V48UnifiedPlatformIntelligenceService:
    """Build read-only v4.8 analytics from explicit foundation reports."""

    def __init__(self, foundation: V48UnifiedPlatformFoundationService | None = None) -> None:
        self._foundation = foundation or V48UnifiedPlatformFoundationService()

    def platform_analytics(
        self, project_id: str, context: WorkflowContext
    ) -> UnifiedPlatformAnalyticsReport:
        platform = self._foundation.unified_platform(project_id, context)
        runtime = self._foundation.modular_runtime()
        return UnifiedPlatformAnalyticsReport(
            platform=platform,
            runtime=runtime,
            analytics=V48PlatformAnalyticsDTO(
                analytics_id=f"platform-analytics:{platform.scope.platform_id}",
                project_id=project_id,
                page_reference=platform.scope.page_reference,
                service_count=platform.summary.service_count,
                module_count=runtime.summary.module_count,
            ),
            summary=V48PlatformAnalyticsSummary(),
        )

    def service_orchestration(
        self, project_id: str, context: WorkflowContext
    ) -> ServiceOrchestrationReport:
        registry = self._foundation.service_registry()
        scope = self._scope(project_id, context)
        service_ids = tuple(descriptor.service_id for descriptor in registry.services)
        return ServiceOrchestrationReport(
            registry=registry,
            orchestration=V48ServiceOrchestrationDTO(
                orchestration_id=f"service-orchestration:{scope.platform_id}",
                service_ids=service_ids,
            ),
            summary=V48ServiceOrchestrationSummary(service_count=len(service_ids)),
        )

    def operational_insights(
        self, project_id: str, context: WorkflowContext
    ) -> OperationalInsightsReport:
        operational_intelligence = self._foundation.operational_intelligence(project_id, context)
        insights = tuple(
            V48OperationalInsightDTO(
                insight_id=f"operational-insight:{signal.signal_id}",
                domain=signal.domain,
                status=signal.status,
                evidence_missing=not signal.evidence_supplied,
            )
            for signal in operational_intelligence.signals
        )
        return OperationalInsightsReport(
            operational_intelligence=operational_intelligence,
            insights=insights,
            summary=V48OperationalInsightsSummary(
                insight_count=len(insights),
                missing_evidence_count=sum(insight.evidence_missing for insight in insights),
            ),
        )

    def lifecycle_analytics(
        self, project_id: str, context: WorkflowContext
    ) -> LifecycleAnalyticsReport:
        lifecycle = self._foundation.lifecycle_manager(project_id, context)
        source_module_count = len({reference.source_module for reference in lifecycle.references})
        return LifecycleAnalyticsReport(
            lifecycle=lifecycle,
            analytics=V48LifecycleAnalyticsDTO(
                analytics_id=f"lifecycle-analytics:{lifecycle.scope.platform_id}",
                project_id=project_id,
                page_reference=lifecycle.scope.page_reference,
                reference_count=lifecycle.summary.reference_count,
                source_module_count=source_module_count,
            ),
            summary=V48LifecycleAnalyticsSummary(),
        )

    def unified_dashboard(self, project_id: str, context: WorkflowContext) -> UnifiedDashboardReport:
        platform_analytics = self.platform_analytics(project_id, context)
        orchestration = self.service_orchestration(project_id, context)
        operational_insights = self.operational_insights(project_id, context)
        lifecycle_analytics = self.lifecycle_analytics(project_id, context)
        scope = self._scope(project_id, context)
        return UnifiedDashboardReport(
            dashboard=V48UnifiedDashboardDTO(
                dashboard_id=f"unified-dashboard:{scope.platform_id}",
                project_id=project_id,
                page_reference=scope.page_reference,
                platform_analytics=platform_analytics,
                orchestration=orchestration,
                operational_insights=operational_insights,
                lifecycle_analytics=lifecycle_analytics,
            ),
            summary=V48UnifiedDashboardSummary(),
        )

    def _scope(self, project_id: str, context: WorkflowContext) -> V48PlatformScopeDTO:
        return self._foundation.unified_platform(project_id, context).scope
