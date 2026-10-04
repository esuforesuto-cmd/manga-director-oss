"""Private, standalone future-generation admission evidence contract.

This module represents deterministic pre-provider evidence only.  It has no
provider, workflow, persistence, filesystem, or StateMachine integration.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from typing import Literal, TypeAlias

from pydantic import ConfigDict, Field, field_validator

from manga_director.production.director import DirectorModel

AdmissionDecisionStatus = Literal["ADMITTED", "REJECTED", "UNVERIFIED"]
CanonicalValue: TypeAlias = (
    None | bool | int | float | str | tuple["CanonicalValue", ...] | dict[str, "CanonicalValue"]
)

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
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
_WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:[\\/]")


class _AdmissionContractModel(DirectorModel):
    """Closed immutable base for the future-only contract."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class SnapshotIdentityV1(_AdmissionContractModel):
    """Authoritative page snapshot identity captured before provider work."""

    revision: int = Field(ge=0)
    fingerprint: str

    @field_validator("fingerprint")
    @classmethod
    def _validate_fingerprint(cls, value: str) -> str:
        return _sha256(value, "snapshot fingerprint")


class CharacterIdentityReferenceV1(_AdmissionContractModel):
    """Optional, supplied character identity binding for one storyboard panel."""

    character_id: str
    identity_id: str
    identity_version: str

    @field_validator("character_id", "identity_id", "identity_version")
    @classmethod
    def _validate_identity_reference(cls, value: str) -> str:
        return _logical_reference(value, "identity reference")


