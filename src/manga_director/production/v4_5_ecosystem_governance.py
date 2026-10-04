"""v4.5 ecosystem governance, trust, and reliability DTOs.

The reports are immutable Application-layer diagnostics over v4.5 ecosystem
intelligence. They cannot enforce policy, register or invoke services, load or
execute plugins, operate a marketplace, synchronize knowledge, connect a
federation, monitor, recover, bill, or call an external service.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.production.director import DirectorModel
from manga_director.production.v4_5_ecosystem_intelligence import (
    EcosystemDashboardReport,
    KnowledgeFederationAnalyticsReport,
    PluginAnalyticsReport,
    ServiceIntelligenceReport,
    V45EcosystemIntelligenceService,
)
from manga_director.workflow.contracts import WorkflowContext


class V45EcosystemPolicyDTO(DirectorModel):
    policy_id: str
    project_id: str
    page_reference: str
    state_machine_authoritative: bool = True
    human_approval_required: bool = True
    policy_enforced: bool = False
    policy_persisted: bool = False


class V45EcosystemComplianceDTO(DirectorModel):
    policy_id: str
    page_count: Literal[1] = 1
    storyboard_evidence_required: bool = True
    completed_quality_review_required: bool = True
    compliance_confirmed: bool = False
    workflow_changed: bool = False


class V45EcosystemGovernanceSummary(DirectorModel):
    policy_count: int = Field(default=1, ge=0)
    compliance_count: int = Field(default=1, ge=0)
    enforcement_action_count: int = 0
    automatic_action_taken: bool = False


class EcosystemGovernanceReport(DirectorModel):
    dashboard: EcosystemDashboardReport
    policy: V45EcosystemPolicyDTO
    compliance: V45EcosystemComplianceDTO
    summary: V45EcosystemGovernanceSummary
    planning_only: bool = True


class V45ServiceTrustDTO(DirectorModel):
    service_id: str
    trust_level: Literal["not_established"] = "not_established"
    provenance_reviewed: bool = False
    compatibility_confirmed: bool = False
    human_trust_required: bool = True
    service_invoked: bool = False


class V45ServiceTrustSummary(DirectorModel):
    service_count: int = Field(default=1, ge=0)
    trust_granted_count: int = 0
    automatic_action_taken: bool = False


class ServiceTrustFrameworkReport(DirectorModel):
    service: ServiceIntelligenceReport
    trust: V45ServiceTrustDTO
    summary: V45ServiceTrustSummary
    planning_only: bool = True


class V45PluginPolicyDTO(DirectorModel):
    policy_id: str
    plugin_id: str
    extension_sdk_contract: Literal["existing_sdk_unchanged"] = "existing_sdk_unchanged"
    human_review_required: bool = True
    policy_enforced: bool = False


class V45PluginComplianceDTO(DirectorModel):
    plugin_id: str
    provenance_reviewed: bool = False
    isolation_confirmed: bool = False
    compliance_confirmed: bool = False
    permission_granted: bool = False
    plugin_executed: bool = False


class PluginGovernanceReport(DirectorModel):
    plugin: PluginAnalyticsReport
    policy: V45PluginPolicyDTO
    compliance: V45PluginComplianceDTO
    planning_only: bool = True


class V45KnowledgeFederationPolicyDTO(DirectorModel):
    policy_id: str
    exchange_id: str
    domain_id: str
    redaction_required: bool = True
    human_consent_required: bool = True
    policy_enforced: bool = False


class V45KnowledgeFederationComplianceDTO(DirectorModel):
    exchange_id: str
    domain_id: str
    consent_confirmed: bool = False
    sharing_approved: bool = False
    knowledge_synchronized: bool = False
    federation_connected: bool = False


class KnowledgeFederationGovernanceReport(DirectorModel):
    analytics: KnowledgeFederationAnalyticsReport
    policy: V45KnowledgeFederationPolicyDTO
    compliance: V45KnowledgeFederationComplianceDTO
    planning_only: bool = True


class V45EcosystemReliabilityDTO(DirectorModel):
    reliability_id: str
    project_id: str
    page_reference: str
    health_status: Literal["not_checked"] = "not_checked"
    health_check_executed: bool = False
    incident_detected: bool = False
    monitoring_active: bool = False
    alert_sent: bool = False
    recovery_attempted: bool = False
    recovery_completed: bool = False


class V45EcosystemReliabilitySummary(DirectorModel):
    observed_component_count: int = Field(default=5, ge=0)
    incident_count: int = 0
    recovery_count: int = 0
    automatic_action_taken: bool = False


class EcosystemReliabilityReport(DirectorModel):
    dashboard: EcosystemDashboardReport
    reliability: V45EcosystemReliabilityDTO
    summary: V45EcosystemReliabilitySummary
    planning_only: bool = True


class EcosystemOperationsValidationReport(DirectorModel):
    governance: EcosystemGovernanceReport
    service_trust: ServiceTrustFrameworkReport
    plugin: PluginGovernanceReport
    knowledge_federation: KnowledgeFederationGovernanceReport
    reliability: EcosystemReliabilityReport
    end_to_end_validated: bool = True
    workflow_executed: bool = False
    planning_only: bool = True


class V45EcosystemGovernanceService:
    """Build non-enforcing v4.5 ecosystem operations evidence reports."""

    def __init__(self, intelligence: V45EcosystemIntelligenceService | None = None) -> None:
        self._intelligence = intelligence or V45EcosystemIntelligenceService()

    def ecosystem_governance(
        self, project_id: str, context: WorkflowContext
    ) -> EcosystemGovernanceReport:
        dashboard = self._intelligence.ecosystem_dashboard(project_id, context)
        page_reference = dashboard.dashboard.page_reference
        policy_id = f"ecosystem-policy:{project_id}:{page_reference}"
        return EcosystemGovernanceReport(
            dashboard=dashboard,
            policy=V45EcosystemPolicyDTO(
                policy_id=policy_id,
                project_id=project_id,
                page_reference=page_reference,
            ),
            compliance=V45EcosystemComplianceDTO(policy_id=policy_id),
            summary=V45EcosystemGovernanceSummary(),
        )

    def service_trust_framework(
        self, project_id: str, context: WorkflowContext
    ) -> ServiceTrustFrameworkReport:
        service = self._intelligence.service_intelligence(project_id, context)
        return ServiceTrustFrameworkReport(
            service=service,
            trust=V45ServiceTrustDTO(service_id=service.insight.service_id),
            summary=V45ServiceTrustSummary(),
        )

    def plugin_governance(self, project_id: str, context: WorkflowContext) -> PluginGovernanceReport:
        plugin = self._intelligence.plugin_analytics(project_id, context)
        plugin_id = plugin.analytics.plugin_id
        return PluginGovernanceReport(
            plugin=plugin,
            policy=V45PluginPolicyDTO(
                policy_id=f"plugin-policy:{project_id}", plugin_id=plugin_id
            ),
            compliance=V45PluginComplianceDTO(plugin_id=plugin_id),
        )

    def knowledge_federation_governance(
        self, project_id: str, context: WorkflowContext
    ) -> KnowledgeFederationGovernanceReport:
        analytics = self._intelligence.knowledge_federation_analytics(project_id, context)
        exchange_id = analytics.analytics.exchange_id
        domain_id = analytics.analytics.domain_id
        return KnowledgeFederationGovernanceReport(
            analytics=analytics,
            policy=V45KnowledgeFederationPolicyDTO(
                policy_id=f"knowledge-federation-policy:{project_id}",
                exchange_id=exchange_id,
                domain_id=domain_id,
            ),
            compliance=V45KnowledgeFederationComplianceDTO(
                exchange_id=exchange_id, domain_id=domain_id
            ),
        )

    def ecosystem_reliability(
        self, project_id: str, context: WorkflowContext
    ) -> EcosystemReliabilityReport:
        dashboard = self._intelligence.ecosystem_dashboard(project_id, context)
        return EcosystemReliabilityReport(
            dashboard=dashboard,
            reliability=V45EcosystemReliabilityDTO(
                reliability_id=f"ecosystem-reliability:{project_id}",
                project_id=project_id,
                page_reference=dashboard.dashboard.page_reference,
            ),
            summary=V45EcosystemReliabilitySummary(),
        )

    def operations_validation(
        self, project_id: str, context: WorkflowContext
    ) -> EcosystemOperationsValidationReport:
        return EcosystemOperationsValidationReport(
            governance=self.ecosystem_governance(project_id, context),
            service_trust=self.service_trust_framework(project_id, context),
            plugin=self.plugin_governance(project_id, context),
            knowledge_federation=self.knowledge_federation_governance(project_id, context),
            reliability=self.ecosystem_reliability(project_id, context),
        )
