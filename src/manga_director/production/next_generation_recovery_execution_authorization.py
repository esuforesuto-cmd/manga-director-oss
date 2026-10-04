"""Internal read-only validation for supplied recovery authorization evidence.

This preview contract binds caller-supplied human authorization records to an
existing Recovery Pre-Execution Readiness report. It never authorizes an
attempt at runtime, invokes a provider, or changes workflow state.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import datetime
from typing import Literal

from pydantic import ConfigDict, field_validator

from manga_director.production.director import DirectorModel
from manga_director.production.next_generation_recovery_pre_execution_readiness import (
    RecoveryPreExecutionReadinessReport,
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


class _RecoveryExecutionAuthorizationModel(DirectorModel):
    """Private base for closed, immutable internal-preview DTOs."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class RecoveryExecutionAuthorizationRecordDTO(_RecoveryExecutionAuthorizationModel):
    """One human authorization record bound to one recovery target and provider."""

    authorization_id: str
    authorizer_id: str
    authorized_at: datetime
    recovery_proposal_id: str
    recovery_request_id: str
    provider_reference: str
    rationale_reference: str | None = None

    @field_validator(
        "authorization_id",
        "authorizer_id",
        "recovery_proposal_id",
        "recovery_request_id",
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


class RecoveryExecutionAuthorizationFindingDTO(_RecoveryExecutionAuthorizationModel):
    """One deterministic validation finding without execution payloads."""

    code: str
    status: FindingStatus
    message: str
    authorization_id: str = ""
    authorizer_id: str = ""
    recovery_proposal_id: str = ""
    recovery_request_id: str = ""
    provider_reference: str = ""


class RecoveryExecutionAuthorizationValidationReport(_RecoveryExecutionAuthorizationModel):
    """Canonical authorization-evidence report without execution semantics."""

    recovery_readiness_report: RecoveryPreExecutionReadinessReport
    authorization_records: tuple[RecoveryExecutionAuthorizationRecordDTO, ...] = ()
    findings: tuple[RecoveryExecutionAuthorizationFindingDTO, ...] = ()
    status: ReportStatus
    ready: bool
    analysis_only: Literal[True] = True


class RecoveryExecutionAuthorizationValidationService:
    """Validate supplied recovery authorization evidence without side effects."""

    def validate(
        self,
        recovery_readiness_report: RecoveryPreExecutionReadinessReport,
        authorization_records: tuple[RecoveryExecutionAuthorizationRecordDTO, ...] = (),
    ) -> RecoveryExecutionAuthorizationValidationReport:
        """Return a deterministic report for supplied readiness and authorization evidence."""

        canonical_records = _canonical_records(authorization_records)
        findings = _readiness_findings(recovery_readiness_report)
        findings.extend(_authorization_findings(canonical_records, recovery_readiness_report))
        ordered_findings = tuple(sorted(findings, key=_finding_key))
        status = _report_status(ordered_findings)
        return RecoveryExecutionAuthorizationValidationReport(
            recovery_readiness_report=recovery_readiness_report,
            authorization_records=canonical_records,
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


def _canonical_records(
    records: tuple[RecoveryExecutionAuthorizationRecordDTO, ...],
) -> tuple[RecoveryExecutionAuthorizationRecordDTO, ...]:
    return tuple(
        sorted(
            records,
            key=lambda item: (
                item.recovery_proposal_id,
                item.recovery_request_id,
                item.provider_reference,
                item.authorizer_id,
                item.authorized_at.isoformat(),
                item.authorization_id,
                item.rationale_reference or "",
            ),
        )
    )


def _readiness_findings(
    report: RecoveryPreExecutionReadinessReport,
) -> list[RecoveryExecutionAuthorizationFindingDTO]:
    if report.status == "ready" and report.ready is True:
        return []
    if report.status == "needs_review" and report.ready is False:
        return [_finding("RECOVERY_READINESS_NEEDS_REVIEW", "needs_review")]
    return [_finding("RECOVERY_READINESS_BLOCKED", "blocked")]


def _authorization_findings(
    records: tuple[RecoveryExecutionAuthorizationRecordDTO, ...],
    readiness_report: RecoveryPreExecutionReadinessReport,
) -> list[RecoveryExecutionAuthorizationFindingDTO]:
    findings: list[RecoveryExecutionAuthorizationFindingDTO] = []
    if not records:
        findings.append(_finding("MISSING_RECOVERY_EXECUTION_AUTHORIZATION", "needs_review"))
        return findings

    request = readiness_report.input.recovery_request_validation_report.request
    expected_proposal_id = request.recovery_proposal_id
    expected_request_id = request.recovery_request_id
    expected_provider_reference = readiness_report.input.provider_reference
    for authorization_id in _duplicates(item.authorization_id for item in records):
        findings.append(
            _finding(
                "DUPLICATE_RECOVERY_AUTHORIZATION_ID",
                "blocked",
                authorization_id=authorization_id,
            )
        )
    for target in _duplicate_authorizer_targets(records):
        findings.append(
            _finding(
                "DUPLICATE_RECOVERY_AUTHORIZER_TARGET",
                "blocked",
                authorizer_id=target[0],
                recovery_proposal_id=target[1],
                recovery_request_id=target[2],
                provider_reference=target[3],
            )
        )
    for record in records:
        if record.recovery_proposal_id != expected_proposal_id:
            findings.append(
                _record_finding("RECOVERY_AUTHORIZATION_PROPOSAL_MISMATCH", record)
            )
        if record.recovery_request_id != expected_request_id:
            findings.append(
                _record_finding("RECOVERY_AUTHORIZATION_REQUEST_MISMATCH", record)
            )
        if record.provider_reference != expected_provider_reference:
            findings.append(
                _record_finding("RECOVERY_AUTHORIZATION_PROVIDER_MISMATCH", record)
            )
    return findings


def _duplicates(values: Iterable[str]) -> tuple[str, ...]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return tuple(sorted(value for value, count in counts.items() if count > 1))


def _duplicate_authorizer_targets(
    records: tuple[RecoveryExecutionAuthorizationRecordDTO, ...],
) -> tuple[tuple[str, str, str, str], ...]:
    counts: dict[tuple[str, str, str, str], int] = {}
    for record in records:
        target = (
            record.authorizer_id,
            record.recovery_proposal_id,
            record.recovery_request_id,
            record.provider_reference,
        )
        counts[target] = counts.get(target, 0) + 1
    return tuple(sorted(target for target, count in counts.items() if count > 1))


def _record_finding(
    code: Literal[
        "RECOVERY_AUTHORIZATION_PROPOSAL_MISMATCH",
        "RECOVERY_AUTHORIZATION_REQUEST_MISMATCH",
        "RECOVERY_AUTHORIZATION_PROVIDER_MISMATCH",
    ],
    record: RecoveryExecutionAuthorizationRecordDTO,
) -> RecoveryExecutionAuthorizationFindingDTO:
    return _finding(
        code,
        "blocked",
        authorization_id=record.authorization_id,
        authorizer_id=record.authorizer_id,
        recovery_proposal_id=record.recovery_proposal_id,
        recovery_request_id=record.recovery_request_id,
        provider_reference=record.provider_reference,
    )


def _finding(
    code: str,
    status: FindingStatus,
    *,
    authorization_id: str = "",
    authorizer_id: str = "",
    recovery_proposal_id: str = "",
    recovery_request_id: str = "",
    provider_reference: str = "",
) -> RecoveryExecutionAuthorizationFindingDTO:
    return RecoveryExecutionAuthorizationFindingDTO(
        code=code,
        status=status,
        message=code.replace("_", " ").lower(),
        authorization_id=authorization_id,
        authorizer_id=authorizer_id,
        recovery_proposal_id=recovery_proposal_id,
        recovery_request_id=recovery_request_id,
        provider_reference=provider_reference,
    )


def _finding_key(
    item: RecoveryExecutionAuthorizationFindingDTO,
) -> tuple[str, str, str, str, str, str, str]:
    return (
        item.code,
        item.status,
        item.authorization_id,
        item.authorizer_id,
        item.recovery_proposal_id,
        item.recovery_request_id,
        item.provider_reference,
    )


def _report_status(
    findings: tuple[RecoveryExecutionAuthorizationFindingDTO, ...],
) -> ReportStatus:
    if any(item.status == "blocked" for item in findings):
        return "blocked"
    if any(item.status == "needs_review" for item in findings):
        return "needs_review"
    return "ready"
