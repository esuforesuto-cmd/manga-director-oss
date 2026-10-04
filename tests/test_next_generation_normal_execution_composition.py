from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from manga_director.production.next_generation_authorized_execution_envelope import (
    AuthorizedGenerationExecutionEnvelopeDTO,
    AuthorizedGenerationExecutionEnvelopeValidationService,
)
from manga_director.production.next_generation_durable_evidence_workflow_binding import (
    AuthoritativeWorkflowPageMappingDTO,
    WorkflowApplicationAuthorizationDTO,
)
from manga_director.production.next_generation_execution_authorization import (
    ExecutionAuthorizationRecordDTO,
    ExecutionAuthorizationValidationService,
)
from manga_director.production.next_generation_generation_evidence import (
    EvidenceValueDTO,
    GenerationIdentityBindingDTO,
    GenerationInputEvidenceDTO,
)
from manga_director.production.next_generation_normal_execution_attempt import (
    NormalExecutionAttemptReservationDTO,
)
from manga_director.production.next_generation_normal_execution_composition import (
    NormalExecutionCompositionInput,
    NormalExecutionCompositionService,
    _derived_reservation,
    _fingerprint_projection,
)
from manga_director.production.next_generation_pre_execution_readiness import (
    PreExecutionReadinessInputDTO,
    PreExecutionReadinessService,
)
from manga_director.production.next_generation_provider_capability_negotiation import (
    GenerationCapabilityRequirementDTO,
    ProviderCapabilityDeclarationDTO,
    ProviderCapabilityNegotiationService,
    ProviderCapabilityStateDTO,
)
from manga_director.production.next_generation_provider_configuration import (
    AuthoritativeProviderConfigurationSnapshot,
    ProviderConfigurationNormalizationService,
)
from manga_director.production.next_generation_provider_output_configuration import (
    ProviderOutputConfigurationBindingDTO,
    ProviderOutputConfigurationBindingService,
)
from manga_director.production.next_generation_structured_generation_request import (
    GenerationProductionProfileDTO,
    StructuredGenerationRequestDTO,
    StructuredGenerationRequestValidationService,
)


class _ContextLoader:
    def load(self, project_id: str, page_id: str):
        return None


class _Unused:
    def apply(self, binding_report, authorization):
        raise AssertionError("external application must not run before PromptBuilt")


class _NoReservationStore:
    calls = 0

    def reserve(self, reservation):
        self.calls += 1
        raise AssertionError("preflight must prevent reservation")


