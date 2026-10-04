"""Read-only security audit and threat-validation projections."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from manga_director.domain.exceptions import ValidationError
from manga_director.security.audit import AuditLogger
from manga_director.security.validation import SecurityValidator


@dataclass(frozen=True, slots=True)
class SecurityThreatFinding:
    """A caller-supplied security finding without secret-bearing evidence."""

    threat_id: str
    category: Literal["authentication", "authorization", "credential", "input", "rate_limit"]
    severity: Literal["low", "medium", "high", "critical"]
    evidence_reference: str
    mitigated: bool = False


@dataclass(frozen=True, slots=True)
class SecurityAuditReport:
    """Secret-safe audit evidence summary and threat-validation result."""

    audit_event_count: int
    authorization_denial_count: int
    threat_ids: tuple[str, ...]
    blocking_threat_ids: tuple[str, ...]
    audit_trail_present: bool
    valid: bool


class SecurityAuditValidator:
    """Validate supplied threat findings against existing audit evidence."""

    _categories = frozenset({"authentication", "authorization", "credential", "input", "rate_limit"})
    _severities = frozenset({"low", "medium", "high", "critical"})

    def __init__(self, validator: SecurityValidator | None = None) -> None:
        self.validator = validator or SecurityValidator()

    def review(
        self,
        audit_logger: AuditLogger,
        threats: tuple[SecurityThreatFinding, ...] = (),
    ) -> SecurityAuditReport:
        """Produce a read-only report without executing remediation or workflow actions."""
        threat_ids = tuple(threat.threat_id for threat in threats)
        for threat in threats:
            self.validator.identifier(threat.threat_id, "threat_id")
            if threat.category not in self._categories:
                raise ValidationError("Threat category is not supported.")
            if threat.severity not in self._severities:
                raise ValidationError("Threat severity is not supported.")
        if len(threat_ids) != len(set(threat_ids)):
            raise ValidationError("Threat identifiers must be unique.")

        ordered_threats = tuple(sorted(threats, key=lambda threat: threat.threat_id))
        blocking = tuple(
            threat.threat_id
            for threat in ordered_threats
            if threat.severity in {"high", "critical"} and not threat.mitigated
        )
        authorization_denials = sum(
            entry.get("action") == "security.authorization"
            and entry.get("metadata", {}).get("allowed") is False
            for entry in audit_logger.entries
        )
        audit_event_count = len(audit_logger.entries)
        audit_trail_present = audit_event_count > 0
        return SecurityAuditReport(
            audit_event_count=audit_event_count,
            authorization_denial_count=authorization_denials,
            threat_ids=tuple(threat.threat_id for threat in ordered_threats),
            blocking_threat_ids=blocking,
            audit_trail_present=audit_trail_present,
            valid=audit_trail_present and not blocking,
        )
