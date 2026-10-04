import pytest

from manga_director.domain.exceptions import ValidationError
from manga_director.security import (
    AuditLogger,
    SecurityAuditValidator,
    SecurityFramework,
    SecurityThreatFinding,
)


def test_security_audit_reports_read_only_authorization_evidence() -> None:
    audit = AuditLogger()
    SecurityFramework(audit_logger=audit).authorize("review", resource="page-1")

    report = SecurityAuditValidator().review(
        audit,
        (
            SecurityThreatFinding(
                threat_id="input-check",
                category="input",
                severity="medium",
                evidence_reference="validator:test",
                mitigated=True,
            ),
        ),
    )

    assert report.audit_event_count == 1
    assert report.authorization_denial_count == 1
    assert report.audit_trail_present is True
    assert report.valid is True
    assert report.threat_ids == ("input-check",)
    assert report.blocking_threat_ids == ()


def test_security_audit_blocks_unmitigated_high_severity_threats() -> None:
    audit = AuditLogger()
    audit.record("security.authorization", metadata={"allowed": True})

    report = SecurityAuditValidator().review(
        audit,
        (
            SecurityThreatFinding(
                threat_id="credential-exposure",
                category="credential",
                severity="high",
                evidence_reference="credential-policy",
            ),
        ),
    )

    assert report.valid is False
    assert report.blocking_threat_ids == ("credential-exposure",)


def test_security_audit_requires_unique_safe_threat_identifiers() -> None:
    audit = AuditLogger()
    audit.record("security.authorization", metadata={"allowed": True})
    finding = SecurityThreatFinding(
        threat_id="duplicate",
        category="authorization",
        severity="low",
        evidence_reference="policy",
    )

    with pytest.raises(ValidationError, match="unique"):
        SecurityAuditValidator().review(audit, (finding, finding))

    with pytest.raises(ValidationError, match="Invalid threat_id"):
        SecurityAuditValidator().review(
            audit,
            (
                SecurityThreatFinding(
                    threat_id="../unsafe",
                    category="authorization",
                    severity="low",
                    evidence_reference="policy",
                ),
            ),
        )


def test_security_audit_marks_missing_evidence_as_not_valid() -> None:
    report = SecurityAuditValidator().review(AuditLogger())

    assert report.audit_trail_present is False
    assert report.valid is False


def test_security_audit_rejects_unsupported_threat_values() -> None:
    audit = AuditLogger()
    audit.record("security.authorization", metadata={"allowed": True})

    with pytest.raises(ValidationError, match="category"):
        SecurityAuditValidator().review(
            audit,
            (SecurityThreatFinding("threat-1", "unknown", "low", "policy"),),  # type: ignore[arg-type]
        )

    with pytest.raises(ValidationError, match="severity"):
        SecurityAuditValidator().review(
            audit,
            (SecurityThreatFinding("threat-1", "input", "unknown", "policy"),),  # type: ignore[arg-type]
        )
