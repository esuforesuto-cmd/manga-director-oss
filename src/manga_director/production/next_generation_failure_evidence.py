"""Internal projection of redacted factual failure evidence for one attempt.

This preview boundary only reads existing execution reports.  It never
invokes a provider, creates successful generation evidence, or retains raw
runtime material.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Literal

from pydantic import ConfigDict, field_validator

from manga_director.production.director import DirectorModel
from manga_director.production.next_generation_asset_registration import (
    OutputAssetRegistrationReport,
)
from manga_director.production.next_generation_provider_invocation import (
    ProviderInvocationReport,
)

FailureStage = Literal[
    "input_resolution", "provider_invocation", "asset_registration", "attempt_integrity"
]
FailureCategory = Literal[
    "upstream_not_ready",
    "input_materialization_unavailable",
    "provider_declared_failure",
    "provider_runtime_failure",
    "invalid_provider_result",
    "generated_output_handle_missing",
    "registration_failure",
    "registration_idempotency_conflict",
    "invalid_registration_result",
]
SourceFindingCode = Literal[
    "RESOLUTION_OUTCOME_NOT_READY",
    "MATERIALIZED_INPUT_MISSING",
    "PROVIDER_DECLARED_FAILURE",
    "PROVIDER_RUNTIME_FAILURE",
    "PROVIDER_RESULT_INVALID",
    "GENERATED_OUTPUT_HANDLE_MISSING",
    "OUTPUT_REGISTRATION_FAILED",
    "OUTPUT_REGISTRATION_IDEMPOTENCY_CONFLICT",
    "OUTPUT_REGISTRATION_RESULT_INVALID",
]
FindingStatus = Literal["needs_evidence", "blocked"]
ReportStatus = Literal["recorded", "needs_evidence", "blocked"]

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
_PROVIDER_SOURCE_MAPPINGS: dict[SourceFindingCode, tuple[FailureStage, FailureCategory]] = {
    "RESOLUTION_OUTCOME_NOT_READY": ("input_resolution", "upstream_not_ready"),
    "MATERIALIZED_INPUT_MISSING": (
        "input_resolution",
        "input_materialization_unavailable",
    ),
    "PROVIDER_DECLARED_FAILURE": ("provider_invocation", "provider_declared_failure"),
    "PROVIDER_RUNTIME_FAILURE": ("provider_invocation", "provider_runtime_failure"),
    "PROVIDER_RESULT_INVALID": ("provider_invocation", "invalid_provider_result"),
}
_REGISTRATION_SOURCE_MAPPINGS: dict[SourceFindingCode, tuple[FailureStage, FailureCategory]] = {
    "GENERATED_OUTPUT_HANDLE_MISSING": (
        "attempt_integrity",
        "generated_output_handle_missing",
    ),
    "OUTPUT_REGISTRATION_FAILED": ("asset_registration", "registration_failure"),
    "OUTPUT_REGISTRATION_IDEMPOTENCY_CONFLICT": (
        "asset_registration",
        "registration_idempotency_conflict",
    ),
    "OUTPUT_REGISTRATION_RESULT_INVALID": (
        "asset_registration",
        "invalid_registration_result",
    ),
}
_BINDING_CODES = {
    "INVOCATION_ATTEMPT_MISMATCH": "ATTEMPT_BINDING_MISMATCH",
    "REGISTRATION_ATTEMPT_MISMATCH": "ATTEMPT_BINDING_MISMATCH",
    "INVOCATION_PROVIDER_REFERENCE_MISMATCH": "PROVIDER_BINDING_MISMATCH",
    "REGISTRATION_PROVIDER_MISMATCH": "PROVIDER_BINDING_MISMATCH",
}


class _FailureEvidenceModel(DirectorModel):
    """Private base for immutable, closed internal-preview DTOs."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class GenerationFailureEvidenceDTO(_FailureEvidenceModel):
    """One projected, redacted factual failure for an exact attempt."""

    attempt_id: str
    request_id: str
    provider_reference: str
    failure_stage: FailureStage
    failure_category: FailureCategory
    source_finding_code: SourceFindingCode
    provenance_reference: str

    @field_validator("attempt_id", "request_id", "provider_reference", "provenance_reference")
    @classmethod
    def _validate_logical_reference(cls, value: str) -> str:
        return _logical_reference(value, "failure evidence reference")


