"""Internal construction of validated Generation Evidence for one registered attempt.

This preview boundary consumes immutable reports only.  It neither accesses an
output handle nor persists, executes, retrieves, or repairs anything.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from pydantic import ConfigDict

from manga_director.production.director import DirectorModel
from manga_director.production.next_generation_asset_registration import (
    OutputAssetRegistrationReport,
)
from manga_director.production.next_generation_attempt_to_evidence_binding import (
    AttemptToEvidenceBindingReport,
    AttemptToEvidenceBindingService,
)
from manga_director.production.next_generation_authorized_execution_envelope import (
    AuthorizedGenerationExecutionEnvelopeDTO,
)
from manga_director.production.next_generation_generation_evidence import (
    EvidenceValueDTO,
    GenerationConfigurationEvidenceDTO,
    GenerationEvidenceEnvelopeDTO,
    GenerationEvidenceValidationReport,
    GenerationEvidenceValidationService,
)
from manga_director.production.next_generation_provider_configuration import (
    ProviderConfigurationNormalizationReport,
)
from manga_director.production.next_generation_structured_generation_request import (
    StructuredGenerationRequestDTO,
)

FindingStatus = Literal["blocked"]
ReportStatus = Literal["ready", "needs_evidence", "needs_review", "blocked"]


class _AttemptToEvidenceConstructionModel(DirectorModel):
    """Private base for closed, immutable internal-preview DTOs."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class AttemptToEvidenceConstructionFindingDTO(_AttemptToEvidenceConstructionModel):
    """One deterministic, redacted construction finding."""

    code: str
    status: FindingStatus
    message: str
    attempt_id: str = ""
    request_id: str = ""
    provider_reference: str = ""
    output_asset_id: str = ""


class AttemptToEvidenceConstructionReport(_AttemptToEvidenceConstructionModel):
    """Immutable result for one read-only construction and binding attempt."""

    output_asset_registration_report: OutputAssetRegistrationReport
    provider_configuration_normalization_report: ProviderConfigurationNormalizationReport
    attempt_id: str = ""
    request_id: str = ""
    provider_reference: str = ""
    generation_evidence: GenerationEvidenceEnvelopeDTO | None = None
    generation_evidence_validation_report: GenerationEvidenceValidationReport | None = None
    attempt_to_evidence_binding_report: AttemptToEvidenceBindingReport | None = None
    findings: tuple[AttemptToEvidenceConstructionFindingDTO, ...] = ()
    status: ReportStatus
    constructed: bool
    bound: bool
    ready: bool
    analysis_only: Literal[True] = True
    persistence_performed: Literal[False] = False
    assets_read: Literal[False] = False
    provider_executed: Literal[False] = False
    timestamp_generated: Literal[False] = False


@dataclass(frozen=True, slots=True)
class _ExecutionChain:
    """Private, report-derived values needed to construct one envelope."""

    attempt_id: str
    request_id: str
    provider_reference: str
    profile_id: str
    profile_version: str
    request: StructuredGenerationRequestDTO
    authorized_envelope: AuthorizedGenerationExecutionEnvelopeDTO


class AttemptToEvidenceConstructionService:
    """Construct and bind evidence using the existing validators only."""

    def construct(
        self,
        attempt_id: str,
        observed_at: datetime,
        output_asset_registration_report: OutputAssetRegistrationReport,
        provider_configuration_normalization_report: ProviderConfigurationNormalizationReport,
    ) -> AttemptToEvidenceConstructionReport:
        """Return a deterministic redacted result without persistence or runtime access."""

        registration = output_asset_registration_report
        configuration = provider_configuration_normalization_report
        chain, findings = _execution_chain(registration, attempt_id)
        if chain is not None:
            findings.extend(_configuration_findings(configuration, chain))
        if not _is_timezone_aware(observed_at):
            findings.append(_finding("OBSERVED_AT_INVALID", attempt_id))
        if findings or chain is None:
            return _blocked_report(registration, configuration, attempt_id, chain, findings)

        try:
            evidence = _evidence_envelope(chain, observed_at, registration, configuration)
        except (TypeError, ValueError, AttributeError):
            return _blocked_report(
                registration,
                configuration,
                attempt_id,
                chain,
                [_finding("MALFORMED_EXECUTION_CHAIN", attempt_id, chain)],
            )

        evidence_report = GenerationEvidenceValidationService().validate((evidence,))
        if evidence_report.status == "blocked":
            return _blocked_report(
                registration,
                configuration,
                attempt_id,
                chain,
                [_finding("EVIDENCE_VALIDATION_BLOCKED", attempt_id, chain)],
                generation_evidence_validation_report=evidence_report,
            )

        binding_report = AttemptToEvidenceBindingService().validate(
            attempt_id, evidence_report, registration
        )
        if binding_report.status == "blocked" or binding_report.bound is not True:
            return _blocked_report(
                registration,
                configuration,
                attempt_id,
                chain,
                [_finding("ATTEMPT_TO_EVIDENCE_BINDING_FAILED", attempt_id, chain)],
                generation_evidence_validation_report=evidence_report,
                attempt_to_evidence_binding_report=binding_report,
            )

        return AttemptToEvidenceConstructionReport(
            output_asset_registration_report=registration,
            provider_configuration_normalization_report=configuration,
            attempt_id=chain.attempt_id,
            request_id=chain.request_id,
            provider_reference=chain.provider_reference,
            generation_evidence=evidence,
            generation_evidence_validation_report=evidence_report,
            attempt_to_evidence_binding_report=binding_report,
            status=binding_report.status,
            constructed=True,
            bound=binding_report.bound,
            ready=binding_report.ready,
        )


