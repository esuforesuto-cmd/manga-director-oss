"""Focused contracts for internal redacted Failure Evidence projection."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from manga_director.production.next_generation_asset_registration import (
    AssetRegistrationRequest,
    AssetRegistrationRuntimeResult,
    OutputAssetRegistrationService,
)
from manga_director.production.next_generation_authorized_execution_envelope import (
    AuthorizedGenerationExecutionEnvelopeDTO,
    AuthorizedGenerationExecutionEnvelopeValidationService,
)
from manga_director.production.next_generation_execution_authorization import (
    ExecutionAuthorizationRecordDTO,
    ExecutionAuthorizationValidationService,
)
from manga_director.production.next_generation_failure_evidence import (
    FailureEvidenceFindingDTO,
    FailureEvidenceProjectionService,
    GenerationFailureEvidenceDTO,
)
from manga_director.production.next_generation_generation_evidence import (
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
    ProviderInvocationFindingDTO,
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


class _InputResolver:
    def __init__(self, snapshot: AuthoritativeExecutionInputSnapshot) -> None:
        self.snapshot = snapshot

    def resolve(self, input_reference: str) -> AuthoritativeExecutionInputSnapshot | None:
        return self.snapshot if input_reference == self.snapshot.input_reference else None


class _AssetResolver:
    def resolve(self, reference_asset_id: str) -> OpaqueReferenceAssetHandle | None:
        if reference_asset_id == "asset:reference:001":
            return OpaqueReferenceAssetHandle(reference_asset_id, object())
        return None


class _ProviderPort:
    provider_reference = "provider:local-a"

    def __init__(self, result: ProviderInvocationRuntimeResult | None = None, raises: bool = False) -> None:
        self.result = result
        self.raises = raises

    def invoke(self, materialized_input: object) -> ProviderInvocationRuntimeResult:
        del materialized_input
        if self.raises:
            raise RuntimeError("PRIVATE-EXCEPTION-DETAIL")
        assert self.result is not None
        return self.result


class _RegistrationPort:
    def __init__(self, mode: str) -> None:
        self.mode = mode

    def register(self, request: AssetRegistrationRequest) -> AssetRegistrationRuntimeResult | object:
        attempt_id = request.attempt_id
        provider_reference = request.provider_reference
        if self.mode == "invalid":
            return object()
        if self.mode == "conflict":
            return AssetRegistrationRuntimeResult(
                attempt_id=attempt_id,
                provider_reference=provider_reference,
                outcome="idempotency_conflict",
            )
        if self.mode == "failed":
            return AssetRegistrationRuntimeResult(
                attempt_id=attempt_id, provider_reference=provider_reference, outcome="failed"
            )
        return AssetRegistrationRuntimeResult(
            attempt_id=attempt_id,
            provider_reference=provider_reference,
            outcome="registered",
            output=GenerationOutputEvidenceDTO(output_asset_id="asset:generated:001"),
            durable_registration_confirmed=True,
        )


def _resolution() -> object:
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
    return SecureExecutionInputResolutionService().resolve(
        "attempt:001", envelope_report, _InputResolver(snapshot), _AssetResolver()
    )


def _invocation(
    outcome: str = "succeeded", *, failure_category: str | None = None, raises: bool = False
) -> ProviderInvocationOutcome:
    result = None
    if not raises:
        result = ProviderInvocationRuntimeResult(
            attempt_id="attempt:001",
            provider_reference="provider:local-a",
            outcome=outcome,  # type: ignore[arg-type]
            output_handle=OpaqueGeneratedOutputHandle("PRIVATE-OUTPUT") if outcome == "succeeded" else None,
            failure_category=failure_category,  # type: ignore[arg-type]
        )
    return ProviderInvocationService().invoke(
        "attempt:001", _resolution(), _ProviderPort(result=result, raises=raises)
    )


def _finding_report(code: str):
    invocation = _invocation()
    finding = ProviderInvocationFindingDTO(
        code=code,
        status="blocked",
        message="untrusted text is not used",
        attempt_id="attempt:001",
        provider_reference="provider:local-a",
    )
    return invocation.report.model_copy(
        update={"findings": (finding,), "status": "blocked", "succeeded": False}
    )


def _registration(mode: str):
    return OutputAssetRegistrationService().register(
        "attempt:001", _invocation(), _RegistrationPort(mode)
    )


def _with_request_value(invocation_report: object, **updates: str):
    resolution = invocation_report.secure_execution_input_resolution_report
    envelope_report = resolution.authorized_execution_envelope_validation_report
    authorization = envelope_report.execution_authorization_validation_report
    readiness = authorization.readiness_report
    readiness_input = readiness.input
    request_report = readiness_input.request_validation_report
    request = request_report.request.model_copy(update=updates)
    updated_request_report = request_report.model_copy(update={"request": request})
    updated_input = readiness_input.model_copy(
        update={"request_validation_report": updated_request_report}
    )
    updated_readiness = readiness.model_copy(update={"input": updated_input})
    updated_authorization = authorization.model_copy(update={"readiness_report": updated_readiness})
    updated_envelopes = envelope_report.model_copy(
        update={"execution_authorization_validation_report": updated_authorization}
    )
    updated_resolution = resolution.model_copy(
        update={"authorized_execution_envelope_validation_report": updated_envelopes}
    )
    return invocation_report.model_copy(update={"secure_execution_input_resolution_report": updated_resolution})


@pytest.mark.parametrize(
    ("code", "stage", "category"),
    (
        ("RESOLUTION_OUTCOME_NOT_READY", "input_resolution", "upstream_not_ready"),
        ("MATERIALIZED_INPUT_MISSING", "input_resolution", "input_materialization_unavailable"),
        ("PROVIDER_DECLARED_FAILURE", "provider_invocation", "provider_declared_failure"),
        ("PROVIDER_RUNTIME_FAILURE", "provider_invocation", "provider_runtime_failure"),
        ("PROVIDER_RESULT_INVALID", "provider_invocation", "invalid_provider_result"),
    ),
)
def test_provider_finding_mappings_are_projected(
    code: str, stage: str, category: str
) -> None:
    report = FailureEvidenceProjectionService().project("attempt:001", _finding_report(code))

    assert report.status == "recorded"
    assert report.recorded is True
    assert report.failure_evidence is not None
    assert report.failure_evidence.failure_stage == stage
    assert report.failure_evidence.failure_category == category
    assert report.failure_evidence.source_finding_code == code


@pytest.mark.parametrize(
    ("mode", "code", "stage", "category"),
    (
        ("failed", "OUTPUT_REGISTRATION_FAILED", "asset_registration", "registration_failure"),
        (
            "conflict",
            "OUTPUT_REGISTRATION_IDEMPOTENCY_CONFLICT",
            "asset_registration",
            "registration_idempotency_conflict",
        ),
        ("invalid", "OUTPUT_REGISTRATION_RESULT_INVALID", "asset_registration", "invalid_registration_result"),
    ),
)
def test_registration_finding_mappings_are_projected(
    mode: str, code: str, stage: str, category: str
) -> None:
    registration = _registration(mode)
    report = FailureEvidenceProjectionService().project(
        "attempt:001", registration.provider_invocation_report, registration
    )

    assert report.status == "recorded"
    assert report.failure_evidence is not None
    assert report.failure_evidence.source_finding_code == code
    assert report.failure_evidence.failure_stage == stage
    assert report.failure_evidence.failure_category == category


def test_missing_generated_output_handle_is_attempt_integrity_evidence() -> None:
    invocation = _invocation()
    registration = OutputAssetRegistrationService().register(
        "attempt:001", ProviderInvocationOutcome(report=invocation.report), _RegistrationPort("failed")
    )

    report = FailureEvidenceProjectionService().project("attempt:001", invocation.report, registration)

    assert report.status == "recorded"
    assert report.failure_evidence is not None
    assert report.failure_evidence.failure_stage == "attempt_integrity"
    assert report.failure_evidence.failure_category == "generated_output_handle_missing"


def test_provider_failure_prevents_registration_from_becoming_source() -> None:
    invocation = _invocation("provider_failed", failure_category="provider_declared_failure")
    later_registration = _registration("failed").model_copy(
        update={"provider_invocation_report": invocation.report}
    )

    report = FailureEvidenceProjectionService().project("attempt:001", invocation.report, later_registration)

    assert report.status == "recorded"
    assert report.failure_evidence is not None
    assert report.failure_evidence.source_finding_code == "PROVIDER_DECLARED_FAILURE"


def test_same_stage_conflict_fails_closed() -> None:
    invocation = _invocation()
    report = invocation.report.model_copy(
        update={
            "findings": (
                ProviderInvocationFindingDTO(
                    code="PROVIDER_DECLARED_FAILURE", status="blocked", message="ignored"
                ),
                ProviderInvocationFindingDTO(
                    code="PROVIDER_RUNTIME_FAILURE", status="blocked", message="ignored"
                ),
            ),
            "status": "blocked",
            "succeeded": False,
        }
    )

    outcome = FailureEvidenceProjectionService().project("attempt:001", report)

    assert outcome.status == "blocked"
    assert outcome.failure_evidence is None
    assert [item.code for item in outcome.findings] == ["CONFLICTING_FAILURE_SOURCE"]


def test_binding_mismatches_and_unknown_sources_fail_closed() -> None:
    service = FailureEvidenceProjectionService()
    mismatch = _finding_report("INVOCATION_ATTEMPT_MISMATCH")
    unknown = _finding_report("ARBITRARY_PROVIDER_PAYLOAD")

    mismatch_report = service.project("attempt:001", mismatch)
    unknown_report = service.project("attempt:001", unknown)

    assert mismatch_report.status == "blocked"
    assert mismatch_report.findings[0].code == "ATTEMPT_BINDING_MISMATCH"
    assert unknown_report.status == "blocked"
    assert unknown_report.findings[0].code == "UNSUPPORTED_FAILURE_SOURCE"


def test_attempt_and_provider_chain_mismatches_fail_closed() -> None:
    service = FailureEvidenceProjectionService()
    invocation = _invocation()

    attempt_report = service.project(
        "attempt:001", invocation.report.model_copy(update={"attempt_id": "attempt:other"})
    )
    provider_report = service.project(
        "attempt:001", invocation.report.model_copy(update={"provider_reference": "provider:other"})
    )

    assert "ATTEMPT_BINDING_MISMATCH" in {item.code for item in attempt_report.findings}
    assert "PROVIDER_BINDING_MISMATCH" in {item.code for item in provider_report.findings}


def test_request_provenance_and_registration_bindings_fail_closed() -> None:
    service = FailureEvidenceProjectionService()
    invocation = _invocation("provider_failed", failure_category="provider_declared_failure")
    request_mismatch = _with_request_value(invocation.report, request_id="request:other")
    invalid_provenance = _with_request_value(invocation.report, provenance_reference="C:/private")
    registration_mismatch = _registration("failed").model_copy(
        update={"provider_reference": "provider:other"}
    )

    request_report = service.project("attempt:001", request_mismatch)
    provenance_report = service.project("attempt:001", invalid_provenance)
    registration_report = service.project(
        "attempt:001", _invocation().report, registration_mismatch
    )

    assert "REQUEST_BINDING_MISMATCH" in {item.code for item in request_report.findings}
    assert "INVALID_LOGICAL_REFERENCE" in {item.code for item in provenance_report.findings}
    assert "REGISTRATION_REPORT_BINDING_MISMATCH" in {
        item.code for item in registration_report.findings
    }


def test_successful_attempt_is_excluded_and_missing_registration_needs_evidence() -> None:
    invocation = _invocation()
    registration = _registration("registered")
    service = FailureEvidenceProjectionService()

    successful = service.project("attempt:001", invocation.report, registration)
    incomplete = service.project("attempt:001", invocation.report)

    assert successful.status == "blocked"
    assert successful.failure_evidence is None
    assert successful.findings[0].code == "SUCCESSFUL_ATTEMPT_EXCLUDED"
    assert incomplete.status == "needs_evidence"
    assert incomplete.failure_evidence is None


def test_frozen_dtos_reject_extra_and_unsafe_references() -> None:
    with pytest.raises(ValidationError):
        GenerationFailureEvidenceDTO(
            attempt_id="attempt:001",
            request_id="request:001",
            provider_reference="provider:local-a",
            failure_stage="provider_invocation",
            failure_category="provider_runtime_failure",
            source_finding_code="PROVIDER_RUNTIME_FAILURE",
            provenance_reference="provenance:001",
            raw_prompt="PRIVATE-PROMPT-MATERIAL",
        )
    with pytest.raises(ValidationError):
        GenerationFailureEvidenceDTO(
            attempt_id="C:/private/attempt",
            request_id="request:001",
            provider_reference="provider:local-a",
            failure_stage="provider_invocation",
            failure_category="provider_runtime_failure",
            source_finding_code="PROVIDER_RUNTIME_FAILURE",
            provenance_reference="provenance:001",
        )
    with pytest.raises(ValidationError):
        FailureEvidenceFindingDTO(code="TEST", status="blocked", message="test", endpoint="x")


def test_projection_is_deterministic_non_mutating_and_redacted() -> None:
    invocation = _invocation(raises=True)
    before = invocation.report.model_dump(mode="json")
    service = FailureEvidenceProjectionService()

    first = service.project("attempt:001", invocation.report)
    second = service.project("attempt:001", invocation.report)
    serialized = first.model_dump_json()

    assert first == second
    assert invocation.report.model_dump(mode="json") == before
    assert first.failure_evidence is not None
    assert first.failure_evidence.provenance_reference == "provenance:001"
    for forbidden in (
        "PRIVATE-PROMPT-MATERIAL",
        "PRIVATE-OUTPUT",
        "PRIVATE-EXCEPTION-DETAIL",
        "opaque_value",
        "C:/",
        "://",
        "credential",
        "token",
        "endpoint",
    ):
        assert forbidden not in serialized
