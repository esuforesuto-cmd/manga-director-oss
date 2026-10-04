"""Focused adversarial tests for the private D08 admission boundary."""

from __future__ import annotations

import copy

import pytest
from pydantic import ValidationError

import manga_director
import manga_director.production as production
from manga_director.production.future_provider_capability_profile import (
    CAPABILITY_NAMES,
    ProviderCapabilityClassificationV1,
    ProviderCapabilityEvidenceV1,
    ProviderCapabilityProfileV1,
    ValidatedCapabilityStateV1,
    classify_provider_capabilities,
    comfyui_capability_profile_fixture_v1,
)


def _evidence(
    capability: str,
    *,
    asserted_state: str = "SUPPORTED",
    provenance_state: str = "CURRENT",
    provider_revision: str = "provider:1",
    review_revision: str = "review:1",
    source_revision: str = "source:1",
    source_reference: str | None = None,
    suffix: str = "one",
) -> dict[str, object]:
    record: dict[str, object] = {
        "capability": capability,
        "asserted_state": asserted_state,
        "provenance_state": provenance_state,
    }
    if asserted_state == "SUPPORTED":
        record.update(
            {
                "source_reference": source_reference or f"test:source:{capability}:{suffix}",
                "claim_identifier": f"test:claim:{capability}:{suffix}",
                "source_digest": ("a" if suffix == "one" else "b") * 64,
                "provider_revision": provider_revision,
                "source_revision": source_revision,
                "review_revision": review_revision,
            }
        )
    return record


