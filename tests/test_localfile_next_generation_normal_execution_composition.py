"""Focused fake-only tests for LocalFile Next Generation normal composition."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState, StateMachine
from manga_director.events import MemoryEventBus
from manga_director.production import future_real_delivery_r25_trusted_pairing as r25_pairing
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
    GenerationInputEvidenceDTO,
)
from manga_director.production.next_generation_normal_execution_attempt import (
    NormalExecutionAttemptReservationDTO,
)
from manga_director.production.next_generation_openai_output_asset_registration import (
    OpenAIAssetOwnerSinkBridge,
    OpenAIOutputAssetRegistrationAdapter,
)
from manga_director.production.next_generation_openai_provider_adapter import (
    OpenAIInMemoryGeneratedImageMaterial,
)
from manga_director.production.next_generation_pre_execution_readiness import (
    PreExecutionReadinessInputDTO,
    PreExecutionReadinessService,
)
from manga_director.production.next_generation_provider_capability_negotiation import (
    ProviderCapabilityDeclarationDTO,
    ProviderCapabilityNegotiationService,
)
from manga_director.production.next_generation_provider_configuration import (
    AuthoritativeProviderConfigurationSnapshot,
    ProviderConfigurationNormalizationService,
)
from manga_director.production.next_generation_provider_invocation import (
    OpaqueGeneratedOutputHandle,
    ProviderInvocationRuntimeResult,
)
from manga_director.production.next_generation_provider_output_configuration import (
    ProviderOutputConfigurationBindingDTO,
    ProviderOutputConfigurationBindingService,
)
from manga_director.production.next_generation_secure_execution_input_resolution import (
    AuthoritativeExecutionInputSnapshot,
    OpaqueReferenceAssetHandle,
)
from manga_director.production.next_generation_structured_generation_request import (
    GenerationProductionProfileDTO,
    StructuredGenerationRequestDTO,
    StructuredGenerationRequestValidationService,
)
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.workflow.localfile_next_generation_normal_execution_composition import (
    FakeNormalExecutionRuntimeEdges,
    LocalFileNormalExecutionFacts,
    build_localfile_fake_normal_execution_composition,
)

_PNG_BYTES = b"\x89PNG\r\n\x1a\nFAKE-ONLY-PRIVATE-OUTPUT"
_REAL_DELIVERY_ARTIFACT_NAMES = frozenset(
    {
        "_post_cas_application_attestations",
        "_post_lts_real_asset_delivery",
        "_post_lts_real_delivery_binding",
        "_r30_pre_cas_ledger_provenance",
        "post-cas-application-attestations.sqlite3",
        "r30-pre-cas-ledger-provenance.sqlite3",
        "real-asset-delivery.sqlite3",
        "real-delivery-binding.sqlite3",
    }
)


class _InputResolver:
    def __init__(self, *, input_reference: str, intent_reference: str) -> None:
        self._input_reference = input_reference
        self._intent_reference = intent_reference
        self.calls = 0

    def resolve(self, input_reference: str) -> AuthoritativeExecutionInputSnapshot | None:
        self.calls += 1
        if input_reference != self._input_reference:
            return None
        return AuthoritativeExecutionInputSnapshot.from_prompt_material(
            input_reference=input_reference,
            generation_intent_reference=self._intent_reference,
            raw_prompt_material="fake-only runtime prompt",
        )


class _ReferenceResolver:
    def __init__(self) -> None:
        self.calls = 0

    def resolve(self, reference_asset_id: str) -> OpaqueReferenceAssetHandle | None:
        self.calls += 1
        return OpaqueReferenceAssetHandle(reference_asset_id)


class _FakeProvider:
    provider_reference = "provider:openai"

    def __init__(self, *, outcome: str = "succeeded") -> None:
        self._outcome = outcome
        self.calls = 0

    def invoke(  # type: ignore[no-untyped-def]
        self, materialized_input
    ) -> ProviderInvocationRuntimeResult:
        self.calls += 1
        if self._outcome != "succeeded":
            return ProviderInvocationRuntimeResult(
                attempt_id=materialized_input.attempt_id,
                provider_reference=self.provider_reference,
                outcome="runtime_failed",
                failure_category="runtime_failure",
            )
        return ProviderInvocationRuntimeResult(
            attempt_id=materialized_input.attempt_id,
            provider_reference=self.provider_reference,
            outcome="succeeded",
            output_handle=OpaqueGeneratedOutputHandle(
                OpenAIInMemoryGeneratedImageMaterial(image_bytes=_PNG_BYTES)
            ),
        )


def _known(value: str) -> EvidenceValueDTO:
    return EvidenceValueDTO(availability="known", value=value)


def _repository(tmp_path: Path, *, pages: tuple[int, ...] = (1,)) -> LocalFileRepository:
    repository = LocalFileRepository(tmp_path)
    repository.save(
        Project(
            id="project_localfile",
            title="LocalFile Next Generation",
            pages=[
                Page(
                    page_number=page_number,
                    state=PageState.PROMPT_BUILT,
                    page_design={},
                    review={},
                    storyboard={},
                    prompt={"prompt_markdown": "legacy prompt is not used by the fake runtime"},
                )
                for page_number in pages
            ],
        )
    )
    return repository


def _runtime(
    *, provider: _FakeProvider | None = None
) -> tuple[FakeNormalExecutionRuntimeEdges, _FakeProvider]:
    fake_provider = provider or _FakeProvider()
    resolver = _InputResolver(
        input_reference="input:localfile",
        intent_reference="intent:localfile",
    )
    edges = FakeNormalExecutionRuntimeEdges(
        fake_only=True,
        generation_input_resolver=resolver,
        reference_asset_resolver=_ReferenceResolver(),
        provider_invocation_port=fake_provider,
        asset_registration_port_factory=lambda owner: OpenAIOutputAssetRegistrationAdapter(
            OpenAIAssetOwnerSinkBridge(owner)
        ),
    )
    return edges, fake_provider


def _facts(
    *,
    attempt_id: str = "attempt:localfile:001",
    request_id: str = "request:localfile:001",
    page_id: str = "1",
    target: str = "target:localfile:001",
) -> LocalFileNormalExecutionFacts:
    provider = "provider:openai"
    profile = GenerationProductionProfileDTO(
        profile_id="profile:localfile", profile_version="v1"
    )
    structured_request = StructuredGenerationRequestDTO(
        request_id=request_id,
        target_page_reference=target,
        generation_intent_reference="intent:localfile",
        input=GenerationInputEvidenceDTO(input_reference="input:localfile"),
        capability_requirements=(),
        provenance_reference="provenance:localfile",
        profile_id=profile.profile_id,
        profile_version=profile.profile_version,
    )
    structured = StructuredGenerationRequestValidationService().validate(
        structured_request, profile
    )
    capability = ProviderCapabilityNegotiationService().validate(
        (), ProviderCapabilityDeclarationDTO(provider_reference=provider, capability_states=())
    )
    readiness = PreExecutionReadinessService().validate(
        PreExecutionReadinessInputDTO(
            request_validation_report=structured,
            capability_negotiation_report=capability,
            provider_reference=provider,
        )
    )
    execution = ExecutionAuthorizationValidationService().validate(
        readiness,
        (
            ExecutionAuthorizationRecordDTO(
                authorization_id="authorization:localfile",
                authorizer_id="human:localfile",
                authorized_at=datetime(2026, 8, 23, 12, 0, tzinfo=UTC),
                request_id=request_id,
                provider_reference=provider,
            ),
        ),
    )
    envelope = AuthorizedGenerationExecutionEnvelopeDTO(
        attempt_id=attempt_id,
        request_id=request_id,
        provider_reference=provider,
        authorization_ids=("authorization:localfile",),
        profile_id=profile.profile_id,
        profile_version=profile.profile_version,
        generation_intent_reference=structured_request.generation_intent_reference,
        input_reference=structured_request.input.input_reference,
    )
    authorized_envelope = AuthorizedGenerationExecutionEnvelopeValidationService().validate(
        (envelope,), execution
    )
    configuration = ProviderConfigurationNormalizationService().normalize(
        attempt_id,
        AuthoritativeProviderConfigurationSnapshot(
            attempt_id=attempt_id,
            provider_reference=provider,
            profile_id=profile.profile_id,
            profile_version=profile.profile_version,
            provider_id=_known("openai"),
            model_id=_known("gpt-image-2-2026-04-21"),
            model_version=_known("model-version:localfile"),
            workflow_id=_known("workflow:localfile"),
            workflow_version=_known("workflow-version:localfile"),
            requested_seed=_known("42"),
        ),
        authorized_envelope,
    )
    output_configuration = ProviderOutputConfigurationBindingService().validate(
        ProviderOutputConfigurationBindingDTO(
            attempt_id=attempt_id,
            provider_reference=provider,
            profile_id=profile.profile_id,
            profile_version=profile.profile_version,
            model_id="gpt-image-2-2026-04-21",
            output_size="1536x1024",
            output_quality="low",
        ),
        configuration,
    )
    reservation = NormalExecutionAttemptReservationDTO(
        attempt_id=attempt_id,
        request_id=request_id,
        project_id="project_localfile",
        page_id=page_id,
        target_page_reference=target,
        provider_reference=provider,
        execution_fingerprint="f" * 64,
    )
    authorization = WorkflowApplicationAuthorizationDTO(
        authorization_id=f"workflow-authorization:{attempt_id}",
        authorizer_id="human:workflow",
        authorized_at=datetime(2026, 8, 23, 12, 1, tzinfo=UTC),
        attempt_id=attempt_id,
        provider_reference=provider,
        project_id="project_localfile",
        page_id=page_id,
        target_page_reference=target,
        source_state="PromptBuilt",
        target_state="Generated",
    )
    return LocalFileNormalExecutionFacts(
        reservation=reservation,
        structured_request_validation_report=structured,
        capability_negotiation_report=capability,
        pre_execution_readiness_report=readiness,
        execution_authorization_validation_report=execution,
        authorized_execution_envelope_validation_report=authorized_envelope,
        workflow_application_authorization=authorization,
        page_mapping=AuthoritativeWorkflowPageMappingDTO(
            project_id="project_localfile", page_id=page_id, target_page_reference=target
        ),
        observed_at=datetime(2026, 8, 23, 12, 2, tzinfo=UTC),
        provider_configuration_report=configuration,
        provider_output_configuration_report=output_configuration,
    )


def _build(repository: LocalFileRepository, edges: FakeNormalExecutionRuntimeEdges):
    return build_localfile_fake_normal_execution_composition(
        repository, StateMachine(), MemoryEventBus(), edges
    )


def _real_delivery_artifacts(repository: LocalFileRepository) -> tuple[Path, ...]:
    return tuple(
        sorted(
            (
                path.relative_to(repository._root)
                for path in repository._root.rglob("*")
                if path.name in _REAL_DELIVERY_ARTIFACT_NAMES
            ),
            key=lambda path: path.as_posix(),
        )
    )


def test_private_root_layout_is_deterministic_absolute_and_separate(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    edges, _provider = _runtime()
    composition = _build(repository, edges)
    root = repository._next_generation_normal_execution_owner_root()

    assert (
        root.is_absolute()
        and root == repository._next_generation_normal_execution_owner_root()
    )
    assert composition._attempt_store._root == root / "attempts"
    assert composition._evidence_store._root == root / "evidence"
    assert composition._asset_owner._root == root / "assets"
    assert (
        len(
            {
                composition._attempt_store._root,
                composition._evidence_store._root,
                composition._asset_owner._root,
            }
        )
        == 3
    )
    assert (
        root.parent / "_workflow_application_ledger"
        == repository._workflow_application_ledger_owner_root()
    )
    assert repository._workflow_application_ledger_owner_root() != root


def test_fake_only_construction_never_creates_real_delivery_artifacts(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    edges, _provider = _runtime()
    registrations = len(r25_pairing._PAIRING_REGISTRY)

    composition = _build(repository, edges)

    assert composition._external_generation.external_application._r25_localfile_composition is None
    assert len(r25_pairing._PAIRING_REGISTRY) == registrations
    assert _real_delivery_artifacts(repository) == ()


def test_repeated_fake_only_construction_never_creates_real_delivery_artifacts(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    edges, _provider = _runtime()
    registrations = len(r25_pairing._PAIRING_REGISTRY)

    _build(repository, edges)
    _build(repository, edges)

    assert len(r25_pairing._PAIRING_REGISTRY) == registrations
    assert _real_delivery_artifacts(repository) == ()


def test_complete_fake_chain_reopens_exact_state_and_never_reinvokes_provider(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    edges, provider = _runtime()
    first = _build(repository, edges)
    facts = _facts()

    result = first.execute(facts)

    assert result.status == "completed" and result.completed is True
    assert provider.calls == 1
    assert repository.load("project_localfile").page(1).state == PageState.GENERATED
    assert first._evidence_store.lookup(facts.reservation.attempt_id).outcome == "found"
    assert _real_delivery_artifacts(repository) == ()
    asset_files = tuple((first._asset_owner._root / "assets").iterdir())
    assert len(asset_files) == 1 and asset_files[0].read_bytes() == _PNG_BYTES

    replay_edges, replay_provider = _runtime()
    reopened = _build(repository, replay_edges)
    replay = reopened.execute(facts)

    assert replay.status == "blocked" and replay_provider.calls == 0
    assert reopened._attempt_store.lookup(facts.reservation.attempt_id) is not None
    assert reopened._evidence_store.lookup(facts.reservation.attempt_id).outcome == "found"
    assert tuple((reopened._asset_owner._root / "assets").iterdir())[0].read_bytes() == _PNG_BYTES


def test_provider_started_reopen_and_same_page_competitor_fail_closed(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    failing_edges, failing_provider = _runtime(provider=_FakeProvider(outcome="runtime_failed"))
    first = _build(repository, failing_edges)
    stranded_facts = _facts()

    partial = first.execute(stranded_facts)

    assert partial.status == "partial" and failing_provider.calls == 1
    assert (
        first._attempt_store.lookup(stranded_facts.reservation.attempt_id).state
        == "PROVIDER_STARTED"
    )

    reopened_edges, reopened_provider = _runtime()
    reopened = _build(repository, reopened_edges)
    same_attempt = reopened.execute(stranded_facts)
    competing = reopened.execute(
        _facts(attempt_id="attempt:localfile:002", request_id="request:localfile:002")
    )

    assert same_attempt.status == "partial"
    assert competing.status == "blocked"
    assert reopened_provider.calls == 0


def test_different_eligible_page_can_execute_independently(tmp_path: Path) -> None:
    repository = _repository(tmp_path, pages=(1, 2))
    edges, provider = _runtime()
    composition = _build(repository, edges)

    first = composition.execute(_facts())
    second = composition.execute(
        _facts(
            attempt_id="attempt:localfile:page-2",
            request_id="request:localfile:page-2",
            page_id="2",
            target="target:localfile:002",
        )
    )

    assert first.completed is True and second.completed is True
    assert provider.calls == 2
    assert repository.load("project_localfile").page(2).state == PageState.GENERATED


def test_fake_only_boundary_rejects_non_fake_runtime_before_durable_work(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    edges, _provider = _runtime()
    invalid = FakeNormalExecutionRuntimeEdges(
        fake_only=False,  # type: ignore[arg-type]
        generation_input_resolver=edges.generation_input_resolver,
        reference_asset_resolver=edges.reference_asset_resolver,
        provider_invocation_port=edges.provider_invocation_port,
        asset_registration_port_factory=edges.asset_registration_port_factory,
    )

    with pytest.raises(ValueError, match="fake-only runtime edges are required"):
        _build(repository, invalid)

    assert not repository._next_generation_normal_execution_owner_root().exists()


def test_private_owners_use_distinct_sidecars_without_ledger_collision(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    edges, _provider = _runtime()
    composition = _build(repository, edges)

    composition.execute(_facts())
    root = repository._next_generation_normal_execution_owner_root()
    with sqlite3.connect(composition._attempt_store._database) as connection:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM normal_execution_attempts"
            ).fetchone()[0]
            == 1
        )
    assert (root / "evidence" / "generation-evidence.sqlite3").is_file()
    assert (root / "assets" / "registry" / "asset-owner.sqlite3").is_file()
    assert (
        repository._workflow_application_ledger_owner_root()
        / "workflow-application-ledger.sqlite3"
    ).is_file()
