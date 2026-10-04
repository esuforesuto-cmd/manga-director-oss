"""v4.8 Creative Operating System governance DTOs without operations control.

The reports compose v4.8 Unified Platform Intelligence into policy,
observability, reliability, and lifecycle evidence for exactly one existing
Page. They cannot enforce policy, register or invoke services, collect
telemetry, monitor, alert, retry, recover, persist evidence, alter Runtime, or
mutate/execute a workflow. The StateMachine remains the transition authority.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.production.director import DirectorModel
from manga_director.production.v4_8_unified_intelligence import (
    LifecycleAnalyticsReport,
    OperationalInsightsReport,
    ServiceOrchestrationReport,
    UnifiedDashboardReport,
    V48UnifiedPlatformIntelligenceService,
)
from manga_director.workflow.contracts import WorkflowContext


class V48PlatformPolicyDTO(DirectorModel):
    policy_id: str
    project_id: str
    page_reference: str
    page_count: Literal[1] = 1
    state_machine_authoritative: bool = True
    persisted_storyboard_required: bool = True
    completed_quality_review_required: bool = True
    human_approval_required: bool = True
    policy_enforced: bool = False
    policy_persisted: bool = False


class V48PlatformComplianceDTO(DirectorModel):
    policy_id: str
    project_id: str
    page_count: Literal[1] = 1
    workflow_invariants_verified: bool = False
    api_compatibility_verified: bool = False
    runtime_compatibility_verified: bool = False
    compliance_confirmed: bool = False
    enforcement_action_taken: bool = False


class V48PlatformGovernanceSummary(DirectorModel):
    policy_count: int = Field(default=1, ge=0)
    compliance_count: int = Field(default=1, ge=0)
    human_review_required: bool = True
    automatic_action_taken: bool = False


class UnifiedPlatformGovernanceReport(DirectorModel):
    dashboard: UnifiedDashboardReport
    policy: V48PlatformPolicyDTO
    compliance: V48PlatformComplianceDTO
    summary: V48PlatformGovernanceSummary
    planning_only: bool = True


class V48ServiceGovernanceDTO(DirectorModel):
    governance_id: str
    service_ids: tuple[str, ...]
    page_count: Literal[1] = 1
    contract_preservation_required: bool = True
    human_review_required: bool = True
    service_discovered: bool = False
    service_invoked: bool = False
    service_routed: bool = False
    governance_enforced: bool = False


class V48ServiceGovernanceSummary(DirectorModel):
    service_count: int = Field(default=0, ge=0)
    compatibility_review_required: bool = True
    permission_granted: bool = False
    automatic_action_taken: bool = False


class ServiceGovernanceReport(DirectorModel):
    orchestration: ServiceOrchestrationReport
    governance: V48ServiceGovernanceDTO
    summary: V48ServiceGovernanceSummary
    planning_only: bool = True


class V48PlatformObservationDTO(DirectorModel):
    observation_id: str
    project_id: str
    page_reference: str
    page_count: Literal[1] = 1
    observed_report_count: int = Field(default=4, ge=0)
    explicit_evidence_required: bool = True
    telemetry_collected: bool = False
    health_probe_executed: bool = False
    monitoring_active: bool = False
    alert_sent: bool = False


class V48PlatformObservabilitySummary(DirectorModel):
    visibility_composed: bool = True
    dashboard_persisted: bool = False
    dashboard_published: bool = False
    operational_action_taken: bool = False


class PlatformObservabilityReport(DirectorModel):
    dashboard: UnifiedDashboardReport
    observation: V48PlatformObservationDTO
    summary: V48PlatformObservabilitySummary
    planning_only: bool = True


class V48OperationalReliabilityDTO(DirectorModel):
    reliability_id: str
    project_id: str
    page_reference: str
    page_count: Literal[1] = 1
    component_count: int = Field(default=6, ge=0)
    health_status: Literal["not_checked"] = "not_checked"
    health_check_executed: bool = False
    failure_detected: bool = False
    retry_attempted: bool = False
    recovery_attempted: bool = False
    runtime_reconfigured: bool = False


class V48OperationalReliabilitySummary(DirectorModel):
    incident_count: int = Field(default=0, ge=0)
    recovery_count: int = Field(default=0, ge=0)
    human_intervention_required: bool = True
    automatic_action_taken: bool = False


class OperationalReliabilityReport(DirectorModel):
    operational_insights: OperationalInsightsReport
    reliability: V48OperationalReliabilityDTO
    summary: V48OperationalReliabilitySummary
    planning_only: bool = True


class V48LifecyclePolicyDTO(DirectorModel):
    policy_id: str
    project_id: str
    page_reference: str
    page_count: Literal[1] = 1
    source_provenance_required: bool = True
    state_machine_authoritative: bool = True
    retention_enforced: bool = False
    lifecycle_persisted: bool = False
    state_transitioned: bool = False


class V48LifecycleGovernanceSummary(DirectorModel):
    reference_count: int = Field(default=0, ge=0)
    compliance_review_required: bool = True
    record_mutated: bool = False
    automatic_action_taken: bool = False


class LifecycleGovernanceReport(DirectorModel):
    lifecycle_analytics: LifecycleAnalyticsReport
    policy: V48LifecyclePolicyDTO
    summary: V48LifecycleGovernanceSummary
    planning_only: bool = True


class V48CreativeOperatingSystemSummary(DirectorModel):
    report_count: int = Field(default=5, ge=0)
    enterprise_readiness_assessed: bool = False
    oss_readiness_assessed: bool = False
    presentation_dependency: bool = False
    automatic_action_taken: bool = False


class CreativeOperatingSystemReport(DirectorModel):
    platform_governance: UnifiedPlatformGovernanceReport
    service_governance: ServiceGovernanceReport
    observability: PlatformObservabilityReport
    reliability: OperationalReliabilityReport
    lifecycle_governance: LifecycleGovernanceReport
    summary: V48CreativeOperatingSystemSummary
    planning_only: bool = True


class V48CreativeOperatingSystemGovernanceService:
    """Build diagnostic v4.8 operations evidence without enforcing or acting."""

    def __init__(self, intelligence: V48UnifiedPlatformIntelligenceService | None = None) -> None:
        self._intelligence = intelligence or V48UnifiedPlatformIntelligenceService()

    def platform_governance(
        self, project_id: str, context: WorkflowContext
    ) -> UnifiedPlatformGovernanceReport:
        dashboard = self._intelligence.unified_dashboard(project_id, context)
        policy_id = f"platform-policy:{dashboard.dashboard.dashboard_id}"
        return UnifiedPlatformGovernanceReport(
            dashboard=dashboard,
            policy=V48PlatformPolicyDTO(
                policy_id=policy_id,
                project_id=project_id,
                page_reference=dashboard.dashboard.page_reference,
            ),
            compliance=V48PlatformComplianceDTO(policy_id=policy_id, project_id=project_id),
            summary=V48PlatformGovernanceSummary(),
        )

    def service_governance(
        self, project_id: str, context: WorkflowContext
    ) -> ServiceGovernanceReport:
        orchestration = self._intelligence.service_orchestration(project_id, context)
        return ServiceGovernanceReport(
            orchestration=orchestration,
            governance=V48ServiceGovernanceDTO(
                governance_id=f"service-governance:{orchestration.orchestration.orchestration_id}",
                service_ids=orchestration.orchestration.service_ids,
            ),
            summary=V48ServiceGovernanceSummary(
                service_count=orchestration.summary.service_count
            ),
        )

    def observability(self, project_id: str, context: WorkflowContext) -> PlatformObservabilityReport:
        dashboard = self._intelligence.unified_dashboard(project_id, context)
        return PlatformObservabilityReport(
            dashboard=dashboard,
            observation=V48PlatformObservationDTO(
                observation_id=f"platform-observation:{dashboard.dashboard.dashboard_id}",
                project_id=project_id,
                page_reference=dashboard.dashboard.page_reference,
            ),
            summary=V48PlatformObservabilitySummary(),
        )

    def operational_reliability(
        self, project_id: str, context: WorkflowContext
    ) -> OperationalReliabilityReport:
        operational_insights = self._intelligence.operational_insights(project_id, context)
        page_reference = operational_insights.operational_intelligence.scope.page_reference
        return OperationalReliabilityReport(
            operational_insights=operational_insights,
            reliability=V48OperationalReliabilityDTO(
                reliability_id=f"operational-reliability:{project_id}:{page_reference}",
                project_id=project_id,
                page_reference=page_reference,
            ),
            summary=V48OperationalReliabilitySummary(),
        )

    def lifecycle_governance(
        self, project_id: str, context: WorkflowContext
    ) -> LifecycleGovernanceReport:
        lifecycle_analytics = self._intelligence.lifecycle_analytics(project_id, context)
        analytics = lifecycle_analytics.analytics
        return LifecycleGovernanceReport(
            lifecycle_analytics=lifecycle_analytics,
            policy=V48LifecyclePolicyDTO(
                policy_id=f"lifecycle-policy:{analytics.analytics_id}",
                project_id=project_id,
                page_reference=analytics.page_reference,
            ),
            summary=V48LifecycleGovernanceSummary(reference_count=analytics.reference_count),
        )

    def creative_operating_system(
        self, project_id: str, context: WorkflowContext
    ) -> CreativeOperatingSystemReport:
        return CreativeOperatingSystemReport(
            platform_governance=self.platform_governance(project_id, context),
            service_governance=self.service_governance(project_id, context),
            observability=self.observability(project_id, context),
            reliability=self.operational_reliability(project_id, context),
            lifecycle_governance=self.lifecycle_governance(project_id, context),
            summary=V48CreativeOperatingSystemSummary(),
        )