class FailureEvidenceFindingDTO(_FailureEvidenceModel):
    """One deterministic, redacted projection finding."""

    code: str
    status: FindingStatus
    message: str
    attempt_id: str = ""
    request_id: str = ""
    provider_reference: str = ""
    provenance_reference: str = ""

    @field_validator("attempt_id", "request_id", "provider_reference", "provenance_reference")
    @classmethod
    def _validate_optional_logical_reference(cls, value: str) -> str:
        return _logical_reference(value, "failure evidence reference") if value else value


class FailureEvidenceReport(_FailureEvidenceModel):
    """Canonical, side-effect-free result for a single supplied attempt."""

    provider_invocation_report: ProviderInvocationReport
    output_asset_registration_report: OutputAssetRegistrationReport | None = None
    attempt_id: str = ""
    request_id: str = ""
    provider_reference: str = ""
    provenance_reference: str = ""
    failure_evidence: GenerationFailureEvidenceDTO | None = None
    findings: tuple[FailureEvidenceFindingDTO, ...] = ()
    status: ReportStatus
    recorded: bool
    analysis_only: Literal[True] = True

    @field_validator("attempt_id", "request_id", "provider_reference", "provenance_reference")
    @classmethod
    def _validate_optional_logical_reference(cls, value: str) -> str:
        return _logical_reference(value, "failure evidence reference") if value else value


class FailureEvidenceProjectionService:
    """Project one permitted redacted failure without execution or persistence."""

    def project(
        self,
        attempt_id: str,
        provider_invocation_report: ProviderInvocationReport,
        output_asset_registration_report: OutputAssetRegistrationReport | None = None,
    ) -> FailureEvidenceReport:
        """Return a canonical projection from supplied immutable upstream reports."""

        if not _is_logical_reference(attempt_id):
            return _report(
                provider_invocation_report,
                output_asset_registration_report,
                "",
                "",
                "",
                "",
                [_finding("INVALID_ATTEMPT_REFERENCE", "blocked")],
            )

        chain = _chain_values(provider_invocation_report, attempt_id)
        findings = _chain_findings(
            attempt_id,
            provider_invocation_report,
            output_asset_registration_report,
            chain,
        )
        if findings:
            return _report(
                provider_invocation_report,
                output_asset_registration_report,
                attempt_id,
                chain.request_id,
                chain.provider_reference,
                chain.provenance_reference,
                findings,
            )

        provider_findings = tuple(item.code for item in provider_invocation_report.findings)
        binding_findings = _upstream_binding_findings(provider_findings)
        if binding_findings:
            return _report(
                provider_invocation_report,
                output_asset_registration_report,
                attempt_id,
                chain.request_id,
                chain.provider_reference,
                chain.provenance_reference,
                binding_findings,
            )

        unsupported = _unsupported_source_findings(provider_findings, _PROVIDER_SOURCE_MAPPINGS)
        if unsupported:
            return _report(
                provider_invocation_report,
                output_asset_registration_report,
                attempt_id,
                chain.request_id,
                chain.provider_reference,
                chain.provenance_reference,
                unsupported,
            )

        provider_sources = _source_codes(provider_findings, _PROVIDER_SOURCE_MAPPINGS)
        if provider_sources:
            return _project_source(
                provider_invocation_report,
                output_asset_registration_report,
                attempt_id,
                chain,
                provider_sources,
                _PROVIDER_SOURCE_MAPPINGS,
            )
        if provider_invocation_report.status != "succeeded" or provider_invocation_report.succeeded is not True:
            return _report(
                provider_invocation_report,
                output_asset_registration_report,
                attempt_id,
                chain.request_id,
                chain.provider_reference,
                chain.provenance_reference,
                [_finding("UNSUPPORTED_FAILURE_SOURCE", "blocked", attempt_id, chain.request_id, chain.provider_reference, chain.provenance_reference)],
            )

        if output_asset_registration_report is None:
            return _report(
                provider_invocation_report,
                None,
                attempt_id,
                chain.request_id,
                chain.provider_reference,
                chain.provenance_reference,
                [_finding("FAILURE_SOURCE_NOT_PROVEN", "needs_evidence", attempt_id, chain.request_id, chain.provider_reference, chain.provenance_reference)],
            )

        registration_findings = tuple(item.code for item in output_asset_registration_report.findings)
        binding_findings = _upstream_binding_findings(registration_findings)
        if binding_findings:
            return _report(
                provider_invocation_report,
                output_asset_registration_report,
                attempt_id,
                chain.request_id,
                chain.provider_reference,
                chain.provenance_reference,
                binding_findings,
            )
        unsupported = _unsupported_source_findings(
            registration_findings, _REGISTRATION_SOURCE_MAPPINGS
        )
        if unsupported:
            return _report(
                provider_invocation_report,
                output_asset_registration_report,
                attempt_id,
                chain.request_id,
                chain.provider_reference,
                chain.provenance_reference,
                unsupported,
            )
        registration_sources = _source_codes(registration_findings, _REGISTRATION_SOURCE_MAPPINGS)
        if registration_sources:
            return _project_source(
                provider_invocation_report,
                output_asset_registration_report,
                attempt_id,
                chain,
                registration_sources,
                _REGISTRATION_SOURCE_MAPPINGS,
            )
        if (
            output_asset_registration_report.status == "registered"
            and output_asset_registration_report.registered is True
        ):
            return _report(
                provider_invocation_report,
                output_asset_registration_report,
                attempt_id,
                chain.request_id,
                chain.provider_reference,
                chain.provenance_reference,
                [_finding("SUCCESSFUL_ATTEMPT_EXCLUDED", "blocked", attempt_id, chain.request_id, chain.provider_reference, chain.provenance_reference)],
            )
        return _report(
            provider_invocation_report,
            output_asset_registration_report,
            attempt_id,
            chain.request_id,
            chain.provider_reference,
            chain.provenance_reference,
            [_finding("UNSUPPORTED_FAILURE_SOURCE", "blocked", attempt_id, chain.request_id, chain.provider_reference, chain.provenance_reference)],
        )


