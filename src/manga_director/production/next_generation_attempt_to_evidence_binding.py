"""Internal exact binding of validated Generation Evidence to one attempt.

This preview service consumes existing immutable reports.  It neither creates
nor validates Generation Evidence, and performs no execution, persistence, or
external access.
"""

from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict

from manga_director.production.director import DirectorModel
from manga_director.production.next_generation_asset_registration import (
    OutputAssetRegistrationReport,
)
from manga_director.production.next_generation_authorized_execution_envelope import (
    AuthorizedGenerationExecutionEnvelopeDTO,
)
from manga_director.production.next_generation_generation_evidence import (
    GenerationEvidenceEnvelopeDTO,
    GenerationEvidenceValidationReport,
)
from manga_director.production.next_generation_structured_generation_request import (
    StructuredGenerationRequestDTO,
)

FindingStatus = Literal["blocked"]
ReportStatus = Literal["ready", "needs_evidence", "needs_review", "blocked"]


class _AttemptToEvidenceBindingModel(DirectorModel):
    """Private base for closed, immutable internal-preview DTOs."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class AttemptToEvidenceBindingFindingDTO(_AttemptToEvidenceBindingModel):
    """One deterministic, redacted exact-binding finding."""

    code: str
    status: FindingStatus
    message: str
    attempt_id: str = ""
    request_id: str = ""
    provider_reference: str = ""
    output_asset_id: str = ""


class AttemptToEvidenceBindingReport(_AttemptToEvidenceBindingModel):
    """Immutable binding result that preserves evidence readiness semantics."""

    generation_evidence_validation_report: GenerationEvidenceValidationReport
    output_asset_registration_report: OutputAssetRegistrationReport
    attempt_id: str
    request_id: str = ""
    findings: tuple[AttemptToEvidenceBindingFindingDTO, ...] = ()
    status: ReportStatus
    bound: bool
    ready: bool
    analysis_only: Literal[True] = True


class AttemptToEvidenceBindingService:
    """Bind one already-validated evidence envelope to one registered attempt."""

    def validate(
        self,
        attempt_id: str,
        generation_evidence_validation_report: GenerationEvidenceValidationReport,
        output_asset_registration_report: OutputAssetRegistrationReport,
    ) -> AttemptToEvidenceBindingReport:
        """Return deterministic exact-binding findings without changing either input."""

        registration = output_asset_registration_report
        invocation = registration.provider_invocation_report
        resolution = invocation.secure_execution_input_resolution_report
        envelope_report = resolution.authorized_execution_envelope_validation_report
        envelopes = tuple(item for item in envelope_report.envelopes if item.attempt_id == attempt_id)
        authorized_envelope = envelopes[0] if len(envelopes) == 1 else None
        request = (
            envelope_report.execution_authorization_validation_report.readiness_report.input
            .request_validation_report.request
        )
        readiness_provider_reference = (
            envelope_report.execution_authorization_validation_report.readiness_report.input
            .provider_reference
        )
        request_id = _safe_value(request.request_id)
        provider_reference = _safe_value(
            authorized_envelope.provider_reference if authorized_envelope is not None else ""
        )
        output_asset_id = _safe_output_asset_id(registration)

        findings = _registration_findings(registration, attempt_id, provider_reference)
        findings.extend(_invocation_findings(registration, attempt_id, provider_reference))
        findings.extend(_evidence_report_findings(generation_evidence_validation_report, attempt_id))
        findings.extend(_authorized_attempt_findings(envelopes, attempt_id, provider_reference))
        evidence = _matching_evidence(generation_evidence_validation_report, attempt_id)
        findings.extend(_evidence_attempt_findings(evidence, attempt_id))
        if authorized_envelope is not None:
            findings.extend(
                _chain_findings(
                    attempt_id,
                    request_id,
                    provider_reference,
                    output_asset_id,
                    registration,
                    resolution.attempt_id,
                    authorized_envelope,
                    request,
                    readiness_provider_reference,
                    evidence,
                )
            )

        ordered_findings = tuple(sorted(findings, key=_finding_key))
        bound = not ordered_findings and generation_evidence_validation_report.status != "blocked"
        status = "blocked" if not bound else generation_evidence_validation_report.status
        return AttemptToEvidenceBindingReport(
            generation_evidence_validation_report=generation_evidence_validation_report,
            output_asset_registration_report=registration,
            attempt_id=attempt_id,
            request_id=request_id,
            findings=ordered_findings,
            status=status,
            bound=bound,
            ready=bound and status == "ready",
        )


def _registration_findings(
    registration: OutputAssetRegistrationReport,
    attempt_id: str,
    provider_reference: str,
) -> list[AttemptToEvidenceBindingFindingDTO]:
    if registration.status == "registered" and registration.registered is True:
        return []
    return [_finding("OUTPUT_REGISTRATION_NOT_REGISTERED", attempt_id, provider_reference)]


def _invocation_findings(
    registration: OutputAssetRegistrationReport,
    attempt_id: str,
    provider_reference: str,
) -> list[AttemptToEvidenceBindingFindingDTO]:
    invocation = registration.provider_invocation_report
    if invocation.status == "succeeded" and invocation.succeeded is True:
        return []
    return [_finding("PROVIDER_INVOCATION_NOT_SUCCEEDED", attempt_id, provider_reference)]


def _evidence_report_findings(
    report: GenerationEvidenceValidationReport, attempt_id: str
) -> list[AttemptToEvidenceBindingFindingDTO]:
    if report.status != "blocked":
        return []
    return [_finding("EVIDENCE_VALIDATION_BLOCKED", attempt_id)]


def _authorized_attempt_findings(
    envelopes: tuple[AuthorizedGenerationExecutionEnvelopeDTO, ...],
    attempt_id: str,
    provider_reference: str,
) -> list[AttemptToEvidenceBindingFindingDTO]:
    if len(envelopes) == 1:
        return []
    return [_finding("ATTEMPT_BINDING_MISMATCH", attempt_id, provider_reference)]


def _matching_evidence(
    report: GenerationEvidenceValidationReport, attempt_id: str
) -> tuple[GenerationEvidenceEnvelopeDTO, ...]:
    return tuple(item for item in report.envelopes if item.attempt_id == attempt_id)


def _evidence_attempt_findings(
    evidence: tuple[GenerationEvidenceEnvelopeDTO, ...], attempt_id: str
) -> list[AttemptToEvidenceBindingFindingDTO]:
    if not evidence:
        return [_finding("EVIDENCE_ATTEMPT_NOT_FOUND", attempt_id)]
    if len(evidence) > 1:
        return [_finding("EVIDENCE_ATTEMPT_NOT_UNIQUE", attempt_id)]
    return []


def _chain_findings(
    attempt_id: str,
    request_id: str,
    provider_reference: str,
    output_asset_id: str,
    registration: OutputAssetRegistrationReport,
    resolution_attempt_id: str,
    authorized_envelope: AuthorizedGenerationExecutionEnvelopeDTO,
    request: StructuredGenerationRequestDTO,
    readiness_provider_reference: str,
    evidence: tuple[GenerationEvidenceEnvelopeDTO, ...],
) -> list[AttemptToEvidenceBindingFindingDTO]:
    if len(evidence) != 1:
        return []
    envelope = authorized_envelope
    evidence_envelope = evidence[0]
    registered_output = registration.registered_output
    invocation = registration.provider_invocation_report
    findings: list[AttemptToEvidenceBindingFindingDTO] = []

    if (
        registration.attempt_id != attempt_id
        or invocation.attempt_id != attempt_id
        or resolution_attempt_id != attempt_id
        or envelope.attempt_id != attempt_id
        or evidence_envelope.attempt_id != attempt_id
        or registered_output is None
        or registered_output.attempt_id != attempt_id
    ):
        findings.append(_finding("ATTEMPT_BINDING_MISMATCH", attempt_id, provider_reference))
    if envelope.request_id != request.request_id:
        findings.append(_finding("REQUEST_BINDING_MISMATCH", attempt_id, request_id, provider_reference))
    if (
        registration.provider_reference != provider_reference
        or invocation.provider_reference != provider_reference
        or registered_output is None
        or registered_output.provider_reference != provider_reference
        or envelope.provider_reference != provider_reference
        or readiness_provider_reference != provider_reference
    ):
        findings.append(_finding("PROVIDER_BINDING_MISMATCH", attempt_id, request_id, provider_reference))
    if (
        envelope.input_reference != request.input.input_reference
        or evidence_envelope.input != request.input
    ):
        findings.append(
            _finding("INPUT_EVIDENCE_BINDING_MISMATCH", attempt_id, request_id, provider_reference)
        )
    if evidence_envelope.identity_bindings != request.identity_bindings:
        findings.append(_finding("IDENTITY_BINDING_MISMATCH", attempt_id, request_id, provider_reference))
    if registered_output is None or evidence_envelope.output != registered_output.output:
        findings.append(
            _finding(
                "OUTPUT_EVIDENCE_BINDING_MISMATCH",
                attempt_id,
                request_id,
                provider_reference,
                output_asset_id,
            )
        )
    if evidence_envelope.provenance_reference != request.provenance_reference:
        findings.append(_finding("PROVENANCE_BINDING_MISMATCH", attempt_id, request_id, provider_reference))
    return findings


def _safe_output_asset_id(registration: OutputAssetRegistrationReport) -> str:
    output = registration.registered_output
    return _safe_value(output.output.output_asset_id) if output is not None else ""


def _safe_value(value: str) -> str:
    return value if isinstance(value, str) and value and value == value.strip() else ""


def _finding(
    code: str,
    attempt_id: str,
    request_id: str = "",
    provider_reference: str = "",
    output_asset_id: str = "",
) -> AttemptToEvidenceBindingFindingDTO:
    return AttemptToEvidenceBindingFindingDTO(
        code=code,
        status="blocked",
        message=code.replace("_", " ").lower(),
        attempt_id=_safe_value(attempt_id),
        request_id=_safe_value(request_id),
        provider_reference=_safe_value(provider_reference),
        output_asset_id=_safe_value(output_asset_id),
    )


def _finding_key(
    item: AttemptToEvidenceBindingFindingDTO,
) -> tuple[str, str, str, str, str, str]:
    return (
        item.code,
        item.status,
        item.attempt_id,
        item.request_id,
        item.provider_reference,
        item.output_asset_id,
    )
