"""v4.5 Creative Intelligence Ecosystem foundation DTOs without side effects.

The module provides immutable Application-layer projections for supplied
creative-service, plugin, workflow-marketplace, knowledge-exchange, and
federation evidence. It cannot register, discover, persist, load, execute,
install, synchronize, authenticate, communicate, publish, bill, or call an
external service. The domain StateMachine remains the transition authority.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.production.director import DirectorModel
from manga_director.workflow.contracts import WorkflowContext


class V45CreativeServiceDTO(DirectorModel):
    service_id: str
    project_id: str
    page_reference: str
    page_count: Literal[1] = 1
    service_registered: bool = False
    service_invoked: bool = False


class V45ServiceCapabilityDTO(DirectorModel):
    service_id: str
    declared_capabilities: tuple[str, ...] = ()
    provenance_supplied: bool = False
    compatibility_assessed: bool = False


class V45ServiceRegistryDTO(DirectorModel):
    registry_id: str
    service_ids: tuple[str, ...] = ()
    registry_persisted: bool = False
    remote_discovery_enabled: bool = False


class V45ServiceRegistrySummary(DirectorModel):
    service_count: int = Field(default=1, ge=0)
    invoked_service_count: int = 0
    automatic_action_taken: bool = False


class CreativeServiceRegistryReport(DirectorModel):
    service: V45CreativeServiceDTO
    capability: V45ServiceCapabilityDTO
    registry: V45ServiceRegistryDTO
    summary: V45ServiceRegistrySummary
    planning_only: bool = True


class V45PluginDTO(DirectorModel):
    plugin_id: str
    extension_sdk_contract: Literal["existing_sdk_unchanged"] = "existing_sdk_unchanged"
    declared_version: str = "not_loaded"
    plugin_loaded: bool = False
    plugin_executed: bool = False


class V45PluginCompatibilityDTO(DirectorModel):
    plugin_id: str
    capability_count: int = Field(default=0, ge=0)
    provenance_supplied: bool = False
    isolation_reviewed: bool = False
    permission_granted: bool = False


class V45PluginRegistryDTO(DirectorModel):
    registry_id: str
    plugin_ids: tuple[str, ...] = ()
    registry_persisted: bool = False
    remote_discovery_enabled: bool = False


class V45PluginFoundationSummary(DirectorModel):
    plugin_count: int = Field(default=1, ge=0)
    loaded_plugin_count: int = 0
    executed_plugin_count: int = 0
    automatic_action_taken: bool = False


class PluginFoundationReport(DirectorModel):
    plugin: V45PluginDTO
    compatibility: V45PluginCompatibilityDTO
    registry: V45PluginRegistryDTO
    summary: V45PluginFoundationSummary
    planning_only: bool = True


class V45WorkflowMarketplaceDTO(DirectorModel):
    catalog_id: str
    entry_ids: tuple[str, ...] = ()
    catalog_persisted: bool = False
    remote_discovery_enabled: bool = False


class V45WorkflowMarketplaceEntryDTO(DirectorModel):
    entry_id: str
    workflow_id: str = "not_installed"
    page_count: Literal[1] = 1
    provenance_supplied: bool = False
    downloaded: bool = False
    installed: bool = False
    executed: bool = False


class V45WorkflowMarketplacePolicyDTO(DirectorModel):
    entry_id: str
    human_review_required: bool = True
    state_machine_authoritative: bool = True
    policy_enforced: bool = False
    published: bool = False
    payment_processed: bool = False
    billing_performed: bool = False


class V45WorkflowMarketplaceSummary(DirectorModel):
    entry_count: int = Field(default=1, ge=0)
    installed_entry_count: int = 0
    executed_entry_count: int = 0
    automatic_action_taken: bool = False


class WorkflowMarketplaceFoundationReport(DirectorModel):
    marketplace: V45WorkflowMarketplaceDTO
    entry: V45WorkflowMarketplaceEntryDTO
    policy: V45WorkflowMarketplacePolicyDTO
    summary: V45WorkflowMarketplaceSummary
    planning_only: bool = True


class V45KnowledgeExchangeDTO(DirectorModel):
    exchange_id: str
    project_id: str
    page_reference: str
    page_count: Literal[1] = 1
    namespace: str = "local"
    exchange_persisted: bool = False
    synchronized: bool = False


class V45KnowledgeExchangeDescriptorDTO(DirectorModel):
    exchange_id: str
    schema_reference: str = "not_supplied"
    provenance_supplied: bool = False
    redaction_required: bool = True
    ownership_transfered: bool = False


class V45KnowledgeExchangePolicyDTO(DirectorModel):
    exchange_id: str
    human_consent_required: bool = True
    quality_review_required: bool = True
    sharing_approved: bool = False
    remote_search_enabled: bool = False


class V45KnowledgeExchangeSummary(DirectorModel):
    exchange_count: int = Field(default=1, ge=0)
    synchronized_exchange_count: int = 0
    automatic_action_taken: bool = False


class KnowledgeExchangeFoundationReport(DirectorModel):
    exchange: V45KnowledgeExchangeDTO
    descriptor: V45KnowledgeExchangeDescriptorDTO
    policy: V45KnowledgeExchangePolicyDTO
    summary: V45KnowledgeExchangeSummary
    planning_only: bool = True


class V45FederationDomainDTO(DirectorModel):
    domain_id: str
    project_id: str
    page_reference: str
    page_count: Literal[1] = 1
    domain_registered: bool = False
    network_connected: bool = False


class V45FederationPeerDTO(DirectorModel):
    peer_id: str
    domain_id: str
    capability_handshake_supplied: bool = False
    compatibility_assessed: bool = False
    authenticated: bool = False
    transport_connected: bool = False


class V45FederationRegistryDTO(DirectorModel):
    registry_id: str
    peer_ids: tuple[str, ...] = ()
    registry_persisted: bool = False
    federation_enabled: bool = False


class V45FederationRegistrySummary(DirectorModel):
    domain_count: int = Field(default=1, ge=0)
    peer_count: int = Field(default=1, ge=0)
    connected_peer_count: int = 0
    automatic_action_taken: bool = False


class FederationRegistryFoundationReport(DirectorModel):
    domain: V45FederationDomainDTO
    peer: V45FederationPeerDTO
    registry: V45FederationRegistryDTO
    summary: V45FederationRegistrySummary
    planning_only: bool = True


class V45EcosystemFoundationService:
    """Build non-executing v4.5 ecosystem foundation projections."""

    def creative_service_registry(
        self, project_id: str, context: WorkflowContext
    ) -> CreativeServiceRegistryReport:
        page_reference = _page_reference(context)
        service_id = f"creative-service:{project_id}:{page_reference}"
        return CreativeServiceRegistryReport(
            service=V45CreativeServiceDTO(
                service_id=service_id,
                project_id=project_id,
                page_reference=page_reference,
            ),
            capability=V45ServiceCapabilityDTO(service_id=service_id),
            registry=V45ServiceRegistryDTO(
                registry_id=f"creative-service-registry:{project_id}", service_ids=(service_id,)
            ),
            summary=V45ServiceRegistrySummary(),
        )

    def plugin_foundation(self, project_id: str, context: WorkflowContext) -> PluginFoundationReport:
        plugin_id = f"plugin:{project_id}:{_page_reference(context)}"
        return PluginFoundationReport(
            plugin=V45PluginDTO(plugin_id=plugin_id),
            compatibility=V45PluginCompatibilityDTO(plugin_id=plugin_id),
            registry=V45PluginRegistryDTO(
                registry_id=f"plugin-registry:{project_id}", plugin_ids=(plugin_id,)
            ),
            summary=V45PluginFoundationSummary(),
        )

    def workflow_marketplace(
        self, project_id: str, context: WorkflowContext
    ) -> WorkflowMarketplaceFoundationReport:
        page_reference = _page_reference(context)
        entry_id = f"workflow-marketplace-entry:{project_id}:{page_reference}"
        return WorkflowMarketplaceFoundationReport(
            marketplace=V45WorkflowMarketplaceDTO(
                catalog_id=f"workflow-marketplace:{project_id}", entry_ids=(entry_id,)
            ),
            entry=V45WorkflowMarketplaceEntryDTO(entry_id=entry_id),
            policy=V45WorkflowMarketplacePolicyDTO(entry_id=entry_id),
            summary=V45WorkflowMarketplaceSummary(),
        )

    def knowledge_exchange(
        self, project_id: str, context: WorkflowContext
    ) -> KnowledgeExchangeFoundationReport:
        page_reference = _page_reference(context)
        exchange_id = f"knowledge-exchange:{project_id}:{page_reference}"
        return KnowledgeExchangeFoundationReport(
            exchange=V45KnowledgeExchangeDTO(
                exchange_id=exchange_id,
                project_id=project_id,
                page_reference=page_reference,
            ),
            descriptor=V45KnowledgeExchangeDescriptorDTO(exchange_id=exchange_id),
            policy=V45KnowledgeExchangePolicyDTO(exchange_id=exchange_id),
            summary=V45KnowledgeExchangeSummary(),
        )

    def federation_registry(
        self, project_id: str, context: WorkflowContext
    ) -> FederationRegistryFoundationReport:
        page_reference = _page_reference(context)
        domain_id = f"federation-domain:{project_id}"
        peer_id = f"federation-peer:{project_id}:{page_reference}"
        return FederationRegistryFoundationReport(
            domain=V45FederationDomainDTO(
                domain_id=domain_id,
                project_id=project_id,
                page_reference=page_reference,
            ),
            peer=V45FederationPeerDTO(peer_id=peer_id, domain_id=domain_id),
            registry=V45FederationRegistryDTO(
                registry_id=f"federation-registry:{project_id}", peer_ids=(peer_id,)
            ),
            summary=V45FederationRegistrySummary(),
        )


def _page_reference(context: WorkflowContext) -> str:
    page_id = context.page.get("id")
    return str(page_id) if page_id is not None else "page"
