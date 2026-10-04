"""Focused tests for the pure future-generation admission evaluator."""

from __future__ import annotations

import inspect
from dataclasses import replace
from pathlib import Path

from generation_admission_v1_fixtures import manifest, provider_request, storyboard

import manga_director
import manga_director.production as production
from manga_director.production import future_generation_admission_evaluator as evaluator_module
from manga_director.production.future_generation_admission_contract import (
    GenerationAdmissionDecision,
    GenerationAdmissionManifestV1,
    GenerationParameterV1,
    PromptEvidenceV1,
    SnapshotIdentityV1,
    content_digest,
)
from manga_director.production.future_generation_admission_evaluator import (
    GenerationAdmissionCurrentEvidence,
    GenerationAdmissionEvaluator,
)


def _current_evidence(
    admitted_manifest: GenerationAdmissionManifestV1 | None = None,
) -> GenerationAdmissionCurrentEvidence:
    admitted = admitted_manifest or manifest()
    return GenerationAdmissionCurrentEvidence(
        project_id=admitted.project_id,
        page_id=admitted.page_id,
        execution_target_reference=admitted.execution_target_reference,
        workflow_state=admitted.source_state,
        snapshot=admitted.snapshot,
        storyboard=admitted.storyboard,
        prompt=admitted.prompt,
        provider_request=admitted.provider_request,
        attempt_id=admitted.attempt_id,
    )


def _evaluate(
    admitted_manifest: GenerationAdmissionManifestV1 | None = None,
    current: GenerationAdmissionCurrentEvidence | None = None,
) -> GenerationAdmissionDecision:
    admitted = admitted_manifest or manifest()
    evidence = current or _current_evidence(admitted)
    return GenerationAdmissionEvaluator().evaluate(admitted, evidence)


def test_complete_valid_evidence_is_admitted() -> None:
    result = _evaluate()

    assert result.status == "ADMITTED"
    assert result.reason_code == "ADMISSION_EVIDENCE_COMPLETE"


def test_promptbuilt_alone_and_wrong_workflow_state_are_not_admitted() -> None:
    admitted = manifest()
    promptbuilt_only = GenerationAdmissionCurrentEvidence(
        project_id=admitted.project_id,
        page_id=admitted.page_id,
        execution_target_reference=admitted.execution_target_reference,
        workflow_state="PromptBuilt",
        snapshot=None,
        storyboard=None,
        prompt=None,
        provider_request=None,
        attempt_id=admitted.attempt_id,
    )

    assert _evaluate(admitted, promptbuilt_only).status == "UNVERIFIED"
    wrong_state = replace(_current_evidence(admitted), workflow_state="Generated")
    assert _evaluate(admitted, wrong_state).reason_code == "WORKFLOW_STATE_MISMATCH"


def test_empty_or_unavailable_storyboard_is_not_admitted() -> None:
    admitted = manifest()
    empty = replace(_current_evidence(admitted), storyboard={"panels": []})
    unavailable = replace(_current_evidence(admitted), storyboard=None)

    assert _evaluate(admitted, empty).status == "REJECTED"
    assert _evaluate(admitted, empty).reason_code == "STORYBOARD_EVIDENCE_INVALID"
    assert _evaluate(admitted, unavailable).status == "UNVERIFIED"


def test_storyboard_and_snapshot_changes_are_rejected_as_stale() -> None:
    admitted = manifest()
    changed_storyboard = replace(_current_evidence(admitted), storyboard=storyboard(panel_count=2))
    changed_snapshot = replace(
        _current_evidence(admitted),
        snapshot=SnapshotIdentityV1(revision=8, fingerprint=admitted.snapshot.fingerprint),
    )

    assert _evaluate(admitted, changed_storyboard).reason_code == "STALE_ADMISSION"
    assert _evaluate(admitted, changed_snapshot).reason_code == "STALE_ADMISSION"


def test_prompt_changes_and_stale_provenance_are_rejected() -> None:
    admitted = manifest()
    changed_prompt = PromptEvidenceV1(
        prompt_reference=admitted.prompt.prompt_reference,
        prompt_content_digest=content_digest({"prompt": "new"}),
        source_storyboard_digest=admitted.storyboard.content_digest,
    )
    stale_provenance = PromptEvidenceV1(
        prompt_reference=admitted.prompt.prompt_reference,
        prompt_content_digest=admitted.prompt.prompt_content_digest,
        source_storyboard_digest=content_digest({"storyboard": "old"}),
    )

    assert _evaluate(admitted, replace(_current_evidence(admitted), prompt=changed_prompt)).reason_code == (
        "PROMPT_EVIDENCE_MISMATCH"
    )
    assert _evaluate(admitted, replace(_current_evidence(admitted), prompt=stale_provenance)).reason_code == (
        "PROMPT_PROVENANCE_STALE"
    )


