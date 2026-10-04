"""v5.5 read-only Creative Platform Lifecycle intelligence diagnostics.

The services analyze caller-supplied Lifecycle Foundation evidence. They never
apply upgrades, retire capabilities, collect telemetry, alter configuration, or
change workflow state.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.platform.platform_lifecycle import (
    CreativePlatformLifecycleFoundation,
    DeprecationFrameworkReport,
    HealthStatus,
    LifecycleManagerReport,
    PlatformHealthReport,
    PlatformLifecycleFoundationReport,
    PlatformLifecycleFoundationRequestDTO,
    UpgradeManagerReport,
)
from manga_director.production.director import DirectorModel

LifecycleReadiness = Literal[
    "ready_for_human_maintenance_decision", "attention_required", "blocked", "unknown"
]


class LifecycleIntelligenceDTO(DirectorModel):
    lifecycle_status: str
    record_count: int = Field(ge=0)
    maintained_count: int = Field(ge=0)
    deprecated_count: int = Field(ge=0)
    missing_evidence_count: int = Field(ge=0)
    recommendation: str
    workflow_changed: bool = False
    planning_only: bool = True


class UpgradeAnalyticsDTO(DirectorModel):
    upgrade_id: str
    status: str
    lts_compatible: bool
    compatibility_evidence_count: int = Field(ge=0)
    finding_count: int = Field(ge=0)
    recommendation: str
    upgrade_performed: bool = False
    planning_only: bool = True


class PlatformHealthAnalyticsDTO(DirectorModel):
    health_status: HealthStatus
    signal_count: int = Field(ge=0)
    unknown_signal_count: int = Field(ge=0)
    blocked_signal_count: int = Field(ge=0)
    evidence_gap_count: int = Field(ge=0)
    recommendation: str
    monitoring_started: bool = False
    planning_only: bool = True


class DeprecationAdvisorDTO(DirectorModel):
    status: str
    notice_count: int = Field(ge=0)
    incomplete_notice_count: int = Field(ge=0)
    recommendation: str
    removal_performed: bool = False
    policy_enforced: bool = False
    planning_only: bool = True


class MaintenanceDashboardDTO(DirectorModel):
    foundation: PlatformLifecycleFoundationReport
    lifecycle: LifecycleIntelligenceDTO
    upgrade: UpgradeAnalyticsDTO
    health: PlatformHealthAnalyticsDTO
    deprecation: DeprecationAdvisorDTO
    maintenance_record_count: int = Field(ge=0)
    high_risk_record_count: int = Field(ge=0)
    readiness: LifecycleReadiness
    recommendation: str
    eligible_for_human_maintenance_decision: bool = False
    automatic_action_taken: bool = False
    planning_only: bool = True


class LifecycleIntelligenceService:
    """Builds an evidence-led maintenance dashboard without operating the platform."""

    def __init__(self, foundation: CreativePlatformLifecycleFoundation | None = None) -> None:
        self._foundation = foundation or CreativePlatformLifecycleFoundation()

    def preview(
        self, request: PlatformLifecycleFoundationRequestDTO
    ) -> MaintenanceDashboardDTO:
        foundation = self._foundation.preview(request)
        lifecycle = self._lifecycle(foundation.lifecycle)
        upgrade = self._upgrade(foundation.upgrade)
        health = self._health(foundation.health)
        deprecation = self._deprecation(foundation.deprecation)
        readiness, recommendation = self._readiness(
            foundation, lifecycle, upgrade, health, deprecation
        )
        maintenance = foundation.maintenance
        return MaintenanceDashboardDTO(
            foundation=foundation,
            lifecycle=lifecycle,
            upgrade=upgrade,
            health=health,
            deprecation=deprecation,
            maintenance_record_count=maintenance.record_count,
            high_risk_record_count=sum(record.risk == "high" for record in maintenance.records),
            readiness=readiness,
            recommendation=recommendation,
            eligible_for_human_maintenance_decision=(
                readiness == "ready_for_human_maintenance_decision"
            ),
        )

    @staticmethod
    def _lifecycle(report: LifecycleManagerReport) -> LifecycleIntelligenceDTO:
        records = report.records
        missing = sum(not record.evidence_references for record in records)
        return LifecycleIntelligenceDTO(
            lifecycle_status=report.status,
            record_count=len(records),
            maintained_count=sum(record.phase == "maintained" for record in records),
            deprecated_count=sum(record.phase == "deprecated" for record in records),
            missing_evidence_count=missing,
            recommendation=(
                "retain lifecycle evidence for the human maintenance review"
                if report.status == "ready"
                else "review lifecycle ownership, evidence, and non-operational boundaries"
            ),
        )

    @staticmethod
    def _upgrade(report: UpgradeManagerReport) -> UpgradeAnalyticsDTO:
        return UpgradeAnalyticsDTO(
            upgrade_id=report.plan.upgrade_id,
            status=report.status,
            lts_compatible=report.plan.lts_compatible,
            compatibility_evidence_count=len(report.plan.compatibility_evidence),
            finding_count=len(report.findings),
            recommendation=(
                "present the upgrade evidence to an authorized human owner"
                if report.status == "ready"
                else "complete compatibility and rollback evidence before an upgrade decision"
            ),
        )

    @staticmethod
    def _health(report: PlatformHealthReport) -> PlatformHealthAnalyticsDTO:
        signals = report.signals
        return PlatformHealthAnalyticsDTO(
            health_status=report.status,
            signal_count=len(signals),
            unknown_signal_count=sum(signal.status == "unknown" for signal in signals),
            blocked_signal_count=sum(signal.status == "blocked" for signal in signals),
            evidence_gap_count=sum(signal.evidence_reference is None for signal in signals),
            recommendation=(
                "retain current health evidence for human maintenance review"
                if report.status == "healthy"
                else "review supplied health evidence before any maintenance decision"
            ),
        )

    @staticmethod
    def _deprecation(report: DeprecationFrameworkReport) -> DeprecationAdvisorDTO:
        return DeprecationAdvisorDTO(
            status=report.status,
            notice_count=len(report.notices),
            incomplete_notice_count=sum(
                not notice.replacement
                or not notice.earliest_removal_version
                or not notice.notice_reference
                for notice in report.notices
            ),
            recommendation=(
                "retain notice evidence and communicate only through human governance"
                if report.status == "ready"
                else "complete deprecation notice evidence without enforcing a removal"
            ),
        )

    @staticmethod
    def _readiness(
        foundation: PlatformLifecycleFoundationReport,
        lifecycle: LifecycleIntelligenceDTO,
        upgrade: UpgradeAnalyticsDTO,
        health: PlatformHealthAnalyticsDTO,
        deprecation: DeprecationAdvisorDTO,
    ) -> tuple[LifecycleReadiness, str]:
        statuses = {
            lifecycle.lifecycle_status,
            upgrade.status,
            health.health_status,
            deprecation.status,
        }
        if not foundation.lts_compatible or "blocked" in statuses:
            return "blocked", "do not change platform maintenance posture until blocking evidence is resolved"
        if "unknown" in statuses:
            return "unknown", "supply declared lifecycle and health evidence before a maintenance decision"
        if "needs_review" in statuses or "attention_required" in statuses:
            return "attention_required", "review incomplete evidence with an authorized human owner"
        return (
            "ready_for_human_maintenance_decision",
            "human authorization remains required for every maintenance action",
        )
