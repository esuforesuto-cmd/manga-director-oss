"""Internal read-only readiness validation for supplied recovery evidence.

This preview contract binds already-validated recovery proposal and request
evidence to one already-negotiated provider capability report.  It does not
authorize, approve, select, invoke, retry, or persist generation work.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import ConfigDict, field_validator

from manga_director.production.director import DirectorModel
from manga_director.production.next_generation_generation_recovery_proposal import (
    GenerationRecoveryProposalValidationReport,
)
from manga_director.production.next_generation_provider_capability_negotiation import (
    CapabilityNegotiationReport,
    CapabilityNegotiationResultDTO,
    GenerationCapabilityRequirementDTO,
)
from manga_director.production.next_generation_recovery_structured_generation_request import (
    RecoveryStructuredGenerationRequestDTO,
    RecoveryStructuredGenerationRequestValidationReport,
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


class _RecoveryPreExecutionReadinessModel(DirectorModel):
    """Private base for closed, immutable internal-preview DTOs."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class RecoveryPreExecutionReadinessInputDTO(_RecoveryPreExecutionReadinessModel):
    """Caller-supplied reports bound to one explicit logical provider reference."""

    recovery_proposal_validation_report: GenerationRecoveryProposalValidationReport
    recovery_request_validation_report: RecoveryStructuredGenerationRequestValidationReport
    capability_negotiation_report: CapabilityNegotiationReport
    provider_reference: str

    @field_validator("provider_reference")
    @classmethod
    def _validate_provider_reference(cls, value: str) -> str:
        return _logical_reference(value)


class RecoveryPreExecutionReadinessFindingDTO(_RecoveryPreExecutionReadinessModel):
    """One safe deterministic recovery-readiness finding."""

    code: str
    status: FindingStatus
    message: str
    recovery_proposal_id: str = ""
    recovery_request_id: str = ""
    capability_id: str | None = None


class RecoveryPreExecutionReadinessReport(_RecoveryPreExecutionReadinessModel):
    """Canonical advisory report without recovery authorization semantics."""

    input: RecoveryPreExecutionReadinessInputDTO
    findings: tuple[RecoveryPreExecutionReadinessFindingDTO, ...] = ()
    status: ReportStatus
    ready: bool
    analysis_only: Literal[True] = True


class RecoveryPreExecutionReadinessService:
    """Bind supplied recovery evidence without inference or side effects."""

    def validate(
        self, input: RecoveryPreExecutionReadinessInputDTO
    ) -> RecoveryPreExecutionReadinessReport:
        """Return a deterministic advisory report for supplied recovery evidence."""

        findings = _binding_findings(input)
        findings.extend(_capability_findings(input.capability_negotiation_report.results))
        ordered_findings = tuple(sorted(findings, key=_finding_key))
        status = _report_status(ordered_findings)
        return RecoveryPreExecutionReadinessReport(
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
    input: RecoveryPreExecutionReadinessInputDTO,
) -> list[RecoveryPreExecutionReadinessFindingDTO]:
    proposal_report = input.recovery_proposal_validation_report
    request_report = input.recovery_request_validation_report
    negotiation_report = input.capability_negotiation_report
    request = request_report.request
    proposal_id = request.recovery_proposal_id
    findings: list[RecoveryPreExecutionReadinessFindingDTO] = []

    _proposal_findings(proposal_report, proposal_id, request.recovery_request_id, findings)
    if request_report.status == "blocked" or not request_report.ready:
        findings.append(_finding("RECOVERY_REQUEST_VALIDATION_BLOCKED", "blocked", request))
    if negotiation_report.status == "blocked":
        findings.append(_finding("RECOVERY_CAPABILITY_NEGOTIATION_BLOCKED", "blocked", request))
    if _canonical_requirements(request.capability_requirements) != _canonical_requirements(
        negotiation_report.requirements
    ):
        findings.append(
            _finding("RECOVERY_REQUEST_NEGOTIATION_REQUIREMENT_MISMATCH", "blocked", request)
        )
    if input.provider_reference != negotiation_report.declaration.provider_reference:
        findings.append(_finding("RECOVERY_PROVIDER_REFERENCE_MISMATCH", "blocked", request))
    return findings


