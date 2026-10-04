"""Internal read-only validation for caller-supplied provider capabilities.

This preview contract compares one explicit provider declaration with supplied
generation requirements. It never selects, invokes, discovers, or configures
a provider and has no workflow, storage, or network behavior.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from typing import Literal

from pydantic import ConfigDict, field_validator

from manga_director.production.director import DirectorModel

CoreCapability = Literal[
    "text_prompt",
    "provenance_capture",
    "reference_image_input",
    "multiple_reference_images",
    "identity_reference_preservation",
    "seed",
    "repeatable_seed",
    "negative_prompt",
    "dimensions",
    "aspect_ratio",
    "output_format",
    "parameter_overrides",
]
RequirementLevel = Literal["required", "optional"]
ProviderSupportState = Literal["supported", "unsupported", "unknown"]
NegotiationOutcome = Literal["satisfied", "missing", "unsupported", "unknown"]
FindingStatus = Literal["blocked", "needs_review", "warning"]
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


class _CapabilityNegotiationModel(DirectorModel):
    """Private base for closed, immutable internal-preview DTOs."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class GenerationCapabilityRequirementDTO(_CapabilityNegotiationModel):
    """One caller-supplied capability requirement without a generation request."""

    capability_id: CoreCapability
    requirement_level: RequirementLevel


class ProviderCapabilityStateDTO(_CapabilityNegotiationModel):
    """One caller-declared support state for an explicit provider."""

    capability_id: CoreCapability
    state: ProviderSupportState


class ProviderCapabilityDeclarationDTO(_CapabilityNegotiationModel):
    """Safe logical capability declaration for exactly one explicit provider."""

    provider_reference: str
    capability_states: tuple[ProviderCapabilityStateDTO, ...] = ()

    @field_validator("provider_reference")
    @classmethod
    def _validate_provider_reference(cls, value: str) -> str:
        return _logical_reference(value)


class CapabilityNegotiationResultDTO(_CapabilityNegotiationModel):
    """The comparison result for exactly one supplied requirement."""

    capability_id: CoreCapability
    requirement_level: RequirementLevel
    declared_state: ProviderSupportState | None = None
    outcome: NegotiationOutcome
    review_required: bool


class CapabilityNegotiationFindingDTO(_CapabilityNegotiationModel):
    """A safe deterministic finding with no provider configuration payload."""

    code: str
    status: FindingStatus
    message: str
    capability_id: CoreCapability | None = None


class CapabilityNegotiationReport(_CapabilityNegotiationModel):
    """Canonical immutable comparison report with no execution semantics."""

    declaration: ProviderCapabilityDeclarationDTO
    requirements: tuple[GenerationCapabilityRequirementDTO, ...] = ()
    results: tuple[CapabilityNegotiationResultDTO, ...] = ()
    findings: tuple[CapabilityNegotiationFindingDTO, ...] = ()
    status: ReportStatus
    ready: bool
    analysis_only: Literal[True] = True


class ProviderCapabilityNegotiationService:
    """Compare supplied declarations without selection, inference, or side effects."""

    def validate(
        self,
        requirements: Sequence[GenerationCapabilityRequirementDTO],
        declaration: ProviderCapabilityDeclarationDTO,
    ) -> CapabilityNegotiationReport:
        """Return a canonical report for one explicit provider declaration."""

        canonical_requirements = tuple(sorted(requirements, key=lambda item: item.capability_id))
        canonical_declaration = declaration.model_copy(
            update={
                "capability_states": tuple(
                    sorted(declaration.capability_states, key=lambda item: item.capability_id)
                )
            }
        )
        findings = _integrity_findings(canonical_requirements, canonical_declaration)
        declared_states = _unambiguous_states(canonical_declaration.capability_states)
        results = tuple(
            _result(requirement, declared_states.get(requirement.capability_id))
            for requirement in canonical_requirements
        )
        findings.extend(_capability_findings(results))
        ordered_findings = tuple(sorted(findings, key=_finding_key))
        status = _report_status(ordered_findings, results)
        return CapabilityNegotiationReport(
            declaration=canonical_declaration,
            requirements=canonical_requirements,
            results=results,
            findings=ordered_findings,
            status=status,
            ready=status == "ready",
        )