def _ready_request(case: str = "") -> NormalExecutionCompositionInput:  # noqa: C901
    reservation = NormalExecutionAttemptReservationDTO(
        attempt_id="attempt-1", request_id="request-1", project_id="project-1", page_id="page-1",
        target_page_reference="target-1", provider_reference="provider-1", execution_fingerprint="f" * 64,
    )
    requirements = (SimpleNamespace(capability_id="text_prompt", requirement_level="required"),)
    source = SimpleNamespace(request_id="request-1", target_page_reference="target-1", profile_id="profile-1", profile_version="v1", generation_intent_reference="intent-1", input=SimpleNamespace(input_reference="input-1"), provenance_reference="prov-1", identity_bindings=(), capability_requirements=requirements)
    structured = SimpleNamespace(ready=True, request=source, profile=SimpleNamespace(profile_id="profile-1", profile_version="v1", capability_requirements=requirements))
    capability = SimpleNamespace(ready=True, requirements=requirements, declaration=SimpleNamespace(provider_reference="provider-1"))
    readiness = SimpleNamespace(ready=True, input=SimpleNamespace(request_validation_report=structured, capability_negotiation_report=capability, provider_reference="provider-1"))
    execution = SimpleNamespace(ready=True, readiness_report=readiness, authorizations=(SimpleNamespace(authorization_id="exec-auth-1"),))
    envelope = SimpleNamespace(attempt_id="attempt-1", request_id="request-1", provider_reference="provider-1", authorization_ids=("exec-auth-1",), profile_id="profile-1", profile_version="v1", generation_intent_reference="intent-1", input_reference="input-1")
    envelope_report = SimpleNamespace(ready=True, envelopes=(envelope,), execution_authorization_validation_report=execution)
    configuration = SimpleNamespace(attempt_id="attempt-1", provider_reference="provider-1", profile_id="profile-1", profile_version="v1", model_id=SimpleNamespace(availability="known", value="model-1"))
    configuration_report = SimpleNamespace(ready=True, selection=configuration)
    output_configuration = SimpleNamespace(attempt_id="attempt-1", provider_reference="provider-1", profile_id="profile-1", profile_version="v1", model_id="model-1")
    output_report = SimpleNamespace(ready=True, output_configuration=output_configuration)
    auth = WorkflowApplicationAuthorizationDTO(authorization_id="workflow-auth-1", authorizer_id="human-1", authorized_at=datetime.now(UTC), attempt_id="attempt-1", provider_reference="provider-1", project_id="project-1", page_id="page-1", target_page_reference="target-1", source_state="PromptBuilt", target_state="Generated")
    mapping = AuthoritativeWorkflowPageMappingDTO(project_id="project-1", page_id="page-1", target_page_reference="target-1")
    values = dict(reservation=reservation, structured_request_validation_report=structured, capability_negotiation_report=capability, pre_execution_readiness_report=readiness, execution_authorization_validation_report=execution, authorized_execution_envelope_validation_report=envelope_report, workflow_application_authorization=auth, page_mapping=mapping, workflow_context_loader=SimpleNamespace(load=lambda *_: SimpleNamespace(state=SimpleNamespace(value="PromptBuilt"))), generation_input_resolver=_Unused(), reference_asset_resolver=_Unused(), provider_invocation_port=_Unused(), asset_registration_port=_Unused(), evidence_store=_Unused(), external_application_coordinator=_Unused(), observed_at=datetime.now(UTC), provider_configuration_report=configuration_report, provider_output_configuration_report=output_report)
    if case == "structured":
        structured.ready = False
    elif case == "capability":
        capability.ready = False
    elif case == "readiness":
        readiness.ready = False
    elif case == "authorization":
        execution.ready = False
    elif case == "envelope":
        envelope.request_id = "wrong"
    elif case == "mapping":
        values["page_mapping"] = AuthoritativeWorkflowPageMappingDTO(project_id="project-1", page_id="page-2", target_page_reference="target-1")
    elif case == "project":
        values["workflow_application_authorization"] = auth.model_copy(update={"project_id": "project-2"})
    elif case == "target":
        values["workflow_application_authorization"] = auth.model_copy(update={"target_page_reference": "target-2"})
    elif case == "prompt":
        values["workflow_context_loader"] = SimpleNamespace(load=lambda *_: SimpleNamespace(state=SimpleNamespace(value="Generated")))
    elif case == "provider":
        configuration.provider_reference = "wrong"
    elif case == "model":
        configuration.model_id = SimpleNamespace(availability="known", value="model-2")
    elif case == "output":
        values["provider_output_configuration_report"] = SimpleNamespace(ready=False, output_configuration=None)
    elif case == "output_attempt":
        output_configuration.attempt_id = "attempt-2"
    elif case == "output_provider":
        output_configuration.provider_reference = "provider-2"
    elif case == "output_profile_id":
        output_configuration.profile_id = "profile-2"
    elif case == "output_profile_version":
        output_configuration.profile_version = "v2"
    elif case == "workflow":
        values["workflow_application_authorization"] = auth.model_copy(update={"page_id": "page-2"})
    return NormalExecutionCompositionInput(**values)


