"""v5.3 Integration Intelligence contracts."""

from manga_director.platform import (
    ConnectorDescriptorDTO,
    DataExchangeDTO,
    IntegrationEventDTO,
    IntegrationGatewayFoundation,
    IntegrationRegistryFoundation,
    IntegrationRequestDTO,
    UnifiedSDKFoundation,
)


def _request() -> IntegrationRequestDTO:
    return IntegrationRequestDTO(
        connector_id="editor", exchange=DataExchangeDTO(exchange_id="x", schema_reference="v1", data_classification="internal", provenance="caller", page_reference="page-1", approval_boundary="editor"),
        event=IntegrationEventDTO(event_id="e", event_type="review", producer="review", provenance="caller", page_reference="page-1"),
    )


def test_integration_intelligence_is_local_human_gated_and_non_operational() -> None:
    gateway = IntegrationGatewayFoundation(IntegrationRegistryFoundation((ConnectorDescriptorDTO(connector_id="editor", title="Editor", owner="ops"),)))
    dashboard = UnifiedSDKFoundation(integration=gateway).integration_dashboard(_request())
    assert dashboard.health == "ready_for_human_review"
    assert dashboard.connector.connection_started is False
    assert dashboard.exchange.transmission_performed is False
    assert dashboard.event.dispatch_performed is False
    assert dashboard.policy.policy_enforced is False
    assert dashboard.automatic_action_taken is False
