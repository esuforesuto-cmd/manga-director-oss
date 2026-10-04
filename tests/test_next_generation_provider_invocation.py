"""Focused contracts for internal single-attempt provider invocation."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

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
    GenerationIdentityBindingDTO,
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
from manga_director.production.next_generation_provider_invocation import (
    OpaqueGeneratedOutputHandle,
    ProviderInvocationFindingDTO,
    ProviderInvocationReport,
    ProviderInvocationRuntimeResult,
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
    def __init__(self, snapshot: AuthoritativeExecutionInputSnapshot) -> None:
        self.snapshot = snapshot

    def resolve(self, input_reference: str) -> AuthoritativeExecutionInputSnapshot | None:
        return self.snapshot if input_reference == self.snapshot.input_reference else None


class InMemoryAssetResolver:
    def resolve(self, reference_asset_id: str) -> OpaqueReferenceAssetHandle | None:
        if reference_asset_id not in {"asset:001", "asset:002"}:
            return None
        return OpaqueReferenceAssetHandle(reference_asset_id, object())


class InMemoryProviderPort:
    def __init__(
        self,
        provider_reference: str,
        result: ProviderInvocationRuntimeResult | None = None,
        raises: bool = False,
    ) -> None:
        self._provider_reference = provider_reference
        self.result = result
        self.raises = raises
        self.calls: list[object] = []

    @property
    def provider_reference(self) -> str:
        return self._provider_reference

    def invoke(self, materialized_input: object) -> ProviderInvocationRuntimeResult:
        self.calls.append(materialized_input)
        if self.raises:
            raise RuntimeError("provider-private-detail: do-not-report")
        assert self.result is not None
        return self.result


def _resolution_outcome() -> SecureExecutionInputResolutionOutcome:
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
                reference_asset_ids=("asset:002", "asset:001"),
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
        required_reference_asset_ids=("asset:002", "asset:001"),
        raw_prompt_material="PRIVATE-PROMPT-MATERIAL",
    )
    return SecureExecutionInputResolutionService().resolve(
        "attempt:001", envelope_report, InMemoryInputResolver(snapshot), InMemoryAssetResolver()
    )


def _result(
    outcome: str = "succeeded",
    *,
    attempt_id: str = "attempt:001",
    provider_reference: str = "provider:local-a",
    output_handle: OpaqueGeneratedOutputHandle | None = None,
    failure_category: str | None = None,
) -> ProviderInvocationRuntimeResult:
    if output_handle is None and outcome == "succeeded":
        output_handle = OpaqueGeneratedOutputHandle(object())
    return ProviderInvocationRuntimeResult(
        attempt_id=attempt_id,
        provider_reference=provider_reference,
        outcome=outcome,  # type: ignore[arg-type]
        output_handle=output_handle,
        failure_category=failure_category,  # type: ignore[arg-type]
    )


def _invoke(
    resolution_outcome: SecureExecutionInputResolutionOutcome,
    port: InMemoryProviderPort,
    attempt_id: str = "attempt:001",
):
    return ProviderInvocationService().invoke(attempt_id, resolution_outcome, port)


def test_successful_exact_bound_invocation_calls_port_once_and_retains_no_prompt() -> None:
    resolution = _resolution_outcome()
    port = InMemoryProviderPort("provider:local-a", _result())

    outcome = _invoke(resolution, port)

    assert outcome.report.status == "succeeded"
    assert outcome.report.succeeded is True
    assert outcome.report.invocation_performed is True
    assert outcome.output_handle is not None
    assert len(port.calls) == 1
    serialized = outcome.report.model_dump_json()
    assert "PRIVATE-PROMPT-MATERIAL" not in serialized
    assert "output_asset_id" not in serialized


@pytest.mark.parametrize(
    ("resolution", "code"),
    (
        (
            lambda: SecureExecutionInputResolutionOutcome(
                report=_resolution_outcome().report.model_copy(
                    update={"status": "needs_review", "ready": False}
                )
            ),
            "RESOLUTION_OUTCOME_NOT_READY",
        ),
        (
            lambda: SecureExecutionInputResolutionOutcome(report=_resolution_outcome().report),
            "MATERIALIZED_INPUT_MISSING",
        ),
    ),
)
def test_preconditions_block_before_port_access(resolution, code: str) -> None:
    port = InMemoryProviderPort("provider:local-a", _result())

    outcome = _invoke(resolution(), port)

    assert [finding.code for finding in outcome.report.findings] == [code]
    assert outcome.report.invocation_performed is False
    assert port.calls == []


def test_explicit_attempt_and_port_provider_mismatches_block_before_invocation() -> None:
    resolution = _resolution_outcome()
    wrong_attempt_port = InMemoryProviderPort("provider:local-a", _result())
    wrong_provider_port = InMemoryProviderPort("provider:other", _result())

    attempt = _invoke(resolution, wrong_attempt_port, "attempt:other")
    provider = _invoke(resolution, wrong_provider_port)

    assert [finding.code for finding in attempt.report.findings] == ["INVOCATION_ATTEMPT_MISMATCH"]
    assert [finding.code for finding in provider.report.findings] == [
        "INVOCATION_PROVIDER_REFERENCE_MISMATCH"
    ]
    assert wrong_attempt_port.calls == []
    assert wrong_provider_port.calls == []


@pytest.mark.parametrize(
    ("result", "code"),
    (
        (_result(attempt_id="attempt:other"), "INVOCATION_ATTEMPT_MISMATCH"),
        (_result(provider_reference="provider:other"), "INVOCATION_PROVIDER_REFERENCE_MISMATCH"),
        (
            _result(
                outcome="provider_failed",
                output_handle=None,
                failure_category="provider_declared_failure",
            ),
            "PROVIDER_DECLARED_FAILURE",
        ),
        (
            _result(outcome="runtime_failed", output_handle=None, failure_category="runtime_failure"),
            "PROVIDER_RUNTIME_FAILURE",
        ),
    ),
)
def test_post_invocation_results_stop_after_one_port_call(
    result: ProviderInvocationRuntimeResult, code: str
) -> None:
    port = InMemoryProviderPort("provider:local-a", result)

    outcome = _invoke(_resolution_outcome(), port)

    assert [finding.code for finding in outcome.report.findings] == [code]
    assert outcome.report.status == "blocked"
    assert outcome.report.invocation_performed is True
    assert outcome.output_handle is None
    assert len(port.calls) == 1


@pytest.mark.parametrize(
    "result",
    (
        ProviderInvocationRuntimeResult(
            attempt_id="attempt:001",
            provider_reference="provider:local-a",
            outcome="succeeded",
        ),
        _result(failure_category="provider_declared_failure"),
        _result(
            outcome="provider_failed",
            output_handle=OpaqueGeneratedOutputHandle(object()),
            failure_category="provider_declared_failure",
        ),
        _result(outcome="runtime_failed", output_handle=None, failure_category=None),
    ),
)
def test_invalid_result_combinations_are_blocked(result: ProviderInvocationRuntimeResult) -> None:
    port = InMemoryProviderPort("provider:local-a", result)

    outcome = _invoke(_resolution_outcome(), port)

    assert [finding.code for finding in outcome.report.findings] == ["PROVIDER_RESULT_INVALID"]
    assert len(port.calls) == 1


def test_provider_exception_is_redacted_and_stops_after_one_call() -> None:
    port = InMemoryProviderPort("provider:local-a", raises=True)

    outcome = _invoke(_resolution_outcome(), port)

    assert [finding.code for finding in outcome.report.findings] == ["PROVIDER_RUNTIME_FAILURE"]
    assert "provider-private-detail" not in outcome.report.model_dump_json()
    assert all("provider-private-detail" not in finding.model_dump_json() for finding in outcome.report.findings)
    assert len(port.calls) == 1


def test_dtos_are_frozen_closed_and_opaque_output_is_runtime_only() -> None:
    finding = ProviderInvocationFindingDTO(code="TEST", status="blocked", message="test")
    with pytest.raises(ValidationError):
        finding.code = "changed"
    with pytest.raises(ValidationError):
        ProviderInvocationFindingDTO(code="TEST", status="blocked", message="test", raw_prompt="x")

    outcome = _invoke(_resolution_outcome(), InMemoryProviderPort("provider:local-a", _result()))
    with pytest.raises(ValidationError):
        outcome.report.succeeded = False
    with pytest.raises(ValidationError):
        ProviderInvocationReport(**outcome.report.model_dump(), output_asset_id="asset:001")
    assert outcome.output_handle is not None
    assert "opaque_value" not in repr(outcome.output_handle)


def test_reports_are_deterministic_and_inputs_are_not_mutated() -> None:
    resolution = _resolution_outcome()
    before = resolution.report.model_dump(mode="json")

    first = _invoke(resolution, InMemoryProviderPort("provider:local-a", _result()))
    second = _invoke(resolution, InMemoryProviderPort("provider:local-a", _result()))

    assert resolution.report.model_dump(mode="json") == before
    assert first.report.model_dump(mode="json") == second.report.model_dump(mode="json")


def test_source_keeps_real_provider_evidence_credentials_and_public_exports_out() -> None:
    source = (
        ROOT / "src/manga_director/production/next_generation_provider_invocation.py"
    ).read_text(encoding="utf-8")
    for forbidden in (
        "manga_director.adapters",
        "manga_director.agents",
        "manga_director.prompting",
        "manga_director.workflow",
        "manga_director.domain.state_machine",
        "CredentialManager",
        "GenerationEvidenceEnvelopeDTO",
        "GenerationConfigurationEvidenceDTO",
        ".generate(",
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
    assert "next_generation_provider_invocation" not in production_init
    assert "next_generation_provider_invocation" not in root_init
