"""Internal fake-port validation for durable generated-output registration.

This preview boundary receives an already successful provider invocation and
delegates only its opaque output handle to an injected asset-owner port.  It
does not retain prompt or output material, access storage, or construct
generation evidence envelopes.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Literal, Protocol

from pydantic import ConfigDict, field_validator

from manga_director.production.director import DirectorModel
from manga_director.production.next_generation_generation_evidence import (
    GenerationOutputEvidenceDTO,
)
from manga_director.production.next_generation_provider_invocation import (
    OpaqueGeneratedOutputHandle,
    ProviderInvocationOutcome,
    ProviderInvocationReport,
)

FindingStatus = Literal["blocked"]
ReportStatus = Literal["registered", "blocked"]
RegistrationOutcome = Literal["registered", "failed", "idempotency_conflict"]

_WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:[\\/]")
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


class _OutputAssetRegistrationModel(DirectorModel):
    """Private base for closed, immutable internal-preview DTOs."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class RegisteredGenerationOutputDTO(_OutputAssetRegistrationModel):
    """A durable, logical output reference for one exact generation attempt."""

    attempt_id: str
    provider_reference: str
    output: GenerationOutputEvidenceDTO

    @field_validator("attempt_id", "provider_reference")
    @classmethod
    def _validate_logical_reference(cls, value: str) -> str:
        return _logical_reference(value, "registration reference")


class OutputAssetRegistrationFindingDTO(_OutputAssetRegistrationModel):
    """One deterministic, redacted blocking registration finding."""

    code: str
    status: FindingStatus
    message: str
    attempt_id: str = ""
    provider_reference: str = ""
    output_asset_id: str = ""


class OutputAssetRegistrationReport(_OutputAssetRegistrationModel):
    """Immutable registration report without an opaque output handle."""

    provider_invocation_report: ProviderInvocationReport
    attempt_id: str
    provider_reference: str
    registered_output: RegisteredGenerationOutputDTO | None = None
    findings: tuple[OutputAssetRegistrationFindingDTO, ...] = ()
    status: ReportStatus
    registered: bool
    registration_performed: bool


@dataclass(frozen=True, slots=True)
class AssetRegistrationRequest:
    """Runtime-only request whose backing output remains opaque to the core."""

    attempt_id: str
    provider_reference: str
    output_handle: OpaqueGeneratedOutputHandle = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class AssetRegistrationRuntimeResult:
    """Asset-owner result with only final logical output evidence."""

    attempt_id: str
    provider_reference: str
    outcome: RegistrationOutcome
    output: GenerationOutputEvidenceDTO | None = None
    durable_registration_confirmed: bool = False


class AssetRegistrationPort(Protocol):
    """Confirm durable output registration through an injected asset owner."""

    def register(self, request: AssetRegistrationRequest) -> AssetRegistrationRuntimeResult: ...


class OutputAssetRegistrationService:
    """Validate one fake-port durable registration without external access."""

    def register(
        self,
        attempt_id: str,
        provider_invocation_outcome: ProviderInvocationOutcome,
        asset_registration_port: AssetRegistrationPort,
    ) -> OutputAssetRegistrationReport:
        """Return a redacted durable-registration report for one exact attempt."""

        invocation_report = provider_invocation_outcome.report
        provider_reference = invocation_report.provider_reference
        findings = _precondition_findings(attempt_id, provider_invocation_outcome)
        output_handle = provider_invocation_outcome.output_handle
        if findings or output_handle is None:
            return _report(
                invocation_report,
                attempt_id,
                provider_reference,
                findings,
                registration_performed=False,
            )

        request = AssetRegistrationRequest(
            attempt_id=attempt_id,
            provider_reference=provider_reference,
            output_handle=output_handle,
        )
        try:
            result = asset_registration_port.register(request)
        except Exception:
            return _report(
                invocation_report,
                attempt_id,
                provider_reference,
                [_finding("OUTPUT_REGISTRATION_FAILED", attempt_id, provider_reference)],
                registration_performed=True,
            )

        findings = _result_findings(result, attempt_id, provider_reference)
        registered_output = _registered_output(result, findings)
        return _report(
            invocation_report,
            attempt_id,
            provider_reference,
            findings,
            registration_performed=True,
            registered_output=registered_output,
        )


