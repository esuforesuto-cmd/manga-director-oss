"""v5.3 local diagnostics for Integration Foundation reports only."""

from __future__ import annotations

from manga_director.platform.integration import (
    IntegrationGatewayFoundation,
    IntegrationGatewayReport,
    IntegrationRequestDTO,
)
from manga_director.production.director import DirectorModel


class ConnectorIntelligenceDTO(DirectorModel):
    connector_id: str | None = None
    capability_count: int = 0
    compatible: bool = False
    connection_started: bool = False
    recommendation: str
    planning_only: bool = True


class DataExchangeAnalyticsDTO(DirectorModel):
    exchange_id: str
    data_classification: str
    approval_boundary_declared: bool
    valid: bool
    transmission_performed: bool = False
    recommendation: str
    planning_only: bool = True


class EventProcessingIntelligenceDTO(DirectorModel):
    event_id: str
    provenance: str
    correlation_present: bool
    valid: bool
    dispatch_performed: bool = False
    recommendation: str
    planning_only: bool = True


class IntegrationPolicyReport(DirectorModel):
    policy_id: str = "integration-policy"
    human_review_required: bool = True
    state_machine_authoritative: bool = True
    connector_valid: bool = False
    exchange_valid: bool = False
    event_valid: bool = False
    policy_enforced: bool = False
    planning_only: bool = True


class IntegrationHealthDashboardDTO(DirectorModel):
    connector: ConnectorIntelligenceDTO
    exchange: DataExchangeAnalyticsDTO
    event: EventProcessingIntelligenceDTO
    policy: IntegrationPolicyReport
    health: str
    findings: tuple[str, ...] = ()
    automatic_action_taken: bool = False
    planning_only: bool = True


class IntegrationIntelligenceService:
    def __init__(self, gateway: IntegrationGatewayFoundation | None = None) -> None:
        self._gateway = gateway or IntegrationGatewayFoundation()

    def preview(self, request: IntegrationRequestDTO) -> IntegrationHealthDashboardDTO:
        report = self._gateway.preview(request)
        return self._dashboard(report, request)

    @staticmethod
    def _dashboard(
        report: IntegrationGatewayReport, request: IntegrationRequestDTO
    ) -> IntegrationHealthDashboardDTO:
        connector = report.connector
        connector_data = connector.connector if connector else None
        connector_view = ConnectorIntelligenceDTO(
            connector_id=connector_data.connector_id if connector_data else None,
            capability_count=len(connector_data.capabilities) if connector_data else 0,
            compatible=bool(connector and connector.valid),
            connection_started=bool(connector_data and connector_data.connection_started),
            recommendation=("retain local descriptor" if connector and connector.valid else "resolve connector findings"),
        )
        exchange_view = DataExchangeAnalyticsDTO(
            exchange_id=request.exchange.exchange_id,
            data_classification=request.exchange.data_classification,
            approval_boundary_declared=bool(request.exchange.approval_boundary),
            valid=report.exchange.valid,
            recommendation=("present exchange to human review" if report.exchange.valid else "declare approval boundary"),
        )
        event_view = EventProcessingIntelligenceDTO(
            event_id=request.event.event_id,
            provenance=request.event.provenance,
            correlation_present=bool(request.event.correlation_id),
            valid=report.event.valid,
            recommendation=("retain local event evidence" if report.event.valid else "remove dispatch semantics"),
        )
        policy = IntegrationPolicyReport(
            connector_valid=bool(connector and connector.valid),
            exchange_valid=report.exchange.valid,
            event_valid=report.event.valid,
        )
        return IntegrationHealthDashboardDTO(
            connector=connector_view,
            exchange=exchange_view,
            event=event_view,
            policy=policy,
            health="ready_for_human_review" if report.eligible_for_human_review else "attention_required",
            findings=report.findings,
        )