@pytest.mark.parametrize("case", ("structured", "capability", "readiness", "authorization", "envelope", "mapping", "project", "target", "prompt", "provider", "model", "output", "output_attempt", "output_provider", "output_profile_id", "output_profile_version", "workflow"))
def test_every_preflight_failure_performs_zero_reservation_or_runtime_work(case: str) -> None:
    store = _NoReservationStore()
    result = NormalExecutionCompositionService().execute(_ready_request(case), store)

    assert result.status == "blocked"
    assert store.calls == 0
    assert result.provider_invocation_performed is False
    assert result.external_application_delegated is False


def test_composition_owns_fingerprint_instead_of_caller_reservation_digest() -> None:
    first = _ready_request()
    second = replace(
        first,
        reservation=first.reservation.model_copy(update={"execution_fingerprint": "0" * 64}),
    )

    assert _derived_reservation(first).execution_fingerprint == _derived_reservation(second).execution_fingerprint
    assert _derived_reservation(first).execution_fingerprint != first.reservation.execution_fingerprint


@pytest.mark.parametrize("field", ("attempt_id", "request_id", "project_id", "page_id", "target_page_reference", "provider_reference"))
def test_material_reservation_identity_changes_fingerprint(field: str) -> None:
    baseline = _derived_reservation(_ready_request()).execution_fingerprint
    request = _ready_request()
    changed = request.reservation.model_copy(update={field: f"changed-{field}"})
    if field == "attempt_id":
        request.authorized_execution_envelope_validation_report.envelopes[0].attempt_id = changed.attempt_id
    changed_request = replace(request, reservation=changed)

    assert _derived_reservation(changed_request).execution_fingerprint != baseline


def test_fingerprint_projection_is_logical_and_has_no_runtime_material() -> None:
    request = _ready_request()
    projection = _fingerprint_projection(
        request,
        request.authorized_execution_envelope_validation_report.envelopes[0],
        request.provider_configuration_report.selection,
        request.provider_output_configuration_report.output_configuration,
    )
    rendered = repr(projection).lower()

    assert all(token not in rendered for token in ("raw_prompt", "credential", "secret", "base64", "path", "header", "response"))


def test_composition_fails_closed_before_resolution_when_prompt_built_is_unavailable() -> None:
    reservation = NormalExecutionAttemptReservationDTO(
        attempt_id="attempt-1", request_id="request-1", project_id="project-1", page_id="page-1",
        target_page_reference="target-1", provider_reference="provider-1", execution_fingerprint="a" * 64,
    )
    authorization = WorkflowApplicationAuthorizationDTO(
        authorization_id="auth-1", authorizer_id="human-1", authorized_at=datetime.now(UTC),
        attempt_id="attempt-1", provider_reference="provider-1", project_id="project-1", page_id="page-1",
        target_page_reference="target-1", source_state="PromptBuilt", target_state="Generated",
    )
    mapping = AuthoritativeWorkflowPageMappingDTO(project_id="project-1", page_id="page-1", target_page_reference="target-1")
    request = NormalExecutionCompositionInput(
        reservation=reservation, authorized_execution_envelope_validation_report=object(),
        structured_request_validation_report=SimpleNamespace(ready=False),
        capability_negotiation_report=SimpleNamespace(ready=False),
        pre_execution_readiness_report=SimpleNamespace(ready=False),
        execution_authorization_validation_report=SimpleNamespace(ready=False),
        workflow_application_authorization=authorization, page_mapping=mapping, workflow_context_loader=_ContextLoader(),
        generation_input_resolver=object(), reference_asset_resolver=object(), provider_invocation_port=object(),
        asset_registration_port=object(), evidence_store=object(), external_application_coordinator=_Unused(), observed_at=datetime.now(UTC),
        provider_configuration_report=SimpleNamespace(ready=False, selection=None),
        provider_output_configuration_report=SimpleNamespace(ready=False, output_configuration=None),
    )

    report = NormalExecutionCompositionService()._preflight(request)

    assert report[0].code == "UPSTREAM_VALIDATED_REPORT_NOT_READY"


