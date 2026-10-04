"""Internal read-only validation for caller-supplied recovery generation request evidence.

This preview contract validates recovery request evidence against one supplied
production-profile snapshot. It does not inspect a recovery proposal, select a
provider, authorize work, or execute generation.
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
from manga_director.production.next_generation_structured_generation_request import (
    GenerationProductionProfileDTO,
)

FindingStatus = Literal["blocked"]
ReportStatus = Literal["ready", "blocked"]

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


class _RecoveryStructuredGenerationRequestModel(DirectorModel):
    """Private base for closed, immutable internal-preview DTOs."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class RecoveryStructuredGenerationRequestDTO(_RecoveryStructuredGenerationRequestModel):
    """One explicit recovery request without provider or execution semantics."""

    recovery_request_id: str
    recovery_proposal_id: str
    generation_intent_reference: str
    input: GenerationInputEvidenceDTO
    profile_id: str
    profile_version: str
    capability_requirements: tuple[GenerationCapabilityRequirementDTO, ...]
    identity_bindings: tuple[GenerationIdentityBindingDTO, ...]

    @field_validator(
        "recovery_request_id",
        "recovery_proposal_id",
        "generation_intent_reference",
        "profile_id",
        "profile_version",
    )
    @classmethod
    def _validate_logical_reference(cls, value: str) -> str:
        return _logical_reference(value)

    @field_validator("identity_bindings")
    @classmethod
    def _require_identity_bindings(
        cls, value: tuple[GenerationIdentityBindingDTO, ...]
    ) -> tuple[GenerationIdentityBindingDTO, ...]:
        if not value:
            raise ValueError("identity_bindings must be non-empty")
        return value


class RecoveryStructuredGenerationRequestFindingDTO(_RecoveryStructuredGenerationRequestModel):
    """One deterministic recovery request input-integrity finding."""

    code: str
    status: FindingStatus
    message: str
    recovery_request_id: str = ""
    recovery_proposal_id: str = ""
    profile_id: str = ""
    capability_id: str = ""
    character_id: str = ""
    identity_id: str = ""
    identity_version: str = ""


class RecoveryStructuredGenerationRequestValidationReport(_RecoveryStructuredGenerationRequestModel):
    """Canonical immutable report without proposal, provider, or execution access."""

    request: RecoveryStructuredGenerationRequestDTO
    profile: GenerationProductionProfileDTO
    findings: tuple[RecoveryStructuredGenerationRequestFindingDTO, ...] = ()
    status: ReportStatus
    ready: bool
    analysis_only: Literal[True] = True


class RecoveryStructuredGenerationRequestValidationService:
    """Validate one recovery request/profile snapshot without inference or side effects."""

    def validate(
        self,
        request: RecoveryStructuredGenerationRequestDTO,
        profile: GenerationProductionProfileDTO,
    ) -> RecoveryStructuredGenerationRequestValidationReport:
        """Return a deterministic canonical validation report for supplied recovery evidence."""

        canonical_profile = _canonical_profile(profile)
        canonical_request = _canonical_request(request)
        findings = _findings(canonical_request, canonical_profile)
        ordered_findings = tuple(sorted(findings, key=_finding_key))
        status: ReportStatus = "blocked" if ordered_findings else "ready"
        return RecoveryStructuredGenerationRequestValidationReport(
            request=canonical_request,
            profile=canonical_profile,
            findings=ordered_findings,
            status=status,
            ready=status == "ready",
        )


def _logical_reference(value: str) -> str:
    if not value or value != value.strip() or any(character.isspace() for character in value):
        raise ValueError("recovery request reference must be a nonblank logical reference")
    if value.startswith(("/", "\\")) or "://" in value or _WINDOWS_ABSOLUTE_PATH.match(value):
        raise ValueError("recovery request reference must not be a path or URL")
    if "@" in value:
        raise ValueError("recovery request reference must not contain an email address")
    if any(part in value.lower() for part in _SECRET_LIKE_PARTS):
        raise ValueError("recovery request reference must not contain a secret-like value")
    return value


def _canonical_profile(profile: GenerationProductionProfileDTO) -> GenerationProductionProfileDTO:
    return profile.model_copy(
        update={"capability_requirements": _canonical_requirements(profile.capability_requirements)}
    )


def _canonical_request(
    request: RecoveryStructuredGenerationRequestDTO,
) -> RecoveryStructuredGenerationRequestDTO:
    bindings = tuple(
        sorted(
            (
                binding.model_copy(
                    update={"reference_asset_ids": tuple(sorted(binding.reference_asset_ids))}
                )
                for binding in request.identity_bindings
            ),
            key=lambda item: (item.character_id, item.identity_id, item.identity_version),
        )
    )
    return request.model_copy(
        update={
            "capability_requirements": _canonical_requirements(request.capability_requirements),
            "identity_bindings": bindings,
        }
    )


def _canonical_requirements(
    requirements: tuple[GenerationCapabilityRequirementDTO, ...],
) -> tuple[GenerationCapabilityRequirementDTO, ...]:
    return tuple(sorted(requirements, key=lambda item: (item.capability_id, item.requirement_level)))


def _findings(
    request: RecoveryStructuredGenerationRequestDTO,
    profile: GenerationProductionProfileDTO,
) -> list[RecoveryStructuredGenerationRequestFindingDTO]:
    findings: list[RecoveryStructuredGenerationRequestFindingDTO] = []
    for capability_id in _duplicates(item.capability_id for item in profile.capability_requirements):
        findings.append(_finding("DUPLICATE_PROFILE_CAPABILITY_REQUIREMENT", request, profile, capability_id=capability_id))
    for capability_id in _duplicates(item.capability_id for item in request.capability_requirements):
        findings.append(_finding("DUPLICATE_RECOVERY_REQUEST_CAPABILITY_REQUIREMENT", request, profile, capability_id=capability_id))
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
    return findings


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


def _finding(
    code: str,
    request: RecoveryStructuredGenerationRequestDTO,
    profile: GenerationProductionProfileDTO,
    *,
    capability_id: str = "",
    character_id: str = "",
    identity_id: str = "",
    identity_version: str = "",
) -> RecoveryStructuredGenerationRequestFindingDTO:
    return RecoveryStructuredGenerationRequestFindingDTO(
        code=code,
        status="blocked",
        message=code.replace("_", " ").lower(),
        recovery_request_id=request.recovery_request_id,
        recovery_proposal_id=request.recovery_proposal_id,
        profile_id=profile.profile_id,
        capability_id=capability_id,
        character_id=character_id,
        identity_id=identity_id,
        identity_version=identity_version,
    )


def _finding_key(
    item: RecoveryStructuredGenerationRequestFindingDTO,
) -> tuple[str, str, str, str, str, str, str, str, str]:
    return (
        item.code,
        item.status,
        item.recovery_request_id,
        item.recovery_proposal_id,
        item.profile_id,
        item.capability_id,
        item.character_id,
        item.identity_id,
        item.identity_version,
    )
