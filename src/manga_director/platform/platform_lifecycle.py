"""v5.5 local, human-gated Creative Platform Lifecycle foundations.

The types in this module normalize supplied maintenance evidence only. They do
not install upgrades, remove capabilities, collect telemetry, mutate platform
state, or alter workflow execution. The StateMachine remains authoritative.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.production.director import DirectorModel

LifecyclePhase = Literal["planned", "active", "maintained", "deprecated", "retired"]
AssessmentStatus = Literal["ready", "needs_review", "blocked", "unknown"]
HealthStatus = Literal["healthy", "attention_required", "blocked", "unknown"]


class LifecycleRecordDTO(DirectorModel):
    """Declared lifecycle evidence for one platform capability."""

    capability_id: str
    owner: str
    phase: LifecyclePhase
    compatibility_range: str = ">=5.0,<6.0"
    evidence_references: tuple[str, ...] = ()
    review_required: bool = True
    state_transitioned: bool = False
    persisted: bool = False


class LifecycleManagerReport(DirectorModel):
    records: tuple[LifecycleRecordDTO, ...] = ()
    status: AssessmentStatus = "unknown"
    findings: tuple[str, ...] = ()
    eligible_for_human_review: bool = False
    state_machine_authoritative: bool = True
    lifecycle_transitioned: bool = False
    planning_only: bool = True


class LifecycleManagerFoundation:
    """Assesses declared lifecycle records without owning their lifecycle."""

    def assess(self, records: tuple[LifecycleRecordDTO, ...] = ()) -> LifecycleManagerReport:
        if not records:
            return LifecycleManagerReport(findings=("no lifecycle records were supplied",))
        findings: list[str] = []
        identifiers = [record.capability_id for record in records]
        if len(set(identifiers)) != len(identifiers):
            findings.append("lifecycle capability identifiers must be unique")
        for record in records:
            if not record.owner:
                findings.append(f"lifecycle owner is required: {record.capability_id}")
            if record.phase in {"active", "maintained", "deprecated"} and not record.evidence_references:
                findings.append(f"lifecycle evidence is required: {record.capability_id}")
            if record.state_transitioned or record.persisted:
                findings.append(f"lifecycle foundation is non-operational: {record.capability_id}")
        status: AssessmentStatus = "ready" if not findings else "needs_review"
        if any("non-operational" in finding or "unique" in finding for finding in findings):
            status = "blocked"
        return LifecycleManagerReport(
            records=records,
            status=status,
            findings=tuple(sorted(set(findings))),
            eligible_for_human_review=status == "ready",
        )


class UpgradePlanDTO(DirectorModel):
    """Human-owned upgrade evidence; never an executable plan."""

    upgrade_id: str
    source_version: str
    target_version: str
    owner: str
    lts_compatible: bool = True
    compatibility_evidence: tuple[str, ...] = ()
    migration_steps: tuple[str, ...] = ()
    rollback_reference: str | None = None
    package_execution_started: bool = False
    configuration_changed: bool = False


class UpgradeManagerReport(DirectorModel):
    plan: UpgradePlanDTO
    status: AssessmentStatus = "unknown"
    findings: tuple[str, ...] = ()
    eligible_for_human_upgrade_decision: bool = False
    upgrade_performed: bool = False
    rollback_performed: bool = False
    planning_only: bool = True


class UpgradeManagerFoundation:
    """Validates upgrade evidence without installing or rolling back anything."""

    def evaluate(self, plan: UpgradePlanDTO) -> UpgradeManagerReport:
        findings: list[str] = []
        if not plan.owner:
            findings.append("upgrade owner is required")
        if not plan.lts_compatible:
            findings.append("v5.0 LTS compatibility evidence is required")
        if not plan.compatibility_evidence:
            findings.append("compatibility evidence is required")
        if not plan.rollback_reference:
            findings.append("rollback reference is required")
        if plan.package_execution_started or plan.configuration_changed:
            findings.append("upgrade foundation is non-operational")
        status: AssessmentStatus
        if "upgrade foundation is non-operational" in findings:
            status = "blocked"
        elif findings:
            status = "needs_review"
        else:
            status = "ready"
        return UpgradeManagerReport(
            plan=plan,
            status=status,
            findings=tuple(findings),
            eligible_for_human_upgrade_decision=status == "ready",
        )


class DeprecationNoticeDTO(DirectorModel):
    capability_id: str
    owner: str
    replacement: str | None = None
    rationale: str
    earliest_removal_version: str | None = None
    notice_reference: str | None = None
    exception_process: str | None = None
    removal_performed: bool = False
    caller_blocked: bool = False


class DeprecationFrameworkReport(DirectorModel):
    notices: tuple[DeprecationNoticeDTO, ...] = ()
    status: AssessmentStatus = "unknown"
    findings: tuple[str, ...] = ()
    eligible_for_human_notice_decision: bool = False
    policy_enforced: bool = False
    planning_only: bool = True


class DeprecationFrameworkFoundation:
    """Reviews deprecation notice completeness without enforcing a policy."""

    def evaluate(
        self, notices: tuple[DeprecationNoticeDTO, ...] = ()
    ) -> DeprecationFrameworkReport:
        if not notices:
            return DeprecationFrameworkReport(findings=("no deprecation notices were supplied",))
        findings: list[str] = []
        for notice in notices:
            if not notice.owner:
                findings.append(f"deprecation owner is required: {notice.capability_id}")
            if not notice.replacement:
                findings.append(f"deprecation replacement is required: {notice.capability_id}")
            if not notice.earliest_removal_version:
                findings.append(f"deprecation horizon is required: {notice.capability_id}")
            if not notice.notice_reference:
                findings.append(f"deprecation notice reference is required: {notice.capability_id}")
            if notice.removal_performed or notice.caller_blocked:
                findings.append(f"deprecation foundation is non-enforcing: {notice.capability_id}")
        status: AssessmentStatus = "ready" if not findings else "needs_review"
        if any("non-enforcing" in finding for finding in findings):
            status = "blocked"
        return DeprecationFrameworkReport(
            notices=notices,
            status=status,
            findings=tuple(sorted(set(findings))),
            eligible_for_human_notice_decision=status == "ready",
        )


class PlatformHealthSignalDTO(DirectorModel):
    dimension: Literal["compatibility", "maintenance", "release", "operations", "evidence"]
    status: HealthStatus
    evidence_reference: str | None = None
    observed_at: str | None = None
    telemetry_collected: bool = False
    action_taken: bool = False


class PlatformHealthReport(DirectorModel):
    signals: tuple[PlatformHealthSignalDTO, ...] = ()
    status: HealthStatus = "unknown"
    findings: tuple[str, ...] = ()
    human_review_required: bool = True
    telemetry_collected: bool = False
    recovery_attempted: bool = False
    planning_only: bool = True


class PlatformHealthFoundation:
    """Aggregates supplied health evidence without monitoring or recovering."""

    def summarize(self, signals: tuple[PlatformHealthSignalDTO, ...] = ()) -> PlatformHealthReport:
        if not signals:
            return PlatformHealthReport(findings=("no platform health signals were supplied",))
        findings: list[str] = []
        for signal in signals:
            if not signal.evidence_reference:
                findings.append(f"health evidence is missing: {signal.dimension}")
            if signal.telemetry_collected or signal.action_taken:
                findings.append(f"platform health foundation is read-only: {signal.dimension}")
        statuses = {signal.status for signal in signals}
        if "blocked" in statuses or any("read-only" in finding for finding in findings):
            status: HealthStatus = "blocked"
        elif "attention_required" in statuses or findings:
            status = "attention_required"
        elif "unknown" in statuses:
            status = "unknown"
        else:
            status = "healthy"
        return PlatformHealthReport(
            signals=signals,
            status=status,
            findings=tuple(sorted(set(findings))),
        )


class MaintenanceRecordDTO(DirectorModel):
    record_id: str
    capability_id: str
    owner: str
    lifecycle_phase: LifecyclePhase
    next_review: str
    risk: Literal["low", "medium", "high", "unknown"] = "unknown"
    evidence_references: tuple[str, ...] = ()
    persisted: bool = False


class MaintenanceRegistryReport(DirectorModel):
    records: tuple[MaintenanceRecordDTO, ...] = ()
    record_count: int = Field(default=0, ge=0)
    findings: tuple[str, ...] = ()
    external_registry_used: bool = False
    persistence_performed: bool = False
    planning_only: bool = True


class MaintenanceRegistryFoundation:
    """Keeps supplied maintenance records in process for report composition only."""

    def __init__(self, records: tuple[MaintenanceRecordDTO, ...] = ()) -> None:
        self._records = {record.record_id: record for record in records}
        if len(self._records) != len(records):
            raise ValueError("duplicate maintenance record")

    def register(self, record: MaintenanceRecordDTO) -> None:
        if record.record_id in self._records:
            raise ValueError(f"duplicate maintenance record: {record.record_id}")
        self._records[record.record_id] = record

    def report(self) -> MaintenanceRegistryReport:
        records = tuple(self._records[key] for key in sorted(self._records))
        findings = tuple(
            f"maintenance record is non-persistent: {record.record_id}"
            for record in records
            if record.persisted
        )
        return MaintenanceRegistryReport(
            records=records,
            record_count=len(records),
            findings=findings,
        )


class PlatformLifecycleFoundationRequestDTO(DirectorModel):
    lifecycle_records: tuple[LifecycleRecordDTO, ...] = ()
    upgrade_plan: UpgradePlanDTO
    deprecations: tuple[DeprecationNoticeDTO, ...] = ()
    health_signals: tuple[PlatformHealthSignalDTO, ...] = ()
    maintenance_records: tuple[MaintenanceRecordDTO, ...] = ()


class PlatformLifecycleFoundationReport(DirectorModel):
    lifecycle: LifecycleManagerReport
    upgrade: UpgradeManagerReport
    deprecation: DeprecationFrameworkReport
    health: PlatformHealthReport
    maintenance: MaintenanceRegistryReport
    lts_compatible: bool = True
    workflow_changed: bool = False
    execution_performed: bool = False
    planning_only: bool = True


class CreativePlatformLifecycleFoundation:
    """Composes the v5.5 foundation reports without operating the platform."""

    def preview(self, request: PlatformLifecycleFoundationRequestDTO) -> PlatformLifecycleFoundationReport:
        lifecycle = LifecycleManagerFoundation().assess(request.lifecycle_records)
        upgrade = UpgradeManagerFoundation().evaluate(request.upgrade_plan)
        deprecation = DeprecationFrameworkFoundation().evaluate(request.deprecations)
        health = PlatformHealthFoundation().summarize(request.health_signals)
        maintenance = MaintenanceRegistryFoundation(request.maintenance_records).report()
        return PlatformLifecycleFoundationReport(
            lifecycle=lifecycle,
            upgrade=upgrade,
            deprecation=deprecation,
            health=health,
            maintenance=maintenance,
            lts_compatible=request.upgrade_plan.lts_compatible,
        )
