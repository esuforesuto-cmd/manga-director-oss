"""Read-only security-compliance and release-readiness validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from manga_director.domain.exceptions import ValidationError
from manga_director.security.audit import AuditLogger
from manga_director.security.monitoring import (
    SecurityIncident,
    SecurityMonitoringReport,
    SecurityMonitoringService,
)
from manga_director.security.threats import SecurityThreatFinding
from manga_director.security.validation import SecurityValidator

SecurityComplianceArea = Literal[
    "authentication", "authorization", "credential", "audit", "incident_response"
]


@dataclass(frozen=True, slots=True)
class SecurityComplianceControl:
    """A caller-supplied control status without exposing its evidence."""

    control_id: str
    area: SecurityComplianceArea
    compliant: bool
    evidence_reference: str


@dataclass(frozen=True, slots=True)
class SecurityComplianceReport:
    """Secret-safe security-compliance and release-readiness result."""

    monitoring: SecurityMonitoringReport
    control_ids: tuple[str, ...]
    missing_control_areas: tuple[SecurityComplianceArea, ...]
    noncompliant_control_ids: tuple[str, ...]
    release_ready: bool
    release_performed: Literal[False] = False


class SecurityComplianceValidator:
    """Validate supplied control evidence without changing release state."""

    _required_areas: frozenset[SecurityComplianceArea] = frozenset(
        {"authentication", "authorization", "credential", "audit", "incident_response"}
    )

    def __init__(
        self,
        monitoring: SecurityMonitoringService | None = None,
        validator: SecurityValidator | None = None,
    ) -> None:
        self.monitoring = monitoring or SecurityMonitoringService()
        self.validator = validator or SecurityValidator()

    def validate_release(
        self,
        audit_logger: AuditLogger,
        controls: tuple[SecurityComplianceControl, ...] = (),
        *,
        threats: tuple[SecurityThreatFinding, ...] = (),
        incidents: tuple[SecurityIncident, ...] = (),
    ) -> SecurityComplianceReport:
        """Return release readiness without publishing, tagging, or mutating evidence."""
        control_ids = tuple(control.control_id for control in controls)
        for control in controls:
            self.validator.identifier(control.control_id, "control_id")
            if control.area not in self._required_areas:
                raise ValidationError("Compliance control area is not supported.")
        if len(control_ids) != len(set(control_ids)):
            raise ValidationError("Control identifiers must be unique.")

        monitoring = self.monitoring.snapshot(audit_logger, threats, incidents)
        ordered_controls = tuple(sorted(controls, key=lambda control: control.control_id))
        covered_areas = {control.area for control in ordered_controls}
        missing_areas = tuple(sorted(self._required_areas - covered_areas))
        noncompliant = tuple(
            control.control_id for control in ordered_controls if not control.compliant
        )
        return SecurityComplianceReport(
            monitoring=monitoring,
            control_ids=tuple(control.control_id for control in ordered_controls),
            missing_control_areas=missing_areas,
            noncompliant_control_ids=noncompliant,
            release_ready=(
                monitoring.audit.valid
                and not monitoring.human_response_required
                and not missing_areas
                and not noncompliant
            ),
        )
