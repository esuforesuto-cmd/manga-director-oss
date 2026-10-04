"""Contracts for the non-enforcing v5.5 Lifecycle Governance layer."""

from __future__ import annotations

from manga_director.platform import (
    DeprecationNoticeDTO,
    LifecyclePolicyDTO,
    LifecycleRecordDTO,
    MaintenancePolicyDTO,
    MaintenanceRecordDTO,
    PlatformHealthSignalDTO,
    PlatformLifecycleFoundationRequestDTO,
    PlatformLifecycleMaturityRequestDTO,
    PlatformLifecycleMaturityService,
    UnifiedSDKFoundation,
    UpgradePlanDTO,
    UpgradePolicyDTO,
)


def _request() -> PlatformLifecycleMaturityRequestDTO:
    return PlatformLifecycleMaturityRequestDTO(
        foundation_request=PlatformLifecycleFoundationRequestDTO(
            lifecycle_records=(
                LifecycleRecordDTO(
                    capability_id="quality-framework",
                    owner="quality-owner",
                    phase="maintained",
                    evidence_references=("release/v5.4",),
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
                ),
            ),
            health_signals=(
                PlatformHealthSignalDTO(
                    dimension="compatibility",
                    status="healthy",
                    evidence_reference="tests/v5.0-lts",
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
        ),
        lifecycle_policy=LifecyclePolicyDTO(
            policy_id="lifecycle-default", revision="1", owner="governance-owner"
        ),
        upgrade_policy=UpgradePolicyDTO(
            policy_id="upgrade-default", revision="1", owner="release-owner"
        ),
        maintenance_policy=MaintenancePolicyDTO(
            policy_id="maintenance-default", revision="1", owner="operations-owner"
        ),
    )


def test_lifecycle_governance_is_human_gated_and_preserves_state_machine_authority() -> None:
    report = PlatformLifecycleMaturityService().report(_request())

    assert report.lifecycle_governance.lifecycle_policy_compliant is True
    assert report.lifecycle_governance.state_machine_authoritative is True
    assert report.lifecycle_governance.policy_enforced is False
    assert report.lifecycle_governance.automatic_action_taken is False


def test_upgrade_governance_requires_lts_and_rollback_evidence_without_execution() -> None:
    report = PlatformLifecycleMaturityService().report(_request())

    assert report.upgrade_governance.upgrade_policy_compliant is True
    assert report.upgrade_governance.lts_compatibility_valid is True
    assert report.upgrade_governance.rollback_reference_present is True
    assert report.upgrade_governance.upgrade_performed is False
    missing_rollback = PlatformLifecycleMaturityService().report(
        _request().model_copy(
            update={
                "foundation_request": _request().foundation_request.model_copy(
                    update={
                        "upgrade_plan": _request().foundation_request.upgrade_plan.model_copy(
                            update={"rollback_reference": None}
                        )
                    }
                )
            }
        )
    )
    assert missing_rollback.upgrade_governance.upgrade_policy_compliant is False


def test_platform_reliability_is_advisory_without_health_check_or_recovery() -> None:
    report = PlatformLifecycleMaturityService().report(_request())

    assert report.reliability.reliability_status == "advisory_healthy"
    assert report.reliability.health_check_performed is False
    assert report.reliability.recovery_attempted is False
    assert report.reliability.runtime_reconfigured is False


def test_maintenance_policy_remains_non_enforcing_and_requires_human_decision() -> None:
    report = PlatformLifecycleMaturityService().report(_request())

    assert report.maintenance_policy.maintenance_policy_compliant is True
    assert report.maintenance_policy.human_decision_required is True
    assert report.maintenance_policy.policy_enforced is False


def test_lifecycle_observability_and_sdk_maturity_never_collect_or_act() -> None:
    request = _request()
    report = UnifiedSDKFoundation().lifecycle_maturity(request)

    assert report.observability.observed_signal_count == 1
    assert report.observability.telemetry_collected is False
    assert report.observability.monitoring_started is False
    assert report.observability.alert_sent is False
    assert report.automatic_action_taken is False
    assert report.lts_compatible is True
