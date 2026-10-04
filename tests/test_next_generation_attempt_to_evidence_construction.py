"""Focused contracts for internal Attempt-to-Evidence construction validation."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from manga_director.production.next_generation_asset_registration import (
    AssetRegistrationRequest,
    AssetRegistrationRuntimeResult,
    OutputAssetRegistrationReport,
    OutputAssetRegistrationService,
)
from manga_director.production.next_generation_attempt_to_evidence_construction import (
    AttemptToEvidenceConstructionFindingDTO,
    AttemptToEvidenceConstructionReport,
    AttemptToEvidenceConstructionService,
)
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
    GenerationOutputEvidenceDTO,
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
from manga_director.production.next_generation_provider_invocation import (
    OpaqueGeneratedOutputHandle,
    ProviderInvocationRuntimeResult,
    ProviderInvocationService,
)
from manga_director.production.next_generation_secure_execution_input_resolution import (
    AuthoritativeExecutionInputSnapshot,
    OpaqueReferenceAssetHandle,
    SecureExecutionInputResolutionService,
)
from manga_director.production.next_generation_structured_generation_request import (
    GenerationIdentityBindingDTO,
    GenerationInputEvidenceDTO,
    GenerationProductionProfileDTO,
    StructuredGenerationRequestDTO,
    StructuredGenerationRequestValidationService,
)

ROOT = Path(__file__).resolve().parents[1]
_ATTEMPT = "attempt:construction:001"
_PROVIDER = "provider:local-a"
_OBSERVED_AT = datetime(2026, 8, 22, 15, 0, tzinfo=UTC)


class InMemoryInputResolver:
    def __init__(self, snapshot: AuthoritativeExecutionInputSnapshot) -> None:
        self.snapshot = snapshot
        self.calls = 0

    def resolve(self, input_reference: str) -> AuthoritativeExecutionInputSnapshot | None:
        self.calls += 1
        return self.snapshot if input_reference == self.snapshot.input_reference else None


class InMemoryReferenceResolver:
    def __init__(self) -> None:
        self.calls = 0

    def resolve(self, reference_asset_id: str) -> OpaqueReferenceAssetHandle | None:
        self.calls += 1
        if reference_asset_id != "asset:reference:001":
            return None
        return OpaqueReferenceAssetHandle(reference_asset_id, object())


class InMemoryProviderPort:
    provider_reference = _PROVIDER

    def __init__(self) -> None:
        self.calls = 0

    def invoke(self, materialized_input: object) -> ProviderInvocationRuntimeResult:
        del materialized_input
        self.calls += 1
        return ProviderInvocationRuntimeResult(
            attempt_id=_ATTEMPT,
            provider_reference=_PROVIDER,
            outcome="succeeded",
            output_handle=OpaqueGeneratedOutputHandle("SYNTHETIC-PRIVATE-OUTPUT"),
        )


class InMemoryAssetRegistrationPort:
    def __init__(self) -> None:
        self.calls = 0

    def register(self, request: AssetRegistrationRequest) -> AssetRegistrationRuntimeResult:
        self.calls += 1
        return AssetRegistrationRuntimeResult(
            attempt_id=request.attempt_id,
            provider_reference=request.provider_reference,
            outcome="registered",
            output=GenerationOutputEvidenceDTO(
                output_asset_id="asset:generated:owner:001",
                media_type="image/png",
            ),
            durable_registration_confirmed=True,
        )


def _known(value: str) -> EvidenceValueDTO:
    return EvidenceValueDTO(availability="known", value=value)


def _reports(*, requested_seed: EvidenceValueDTO | None = None):
    requirements = (
        GenerationCapabilityRequirementDTO(capability_id="text_prompt", requirement_level="required"),
    )
    profile = GenerationProductionProfileDTO(
        profile_id="profile:manga", profile_version="v1", capability_requirements=requirements
    )
    request = StructuredGenerationRequestDTO(
        request_id="request:construction:001",
        target_page_reference="page:001",
        generation_intent_reference="intent:001",
        input=GenerationInputEvidenceDTO(
            input_reference="input:001",
            input_content_hash=_known("input-hash"),
        ),
        capability_requirements=requirements,
        provenance_reference="provenance:001",
        profile_id=profile.profile_id,
        profile_version=profile.profile_version,
        identity_bindings=(
            GenerationIdentityBindingDTO(
                character_id="character:001",
                identity_id="identity:001",
                identity_version="v1",
                reference_asset_ids=("asset:reference:001",),
            ),
        ),
    )
    request_report = StructuredGenerationRequestValidationService().validate(request, profile)
    negotiation = ProviderCapabilityNegotiationService().validate(
        requirements,
        ProviderCapabilityDeclarationDTO(
            provider_reference=_PROVIDER,
            capability_states=(
                ProviderCapabilityStateDTO(capability_id="text_prompt", state="supported"),
            ),
        ),
    )
    readiness = PreExecutionReadinessService().validate(
        PreExecutionReadinessInputDTO(
            request_validation_report=request_report,
            capability_negotiation_report=negotiation,
            provider_reference=_PROVIDER,
        )
    )
    authorization = ExecutionAuthorizationValidationService().validate(
        readiness,
        (
            ExecutionAuthorizationRecordDTO(
                authorization_id="authorization:001",
                authorizer_id="human:editor:001",
                authorized_at=datetime(2026, 8, 22, 14, 0, tzinfo=UTC),
                request_id=request.request_id,
                provider_reference=_PROVIDER,
            ),
        ),
    )
    envelope_report = AuthorizedGenerationExecutionEnvelopeValidationService().validate(
        (
            AuthorizedGenerationExecutionEnvelopeDTO(
                attempt_id=_ATTEMPT,
                request_id=request.request_id,
                provider_reference=_PROVIDER,
                authorization_ids=("authorization:001",),
                profile_id=profile.profile_id,
                profile_version=profile.profile_version,
                generation_intent_reference=request.generation_intent_reference,
                input_reference=request.input.input_reference,
            ),
        ),
        authorization,
    )
    input_resolver = InMemoryInputResolver(
        AuthoritativeExecutionInputSnapshot.from_prompt_material(
            input_reference=request.input.input_reference,
            generation_intent_reference=request.generation_intent_reference,
            required_reference_asset_ids=("asset:reference:001",),
            raw_prompt_material="SYNTHETIC-PRIVATE-PROMPT",
        )
    )
    reference_resolver = InMemoryReferenceResolver()
    resolution = SecureExecutionInputResolutionService().resolve(
        _ATTEMPT, envelope_report, input_resolver, reference_resolver
    )
    provider_port = InMemoryProviderPort()
    invocation = ProviderInvocationService().invoke(_ATTEMPT, resolution, provider_port)
    asset_port = InMemoryAssetRegistrationPort()
    registration = OutputAssetRegistrationService().register(_ATTEMPT, invocation, asset_port)
    configuration = ProviderConfigurationNormalizationService().normalize(
        _ATTEMPT,
        AuthoritativeProviderConfigurationSnapshot(
            attempt_id=_ATTEMPT,
            provider_reference=_PROVIDER,
            profile_id=profile.profile_id,
            profile_version=profile.profile_version,
            provider_id=_known("provider:local"),
            model_id=_known("model:001"),
            model_version=_known("v1"),
            workflow_id=_known("workflow:001"),
            workflow_version=_known("v1"),
            requested_seed=requested_seed,
        ),
        envelope_report,
    )
    return registration, configuration, (input_resolver, reference_resolver, provider_port, asset_port)


def _construct(
    registration: OutputAssetRegistrationReport,
    configuration,
    observed_at: datetime = _OBSERVED_AT,
) -> AttemptToEvidenceConstructionReport:
    return AttemptToEvidenceConstructionService().construct(
        _ATTEMPT, observed_at, registration, configuration
    )


def test_constructs_valid_evidence_from_the_durable_chain() -> None:
    registration, configuration, _ = _reports(requested_seed=_known("42"))

    report = _construct(registration, configuration)

    assert report.status == "ready"
    assert report.constructed is True
    assert report.bound is True
    assert report.ready is True
    assert report.generation_evidence is not None
    assert report.generation_evidence.observed_at == _OBSERVED_AT
    assert report.generation_evidence.output == registration.registered_output.output
    assert report.generation_evidence.output.output_asset_id == "asset:generated:owner:001"
    assert report.generation_evidence.output.media_type == "image/png"
    assert report.generation_evidence_validation_report is not None
    assert report.attempt_to_evidence_binding_report is not None


def test_missing_requested_seed_is_declared_unknown_without_a_scalar_value() -> None:
    registration, configuration, _ = _reports()

    report = _construct(registration, configuration)

    assert report.constructed is True
    assert report.bound is True
    assert report.ready is False
    assert report.status == "needs_evidence"
    assert report.generation_evidence is not None
    assert report.generation_evidence.configuration.seed == EvidenceValueDTO(availability="unknown")
    assert report.generation_evidence.configuration.parameters == ()


def test_naive_or_invalid_observation_time_fails_closed() -> None:
    registration, configuration, _ = _reports()

    naive = _construct(registration, configuration, datetime(2026, 8, 22, 15, 0))
    invalid = AttemptToEvidenceConstructionService().construct(
        _ATTEMPT, "not-a-timestamp", registration, configuration  # type: ignore[arg-type]
    )

    assert [item.code for item in naive.findings] == ["OBSERVED_AT_INVALID"]
    assert [item.code for item in invalid.findings] == ["OBSERVED_AT_INVALID"]
    assert naive.generation_evidence is None
    assert invalid.generation_evidence is None


@pytest.mark.parametrize(
    ("update", "code"),
    (
        ({"status": "blocked", "registered": False}, "OUTPUT_REGISTRATION_NOT_REGISTERED"),
        ({"registered_output": None}, "REGISTERED_OUTPUT_MISSING"),
    ),
)
def test_registration_durability_prerequisites_fail_closed(update: dict[str, object], code: str) -> None:
    registration, configuration, _ = _reports()

    report = _construct(registration.model_copy(update=update), configuration)

    assert report.status == "blocked"
    assert report.constructed is False
    assert [item.code for item in report.findings] == [code]


def test_attempt_and_provider_mismatches_fail_closed() -> None:
    registration, configuration, _ = _reports()
    wrong_attempt = registration.model_copy(update={"attempt_id": "attempt:other"})
    wrong_provider = registration.model_copy(update={"provider_reference": "provider:other"})

    attempt_report = _construct(wrong_attempt, configuration)
    provider_report = _construct(wrong_provider, configuration)

    assert [item.code for item in attempt_report.findings] == ["ATTEMPT_BINDING_MISMATCH"]
    assert [item.code for item in provider_report.findings] == ["PROVIDER_BINDING_MISMATCH"]


def test_malformed_chain_and_configuration_mismatch_fail_closed() -> None:
    registration, configuration, _ = _reports()
    malformed = registration.model_copy(update={"provider_invocation_report": None})
    mismatched_selection = configuration.selection.model_copy(update={"profile_id": "profile:other"})
    mismatched_configuration = configuration.model_copy(update={"selection": mismatched_selection})

    malformed_report = _construct(malformed, configuration)
    configuration_report = _construct(registration, mismatched_configuration)

    assert [item.code for item in malformed_report.findings] == ["MALFORMED_EXECUTION_CHAIN"]
    assert [item.code for item in configuration_report.findings] == [
        "PROVIDER_CONFIGURATION_BINDING_MISMATCH"
    ]


def test_nonready_configuration_blocks_before_evidence_construction() -> None:
    registration, configuration, _ = _reports()

    report = _construct(
        registration, configuration.model_copy(update={"status": "blocked", "ready": False})
    )

    assert [item.code for item in report.findings] == ["PROVIDER_CONFIGURATION_NOT_READY"]
    assert report.generation_evidence_validation_report is None
    assert report.attempt_to_evidence_binding_report is None


def test_replay_is_deterministic_and_does_not_mutate_caller_reports() -> None:
    registration, configuration, _ = _reports(requested_seed=_known("42"))
    before_registration = registration.model_dump(mode="json")
    before_configuration = configuration.model_dump(mode="json")

    first = _construct(registration, configuration)
    second = _construct(registration, configuration)

    assert first == second
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert registration.model_dump(mode="json") == before_registration
    assert configuration.model_dump(mode="json") == before_configuration


def test_construction_is_closed_immutable_and_redacts_private_material() -> None:
    registration, configuration, _ = _reports(requested_seed=_known("42"))
    report = _construct(registration, configuration)
    finding = AttemptToEvidenceConstructionFindingDTO(code="TEST", status="blocked", message="test")

    with pytest.raises(ValidationError):
        finding.code = "changed"
    with pytest.raises(ValidationError):
        AttemptToEvidenceConstructionReport(**report.model_dump(), prompt="private")
    serialized = report.model_dump_json()
    for private_value in (
        "SYNTHETIC-PRIVATE-PROMPT",
        "SYNTHETIC-PRIVATE-OUTPUT",
        "storage_path",
        "credential",
        "base64",
    ):
        assert private_value not in serialized


def test_construction_performs_no_new_runtime_or_persistence_activity() -> None:
    registration, configuration, ports = _reports(requested_seed=_known("42"))
    calls_before = tuple(port.calls for port in ports)

    report = _construct(registration, configuration)

    assert tuple(port.calls for port in ports) == calls_before
    assert report.persistence_performed is False
    assert report.assets_read is False
    assert report.provider_executed is False
    assert report.timestamp_generated is False


def test_source_uses_existing_validators_and_keeps_forbidden_boundaries_out() -> None:
    source = (
        ROOT
        / "src/manga_director/production/next_generation_attempt_to_evidence_construction.py"
    ).read_text(encoding="utf-8")

    assert "GenerationEvidenceValidationService().validate" in source
    assert "AttemptToEvidenceBindingService().validate" in source
    for forbidden in (
        "OpaqueGeneratedOutputHandle",
        "LocalDurableAssetOwner",
        "AssetRetriever",
        "WorkflowEngine",
        "StateMachine",
        "FailureEvidence",
        "CredentialManager",
        "openai",
        "sqlite3",
        "requests.",
        "httpx.",
        "datetime.now",
        "Path(",
        "open(",
    ):
        assert forbidden not in source
    production_init = (ROOT / "src/manga_director/production/__init__.py").read_text(
        encoding="utf-8"
    )
    root_init = (ROOT / "src/manga_director/__init__.py").read_text(encoding="utf-8")
    assert "next_generation_attempt_to_evidence_construction" not in production_init
    assert "next_generation_attempt_to_evidence_construction" not in root_init
