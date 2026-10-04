"""Focused tests for the standalone future-generation admission contract."""

from __future__ import annotations

import inspect

import pytest
from generation_admission_v1_fixtures import (
    DUPLICATE_PANEL_ID,
    EMPTY_STORYBOARD,
    LEGACY_PAGE,
    MALFORMED_VERSION,
    MISSING_ACTION,
    MISSING_PANEL_ID,
    MISSING_PURPOSE,
    MISSING_SCENE,
    PROMPT_DIGEST,
    SECRET_SHAPED_PARAMETER,
    UNSTABLE_PANEL_ORDER,
    manifest,
    prompt,
    provider_request,
    storyboard,
)
from pydantic import ValidationError

import manga_director
import manga_director.production as production
from manga_director.production import future_generation_admission_contract as admission
from manga_director.production.future_generation_admission_contract import (
    GenerationAdmissionDecision,
    GenerationAdmissionManifestV1,
    GenerationParameterV1,
    PromptEvidenceV1,
    ProviderRequestBindingV1,
    SnapshotIdentityV1,
    StoryboardEvidenceV1,
    StoryboardPanelV1,
    canonical_json,
    content_digest,
    legacy_evidence_decision,
)


def test_valid_single_panel_manifest_is_deterministic_and_admittable() -> None:
    first = manifest()
    second = manifest()

    assert first.content_digest == second.content_digest
    decision = GenerationAdmissionDecision(
        status="ADMITTED",
        reason_code="ADMISSION_EVIDENCE_COMPLETE",
        manifest_digest=first.content_digest,
    )
    assert decision.status == "ADMITTED"
    assert decision.provider_invocation_performed is False
    assert decision.external_side_effect_performed is False


def test_valid_multi_panel_manifest_preserves_meaningful_panel_order() -> None:
    single = manifest(storyboard_evidence=storyboard(panel_count=1))
    multi = manifest(storyboard_evidence=storyboard(panel_count=2))

    assert single.content_digest != multi.content_digest
    assert tuple(panel.order for panel in multi.storyboard.panels) == (1, 2)


def test_empty_storyboard_and_malformed_panel_evidence_fail_closed() -> None:
    with pytest.raises(ValidationError, match="at least one panel"):
        StoryboardEvidenceV1.model_validate(
            {**EMPTY_STORYBOARD, "storyboard_reference": "storyboard:empty"}
        )
    with pytest.raises(ValidationError):
        StoryboardPanelV1.model_validate(MISSING_PANEL_ID)
    with pytest.raises(ValidationError):
        StoryboardPanelV1.model_validate(MISSING_PURPOSE)
    with pytest.raises(ValidationError):
        StoryboardPanelV1.model_validate(MISSING_SCENE)
    with pytest.raises(ValidationError):
        StoryboardPanelV1.model_validate(MISSING_ACTION)


def test_duplicate_panel_ids_and_unstable_order_fail_closed() -> None:
    first = StoryboardPanelV1(
        panel_id=DUPLICATE_PANEL_ID[0],
        order=1,
        purpose="setup",
        scene="station",
        action="arrive",
    )
    second = first.model_copy(update={"order": 2})
    with pytest.raises(ValidationError, match="identities must be unique"):
        StoryboardEvidenceV1(
            schema_id="manga.storyboard",
            schema_version="1",
            storyboard_reference="storyboard:duplicate",
            panels=(first, second),
        )

    out_of_order = (
        first.model_copy(update={"panel_id": "panel:2", "order": UNSTABLE_PANEL_ORDER[0]}),
        second.model_copy(update={"panel_id": "panel:1", "order": UNSTABLE_PANEL_ORDER[1]}),
    )
    with pytest.raises(ValidationError, match="contiguous deterministic order"):
        StoryboardEvidenceV1(
            schema_id="manga.storyboard",
            schema_version="1",
            storyboard_reference="storyboard:unstable",
            panels=out_of_order,
        )


def test_prompt_provenance_mismatch_and_stale_storyboard_are_rejected() -> None:
    original = storyboard()
    changed = storyboard(panel_count=2)
    original_prompt = prompt(original)

    with pytest.raises(ValidationError, match="provenance"):
        manifest(storyboard_evidence=changed, prompt_evidence=original_prompt)
    assert original.content_digest != changed.content_digest


def test_provider_model_workflow_binding_and_changes_affect_manifest_identity() -> None:
    first = manifest()
    changed_provider = ProviderRequestBindingV1(
        provider_reference="provider:other",
        model_id="model:fixture",
        model_version="1",
        workflow_id="workflow:fixture",
        workflow_version="1",
        workflow_content_digest=content_digest({"workflow": "fixture"}),
        parameters=(GenerationParameterV1.from_value("width", 1024),),
    )
    changed = manifest(provider=changed_provider)

    assert first.content_digest != changed.content_digest
    assert first.provider_request.model_id == "model:fixture"
    assert first.provider_request.workflow_id == "workflow:fixture"