def test_provider_model_workflow_and_parameter_substitution_are_rejected() -> None:
    admitted = manifest()
    provider_changed = admitted.provider_request.model_copy(update={"provider_reference": "provider:other"})
    model_changed = admitted.provider_request.model_copy(update={"model_id": "model:other"})
    workflow_changed = admitted.provider_request.model_copy(update={"workflow_id": "workflow:other"})
    parameters_changed = provider_request(parameter_value=768)

    assert _evaluate(admitted, replace(_current_evidence(admitted), provider_request=provider_changed)).reason_code == (
        "PROVIDER_REFERENCE_MISMATCH"
    )
    assert _evaluate(admitted, replace(_current_evidence(admitted), provider_request=model_changed)).reason_code == (
        "MODEL_BINDING_MISMATCH"
    )
    assert _evaluate(admitted, replace(_current_evidence(admitted), provider_request=workflow_changed)).reason_code == (
        "WORKFLOW_BINDING_MISMATCH"
    )
    assert _evaluate(admitted, replace(_current_evidence(admitted), provider_request=parameters_changed)).reason_code == (
        "PARAMETER_BINDING_MISMATCH"
    )


def test_attempt_and_secret_shaped_runtime_input_are_rejected() -> None:
    admitted = manifest()
    changed_attempt = replace(_current_evidence(admitted), attempt_id="attempt:other")
    secret_parameter = replace(
        _current_evidence(admitted),
        provider_request={"sampler": "safe", "credential": "not-a-real-secret"},
    )

    assert _evaluate(admitted, changed_attempt).reason_code == "ATTEMPT_ID_MISMATCH"
    assert _evaluate(admitted, secret_parameter).reason_code == "SECRET_SHAPED_PROVIDER_REQUEST"


def test_legacy_or_unsupported_evidence_remains_unverified() -> None:
    admitted = manifest()
    legacy = GenerationAdmissionCurrentEvidence(
        project_id=admitted.project_id,
        page_id=admitted.page_id,
        execution_target_reference=admitted.execution_target_reference,
        workflow_state="PromptBuilt",
        snapshot=None,
        storyboard={},
        prompt={"prompt_markdown": "legacy"},
        provider_request=None,
        attempt_id=admitted.attempt_id,
    )

    result = _evaluate(admitted, legacy)
    assert result.status == "UNVERIFIED"
    assert result.reason_code == "SNAPSHOT_EVIDENCE_UNAVAILABLE"


def test_identical_inputs_produce_identical_non_mutating_decisions() -> None:
    admitted = manifest()
    current = _current_evidence(admitted)
    manifest_before = admitted.model_dump(mode="json")
    current_before = current

    first = _evaluate(admitted, current)
    second = _evaluate(admitted, current)

    assert first == second
    assert admitted.model_dump(mode="json") == manifest_before
    assert current == current_before


def test_evaluator_has_no_provider_or_external_side_effect_surface(tmp_path: Path) -> None:
    before = tuple(tmp_path.iterdir())
    result = _evaluate()
    source = inspect.getsource(evaluator_module)

    assert result.provider_invocation_performed is False
    assert result.external_side_effect_performed is False
    assert tuple(tmp_path.iterdir()) == before
    assert "ProviderGenerationInvocationPort" not in source
    assert ".invoke(" not in source
    assert "import socket" not in source
    assert "import subprocess" not in source
    assert "from pathlib" not in source
    assert "sqlite" not in source.lower()


def test_state_machine_and_public_exports_remain_unchanged() -> None:
    source = inspect.getsource(evaluator_module)

    assert "from manga_director.domain.state_machine" not in source
    assert not hasattr(manga_director, "GenerationAdmissionEvaluator")
    assert not hasattr(production, "GenerationAdmissionEvaluator")


def test_malformed_current_input_cannot_be_admitted() -> None:
    result = GenerationAdmissionEvaluator().evaluate(manifest(), object())

    assert result.status == "UNVERIFIED"
    assert result.reason_code == "CURRENT_EVIDENCE_UNSUPPORTED"
    assert GenerationParameterV1.from_value("width", 1024).key == "width"
