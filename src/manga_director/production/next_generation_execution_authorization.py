"""Internal read-only validation for supplied execution authorization evidence.

This preview contract binds caller-supplied human authorization records to an
existing readiness report. It neither starts an execution attempt nor changes
workflow, provider, storage, or authorization-policy state.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import datetime
from typing import Literal

from pydantic import ConfigDict, field_validator

from manga_director.production.director import DirectorModel
from manga_director.production.next_generation_pre_execution_readiness import (
    PreExecutionReadinessReport,
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


class _ExecutionAuthorizationModel(DirectorModel):
    """Private base for closed, immutable internal-preview DTOs."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class ExecutionAuthorizationRecordDTO(_ExecutionAuthorizationModel):
    """One caller-supplied human authorization record for one request/provider pair."""

    authorization_id: str
    authorizer_id: str
    authorized_at: datetime
    request_id: str
    provider_reference: str
    rationale_reference: str | None = None

    @field_validator(
        "authorization_id",
        "authorizer_id",
        "request_id",
        "provider_reference",
        "rationale_reference",
    )
    @classmethod
    def _validate_logical_reference(cls, value: str | None) -> str | None:
        return _logical_reference(value) if value is not None else None

    @field_validator("authorized_at")
    @classmethod
    def _require_timezone_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("authorized_at must be timezone-aware")
        return value


class ExecutionAuthorizationFindingDTO(_ExecutionAuthorizationModel):
    """One deterministic validation finding without execution payloads."""

    code: str
    status: FindingStatus
    message: str
    authorization_id: str = ""
    authorizer_id: str = ""
    request_id: str = ""
    provider_reference: str = ""


class ExecutionAuthorizationValidationReport(_ExecutionAuthorizationModel):
    """Canonical authorization-evidence validation report without execution semantics."""

    readiness_report: PreExecutionReadinessReport
    authorizations: tuple[ExecutionAuthorizationRecordDTO, ...] = ()
    findings: tuple[ExecutionAuthorizationFindingDTO, ...] = ()
    status: ReportStatus
    ready: bool
    analysis_only: Literal[True] = True


class ExecutionAuthorizationValidationService:
    """Validate supplied authorization evidence without selection or side effects."""

    def validate(
        self,
        readiness_report: PreExecutionReadinessReport,
        authorizations: tuple[ExecutionAuthorizationRecordDTO, ...] = (),
    ) -> ExecutionAuthorizationValidationReport:
        """Return a canonical report for one supplied readiness report and authorization set."""

        canonical_authorizations = _canonical_authorizations(authorizations)
        findings = _readiness_findings(readiness_report)
        findings.extend(_authorization_findings(canonical_authorizations, readiness_report))
        ordered_findings = tuple(sorted(findings, key=_finding_key))
        status = _report_status(ordered_findings)
        return ExecutionAuthorizationValidationReport(
            readiness_report=readiness_report,
            authorizations=canonical_authorizations,
            findings=ordered_findings,
            status=status,
            ready=status == "ready",
        )


def _logical_reference(value: str) -> str:
    if not value or value != value.strip() or any(character.isspace() for character in value):
        raise ValueError("authorization reference must be a nonblank logical reference")
    if value.startswith(("/", "\\")) or "://" in value or _WINDOWS_ABSOLUTE_PATH.match(value):
        raise ValueError("authorization reference must not be a path or URL")
    if "@" in value:
        raise ValueError("authorization reference must not contain an email address")
    if any(part in value.lower() for part in _SECRET_LIKE_PARTS):
        raise ValueError("authorization reference must not contain a secret-like value")
    return value


def _canonical_authorizations(
    authorizations: tuple[ExecutionAuthorizationRecordDTO, ...],
) -> tuple[ExecutionAuthorizationRecordDTO, ...]:
    return tuple(
        sorted(
            authorizations,
            key=lambda item: (
                item.request_id,
                item.provider_reference,
                item.authorizer_id,
                item.authorized_at.isoformat(),
                item.authorization_id,
                item.rationale_reference or "",
            ),
        )
    )