def _precondition_findings(
    attempt_id: str, outcome: ProviderInvocationOutcome
) -> list[OutputAssetRegistrationFindingDTO]:
    report = outcome.report
    provider_reference = report.provider_reference
    if report.status != "succeeded" or report.succeeded is not True:
        return [_finding("PROVIDER_INVOCATION_NOT_SUCCEEDED", attempt_id, provider_reference)]
    if not _is_logical_reference(attempt_id) or report.attempt_id != attempt_id:
        return [_finding("REGISTRATION_ATTEMPT_MISMATCH", attempt_id, provider_reference)]
    if not _is_logical_reference(provider_reference):
        return [_finding("REGISTRATION_PROVIDER_MISMATCH", attempt_id, provider_reference)]
    if outcome.output_handle is None:
        return [_finding("GENERATED_OUTPUT_HANDLE_MISSING", attempt_id, provider_reference)]
    return []


def _result_findings(
    result: object, attempt_id: str, provider_reference: str
) -> list[OutputAssetRegistrationFindingDTO]:
    if not isinstance(result, AssetRegistrationRuntimeResult):
        return [_finding("OUTPUT_REGISTRATION_RESULT_INVALID", attempt_id, provider_reference)]
    if result.attempt_id != attempt_id:
        return [_finding("REGISTRATION_ATTEMPT_MISMATCH", attempt_id, provider_reference)]
    if result.provider_reference != provider_reference:
        return [_finding("REGISTRATION_PROVIDER_MISMATCH", attempt_id, provider_reference)]
    if result.outcome == "registered":
        if result.output is None or result.durable_registration_confirmed is not True:
            return [_finding("OUTPUT_REGISTRATION_RESULT_INVALID", attempt_id, provider_reference)]
        return []
    if result.outcome == "idempotency_conflict":
        if result.output is not None or result.durable_registration_confirmed:
            return [_finding("OUTPUT_REGISTRATION_RESULT_INVALID", attempt_id, provider_reference)]
        return [_finding("OUTPUT_REGISTRATION_IDEMPOTENCY_CONFLICT", attempt_id, provider_reference)]
    if result.output is not None or result.durable_registration_confirmed:
        return [_finding("OUTPUT_REGISTRATION_RESULT_INVALID", attempt_id, provider_reference)]
    return [_finding("OUTPUT_REGISTRATION_FAILED", attempt_id, provider_reference)]


def _registered_output(
    result: object, findings: Iterable[OutputAssetRegistrationFindingDTO]
) -> RegisteredGenerationOutputDTO | None:
    if tuple(findings) or not isinstance(result, AssetRegistrationRuntimeResult):
        return None
    if result.outcome != "registered" or result.output is None:
        return None
    return RegisteredGenerationOutputDTO(
        attempt_id=result.attempt_id,
        provider_reference=result.provider_reference,
        output=result.output,
    )


def _report(
    provider_invocation_report: ProviderInvocationReport,
    attempt_id: str,
    provider_reference: str,
    findings: Iterable[OutputAssetRegistrationFindingDTO],
    *,
    registration_performed: bool,
    registered_output: RegisteredGenerationOutputDTO | None = None,
) -> OutputAssetRegistrationReport:
    ordered_findings = tuple(sorted(findings, key=_finding_key))
    registered = not ordered_findings and registered_output is not None
    return OutputAssetRegistrationReport(
        provider_invocation_report=provider_invocation_report,
        attempt_id=attempt_id,
        provider_reference=provider_reference,
        registered_output=registered_output if registered else None,
        findings=ordered_findings,
        status="registered" if registered else "blocked",
        registered=registered,
        registration_performed=registration_performed,
    )


def _finding(
    code: str, attempt_id: str, provider_reference: str
) -> OutputAssetRegistrationFindingDTO:
    return OutputAssetRegistrationFindingDTO(
        code=code,
        status="blocked",
        message=code.replace("_", " ").lower(),
        attempt_id=attempt_id,
        provider_reference=provider_reference,
    )


def _finding_key(item: OutputAssetRegistrationFindingDTO) -> tuple[str, str, str, str, str]:
    return (
        item.code,
        item.status,
        item.attempt_id,
        item.provider_reference,
        item.output_asset_id,
    )


def _logical_reference(value: str, label: str) -> str:
    if not _is_logical_reference(value):
        raise ValueError(f"{label} must be a safe logical reference")
    return value


def _is_logical_reference(value: str) -> bool:
    if not isinstance(value, str) or not value or value != value.strip() or any(char.isspace() for char in value):
        return False
    if value.startswith(("/", "\\")) or "://" in value or _WINDOWS_ABSOLUTE_PATH.match(value):
        return False
    if "@" in value or any(part in value.lower() for part in _SECRET_LIKE_PARTS):
        return False
    return True
