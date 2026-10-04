"""v5.1 Composable Creative Platform foundation contracts."""

from __future__ import annotations

import pytest

from manga_director.platform import (
    CapabilityDescriptorDTO,
    CapabilityRegistryFoundation,
    FeaturePackDTO,
    FeaturePackFoundation,
    ModuleCompositionEngineFoundation,
    ModuleCompositionRequestDTO,
    PlatformProfileDTO,
    PlatformProfileFoundation,
    SolutionTemplateDTO,
    SolutionTemplateFoundation,
    UnifiedSDKFoundation,
)


def _pack() -> FeaturePackDTO:
    return FeaturePackDTO(
        pack_id="creative-planning",
        title="Creative Planning",
        capability_ids=("platform.unified-context", "platform.unified-api"),
    )


def _profile() -> PlatformProfileDTO:
    return PlatformProfileDTO(
        profile_id="local.creative-review",
        title="Creative Review",
        feature_pack_ids=("creative-planning",),
        capability_ids=("platform.unified-sdk",),
    )


def _template() -> SolutionTemplateDTO:
    return SolutionTemplateDTO(
        template_id="story-to-review",
        title="Story to Review",
        profile_id="local.creative-review",
        required_evidence=("storyboard", "quality-review"),
    )


def test_capability_registry_is_local_and_preserves_public_contracts() -> None:
    registry = CapabilityRegistryFoundation()
    report = registry.report()

    assert report.capability_count == 6
    assert report.external_discovery_performed is False
    assert report.runtime_changed is False
    assert all(capability.public_contract_preserved for capability in report.capabilities)
    assert all(capability.dynamically_loaded is False for capability in report.capabilities)

    with pytest.raises(ValueError, match="duplicate capability descriptor"):
        registry.register(report.capabilities[0])


def test_feature_pack_validates_capabilities_without_installing_or_invoking() -> None:
    report = FeaturePackFoundation().validate(_pack(), CapabilityRegistryFoundation())

    assert report.valid
    assert report.resolved_capability_ids == _pack().capability_ids
    assert report.missing_capability_ids == ()
    assert report.pack.executable is False
    assert report.pack.installation_required is False
    assert report.services_invoked is False


def test_platform_profile_composes_supplied_pack_with_a_legacy_fallback() -> None:
    report = PlatformProfileFoundation().validate(
        _profile(), (_pack(),), CapabilityRegistryFoundation()
    )

    assert report.valid
    assert report.profile.legacy_only_fallback
    assert report.profile.configuration_changed is False
    assert report.profile.execution_routed is False
    assert report.selected_capability_ids == (
        "platform.unified-api",
        "platform.unified-context",
        "platform.unified-sdk",
    )


def test_solution_template_remains_advisory_and_human_reviewed() -> None:
    report = SolutionTemplateFoundation().validate(_template(), _profile())

    assert report.valid
    assert report.profile_found
    assert report.template.human_review_required
    assert report.template.creates_project is False
    assert report.template.workflow_started is False
    assert report.template.approval_automated is False
    assert report.advisory_only


def test_composition_engine_is_read_only_one_page_safe_and_sdk_available() -> None:
    request = ModuleCompositionRequestDTO(
        profile=_profile(), feature_packs=(_pack(),), templates=(_template(),)
    )
    engine = ModuleCompositionEngineFoundation()
    report = engine.preview(request)

    assert report.summary.valid
    assert report.summary.capability_count == 3
    assert report.summary.state_machine_authoritative
    assert report.summary.workflow_mutated is False
    assert report.summary.services_invoked is False
    assert report.planning_only
    assert UnifiedSDKFoundation().composition_preview(request) == report


def test_composition_engine_reports_invalid_metadata_without_repair_or_execution() -> None:
    invalid_profile = PlatformProfileDTO(
        profile_id="invalid",
        title="Invalid",
        capability_ids=("missing.capability",),
    )
    report = ModuleCompositionEngineFoundation().preview(
        ModuleCompositionRequestDTO(profile=invalid_profile)
    )

    assert report.summary.valid is False
    assert report.profile.missing_capability_ids == ("missing.capability",)
    assert report.summary.workflow_mutated is False
    assert report.summary.services_invoked is False


def test_duplicate_pack_references_fail_closed_as_metadata_findings() -> None:
    duplicate_pack = FeaturePackDTO(
        pack_id="duplicate",
        title="Duplicate",
        capability_ids=("platform.unified-context", "platform.unified-context"),
    )
    report = FeaturePackFoundation().validate(duplicate_pack, CapabilityRegistryFoundation())

    assert report.valid is False
    assert report.missing_capability_ids == ("platform.unified-context",)


def test_custom_capability_remains_non_executable() -> None:
    registry = CapabilityRegistryFoundation(
        (
            CapabilityDescriptorDTO(
                capability_id="custom.report",
                title="Custom Report",
                owner_module="enterprise",
            ),
        )
    )

    assert registry.report().capabilities[0].service_invoked is False
