"""Focused contracts for internal fake-port output asset registration."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from manga_director.production.next_generation_asset_registration import (
    AssetRegistrationRequest,
    AssetRegistrationRuntimeResult,
    OutputAssetRegistrationFindingDTO,
    OutputAssetRegistrationReport,
    OutputAssetRegistrationService,
    RegisteredGenerationOutputDTO,
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
    GenerationIdentityBindingDTO,
    GenerationInputEvidenceDTO,
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
from manga_director.production.next_generation_provider_invocation import (
    OpaqueGeneratedOutputHandle,
    ProviderInvocationOutcome,
    ProviderInvocationRuntimeResult,
    ProviderInvocationService,
)
from manga_director.production.next_generation_secure_execution_input_resolution import (
    AuthoritativeExecutionInputSnapshot,
    OpaqueReferenceAssetHandle,
    SecureExecutionInputResolutionService,
)
from manga_director.production.next_generation_structured_generation_request import (
    GenerationProductionProfileDTO,
    StructuredGenerationRequestDTO,
    StructuredGenerationRequestValidationService,
)

ROOT = Path(__file__).resolve().parents[1]


class InMemoryInputResolver:
    def __init__(self, snapshot: AuthoritativeExecutionInputSnapshot) -> None:
        self.snapshot = snapshot

    def resolve(self, input_reference: str) -> AuthoritativeExecutionInputSnapshot | None:
        return self.snapshot if input_reference == self.snapshot.input_reference else None


class InMemoryReferenceAssetResolver:
    def resolve(self, reference_asset_id: str) -> OpaqueReferenceAssetHandle | None:
        if reference_asset_id != "asset:reference:001":
            return None
        return OpaqueReferenceAssetHandle(reference_asset_id, object())


class InMemoryProviderPort:
    provider_reference = "provider:local-a"

    def invoke(self, materialized_input: object) -> ProviderInvocationRuntimeResult:
        del materialized_input
        return ProviderInvocationRuntimeResult(
            attempt_id="attempt:001",
            provider_reference=self.provider_reference,
            outcome="succeeded",
            output_handle=OpaqueGeneratedOutputHandle("PRIVATE-OUTPUT-BYTES"),
        )


class InMemoryAssetRegistrationPort:
    """Test-only asset owner with explicit idempotency and no external access."""

    def __init__(
        self,
        *,
        output: GenerationOutputEvidenceDTO | None = None,
        mode: str = "registered",
        raises: bool = False,
        returned_attempt_id: str = "attempt:001",
        returned_provider_reference: str = "provider:local-a",
        durable_registration_confirmed: bool = True,
    ) -> None:
        self.output = output or GenerationOutputEvidenceDTO(output_asset_id="asset:generated:001")
        self.mode = mode
        self.raises = raises
        self.returned_attempt_id = returned_attempt_id
        self.returned_provider_reference = returned_provider_reference
        self.durable_registration_confirmed = durable_registration_confirmed
        self.calls: list[AssetRegistrationRequest] = []
        self._registrations: dict[str, tuple[str, object, GenerationOutputEvidenceDTO]] = {}

    def register(self, request: AssetRegistrationRequest) -> AssetRegistrationRuntimeResult | object:
        self.calls.append(request)
        if self.raises:
            raise RuntimeError("asset-owner-private-detail: do-not-report")
        if self.mode == "invalid":
            return object()
        if self.mode == "failed":
            return AssetRegistrationRuntimeResult(
                attempt_id=request.attempt_id,
                provider_reference=request.provider_reference,
                outcome="failed",
            )
        existing = self._registrations.get(request.attempt_id)
        if existing is not None:
            provider_reference, opaque_value, output = existing
            if (
                provider_reference != request.provider_reference
                or opaque_value is not request.output_handle.opaque_value
            ):
                return AssetRegistrationRuntimeResult(
                    attempt_id=request.attempt_id,
                    provider_reference=request.provider_reference,
                    outcome="idempotency_conflict",
                )
            return AssetRegistrationRuntimeResult(
                attempt_id=request.attempt_id,
                provider_reference=request.provider_reference,
                outcome="registered",
                output=output,
                durable_registration_confirmed=True,
            )
        self._registrations[request.attempt_id] = (
            request.provider_reference,
            request.output_handle.opaque_value,
            self.output,
        )
        return AssetRegistrationRuntimeResult(
            attempt_id=self.returned_attempt_id,
            provider_reference=self.returned_provider_reference,
            outcome=self.mode,  # type: ignore[arg-type]
            output=self.output if self.mode == "registered" else None,
            durable_registration_confirmed=self.durable_registration_confirmed,
        )


def _provider_outcome() -> ProviderInvocationOutcome:
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
                reference_asset_ids=("asset:reference:001",),
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
    envelope_report = AuthorizedGenerationExecutionEnvelopeValidationService().validate(
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
    snapshot = AuthoritativeExecutionInputSnapshot.from_prompt_material(
        input_reference="input:001",
        generation_intent_reference="intent:001",
        required_reference_asset_ids=("asset:reference:001",),
        raw_prompt_material="PRIVATE-PROMPT-MATERIAL",
    )
    resolution = SecureExecutionInputResolutionService().resolve(
        "attempt:001",
        envelope_report,
        InMemoryInputResolver(snapshot),
        InMemoryReferenceAssetResolver(),
    )
    return ProviderInvocationService().invoke("attempt:001", resolution, InMemoryProviderPort())


def _register(
    outcome: ProviderInvocationOutcome,
    port: InMemoryAssetRegistrationPort,
    attempt_id: str = "attempt:001",
) -> OutputAssetRegistrationReport:
    return OutputAssetRegistrationService().register(attempt_id, outcome, port)


def test_success_requires_durable_confirmation_and_exposes_only_logical_output_evidence() -> None:
    output = GenerationOutputEvidenceDTO(
        output_asset_id="asset:generated:owner-issued:001",
        output_content_hash=EvidenceValueDTO(availability="known", value="owner-supplied-hash"),
        media_type="image/png",
    )
    port = InMemoryAssetRegistrationPort(output=output)
    outcome = _provider_outcome()

    report = _register(outcome, port)

    assert report.status == "registered"
    assert report.registered is True
    assert report.registration_performed is True
    assert report.registered_output is not None
    assert report.registered_output.output == output
    assert port.calls[0].output_handle is outcome.output_handle
    assert report.model_dump(mode="json") == report.model_dump(mode="json")


def test_id_issuance_without_durable_confirmation_is_invalid() -> None:
    report = _register(
        _provider_outcome(),
        InMemoryAssetRegistrationPort(durable_registration_confirmed=False),
    )

    assert report.status == "blocked"
    assert report.registered is False
    assert report.registered_output is None
    assert [item.code for item in report.findings] == ["OUTPUT_REGISTRATION_RESULT_INVALID"]


def test_idempotent_repeat_returns_the_same_owner_issued_asset() -> None:
    outcome = _provider_outcome()
    port = InMemoryAssetRegistrationPort()

    first = _register(outcome, port)
    second = _register(outcome, port)

    assert first.registered_output is not None
    assert second.registered_output is not None
    assert first.registered_output.output.output_asset_id == second.registered_output.output.output_asset_id
    assert len(port.calls) == 2


def test_conflicting_repeat_fails_closed_without_an_output_asset() -> None:
    initial = _provider_outcome()
    port = InMemoryAssetRegistrationPort()
    first = _register(initial, port)
    conflicting = ProviderInvocationOutcome(
        report=initial.report,
        output_handle=OpaqueGeneratedOutputHandle("DIFFERENT-PRIVATE-OUTPUT"),
    )

    report = _register(conflicting, port)

    assert first.registered is True
    assert report.status == "blocked"
    assert report.registered_output is None
    assert [item.code for item in report.findings] == ["OUTPUT_REGISTRATION_IDEMPOTENCY_CONFLICT"]


@pytest.mark.parametrize(
    ("port", "code"),
    (
        (InMemoryAssetRegistrationPort(mode="failed"), "OUTPUT_REGISTRATION_FAILED"),
        (InMemoryAssetRegistrationPort(mode="invalid"), "OUTPUT_REGISTRATION_RESULT_INVALID"),
        (InMemoryAssetRegistrationPort(raises=True), "OUTPUT_REGISTRATION_FAILED"),
        (
            InMemoryAssetRegistrationPort(returned_attempt_id="attempt:other"),
            "REGISTRATION_ATTEMPT_MISMATCH",
        ),
        (
            InMemoryAssetRegistrationPort(returned_provider_reference="provider:other"),
            "REGISTRATION_PROVIDER_MISMATCH",
        ),
    ),
)
def test_port_failures_and_invalid_results_are_redacted(
    port: InMemoryAssetRegistrationPort, code: str
) -> None:
    report = _register(_provider_outcome(), port)

    assert report.status == "blocked"
    assert report.registered is False
    assert report.registered_output is None
    assert [item.code for item in report.findings] == [code]
    assert "asset-owner-private-detail" not in report.model_dump_json()


@pytest.mark.parametrize(
    ("outcome", "code"),
    (
        (
            lambda: ProviderInvocationOutcome(
                report=_provider_outcome().report.model_copy(
                    update={"status": "blocked", "succeeded": False}
                ),
                output_handle=OpaqueGeneratedOutputHandle("PRIVATE-OUTPUT-BYTES"),
            ),
            "PROVIDER_INVOCATION_NOT_SUCCEEDED",
        ),
        (
            lambda: ProviderInvocationOutcome(report=_provider_outcome().report),
            "GENERATED_OUTPUT_HANDLE_MISSING",
        ),
    ),
)
def test_invalid_or_missing_upstream_outcome_blocks_before_port_access(outcome, code: str) -> None:
    port = InMemoryAssetRegistrationPort()

    report = _register(outcome(), port)

    assert [item.code for item in report.findings] == [code]
    assert report.registration_performed is False
    assert port.calls == []


def test_explicit_attempt_and_upstream_provider_bindings_are_exact() -> None:
    outcome = _provider_outcome()
    wrong_attempt = _register(outcome, InMemoryAssetRegistrationPort(), "attempt:other")
    wrong_provider = _register(
        ProviderInvocationOutcome(
            report=outcome.report.model_copy(update={"provider_reference": "https://unsafe.example"}),
            output_handle=outcome.output_handle,
        ),
        InMemoryAssetRegistrationPort(),
    )

    assert [item.code for item in wrong_attempt.findings] == ["REGISTRATION_ATTEMPT_MISMATCH"]
    assert [item.code for item in wrong_provider.findings] == ["REGISTRATION_PROVIDER_MISMATCH"]


def test_dtos_are_frozen_closed_and_durable_reports_do_not_leak_private_material() -> None:
    finding = OutputAssetRegistrationFindingDTO(code="TEST", status="blocked", message="test")
    with pytest.raises(ValidationError):
        finding.code = "changed"
    with pytest.raises(ValidationError):
        RegisteredGenerationOutputDTO(
            attempt_id="attempt:001",
            provider_reference="provider:local-a",
            output=GenerationOutputEvidenceDTO(output_asset_id="asset:001"),
            raw_output="PRIVATE-OUTPUT-BYTES",
        )

    report = _register(_provider_outcome(), InMemoryAssetRegistrationPort())
    with pytest.raises(ValidationError):
        report.registered = False
    with pytest.raises(ValidationError):
        OutputAssetRegistrationReport(**report.model_dump(), storage_path="C:/private/output.png")
    serialized = report.model_dump_json()
    for private_value in (
        "PRIVATE-PROMPT-MATERIAL",
        "PRIVATE-OUTPUT-BYTES",
        "asset-owner-private-detail",
        "storage_path",
    ):
        assert private_value not in serialized


def test_reports_are_deterministic_and_caller_inputs_are_not_mutated() -> None:
    outcome = _provider_outcome()
    before = outcome.report.model_dump(mode="json")
    port = InMemoryAssetRegistrationPort()

    first = _register(outcome, port)
    second = _register(outcome, port)

    assert outcome.report.model_dump(mode="json") == before
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_source_keeps_external_io_evidence_and_public_exports_out() -> None:
    source = (ROOT / "src/manga_director/production/next_generation_asset_registration.py").read_text(
        encoding="utf-8"
    )
    for forbidden in (
        "manga_director.adapters",
        "manga_director.agents",
        "manga_director.workflow",
        "manga_director.domain.state_machine",
        "GenerationEvidenceEnvelopeDTO",
        "CredentialManager",
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
    assert "next_generation_asset_registration" not in production_init
    assert "next_generation_asset_registration" not in root_init
