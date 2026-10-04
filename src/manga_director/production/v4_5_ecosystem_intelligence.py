"""v4.5 Creative Intelligence Ecosystem analysis DTOs without side effects.

These Application-layer reports analyze supplied v4.5 foundation evidence.
They cannot register or invoke services, load or execute plugins, operate a
marketplace, synchronize knowledge, connect a federation, mutate a repository,
or change workflow state.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.production.director import DirectorModel
from manga_director.production.v4_5_ecosystem_foundation import (
    CreativeServiceRegistryReport,
    FederationRegistryFoundationReport,
    KnowledgeExchangeFoundationReport,
    PluginFoundationReport,
    V45EcosystemFoundationService,
    WorkflowMarketplaceFoundationReport,
)
from manga_director.workflow.contracts import WorkflowContext


class V45ServiceInsightDTO(DirectorModel):
    service_id: str
    declared_capability_count: int = Field(default=0, ge=0)
    provenance_available: bool = False
    compatibility_status: Literal["not_assessed"] = "not_assessed"
    service_invoked: bool = False


class V45ServiceRecommendationDTO(DirectorModel):
    service_id: str
    message: str = "Require human provenance and compatibility review before any opt-in use."
    registration_enabled: bool = False
    automatic_action_taken: bool = False


class ServiceIntelligenceReport(DirectorModel):
    registry: CreativeServiceRegistryReport
    insight: V45ServiceInsightDTO
    recommendation: V45ServiceRecommendationDTO
    planning_only: bool = True


class V45PluginAnalyticsDTO(DirectorModel):
    plugin_id: str
    declared_capability_count: int = Field(default=0, ge=0)
    provenance_available: bool = False
    isolation_status: Literal["not_reviewed"] = "not_reviewed"
    plugin_loaded: bool = False
    plugin_executed: bool = False


class V45PluginRecommendationDTO(DirectorModel):
    plugin_id: str
    message: str = "Keep Plugin and Extension SDK review human owned."
    permission_granted: bool = False
    automatic_action_taken: bool = False


class PluginAnalyticsReport(DirectorModel):
    foundation: PluginFoundationReport
    analytics: V45PluginAnalyticsDTO
    recommendation: V45PluginRecommendationDTO
    planning_only: bool = True


class V45WorkflowInsightDTO(DirectorModel):
    entry_id: str
    page_count: Literal[1] = 1
    provenance_available: bool = False
    compatibility_status: Literal["not_assessed"] = "not_assessed"
    state_machine_authoritative: bool = True
    workflow_executed: bool = False


class V45WorkflowRecommendationDTO(DirectorModel):
    entry_id: str
    message: str = "Require human review before any separately approved workflow use."
    installation_enabled: bool = False
    automatic_action_taken: bool = False


class WorkflowInsightsReport(DirectorModel):
    marketplace: WorkflowMarketplaceFoundationReport
    insight: V45WorkflowInsightDTO
    recommendation: V45WorkflowRecommendationDTO
    planning_only: bool = True


class V45KnowledgeFederationAnalyticsDTO(DirectorModel):
    exchange_id: str
    domain_id: str
    page_count: Literal[1] = 1
    redaction_required: bool = True
    consent_required: bool = True
    knowledge_synchronized: bool = False
    federation_connected: bool = False


class V45KnowledgeFederationRecommendationDTO(DirectorModel):
    exchange_id: str
    domain_id: str
    message: str = "Require human consent, redaction, and compatibility review."
    sharing_enabled: bool = False
    transport_enabled: bool = False
    automatic_action_taken: bool = False


class KnowledgeFederationAnalyticsReport(DirectorModel):
    exchange: KnowledgeExchangeFoundationReport
    federation: FederationRegistryFoundationReport
    analytics: V45KnowledgeFederationAnalyticsDTO
    recommendation: V45KnowledgeFederationRecommendationDTO
    planning_only: bool = True


class V45EcosystemDashboardDTO(DirectorModel):
    project_id: str
    page_reference: str
    service: ServiceIntelligenceReport
    plugin: PluginAnalyticsReport
    workflow: WorkflowInsightsReport
    knowledge_federation: KnowledgeFederationAnalyticsReport
    dashboard_persisted: bool = False
    dashboard_published: bool = False
    automatic_action_taken: bool = False


class EcosystemDashboardReport(DirectorModel):
    dashboard: V45EcosystemDashboardDTO
    planning_only: bool = True


class V45EcosystemIntelligenceService:
    """Build non-executing v4.5 ecosystem analysis and dashboard projections."""

    def __init__(self, foundation: V45EcosystemFoundationService | None = None) -> None:
        self._foundation = foundation or V45EcosystemFoundationService()

    def service_intelligence(
        self, project_id: str, context: WorkflowContext
    ) -> ServiceIntelligenceReport:
        registry = self._foundation.creative_service_registry(project_id, context)
        service = registry.service
        return ServiceIntelligenceReport(
            registry=registry,
            insight=V45ServiceInsightDTO(
                service_id=service.service_id,
                declared_capability_count=len(registry.capability.declared_capabilities),
                provenance_available=registry.capability.provenance_supplied,
                service_invoked=service.service_invoked,
            ),
            recommendation=V45ServiceRecommendationDTO(service_id=service.service_id),
        )

    def plugin_analytics(self, project_id: str, context: WorkflowContext) -> PluginAnalyticsReport:
        foundation = self._foundation.plugin_foundation(project_id, context)
        plugin = foundation.plugin
        return PluginAnalyticsReport(
            foundation=foundation,
            analytics=V45PluginAnalyticsDTO(
                plugin_id=plugin.plugin_id,
                declared_capability_count=foundation.compatibility.capability_count,
                provenance_available=foundation.compatibility.provenance_supplied,
                plugin_loaded=plugin.plugin_loaded,
                plugin_executed=plugin.plugin_executed,
            ),
            recommendation=V45PluginRecommendationDTO(plugin_id=plugin.plugin_id),
        )

    def workflow_insights(self, project_id: str, context: WorkflowContext) -> WorkflowInsightsReport:
        marketplace = self._foundation.workflow_marketplace(project_id, context)
        return WorkflowInsightsReport(
            marketplace=marketplace,
            insight=V45WorkflowInsightDTO(
                entry_id=marketplace.entry.entry_id,
                provenance_available=marketplace.entry.provenance_supplied,
            ),
            recommendation=V45WorkflowRecommendationDTO(entry_id=marketplace.entry.entry_id),
        )

    def knowledge_federation_analytics(
        self, project_id: str, context: WorkflowContext
    ) -> KnowledgeFederationAnalyticsReport:
        exchange = self._foundation.knowledge_exchange(project_id, context)
        federation = self._foundation.federation_registry(project_id, context)
        return KnowledgeFederationAnalyticsReport(
            exchange=exchange,
            federation=federation,
            analytics=V45KnowledgeFederationAnalyticsDTO(
                exchange_id=exchange.exchange.exchange_id,
                domain_id=federation.domain.domain_id,
            ),
            recommendation=V45KnowledgeFederationRecommendationDTO(
                exchange_id=exchange.exchange.exchange_id,
                domain_id=federation.domain.domain_id,
            ),
        )

    def ecosystem_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> EcosystemDashboardReport:
        service = self.service_intelligence(project_id, context)
        plugin = self.plugin_analytics(project_id, context)
        workflow = self.workflow_insights(project_id, context)
        knowledge_federation = self.knowledge_federation_analytics(project_id, context)
        return EcosystemDashboardReport(
            dashboard=V45EcosystemDashboardDTO(
                project_id=project_id,
                page_reference=service.registry.service.page_reference,
                service=service,
                plugin=plugin,
                workflow=workflow,
                knowledge_federation=knowledge_federation,
            )
        )
