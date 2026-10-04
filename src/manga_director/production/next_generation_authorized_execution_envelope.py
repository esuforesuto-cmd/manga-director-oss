"""Internal read-only validation for authorized generation execution envelopes.

This preview contract binds caller-supplied attempt snapshots to an existing
Normal Execution Authorization report. It does not resolve input, invoke a
provider, create evidence, or persist an attempt.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from typing import Literal

from pydantic import ConfigDict, field_validator

from manga_director.production.director import DirectorModel
from manga_director.production.next_generation_execution_authorization import (
    ExecutionAuthorizationValidationReport,
)

FindingStatus = Literal["blocked", "needs_review"]
ReportStatus = Literal["ready", "needs_review", "blocked"]

_WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:[\\\\/]")
_SECRET_LIKE_PARTS = (
    "api_key",
    "apikey",
    "credential",
    "endpoint",
    "password",
    "secret",
    "token",
)


class _AuthorizedExecutionEnvelopeModel(DirectorModel):
    """Private base for closed, immutable internal-preview DTOs."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class AuthorizedGenerationExecutionEnvelopeDTO(_AuthorizedExecutionEnvelopeModel):
    """One opaque attempt snapshot with no executable prompt or provider payload."""

    attempt_id: str
    request_id: str
    provider_reference: str
    authorization_ids: tuple[str, ...]
    profile_id: str
    profile_version: str
    generation_intent_reference: str
    input_reference: str

    @field_validator(
        "attempt_id",
        "request_id",
        "provider_reference",
        "profile_id",
        "profile_version",
        "generation_intent_reference",
        "input_reference",
    )
    @classmethod
    def _validate_logical_reference(cls, value: str) -> str:
        return _logical_reference(value)

    @field_validator("authorization_ids")
    @classmethod
    def _validate_authorization_ids(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(_logical_reference(value) for value in values)


class AuthorizedGenerationExecutionEnvelopeFindingDTO(_AuthorizedExecutionEnvelopeModel):
    """One deterministic envelope-validation finding without execution payloads."""

    code: str
    status: FindingStatus
    message: str
    attempt_id: str = ""
    authorization_id: str = ""
    request_id: str = ""
    provider_reference: str = ""
    profile_id: str = ""
    profile_version: str = ""
    generation_intent_reference: str = ""
    input_reference: str = ""


class AuthorizedGenerationExecutionEnvelopeValidationReport(_AuthorizedExecutionEnvelopeModel):
    """Canonical validation report that remains separate from execution runtime."""

    execution_authorization_validation_report: ExecutionAuthorizationValidationReport
    envelopes: tuple[AuthorizedGenerationExecutionEnvelopeDTO, ...] = ()
    findings: tuple[AuthorizedGenerationExecutionEnvelopeFindingDTO, ...] = ()
    status: ReportStatus
    ready: bool
    analysis_only: Literal[True] = True


class AuthorizedGenerationExecutionEnvelopeValidationService:
    """Bind supplied attempt snapshots without selection, execution, or side effects."""

    def validate(
        self,
        envelopes: Sequence[AuthorizedGenerationExecutionEnvelopeDTO],
        execution_authorization_validation_report: ExecutionAuthorizationValidationReport,
    ) -> AuthorizedGenerationExecutionEnvelopeValidationReport:
        """Return a deterministic report for supplied envelopes and authorization evidence."""

        canonical_envelopes = _canonical_envelopes(envelopes)
        findings = _authorization_report_findings(execution_authorization_validation_report)
        findings.extend(
            _envelope_findings(canonical_envelopes, execution_authorization_validation_report)
        )
        ordered_findings = tuple(sorted(findings, key=_finding_key))
        status = _report_status(ordered_findings)
        return AuthorizedGenerationExecutionEnvelopeValidationReport(
            execution_authorization_validation_report=execution_authorization_validation_report,
            envelopes=canonical_envelopes,
            findings=ordered_findings,
            status=status,
            ready=status == "ready",
        )


def _logical_reference(value: str) -> str:
    if not value or value != value.strip() or any(character.isspace() for character in value):
        raise ValueError("execution envelope reference must be a nonblank logical reference")
    if value.startswith(("/", "\\")) or "://" in value or _WINDOWS_ABSOLUTE_PATH.match(value):
        raise ValueError("execution envelope reference must not be a path or URL")
    if "@" in value:
        raise ValueError("execution envelope reference must not contain an email address")
    if any(part in value.lower() for part in _SECRET_LIKE_PARTS):
        raise ValueError("execution envelope reference must not contain a secret-like value")
    return value


def _canonical_envelopes(
    envelopes: Sequence[AuthorizedGenerationExecutionEnvelopeDTO],
) -> tuple[AuthorizedGenerationExecutionEnvelopeDTO, ...]:
    return tuple(
        sorted(
            (
                envelope.model_copy(
                    update={"authorization_ids": tuple(sorted(envelope.authorization_ids))}
                )
                for envelope in envelopes
            ),
            key=lambda item: (
                item.attempt_id,
                item.request_id,
                item.provider_reference,
                item.profile_id,
                item.profile_version,
                item.generation_intent_reference,
                item.input_reference,
                item.authorization_ids,
            ),
        )
    )


def _authorization_report_findings(
    report: ExecutionAuthorizationValidationReport,
) -> list[AuthorizedGenerationExecutionEnvelopeFindingDTO]:
    if report.status == "ready" and report.ready is True:
        return []
    if report.status == "needs_review" and report.ready is False:
        return [_finding("AUTHORIZATION_VALIDATION_NEEDS_REVIEW", "needs_review")]
    return [_finding("AUTHORIZATION_VALIDATION_BLOCKED", "blocked")]


def _envelope_findings(
    envelopes: tuple[AuthorizedGenerationExecutionEnvelopeDTO, ...],
    report: ExecutionAuthorizationValidationReport,
) -> list[AuthorizedGenerationExecutionEnvelopeFindingDTO]:
    findings: list[AuthorizedGenerationExecutionEnvelopeFindingDTO] = []
    if not envelopes:
        findings.append(_finding("MISSING_AUTHORIZED_EXECUTION_ENVELOPE", "needs_review"))
        return findings

    request = report.readiness_report.input.request_validation_report.request
    expected_authorization_ids = tuple(sorted(item.authorization_id for item in report.authorizations))
    for attempt_id in _duplicates(item.attempt_id for item in envelopes):
        findings.append(_finding("DUPLICATE_EXECUTION_ATTEMPT_ID", "blocked", attempt_id=attempt_id))
    for envelope in envelopes:
        for authorization_id in _duplicates(envelope.authorization_ids):
            findings.append(
                _finding(
                    "DUPLICATE_AUTHORIZATION_BINDING",
                    "blocked",
                    attempt_id=envelope.attempt_id,
                    authorization_id=authorization_id,
                )
            )
        if envelope.authorization_ids != expected_authorization_ids:
            findings.append(
                _envelope_finding("EXECUTION_ENVELOPE_AUTHORIZATION_BINDING_MISMATCH", envelope)
            )
        if envelope.request_id != request.request_id:
            findings.append(_envelope_finding("EXECUTION_ENVELOPE_REQUEST_MISMATCH", envelope))
        if envelope.provider_reference != report.readiness_report.input.provider_reference:
            findings.append(_envelope_finding("EXECUTION_ENVELOPE_PROVIDER_MISMATCH", envelope))
        if envelope.profile_id != request.profile_id or envelope.profile_version != request.profile_version:
            findings.append(_envelope_finding("EXECUTION_ENVELOPE_PROFILE_MISMATCH", envelope))
        if envelope.generation_intent_reference != request.generation_intent_reference:
            findings.append(
                _envelope_finding("EXECUTION_ENVELOPE_GENERATION_INTENT_MISMATCH", envelope)
            )
        if envelope.input_reference != request.input.input_reference:
            findings.append(_envelope_finding("EXECUTION_ENVELOPE_INPUT_REFERENCE_MISMATCH", envelope))
    return findings


def _duplicates(values: Iterable[str]) -> tuple[str, ...]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return tuple(sorted(value for value, count in counts.items() if count > 1))


def _envelope_finding(
    code: Literal[
        "EXECUTION_ENVELOPE_AUTHORIZATION_BINDING_MISMATCH",
        "EXECUTION_ENVELOPE_REQUEST_MISMATCH",
        "EXECUTION_ENVELOPE_PROVIDER_MISMATCH",
        "EXECUTION_ENVELOPE_PROFILE_MISMATCH",
        "EXECUTION_ENVELOPE_GENERATION_INTENT_MISMATCH",
        "EXECUTION_ENVELOPE_INPUT_REFERENCE_MISMATCH",
    ],
    envelope: AuthorizedGenerationExecutionEnvelopeDTO,
) -> AuthorizedGenerationExecutionEnvelopeFindingDTO:
    return _finding(
        code,
        "blocked",
        attempt_id=envelope.attempt_id,
        request_id=envelope.request_id,
        provider_reference=envelope.provider_reference,
        profile_id=envelope.profile_id,
        profile_version=envelope.profile_version,
        generation_intent_reference=envelope.generation_intent_reference,
        input_reference=envelope.input_reference,
    )


def _finding(
    code: str,
    status: FindingStatus,
    *,
    attempt_id: str = "",
    authorization_id: str = "",
    request_id: str = "",
    provider_reference: str = "",
    profile_id: str = "",
    profile_version: str = "",
    generation_intent_reference: str = "",
    input_reference: str = "",
) -> AuthorizedGenerationExecutionEnvelopeFindingDTO:
    return AuthorizedGenerationExecutionEnvelopeFindingDTO(
        code=code,
        status=status,
        message=code.replace("_", " ").lower(),
        attempt_id=attempt_id,
        authorization_id=authorization_id,
        request_id=request_id,
        provider_reference=provider_reference,
        profile_id=profile_id,
        profile_version=profile_version,
        generation_intent_reference=generation_intent_reference,
        input_reference=input_reference,
    )


def _finding_key(
    item: AuthorizedGenerationExecutionEnvelopeFindingDTO,
) -> tuple[str, str, str, str, str, str, str, str, str, str]:
    return (
        item.code,
        item.status,
        item.attempt_id,
        item.authorization_id,
        item.request_id,
        item.provider_reference,
        item.profile_id,
        item.profile_version,
        item.generation_intent_reference,
        item.input_reference,
    )


def _report_status(
    findings: tuple[AuthorizedGenerationExecutionEnvelopeFindingDTO, ...],
) -> ReportStatus:
    if any(item.status == "blocked" for item in findings):
        return "blocked"
    if any(item.status == "needs_review" for item in findings):
        return "needs_review"
    return "ready"
