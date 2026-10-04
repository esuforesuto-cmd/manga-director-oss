"""Contracts for the non-operational v5.3 Integration Foundation."""

from __future__ import annotations

import pytest

from manga_director.platform import (
    ConnectorDescriptorDTO,
    ConnectorSDKFoundation,
    DataExchangeDTO,
    DataExchangeFoundation,
    EventIntegrationFoundation,
    IntegrationEventDTO,
    IntegrationGatewayFoundation,
    IntegrationRegistryFoundation,
    IntegrationRequestDTO,
    UnifiedSDKFoundation,
)


def _connector() -> ConnectorDescriptorDTO:
    return ConnectorDescriptorDTO(
        connector_id="editor-export", title="Editor Export", owner="creative-ops"
    )


def _exchange() -> DataExchangeDTO:
    return DataExchangeDTO(
        exchange_id="exchange-1", schema_reference="creative/v1", data_classification="internal",
        provenance="caller", page_reference="page-001", approval_boundary="editor-review"
    )


def _event() -> IntegrationEventDTO:
    return IntegrationEventDTO(
        event_id="reviewed", event_type="review.completed", producer="review",
        provenance="caller", page_reference="page-001"
    )


def test_connector_sdk_is_descriptor_only() -> None:
    report = ConnectorSDKFoundation().validate(_connector())
    assert report.valid and report.invocation_performed is False


def test_data_exchange_requires_human_boundary_and_never_transmits() -> None:
    report = DataExchangeFoundation().validate(_exchange())
    assert report.valid and report.transmission_performed is False
    assert not DataExchangeFoundation().validate(_exchange().model_copy(update={"approval_boundary": None})).valid


def test_event_integration_never_dispatches() -> None:
    report = EventIntegrationFoundation().validate(_event())
    assert report.valid and report.dispatch_performed is False


def test_registry_is_local_and_rejects_duplicate_connector() -> None:
    registry = IntegrationRegistryFoundation((_connector(),))
    assert registry.report().external_discovery_performed is False
    with pytest.raises(ValueError, match="duplicate connector"):
        registry.register(_connector())


def test_gateway_and_sdk_are_human_gated_and_non_executing() -> None:
    gateway = IntegrationGatewayFoundation(IntegrationRegistryFoundation((_connector(),)))
    request = IntegrationRequestDTO(connector_id="editor-export", exchange=_exchange(), event=_event())
    report = UnifiedSDKFoundation(integration=gateway).integration_preview(request)
    assert report.eligible_for_human_review
    assert report.execution_performed is False
    assert report.state_machine_authoritative is True