_SOURCE_REQUIREMENTS = (
    GenerationCapabilityRequirementDTO(capability_id="dimensions", requirement_level="required"),
    GenerationCapabilityRequirementDTO(capability_id="text_prompt", requirement_level="required"),
)
_SOURCE_IDENTITIES = (
    GenerationIdentityBindingDTO(
        character_id="character:aki",
        identity_id="identity:aki",
        identity_version="v1",
        reference_asset_ids=("asset:aki:front", "asset:aki:side"),
    ),
    GenerationIdentityBindingDTO(
        character_id="character:ren",
        identity_id="identity:ren",
        identity_version="v1",
        reference_asset_ids=("asset:ren:front",),
    ),
)


def _known(value: str) -> EvidenceValueDTO:
    return EvidenceValueDTO(availability="known", value=value)


def _source_backed_request(  # noqa: PLR0913 - frozen fingerprint matrix names each material binding.
    *,
    attempt_id: str = "attempt:source",
    request_id: str = "request:source",
    project_id: str = "project:source",
    page_id: str = "page:source",
    target_page_reference: str = "target:source",
    provider_reference: str = "provider:source",
    profile_id: str = "profile:source",
    profile_version: str = "v1",
    generation_intent_reference: str = "intent:source",
    input_reference: str = "input:source",
    provenance_reference: str = "provenance:source",
    identity_bindings: tuple[GenerationIdentityBindingDTO, ...] = _SOURCE_IDENTITIES,
    requirements: tuple[GenerationCapabilityRequirementDTO, ...] = _SOURCE_REQUIREMENTS,
    execution_authorization_ids: tuple[str, ...] = ("authorization:alpha", "authorization:beta"),
    workflow_authorization_id: str = "workflow-authorization:source",
    configuration_workflow_id: str = "workflow:source",
    model_version: str = "model-version:source",
    output_size: str = "1536x1024",
    output_quality: str = "low",
    observed_at: datetime = datetime(2026, 8, 23, 12, 0, tzinfo=UTC),
) -> NormalExecutionCompositionInput:
    """Build a complete valid chain with the real frozen DTO/report services."""

    profile = GenerationProductionProfileDTO(
        profile_id=profile_id,
        profile_version=profile_version,
        capability_requirements=requirements,
    )
    structured_request = StructuredGenerationRequestDTO(
        request_id=request_id,
        target_page_reference=target_page_reference,
        generation_intent_reference=generation_intent_reference,
        input=GenerationInputEvidenceDTO(input_reference=input_reference),
        capability_requirements=requirements,
        provenance_reference=provenance_reference,
        profile_id=profile_id,
        profile_version=profile_version,
        identity_bindings=identity_bindings,
    )
    structured = StructuredGenerationRequestValidationService().validate(structured_request, profile)
    capability = ProviderCapabilityNegotiationService().validate(
        requirements,
        ProviderCapabilityDeclarationDTO(
            provider_reference=provider_reference,
            capability_states=tuple(
                ProviderCapabilityStateDTO(capability_id=item.capability_id, state="supported")
                for item in requirements
            ),
        ),
    )
    readiness = PreExecutionReadinessService().validate(
        PreExecutionReadinessInputDTO(
            request_validation_report=structured,
            capability_negotiation_report=capability,
            provider_reference=provider_reference,
        )
    )
    execution = ExecutionAuthorizationValidationService().validate(
        readiness,
        tuple(
            ExecutionAuthorizationRecordDTO(
                authorization_id=authorization_id,
                authorizer_id=f"human:{index}",
                authorized_at=datetime(2026, 8, 23, 11, index, tzinfo=UTC),
                request_id=request_id,
                provider_reference=provider_reference,
            )
            for index, authorization_id in enumerate(execution_authorization_ids, start=1)
        ),
    )
    envelope = AuthorizedGenerationExecutionEnvelopeDTO(
        attempt_id=attempt_id,
        request_id=request_id,
        provider_reference=provider_reference,
        authorization_ids=execution_authorization_ids,
        profile_id=profile_id,
        profile_version=profile_version,
        generation_intent_reference=generation_intent_reference,
        input_reference=input_reference,
    )
    authorized_envelope = AuthorizedGenerationExecutionEnvelopeValidationService().validate(
        (envelope,), execution
    )
    configuration = ProviderConfigurationNormalizationService().normalize(
        attempt_id,
        AuthoritativeProviderConfigurationSnapshot(
            attempt_id=attempt_id,
            provider_reference=provider_reference,
            profile_id=profile_id,
            profile_version=profile_version,
            provider_id=_known("openai"),
            model_id=_known("gpt-image-2-2026-04-21"),
            model_version=_known(model_version),
            workflow_id=_known(configuration_workflow_id),
            workflow_version=_known("workflow-version:source"),
        ),
        authorized_envelope,
    )
    output = ProviderOutputConfigurationBindingService().validate(
        ProviderOutputConfigurationBindingDTO(
            attempt_id=attempt_id,
            provider_reference=provider_reference,
            profile_id=profile_id,
            profile_version=profile_version,
            model_id="gpt-image-2-2026-04-21",
            output_size=output_size,
            output_quality=output_quality,
        ),
        configuration,
    )
    reservation = NormalExecutionAttemptReservationDTO(
        attempt_id=attempt_id,
        request_id=request_id,
        project_id=project_id,
        page_id=page_id,
        target_page_reference=target_page_reference,
        provider_reference=provider_reference,
        execution_fingerprint="f" * 64,
    )
    authorization = WorkflowApplicationAuthorizationDTO(
        authorization_id=workflow_authorization_id,
        authorizer_id="human:workflow",
        authorized_at=datetime(2026, 8, 23, 11, 30, tzinfo=UTC),
        attempt_id=attempt_id,
        provider_reference=provider_reference,
        project_id=project_id,
        page_id=page_id,
        target_page_reference=target_page_reference,
        source_state="PromptBuilt",
        target_state="Generated",
    )
    return NormalExecutionCompositionInput(
        reservation=reservation,
        structured_request_validation_report=structured,
        capability_negotiation_report=capability,
        pre_execution_readiness_report=readiness,
        execution_authorization_validation_report=execution,
        authorized_execution_envelope_validation_report=authorized_envelope,
        workflow_application_authorization=authorization,
        page_mapping=AuthoritativeWorkflowPageMappingDTO(
            project_id=project_id,
            page_id=page_id,
            target_page_reference=target_page_reference,
        ),
        workflow_context_loader=SimpleNamespace(
            load=lambda *_: SimpleNamespace(state=SimpleNamespace(value="PromptBuilt"))
        ),
        generation_input_resolver=_Unused(),
        reference_asset_resolver=_Unused(),
        provider_invocation_port=_Unused(),
        asset_registration_port=_Unused(),
        evidence_store=_Unused(),
        external_application_coordinator=_Unused(),
        observed_at=observed_at,
        provider_configuration_report=configuration,
        provider_output_configuration_report=output,
    )