def _applicability(evidence: list[dict[str, object]]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for item in evidence:
        source_reference = item.get("source_reference")
        source_revision = item.get("source_revision")
        if source_reference is not None and source_revision is not None:
            record = {
                "source_reference": source_reference,
                "source_revision": source_revision,
                "provider_reference": "test:provider",
                "provider_revision": "provider:1",
                "review_revision": "review:1",
            }
            if record not in records:
                records.append(record)
    return records


def _raw_profile(
    *,
    duplicate_submit_semantics: str = "IDEMPOTENT_SAME_OPERATION",
    evidence: list[dict[str, object]] | None = None,
    applicability: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    supplied_evidence = evidence if evidence is not None else [
        _evidence(capability) for capability in CAPABILITY_NAMES
    ]
    return {
        "schema_name": "manga_director.future_provider_capability_profile",
        "schema_version": "1",
        "provider_reference": "test:provider",
        "provider_revision": "provider:1",
        "adapter_version": "fixture:1",
        "review_revision": "review:1",
        "profile_revision": 1,
        "duplicate_submit_semantics": duplicate_submit_semantics,
        "reviewed_source_applicability": (
            applicability if applicability is not None else _applicability(supplied_evidence)
        ),
        "evidence": supplied_evidence,
    }


def _class(raw_profile: dict[str, object]) -> str:
    return classify_provider_capabilities(raw_profile).provider_class


def _unsafe_supported_evidence() -> list[ProviderCapabilityEvidenceV1]:
    return [
        ProviderCapabilityEvidenceV1.model_construct(
            capability=capability,
            asserted_state="SUPPORTED",
            provenance_state="CURRENT",
        )
        for capability in CAPABILITY_NAMES
    ]


def test_valid_class_a_is_admitted_after_strict_raw_validation() -> None:
    assert _class(_raw_profile()) == "A"


def test_valid_class_b_is_admitted_without_safe_duplicate_semantics() -> None:
    evidence = [_evidence(capability) for capability in CAPABILITY_NAMES]
    evidence[2] = _evidence(
        "client_idempotency_identity",
        asserted_state="UNVERIFIED",
        provenance_state="UNVERIFIED",
    )
    raw = _raw_profile(duplicate_submit_semantics="REJECTED_NON_IDEMPOTENT", evidence=evidence)
    assert _class(raw) == "B"


def test_model_construct_candidate_cannot_be_classified_or_obtain_identity() -> None:
    unsafe = ProviderCapabilityProfileV1.model_construct(
        schema_name="manga_director.future_provider_capability_profile",
        schema_version="1",
        provider_reference="unsafe:provider",
        provider_revision="provider:1",
        adapter_version="unsafe:1",
        review_revision="review:1",
        profile_revision=1,
        duplicate_submit_semantics="IDEMPOTENT_SAME_OPERATION",
        evidence=_unsafe_supported_evidence(),
    )
    with pytest.raises(ValueError, match="primitive raw mapping"):
        classify_provider_capabilities(unsafe)


def test_model_copy_candidate_cannot_be_classified_or_obtain_identity() -> None:
    valid = ProviderCapabilityProfileV1.model_validate(comfyui_capability_profile_fixture_v1())
    unsafe = valid.model_copy(
        update={
            "duplicate_submit_semantics": "IDEMPOTENT_SAME_OPERATION",
            "evidence": _unsafe_supported_evidence(),
        }
    )
    with pytest.raises(ValueError, match="primitive raw mapping"):
        classify_provider_capabilities(unsafe)


def test_forged_classification_result_cannot_enter_authoritative_boundary() -> None:
    forged = ProviderCapabilityClassificationV1(
        profile_identity="fake:identity",
        provider_class="A",
        capability_states=(ValidatedCapabilityStateV1("submission", "SUPPORTED"),),
    )
    with pytest.raises(ValueError, match="primitive raw mapping"):
        classify_provider_capabilities(forged)


def test_caller_supplied_profile_identity_is_not_a_raw_authority_input() -> None:
    raw = _raw_profile()
    raw["profile_identity"] = "fake:identity"
    with pytest.raises(ValidationError, match="Extra inputs"):
        classify_provider_capabilities(raw)


def test_provenance_free_supported_evidence_is_rejected() -> None:
    evidence = [_evidence(capability) for capability in CAPABILITY_NAMES]
    evidence[0] = {
        "capability": "submission",
        "asserted_state": "SUPPORTED",
        "provenance_state": "CURRENT",
    }
    with pytest.raises(ValidationError, match="complete provenance"):
        classify_provider_capabilities(_raw_profile(evidence=evidence))


@pytest.mark.parametrize("field", ["arbitrary", "authorization", "api_key", "token"])
def test_unknown_raw_field_is_rejected_before_classification(field: str) -> None:
    raw = _raw_profile()
    raw[field] = "Bearer placeholder" if field == "authorization" else "placeholder"
    with pytest.raises((ValueError, ValidationError)):
        classify_provider_capabilities(raw)


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_reference", "api_key:placeholder"),
        ("source_reference", "https://user:pass@example.invalid"),
        ("claim_identifier", "https://example.invalid/?token=placeholder"),
        ("claim_identifier", "Bearer placeholder"),
    ],
)
def test_secret_shaped_evidence_is_rejected_before_normalization(field: str, value: str) -> None:
    raw = _raw_profile()
    evidence = copy.deepcopy(raw["evidence"])
    assert isinstance(evidence, list)
    evidence[0][field] = value
    raw["evidence"] = evidence
    with pytest.raises(ValueError, match="secret-shaped"):
        classify_provider_capabilities(raw)


@pytest.mark.parametrize("provenance_state", ["STALE", "CONFLICTING", "UNVERIFIED"])
def test_non_current_evidence_cannot_strengthen_classification(provenance_state: str) -> None:
    evidence = [_evidence(capability) for capability in CAPABILITY_NAMES]
    evidence[0] = _evidence("submission", provenance_state=provenance_state)
    assert _class(_raw_profile(evidence=evidence)) == "C"


def test_provider_revision_mismatch_cannot_strengthen_classification() -> None:
    evidence = [_evidence(capability) for capability in CAPABILITY_NAMES]
    evidence[0] = _evidence("submission", provider_revision="provider:other")
    assert _class(_raw_profile(evidence=evidence)) == "C"


def test_review_revision_mismatch_cannot_strengthen_classification() -> None:
    evidence = [_evidence(capability) for capability in CAPABILITY_NAMES]
    evidence[0] = _evidence("submission", review_revision="review:other")
    assert _class(_raw_profile(evidence=evidence)) == "C"


