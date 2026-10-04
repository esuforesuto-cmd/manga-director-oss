"""Read-only security monitoring snapshots and incident-response recommendations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from manga_director.domain.exceptions import ValidationError
from manga_director.security.audit import AuditLogger
from manga_director.security.threats import (
    SecurityAuditReport,
    SecurityAuditValidator,
    SecurityThreatFinding,
)
from manga_director.security.validation import SecurityValidator

SecurityThreatCategory = Literal[
    "authentication", "authorization", "credential", "input", "rate_limit"
]
SecurityResponseAction = Literal[
    "review_access", "review_credentials", "review_input_validation", "review_rate_limit"
]


@dataclass(frozen=True, slots=True)
class SecurityIncident:
    """A secret-safe, caller-supplied incident status projection."""

    incident_id: str
    threat_id: str
    category: SecurityThreatCategory
    severity: Literal["low", "medium", "high", "critical"]
    status: Literal["open", "acknowledged", "resolved"]


@dataclass(frozen=True, slots=True)
class IncidentResponseRecommendation:
    """A human-review recommendation that never executes a response."""

    incident_id: str
    action: SecurityResponseAction
    human_action_required: bool
    response_executed: Literal[False] = False


@dataclass(frozen=True, slots=True)
class SecurityMonitoringReport:
    """One bounded security snapshot without monitoring or notification side effects."""

    audit: SecurityAuditReport
    incident_ids: tuple[str, ...]
    open_incident_ids: tuple[str, ...]
    recommendations: tuple[IncidentResponseRecommendation, ...]
    human_response_required: bool
    monitoring_active: Literal[False] = False
    alert_dispatched: Literal[False] = False
    response_executed: Literal[False] = False


class SecurityMonitoringService:
    """Summarize supplied audit and incident evidence without operational actions."""

    _actions: dict[SecurityThreatCategory, SecurityResponseAction] = {
        "authentication": "review_access",
        "authorization": "review_access",
        "credential": "review_credentials",
        "input": "review_input_validation",
        "rate_limit": "review_rate_limit",
    }
    _severities = frozenset({"low", "medium", "high", "critical"})
    _statuses = frozenset({"open", "acknowledged", "resolved"})

    def __init__(
        self,
        audit_validator: SecurityAuditValidator | None = None,
        validator: SecurityValidator | None = None,
    ) -> None:
        self.audit_validator = audit_validator or SecurityAuditValidator()
        self.validator = validator or SecurityValidator()

    def snapshot(
        self,
        audit_logger: AuditLogger,
        threats: tuple[SecurityThreatFinding, ...] = (),
        incidents: tuple[SecurityIncident, ...] = (),
    ) -> SecurityMonitoringReport:
        """Summarize one supplied evidence set without polling, alerting, or remediation."""
        incident_ids = tuple(incident.incident_id for incident in incidents)
        for incident in incidents:
            self.validator.identifier(incident.incident_id, "incident_id")
            self.validator.identifier(incident.threat_id, "threat_id")
            if incident.category not in self._actions:
                raise ValidationError("Incident category is not supported.")
            if incident.severity not in self._severities:
                raise ValidationError("Incident severity is not supported.")
            if incident.status not in self._statuses:
                raise ValidationError("Incident status is not supported.")
        if len(incident_ids) != len(set(incident_ids)):
            raise ValidationError("Incident identifiers must be unique.")

        audit = self.audit_validator.review(audit_logger, threats)
        ordered_incidents = tuple(sorted(incidents, key=lambda incident: incident.incident_id))
        open_incidents = tuple(
            incident for incident in ordered_incidents if incident.status != "resolved"
        )
        recommendations = tuple(
            IncidentResponseRecommendation(
                incident_id=incident.incident_id,
                action=self._actions[incident.category],
                human_action_required=incident.status != "resolved",
            )
            for incident in ordered_incidents
        )
        human_response_required = bool(audit.blocking_threat_ids) or any(
            incident.severity in {"high", "critical"} for incident in open_incidents
        )
        return SecurityMonitoringReport(
            audit=audit,
            incident_ids=tuple(incident.incident_id for incident in ordered_incidents),
            open_incident_ids=tuple(incident.incident_id for incident in open_incidents),
            recommendations=recommendations,
            human_response_required=human_response_required,
        )
