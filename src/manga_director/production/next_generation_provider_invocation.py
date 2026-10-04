"""Internal one-attempt provider invocation through an injected fake-safe port.

This preview boundary consumes a ready secure-input outcome once.  It retains
neither the raw prompt nor provider/runtime details in durable reports.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Literal, Protocol

from pydantic import ConfigDict

from manga_director.production.director import DirectorModel
from manga_director.production.next_generation_secure_execution_input_resolution import (
    MaterializedGenerationInput,
    SecureExecutionInputResolutionOutcome,
    SecureExecutionInputResolutionReport,
)

FindingStatus = Literal["blocked"]
ReportStatus = Literal["succeeded", "blocked"]
InvocationStatus = Literal["succeeded", "provider_failed", "runtime_failed"]
FailureCategory = Literal["provider_declared_failure", "runtime_failure"]
OpenAIFailureDiagnosticCategory = Literal[
    "access_failure",
    "billing_or_quota_failure",
    "rate_limit_failure",
    "transport_failure",
    "timeout_failure",
    "sdk_validation_failure",
    "response_shape_failure",
    "base64_validation_failure",
    "provider_declared_failure",
    "unknown_runtime_failure",
]


class _ProviderInvocationModel(DirectorModel):
    """Private base for closed, immutable internal-preview DTOs."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class ProviderInvocationFindingDTO(_ProviderInvocationModel):
    """One deterministic, redacted blocking finding."""

    code: str
    status: FindingStatus
    message: str
    attempt_id: str = ""
    provider_reference: str = ""
    diagnostic_category: OpenAIFailureDiagnosticCategory | None = None


class ProviderInvocationReport(_ProviderInvocationModel):
    """Durable raw-prompt-free report for one provider port call at most."""

    secure_execution_input_resolution_report: SecureExecutionInputResolutionReport
    attempt_id: str
    provider_reference: str
    findings: tuple[ProviderInvocationFindingDTO, ...] = ()
    status: ReportStatus
    succeeded: bool
    invocation_performed: bool


@dataclass(frozen=True, slots=True)
class OpaqueGeneratedOutputHandle:
    """Runtime-only generated output handle with no core-visible backing data."""

    opaque_value: object = field(repr=False, compare=False, default=None)


@dataclass(frozen=True, slots=True)
class ProviderInvocationRuntimeResult:
    """Provider-port result that is never stored in the durable report."""

    attempt_id: str
    provider_reference: str
    outcome: InvocationStatus
    output_handle: OpaqueGeneratedOutputHandle | None = field(repr=False, default=None)
    failure_category: FailureCategory | None = None
    diagnostic_category: OpenAIFailureDiagnosticCategory | None = None


@dataclass(frozen=True, slots=True)
class ProviderInvocationOutcome:
    """Private operation outcome with an optional opaque runtime output handle."""

    report: ProviderInvocationReport
    output_handle: OpaqueGeneratedOutputHandle | None = field(repr=False, default=None)


class ProviderGenerationInvocationPort(Protocol):
    """Invoke exactly one already-selected provider without credential arguments."""

    @property
    def provider_reference(self) -> str: ...

    def invoke(self, materialized_input: MaterializedGenerationInput) -> ProviderInvocationRuntimeResult: ...


class ProviderInvocationService:
    """Perform at most one port invocation for one exact resolved attempt."""

    def invoke(
        self,
        attempt_id: str,
        resolution_outcome: SecureExecutionInputResolutionOutcome,
        provider_invocation_port: ProviderGenerationInvocationPort,
    ) -> ProviderInvocationOutcome:
        """Return a redacted report and optional opaque output handle."""

        resolution_report = resolution_outcome.report
        provider_reference = _expected_provider_reference(resolution_report, attempt_id)
        findings = _precondition_findings(
            attempt_id,
            resolution_outcome,
            provider_invocation_port.provider_reference,
            provider_reference,
        )
        materialized = resolution_outcome.materialized_input
        if findings or materialized is None:
            return _outcome(
                resolution_report,
                attempt_id,
                provider_reference,
                findings,
                invocation_performed=False,
            )

        try:
            result = provider_invocation_port.invoke(materialized)
        except Exception:
            return _outcome(
                resolution_report,
                attempt_id,
                provider_reference,
                [_finding("PROVIDER_RUNTIME_FAILURE", attempt_id, provider_reference)],
                invocation_performed=True,
            )

        findings = _result_findings(result, attempt_id, provider_reference)
        output_handle = _successful_output_handle(result, findings)
        return _outcome(
            resolution_report,
            attempt_id,
            provider_reference,
            findings,
            invocation_performed=True,
            output_handle=output_handle,
        )