def _readiness_findings(
    readiness_report: PreExecutionReadinessReport,
) -> list[ExecutionAuthorizationFindingDTO]:
    if readiness_report.status == "needs_review":
        return [_finding("READINESS_NEEDS_REVIEW", "needs_review")]
    if readiness_report.status == "blocked" or not readiness_report.ready:
        return [_finding("READINESS_BLOCKED", "blocked")]
    return []


def _authorization_findings(
    authorizations: tuple[ExecutionAuthorizationRecordDTO, ...],
    readiness_report: PreExecutionReadinessReport,
) -> list[ExecutionAuthorizationFindingDTO]:
    findings: list[ExecutionAuthorizationFindingDTO] = []
    if not authorizations:
        findings.append(_finding("MISSING_EXECUTION_AUTHORIZATION", "needs_review"))
        return findings
    expected_request_id = readiness_report.input.request_validation_report.request.request_id
    expected_provider_reference = readiness_report.input.provider_reference
    for authorization_id in _duplicates(item.authorization_id for item in authorizations):
        findings.append(
            _finding(
                "DUPLICATE_AUTHORIZATION_ID",
                "blocked",
                authorization_id=authorization_id,
            )
        )
    for authorizer_id, request_id, provider_reference in _duplicate_authorizer_targets(authorizations):
        findings.append(
            _finding(
                "DUPLICATE_AUTHORIZER_REQUEST_PROVIDER",
                "blocked",
                authorizer_id=authorizer_id,
                request_id=request_id,
                provider_reference=provider_reference,
            )
        )
    for authorization in authorizations:
        if authorization.request_id != expected_request_id:
            findings.append(
                _finding(
                    "AUTHORIZATION_REQUEST_MISMATCH",
                    "blocked",
                    authorization_id=authorization.authorization_id,
                    authorizer_id=authorization.authorizer_id,
                    request_id=authorization.request_id,
                    provider_reference=authorization.provider_reference,
                )
            )
        if authorization.provider_reference != expected_provider_reference:
            findings.append(
                _finding(
                    "AUTHORIZATION_PROVIDER_MISMATCH",
                    "blocked",
                    authorization_id=authorization.authorization_id,
                    authorizer_id=authorization.authorizer_id,
                    request_id=authorization.request_id,
                    provider_reference=authorization.provider_reference,
                )
            )
    return findings


def _duplicates(values: Iterable[str]) -> tuple[str, ...]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return tuple(sorted(value for value, count in counts.items() if count > 1))


def _duplicate_authorizer_targets(
    authorizations: tuple[ExecutionAuthorizationRecordDTO, ...],
) -> tuple[tuple[str, str, str], ...]:
    counts: dict[tuple[str, str, str], int] = {}
    for authorization in authorizations:
        target = (
            authorization.authorizer_id,
            authorization.request_id,
            authorization.provider_reference,
        )
        counts[target] = counts.get(target, 0) + 1
    return tuple(sorted(target for target, count in counts.items() if count > 1))


def _finding(
    code: str,
    status: FindingStatus,
    authorization_id: str = "",
    authorizer_id: str = "",
    request_id: str = "",
    provider_reference: str = "",
) -> ExecutionAuthorizationFindingDTO:
    return ExecutionAuthorizationFindingDTO(
        code=code,
        status=status,
        message=code.replace("_", " ").lower(),
        authorization_id=authorization_id,
        authorizer_id=authorizer_id,
        request_id=request_id,
        provider_reference=provider_reference,
    )


def _finding_key(
    item: ExecutionAuthorizationFindingDTO,
) -> tuple[str, str, str, str, str, str]:
    return (
        item.code,
        item.status,
        item.authorization_id,
        item.authorizer_id,
        item.request_id,
        item.provider_reference,
    )


def _report_status(
    findings: tuple[ExecutionAuthorizationFindingDTO, ...],
) -> ReportStatus:
    if any(item.status == "blocked" for item in findings):
        return "blocked"
    if any(item.status == "needs_review" for item in findings):
        return "needs_review"
    return "ready"
