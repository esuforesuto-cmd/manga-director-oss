"""Contracts for the read-only v5.5 Lifecycle Intelligence layer."""

from __future__ import annotations

from manga_director.platform import (
    DeprecationNoticeDTO,
    LifecycleIntelligenceService,
    LifecycleRecordDTO,
    MaintenanceRecordDTO,
    PlatformHealthSignalDTO,
    PlatformLifecycleFoundationRequestDTO,
    UnifiedSDKFoundation,
    UpgradePlanDTO,
)


def _request() -> PlatformLifecycleFoundationRequestDTO:
    return PlatformLifecycleFoundationRequestDTO(
        lifecycle_records=(
            LifecycleRecordDTO(
                capability_id="quality-framework",
                owner="quality-owner",
                phase="maintained",
                evidence_references=("release/v5.4",),
            ),
            LifecycleRecordDTO(
                capability_id="legacy-quality-preview",
                owner="sdk-owner",
                phase="deprecated",
                evidence_references=("docs/deprecation",),
            ),
        ),
        upgrade_plan=UpgradePlanDTO(
            upgrade_id="upgrade-5.5",
            source_version="5.4.0",
            target_version="5.5.0",
            owner="release-owner",
            compatibility_evidence=("compatibility/v5.0-lts",),
            rollback_reference="migration/v5.4-rollback",
        ),
        deprecations=(
            DeprecationNoticeDTO(
                capability_id="legacy-quality-preview",
                owner="sdk-owner",
                replacement="quality_preview",
                rationale="consolidate optional reporting entry points",
                earliest_removal_version="6.0.0",
                notice_reference="docs/deprecation/legacy-quality-preview",
                exception_process="governance/exception",
            ),
        ),
        health_signals=(
            PlatformHealthSignalDTO(
                dimension="compatibility",
                status="healthy",
                evidence_reference="tests/v5.0-lts",
            ),
            PlatformHealthSignalDTO(
                dimension="maintenance",
                status="healthy",
                evidence_reference="maintenance/quality-framework",
            ),
        ),
        maintenance_records=(
            MaintenanceRecordDTO(
                record_id="quality-maintenance",
                capability_id="quality-framework",
                owner="quality-owner",
                lifecycle_phase="maintained",
                next_review="2026-12-01",
                risk="low",
                evidence_references=("release/v5.4",),
            ),
        ),
    )


def test_lifecycle_intelligence_counts_lifecycle_evidence_without_mutation() -> None:
    dashboard = LifecycleIntelligenceService().preview(_request())

    assert dashboard.lifecycle.record_count == 2
    assert dashboard.lifecycle.maintained_count == 1
    assert dashboard.lifecycle.deprecated_count == 1
    assert dashboard.lifecycle.workflow_changed is False


def test_upgrade_analytics_requires_lts_evidence_and_never_upgrades() -> None:
    dashboard = LifecycleIntelligenceService().preview(_request())

    assert dashboard.upgrade.lts_compatible is True
    assert dashboard.upgrade.compatibility_evidence_count == 1
    assert dashboard.upgrade.upgrade_performed is False
    blocked = LifecycleIntelligenceService().preview(
        _request().model_copy(
            update={"upgrade_plan": _request().upgrade_plan.model_copy(update={"lts_compatible": False})}
        )
    )
    assert blocked.readiness == "blocked"


def test_platform_health_analytics_preserves_unknown_and_never_starts_monitoring() -> None:
    dashboard = LifecycleIntelligenceService().preview(
        _request().model_copy(update={"health_signals": ()})
    )

    assert dashboard.health.health_status == "unknown"
    assert dashboard.health.monitoring_started is False
    assert dashboard.readiness == "unknown"


def test_deprecation_advisor_is_non_enforcing_and_reports_missing_notice_data() -> None:
    dashboard = LifecycleIntelligenceService().preview(_request())

    assert dashboard.deprecation.notice_count == 1
    assert dashboard.deprecation.removal_performed is False
    assert dashboard.deprecation.policy_enforced is False
    incomplete = LifecycleIntelligenceService().preview(
        _request().model_copy(
            update={
                "deprecations": (
                    _request().deprecations[0].model_copy(update={"notice_reference": None}),
                )
            }
        )
    )
    assert incomplete.deprecation.incomplete_notice_count == 1
    assert incomplete.readiness == "attention_required"


def test_maintenance_dashboard_and_sdk_are_human_gated_and_lts_compatible() -> None:
    request = _request()
    dashboard = UnifiedSDKFoundation().lifecycle_dashboard(request)

    assert dashboard.readiness == "ready_for_human_maintenance_decision"
    assert dashboard.eligible_for_human_maintenance_decision is True
    assert dashboard.automatic_action_taken is False
    assert dashboard.foundation.lts_compatible is True
