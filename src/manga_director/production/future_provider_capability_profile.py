"""Private, provider-free capability-profile admission and classification.

Only primitive raw mappings can cross the authoritative admission boundary.
Pydantic model instances are deliberately not trusted classification input.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Final, Literal, TypeAlias, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CapabilityState: TypeAlias = Literal["SUPPORTED", "UNSUPPORTED", "UNVERIFIED"]
ProviderCapabilityClass: TypeAlias = Literal["A", "B", "C"]
ProvenanceState: TypeAlias = Literal["CURRENT", "STALE", "CONFLICTING", "UNVERIFIED"]
DuplicateSubmitSemantics: TypeAlias = Literal[
    "IDEMPOTENT_SAME_OPERATION",
    "CONFLICT_RECONCILABLE",
    "REJECTED_NON_IDEMPOTENT",
    "UNSUPPORTED",
    "UNVERIFIED",
]
CapabilityName: TypeAlias = Literal[
    "submission",
    "provider_request_identity",
    "client_idempotency_identity",
    "duplicate_submit_semantics",
    "status_reconciliation",
    "result_lookup",
    "cancellation",
    "restart_safe_retention",
]

CAPABILITY_NAMES: Final[tuple[CapabilityName, ...]] = (
    "submission",
    "provider_request_identity",
    "client_idempotency_identity",
    "duplicate_submit_semantics",
    "status_reconciliation",
    "result_lookup",
    "cancellation",
    "restart_safe_retention",
)
_CAPABILITY_ORDER: Final[dict[CapabilityName, int]] = {
    capability: index for index, capability in enumerate(CAPABILITY_NAMES)
}
_SAFE_DUPLICATE_SEMANTICS: Final[frozenset[DuplicateSubmitSemantics]] = frozenset(
    {"IDEMPOTENT_SAME_OPERATION", "CONFLICT_RECONCILABLE"}
)
_IDENTIFIER_PATTERN: Final[re.Pattern[str]] = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,159}")
_DIGEST_PATTERN: Final[re.Pattern[str]] = re.compile(r"[0-9a-f]{64}")
_SECRET_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"api[_-]?key|authorization|credential|password|secret|bearer|token|sk-[A-Za-z0-9_-]{8,}",
    re.IGNORECASE,
)
_CREDENTIAL_URL_PATTERN: Final[re.Pattern[str]] = re.compile(r"://[^/\s:@]+:[^/\s@]+@")
_SECRET_QUERY_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"[?&](?:api[_-]?key|authorization|credential|password|secret|token)=",
    re.IGNORECASE,
)
_MAX_RAW_DEPTH: Final[int] = 12
_MAX_RAW_COLLECTION_SIZE: Final[int] = 64


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True, allow_nan=False)


def _identity(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _validate_logical_identifier(value: str, field_name: str) -> str:
    if not _IDENTIFIER_PATTERN.fullmatch(value) or _SECRET_PATTERN.search(value):
        raise ValueError(f"{field_name} must be a bounded non-secret logical identifier")
    return value


def _scan_raw(value: object, depth: int = 0) -> None:
    """Reject unsupported and secret-bearing raw values before normalization."""

    if depth > _MAX_RAW_DEPTH:
        raise ValueError("raw profile exceeds the maximum nesting depth")
    if isinstance(value, str):
        if (
            _SECRET_PATTERN.search(value)
            or _CREDENTIAL_URL_PATTERN.search(value)
            or _SECRET_QUERY_PATTERN.search(value)
        ):
            raise ValueError("raw profile contains a secret-shaped value")
        return
    if value is None or type(value) in {bool, int}:
        return
    if type(value) is list:
        raw_list = cast(list[object], value)
        if len(raw_list) > _MAX_RAW_COLLECTION_SIZE:
            raise ValueError("raw profile collection exceeds the maximum size")
        for item in raw_list:
            _scan_raw(item, depth + 1)
        return
    if type(value) is dict:
        raw_dict = cast(dict[object, object], value)
        if len(raw_dict) > _MAX_RAW_COLLECTION_SIZE:
            raise ValueError("raw profile collection exceeds the maximum size")
        for key, item in raw_dict.items():
            if type(key) is not str:
                raise ValueError("raw profile keys must be strings")
            _scan_raw(key, depth + 1)
            _scan_raw(item, depth + 1)
        return
    raise ValueError("raw profile contains an unsupported value type")


def _raw_mapping(candidate: object) -> dict[str, object]:
    if type(candidate) is not dict:
        raise ValueError("provider capability classification accepts only a primitive raw mapping")
    raw = cast(dict[object, object], candidate)
    if any(type(key) is not str for key in raw):
        raise ValueError("provider capability profile keys must be strings")
    primitive_mapping = cast(dict[str, object], raw)
    _scan_raw(primitive_mapping)
    return primitive_mapping


class _StrictD08Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ProviderCapabilityEvidenceV1(_StrictD08Model):
    """One bounded, non-secret source claim for a provider capability."""

    capability: CapabilityName
    asserted_state: CapabilityState
    provenance_state: ProvenanceState
    source_reference: str | None = None
    claim_identifier: str | None = None
    source_digest: str | None = None
    provider_revision: str | None = None
    source_revision: str | None = None
    review_revision: str | None = None

    @field_validator(
        "source_reference",
        "claim_identifier",
        "provider_revision",
        "source_revision",
        "review_revision",
    )
    @classmethod
    def _logical_identifier(cls, value: str | None, info: object) -> str | None:
        if value is None:
            return None
        return _validate_logical_identifier(value, str(getattr(info, "field_name", "identifier")))

    @field_validator("source_digest")
    @classmethod
    def _digest(cls, value: str | None) -> str | None:
        if value is not None and not _DIGEST_PATTERN.fullmatch(value):
            raise ValueError("source_digest must be a lowercase SHA-256 digest")
        return value

    @model_validator(mode="after")
    def _supported_requires_complete_provenance(self) -> ProviderCapabilityEvidenceV1:
        provenance_fields = (
            self.source_reference,
            self.claim_identifier,
            self.source_digest,
            self.provider_revision,
            self.source_revision,
            self.review_revision,
        )
        if self.asserted_state == "SUPPORTED" and any(value is None for value in provenance_fields):
            raise ValueError("SUPPORTED evidence requires complete provenance")
        if any(value is not None for value in provenance_fields) and any(
            value is None for value in provenance_fields
        ):
            raise ValueError("provenance must be complete when any provenance field is supplied")
        return self

    @property
    def canonical_projection(self) -> dict[str, object]:
        return self.model_dump(mode="json")


class ReviewedSourceApplicabilityV1(_StrictD08Model):
    """A reviewed exact source-to-provider applicability declaration."""

    source_reference: str
    source_revision: str
    provider_reference: str
    provider_revision: str
    review_revision: str

    @field_validator(
        "source_reference",
        "source_revision",
        "provider_reference",
        "provider_revision",
        "review_revision",
    )
    @classmethod
    def _logical_identifier(cls, value: str, info: object) -> str:
        return _validate_logical_identifier(value, str(getattr(info, "field_name", "identifier")))

    @property
    def applicability_key(self) -> tuple[str, str, str, str, str]:
        return (
            self.source_reference,
            self.source_revision,
            self.provider_reference,
            self.provider_revision,
            self.review_revision,
        )


class ProviderCapabilityProfileV1(_StrictD08Model):
    """Strict raw profile schema with no trusted identity or classification."""

    schema_name: Literal["manga_director.future_provider_capability_profile"] = (
        "manga_director.future_provider_capability_profile"
    )
    schema_version: Literal["1"] = "1"
    provider_reference: str
    provider_revision: str
    adapter_version: str
    review_revision: str
    profile_revision: int = Field(ge=1)
    duplicate_submit_semantics: DuplicateSubmitSemantics
    reviewed_source_applicability: list[ReviewedSourceApplicabilityV1]
    evidence: list[ProviderCapabilityEvidenceV1]

    @field_validator("provider_reference", "provider_revision", "adapter_version", "review_revision")
    @classmethod
    def _profile_identifier(cls, value: str, info: object) -> str:
        return _validate_logical_identifier(value, str(getattr(info, "field_name", "identifier")))

    @field_validator("reviewed_source_applicability")
    @classmethod
    def _canonical_applicability(
        cls, applicability: list[ReviewedSourceApplicabilityV1]
    ) -> list[ReviewedSourceApplicabilityV1]:
        keys = tuple(item.applicability_key for item in applicability)
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate reviewed applicability records are not permitted")
        return sorted(applicability, key=lambda item: item.applicability_key)

    @field_validator("evidence")
    @classmethod
    def _complete_non_duplicate_evidence(
        cls, evidence: list[ProviderCapabilityEvidenceV1]
    ) -> list[ProviderCapabilityEvidenceV1]:
        capabilities = {item.capability for item in evidence}
        if capabilities != set(CAPABILITY_NAMES):
            raise ValueError("evidence must cover the complete V1 capability set")
        keys = tuple(
            (
                item.capability,
                item.asserted_state,
                item.provenance_state,
                item.source_reference,
                item.claim_identifier,
                item.source_digest,
                item.provider_revision,
                item.source_revision,
                item.review_revision,
            )
            for item in evidence
        )
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate evidence records are not permitted")
        return sorted(
            evidence,
            key=lambda item: (
                _CAPABILITY_ORDER[item.capability],
                _canonical_json(item.canonical_projection),
            ),
        )


@dataclass(frozen=True)
class ValidatedCapabilityStateV1:
    """A capability state produced only by authoritative D08 admission."""

    capability: CapabilityName
    state: CapabilityState


@dataclass(frozen=True)
class ProviderCapabilityClassificationV1:
    """Trusted D08 result for future internal consumers such as D09."""

    profile_identity: str
    provider_class: ProviderCapabilityClass
    capability_states: tuple[ValidatedCapabilityStateV1, ...]


@dataclass(frozen=True)
class _ValidatedProviderCapabilityProfileV1:
    profile: ProviderCapabilityProfileV1
    capability_states: tuple[ValidatedCapabilityStateV1, ...]
    profile_identity: str


def _is_current_and_applicable(
    item: ProviderCapabilityEvidenceV1, profile: ProviderCapabilityProfileV1
) -> bool:
    if (
        item.provenance_state != "CURRENT"
        or item.source_reference is None
        or item.source_revision is None
        or item.provider_revision != profile.provider_revision
        or item.review_revision != profile.review_revision
    ):
        return False
    evidence_key = (
        item.source_reference,
        item.source_revision,
        profile.provider_reference,
        profile.provider_revision,
        profile.review_revision,
    )
    return evidence_key in {record.applicability_key for record in profile.reviewed_source_applicability}


def _resolved_state(
    capability: CapabilityName, profile: ProviderCapabilityProfileV1
) -> ValidatedCapabilityStateV1:
    records = tuple(item for item in profile.evidence if item.capability == capability)
    states = {item.asserted_state for item in records}
    if len(states) != 1 or not records:
        return ValidatedCapabilityStateV1(capability=capability, state="UNVERIFIED")
    if not all(_is_current_and_applicable(item, profile) for item in records):
        return ValidatedCapabilityStateV1(capability=capability, state="UNVERIFIED")
    return ValidatedCapabilityStateV1(capability=capability, state=records[0].asserted_state)


def _validated_profile(candidate: object) -> _ValidatedProviderCapabilityProfileV1:
    raw = _raw_mapping(candidate)
    profile = ProviderCapabilityProfileV1.model_validate(raw, strict=True)
    canonical_raw = profile.model_dump(mode="json")
    canonical_profile = ProviderCapabilityProfileV1.model_validate(canonical_raw, strict=True)
    states = tuple(_resolved_state(capability, canonical_profile) for capability in CAPABILITY_NAMES)
    projection = {
        "profile": canonical_profile.model_dump(mode="json"),
        "resolved_capability_states": [
            {"capability": state.capability, "state": state.state} for state in states
        ],
    }
    return _ValidatedProviderCapabilityProfileV1(
        profile=canonical_profile,
        capability_states=states,
        profile_identity=_identity(projection),
    )


def _state_map(states: tuple[ValidatedCapabilityStateV1, ...]) -> dict[CapabilityName, CapabilityState]:
    return {state.capability: state.state for state in states}


def classify_provider_capabilities(candidate: object) -> ProviderCapabilityClassificationV1:
    """Classify raw mappings; direct result construction never establishes authority.

    Future security-relevant consumers must invoke this function from their
    own raw-input composition and must not accept result objects as input.
    """

    validated = _validated_profile(candidate)
    states = _state_map(validated.capability_states)
    class_a_capabilities: tuple[CapabilityName, ...] = (
        "submission",
        "provider_request_identity",
        "client_idempotency_identity",
        "duplicate_submit_semantics",
        "status_reconciliation",
        "result_lookup",
        "restart_safe_retention",
    )
    class_b_capabilities: tuple[CapabilityName, ...] = (
        "submission",
        "provider_request_identity",
        "status_reconciliation",
        "result_lookup",
        "restart_safe_retention",
    )
    if all(states[name] == "SUPPORTED" for name in class_a_capabilities) and (
        validated.profile.duplicate_submit_semantics in _SAFE_DUPLICATE_SEMANTICS
    ):
        provider_class: ProviderCapabilityClass = "A"
    elif all(states[name] == "SUPPORTED" for name in class_b_capabilities) and (
        validated.profile.duplicate_submit_semantics not in _SAFE_DUPLICATE_SEMANTICS
    ):
        provider_class = "B"
    else:
        provider_class = "C"
    return ProviderCapabilityClassificationV1(
        profile_identity=validated.profile_identity,
        provider_class=provider_class,
        capability_states=validated.capability_states,
    )


def _fixture_digest(reference: str, claim: str) -> str:
    return _identity({"reference": reference, "claim": claim})


def comfyui_capability_profile_fixture_v1() -> dict[str, object]:
    """Return a raw static fixture; it makes no live ComfyUI query."""

    documented = {
        "submission": "route-prompt",
        "provider_request_identity": "prompt-id",
        "status_reconciliation": "queue-history-websocket",
        "result_lookup": "history-output",
        "cancellation": "route-interrupt",
    }
    evidence: list[dict[str, object]] = []
    applicability: list[dict[str, object]] = []
    for capability in CAPABILITY_NAMES:
        if capability in documented:
            claim = documented[capability]
            evidence.append(
                {
                    "capability": capability,
                    "asserted_state": "SUPPORTED",
                    "provenance_state": "CURRENT",
                    "source_reference": "accepted:comfyui:static-docs",
                    "claim_identifier": claim,
                    "source_digest": _fixture_digest("accepted:comfyui:static-docs", claim),
                    "provider_revision": "comfyui:static",
                    "source_revision": "d06-d07:accepted",
                    "review_revision": "d08:1",
                }
            )
            if not applicability:
                applicability.append(
                    {
                        "source_reference": "accepted:comfyui:static-docs",
                        "source_revision": "d06-d07:accepted",
                        "provider_reference": "comfyui:static-profile",
                        "provider_revision": "comfyui:static",
                        "review_revision": "d08:1",
                    }
                )
        else:
            evidence.append(
                {
                    "capability": capability,
                    "asserted_state": "UNVERIFIED",
                    "provenance_state": "UNVERIFIED",
                }
            )
    return {
        "schema_name": "manga_director.future_provider_capability_profile",
        "schema_version": "1",
        "provider_reference": "comfyui:static-profile",
        "provider_revision": "comfyui:static",
        "adapter_version": "fixture:1",
        "review_revision": "d08:1",
        "profile_revision": 1,
        "duplicate_submit_semantics": "UNVERIFIED",
        "reviewed_source_applicability": applicability,
        "evidence": evidence,
    }