class StoryboardPanelV1(_AdmissionContractModel):
    """The minimum generation-relevant, ordered panel evidence."""

    panel_id: str
    order: int = Field(ge=1)
    purpose: str
    scene: str
    action: str
    character_identity_references: tuple[CharacterIdentityReferenceV1, ...] = ()
    reference_asset_ids: tuple[str, ...] = ()

    @field_validator("panel_id")
    @classmethod
    def _validate_panel_id(cls, value: str) -> str:
        return _logical_reference(value, "panel identity")

    @field_validator("purpose", "scene", "action")
    @classmethod
    def _validate_panel_content(cls, value: str) -> str:
        return _nonblank_text(value, "panel evidence")

    @field_validator("reference_asset_ids")
    @classmethod
    def _validate_reference_assets(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        validated = tuple(_logical_reference(value, "reference asset") for value in values)
        if len(set(validated)) != len(validated):
            raise ValueError("reference asset identities must be unique within a panel")
        return tuple(sorted(validated))

    def model_post_init(self, __context: object) -> None:
        bindings = tuple(
            (item.character_id, item.identity_id, item.identity_version)
            for item in self.character_identity_references
        )
        if len(set(bindings)) != len(bindings):
            raise ValueError("character identity references must be unique within a panel")


class StoryboardEvidenceV1(_AdmissionContractModel):
    """Versioned storyboard evidence whose panel order is significant."""

    schema_id: str
    schema_version: str
    storyboard_reference: str
    panels: tuple[StoryboardPanelV1, ...]

    @field_validator("schema_id", "schema_version", "storyboard_reference")
    @classmethod
    def _validate_storyboard_reference(cls, value: str) -> str:
        return _logical_reference(value, "storyboard evidence reference")

    @field_validator("panels")
    @classmethod
    def _validate_panels(
        cls, values: tuple[StoryboardPanelV1, ...]
    ) -> tuple[StoryboardPanelV1, ...]:
        if not values:
            raise ValueError("storyboard evidence requires at least one panel")
        panel_ids = tuple(item.panel_id for item in values)
        if len(set(panel_ids)) != len(panel_ids):
            raise ValueError("storyboard panel identities must be unique")
        orders = tuple(item.order for item in values)
        if orders != tuple(range(1, len(values) + 1)):
            raise ValueError("storyboard panels must be supplied in contiguous deterministic order")
        return values

    @property
    def content_digest(self) -> str:
        return content_digest(self.canonical_projection())

    def canonical_projection(self) -> dict[str, CanonicalValue]:
        return {
            "panels": tuple(
                {
                    "action": panel.action,
                    "character_identity_references": tuple(
                        {
                            "character_id": binding.character_id,
                            "identity_id": binding.identity_id,
                            "identity_version": binding.identity_version,
                        }
                        for binding in panel.character_identity_references
                    ),
                    "order": panel.order,
                    "panel_id": panel.panel_id,
                    "purpose": panel.purpose,
                    "reference_asset_ids": panel.reference_asset_ids,
                    "scene": panel.scene,
                }
                for panel in self.panels
            ),
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "storyboard_reference": self.storyboard_reference,
        }


class PromptEvidenceV1(_AdmissionContractModel):
    """Redacted prompt identity and its required source-storyboard binding."""

    prompt_reference: str
    prompt_content_digest: str
    source_storyboard_digest: str

    @field_validator("prompt_reference")
    @classmethod
    def _validate_prompt_reference(cls, value: str) -> str:
        return _logical_reference(value, "prompt reference")

    @field_validator("prompt_content_digest", "source_storyboard_digest")
    @classmethod
    def _validate_prompt_digest(cls, value: str) -> str:
        return _sha256(value, "prompt evidence digest")


class GenerationParameterV1(_AdmissionContractModel):
    """One non-secret, canonical JSON parameter without retaining raw input."""

    key: str
    canonical_value_json: str

    @classmethod
    def from_value(cls, key: str, value: object) -> GenerationParameterV1:
        """Build a parameter from a supported non-secret JSON-like value."""

        return cls(key=key, canonical_value_json=canonical_json(value))

    @field_validator("key")
    @classmethod
    def _validate_parameter_key(cls, value: str) -> str:
        return _safe_parameter_key(value)

    @field_validator("canonical_value_json")
    @classmethod
    def _validate_canonical_value(cls, value: str) -> str:
        if not value:
            raise ValueError("canonical generation parameter value must not be blank")
        try:
            decoded = json.loads(value, parse_constant=_reject_json_constant)
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            raise ValueError("generation parameter value must be canonical JSON") from error
        if canonical_json(decoded) != value:
            raise ValueError("generation parameter value must use canonical JSON")
        return value


class ProviderRequestBindingV1(_AdmissionContractModel):
    """Non-secret provider request identity, not an invocation instruction."""

    provider_reference: str
    plugin_reference: str | None = None
    model_id: str | None = None
    model_version: str | None = None
    workflow_id: str | None = None
    workflow_version: str | None = None
    workflow_content_digest: str | None = None
    parameters: tuple[GenerationParameterV1, ...] = ()

    @field_validator(
        "provider_reference",
        "plugin_reference",
        "model_id",
        "model_version",
        "workflow_id",
        "workflow_version",
    )
    @classmethod
    def _validate_optional_provider_references(cls, value: str | None) -> str | None:
        return _logical_reference(value, "provider binding reference") if value is not None else None

    @field_validator("workflow_content_digest")
    @classmethod
    def _validate_optional_workflow_digest(cls, value: str | None) -> str | None:
        return _sha256(value, "workflow content digest") if value is not None else None

    @field_validator("parameters")
    @classmethod
    def _validate_parameters(
        cls, values: tuple[GenerationParameterV1, ...]
    ) -> tuple[GenerationParameterV1, ...]:
        keys = tuple(item.key for item in values)
        if len(set(keys)) != len(keys):
            raise ValueError("generation parameter keys must be unique")
        return tuple(sorted(values, key=lambda item: item.key))

    def model_post_init(self, __context: object) -> None:
        if (self.model_id is None) != (self.model_version is None):
            raise ValueError("model identity requires both id and version when supplied")
        if (self.workflow_id is None) != (self.workflow_version is None):
            raise ValueError("workflow identity requires both id and version when supplied")
        if self.workflow_content_digest is not None and self.workflow_id is None:
            raise ValueError("workflow content digest requires a workflow identity")

    def canonical_projection(self) -> dict[str, CanonicalValue]:
        return {
            "model_id": self.model_id,
            "model_version": self.model_version,
            "parameters": tuple(
                {"canonical_value_json": parameter.canonical_value_json, "key": parameter.key}
                for parameter in self.parameters
            ),
            "plugin_reference": self.plugin_reference,
            "provider_reference": self.provider_reference,
            "workflow_content_digest": self.workflow_content_digest,
            "workflow_id": self.workflow_id,
            "workflow_version": self.workflow_version,
        }


class GenerationAdmissionManifestV1(_AdmissionContractModel):
    """Complete, versioned pre-provider generation admission evidence."""

    schema_id: Literal["manga_director.generation_admission"] = (
        "manga_director.generation_admission"
    )
    schema_version: Literal["1"] = "1"
    project_id: str
    page_id: str
    execution_target_reference: str
    source_state: Literal["PromptBuilt"] = "PromptBuilt"
    snapshot: SnapshotIdentityV1
    storyboard: StoryboardEvidenceV1
    prompt: PromptEvidenceV1
    provider_request: ProviderRequestBindingV1
    attempt_id: str

    @field_validator("project_id", "page_id", "execution_target_reference", "attempt_id")
    @classmethod
    def _validate_manifest_reference(cls, value: str) -> str:
        return _logical_reference(value, "manifest reference")

    def model_post_init(self, __context: object) -> None:
        if self.prompt.source_storyboard_digest != self.storyboard.content_digest:
            raise ValueError("prompt provenance does not match the admitted storyboard")

    @property
    def content_digest(self) -> str:
        return content_digest(self.canonical_projection())

    def canonical_projection(self) -> dict[str, CanonicalValue]:
        return {
            "attempt_id": self.attempt_id,
            "execution_target_reference": self.execution_target_reference,
            "page_id": self.page_id,
            "project_id": self.project_id,
            "prompt": {
                "prompt_content_digest": self.prompt.prompt_content_digest,
                "prompt_reference": self.prompt.prompt_reference,
                "source_storyboard_digest": self.prompt.source_storyboard_digest,
            },
            "provider_request": self.provider_request.canonical_projection(),
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "snapshot": {
                "fingerprint": self.snapshot.fingerprint,
                "revision": self.snapshot.revision,
            },
            "source_state": self.source_state,
            "storyboard": self.storyboard.canonical_projection(),
        }


class GenerationAdmissionDecision(_AdmissionContractModel):
    """A non-authoritative, side-effect-free admission decision record."""

    status: AdmissionDecisionStatus
    reason_code: str
    manifest_digest: str | None = None
    state_machine_changed: Literal[False] = False
    provider_invocation_performed: Literal[False] = False
    external_side_effect_performed: Literal[False] = False

    @field_validator("reason_code")
    @classmethod
    def _validate_reason_code(cls, value: str) -> str:
        return _logical_reference(value, "admission decision reason code")

    @field_validator("manifest_digest")
    @classmethod
    def _validate_optional_manifest_digest(cls, value: str | None) -> str | None:
        return _sha256(value, "manifest digest") if value is not None else None

    def model_post_init(self, __context: object) -> None:
        if self.status == "ADMITTED":
            if self.manifest_digest is None:
                raise ValueError("ADMITTED requires a deterministic manifest digest")
            if self.reason_code != "ADMISSION_EVIDENCE_COMPLETE":
                raise ValueError("ADMITTED requires the complete-evidence reason code")


def legacy_evidence_decision() -> GenerationAdmissionDecision:
    """Return the required non-admission decision for unverifiable legacy evidence."""

    return GenerationAdmissionDecision(
        status="UNVERIFIED",
        reason_code="LEGACY_EVIDENCE_INSUFFICIENT",
    )


def canonical_json(value: object) -> str:
    """Return canonical JSON for non-secret values; sequences retain their supplied order."""

    return json.dumps(
        _canonical_value(value),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    )


def content_digest(value: object) -> str:
    """Return the SHA-256 content identity for a canonical JSON projection."""

    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _canonical_value(value: object) -> CanonicalValue:
    if value is None:
        return None
    if type(value) is bool:
        return value
    if type(value) is int:
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("canonical JSON does not accept non-finite floats")
        return 0.0 if value == 0 else value
    if type(value) is str:
        _reject_secret_value(value)
        return value
    if isinstance(value, Mapping):
        normalized: dict[str, CanonicalValue] = {}
        for key, nested_value in value.items():
            if type(key) is not str:
                raise ValueError("canonical JSON mapping keys must be strings")
            _safe_parameter_key(key)
            normalized[key] = _canonical_value(nested_value)
        return {key: normalized[key] for key in sorted(normalized)}
    if isinstance(value, (list, tuple)):
        return tuple(_canonical_value(item) for item in value)
    raise ValueError("canonical JSON accepts only JSON scalars, mappings, and ordered sequences")


def _logical_reference(value: str, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{label} must be a nonblank logical reference")
    if any(character.isspace() for character in value):
        raise ValueError(f"{label} must not contain whitespace")
    if value.startswith(("/", "\\")) or "://" in value or _WINDOWS_ABSOLUTE_PATH.match(value):
        raise ValueError(f"{label} must not be a path or URL")
    _reject_secret_value(value)
    return value


def _nonblank_text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value or not value.strip():
        raise ValueError(f"{label} must be nonblank")
    _reject_secret_value(value)
    return value


def _safe_parameter_key(value: str) -> str:
    key = _logical_reference(value, "generation parameter key")
    if any(part in key.lower() for part in _SECRET_KEY_PARTS):
        raise ValueError("generation parameter key is secret-shaped")
    return key


def _sha256(value: str, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _reject_secret_value(value: str) -> None:
    if _SECRET_VALUE.search(value) is not None:
        raise ValueError("secret-shaped values are not accepted in admission evidence")


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"unsupported JSON constant: {value}")
