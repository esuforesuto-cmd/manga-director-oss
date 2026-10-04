"""Focused contracts for internal provider configuration normalization."""

from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError, asdict
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from manga_director.production.next_generation_authorized_execution_envelope import (
    AuthorizedGenerationExecutionEnvelopeDTO,
    AuthorizedGenerationExecutionEnvelopeValidationService,
)
from manga_director.production.next_generation_execution_authorization import (
    ExecutionAuthorizationRecordDTO,
    ExecutionAuthorizationValidationService,
)
from manga_director.production.next_generation_generation_evidence import (
    EvidenceValueDTO,
    GenerationInputEvidenceDTO,
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
    ProviderConfigurationNormalizationFindingDTO,
    ProviderConfigurationNormalizationService,
    ProviderConfigurationSelectionDTO,
)
from manga_director.production.next_generation_provider_invocation import (
    ProviderGenerationInvocationPort,
)
from manga_director.production.next_generation_structured_generation_request import (
    GenerationProductionProfileDTO,
    StructuredGenerationRequestDTO,
    StructuredGenerationRequestValidationService,
)


def _authorized_report():
    requirements = (
        GenerationCapabilityRequirementDTO(capability_id="text_prompt", requirement_level="required"),
    )
    profile = GenerationProductionProfileDTO(
        profile_id="profile:manga", profile_version="v1", capability_requirements=requirements
    )
    request = StructuredGenerationRequestDTO(
        request_id="request:001",
        target_page_reference="page:001",
        generation_intent_reference="intent:001",
        input=GenerationInputEvidenceDTO(input_reference="input:001"),
        capability_requirements=requirements,
        provenance_reference="provenance:001",
        profile_id="profile:manga",
        profile_version="v1",
    )
    request_report = StructuredGenerationRequestValidationService().validate(request, profile)
    negotiation = ProviderCapabilityNegotiationService().validate(
        requirements,
        ProviderCapabilityDeclarationDTO(
            provider_reference="provider:local-a",
            capability_states=(
                ProviderCapabilityStateDTO(capability_id="text_prompt", state="supported"),
            ),
        ),
    )
    readiness = PreExecutionReadinessService().validate(
        PreExecutionReadinessInputDTO(
            request_validation_report=request_report,
            capability_negotiation_report=negotiation,
            provider_reference="provider:local-a",
        )
    )
    authorization = ExecutionAuthorizationValidationService().validate(
        readiness,
        (
            ExecutionAuthorizationRecordDTO(
                authorization_id="authorization:001",
                authorizer_id="human:editor-a",
                authorized_at=datetime(2026, 8, 22, 12, 0, tzinfo=UTC),
                request_id="request:001",
                provider_reference="provider:local-a",
            ),
        ),
    )
    return AuthorizedGenerationExecutionEnvelopeValidationService().validate(
        (
            AuthorizedGenerationExecutionEnvelopeDTO(
                attempt_id="attempt:001",
                request_id="request:001",
                provider_reference="provider:local-a",
                authorization_ids=("authorization:001",),
                profile_id="profile:manga",
                profile_version="v1",
                generation_intent_reference="intent:001",
                input_reference="input:001",
            ),
        ),
        authorization,
    )


def _value(availability: str = "known", value: object = "selected:001") -> EvidenceValueDTO:
    return EvidenceValueDTO(
        availability=availability,  # type: ignore[arg-type]
        value=value if availability == "known" else None,
    )


def _snapshot(**updates: object) -> AuthoritativeProviderConfigurationSnapshot:
    values: dict[str, object] = {
        "attempt_id": "attempt:001",
        "provider_reference": "provider:local-a",
        "profile_id": "profile:manga",
        "profile_version": "v1",
        "provider_id": _value(value="openai"),
        "model_id": _value(value="gpt-image"),
        "model_version": _value(value="v1"),
        "workflow_id": _value(availability="unavailable"),
        "workflow_version": _value(availability="unavailable"),
        "requested_seed": _value(value=1234),
    }
    values.update(updates)
    return AuthoritativeProviderConfigurationSnapshot(**values)  # type: ignore[arg-type]


def test_valid_configuration_is_exact_bound_and_preserves_requested_seed() -> None:
    upstream = _authorized_report()
    snapshot = _snapshot()

    report = ProviderConfigurationNormalizationService().normalize(
        "attempt:001", snapshot, upstream
    )

    assert report.status == "ready"
    assert report.ready is True
    assert report.selection is not None
    assert report.selection.requested_seed == _value(value=1234)
    assert not hasattr(report.selection, "effective_seed")


@pytest.mark.parametrize("availability", ("known", "unknown", "unavailable"))
def test_provider_id_factual_states_are_accepted(availability: str) -> None:
    snapshot = _snapshot(provider_id=_value(availability, "openai"))

    report = ProviderConfigurationNormalizationService().normalize(
        "attempt:001", snapshot, _authorized_report()
    )

    assert report.ready is True
    assert report.selection is not None
    assert report.selection.provider_id.availability == availability


