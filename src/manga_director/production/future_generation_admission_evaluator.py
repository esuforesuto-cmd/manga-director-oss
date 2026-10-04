"""Pure, private evaluation of current evidence against an admission manifest.

The evaluator is a pre-provider decision boundary only.  It does not read or
write external state, invoke a provider, or advance a workflow.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from manga_director.production.future_generation_admission_contract import (
    AdmissionDecisionStatus,
    GenerationAdmissionDecision,
    GenerationAdmissionManifestV1,
    PromptEvidenceV1,
    ProviderRequestBindingV1,
    SnapshotIdentityV1,
    StoryboardEvidenceV1,
)

_SECRET_KEY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "endpoint",
    "password",
    "secret",
    "token",
)
_SECRET_VALUE = re.compile(
    r"(?:\Ask-[A-Za-z0-9_-]{8,}\Z|\Agh[pousr]_[A-Za-z0-9_-]{8,}\Z|\Abearer\s+\S+)",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class GenerationAdmissionCurrentEvidence:
    """Explicit, caller-owned current evidence; the evaluator never fetches state."""

    project_id: object
    page_id: object
    execution_target_reference: object
    workflow_state: object
    snapshot: object
    storyboard: object
    prompt: object
    provider_request: object
    attempt_id: object


class GenerationAdmissionEvaluator:
    """Compare one manifest with supplied current evidence, fail-closed and without effects."""

    def evaluate(
        self,
        manifest: object,
        current_evidence: object,
    ) -> GenerationAdmissionDecision:
        if not isinstance(manifest, GenerationAdmissionManifestV1):
            return _decision("UNVERIFIED", "MANIFEST_EVIDENCE_UNSUPPORTED")
        if not isinstance(current_evidence, GenerationAdmissionCurrentEvidence):
            return _decision("UNVERIFIED", "CURRENT_EVIDENCE_UNSUPPORTED", manifest)
        return _evaluate_manifest(manifest, current_evidence)


def _evaluate_manifest(
    manifest: GenerationAdmissionManifestV1,
    current: GenerationAdmissionCurrentEvidence,
) -> GenerationAdmissionDecision:
    for evaluation in (
        _identity_decision,
        _workflow_decision,
        _snapshot_decision,
        _storyboard_decision,
        _prompt_decision,
        _provider_request_decision,
    ):
        decision = evaluation(manifest, current)
        if decision is not None:
            return decision
    return _decision("ADMITTED", "ADMISSION_EVIDENCE_COMPLETE", manifest)


def _identity_decision(
    manifest: GenerationAdmissionManifestV1,
    current: GenerationAdmissionCurrentEvidence,
) -> GenerationAdmissionDecision | None:
    identifiers = (
        ("project_id", current.project_id, manifest.project_id, "PROJECT_ID_MISMATCH"),
        ("page_id", current.page_id, manifest.page_id, "PAGE_ID_MISMATCH"),
        (
            "execution target",
            current.execution_target_reference,
            manifest.execution_target_reference,
            "EXECUTION_TARGET_MISMATCH",
        ),
        ("attempt_id", current.attempt_id, manifest.attempt_id, "ATTEMPT_ID_MISMATCH"),
    )
    for label, actual, expected, mismatch_code in identifiers:
        if not _is_nonblank_string(actual):
            return _decision("UNVERIFIED", f"{label.upper().replace(' ', '_')}_UNAVAILABLE", manifest)
        if actual != expected:
            return _decision("REJECTED", mismatch_code, manifest)
    return None


def _workflow_decision(
    manifest: GenerationAdmissionManifestV1,
    current: GenerationAdmissionCurrentEvidence,
) -> GenerationAdmissionDecision | None:

    if not _is_nonblank_string(current.workflow_state):
        return _decision("UNVERIFIED", "WORKFLOW_STATE_UNAVAILABLE", manifest)
    if current.workflow_state != manifest.source_state:
        return _decision("REJECTED", "WORKFLOW_STATE_MISMATCH", manifest)
    return None


def _snapshot_decision(
    manifest: GenerationAdmissionManifestV1,
    current: GenerationAdmissionCurrentEvidence,
) -> GenerationAdmissionDecision | None:

    if not isinstance(current.snapshot, SnapshotIdentityV1):
        return _decision("UNVERIFIED", "SNAPSHOT_EVIDENCE_UNAVAILABLE", manifest)
    if current.snapshot != manifest.snapshot:
        return _decision("REJECTED", "STALE_ADMISSION", manifest)
    return None


def _storyboard_decision(
    manifest: GenerationAdmissionManifestV1,
    current: GenerationAdmissionCurrentEvidence,
) -> GenerationAdmissionDecision | None:

    if not isinstance(current.storyboard, StoryboardEvidenceV1):
        if _is_empty_storyboard(current.storyboard):
            return _decision("REJECTED", "STORYBOARD_EVIDENCE_INVALID", manifest)
        return _decision("UNVERIFIED", "STORYBOARD_EVIDENCE_UNAVAILABLE", manifest)
    if current.storyboard.content_digest != manifest.storyboard.content_digest:
        return _decision("REJECTED", "STALE_ADMISSION", manifest)
    return None


def _prompt_decision(
    manifest: GenerationAdmissionManifestV1,
    current: GenerationAdmissionCurrentEvidence,
) -> GenerationAdmissionDecision | None:
    if not isinstance(current.prompt, PromptEvidenceV1):
        return _decision("UNVERIFIED", "PROMPT_EVIDENCE_UNAVAILABLE", manifest)
    if not isinstance(current.storyboard, StoryboardEvidenceV1):
        return _decision("UNVERIFIED", "STORYBOARD_EVIDENCE_UNAVAILABLE", manifest)
    if current.prompt.source_storyboard_digest != current.storyboard.content_digest:
        return _decision("REJECTED", "PROMPT_PROVENANCE_STALE", manifest)
    if current.prompt != manifest.prompt:
        return _decision("REJECTED", "PROMPT_EVIDENCE_MISMATCH", manifest)
    return None


def _provider_request_decision(
    manifest: GenerationAdmissionManifestV1,
    current: GenerationAdmissionCurrentEvidence,
) -> GenerationAdmissionDecision | None:

    if not isinstance(current.provider_request, ProviderRequestBindingV1):
        if _contains_secret_shaped_value(current.provider_request):
            return _decision("REJECTED", "SECRET_SHAPED_PROVIDER_REQUEST", manifest)
        return _decision("UNVERIFIED", "PROVIDER_REQUEST_UNAVAILABLE", manifest)
    provider_decision = _provider_binding_decision(manifest, current.provider_request)
    if provider_decision is not None:
        return provider_decision
    return None


def _provider_binding_decision(
    manifest: GenerationAdmissionManifestV1,
    current: ProviderRequestBindingV1,
) -> GenerationAdmissionDecision | None:
    admitted = manifest.provider_request
    if current.provider_reference != admitted.provider_reference:
        return _decision("REJECTED", "PROVIDER_REFERENCE_MISMATCH", manifest)
    if (current.model_id, current.model_version) != (admitted.model_id, admitted.model_version):
        return _decision("REJECTED", "MODEL_BINDING_MISMATCH", manifest)
    if (
        current.workflow_id,
        current.workflow_version,
        current.workflow_content_digest,
    ) != (
        admitted.workflow_id,
        admitted.workflow_version,
        admitted.workflow_content_digest,
    ):
        return _decision("REJECTED", "WORKFLOW_BINDING_MISMATCH", manifest)
    if current.plugin_reference != admitted.plugin_reference:
        return _decision("REJECTED", "PLUGIN_BINDING_MISMATCH", manifest)
    if current.parameters != admitted.parameters:
        return _decision("REJECTED", "PARAMETER_BINDING_MISMATCH", manifest)
    return None


def _decision(
    status: AdmissionDecisionStatus,
    reason_code: str,
    manifest: GenerationAdmissionManifestV1 | None = None,
) -> GenerationAdmissionDecision:
    return GenerationAdmissionDecision(
        status=status,
        reason_code=reason_code,
        manifest_digest=manifest.content_digest if manifest is not None else None,
    )


def _is_nonblank_string(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip()


def _is_empty_storyboard(value: object) -> bool:
    return isinstance(value, Mapping) and value.get("panels") in ((), [])


def _contains_secret_shaped_value(value: object) -> bool:
    if isinstance(value, str):
        return _SECRET_VALUE.search(value) is not None
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if not isinstance(key, str) or any(part in key.lower() for part in _SECRET_KEY_PARTS):
                return True
            if _contains_secret_shaped_value(nested):
                return True
        return False
    if isinstance(value, (list, tuple)):
        return any(_contains_secret_shaped_value(item) for item in value)
    return False
