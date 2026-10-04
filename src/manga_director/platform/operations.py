"""Read-only unified observability and reliability reports without monitoring."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.platform.dashboard import UnifiedPlatformDashboardDTO
from manga_director.production.director import DirectorModel


class UnifiedObservationDTO(DirectorModel):
    observation_id: str
    domain: str
    status: Literal["available", "unknown"] = "unknown"
    evidence_supplied: bool = True
    telemetry_collected: bool = False
    health_probe_executed: bool = False
    alert_sent: bool = False


class UnifiedObservabilityReport(DirectorModel):
    dashboard: UnifiedPlatformDashboardDTO
    observations: tuple[UnifiedObservationDTO, ...]
    observation_count: int = Field(default=0, ge=0)
    monitoring_started: bool = False
    report_persisted: bool = False
    planning_only: bool = True


class UnifiedObservabilityService:
    """Exposes supplied dashboard evidence without collecting operational data."""

    def report(self, dashboard: UnifiedPlatformDashboardDTO) -> UnifiedObservabilityReport:
        observations = (
            UnifiedObservationDTO(observation_id="context-coverage", domain="context"),
            UnifiedObservationDTO(observation_id="api-surface", domain="api"),
            UnifiedObservationDTO(observation_id="runtime-plan", domain="runtime"),
            UnifiedObservationDTO(observation_id="sdk-preview", domain="sdk"),
        )
        return UnifiedObservabilityReport(
            dashboard=dashboard, observations=observations, observation_count=len(observations)
        )


class UnifiedReliabilityComponentDTO(DirectorModel):
    component_id: str
    status: Literal["not_checked"] = "not_checked"
    compatibility_required: bool = True
    health_check_performed: bool = False
    recovery_attempted: bool = False


class UnifiedReliabilityReport(DirectorModel):
    observability: UnifiedObservabilityReport
    components: tuple[UnifiedReliabilityComponentDTO, ...]
    component_count: int = Field(default=0, ge=0)
    runtime_reconfigured: bool = False
    automatic_recovery_taken: bool = False
    planning_only: bool = True


class UnifiedReliabilityService:
    """Makes unverified health explicit without testing or repairing components."""

    def report(self, observability: UnifiedObservabilityReport) -> UnifiedReliabilityReport:
        components = tuple(
            UnifiedReliabilityComponentDTO(component_id=domain)
            for domain in ("context", "api", "runtime", "sdk", "dashboard")
        )
        return UnifiedReliabilityReport(
            observability=observability, components=components, component_count=len(components)
        )

