"""Internal read-only validation for caller-supplied generation request inputs.

This preview contract validates a request against one explicit production
profile. It never renders a prompt, selects or invokes a provider, or changes
workflow, storage, or external state.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Literal

from pydantic import ConfigDict, field_validator

from manga_director.production.director import DirectorModel
from manga_director.production.next_generation_generation_evidence import (
    GenerationIdentityBindingDTO,
    GenerationInputEvidenceDTO,
)
from manga_director.production.next_generation_provider_capability_negotiation import (
    GenerationCapabilityRequirementDTO,
)

PreservationScope = Literal[
    "identity_bindings",
    "reference_asset_ids",
    "generation_input_reference",
    "provider_configuration",
    "seed",
    "output_provenance",
]
FindingStatus = Literal["blocked", "warning"]
ReportStatus = Literal["ready", "needs_review", "blocked"]

_WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:[\\\\/]")
_SECRET_LIKE_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "endpoint",
    "password",
    "secret",
    "token",
)


class _StructuredGenerationRequestModel(DirectorModel):
    """Private base for closed, immutable internal-preview DTOs."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class GenerationProductionProfileDTO(_StructuredGenerationRequestModel):
    """One caller-supplied immutable source of generation requirements."""

    profile_id: str
    profile_version: str
    capability_requirements: tuple[GenerationCapabilityRequirementDTO, ...] = ()

    @field_validator("profile_id", "profile_version")
    @classmethod
    def _validate_profile_reference(cls, value: str) -> str:
        return _logical_reference(value, "profile reference")


class StructuredGenerationRequestDTO(_StructuredGenerationRequestModel):
    """One intent/evidence request without prompt retention or execution behavior."""

    request_id: str
    target_page_reference: str
    generation_intent_reference: str
    input: GenerationInputEvidenceDTO
    capability_requirements: tuple[GenerationCapabilityRequirementDTO, ...]
    provenance_reference: str
    profile_id: str
    profile_version: str
    target_panel_reference: str | None = None
    identity_bindings: tuple[GenerationIdentityBindingDTO, ...] = ()
    preservation_scopes: tuple[PreservationScope, ...] = ()

    @field_validator(
        "request_id",
        "target_page_reference",
        "generation_intent_reference",
        "provenance_reference",
        "profile_id",
        "profile_version",
    )
    @classmethod
    def _validate_request_reference(cls, value: str) -> str:
        return _logical_reference(value, "request reference")

    @field_validator("target_panel_reference")
    @classmethod
    def _validate_optional_panel_reference(cls, value: str | None) -> str | None:
        return _logical_reference(value, "target_panel_reference") if value is not None else None


class StructuredGenerationRequestFindingDTO(_StructuredGenerationRequestModel):
    """One deterministic input-integrity finding without private payloads."""

    code: str
    status: FindingStatus
    message: str
    request_id: str = ""
    profile_id: str = ""
    capability_id: str = ""
    character_id: str = ""
    identity_id: str = ""
    identity_version: str = ""
    preservation_scope: str = ""


class StructuredGenerationRequestValidationReport(_StructuredGenerationRequestModel):
    """Canonical immutable report with no generation, approval, or workflow semantics."""

    request: StructuredGenerationRequestDTO
    profile: GenerationProductionProfileDTO
    findings: tuple[StructuredGenerationRequestFindingDTO, ...] = ()
    status: ReportStatus
    ready: bool
    analysis_only: Literal[True] = True


class StructuredGenerationRequestValidationService:
    """Validate one request/profile snapshot without inference or side effects."""

    def validate(
        self,
        request: StructuredGenerationRequestDTO,
        profile: GenerationProductionProfileDTO,
    ) -> StructuredGenerationRequestValidationReport:
        """Return a canonical report for one explicit request/profile pair."""

        canonical_profile = _canonical_profile(profile)
        canonical_request = _canonical_request(request)
        findings = _findings(canonical_request, canonical_profile)
        ordered_findings = tuple(sorted(findings, key=_finding_key))
        status: ReportStatus = "blocked" if ordered_findings else "ready"
        return StructuredGenerationRequestValidationReport(
            request=canonical_request,
            profile=canonical_profile,
            findings=ordered_findings,
            status=status,
            ready=status == "ready",
        )


def _logical_reference(value: str, label: str) -> str:
    if not value or value != value.strip() or any(character.isspace() for character in value):
        raise ValueError(f"{label} must be a nonblank logical reference")
    if value.startswith(("/", "\\")) or "://" in value or _WINDOWS_ABSOLUTE_PATH.match(value):
        raise ValueError(f"{label} must not be a path or URL")
    if "@" in value:
        raise ValueError(f"{label} must not contain an email address")
    if any(part in value.lower() for part in _SECRET_LIKE_PARTS):
        raise ValueError(f"{label} must not contain a secret-like value")
    return value


