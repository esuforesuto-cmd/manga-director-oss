"""v5.3 non-enforcing operating-quality reports for Integration previews."""

from __future__ import annotations

from manga_director.platform.integration import (
    IntegrationGatewayFoundation,
    IntegrationGatewayReport,
    IntegrationRequestDTO,
)
from manga_director.production.director import DirectorModel


class IntegrationGovernanceReport(DirectorModel):
    integration: IntegrationGatewayReport
    human_review_required: bool = True
    state_machine_authoritative: bool = True
    policy_enforced: bool = False
    automatic_action_taken: bool = False
    planning_only: bool = True


class ConnectorSecurityReport(DirectorModel):
    connector_id: str | None = None
    credentials_loaded: bool = False
    connection_started: bool = False
    security_valid: bool = False
    security_scan_performed: bool = False
    planning_only: bool = True


class IntegrationObservabilityReport(DirectorModel):
    integration: IntegrationGatewayReport
    status: str
    telemetry_collected: bool = False
    monitoring_started: bool = False
    alert_sent: bool = False
    planning_only: bool = True


class IntegrationReliabilityReport(DirectorModel):
    observability: IntegrationObservabilityReport
    metadata_valid: bool
    health_check_performed: bool = False
    recovery_attempted: bool = False
    runtime_reconfigured: bool = False
    planning_only: bool = True


class IntegrationLifecycleReport(DirectorModel):
    integration: IntegrationGatewayReport
    stage: str = "advisory"
    lifecycle_transitioned: bool = False
    lifecycle_persisted: bool = False
    retention_enforced: bool = False
    planning_only: bool = True


class IntegrationPlatformMaturityReport(DirectorModel):
    integration: IntegrationGatewayReport
    governance: IntegrationGovernanceReport
    security: ConnectorSecurityReport
    observability: IntegrationObservabilityReport
    reliability: IntegrationReliabilityReport
    lifecycle: IntegrationLifecycleReport
    lts_compatible: bool = True
    automatic_action_taken: bool = False
    planning_only: bool = True


class IntegrationPlatformMaturityService:
    def __init__(self, gateway: IntegrationGatewayFoundation | None = None) -> None:
        self._gateway = gateway or IntegrationGatewayFoundation()

    def report(self, request: IntegrationRequestDTO) -> IntegrationPlatformMaturityReport:
        integration = self._gateway.preview(request)
        connector = integration.connector.connector if integration.connector else None
        observability = IntegrationObservabilityReport(
            integration=integration,
            status="available" if integration.eligible_for_human_review else "attention_required",
        )
        return IntegrationPlatformMaturityReport(
            integration=integration,
            governance=IntegrationGovernanceReport(integration=integration),
            security=ConnectorSecurityReport(
                connector_id=connector.connector_id if connector else None,
                credentials_loaded=bool(connector and connector.credentials_loaded),
                connection_started=bool(connector and connector.connection_started),
                security_valid=bool(connector and integration.connector and integration.connector.valid),
            ),
            observability=observability,
            reliability=IntegrationReliabilityReport(
                observability=observability, metadata_valid=integration.eligible_for_human_review
            ),
            lifecycle=IntegrationLifecycleReport(integration=integration),
        )