def _source_backed_fingerprint(request: NormalExecutionCompositionInput) -> str:
    """Reach the production derivation seam only through a complete valid chain."""

    assert NormalExecutionCompositionService()._preflight(request) == []
    return _derived_reservation(request).execution_fingerprint


@pytest.mark.parametrize(
    ("name", "changed"),
    (
        ("attempt_id", lambda: _source_backed_request(attempt_id="attempt:changed")),
        ("request_id", lambda: _source_backed_request(request_id="request:changed")),
        ("project_id", lambda: _source_backed_request(project_id="project:changed")),
        ("page_id", lambda: _source_backed_request(page_id="page:changed")),
        (
            "target_page_reference",
            lambda: _source_backed_request(target_page_reference="target:changed"),
        ),
        (
            "provider_reference",
            lambda: _source_backed_request(provider_reference="provider:changed"),
        ),
        ("profile_id", lambda: _source_backed_request(profile_id="profile:changed")),
        ("profile_version", lambda: _source_backed_request(profile_version="v2")),
        (
            "generation_intent_reference",
            lambda: _source_backed_request(generation_intent_reference="intent:changed"),
        ),
        ("input_reference", lambda: _source_backed_request(input_reference="input:changed")),
        (
            "provenance_reference",
            lambda: _source_backed_request(provenance_reference="provenance:changed"),
        ),
        (
            "identity_bindings",
            lambda: _source_backed_request(
                identity_bindings=(
                    GenerationIdentityBindingDTO(
                        character_id="character:aki",
                        identity_id="identity:aki",
                        identity_version="v2",
                        reference_asset_ids=("asset:aki:front", "asset:aki:side"),
                    ),
                    _SOURCE_IDENTITIES[1],
                )
            ),
        ),
        (
            "capability_requirements",
            lambda: _source_backed_request(
                requirements=(
                    GenerationCapabilityRequirementDTO(
                        capability_id="output_format", requirement_level="required"
                    ),
                    _SOURCE_REQUIREMENTS[1],
                )
            ),
        ),
        (
            "execution_authorization_ids",
            lambda: _source_backed_request(
                execution_authorization_ids=("authorization:alpha", "authorization:gamma")
            ),
        ),
        (
            "workflow_application_authorization_id",
            lambda: _source_backed_request(
                workflow_authorization_id="workflow-authorization:changed"
            ),
        ),
        (
            "provider_configuration",
            lambda: _source_backed_request(configuration_workflow_id="workflow:changed"),
        ),
        # The output contract freezes the supported model ID to one exact OpenAI
        # snapshot.  model_version is the smallest independently mutable, valid
        # normalized model-configuration fact; a changed model ID would correctly
        # be rejected by the output-contract validation before this seam.
        (
            "model_configuration",
            lambda: _source_backed_request(model_version="model-version:changed"),
        ),
        (
            "output_configuration",
            lambda: _source_backed_request(output_quality="medium"),
        ),
        (
            "observed_at",
            lambda: _source_backed_request(
                observed_at=datetime(2026, 8, 23, 12, 1, tzinfo=UTC)
            ),
        ),
    ),
    ids=lambda item: item if isinstance(item, str) else None,
)
def test_source_backed_material_fingerprint_bindings_change_digest(name: str, changed) -> None:
    baseline = _source_backed_fingerprint(_source_backed_request())

    assert _source_backed_fingerprint(changed()) != baseline, name


@pytest.mark.parametrize(
    "equivalent",
    (
        lambda: _source_backed_request(identity_bindings=tuple(reversed(_SOURCE_IDENTITIES))),
        lambda: _source_backed_request(
            identity_bindings=(
                _SOURCE_IDENTITIES[0].model_copy(
                    update={"reference_asset_ids": ("asset:aki:side", "asset:aki:front")}
                ),
                _SOURCE_IDENTITIES[1],
            )
        ),
        lambda: _source_backed_request(requirements=tuple(reversed(_SOURCE_REQUIREMENTS))),
        lambda: _source_backed_request(
            execution_authorization_ids=("authorization:beta", "authorization:alpha")
        ),
    ),
    ids=(
        "identity_bindings",
        "reference_asset_ids",
        "capability_requirements",
        "execution_authorization_ids",
    ),
)
def test_source_backed_unordered_fingerprint_projections_are_canonical(equivalent) -> None:
    assert _source_backed_fingerprint(equivalent()) == _source_backed_fingerprint(
        _source_backed_request()
    )


def test_source_backed_fingerprint_is_reproducible_across_distinct_report_objects() -> None:
    assert _source_backed_fingerprint(_source_backed_request()) == _source_backed_fingerprint(
        _source_backed_request()
    )