def _logical_reference(value: str) -> str:
    if not value or value != value.strip() or any(character.isspace() for character in value):
        raise ValueError("provider_reference must be a nonblank logical reference")
    if value.startswith(("/", "\\")) or "://" in value or _WINDOWS_ABSOLUTE_PATH.match(value):
        raise ValueError("provider_reference must not be a path or URL")
    if "@" in value:
        raise ValueError("provider_reference must not contain an email address")
    if any(part in value.lower() for part in _SECRET_LIKE_PARTS):
        raise ValueError("provider_reference must not contain a secret-like value")
    return value


def _integrity_findings(
    requirements: tuple[GenerationCapabilityRequirementDTO, ...],
    declaration: ProviderCapabilityDeclarationDTO,
) -> list[CapabilityNegotiationFindingDTO]:
    findings: list[CapabilityNegotiationFindingDTO] = []
    for capability_id in _duplicates(item.capability_id for item in requirements):
        findings.append(
            _finding("DUPLICATE_CAPABILITY_REQUIREMENT", "blocked", capability_id)
        )
    states_by_capability: dict[CoreCapability, list[ProviderCapabilityStateDTO]] = {}
    for state in declaration.capability_states:
        states_by_capability.setdefault(state.capability_id, []).append(state)
    for capability_id in sorted(states_by_capability):
        states = states_by_capability[capability_id]
        if len(states) <= 1:
            continue
        code = (
            "CONFLICTING_PROVIDER_CAPABILITY_DECLARATION"
            if len({item.state for item in states}) > 1
            else "DUPLICATE_PROVIDER_CAPABILITY_DECLARATION"
        )
        findings.append(_finding(code, "blocked", capability_id))
    return findings


def _unambiguous_states(
    states: tuple[ProviderCapabilityStateDTO, ...],
) -> dict[CoreCapability, ProviderSupportState]:
    grouped: dict[CoreCapability, list[ProviderCapabilityStateDTO]] = {}
    for state in states:
        grouped.setdefault(state.capability_id, []).append(state)
    return {
        capability_id: values[0].state
        for capability_id, values in grouped.items()
        if len(values) == 1
    }


def _result(
    requirement: GenerationCapabilityRequirementDTO,
    declared_state: ProviderSupportState | None,
) -> CapabilityNegotiationResultDTO:
    outcome: NegotiationOutcome
    if declared_state is None:
        outcome = "missing"
    elif declared_state == "supported":
        outcome = "satisfied"
    else:
        outcome = declared_state
    return CapabilityNegotiationResultDTO(
        capability_id=requirement.capability_id,
        requirement_level=requirement.requirement_level,
        declared_state=declared_state,
        outcome=outcome,
        review_required=requirement.requirement_level == "required" and outcome != "satisfied",
    )


def _capability_findings(
    results: tuple[CapabilityNegotiationResultDTO, ...],
) -> list[CapabilityNegotiationFindingDTO]:
    findings: list[CapabilityNegotiationFindingDTO] = []
    for result in results:
        if result.outcome == "satisfied":
            continue
        prefix = "REQUIRED" if result.requirement_level == "required" else "OPTIONAL"
        status: FindingStatus = "needs_review" if result.review_required else "warning"
        findings.append(
            _finding(
                f"{prefix}_CAPABILITY_{result.outcome.upper()}",
                status,
                result.capability_id,
            )
        )
    return findings


def _finding(
    code: str, status: FindingStatus, capability_id: CoreCapability
) -> CapabilityNegotiationFindingDTO:
    return CapabilityNegotiationFindingDTO(
        code=code,
        status=status,
        message=code.replace("_", " ").lower(),
        capability_id=capability_id,
    )


def _duplicates(values: Iterable[CoreCapability]) -> tuple[CoreCapability, ...]:
    counts: dict[CoreCapability, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return tuple(sorted(value for value, count in counts.items() if count > 1))


def _finding_key(item: CapabilityNegotiationFindingDTO) -> tuple[str, str, str, str]:
    return (item.code, item.status, item.capability_id or "", item.message)


def _report_status(
    findings: tuple[CapabilityNegotiationFindingDTO, ...],
    results: tuple[CapabilityNegotiationResultDTO, ...],
) -> ReportStatus:
    if any(item.status == "blocked" for item in findings):
        return "blocked"
    if any(item.review_required for item in results):
        return "needs_review"
    return "ready"
