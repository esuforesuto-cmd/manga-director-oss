import pytest

from manga_director.domain.exceptions import ValidationError
from manga_director.security import (
    AuditLogger,
    SecurityIncident,
    SecurityMonitoringService,
    SecurityThreatFinding,
)


def test_security_monitoring_returns_a_read_only_incident_snapshot() -> None:
    audit = AuditLogger()
    audit.record("security.authorization", metadata={"allowed": False})
    report = SecurityMonitoringService().snapshot(
        audit,
        threats=(
            SecurityThreatFinding(
                threat_id="authorization-check",
                category="authorization",
                severity="medium",
                evidence_reference="policy:test",
                mitigated=True,
            ),
        ),
        incidents=(
            SecurityIncident(
                incident_id="incident-1",
                threat_id="authorization-check",
                category="authorization",
                severity="medium",
                status="acknowledged",
            ),
        ),
    )

    assert report.audit.authorization_denial_count == 1
    assert report.open_incident_ids == ("incident-1",)
    assert report.recommendations[0].action == "review_access"
    assert report.monitoring_active is False
    assert report.alert_dispatched is False
    assert report.response_executed is False


def test_security_monitoring_requires_human_response_for_open_high_incidents() -> None:
    audit = AuditLogger()
    audit.record("security.authorization", metadata={"allowed": True})
    report = SecurityMonitoringService().snapshot(
        audit,
        incidents=(
            SecurityIncident(
                incident_id="credential-incident",
                threat_id="credential-check",
                category="credential",
                severity="high",
                status="open",
            ),
        ),
    )

    assert report.human_response_required is True
    assert report.recommendations[0].action == "review_credentials"
    assert report.recommendations[0].response_executed is False


def test_security_monitoring_rejects_duplicate_or_unsafe_incident_identifiers() -> None:
    audit = AuditLogger()
    audit.record("security.authorization", metadata={"allowed": True})
    incident = SecurityIncident(
        incident_id="duplicate",
        threat_id="input-check",
        category="input",
        severity="low",
        status="resolved",
    )

    with pytest.raises(ValidationError, match="unique"):
        SecurityMonitoringService().snapshot(audit, incidents=(incident, incident))

    with pytest.raises(ValidationError, match="Invalid incident_id"):
        SecurityMonitoringService().snapshot(
            audit,
            incidents=(
                SecurityIncident(
                    incident_id="../unsafe",
                    threat_id="input-check",
                    category="input",
                    severity="low",
                    status="resolved",
                ),
            ),
        )


def test_security_monitoring_rejects_unsupported_incident_values() -> None:
    audit = AuditLogger()
    audit.record("security.authorization", metadata={"allowed": True})

    with pytest.raises(ValidationError, match="category"):
        SecurityMonitoringService().snapshot(
            audit,
            incidents=(
                SecurityIncident("incident-1", "threat-1", "unknown", "low", "open"),  # type: ignore[arg-type]
            ),
        )

    with pytest.raises(ValidationError, match="status"):
        SecurityMonitoringService().snapshot(
            audit,
            incidents=(
                SecurityIncident("incident-1", "threat-1", "input", "low", "unknown"),  # type: ignore[arg-type]
            ),
        )