def test_attempt_identity_changes_manifest_identity() -> None:
    first = manifest(attempt_id="attempt:volume:one:page:1:001")
    changed = manifest(attempt_id="attempt:volume:one:page:1:002")

    assert first.content_digest != changed.content_digest


def test_canonicalization_sorts_mappings_and_preserves_ordered_sequences() -> None:
    first = {"outer": {"b": 2, "a": ["first", "second"]}, "width": 1024}
    second = {"width": 1024, "outer": {"a": ["first", "second"], "b": 2}}

    assert canonical_json(first) == canonical_json(second)
    assert content_digest(first) == content_digest(second)
    assert canonical_json(["first", "second"]) != canonical_json(["second", "first"])


def test_secret_shaped_and_unsupported_parameter_values_fail_closed() -> None:
    with pytest.raises(ValidationError, match="secret-shaped"):
        GenerationParameterV1.from_value("api_key", SECRET_SHAPED_PARAMETER["api_key"])
    with pytest.raises(ValueError, match="secret-shaped"):
        GenerationParameterV1.from_value("sampler", "sk-not-a-real-secret")
    with pytest.raises(ValueError, match="ordered sequences"):
        GenerationParameterV1.from_value("styles", {"ink", "tone"})


def test_canonical_parameter_storage_is_deterministic_for_nested_mappings() -> None:
    first = GenerationParameterV1.from_value("control", {"b": [2, 1], "a": {"z": True}})
    second = GenerationParameterV1.from_value("control", {"a": {"z": True}, "b": [2, 1]})

    assert first.canonical_value_json == second.canonical_value_json
    assert provider_request(parameter_value={"b": 2, "a": 1}).parameters[0].canonical_value_json == (
        '{"a":1,"b":2}'
    )


def test_malformed_schema_and_legacy_evidence_cannot_be_admitted() -> None:
    with pytest.raises(ValidationError):
        StoryboardEvidenceV1.model_validate(
            {
                **MALFORMED_VERSION,
                "storyboard_reference": "storyboard:malformed",
                "panels": (
                    StoryboardPanelV1(
                        panel_id="panel:1",
                        order=1,
                        purpose="setup",
                        scene="station",
                        action="arrive",
                    ),
                ),
            }
        )

    legacy = legacy_evidence_decision()
    assert LEGACY_PAGE["state"] == "PromptBuilt"
    assert legacy.status == "UNVERIFIED"
    assert legacy.manifest_digest is None
    with pytest.raises(ValidationError, match="requires a deterministic manifest"):
        GenerationAdmissionDecision(status="ADMITTED", reason_code="ADMISSION_EVIDENCE_COMPLETE")


def test_decision_contract_is_side_effect_free_and_state_machine_independent() -> None:
    decision = GenerationAdmissionDecision(
        status="REJECTED",
        reason_code="STORYBOARD_EVIDENCE_INVALID",
        manifest_digest=manifest().content_digest,
    )

    assert decision.state_machine_changed is False
    assert decision.provider_invocation_performed is False
    assert decision.external_side_effect_performed is False
    source = inspect.getsource(admission)
    assert "from manga_director.domain.state_machine" not in source
    assert "ProviderGenerationInvocationPort" not in source
    assert ".invoke(" not in source
    assert "import socket" not in source
    assert "import subprocess" not in source
    assert "from pathlib" not in source


def test_private_contract_is_not_exposed_through_frozen_public_exports() -> None:
    assert not hasattr(manga_director, "GenerationAdmissionManifestV1")
    assert not hasattr(production, "GenerationAdmissionManifestV1")


def test_digest_validators_reject_malformed_content_identity() -> None:
    with pytest.raises(ValidationError):
        SnapshotIdentityV1(revision=1, fingerprint="not-a-digest")
    with pytest.raises(ValidationError):
        PromptEvidenceV1(
            prompt_reference="prompt:one",
            prompt_content_digest=PROMPT_DIGEST,
            source_storyboard_digest="not-a-digest",
        )


def test_parameter_key_order_does_not_change_provider_request_identity() -> None:
    first = ProviderRequestBindingV1(
        provider_reference="provider:fixture",
        parameters=(
            GenerationParameterV1.from_value("height", 1536),
            GenerationParameterV1.from_value("width", 1024),
        ),
    )
    second = ProviderRequestBindingV1(
        provider_reference="provider:fixture",
        parameters=(
            GenerationParameterV1.from_value("width", 1024),
            GenerationParameterV1.from_value("height", 1536),
        ),
    )

    assert first.canonical_projection() == second.canonical_projection()
    assert manifest(provider=first).content_digest == manifest(provider=second).content_digest


def test_public_contract_source_state_is_fixed_without_state_machine_mutation() -> None:
    valid = manifest()
    values = valid.model_dump()
    values["source_state"] = "Generated"

    with pytest.raises(ValidationError):
        GenerationAdmissionManifestV1(**values)
    assert valid.source_state == "PromptBuilt"
