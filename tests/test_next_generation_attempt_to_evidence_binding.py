"""Focused contracts for internal Attempt-to-Evidence binding validation."""

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
from manga_director.production.next_generation_attempt_to_evidence_binding import (
    AttemptToEvidenceBindingFindingDTO,
    AttemptToEvidenceBindingReport,
    AttemptToEvidenceBindingService,
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
    GenerationConfigurationEvidenceDTO,
    GenerationEvidenceEnvelopeDTO,
    GenerationEvidenceValidationReport,
    GenerationEvidenceValidationService,
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
    def register(self, request: AssetRegistrationRequest) -> AssetRegistrationRuntimeResult:
        return AssetRegistrationRuntimeResult(
            attempt_id=request.attempt_id,
            provider_reference=request.provider_reference,
            outcome="registered",
            output=GenerationOutputEvidenceDTO(
                output_asset_id="asset:generated:001",
                output_content_hash=EvidenceValueDTO(availability="known", value="owner-hash"),
                media_type="image/png",
            ),
            durable_registration_confirmed=True,
        )


def _registered_report() -> OutputAssetRegistrationReport:
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
        input=GenerationInputEvidenceDTO(
            input_reference="input:001",
            input_content_hash=EvidenceValueDTO(availability="known", value="input-hash"),
        ),
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
    invocation = ProviderInvocationService().invoke("attempt:001", resolution, InMemoryProviderPort())
    return OutputAssetRegistrationService().register(
        "attempt:001", invocation, InMemoryAssetRegistrationPort()
    )


def _known(value: str) -> EvidenceValueDTO:
    return EvidenceValueDTO(availability="known", value=value)


def _evidence_envelope(
    report: OutputAssetRegistrationReport,
    *,
    attempt_id: str = "attempt:001",
) -> GenerationEvidenceEnvelopeDTO:
    request = _request(report)
    assert report.registered_output is not None
    return GenerationEvidenceEnvelopeDTO(
        attempt_id=attempt_id,
        observed_at=datetime(2026, 8, 22, 13, 0, tzinfo=UTC),
        provenance_reference=request.provenance_reference,
        input=request.input,
        output=report.registered_output.output,
        configuration=GenerationConfigurationEvidenceDTO(
            provider_id=_known("caller-provider-evidence"),
            model_id=_known("model:001"),
            model_version=_known("v1"),
            workflow_id=_known("workflow:001"),
            workflow_version=_known("v1"),
            seed=_known("42"),
        ),
        identity_bindings=request.identity_bindings,
    )


def _evidence_report(
    registration: OutputAssetRegistrationReport,
    envelope: GenerationEvidenceEnvelopeDTO | None = None,
) -> GenerationEvidenceValidationReport:
    return GenerationEvidenceValidationService().validate((envelope or _evidence_envelope(registration),))


def _request(report: OutputAssetRegistrationReport) -> StructuredGenerationRequestDTO:
    return (
        report.provider_invocation_report.secure_execution_input_resolution_report
        .authorized_execution_envelope_validation_report.execution_authorization_validation_report
        .readiness_report.input.request_validation_report.request
    )


def _bind(
    registration: OutputAssetRegistrationReport,
    evidence: GenerationEvidenceValidationReport,
    attempt_id: str = "attempt:001",
) -> AttemptToEvidenceBindingReport:
    return AttemptToEvidenceBindingService().validate(attempt_id, evidence, registration)


def _with_authorized_envelope(
    report: OutputAssetRegistrationReport,
    envelope: AuthorizedGenerationExecutionEnvelopeDTO,
) -> OutputAssetRegistrationReport:
    resolution = report.provider_invocation_report.secure_execution_input_resolution_report
    envelope_report = resolution.authorized_execution_envelope_validation_report.model_copy(
        update={"envelopes": (envelope,)}
    )
    updated_resolution = resolution.model_copy(
        update={"authorized_execution_envelope_validation_report": envelope_report}
    )
    invocation = report.provider_invocation_report.model_copy(
        update={"secure_execution_input_resolution_report": updated_resolution}
    )
    return report.model_copy(update={"provider_invocation_report": invocation})


def _with_readiness_provider(
    report: OutputAssetRegistrationReport, provider_reference: str
) -> OutputAssetRegistrationReport:
    resolution = report.provider_invocation_report.secure_execution_input_resolution_report
    envelope_report = resolution.authorized_execution_envelope_validation_report
    authorization = envelope_report.execution_authorization_validation_report
    readiness = authorization.readiness_report
    readiness_input = readiness.input.model_copy(update={"provider_reference": provider_reference})
    updated_readiness = readiness.model_copy(update={"input": readiness_input})
    updated_authorization = authorization.model_copy(update={"readiness_report": updated_readiness})
    updated_envelope_report = envelope_report.model_copy(
        update={"execution_authorization_validation_report": updated_authorization}
    )
    updated_resolution = resolution.model_copy(
        update={"authorized_execution_envelope_validation_report": updated_envelope_report}
    )
    invocation = report.provider_invocation_report.model_copy(
        update={"secure_execution_input_resolution_report": updated_resolution}
    )
    return report.model_copy(update={"provider_invocation_report": invocation})


def test_ready_evidence_is_bound_and_ready_without_mapping_configuration_provider() -> None:
    registration = _registered_report()
    evidence = _evidence_report(registration)

    report = _bind(registration, evidence)

    assert report.bound is True
    assert report.ready is True
    assert report.status == "ready"
    assert report.request_id == "request:001"
    assert evidence.envelopes[0].configuration.provider_id.value == "caller-provider-evidence"


@pytest.mark.parametrize("status", ("needs_evidence", "needs_review"))
def test_complete_binding_preserves_nonready_evidence_status(status: str) -> None:
    registration = _registered_report()
    evidence = _evidence_report(registration).model_copy(
        update={"status": status, "ready": False}
    )

    report = _bind(registration, evidence)

    assert report.bound is True
    assert report.ready is False
    assert report.status == status


@pytest.mark.parametrize(
    ("registration_update", "evidence_update", "code"),
    (
        ({"status": "blocked", "registered": False}, {}, "OUTPUT_REGISTRATION_NOT_REGISTERED"),
        (
            {"provider_invocation_report": None},
            {},
            "PROVIDER_INVOCATION_NOT_SUCCEEDED",
        ),
        ({}, {"status": "blocked", "ready": False}, "EVIDENCE_VALIDATION_BLOCKED"),
        ({}, {"envelopes": ()}, "EVIDENCE_ATTEMPT_NOT_FOUND"),
        ({"attempt_id": "attempt:other"}, {}, "ATTEMPT_BINDING_MISMATCH"),
        ({"provider_reference": "provider:other"}, {}, "PROVIDER_BINDING_MISMATCH"),
    ),
)
def test_direct_integrity_failures_block(
    registration_update: dict[str, object], evidence_update: dict[str, object], code: str
) -> None:
    registration = _registered_report()
    if "provider_invocation_report" in registration_update and (
        registration_update["provider_invocation_report"] is None
    ):
        invocation = registration.provider_invocation_report.model_copy(
            update={"status": "blocked", "succeeded": False}
        )
        registration_update = {"provider_invocation_report": invocation}
    changed_registration = registration.model_copy(update=registration_update)
    evidence = _evidence_report(registration).model_copy(update=evidence_update)

    report = _bind(changed_registration, evidence)

    assert report.bound is False
    assert report.ready is False
    assert report.status == "blocked"
    assert code in {item.code for item in report.findings}


def test_unambiguous_evidence_requirement_blocks_duplicate_attempts() -> None:
    registration = _registered_report()
    envelope = _evidence_envelope(registration)
    evidence = _evidence_report(registration).model_copy(update={"envelopes": (envelope, envelope)})

    report = _bind(registration, evidence)

    assert report.bound is False
    assert "EVIDENCE_ATTEMPT_NOT_UNIQUE" in {item.code for item in report.findings}


@pytest.mark.parametrize(
    ("kind", "code"),
    (
        ("request", "REQUEST_BINDING_MISMATCH"),
        ("input", "INPUT_EVIDENCE_BINDING_MISMATCH"),
        ("identity", "IDENTITY_BINDING_MISMATCH"),
        ("output", "OUTPUT_EVIDENCE_BINDING_MISMATCH"),
        ("provenance", "PROVENANCE_BINDING_MISMATCH"),
    ),
)
def test_exact_evidence_and_authorized_bindings_fail_closed(kind: str, code: str) -> None:
    registration = _registered_report()
    envelope = _evidence_envelope(registration)
    if kind == "request":
        authorized = (
            registration.provider_invocation_report.secure_execution_input_resolution_report
            .authorized_execution_envelope_validation_report.envelopes[0].model_copy(
                update={"request_id": "request:other"}
            )
        )
        registration = _with_authorized_envelope(registration, authorized)
        evidence = _evidence_report(registration, envelope)
    elif kind == "input":
        evidence = _evidence_report(
            registration,
            envelope.model_copy(update={"input": GenerationInputEvidenceDTO(input_reference="input:other")}),
        )
    elif kind == "identity":
        evidence = _evidence_report(
            registration,
            envelope.model_copy(update={"identity_bindings": ()}),
        )
    elif kind == "output":
        evidence = _evidence_report(
            registration,
            envelope.model_copy(
                update={"output": GenerationOutputEvidenceDTO(output_asset_id="asset:other")}
            ),
        )
    else:
        evidence = _evidence_report(
            registration,
            envelope.model_copy(update={"provenance_reference": "provenance:other"}),
        )

    report = _bind(registration, evidence)

    assert report.bound is False
    assert report.status == "blocked"
    assert code in {item.code for item in report.findings}


def test_execution_chain_provider_and_input_references_are_exact() -> None:
    registration = _registered_report()
    authorized = (
        registration.provider_invocation_report.secure_execution_input_resolution_report
        .authorized_execution_envelope_validation_report.envelopes[0]
    )
    provider_report = _bind(
        _with_readiness_provider(registration, "provider:other"), _evidence_report(registration)
    )
    input_report = _bind(
        _with_authorized_envelope(
            registration,
            authorized.model_copy(update={"input_reference": "input:other"}),
        ),
        _evidence_report(registration),
    )

    assert "PROVIDER_BINDING_MISMATCH" in {item.code for item in provider_report.findings}
    assert "INPUT_EVIDENCE_BINDING_MISMATCH" in {item.code for item in input_report.findings}


def test_dtos_are_frozen_closed_and_reports_redact_private_material() -> None:
    finding = AttemptToEvidenceBindingFindingDTO(code="TEST", status="blocked", message="test")
    with pytest.raises(ValidationError):
        finding.code = "changed"
    registration = _registered_report()
    evidence = _evidence_report(registration)
    report = _bind(registration, evidence)
    with pytest.raises(ValidationError):
        report.bound = False
    with pytest.raises(ValidationError):
        AttemptToEvidenceBindingReport(**report.model_dump(), raw_prompt="PRIVATE-PROMPT-MATERIAL")
    serialized = report.model_dump_json()
    for private_value in ("PRIVATE-PROMPT-MATERIAL", "PRIVATE-OUTPUT-BYTES", "raw_prompt"):
        assert private_value not in serialized


def test_reports_are_deterministic_and_do_not_modify_caller_reports() -> None:
    registration = _registered_report()
    evidence = _evidence_report(registration)
    registration_before = registration.model_dump(mode="json")
    evidence_before = evidence.model_dump(mode="json")

    first = _bind(registration, evidence)
    second = _bind(registration, evidence)

    assert registration.model_dump(mode="json") == registration_before
    assert evidence.model_dump(mode="json") == evidence_before
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_source_keeps_execution_persistence_and_public_exports_out() -> None:
    source = (
        ROOT / "src/manga_director/production/next_generation_attempt_to_evidence_binding.py"
    ).read_text(encoding="utf-8")
    for forbidden in (
        "GenerationEvidenceValidationService",
        "GenerationEvidenceEnvelopeDTO(",
        "manga_director.adapters",
        "manga_director.workflow",
        "manga_director.domain.state_machine",
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
    assert "next_generation_attempt_to_evidence_binding" not in production_init
    assert "next_generation_attempt_to_evidence_binding" not in root_init