class _ChainValues:
    def __init__(
        self,
        request_id: str = "",
        provider_reference: str = "",
        provenance_reference: str = "",
        envelope_count: int = 0,
        resolution_attempt_id: str = "",
        request_ready: bool = False,
    ) -> None:
        self.request_id = request_id
        self.provider_reference = provider_reference
        self.provenance_reference = provenance_reference
        self.envelope_count = envelope_count
        self.resolution_attempt_id = resolution_attempt_id
        self.request_ready = request_ready


def _chain_values(report: ProviderInvocationReport, attempt_id: str) -> _ChainValues:
    resolution = report.secure_execution_input_resolution_report
    envelope_report = resolution.authorized_execution_envelope_validation_report
    matches = tuple(item for item in envelope_report.envelopes if item.attempt_id == attempt_id)
    if len(matches) != 1:
        return _ChainValues(envelope_count=len(matches), resolution_attempt_id=resolution.attempt_id)
    request_report = (
        envelope_report.execution_authorization_validation_report.readiness_report.input.request_validation_report
    )
    request = request_report.request
    return _ChainValues(
        request_id=_safe_value(request.request_id),
        provider_reference=_safe_value(matches[0].provider_reference),
        provenance_reference=_safe_value(request.provenance_reference),
        envelope_count=1,
        resolution_attempt_id=_safe_value(resolution.attempt_id),
        request_ready=request_report.status == "ready" and request_report.ready is True,
    )


def _chain_findings(
    attempt_id: str,
    invocation: ProviderInvocationReport,
    registration: OutputAssetRegistrationReport | None,
    chain: _ChainValues,
) -> list[FailureEvidenceFindingDTO]:
    findings: list[FailureEvidenceFindingDTO] = []
    if chain.envelope_count != 1 or chain.resolution_attempt_id != attempt_id or invocation.attempt_id != attempt_id:
        findings.append(_finding("ATTEMPT_BINDING_MISMATCH", "blocked", attempt_id))
    if not chain.request_ready:
        findings.append(_finding("UPSTREAM_EXECUTION_CHAIN_NOT_READY", "blocked", attempt_id))
    if not all(
        _is_logical_reference(value)
        for value in (chain.request_id, chain.provider_reference, chain.provenance_reference)
    ):
        findings.append(_finding("INVALID_LOGICAL_REFERENCE", "blocked", attempt_id))
        return findings
    envelope_report = invocation.secure_execution_input_resolution_report.authorized_execution_envelope_validation_report
    envelope = next(item for item in envelope_report.envelopes if item.attempt_id == attempt_id)
    request = (
        envelope_report.execution_authorization_validation_report.readiness_report.input.request_validation_report.request
    )
    readiness_provider = (
        envelope_report.execution_authorization_validation_report.readiness_report.input.provider_reference
    )
    if envelope.request_id != request.request_id:
        findings.append(_finding("REQUEST_BINDING_MISMATCH", "blocked", attempt_id, chain.request_id, chain.provider_reference, chain.provenance_reference))
    if invocation.provider_reference != chain.provider_reference or readiness_provider != chain.provider_reference:
        findings.append(_finding("PROVIDER_BINDING_MISMATCH", "blocked", attempt_id, chain.request_id, chain.provider_reference, chain.provenance_reference))
    if registration is not None and (
        registration.attempt_id != attempt_id
        or registration.provider_reference != chain.provider_reference
        or registration.provider_invocation_report != invocation
    ):
        findings.append(_finding("REGISTRATION_REPORT_BINDING_MISMATCH", "blocked", attempt_id, chain.request_id, chain.provider_reference, chain.provenance_reference))
    return findings