def _proposal_findings(
    report: GenerationRecoveryProposalValidationReport,
    proposal_id: str,
    recovery_request_id: str,
    findings: list[RecoveryPreExecutionReadinessFindingDTO],
) -> None:
    matching_proposals = tuple(item for item in report.proposals if item.proposal_id == proposal_id)
    if report.status == "blocked" or any(item.status == "blocked" for item in report.findings):
        findings.append(
            _finding(
                "RECOVERY_PROPOSAL_VALIDATION_BLOCKED",
                "blocked",
                recovery_proposal_id=proposal_id,
                recovery_request_id=recovery_request_id,
            )
        )
    if len(matching_proposals) != 1:
        findings.append(
            _finding(
                "RECOVERY_PROPOSAL_REQUEST_MISMATCH",
                "blocked",
                recovery_proposal_id=proposal_id,
                recovery_request_id=recovery_request_id,
            )
        )
        return
    reasons = tuple(item for item in report.findings if item.proposal_id == proposal_id)
    needs_review_reasons = tuple(item for item in reasons if item.status == "needs_review")
    if not needs_review_reasons or any(item.code != "AUTHORIZATION_REQUIRED" for item in needs_review_reasons):
        findings.append(
            _finding(
                "RECOVERY_PROPOSAL_NEEDS_REVIEW",
                "needs_review",
                recovery_proposal_id=proposal_id,
                recovery_request_id=recovery_request_id,
            )
        )


def _canonical_requirements(
    requirements: tuple[GenerationCapabilityRequirementDTO, ...],
) -> tuple[GenerationCapabilityRequirementDTO, ...]:
    return tuple(sorted(requirements, key=lambda item: (item.capability_id, item.requirement_level)))


def _capability_findings(
    results: tuple[CapabilityNegotiationResultDTO, ...],
) -> list[RecoveryPreExecutionReadinessFindingDTO]:
    findings: list[RecoveryPreExecutionReadinessFindingDTO] = []
    for result in results:
        if result.outcome == "satisfied":
            continue
        prefix = "REQUIRED" if result.requirement_level == "required" else "OPTIONAL"
        status: FindingStatus = "needs_review" if prefix == "REQUIRED" else "warning"
        findings.append(
            _finding(
                f"{prefix}_CAPABILITY_{result.outcome.upper()}",
                status,
                capability_id=result.capability_id,
            )
        )
    return findings


def _finding(
    code: str,
    status: FindingStatus,
    request: RecoveryStructuredGenerationRequestDTO | None = None,
    *,
    recovery_proposal_id: str = "",
    recovery_request_id: str = "",
    capability_id: str | None = None,
) -> RecoveryPreExecutionReadinessFindingDTO:
    if request is not None:
        recovery_proposal_id = request.recovery_proposal_id
        recovery_request_id = request.recovery_request_id
    return RecoveryPreExecutionReadinessFindingDTO(
        code=code,
        status=status,
        message=code.replace("_", " ").lower(),
        recovery_proposal_id=recovery_proposal_id,
        recovery_request_id=recovery_request_id,
        capability_id=capability_id,
    )


def _finding_key(
    item: RecoveryPreExecutionReadinessFindingDTO,
) -> tuple[str, str, str, str, str, str]:
    return (
        item.code,
        item.status,
        item.recovery_proposal_id,
        item.recovery_request_id,
        item.capability_id or "",
        item.message,
    )


def _report_status(
    findings: tuple[RecoveryPreExecutionReadinessFindingDTO, ...],
) -> ReportStatus:
    if any(item.status == "blocked" for item in findings):
        return "blocked"
    if any(item.status == "needs_review" for item in findings):
        return "needs_review"
    return "ready"