def _canonical_profile(profile: GenerationProductionProfileDTO) -> GenerationProductionProfileDTO:
    return profile.model_copy(
        update={"capability_requirements": _canonical_requirements(profile.capability_requirements)}
    )


def _canonical_request(request: StructuredGenerationRequestDTO) -> StructuredGenerationRequestDTO:
    bindings = tuple(
        binding.model_copy(update={"reference_asset_ids": tuple(sorted(binding.reference_asset_ids))})
        for binding in sorted(
            request.identity_bindings,
            key=lambda item: (item.character_id, item.identity_id, item.identity_version),
        )
    )
    return request.model_copy(
        update={
            "capability_requirements": _canonical_requirements(request.capability_requirements),
            "identity_bindings": bindings,
            "preservation_scopes": tuple(sorted(request.preservation_scopes)),
        }
    )


def _canonical_requirements(
    requirements: tuple[GenerationCapabilityRequirementDTO, ...],
) -> tuple[GenerationCapabilityRequirementDTO, ...]:
    return tuple(
        sorted(requirements, key=lambda item: (item.capability_id, item.requirement_level))
    )


def _findings(
    request: StructuredGenerationRequestDTO,
    profile: GenerationProductionProfileDTO,
) -> list[StructuredGenerationRequestFindingDTO]:
    findings: list[StructuredGenerationRequestFindingDTO] = []
    for capability_id in _duplicates(item.capability_id for item in profile.capability_requirements):
        findings.append(
            _finding(
                "DUPLICATE_PROFILE_CAPABILITY_REQUIREMENT",
                request,
                profile,
                capability_id=capability_id,
            )
        )
    for capability_id in _duplicates(item.capability_id for item in request.capability_requirements):
        findings.append(
            _finding(
                "DUPLICATE_REQUEST_CAPABILITY_REQUIREMENT",
                request,
                profile,
                capability_id=capability_id,
            )
        )
    if (request.profile_id, request.profile_version) != (profile.profile_id, profile.profile_version):
        findings.append(_finding("PROFILE_SNAPSHOT_MISMATCH", request, profile))
    if request.capability_requirements != profile.capability_requirements:
        findings.append(_finding("PROFILE_REQUIREMENT_PROJECTION_MISMATCH", request, profile))
    for character_id, identity_id, identity_version in _duplicate_binding_keys(request.identity_bindings):
        findings.append(
            _finding(
                "DUPLICATE_IDENTITY_BINDING",
                request,
                profile,
                character_id=character_id,
                identity_id=identity_id,
                identity_version=identity_version,
            )
        )
    for scope in _duplicates(request.preservation_scopes):
        findings.append(
            _finding(
                "DUPLICATE_PRESERVATION_SCOPE",
                request,
                profile,
                preservation_scope=scope,
            )
        )
    return findings


def _finding(
    code: str,
    request: StructuredGenerationRequestDTO,
    profile: GenerationProductionProfileDTO,
    *,
    capability_id: str = "",
    character_id: str = "",
    identity_id: str = "",
    identity_version: str = "",
    preservation_scope: str = "",
) -> StructuredGenerationRequestFindingDTO:
    return StructuredGenerationRequestFindingDTO(
        code=code,
        status="blocked",
        message=code.replace("_", " ").lower(),
        request_id=request.request_id,
        profile_id=profile.profile_id,
        capability_id=capability_id,
        character_id=character_id,
        identity_id=identity_id,
        identity_version=identity_version,
        preservation_scope=preservation_scope,
    )


def _duplicates(values: Iterable[str]) -> tuple[str, ...]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return tuple(sorted(value for value, count in counts.items() if count > 1))


def _duplicate_binding_keys(
    bindings: tuple[GenerationIdentityBindingDTO, ...],
) -> tuple[tuple[str, str, str], ...]:
    counts: dict[tuple[str, str, str], int] = {}
    for binding in bindings:
        key = (binding.character_id, binding.identity_id, binding.identity_version)
        counts[key] = counts.get(key, 0) + 1
    return tuple(sorted(key for key, count in counts.items() if count > 1))


def _finding_key(item: StructuredGenerationRequestFindingDTO) -> tuple[str, ...]:
    return (
        item.code,
        item.request_id,
        item.profile_id,
        item.capability_id,
        item.character_id,
        item.identity_id,
        item.identity_version,
        item.preservation_scope,
        item.message,
    )
