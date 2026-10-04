"""Private, fake-safe composition for one normal generation attempt.

The composition owns ordering and Attempt Authority only.  Existing services
remain the sole owners of resolution, invocation, registration, evidence, and
LocalFile external application algorithms.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Protocol, cast

from pydantic import ConfigDict

from manga_director.production.director import DirectorModel
from manga_director.production.next_generation_asset_registration import (
    OutputAssetRegistrationService,
)
from manga_director.production.next_generation_attempt_to_evidence_construction import (
    AttemptToEvidenceConstructionService,
)
from manga_director.production.next_generation_durable_evidence_workflow_binding import (
    AuthoritativeWorkflowPageMappingDTO,
    DurableEvidenceWorkflowBindingReport,
    DurableEvidenceWorkflowBindingValidationService,
    WorkflowApplicationAuthorizationDTO,
)
from manga_director.production.next_generation_execution_authorization import (
    ExecutionAuthorizationValidationReport,
)
from manga_director.production.next_generation_generation_evidence_persistence import (
    GenerationEvidencePersistenceService,
)
from manga_director.production.next_generation_normal_execution_attempt import (
    NormalExecutionAttemptReservationDTO,
    NormalExecutionAttemptService,
    NormalExecutionAttemptStorePort,
    derive_execution_fingerprint,
)
from manga_director.production.next_generation_pre_execution_readiness import (
    PreExecutionReadinessReport,
)
from manga_director.production.next_generation_provider_capability_negotiation import (
    CapabilityNegotiationReport,
)
from manga_director.production.next_generation_provider_configuration import (
    ProviderConfigurationNormalizationReport,
)
from manga_director.production.next_generation_provider_invocation import (
    ProviderGenerationInvocationPort,
    ProviderInvocationService,
)
from manga_director.production.next_generation_provider_output_configuration import (
    ProviderOutputConfigurationBindingReport,
)
from manga_director.production.next_generation_secure_execution_input_resolution import (
    GenerationInputResolverPort,
    ReferenceAssetResolverPort,
    SecureExecutionInputResolutionService,
)
from manga_director.production.next_generation_structured_generation_request import (
    StructuredGenerationRequestValidationReport,
)


class _CompositionModel(DirectorModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class NormalExecutionCompositionFindingDTO(_CompositionModel):
    code: str
    status: Literal["blocked", "partial"]
    message: str
    attempt_id: str = ""
    project_id: str = ""
    page_id: str = ""


class NormalExecutionCompositionReport(_CompositionModel):
    attempt_id: str
    findings: tuple[NormalExecutionCompositionFindingDTO, ...] = ()
    status: Literal["completed", "partial", "blocked"]
    provider_invocation_performed: bool
    external_application_delegated: bool
    completed: bool


class _ExternalApplicationPort(Protocol):
    def apply(
        self,
        binding_report: DurableEvidenceWorkflowBindingReport,
        authorization: WorkflowApplicationAuthorizationDTO,
    ) -> object: ...


class _WorkflowContextLoaderPort(Protocol):
    def load(self, project_id: str, page_id: str) -> object | None: ...


@dataclass(frozen=True, slots=True)
class NormalExecutionCompositionInput:
    """Runtime-only carrier; it intentionally contains no raw prompt field."""

    reservation: NormalExecutionAttemptReservationDTO
    structured_request_validation_report: StructuredGenerationRequestValidationReport
    capability_negotiation_report: CapabilityNegotiationReport
    pre_execution_readiness_report: PreExecutionReadinessReport
    execution_authorization_validation_report: ExecutionAuthorizationValidationReport
    authorized_execution_envelope_validation_report: object
    workflow_application_authorization: WorkflowApplicationAuthorizationDTO
    page_mapping: AuthoritativeWorkflowPageMappingDTO
    workflow_context_loader: _WorkflowContextLoaderPort
    generation_input_resolver: GenerationInputResolverPort
    reference_asset_resolver: ReferenceAssetResolverPort
    provider_invocation_port: ProviderGenerationInvocationPort
    asset_registration_port: object
    evidence_store: object
    external_application_coordinator: _ExternalApplicationPort
    observed_at: datetime
    provider_configuration_report: ProviderConfigurationNormalizationReport
    provider_output_configuration_report: ProviderOutputConfigurationBindingReport


class NormalExecutionCompositionService:
    """Execute one already-authorized normal attempt without retry or fallback."""

    def __init__(
        self,
        *,
        attempt_service: NormalExecutionAttemptService | None = None,
        resolution_service: SecureExecutionInputResolutionService | None = None,
        invocation_service: ProviderInvocationService | None = None,
        registration_service: OutputAssetRegistrationService | None = None,
        construction_service: AttemptToEvidenceConstructionService | None = None,
        persistence_service: GenerationEvidencePersistenceService | None = None,
        binding_service: DurableEvidenceWorkflowBindingValidationService | None = None,
    ) -> None:
        self._attempts = attempt_service or NormalExecutionAttemptService()
        self._resolution = resolution_service or SecureExecutionInputResolutionService()
        self._invocation = invocation_service or ProviderInvocationService()
        self._registration = registration_service or OutputAssetRegistrationService()
        self._construction = construction_service or AttemptToEvidenceConstructionService()
        self._persistence = persistence_service or GenerationEvidencePersistenceService()
        self._binding = binding_service or DurableEvidenceWorkflowBindingValidationService()

    def execute(  # noqa: C901 - frozen canonical chain deliberately has visible ordered gates.
        self,
        request: NormalExecutionCompositionInput,
        attempt_store: NormalExecutionAttemptStorePort,
    ) -> NormalExecutionCompositionReport:
        """Run the frozen chain once; all downstream failures preserve partial progress."""

        preflight = self._preflight(request)
        if preflight:
            return _result(request.reservation.attempt_id, "blocked", preflight)
        reservation = _derived_reservation(request)
        reserved = self._attempts.reserve(reservation, attempt_store)
        if reserved.status == "blocked":
            return _result(request.reservation.attempt_id, "blocked", [_finding("ATTEMPT_RESERVATION_BLOCKED", "blocked", request)])
        if reserved.state != "RESERVED":
            return _result(request.reservation.attempt_id, "completed" if reserved.state == "COMPLETED" else "partial", [_finding("ATTEMPT_REPLAY_NO_PROVIDER", "partial", request)])

        resolution = self._resolution.resolve(
            request.reservation.attempt_id,
            cast(Any, request.authorized_execution_envelope_validation_report),
            request.generation_input_resolver,
            request.reference_asset_resolver,
        )
        if getattr(resolution.report, "ready", False) is not True:
            return _result(request.reservation.attempt_id, "blocked", [_finding("SECURE_RESOLUTION_BLOCKED", "blocked", request)])

        started = self._attempts.begin_provider(reservation, attempt_store)
        if started.provider_invocation_permitted is not True:
            return _result(request.reservation.attempt_id, "partial", [_finding("PROVIDER_CALL_ALREADY_CONSUMED", "partial", request)])
        invocation = self._invocation.invoke(request.reservation.attempt_id, resolution, request.provider_invocation_port)
        if invocation.report.succeeded is not True:
            if _provider_declared_failure(invocation.report) and invocation.report.invocation_performed:
                self._attempts.record_provider_declared_failure(reservation, attempt_store)
                return _result(request.reservation.attempt_id, "completed", [_finding("PROVIDER_DECLARED_TERMINAL_FAILURE", "partial", request)], invoked=True, completed=True)
            return _result(request.reservation.attempt_id, "partial", [_finding("PROVIDER_OUTCOME_AMBIGUOUS", "partial", request)], invoked=invocation.report.invocation_performed)

        provider_completed = self._attempts.record_provider_success(reservation, attempt_store)
        if provider_completed.status == "blocked":
            return _result(request.reservation.attempt_id, "partial", [_finding("PROVIDER_COMPLETION_RECORD_BLOCKED", "partial", request)], invoked=True)
        registration = self._registration.register(request.reservation.attempt_id, invocation, cast(Any, request.asset_registration_port))
        if getattr(registration, "registered", False) is not True:
            return _result(request.reservation.attempt_id, "partial", [_finding("ASSET_REGISTRATION_PARTIAL", "partial", request)], invoked=True)
        construction = self._construction.construct(
            request.reservation.attempt_id, request.observed_at, registration, cast(Any, request.provider_configuration_report)
        )
        if getattr(construction, "constructed", False) is not True:
            return _result(request.reservation.attempt_id, "partial", [_finding("EVIDENCE_CONSTRUCTION_PARTIAL", "partial", request)], invoked=True)
        persistence = self._persistence.persist(construction, cast(Any, request.evidence_store))
        if getattr(persistence, "persisted", False) is not True:
            return _result(request.reservation.attempt_id, "partial", [_finding("EVIDENCE_PERSISTENCE_PARTIAL", "partial", request)], invoked=True)
        context = _load_context(request)
        binding = self._binding.validate(
            request.workflow_application_authorization, request.page_mapping, cast(Any, context),
            persistence, cast(Any, request.evidence_store), construction,
        )
        if getattr(binding, "eligible", False) is not True:
            return _result(request.reservation.attempt_id, "partial", [_finding("WORKFLOW_BINDING_PARTIAL", "partial", request)], invoked=True)
        application = request.external_application_coordinator.apply(binding, request.workflow_application_authorization)
        if getattr(application, "status", "") != "application_applied_event_published":
            return _result(request.reservation.attempt_id, "partial", [_finding("EXTERNAL_APPLICATION_PARTIAL", "partial", request)], invoked=True, delegated=True)
        completed = self._attempts.complete_after_application(reservation, attempt_store)
        if completed.status == "blocked":
            return _result(request.reservation.attempt_id, "partial", [_finding("ATTEMPT_COMPLETION_PARTIAL", "partial", request)], invoked=True, delegated=True)
        return _result(request.reservation.attempt_id, "completed", [], invoked=True, delegated=True, completed=True)

    @staticmethod
    def _preflight(request: NormalExecutionCompositionInput) -> list[NormalExecutionCompositionFindingDTO]:
        authorization = request.workflow_application_authorization
        reservation = request.reservation
        structured = request.structured_request_validation_report
        capability = request.capability_negotiation_report
        readiness = request.pre_execution_readiness_report
        execution = request.execution_authorization_validation_report
        if any(report.ready is not True for report in (structured, capability, readiness, execution)):
            return [_finding("UPSTREAM_VALIDATED_REPORT_NOT_READY", "blocked", request)]
        source_request = structured.request
        if (
            readiness.input.request_validation_report != structured
            or readiness.input.capability_negotiation_report != capability
            or readiness.input.provider_reference != reservation.provider_reference
            or execution.readiness_report != readiness
            or source_request.request_id != reservation.request_id
            or source_request.target_page_reference != reservation.target_page_reference
            or source_request.capability_requirements != capability.requirements
            or source_request.capability_requirements != structured.profile.capability_requirements
        ):
            return [_finding("REQUEST_CAPABILITY_READINESS_AUTHORIZATION_MISMATCH", "blocked", request)]
        if (
            authorization.attempt_id != reservation.attempt_id
            or authorization.provider_reference != reservation.provider_reference
            or authorization.project_id != reservation.project_id
            or authorization.page_id != reservation.page_id
            or authorization.target_page_reference != reservation.target_page_reference
        ):
            return [_finding("WORKFLOW_AUTHORIZATION_BINDING_MISMATCH", "blocked", request)]
        mapping = request.page_mapping
        if (
            mapping.project_id != reservation.project_id
            or mapping.page_id != reservation.page_id
            or mapping.target_page_reference != reservation.target_page_reference
        ):
            return [_finding("AUTHORITATIVE_PAGE_MAPPING_MISMATCH", "blocked", request)]
        envelope = _ready_envelope(request)
        if envelope is None:
            return [_finding("AUTHORIZED_ENVELOPE_PREFLIGHT_INVALID", "blocked", request)]
        envelope_values = cast(Any, envelope)
        if (
            envelope_values.request_id != reservation.request_id
            or envelope_values.provider_reference != reservation.provider_reference
            or len(envelope_values.authorization_ids) != len(set(envelope_values.authorization_ids))
            or tuple(sorted(envelope_values.authorization_ids)) != tuple(sorted(record.authorization_id for record in execution.authorizations))
            or envelope_values.profile_id != source_request.profile_id
            or envelope_values.profile_version != source_request.profile_version
            or envelope_values.generation_intent_reference != source_request.generation_intent_reference
            or envelope_values.input_reference != source_request.input.input_reference
        ):
            return [_finding("AUTHORIZED_ENVELOPE_BINDING_MISMATCH", "blocked", request)]
        configuration = request.provider_configuration_report.selection
        if (
            request.provider_configuration_report.ready is not True
            or configuration is None
            or any(
                getattr(configuration, name, None) != getattr(envelope, name, None)
                for name in ("attempt_id", "provider_reference", "profile_id", "profile_version")
            )
        ):
            return [_finding("PROVIDER_CONFIGURATION_PREFLIGHT_INVALID", "blocked", request)]
        output_report = request.provider_output_configuration_report
        output = getattr(output_report, "output_configuration", None)
        selected_model = getattr(getattr(configuration, "model_id", None), "value", None)
        if (
            output_report is None
            or getattr(output_report, "ready", False) is not True
            or output is None
            or any(getattr(output, name, None) != getattr(envelope, name, None) for name in ("attempt_id", "provider_reference", "profile_id", "profile_version"))
            or getattr(output, "model_id", None) != selected_model
        ):
            return [_finding("OUTPUT_CONFIGURATION_PREFLIGHT_INVALID", "blocked", request)]
        context = _load_context(request)
        if context is None or getattr(getattr(context, "state", None), "value", None) != "PromptBuilt":
            return [_finding("AUTHORITATIVE_PROMPT_BUILT_REQUIRED", "blocked", request)]
        if request.observed_at.tzinfo is None or request.observed_at.utcoffset() is None:
            return [_finding("OBSERVED_AT_INVALID", "blocked", request)]
        try:
            derive_execution_fingerprint(_fingerprint_projection(request, envelope, configuration, output))
        except (TypeError, ValueError):
            return [_finding("EXECUTION_FINGERPRINT_PROJECTION_INVALID", "blocked", request)]
        return []


def _ready_envelope(request: NormalExecutionCompositionInput) -> object | None:
    report = request.authorized_execution_envelope_validation_report
    matches = tuple(envelope for envelope in getattr(report, "envelopes", ()) if getattr(envelope, "attempt_id", None) == request.reservation.attempt_id)
    if getattr(report, "ready", False) is not True or len(matches) != 1:
        return None
    return cast(object, matches[0])


def _fingerprint_projection(request: NormalExecutionCompositionInput, envelope: object, configuration: object, output: object | None) -> dict[str, object]:
    reservation = request.reservation
    return {
        "attempt_id": reservation.attempt_id,
        "request_id": reservation.request_id,
        "project_id": reservation.project_id,
        "page_id": reservation.page_id,
        "target_page_reference": reservation.target_page_reference,
        "provider_reference": reservation.provider_reference,
        "profile_id": getattr(envelope, "profile_id", ""),
        "profile_version": getattr(envelope, "profile_version", ""),
        "generation_intent_reference": getattr(envelope, "generation_intent_reference", ""),
        "input_reference": getattr(envelope, "input_reference", ""),
        "provenance_reference": request.structured_request_validation_report.request.provenance_reference,
        "identity_bindings": tuple(sorted((binding.character_id, binding.identity_id, binding.identity_version, tuple(sorted(binding.reference_asset_ids))) for binding in request.structured_request_validation_report.request.identity_bindings)),
        "capability_requirements": tuple(sorted((item.capability_id, item.requirement_level) for item in request.capability_negotiation_report.requirements)),
        "execution_authorization_ids": tuple(sorted(record.authorization_id for record in request.execution_authorization_validation_report.authorizations)),
        "workflow_application_authorization_id": request.workflow_application_authorization.authorization_id,
        "provider_configuration": _safe_model_projection(configuration),
        "output_configuration": _safe_model_projection(output),
        "observed_at": request.observed_at.isoformat(),
    }


def _derived_reservation(request: NormalExecutionCompositionInput) -> NormalExecutionAttemptReservationDTO:
    envelope = _ready_envelope(request)
    configuration = request.provider_configuration_report.selection
    output = getattr(request.provider_output_configuration_report, "output_configuration", None)
    if envelope is None or configuration is None:
        raise RuntimeError("validated execution inputs are unavailable")
    return request.reservation.model_copy(update={"execution_fingerprint": derive_execution_fingerprint(_fingerprint_projection(request, envelope, configuration, output))})


def _safe_model_projection(value: object | None) -> object:
    if value is None:
        return None
    dumped: dict[str, object] = getattr(value, "model_dump", lambda: {})()
    return {key: dumped[key] for key in sorted(dumped) if key not in {"requested_seed"}}


def _load_context(request: NormalExecutionCompositionInput) -> object | None:
    try:
        return request.workflow_context_loader.load(request.reservation.project_id, request.reservation.page_id)
    except Exception:
        return None


def _provider_declared_failure(report: object) -> bool:
    return any(getattr(finding, "code", "") == "PROVIDER_DECLARED_FAILURE" for finding in getattr(report, "findings", ()))


def _finding(code: str, status: Literal["blocked", "partial"], request: NormalExecutionCompositionInput) -> NormalExecutionCompositionFindingDTO:
    reservation = request.reservation
    return NormalExecutionCompositionFindingDTO(code=code, status=status, message="normal execution did not advance", attempt_id=reservation.attempt_id, project_id=reservation.project_id, page_id=reservation.page_id)


def _result(attempt_id: str, status: Literal["completed", "partial", "blocked"], findings: list[NormalExecutionCompositionFindingDTO], *, invoked: bool = False, delegated: bool = False, completed: bool = False) -> NormalExecutionCompositionReport:
    return NormalExecutionCompositionReport(attempt_id=attempt_id, findings=tuple(sorted(findings, key=lambda finding: (finding.code, finding.attempt_id))), status=status, provider_invocation_performed=invoked, external_application_delegated=delegated, completed=completed)
