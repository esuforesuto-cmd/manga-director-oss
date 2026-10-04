"""v5.1 Composable Platform governance and operating-quality contracts."""

from __future__ import annotations

from manga_director.platform import (
    CapabilityGovernanceService,
    CompositionGovernanceService,
    CompositionObservabilityService,
    CompositionPlatformMaturityService,
    CompositionReliabilityService,
    FeaturePackDTO,
    ModuleCompositionEngineFoundation,
    ModuleCompositionRequestDTO,
    ModuleLifecycleManagementService,
    PlatformProfileDTO,
    SolutionTemplateDTO,
    UnifiedSDKFoundation,
)


def _request() -> ModuleCompositionRequestDTO:
    pack = FeaturePackDTO(
        pack_id="creative-planning",
        title="Creative Planning",
        capability_ids=("platform.unified-context", "platform.unified-api"),
    )
    profile = PlatformProfileDTO(
        profile_id="local.creative-review",
        title="Creative Review",
        feature_pack_ids=(pack.pack_id,),
        capability_ids=("platform.unified-sdk",),
    )
    template = SolutionTemplateDTO(
        template_id="story-to-review",
        title="Story to Review",
        profile_id=profile.profile_id,
        required_evidence=("storyboard", "quality-review"),
    )
    return ModuleCompositionRequestDTO(
        profile=profile, feature_packs=(pack,), templates=(template,)
    )


def test_composition_governance_requires_human_review_without_enforcement() -> None:
    composition = ModuleCompositionEngineFoundation().preview(_request())
    report = CompositionGovernanceService().report(composition)

    assert report.compliance.metadata_valid
    assert report.compliance.profile_legacy_fallback
    assert report.policy.state_machine_authoritative
    assert report.policy.one_page_scope_required
    assert report.policy.persisted_storyboard_required
    assert report.policy.completed_quality_review_required
    assert report.policy.policy_enforced is False
    assert report.summary.human_review_required


def test_capability_governance_audits_metadata_without_loading_a_module() -> None:
    composition = ModuleCompositionEngineFoundation().preview(_request())
    report = CapabilityGovernanceService().report(composition)

    assert report.capability_count == 6
    assert report.external_audit_performed is False
    assert all(item.owner_module_declared for item in report.capabilities)
    assert all(item.compatibility_declared for item in report.capabilities)
    assert all(item.public_contract_preserved for item in report.capabilities)
    assert all(item.dynamically_loaded is False for item in report.capabilities)


def test_composition_observability_is_supplied_evidence_not_monitoring() -> None:
    composition = ModuleCompositionEngineFoundation().preview(_request())
    report = CompositionObservabilityService().report(composition)

    assert report.observation_count == 5
    assert all(item.status == "available" for item in report.observations)
    assert report.monitoring_started is False
    assert report.report_persisted is False
    assert all(item.telemetry_collected is False for item in report.observations)
    assert all(item.alert_sent is False for item in report.observations)


def test_module_lifecycle_preserves_module_ownership_and_never_transitions() -> None:
    composition = ModuleCompositionEngineFoundation().preview(_request())
    report = ModuleLifecycleManagementService().report(composition)

    assert report.module_count == 6
    assert all(module.stage == "declared" for module in report.modules)
    assert all(module.lifecycle_transitioned is False for module in report.modules)
    assert all(module.lifecycle_persisted is False for module in report.modules)
    assert report.ownership_transferred is False
    assert report.retention_enforced is False


def test_composition_reliability_reports_metadata_not_runtime_health() -> None:
    composition = ModuleCompositionEngineFoundation().preview(_request())
    observability = CompositionObservabilityService().report(composition)
    report = CompositionReliabilityService().report(observability)

    assert report.component_count == 5
    assert all(component.status == "metadata_valid" for component in report.components)
    assert all(component.health_check_performed is False for component in report.components)
    assert all(component.recovery_attempted is False for component in report.components)
    assert report.runtime_reconfigured is False
    assert report.automatic_recovery_taken is False


def test_maturity_and_sdk_keep_composition_read_only_and_lts_compatible() -> None:
    request = _request()
    report = CompositionPlatformMaturityService().report(request)

    assert report.composition.summary.valid
    assert report.lts_compatible
    assert report.automatic_action_taken is False
    assert report.governance.compliance.compliance_confirmed is False
    assert UnifiedSDKFoundation().composition_maturity(request) == report


def test_invalid_composition_is_visible_without_automatic_repair() -> None:
    request = ModuleCompositionRequestDTO(
        profile=PlatformProfileDTO(
            profile_id="invalid", title="Invalid", capability_ids=("missing.capability",)
        )
    )
    report = CompositionPlatformMaturityService().report(request)

    assert report.composition.summary.valid is False
    assert all(observation.status == "invalid" for observation in report.observability.observations)
    assert all(component.status == "metadata_invalid" for component in report.reliability.components)
    assert report.automatic_action_taken is False
