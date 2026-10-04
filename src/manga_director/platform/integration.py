"""v5.3 local, human-gated Integration Framework foundations.

No type in this module connects, sends, receives, persists, dispatches, or
mutates data or workflow state. StateMachine ownership remains unchanged.
"""

from __future__ import annotations

from pydantic import Field

from manga_director.production.director import DirectorModel


class ConnectorDescriptorDTO(DirectorModel):
    connector_id: str
    title: str
    owner: str
    capabilities: tuple[str, ...] = ()
    compatibility: str = ">=5.0,<6.0"
    human_review_required: bool = True
    connection_started: bool = False
    credentials_loaded: bool = False


class DataExchangeDTO(DirectorModel):
    exchange_id: str
    schema_reference: str
    data_classification: str
    provenance: str
    page_reference: str
    approval_boundary: str | None = None
    transmitted: bool = False
    persisted: bool = False


class IntegrationEventDTO(DirectorModel):
    event_id: str
    event_type: str
    producer: str
    provenance: str
    page_reference: str
    correlation_id: str | None = None
    dispatched: bool = False


class IntegrationRegistryReport(DirectorModel):
    connectors: tuple[ConnectorDescriptorDTO, ...] = ()
    connector_count: int = Field(default=0, ge=0)
    external_discovery_performed: bool = False
    runtime_changed: bool = False
    planning_only: bool = True


class IntegrationRegistryFoundation:
    def __init__(self, connectors: tuple[ConnectorDescriptorDTO, ...] = ()) -> None:
        self._connectors = {item.connector_id: item for item in connectors}
        if len(self._connectors) != len(connectors):
            raise ValueError("duplicate connector descriptor")

    def register(self, connector: ConnectorDescriptorDTO) -> None:
        if connector.connector_id in self._connectors:
            raise ValueError(f"duplicate connector descriptor: {connector.connector_id}")
        self._connectors[connector.connector_id] = connector

    def report(self) -> IntegrationRegistryReport:
        connectors = tuple(self._connectors[key] for key in sorted(self._connectors))
        return IntegrationRegistryReport(connectors=connectors, connector_count=len(connectors))


class ConnectorSDKReport(DirectorModel):
    connector: ConnectorDescriptorDTO
    valid: bool
    findings: tuple[str, ...] = ()
    invocation_performed: bool = False
    planning_only: bool = True


class ConnectorSDKFoundation:
    def validate(self, connector: ConnectorDescriptorDTO) -> ConnectorSDKReport:
        findings: list[str] = []
        if not connector.owner:
            findings.append("connector owner is required")
        if not connector.human_review_required:
            findings.append("human review is required")
        if connector.connection_started or connector.credentials_loaded:
            findings.append("connector must remain non-operational")
        return ConnectorSDKReport(
            connector=connector, valid=not findings, findings=tuple(findings)
        )


class DataExchangeReport(DirectorModel):
    exchange: DataExchangeDTO
    valid: bool
    findings: tuple[str, ...] = ()
    transmission_performed: bool = False
    planning_only: bool = True


class DataExchangeFoundation:
    def validate(self, exchange: DataExchangeDTO) -> DataExchangeReport:
        findings: list[str] = []
        if not exchange.approval_boundary:
            findings.append("human approval boundary is required")
        if exchange.transmitted or exchange.persisted:
            findings.append("data exchange must remain local and non-transmitting")
        return DataExchangeReport(exchange=exchange, valid=not findings, findings=tuple(findings))


class EventIntegrationReport(DirectorModel):
    event: IntegrationEventDTO
    valid: bool
    dispatch_performed: bool = False
    planning_only: bool = True


class EventIntegrationFoundation:
    def validate(self, event: IntegrationEventDTO) -> EventIntegrationReport:
        return EventIntegrationReport(event=event, valid=not event.dispatched)


class IntegrationRequestDTO(DirectorModel):
    connector_id: str
    exchange: DataExchangeDTO
    event: IntegrationEventDTO


class IntegrationGatewayReport(DirectorModel):
    registry: IntegrationRegistryReport
    connector: ConnectorSDKReport | None
    exchange: DataExchangeReport
    event: EventIntegrationReport
    eligible_for_human_review: bool = False
    findings: tuple[str, ...] = ()
    state_machine_authoritative: bool = True
    execution_performed: bool = False
    planning_only: bool = True


class IntegrationGatewayFoundation:
    def __init__(
        self, registry: IntegrationRegistryFoundation | None = None
    ) -> None:
        self._registry = registry or IntegrationRegistryFoundation()
        self._connectors = ConnectorSDKFoundation()
        self._exchange = DataExchangeFoundation()
        self._events = EventIntegrationFoundation()

    def preview(self, request: IntegrationRequestDTO) -> IntegrationGatewayReport:
        registry = self._registry.report()
        connector = next(
            (item for item in registry.connectors if item.connector_id == request.connector_id), None
        )
        connector_report = self._connectors.validate(connector) if connector else None
        exchange_report = self._exchange.validate(request.exchange)
        event_report = self._events.validate(request.event)
        findings = list(connector_report.findings if connector_report else ("unknown connector",))
        findings.extend(exchange_report.findings)
        if not event_report.valid:
            findings.append("event dispatch is prohibited")
        if request.exchange.page_reference != request.event.page_reference:
            findings.append("exchange and event page references differ")
        return IntegrationGatewayReport(
            registry=registry,
            connector=connector_report,
            exchange=exchange_report,
            event=event_report,
            eligible_for_human_review=not findings,
            findings=tuple(sorted(set(findings))),
        )
