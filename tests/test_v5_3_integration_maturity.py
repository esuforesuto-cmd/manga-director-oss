"""v5.3 Integration Governance contracts."""

from manga_director.platform import (
    ConnectorDescriptorDTO,
    DataExchangeDTO,
    IntegrationEventDTO,
    IntegrationGatewayFoundation,
    IntegrationPlatformMaturityService,
    IntegrationRegistryFoundation,
    IntegrationRequestDTO,
)


def test_integration_maturity_is_non_enforcing_non_operational_and_human_gated() -> None:
    gateway = IntegrationGatewayFoundation(IntegrationRegistryFoundation((ConnectorDescriptorDTO(connector_id="c", title="C", owner="ops"),)))
    request = IntegrationRequestDTO(connector_id="c", exchange=DataExchangeDTO(exchange_id="x", schema_reference="v1", data_classification="internal", provenance="caller", page_reference="p", approval_boundary="human"), event=IntegrationEventDTO(event_id="e", event_type="review", producer="review", provenance="caller", page_reference="p"))
    report = IntegrationPlatformMaturityService(gateway).report(request)
    assert report.governance.policy_enforced is False
    assert report.security.credentials_loaded is False
    assert report.observability.monitoring_started is False
    assert report.reliability.recovery_attempted is False
    assert report.lifecycle.lifecycle_transitioned is False
    assert report.automatic_action_taken is False
