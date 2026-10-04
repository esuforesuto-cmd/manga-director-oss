import pytest

from manga_director.domain.exceptions import ValidationError
from manga_director.security import (
    AuditLogger,
    SecurityComplianceControl,
    SecurityComplianceValidator,
    SecurityIncident,
    SecurityThreatFinding,
)


def _controls() -> tuple[SecurityComplianceControl, ...]:
    return (
        SecurityComplianceControl("audit-control", "audit", True, "audit:test"),
        SecurityComplianceControl("authn-control", "authentication", True, "authn:test"),
        SecurityComplianceControl("authz-control", "authorization", True, "authz:test"),
        SecurityComplianceControl("credential-control", "credential", True, "credential:test"),
        SecurityComplianceControl(
            "incident-control", "incident_response", True, "incident:test"
        ),
    )


def test_security_compliance_accepts_complete_safe_release_evidence() -> None:
    audit = AuditLogger()
    audit.record("security.authorization", metadata={"allowed": False})

    report = SecurityComplianceValidator().validate_release(
        audit,
        _controls(),
        threats=(
            SecurityThreatFinding(
                threat_id="input-check",
                category="input",
                severity="medium",
                evidence_reference="validation:test",
                mitigated=True,
            ),
        ),
        incidents=(
            SecurityIncident(
                incident_id="input-incident",
                threat_id="input-check",
                category="input",
                severity="medium",
                status="resolved",
            ),
        ),
    )

    assert report.release_ready is True
    assert report.release_performed is False
    assert report.missing_control_areas == ()
    assert report.noncompliant_control_ids == ()


def test_security_compliance_blocks_missing_or_noncompliant_controls() -> None:
    audit = AuditLogger()
    audit.record("security.authorization", metadata={"allowed": True})
    controls = (
        SecurityComplianceControl("audit-control", "audit", False, "audit:test"),
    )

    report = SecurityComplianceValidator().validate_release(audit, controls)

    assert report.release_ready is False
    assert report.noncompliant_control_ids == ("audit-control",)
    assert report.missing_control_areas == (
        "authentication",
        "authorization",
        "credential",
        "incident_response",
    )


def test_security_compliance_blocks_open_high_severity_incidents() -> None:
    audit = AuditLogger()
    audit.record("security.authorization", metadata={"allowed": True})

    report = SecurityComplianceValidator().validate_release(
        audit,
        _controls(),
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

    assert report.release_ready is False
    assert report.monitoring.human_response_required is True


def test_security_compliance_rejects_duplicate_or_unsafe_control_identifiers() -> None:
    audit = AuditLogger()
    audit.record("security.authorization", metadata={"allowed": True})
    control = SecurityComplianceControl("duplicate", "audit", True, "audit:test")

    with pytest.raises(ValidationError, match="unique"):
        SecurityComplianceValidator().validate_release(audit, (control, control))

    with pytest.raises(ValidationError, match="Invalid control_id"):
        SecurityComplianceValidator().validate_release(
            audit,
            (SecurityComplianceControl("../unsafe", "audit", True, "audit:test"),),
        )


def test_security_compliance_rejects_unsupported_control_areas() -> None:
    audit = AuditLogger()
    audit.record("security.authorization", metadata={"allowed": True})

    with pytest.raises(ValidationError, match="area"):
        SecurityComplianceValidator().validate_release(
            audit,
            (SecurityComplianceControl("control-1", "unknown", True, "audit:test"),),  # type: ignore[arg-type]
        )