def test_model_workflow_and_optional_preset_evidence_are_factual() -> None:
    snapshot = _snapshot(
        model_id=_value("unknown"),
        model_version=_value("unavailable"),
        workflow_id=_value(value="workflow:manga"),
        workflow_version=_value(value="v2"),
        preset_id=_value(value="preset:ink"),
        preset_version=_value(value="v3"),
    )

    report = ProviderConfigurationNormalizationService().normalize(
        "attempt:001", snapshot, _authorized_report()

    )

    assert report.ready is True
    assert report.selection is not None
    assert report.selection.workflow_id.value == "workflow:manga"
    assert report.selection.preset_id is not None
    assert report.selection.preset_id.value == "preset:ink"


@pytest.mark.parametrize(
    ("updates", "code"),
    (
        ({"attempt_id": "attempt:other"}, "ATTEMPT_BINDING_MISMATCH"),
        ({"provider_reference": "provider:other"}, "PROVIDER_REFERENCE_MISMATCH"),
        ({"profile_id": "profile:other"}, "PROFILE_ID_MISMATCH"),
        ({"profile_version": "v2"}, "PROFILE_VERSION_MISMATCH"),
    ),
)
def test_exact_bindings_fail_closed(updates: dict[str, object], code: str) -> None:
    report = ProviderConfigurationNormalizationService().normalize(
        "attempt:001", _snapshot(**updates), _authorized_report()
    )

    assert report.status == "blocked"
    assert report.selection is None
    assert code in {finding.code for finding in report.findings}


def test_unready_missing_and_duplicate_authorized_attempts_fail_closed() -> None:
    upstream = _authorized_report()
    service = ProviderConfigurationNormalizationService()
    unready = upstream.model_copy(update={"status": "needs_review", "ready": False})
    missing = upstream.model_copy(update={"envelopes": ()})
    duplicate = upstream.model_copy(update={"envelopes": upstream.envelopes * 2})

    assert service.normalize("attempt:001", _snapshot(), unready).findings[0].code == (
        "AUTHORIZED_ENVELOPE_NOT_READY"
    )
    assert service.normalize("attempt:001", _snapshot(), missing).findings[0].code == (
        "AUTHORIZED_ATTEMPT_NOT_FOUND"
    )
    assert service.normalize("attempt:001", _snapshot(), duplicate).findings[0].code == (
        "AUTHORIZED_ATTEMPT_NOT_UNIQUE"
    )


def test_dtos_reject_extra_unsafe_identity_and_effective_seed() -> None:
    with pytest.raises(ValidationError):
        ProviderConfigurationSelectionDTO(
            **asdict(_snapshot()),
            effective_seed=_value(value=1234),
        )
    with pytest.raises(ValidationError):
        ProviderConfigurationSelectionDTO(
            attempt_id="attempt:001",
            provider_reference="provider:local-a",
            profile_id="profile:manga",
            profile_version="v1",
            provider_id=_value(value="openai"),
            model_id=_value(value="C:/private/model"),
            model_version=_value(value="v1"),
            workflow_id=_value("unavailable"),
            workflow_version=_value("unavailable"),
        )
    with pytest.raises(TypeError):
        AuthoritativeProviderConfigurationSnapshot(
            **{
                "attempt_id": "attempt:001",
                "provider_reference": "provider:local-a",
                "profile_id": "profile:manga",
                "profile_version": "v1",
                "provider_id": _value(),
                "model_id": _value(),
                "model_version": _value(),
                "workflow_id": _value(),
                "workflow_version": _value(),
                "effective_seed": _value(value=1),
            }
        )


def test_snapshot_is_frozen_and_service_rejects_unsafe_snapshot() -> None:
    snapshot = _snapshot()
    with pytest.raises(FrozenInstanceError):
        snapshot.provider_reference = "provider:other"  # type: ignore[misc]

    unsafe = _snapshot(model_id=_value(value="https://private.example/model"))
    report = ProviderConfigurationNormalizationService().normalize(
        "attempt:001", unsafe, _authorized_report()
    )

    assert report.status == "blocked"
    assert report.findings[0].code == "UNSAFE_CONFIGURATION_EVIDENCE"


def test_repeatability_non_mutation_redaction_and_port_signature() -> None:
    upstream = _authorized_report()
    snapshot = _snapshot()
    before = upstream.model_dump(mode="json")
    service = ProviderConfigurationNormalizationService()

    first = service.normalize("attempt:001", snapshot, upstream)
    second = service.normalize("attempt:001", snapshot, upstream)
    serialized = first.model_dump_json()
    signature = inspect.signature(ProviderGenerationInvocationPort.invoke)

    assert first == second
    assert upstream.model_dump(mode="json") == before
    assert tuple(signature.parameters) == ("self", "materialized_input")
    for forbidden in (
        "PRIVATE-PROMPT",
        "api_key",
        "credential",
        "token",
        "endpoint",
        "https://",
        "C:/",
        "workflow_json",
        "provider_payload",
    ):
        assert forbidden not in serialized


def test_finding_dto_is_closed() -> None:
    with pytest.raises(ValidationError):
        ProviderConfigurationNormalizationFindingDTO(
            code="TEST", status="blocked", message="test", raw_prompt="PRIVATE-PROMPT"
        )