def test_wrong_source_revision_absent_from_manifest_cannot_strengthen() -> None:
    baseline = _raw_profile()
    evidence = copy.deepcopy(baseline["evidence"])
    applicability = copy.deepcopy(baseline["reviewed_source_applicability"])
    assert isinstance(evidence, list)
    assert isinstance(applicability, list)
    evidence[0]["source_revision"] = "source:other"
    assert _class(_raw_profile(evidence=evidence, applicability=applicability)) == "C"


def test_source_absent_from_manifest_cannot_strengthen() -> None:
    baseline = _raw_profile()
    evidence = copy.deepcopy(baseline["evidence"])
    applicability = copy.deepcopy(baseline["reviewed_source_applicability"])
    assert isinstance(evidence, list)
    assert isinstance(applicability, list)
    evidence[0]["source_reference"] = "test:source:unknown"
    assert _class(_raw_profile(evidence=evidence, applicability=applicability)) == "C"


def test_multiple_current_applicable_agreeing_sources_may_support_class_a() -> None:
    baseline = _raw_profile()
    evidence = copy.deepcopy(baseline["evidence"])
    applicability = copy.deepcopy(baseline["reviewed_source_applicability"])
    assert isinstance(evidence, list)
    assert isinstance(applicability, list)
    second = _evidence("submission", suffix="two")
    evidence.append(second)
    applicability.extend(_applicability([second]))
    assert _class(_raw_profile(evidence=evidence, applicability=applicability)) == "A"


def test_conflicting_source_claims_are_deterministically_class_c() -> None:
    evidence = [_evidence(capability) for capability in CAPABILITY_NAMES]
    evidence.append(
        _evidence(
            "submission",
            asserted_state="UNSUPPORTED",
            provenance_state="CURRENT",
            suffix="two",
        )
    )
    assert _class(_raw_profile(evidence=evidence)) == "C"


def test_unverified_evidence_cannot_strengthen_classification() -> None:
    evidence = [_evidence(capability) for capability in CAPABILITY_NAMES]
    evidence[0] = _evidence(
        "submission", asserted_state="UNVERIFIED", provenance_state="UNVERIFIED"
    )
    assert _class(_raw_profile(evidence=evidence)) == "C"


def test_comfyui_raw_fixture_is_class_c() -> None:
    result = classify_provider_capabilities(comfyui_capability_profile_fixture_v1())
    assert result.provider_class == "C"
    assert result.capability_states[0].state == "SUPPORTED"


def test_validated_identity_is_deterministic_and_order_neutral() -> None:
    first = _raw_profile()
    evidence = copy.deepcopy(first["evidence"])
    assert isinstance(evidence, list)
    second = _raw_profile(evidence=list(reversed(evidence)))
    first_result = classify_provider_capabilities(first)
    second_result = classify_provider_capabilities(second)
    assert first_result.profile_identity == second_result.profile_identity
    assert first_result.provider_class == second_result.provider_class


def test_changed_validated_evidence_changes_trusted_identity() -> None:
    first_result = classify_provider_capabilities(_raw_profile())
    evidence = [_evidence(capability) for capability in CAPABILITY_NAMES]
    evidence[0] = _evidence("submission", suffix="two")
    second_result = classify_provider_capabilities(_raw_profile(evidence=evidence))
    assert first_result.profile_identity != second_result.profile_identity


def test_changed_applicability_manifest_changes_trusted_identity() -> None:
    first = classify_provider_capabilities(_raw_profile())
    second = classify_provider_capabilities(
        _raw_profile(
            applicability=[
                *_applicability([_evidence(capability) for capability in CAPABILITY_NAMES]),
                {
                    "source_reference": "test:source:additional",
                    "source_revision": "source:additional",
                    "provider_reference": "test:provider",
                    "provider_revision": "provider:1",
                    "review_revision": "review:1",
                },
            ]
        )
    )
    assert first.profile_identity != second.profile_identity


def test_input_structure_is_not_mutated() -> None:
    raw = _raw_profile()
    original = copy.deepcopy(raw)
    classify_provider_capabilities(raw)
    assert raw == original


def test_d08_remains_private_and_unconnected_to_public_packages() -> None:
    assert not hasattr(manga_director, "ProviderCapabilityProfileV1")
    assert not hasattr(production, "ProviderCapabilityProfileV1")
