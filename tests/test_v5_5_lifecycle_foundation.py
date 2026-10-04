"""Contracts for the non-operational v5.5 Creative Platform Lifecycle foundation."""

from __future__ import annotations

import pytest

from manga_director.platform import (
    CreativePlatformLifecycleFoundation,
    DeprecationFrameworkFoundation,
    DeprecationNoticeDTO,
    LifecycleManagerFoundation,
    LifecycleRecordDTO,
    MaintenanceRecordDTO,
    MaintenanceRegistryFoundation,
    PlatformHealthFoundation,
    PlatformHealthSignalDTO,
    PlatformLifecycleFoundationRequestDTO,
    UnifiedSDKFoundation,
    UpgradeManagerFoundation,
    UpgradePlanDTO,
)


def _upgrade_plan() -> UpgradePlanDTO:
    return UpgradePlanDTO(
        upgrade_id="upgrade-5.5",
        source_version="5.4.0",
        target_version="5.5.0",
        owner="release-owner",
        compatibility_evidence=("compatibility/v5.0-lts",),
        rollback_reference="migration/v5.4-rollback",
    )


def _lifecycle_record() -> LifecycleRecordDTO:
    return LifecycleRecordDTO(
        capability_id="quality-framework",
        owner="quality-owner",
        phase="maintained",
        evidence_references=("release/v5.4",),
    )


def _deprecation_notice() -> DeprecationNoticeDTO:
    return DeprecationNoticeDTO(
        capability_id="legacy-quality-preview",
        owner="sdk-owner",
        replacement="quality_preview",
        rationale="consolidate optional reporting entry points",
        earliest_removal_version="6.0.0",
        notice_reference="docs/deprecation/legacy-quality-preview",
        exception_process="governance/exception",
    )


def _health_signal() -> PlatformHealthSignalDTO:
    return PlatformHealthSignalDTO(
        dimension="compatibility",
        status="healthy",
        evidence_reference="tests/v5.0-lts",
    )


def _maintenance_record() -> MaintenanceRecordDTO:
    return MaintenanceRecordDTO(
        record_id="maintenance-quality",
        capability_id="quality-framework",
        owner="quality-owner",
        lifecycle_phase="maintained",
        next_review="2026-12-01",
        risk="low",
        evidence_references=("release/v5.4",),
    )


def test_lifecycle_manager_reports_declared_evidence_without_transitioning() -> None:
    report = LifecycleManagerFoundation().assess((_lifecycle_record(),))

    assert report.status == "ready"
    assert report.eligible_for_human_review is True
    assert report.lifecycle_transitioned is False
    assert report.state_machine_authoritative is True


def test_upgrade_manager_requires_lts_compatibility_and_never_executes() -> None:
    report = UpgradeManagerFoundation().evaluate(_upgrade_plan())

    assert report.status == "ready"
    assert report.eligible_for_human_upgrade_decision is True
    assert report.upgrade_performed is False
    blocked = UpgradeManagerFoundation().evaluate(
        _upgrade_plan().model_copy(update={"package_execution_started": True})
    )
    assert blocked.status == "blocked"


def test_deprecation_framework_requires_complete_human_notice_and_never_enforces() -> None:
    report = DeprecationFrameworkFoundation().evaluate((_deprecation_notice(),))

    assert report.status == "ready"
    assert report.eligible_for_human_notice_decision is True
    assert report.policy_enforced is False
    incomplete = DeprecationFrameworkFoundation().evaluate(
        (_deprecation_notice().model_copy(update={"replacement": None}),)
    )
    assert incomplete.status == "needs_review"


def test_platform_health_is_read_only_and_exposes_unknown_evidence() -> None:
    report = PlatformHealthFoundation().summarize((_health_signal(),))

    assert report.status == "healthy"
    assert report.telemetry_collected is False
    assert report.recovery_attempted is False
    assert PlatformHealthFoundation().summarize().status == "unknown"


def test_maintenance_registry_is_local_and_rejects_duplicate_records() -> None:
    registry = MaintenanceRegistryFoundation((_maintenance_record(),))

    assert registry.report().record_count == 1
    with pytest.raises(ValueError, match="duplicate maintenance record"):
        registry.register(_maintenance_record())
    persisted = MaintenanceRegistryFoundation(
        (_maintenance_record().model_copy(update={"persisted": True}),)
    ).report()
    assert persisted.persistence_performed is False
    assert persisted.findings


def test_lifecycle_gateway_and_sdk_remain_lts_compatible_and_non_operational() -> None:
    request = PlatformLifecycleFoundationRequestDTO(
        lifecycle_records=(_lifecycle_record(),),
        upgrade_plan=_upgrade_plan(),
        deprecations=(_deprecation_notice(),),
        health_signals=(_health_signal(),),
        maintenance_records=(_maintenance_record(),),
    )

    report = CreativePlatformLifecycleFoundation().preview(request)
    sdk_report = UnifiedSDKFoundation().lifecycle_preview(request)

    assert report.lts_compatible is True
    assert report.workflow_changed is False
    assert report.execution_performed is False
    assert sdk_report == report
