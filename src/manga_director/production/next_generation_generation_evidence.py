"""Internal read-only validation for caller-supplied generation evidence.

The preview contract records supplied logical evidence for one generation
attempt. It never executes a provider, reads an asset, calculates a hash,
selects an identity version, or assesses reproducibility.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from datetime import datetime
from typing import Literal

from pydantic import ConfigDict, field_validator

from manga_director.production.director import DirectorModel

EvidenceScalar = str | int | float | bool
EvidenceAvailability = Literal["known", "unknown", "unavailable"]
FindingStatus = Literal["ready", "needs_evidence", "needs_review", "blocked"]

_WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:[\\/]")
_SECRET_LIKE_KEY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "endpoint",
    "password",
    "secret",
    "token",
)
_STATUS_PRIORITY = {"blocked": 3, "needs_evidence": 2, "needs_review": 1, "ready": 0}


class _GenerationEvidenceModel(DirectorModel):
    """Private base for closed, immutable internal-preview DTOs."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class EvidenceValueDTO(_GenerationEvidenceModel):
    """A caller-declared known, unknown, or unavailable scalar evidence value."""

    availability: EvidenceAvailability
    value: EvidenceScalar | None = None

    @field_validator("value")
    @classmethod
    def _reject_blank_known_strings(cls, value: EvidenceScalar | None) -> EvidenceScalar | None:
        if isinstance(value, str) and not value.strip():
            raise ValueError("evidence value must not be blank")
        return value

    def model_post_init(self, __context: object) -> None:
        if self.availability == "known" and self.value is None:
            raise ValueError("known evidence requires a caller-supplied value")
        if self.availability != "known" and self.value is not None:
            raise ValueError("unknown or unavailable evidence must not include a value")


class GenerationInputEvidenceDTO(_GenerationEvidenceModel):
    """Logical reference to a supplied generation input, without prompt retention."""

    input_reference: str
    input_content_hash: EvidenceValueDTO | None = None

    @field_validator("input_reference")
    @classmethod
    def _validate_input_reference(cls, value: str) -> str:
        return _logical_reference(value, "input_reference")

    @field_validator("input_content_hash")
    @classmethod
    def _validate_input_hash(cls, value: EvidenceValueDTO | None) -> EvidenceValueDTO | None:
        return _optional_string_evidence(value, "input_content_hash")


