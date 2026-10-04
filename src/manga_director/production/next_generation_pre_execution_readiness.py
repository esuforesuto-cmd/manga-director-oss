"""Internal read-only readiness validation for supplied generation evidence.

This preview contract only binds existing request-validation and capability-
negotiation reports for one explicit provider reference.  It does not
authorize, approve, select, invoke, or persist generation work.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import ConfigDict, field_validator

from manga_director.production.director import DirectorModel
from manga_director.production.next_generation_provider_capability_negotiation import (
    CapabilityNegotiationReport,
    CapabilityNegotiationResultDTO,
    GenerationCapabilityRequirementDTO,
)
from manga_director.production.next_generation_structured_generation_request import (
    StructuredGenerationRequestValidationReport,
)

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


class _PreExecutionReadinessModel(DirectorModel):
    """Private base for closed, immutable internal-preview DTOs."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class PreExecutionReadinessInputDTO(_PreExecutionReadinessModel):
    """Caller-supplied evidence bound to one explicit logical provider reference."""

    request_validation_report: StructuredGenerationRequestValidationReport
    capability_negotiation_report: CapabilityNegotiationReport
    provider_reference: str

    @field_validator("provider_reference")
    @classmethod
    def _validate_provider_reference(cls, value: str) -> str:
        return _logical_reference(value)


class PreExecutionReadinessFindingDTO(_PreExecutionReadinessModel):
    """One safe deterministic readiness finding."""

    code: str
    status: FindingStatus
    message: str
    capability_id: str | None = None


class PreExecutionReadinessReport(_PreExecutionReadinessModel):
    """Canonical immutable advisory report without authorization semantics."""

    input: PreExecutionReadinessInputDTO
    findings: tuple[PreExecutionReadinessFindingDTO, ...] = ()
    status: ReportStatus
    ready: bool
    analysis_only: Literal[True] = True


class PreExecutionReadinessService:
    """Bind supplied validation evidence without inference or side effects."""

    def validate(self, input: PreExecutionReadinessInputDTO) -> PreExecutionReadinessReport:
        """Return a deterministic advisory readiness report for supplied evidence."""

        findings = _binding_findings(input)
        findings.extend(_capability_findings(input.capability_negotiation_report.results))
        ordered_findings = tuple(sorted(findings, key=_finding_key))
        status = _report_status(ordered_findings)
        return PreExecutionReadinessReport(
            input=input,
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


def _binding_findings(
    input: PreExecutionReadinessInputDTO,
) -> list[PreExecutionReadinessFindingDTO]:
    request_report = input.request_validation_report
    negotiation_report = input.capability_negotiation_report
    findings: list[PreExecutionReadinessFindingDTO] = []
    if request_report.status == "blocked" or not request_report.ready:
        findings.append(_finding("REQUEST_VALIDATION_BLOCKED", "blocked"))
    if negotiation_report.status == "blocked":
        findings.append(_finding("CAPABILITY_NEGOTIATION_BLOCKED", "blocked"))
    if _canonical_requirements(request_report.request.capability_requirements) != _canonical_requirements(
        negotiation_report.requirements
    ):
        findings.append(_finding("REQUEST_NEGOTIATION_REQUIREMENT_MISMATCH", "blocked"))
    if input.provider_reference != negotiation_report.declaration.provider_reference:
        findings.append(_finding("PROVIDER_REFERENCE_MISMATCH", "blocked"))
    return findings


def _canonical_requirements(
    requirements: tuple[GenerationCapabilityRequirementDTO, ...],
) -> tuple[GenerationCapabilityRequirementDTO, ...]:
    return tuple(
        sorted(
            requirements,
            key=lambda item: (item.capability_id, item.requirement_level),
        )
    )


def _capability_findings(
    results: tuple[CapabilityNegotiationResultDTO, ...],
) -> list[PreExecutionReadinessFindingDTO]:
    findings: list[PreExecutionReadinessFindingDTO] = []
    for result in results:
        if result.outcome == "satisfied":
            continue
        prefix = "REQUIRED" if result.requirement_level == "required" else "OPTIONAL"
        status: FindingStatus = "needs_review" if prefix == "REQUIRED" else "warning"
        findings.append(
            _finding(
                f"{prefix}_CAPABILITY_{result.outcome.upper()}",
                status,
                result.capability_id,
            )
        )
    return findings


def _finding(
    code: str,
    status: FindingStatus,
    capability_id: str | None = None,
) -> PreExecutionReadinessFindingDTO:
    return PreExecutionReadinessFindingDTO(
        code=code,
        status=status,
        message=code.replace("_", " ").lower(),
        capability_id=capability_id,
    )


def _finding_key(
    item: PreExecutionReadinessFindingDTO,
) -> tuple[str, str, str, str]:
    return (item.code, item.status, item.capability_id or "", item.message)


def _report_status(
    findings: tuple[PreExecutionReadinessFindingDTO, ...],
) -> ReportStatus:
    if any(item.status == "blocked" for item in findings):
        return "blocked"
    if any(item.status == "needs_review" for item in findings):
        return "needs_review"
    return "ready"