def _precondition_findings(
    attempt_id: str,
    resolution_outcome: SecureExecutionInputResolutionOutcome,
    port_provider_reference: str,
    expected_provider_reference: str,
) -> list[ProviderInvocationFindingDTO]:
    report = resolution_outcome.report
    materialized = resolution_outcome.materialized_input
    if report.status != "ready" or report.ready is not True:
        return [_finding("RESOLUTION_OUTCOME_NOT_READY", attempt_id, expected_provider_reference)]
    if materialized is None:
        return [_finding("MATERIALIZED_INPUT_MISSING", attempt_id, expected_provider_reference)]
    if (
        report.attempt_id != attempt_id
        or materialized.attempt_id != attempt_id
        or not expected_provider_reference
    ):
        return [_finding("INVOCATION_ATTEMPT_MISMATCH", attempt_id, expected_provider_reference)]
    if (
        materialized.provider_reference != expected_provider_reference
        or port_provider_reference != expected_provider_reference
    ):
        return [
            _finding(
                "INVOCATION_PROVIDER_REFERENCE_MISMATCH",
                attempt_id,
                expected_provider_reference,
            )
        ]
    return []


def _expected_provider_reference(
    report: SecureExecutionInputResolutionReport, attempt_id: str
) -> str:
    envelopes = report.authorized_execution_envelope_validation_report.envelopes
    matches = tuple(envelope for envelope in envelopes if envelope.attempt_id == attempt_id)
    return matches[0].provider_reference if len(matches) == 1 else ""


def _result_findings(
    result: ProviderInvocationRuntimeResult,
    attempt_id: str,
    provider_reference: str,
) -> list[ProviderInvocationFindingDTO]:
    if result.attempt_id != attempt_id:
        return [_finding("INVOCATION_ATTEMPT_MISMATCH", attempt_id, provider_reference)]
    if result.provider_reference != provider_reference:
        return [_finding("INVOCATION_PROVIDER_REFERENCE_MISMATCH", attempt_id, provider_reference)]
    if result.outcome == "provider_failed":
        if (
            result.output_handle is not None
            or result.failure_category != "provider_declared_failure"
            or result.diagnostic_category not in (None, "provider_declared_failure")
        ):
            return [_finding("PROVIDER_RESULT_INVALID", attempt_id, provider_reference)]
        return [
            _finding(
                "PROVIDER_DECLARED_FAILURE",
                attempt_id,
                provider_reference,
                result.diagnostic_category,
            )
        ]
    if result.outcome == "runtime_failed":
        if (
            result.output_handle is not None
            or result.failure_category != "runtime_failure"
            or result.diagnostic_category == "provider_declared_failure"
        ):
            return [_finding("PROVIDER_RESULT_INVALID", attempt_id, provider_reference)]
        return [
            _finding(
                "PROVIDER_RUNTIME_FAILURE",
                attempt_id,
                provider_reference,
                result.diagnostic_category,
            )
        ]
    if (
        result.output_handle is None
        or result.failure_category is not None
        or result.diagnostic_category is not None
    ):
        return [_finding("PROVIDER_RESULT_INVALID", attempt_id, provider_reference)]
    return []


def _successful_output_handle(
    result: ProviderInvocationRuntimeResult,
    findings: Iterable[ProviderInvocationFindingDTO],
) -> OpaqueGeneratedOutputHandle | None:
    if tuple(findings) or result.outcome != "succeeded":
        return None
    return result.output_handle


def _outcome(
    resolution_report: SecureExecutionInputResolutionReport,
    attempt_id: str,
    provider_reference: str,
    findings: Iterable[ProviderInvocationFindingDTO],
    *,
    invocation_performed: bool,
    output_handle: OpaqueGeneratedOutputHandle | None = None,
) -> ProviderInvocationOutcome:
    ordered_findings = tuple(sorted(findings, key=_finding_key))
    succeeded = not ordered_findings and output_handle is not None
    report = ProviderInvocationReport(
        secure_execution_input_resolution_report=resolution_report,
        attempt_id=attempt_id,
        provider_reference=provider_reference,
        findings=ordered_findings,
        status="succeeded" if succeeded else "blocked",
        succeeded=succeeded,
        invocation_performed=invocation_performed,
    )
    return ProviderInvocationOutcome(report=report, output_handle=output_handle if succeeded else None)


def _finding(
    code: str,
    attempt_id: str,
    provider_reference: str,
    diagnostic_category: OpenAIFailureDiagnosticCategory | None = None,
) -> ProviderInvocationFindingDTO:
    return ProviderInvocationFindingDTO(
        code=code,
        status="blocked",
        message=code.replace("_", " ").lower(),
        attempt_id=attempt_id,
        provider_reference=provider_reference,
        diagnostic_category=diagnostic_category,
    )


def _finding_key(item: ProviderInvocationFindingDTO) -> tuple[str, str, str, str, str]:
    return (
        item.code,
        item.status,
        item.attempt_id,
        item.provider_reference,
        item.diagnostic_category or "",
    )