def _execution_chain(
    registration: OutputAssetRegistrationReport, attempt_id: str
) -> tuple[_ExecutionChain | None, list[AttemptToEvidenceConstructionFindingDTO]]:
    if not _is_logical_reference(attempt_id):
        return None, [_finding("INVALID_ATTEMPT_REFERENCE", attempt_id)]
    if registration.status != "registered" or registration.registered is not True:
        return None, [_finding("OUTPUT_REGISTRATION_NOT_REGISTERED", attempt_id)]
    if registration.registered_output is None:
        return None, [_finding("REGISTERED_OUTPUT_MISSING", attempt_id)]
    try:
        invocation = registration.provider_invocation_report
        resolution = invocation.secure_execution_input_resolution_report
        envelope_report = resolution.authorized_execution_envelope_validation_report
        authorization = envelope_report.execution_authorization_validation_report
        readiness = authorization.readiness_report
        request_report = readiness.input.request_validation_report
        request = request_report.request
        envelopes = tuple(item for item in envelope_report.envelopes if item.attempt_id == attempt_id)
    except (AttributeError, TypeError):
        return None, [_finding("MALFORMED_EXECUTION_CHAIN", attempt_id)]

    if invocation.status != "succeeded" or invocation.succeeded is not True:
        return None, [_finding("PROVIDER_INVOCATION_NOT_SUCCEEDED", attempt_id)]
    if (
        resolution.status != "ready"
        or resolution.ready is not True
        or envelope_report.status != "ready"
        or envelope_report.ready is not True
        or authorization.status != "ready"
        or authorization.ready is not True
        or readiness.status != "ready"
        or readiness.ready is not True
        or request_report.status != "ready"
        or request_report.ready is not True
    ):
        return None, [_finding("UPSTREAM_EXECUTION_CHAIN_NOT_READY", attempt_id)]
    if len(envelopes) != 1:
        return None, [_finding("ATTEMPT_BINDING_MISMATCH", attempt_id)]

    envelope = envelopes[0]
    provider_reference = _safe_value(envelope.provider_reference)
    request_id = _safe_value(request.request_id)
    profile_id = _safe_value(envelope.profile_id)
    profile_version = _safe_value(envelope.profile_version)
    output = registration.registered_output
    if not all((provider_reference, request_id, profile_id, profile_version)):
        return None, [_finding("MALFORMED_EXECUTION_CHAIN", attempt_id)]
    if (
        registration.attempt_id != attempt_id
        or invocation.attempt_id != attempt_id
        or resolution.attempt_id != attempt_id
        or envelope.attempt_id != attempt_id
        or output.attempt_id != attempt_id
    ):
        return None, [_finding("ATTEMPT_BINDING_MISMATCH", attempt_id, provider_reference=provider_reference)]
    if (
        registration.provider_reference != provider_reference
        or invocation.provider_reference != provider_reference
        or output.provider_reference != provider_reference
        or readiness.input.provider_reference != provider_reference
    ):
        return None, [_finding("PROVIDER_BINDING_MISMATCH", attempt_id, provider_reference=provider_reference)]
    if (
        envelope.request_id != request_id
        or envelope.profile_id != request.profile_id
        or envelope.profile_version != request.profile_version
    ):
        return None, [_finding("MALFORMED_EXECUTION_CHAIN", attempt_id, provider_reference=provider_reference)]
    return (
        _ExecutionChain(
            attempt_id=attempt_id,
            request_id=request_id,
            provider_reference=provider_reference,
            profile_id=profile_id,
            profile_version=profile_version,
            request=request,
            authorized_envelope=envelope,
        ),
        [],
    )


