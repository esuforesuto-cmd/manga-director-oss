"""Focused contracts for internal fake-transport provider adapter composition."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

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
    GenerationIdentityBindingDTO,
    GenerationInputEvidenceDTO,
)
from manga_director.production.next_generation_pre_execution_readiness import (
    PreExecutionReadinessInputDTO,
    PreExecutionReadinessService,
)
from manga_director.production.next_generation_provider_adapter_composition import (
    ProviderAdapterCompositionService,
    ProviderPrivateTransportRequest,
    ProviderPrivateTransportResult,
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
from manga_director.production.next_generation_provider_invocation import (
    ProviderInvocationService,
)
from manga_director.production.next_generation_secure_execution_input_resolution import (
    AuthoritativeExecutionInputSnapshot,
    OpaqueReferenceAssetHandle,
    SecureExecutionInputResolutionOutcome,
    SecureExecutionInputResolutionService,
)
from manga_director.production.next_generation_structured_generation_request import (
    GenerationProductionProfileDTO,
    StructuredGenerationRequestDTO,
    StructuredGenerationRequestValidationService,
)

ROOT = Path(__file__).resolve().parents[1]


class InMemoryInputResolver:
    def resolve(self, input_reference: str) -> AuthoritativeExecutionInputSnapshot | None:
        if input_reference != "input:001":
            return None
        return AuthoritativeExecutionInputSnapshot.from_prompt_material(
            input_reference="input:001",
            generation_intent_reference="intent:001",
            raw_prompt_material="TOP-SECRET-PROMPT",
            required_reference_asset_ids=("asset:001",),
        )


class InMemoryAssetResolver:
    def resolve(self, reference_asset_id: str) -> OpaqueReferenceAssetHandle | None:
        if reference_asset_id != "asset:001":
            return None
        return OpaqueReferenceAssetHandle(reference_asset_id, object())


class InMemoryPrivateTransport:
    def __init__(self, result: object | None = None, *, raises: bool = False) -> None:
        self.result = result or ProviderPrivateTransportResult("succeeded", object())
        self.raises = raises
        self.calls: list[ProviderPrivateTransportRequest] = []

    def invoke(self, request: ProviderPrivateTransportRequest) -> ProviderPrivateTransportResult:
        self.calls.append(request)
        if self.raises:
            raise TimeoutError("native private timeout detail")
        return self.result  # type: ignore[return-value]


def _chain():
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
        identity_bindings=(
            GenerationIdentityBindingDTO(
                character_id="character:001",
                identity_id="identity:001",
                identity_version="v1",
                reference_asset_ids=("asset:001",),
            ),
        ),
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
    authorized = AuthorizedGenerationExecutionEnvelopeValidationService().validate(
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
    configuration = ProviderConfigurationNormalizationService().normalize(
        "attempt:001",
        AuthoritativeProviderConfigurationSnapshot(
            attempt_id="attempt:001",
            provider_reference="provider:local-a",
            profile_id="profile:manga",
            profile_version="v1",
            provider_id=_value("openai"),
            model_id=_value("model:image"),
            model_version=_value("v1"),
            workflow_id=_value(availability="unavailable"),
            workflow_version=_value(availability="unavailable"),
            requested_seed=_value(1234),
        ),
        authorized,
    )
    resolution = SecureExecutionInputResolutionService().resolve(
        "attempt:001", authorized, InMemoryInputResolver(), InMemoryAssetResolver()
    )
    assert resolution.materialized_input is not None
    return configuration, resolution


def _value(value: object | None = None, availability: str = "known") -> EvidenceValueDTO:
    return EvidenceValueDTO(
        availability=availability,  # type: ignore[arg-type]
        value=value if availability == "known" else None,
    )


def _adapter(transport: InMemoryPrivateTransport):
    configuration, _ = _chain()
    adapter = ProviderAdapterCompositionService().compose(configuration, transport)
    assert adapter is not None
    return adapter


def test_non_ready_configuration_is_rejected_without_transport_access() -> None:
    configuration, _ = _chain()
    transport = InMemoryPrivateTransport()
    blocked = configuration.model_copy(update={"status": "blocked", "ready": False, "selection": None})

    adapter = ProviderAdapterCompositionService().compose(blocked, transport)

    assert adapter is None
    assert transport.calls == []


def test_adapter_is_exact_bound_to_one_immutable_configuration_selection() -> None:
    configuration, _ = _chain()
    transport = InMemoryPrivateTransport()
    adapter = ProviderAdapterCompositionService().compose(configuration, transport)

    assert adapter is not None
    assert adapter.provider_reference == "provider:local-a"
    assert configuration.selection is not None
    assert adapter._selection == configuration.selection


@pytest.mark.parametrize(
    "updates",
    (
        {"attempt_id": "attempt:other"},
        {"provider_reference": "provider:other"},
        {"profile_id": "profile:other"},
        {"profile_version": "v2"},
    ),
)
def test_binding_mismatches_fail_closed_before_transport(
    updates: dict[str, str],
) -> None:
    transport = InMemoryPrivateTransport()
    adapter = _adapter(transport)
    _, resolution = _chain()
    assert resolution.materialized_input is not None

    result = adapter.invoke(replace(resolution.materialized_input, **updates))

    assert result.outcome == "runtime_failed"
    assert result.failure_category == "runtime_failure"
    assert result.output_handle is None
    assert transport.calls == []


def test_valid_invocation_calls_transport_once_and_returns_opaque_output() -> None:
    transport = InMemoryPrivateTransport()
    adapter = _adapter(transport)
    _, resolution = _chain()
    assert resolution.materialized_input is not None

    result = adapter.invoke(resolution.materialized_input)

    assert result.outcome == "succeeded"
    assert result.output_handle is not None
    assert "opaque_value" not in repr(result.output_handle)
    assert len(transport.calls) == 1
    request = transport.calls[0]
    assert request.raw_prompt == "TOP-SECRET-PROMPT"
    assert tuple(handle.reference_asset_id for handle in request.reference_asset_handles) == (
        "asset:001",
    )
    assert request.configuration_selection.requested_seed == _value(1234)
    assert not hasattr(request.configuration_selection, "effective_seed")


@pytest.mark.parametrize(
    ("result", "outcome", "category"),
    (
        (
            ProviderPrivateTransportResult("provider_failed"),
            "provider_failed",
            "provider_declared_failure",
        ),
        (ProviderPrivateTransportResult("runtime_failed"), "runtime_failed", "runtime_failure"),
        (ProviderPrivateTransportResult("succeeded"), "runtime_failed", "runtime_failure"),
        (
            ProviderPrivateTransportResult("provider_failed", object()),
            "runtime_failed",
            "runtime_failure",
        ),
        (object(), "runtime_failed", "runtime_failure"),
    ),
)
def test_private_failures_and_invalid_results_are_normalized(
    result: object, outcome: str, category: str
) -> None:
    transport = InMemoryPrivateTransport(result)
    adapter = _adapter(transport)
    _, resolution = _chain()
    assert resolution.materialized_input is not None

    invocation = adapter.invoke(resolution.materialized_input)

    assert invocation.outcome == outcome
    assert invocation.failure_category == category
    assert invocation.output_handle is None
    assert len(transport.calls) == 1


def test_timeout_style_exception_is_redacted_and_never_retried() -> None:
    transport = InMemoryPrivateTransport(raises=True)
    adapter = _adapter(transport)
    _, resolution = _chain()
    assert resolution.materialized_input is not None

    invocation = ProviderInvocationService().invoke(
        "attempt:001",
        SecureExecutionInputResolutionOutcome(
            report=resolution.report,
            materialized_input=resolution.materialized_input,
        ),
        adapter,
    )

    assert [item.code for item in invocation.report.findings] == ["PROVIDER_RUNTIME_FAILURE"]
    assert "native private timeout detail" not in invocation.report.model_dump_json()
    assert "TOP-SECRET-PROMPT" not in invocation.report.model_dump_json()
    assert len(transport.calls) == 1


def test_repeatability_input_non_mutation_and_report_redaction() -> None:
    configuration, resolution = _chain()
    assert resolution.materialized_input is not None
    transport = InMemoryPrivateTransport()
    adapter = ProviderAdapterCompositionService().compose(configuration, transport)
    assert adapter is not None
    before = (
        configuration.model_dump(mode="json"),
        resolution.report.model_dump(mode="json"),
        resolution.materialized_input.raw_prompt,
    )

    first = ProviderInvocationService().invoke("attempt:001", resolution, adapter)
    second = ProviderInvocationService().invoke("attempt:001", resolution, adapter)

    assert (
        configuration.model_dump(mode="json"),
        resolution.report.model_dump(mode="json"),
        resolution.materialized_input.raw_prompt,
    ) == before
    assert first.report.model_dump(mode="json") == second.report.model_dump(mode="json")
    assert "TOP-SECRET-PROMPT" not in first.report.model_dump_json()
    assert "output_material" not in first.report.model_dump_json()
    assert len(transport.calls) == 2


def test_source_does_not_contaminate_legacy_public_or_runtime_boundaries() -> None:
    source = (
        ROOT / "src/manga_director/production/next_generation_provider_adapter_composition.py"
    ).read_text(encoding="utf-8")
    for forbidden in (
        "manga_director.adapters",
        "manga_director.agents",
        "manga_director.prompting",
        "manga_director.workflow",
        "manga_director.domain.state_machine",
        "CredentialManager",
        "SecretManager",
        "GenerationEvidenceEnvelopeDTO",
        "open(",
        "requests.",
        "httpx.",
        "logging",
        "datetime",
    ):
        assert forbidden not in source
    production_init = (ROOT / "src/manga_director/production/__init__.py").read_text(
        encoding="utf-8"
    )
    root_init = (ROOT / "src/manga_director/__init__.py").read_text(encoding="utf-8")
    assert "next_generation_provider_adapter_composition" not in production_init
    assert "next_generation_provider_adapter_composition" not in root_init