def _upstream_binding_findings(codes: tuple[str, ...]) -> list[FailureEvidenceFindingDTO]:
    return [_finding(_BINDING_CODES[code], "blocked") for code in codes if code in _BINDING_CODES]


def _source_codes(
    codes: tuple[str, ...], mappings: dict[SourceFindingCode, tuple[FailureStage, FailureCategory]]
) -> tuple[SourceFindingCode, ...]:
    return tuple(sorted(code for code in mappings if code in codes))


def _unsupported_source_findings(
    codes: tuple[str, ...], mappings: dict[SourceFindingCode, tuple[FailureStage, FailureCategory]]
) -> list[FailureEvidenceFindingDTO]:
    supported = set(mappings).union(_BINDING_CODES)
    return [_finding("UNSUPPORTED_FAILURE_SOURCE", "blocked") for code in codes if code not in supported]


def _project_source(
    invocation: ProviderInvocationReport,
    registration: OutputAssetRegistrationReport | None,
    attempt_id: str,
    chain: _ChainValues,
    source_codes: tuple[SourceFindingCode, ...],
    mappings: dict[SourceFindingCode, tuple[FailureStage, FailureCategory]],
) -> FailureEvidenceReport:
    if len(source_codes) != 1:
        return _report(
            invocation,
            registration,
            attempt_id,
            chain.request_id,
            chain.provider_reference,
            chain.provenance_reference,
            [_finding("CONFLICTING_FAILURE_SOURCE", "blocked", attempt_id, chain.request_id, chain.provider_reference, chain.provenance_reference)],
        )
    source_code = source_codes[0]
    stage, category = mappings[source_code]
    evidence = GenerationFailureEvidenceDTO(
        attempt_id=attempt_id,
        request_id=chain.request_id,
        provider_reference=chain.provider_reference,
        failure_stage=stage,
        failure_category=category,
        source_finding_code=source_code,
        provenance_reference=chain.provenance_reference,
    )
    return FailureEvidenceReport(
        provider_invocation_report=invocation,
        output_asset_registration_report=registration,
        attempt_id=attempt_id,
        request_id=chain.request_id,
        provider_reference=chain.provider_reference,
        provenance_reference=chain.provenance_reference,
        failure_evidence=evidence,
        status="recorded",
        recorded=True,
    )


def _report(
    invocation: ProviderInvocationReport,
    registration: OutputAssetRegistrationReport | None,
    attempt_id: str,
    request_id: str,
    provider_reference: str,
    provenance_reference: str,
    findings: Iterable[FailureEvidenceFindingDTO],
) -> FailureEvidenceReport:
    ordered = tuple(sorted(findings, key=_finding_key))
    status: ReportStatus = "needs_evidence" if ordered and all(
        item.status == "needs_evidence" for item in ordered
    ) else "blocked"
    return FailureEvidenceReport(
        provider_invocation_report=invocation,
        output_asset_registration_report=registration,
        attempt_id=_safe_value(attempt_id),
        request_id=_safe_value(request_id),
        provider_reference=_safe_value(provider_reference),
        provenance_reference=_safe_value(provenance_reference),
        findings=ordered,
        status=status,
        recorded=False,
    )


def _finding(
    code: str,
    status: FindingStatus,
    attempt_id: str = "",
    request_id: str = "",
    provider_reference: str = "",
    provenance_reference: str = "",
) -> FailureEvidenceFindingDTO:
    return FailureEvidenceFindingDTO(
        code=code,
        status=status,
        message=code.replace("_", " ").lower(),
        attempt_id=_safe_value(attempt_id),
        request_id=_safe_value(request_id),
        provider_reference=_safe_value(provider_reference),
        provenance_reference=_safe_value(provenance_reference),
    )


def _finding_key(item: FailureEvidenceFindingDTO) -> tuple[str, str, str, str, str, str]:
    return (
        item.code,
        item.status,
        item.attempt_id,
        item.request_id,
        item.provider_reference,
        item.provenance_reference,
    )


def _safe_value(value: str) -> str:
    return value if _is_logical_reference(value) else ""


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