def _configuration_findings(
    configuration: ProviderConfigurationNormalizationReport,
    chain: _ExecutionChain,
) -> list[AttemptToEvidenceConstructionFindingDTO]:
    selection = configuration.selection
    if configuration.status != "ready" or configuration.ready is not True or selection is None:
        return [_finding("PROVIDER_CONFIGURATION_NOT_READY", chain.attempt_id, chain)]
    try:
        configuration_envelopes = tuple(
            item
            for item in configuration.authorized_execution_envelope_validation_report.envelopes
            if item.attempt_id == chain.attempt_id
        )
    except (AttributeError, TypeError):
        return [_finding("MALFORMED_EXECUTION_CHAIN", chain.attempt_id, chain)]
    if len(configuration_envelopes) != 1:
        return [_finding("PROVIDER_CONFIGURATION_BINDING_MISMATCH", chain.attempt_id, chain)]
    configuration_envelope = configuration_envelopes[0]
    execution_envelope = chain.authorized_envelope
    if (
        selection.attempt_id != chain.attempt_id
        or selection.provider_reference != chain.provider_reference
        or selection.profile_id != chain.profile_id
        or selection.profile_version != chain.profile_version
        or configuration_envelope.request_id != execution_envelope.request_id
        or configuration_envelope.provider_reference != execution_envelope.provider_reference
        or configuration_envelope.profile_id != execution_envelope.profile_id
        or configuration_envelope.profile_version != execution_envelope.profile_version
        or configuration_envelope.generation_intent_reference
        != execution_envelope.generation_intent_reference
        or configuration_envelope.input_reference != execution_envelope.input_reference
    ):
        return [_finding("PROVIDER_CONFIGURATION_BINDING_MISMATCH", chain.attempt_id, chain)]
    return []


def _evidence_envelope(
    chain: _ExecutionChain,
    observed_at: datetime,
    registration: OutputAssetRegistrationReport,
    configuration: ProviderConfigurationNormalizationReport,
) -> GenerationEvidenceEnvelopeDTO:
    selection = configuration.selection
    output = registration.registered_output
    if selection is None or output is None:
        raise ValueError("validated construction input is unavailable")
    seed = selection.requested_seed or EvidenceValueDTO(availability="unknown")
    return GenerationEvidenceEnvelopeDTO(
        attempt_id=chain.attempt_id,
        observed_at=observed_at,
        provenance_reference=chain.request.provenance_reference,
        input=chain.request.input,
        output=output.output,
        configuration=GenerationConfigurationEvidenceDTO(
            provider_id=selection.provider_id,
            model_id=selection.model_id,
            model_version=selection.model_version,
            workflow_id=selection.workflow_id,
            workflow_version=selection.workflow_version,
            seed=seed,
        ),
        identity_bindings=chain.request.identity_bindings,
    )


def _blocked_report(
    registration: OutputAssetRegistrationReport,
    configuration: ProviderConfigurationNormalizationReport,
    attempt_id: str,
    chain: _ExecutionChain | None,
    findings: list[AttemptToEvidenceConstructionFindingDTO],
    *,
    generation_evidence_validation_report: GenerationEvidenceValidationReport | None = None,
    attempt_to_evidence_binding_report: AttemptToEvidenceBindingReport | None = None,
) -> AttemptToEvidenceConstructionReport:
    ordered_findings = tuple(sorted(findings, key=_finding_key))
    return AttemptToEvidenceConstructionReport(
        output_asset_registration_report=registration,
        provider_configuration_normalization_report=configuration,
        attempt_id=_safe_value(attempt_id),
        request_id=chain.request_id if chain is not None else "",
        provider_reference=chain.provider_reference if chain is not None else "",
        generation_evidence_validation_report=generation_evidence_validation_report,
        attempt_to_evidence_binding_report=attempt_to_evidence_binding_report,
        findings=ordered_findings,
        status="blocked",
        constructed=False,
        bound=False,
        ready=False,
    )


def _finding(
    code: str,
    attempt_id: str,
    chain: _ExecutionChain | None = None,
    *,
    provider_reference: str = "",
) -> AttemptToEvidenceConstructionFindingDTO:
    output_asset_id = ""
    if chain is not None:
        provider_reference = chain.provider_reference
    return AttemptToEvidenceConstructionFindingDTO(
        code=code,
        status="blocked",
        message=code.replace("_", " ").lower(),
        attempt_id=_safe_value(attempt_id),
        request_id=chain.request_id if chain is not None else "",
        provider_reference=_safe_value(provider_reference),
        output_asset_id=output_asset_id,
    )


def _finding_key(
    finding: AttemptToEvidenceConstructionFindingDTO,
) -> tuple[str, str, str, str, str, str]:
    return (
        finding.code,
        finding.status,
        finding.attempt_id,
        finding.request_id,
        finding.provider_reference,
        finding.output_asset_id,
    )


def _is_timezone_aware(value: object) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def _safe_value(value: object) -> str:
    return value if isinstance(value, str) and _is_logical_reference(value) else ""


def _is_logical_reference(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip() and not any(
        character.isspace() for character in value
    )