class GenerationOutputEvidenceDTO(_GenerationEvidenceModel):
    """Logical output evidence only; it does not access an output asset."""

    output_asset_id: str
    output_content_hash: EvidenceValueDTO | None = None
    media_type: str | None = None

    @field_validator("output_asset_id")
    @classmethod
    def _validate_output_asset_id(cls, value: str) -> str:
        return _logical_reference(value, "output_asset_id")

    @field_validator("output_content_hash")
    @classmethod
    def _validate_output_hash(cls, value: EvidenceValueDTO | None) -> EvidenceValueDTO | None:
        return _optional_string_evidence(value, "output_content_hash")

    @field_validator("media_type")
    @classmethod
    def _reject_blank_media_type(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("media_type must not be blank")
        return value


class GenerationIdentityBindingDTO(_GenerationEvidenceModel):
    """Explicit identity-version references used by one supplied attempt."""

    character_id: str
    identity_id: str
    identity_version: str
    reference_asset_ids: tuple[str, ...] = ()

    @field_validator("character_id", "identity_id", "identity_version")
    @classmethod
    def _validate_identity_reference(cls, value: str) -> str:
        return _logical_reference(value, "identity binding reference")

    @field_validator("reference_asset_ids")
    @classmethod
    def _validate_reference_asset_ids(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(_logical_reference(value, "reference_asset_id") for value in values)


class GenerationParameterEvidenceDTO(_GenerationEvidenceModel):
    """One portable, caller-supplied generation parameter evidence item."""

    key: str
    value: EvidenceValueDTO

    @field_validator("key")
    @classmethod
    def _validate_parameter_key(cls, value: str) -> str:
        return _safe_evidence_key(value, "parameter key")


class ProviderSpecificEvidenceDTO(_GenerationEvidenceModel):
    """One namespaced scalar provider extension, without a raw provider payload."""

    namespace: str
    key: str
    value: EvidenceValueDTO

    @field_validator("namespace")
    @classmethod
    def _validate_namespace(cls, value: str) -> str:
        return _logical_reference(value, "provider evidence namespace")

    @field_validator("key")
    @classmethod
    def _validate_provider_key(cls, value: str) -> str:
        return _safe_evidence_key(value, "provider evidence key")


class GenerationConfigurationEvidenceDTO(_GenerationEvidenceModel):
    """Provider-neutral configuration evidence for one supplied generation attempt."""

    provider_id: EvidenceValueDTO
    model_id: EvidenceValueDTO
    model_version: EvidenceValueDTO
    workflow_id: EvidenceValueDTO
    workflow_version: EvidenceValueDTO
    workflow_content_hash: EvidenceValueDTO | None = None
    seed: EvidenceValueDTO
    parameters: tuple[GenerationParameterEvidenceDTO, ...] = ()
    provider_specific_evidence: tuple[ProviderSpecificEvidenceDTO, ...] = ()

    @field_validator(
        "provider_id", "model_id", "model_version", "workflow_id", "workflow_version"
    )
    @classmethod
    def _validate_string_configuration_evidence(cls, value: EvidenceValueDTO) -> EvidenceValueDTO:
        return _string_evidence(value, "configuration evidence")

    @field_validator("workflow_content_hash")
    @classmethod
    def _validate_workflow_hash(cls, value: EvidenceValueDTO | None) -> EvidenceValueDTO | None:
        return _optional_string_evidence(value, "workflow_content_hash")


class GenerationEvidenceEnvelopeDTO(_GenerationEvidenceModel):
    """One caller-supplied generation attempt evidence envelope."""

    attempt_id: str
    observed_at: datetime
    provenance_reference: str
    input: GenerationInputEvidenceDTO
    output: GenerationOutputEvidenceDTO
    configuration: GenerationConfigurationEvidenceDTO
    identity_bindings: tuple[GenerationIdentityBindingDTO, ...] = ()

    @field_validator("attempt_id", "provenance_reference")
    @classmethod
    def _validate_envelope_reference(cls, value: str) -> str:
        return _logical_reference(value, "generation evidence reference")

    @field_validator("observed_at")
    @classmethod
    def _require_timezone_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        return value


class GenerationEvidenceFindingDTO(_GenerationEvidenceModel):
    """One deterministic validation finding that never contains an evidence value."""

    code: str
    status: FindingStatus
    message: str
    attempt_id: str = ""
    output_asset_id: str = ""
    evidence_name: str = ""


class GenerationEvidenceValidationReport(_GenerationEvidenceModel):
    """Canonical immutable report; it deliberately makes no reproducibility claim."""

    envelopes: tuple[GenerationEvidenceEnvelopeDTO, ...] = ()
    findings: tuple[GenerationEvidenceFindingDTO, ...] = ()
    status: FindingStatus
    ready: bool
    analysis_only: Literal[True] = True
    assets_read: Literal[False] = False
    content_hash_calculated: Literal[False] = False
    network_accessed: Literal[False] = False
    persistence_performed: Literal[False] = False
    provider_executed: Literal[False] = False
    timestamp_generated: Literal[False] = False
    identity_version_selected: Literal[False] = False


class GenerationEvidenceValidationService:
    """Validate supplied evidence without execution, lookup, selection, or inference."""

    def validate(
        self, envelopes: Sequence[GenerationEvidenceEnvelopeDTO] = ()
    ) -> GenerationEvidenceValidationReport:
        """Return a deterministic, immutable validation report for supplied attempts."""

        canonical_envelopes = _canonical_envelopes(envelopes)
        findings = _envelope_findings(canonical_envelopes)
        ordered_findings = tuple(sorted(findings, key=_finding_key))
        status = _report_status(ordered_findings)
        return GenerationEvidenceValidationReport(
            envelopes=canonical_envelopes,
            findings=ordered_findings,
            status=status,
            ready=status == "ready",
        )


def _logical_reference(value: str, label: str) -> str:
    if not value.strip():
        raise ValueError(f"{label} must not be blank")
    if value.startswith(("/", "\\")) or "://" in value or _WINDOWS_ABSOLUTE_PATH.match(value):
        raise ValueError(f"{label} must be a logical reference, not a path or URL")
    return value


def _safe_evidence_key(value: str, label: str) -> str:
    value = _logical_reference(value, label)
    if any(part in value.lower() for part in _SECRET_LIKE_KEY_PARTS):
        raise ValueError(f"{label} is not allowed")
    return value


def _string_evidence(value: EvidenceValueDTO, label: str) -> EvidenceValueDTO:
    if value.availability == "known" and not isinstance(value.value, str):
        raise ValueError(f"{label} must be a string when known")
    return value


def _optional_string_evidence(
    value: EvidenceValueDTO | None, label: str
) -> EvidenceValueDTO | None:
    return _string_evidence(value, label) if value is not None else None


def _canonical_envelopes(
    envelopes: Sequence[GenerationEvidenceEnvelopeDTO],
) -> tuple[GenerationEvidenceEnvelopeDTO, ...]:
    return tuple(
        _canonical_envelope(envelope)
        for envelope in sorted(
            envelopes,
            key=lambda item: (item.attempt_id, item.observed_at.isoformat(), item.provenance_reference),
        )
    )


def _canonical_envelope(envelope: GenerationEvidenceEnvelopeDTO) -> GenerationEvidenceEnvelopeDTO:
    configuration = envelope.configuration.model_copy(
        update={
            "parameters": tuple(sorted(envelope.configuration.parameters, key=lambda item: item.key)),
            "provider_specific_evidence": tuple(
                sorted(
                    envelope.configuration.provider_specific_evidence,
                    key=lambda item: (item.namespace, item.key),
                )
            ),
        }
    )
    bindings = tuple(
        binding.model_copy(update={"reference_asset_ids": tuple(sorted(binding.reference_asset_ids))})
        for binding in sorted(
            envelope.identity_bindings,
            key=lambda item: (item.character_id, item.identity_id, item.identity_version),
        )
    )
    return envelope.model_copy(update={"configuration": configuration, "identity_bindings": bindings})


def _envelope_findings(
    envelopes: tuple[GenerationEvidenceEnvelopeDTO, ...],
) -> list[GenerationEvidenceFindingDTO]:
    findings: list[GenerationEvidenceFindingDTO] = []
    _append_duplicate_attempt_findings(envelopes, findings)
    _append_per_envelope_findings(envelopes, findings)
    _append_output_conflict_findings(envelopes, findings)
    return findings


def _append_duplicate_attempt_findings(
    envelopes: tuple[GenerationEvidenceEnvelopeDTO, ...], findings: list[GenerationEvidenceFindingDTO]
) -> None:
    for attempt_id in _duplicate_strings(envelope.attempt_id for envelope in envelopes):
        findings.append(
            GenerationEvidenceFindingDTO(
                code="duplicate_attempt_id",
                status="blocked",
                message=f"attempt_id {attempt_id} is supplied more than once",
                attempt_id=attempt_id,
            )
        )


def _append_per_envelope_findings(
    envelopes: tuple[GenerationEvidenceEnvelopeDTO, ...], findings: list[GenerationEvidenceFindingDTO]
) -> None:
    for envelope in envelopes:
        _append_duplicate_binding_findings(envelope, findings)
        _append_duplicate_parameter_findings(envelope, findings)
        _append_duplicate_provider_evidence_findings(envelope, findings)
        _append_unknown_evidence_findings(envelope, findings)


def _append_duplicate_binding_findings(
    envelope: GenerationEvidenceEnvelopeDTO, findings: list[GenerationEvidenceFindingDTO]
) -> None:
    bindings = tuple(
        (binding.character_id, binding.identity_id, binding.identity_version)
        for binding in envelope.identity_bindings
    )
    for character_id, identity_id, identity_version in _duplicate_tuples(bindings):
        findings.append(
            GenerationEvidenceFindingDTO(
                code="duplicate_identity_binding",
                status="blocked",
                message=(
                    "identity binding is supplied more than once for "
                    f"{character_id}, {identity_id}, {identity_version}"
                ),
                attempt_id=envelope.attempt_id,
            )
        )


def _append_duplicate_parameter_findings(
    envelope: GenerationEvidenceEnvelopeDTO, findings: list[GenerationEvidenceFindingDTO]
) -> None:
    for key in _duplicate_strings(item.key for item in envelope.configuration.parameters):
        findings.append(
            GenerationEvidenceFindingDTO(
                code="duplicate_parameter_key",
                status="blocked",
                message=f"generation parameter key {key} is supplied more than once",
                attempt_id=envelope.attempt_id,
                evidence_name=key,
            )
        )


def _append_duplicate_provider_evidence_findings(
    envelope: GenerationEvidenceEnvelopeDTO, findings: list[GenerationEvidenceFindingDTO]
) -> None:
    values = tuple(
        (item.namespace, item.key) for item in envelope.configuration.provider_specific_evidence
    )
    for namespace, key in _duplicate_pairs(values):
        findings.append(
            GenerationEvidenceFindingDTO(
                code="duplicate_provider_specific_evidence",
                status="blocked",
                message=f"provider-specific evidence key {namespace}:{key} is supplied more than once",
                attempt_id=envelope.attempt_id,
                evidence_name=f"{namespace}:{key}",
            )
        )


def _append_unknown_evidence_findings(
    envelope: GenerationEvidenceEnvelopeDTO, findings: list[GenerationEvidenceFindingDTO]
) -> None:
    for name, value in _named_evidence(envelope):
        if value is not None and value.availability != "known":
            findings.append(
                GenerationEvidenceFindingDTO(
                    code=f"{value.availability}_evidence",
                    status="needs_evidence",
                    message=f"{name} is declared {value.availability}",
                    attempt_id=envelope.attempt_id,
                    evidence_name=name,
                )
            )


def _named_evidence(
    envelope: GenerationEvidenceEnvelopeDTO,
) -> tuple[tuple[str, EvidenceValueDTO | None], ...]:
    configuration = envelope.configuration
    return (
        ("input_content_hash", envelope.input.input_content_hash),
        ("output_content_hash", envelope.output.output_content_hash),
        ("provider_id", configuration.provider_id),
        ("model_id", configuration.model_id),
        ("model_version", configuration.model_version),
        ("workflow_id", configuration.workflow_id),
        ("workflow_version", configuration.workflow_version),
        ("workflow_content_hash", configuration.workflow_content_hash),
        ("seed", configuration.seed),
        *((f"parameter:{item.key}", item.value) for item in configuration.parameters),
        *(
            (f"provider:{item.namespace}:{item.key}", item.value)
            for item in configuration.provider_specific_evidence
        ),
    )


def _append_output_conflict_findings(
    envelopes: tuple[GenerationEvidenceEnvelopeDTO, ...], findings: list[GenerationEvidenceFindingDTO]
) -> None:
    by_output_asset: dict[str, list[GenerationEvidenceEnvelopeDTO]] = {}
    for envelope in envelopes:
        by_output_asset.setdefault(envelope.output.output_asset_id, []).append(envelope)
    for output_asset_id in sorted(by_output_asset):
        matching_envelopes = by_output_asset[output_asset_id]
        supplied_hashes = {
            _known_string(envelope.output.output_content_hash)
            for envelope in matching_envelopes
            if _known_string(envelope.output.output_content_hash) is not None
        }
        if len(supplied_hashes) > 1:
            findings.append(
                GenerationEvidenceFindingDTO(
                    code="conflicting_output_content_hash",
                    status="blocked",
                    message=(
                        "output asset has conflicting caller-supplied content_hash evidence"
                    ),
                    output_asset_id=output_asset_id,
                )
            )
        if len({envelope.provenance_reference for envelope in matching_envelopes}) > 1:
            findings.append(
                GenerationEvidenceFindingDTO(
                    code="conflicting_output_provenance",
                    status="blocked",
                    message="output asset has conflicting provenance references",
                    output_asset_id=output_asset_id,
                )
            )


def _known_string(value: EvidenceValueDTO | None) -> str | None:
    if value is not None and value.availability == "known" and isinstance(value.value, str):
        return value.value
    return None


def _duplicate_strings(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return tuple(sorted(duplicates))


def _duplicate_pairs(values: Iterable[tuple[str, str]]) -> tuple[tuple[str, str], ...]:
    seen: set[tuple[str, str]] = set()
    duplicates: set[tuple[str, str]] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return tuple(sorted(duplicates))


def _duplicate_tuples(
    values: Iterable[tuple[str, str, str]],
) -> tuple[tuple[str, str, str], ...]:
    seen: set[tuple[str, str, str]] = set()
    duplicates: set[tuple[str, str, str]] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return tuple(sorted(duplicates))


def _finding_key(
    finding: GenerationEvidenceFindingDTO,
) -> tuple[str, str, str, str, str]:
    return (
        finding.code,
        finding.attempt_id,
        finding.output_asset_id,
        finding.evidence_name,
        finding.message,
    )


def _report_status(findings: tuple[GenerationEvidenceFindingDTO, ...]) -> FindingStatus:
    return max(findings, key=lambda finding: _STATUS_PRIORITY[finding.status]).status if findings else "ready"
