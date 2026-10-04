"""Focused canonical normal-path R25 materialization tests."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import pytest

from manga_director.domain.events import EventType, WorkflowEvent
from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState, StateMachine
from manga_director.events import MemoryEventBus
from manga_director.production import (
    future_real_delivery_i02_real_asset_delivery_journal as i02_journal,
)
from manga_director.production import (
    future_real_delivery_i02a_protocol as i02_protocol,
)
from manga_director.production.future_real_delivery_r18_construction import (
    PrivateR18CompositionFactoryV1,
)
from manga_director.production.future_real_delivery_r25_attestation import (
    _canonical_r25_record_v1,
)
from manga_director.production.future_real_delivery_r25_trusted_pairing import (
    _r27_application_binding_identity,
    _r27_application_binding_json,
)
from manga_director.production.next_generation_durable_evidence_workflow_binding import (
    DurableEvidenceWorkflowBindingReport,
    WorkflowApplicationAuthorizationDTO,
)
from manga_director.production.next_generation_generation_evidence import (
    EvidenceValueDTO,
    GenerationConfigurationEvidenceDTO,
    GenerationEvidenceEnvelopeDTO,
    GenerationInputEvidenceDTO,
    GenerationOutputEvidenceDTO,
)
from manga_director.production.next_generation_generation_evidence_persistence import (
    GenerationEvidenceStoreWriteRequest,
    LocalGenerationEvidenceStore,
)
from manga_director.production.next_generation_local_durable_asset_owner import (
    OwnerRegistrationMaterial,
)
from manga_director.production.next_generation_workflow_application_ledger import (
    WorkflowApplicationLedgerBindingDTO,
    _canonical_payload,
)
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.workflow import localfile_external_generated_application as external_application
from manga_director.workflow.localfile_external_generated_application import (
    _descriptor,
    build_localfile_external_generation_composition,
)

_IMAGE_BYTES = b"\x89PNG\r\n\x1a\n" + b"r25-normal" * 32
_IMAGE_DIGEST = hashlib.sha256(_IMAGE_BYTES).hexdigest()
_PROJECT_ID = "project-r25-normal"
_ATTEMPT_ID = "attempt:r25:normal"
_PROVIDER = "provider:r25:normal"
_OUTPUT = "output:r25:normal"
_TARGET = "target:r25:normal"


def _known(value: str) -> EvidenceValueDTO:
    return EvidenceValueDTO(availability="known", value=value)


def _binding_input() -> i02_journal._DeliveryBindingInputV1:
    return i02_journal._DeliveryBindingInputV1(
        attempt_id=_ATTEMPT_ID,
        project_id=_PROJECT_ID,
        page_id="1",
        target_page_reference=_TARGET,
        provider_reference=_PROVIDER,
        dispatch_identity="dispatch:r25:normal",
        idempotency_identity="idempotency:r25:normal",
        submission_receipt_identity="receipt:r25:normal",
        logical_output_id=_OUTPUT,
        canonical_result_identity=i02_journal._canonical_result_identity_v1(
            attempt_id=_ATTEMPT_ID,
            project_id=_PROJECT_ID,
            page_id="1",
            target_page_reference=_TARGET,
            provider_reference=_PROVIDER,
            dispatch_identity="dispatch:r25:normal",
            idempotency_identity="idempotency:r25:normal",
            submission_receipt_identity="receipt:r25:normal",
            logical_output_id=_OUTPUT,
            asset_sha256=_IMAGE_DIGEST,
            expected_byte_length=len(_IMAGE_BYTES),
        ),
        asset_sha256=_IMAGE_DIGEST,
        expected_byte_length=len(_IMAGE_BYTES),
    )


def _report() -> DurableEvidenceWorkflowBindingReport:
    return DurableEvidenceWorkflowBindingReport.model_validate(
        {
            "attempt_id": _ATTEMPT_ID,
            "provider_reference": _PROVIDER,
            "output_asset_id": _OUTPUT,
            "project_id": _PROJECT_ID,
            "page_id": "1",
            "target_page_reference": _TARGET,
            "status": "eligible",
            "eligible": True,
        }
    )


def _authorization() -> WorkflowApplicationAuthorizationDTO:
    return WorkflowApplicationAuthorizationDTO.model_validate(
        {
            "authorization_id": "authorization:r25:normal",
            "authorizer_id": "human:r25:normal",
            "authorized_at": datetime(2026, 9, 4, tzinfo=UTC),
            "attempt_id": _ATTEMPT_ID,
            "provider_reference": _PROVIDER,
            "project_id": _PROJECT_ID,
            "page_id": "1",
            "target_page_reference": _TARGET,
            "source_state": "PromptBuilt",
            "target_state": "Generated",
        }
    )


def _prepare_completed_r18_lineage(repository: LocalFileRepository) -> None:
    factory = PrivateR18CompositionFactoryV1()
    r18_composition = factory._create_for_existing_repository_v1(repository)
    authority = factory.construct_authority(r18_composition)
    binding = _binding_input()
    r18_composition.journal._begin_delivery_v1(binding)
    r18_composition.journal._record_bytes_validated_v1(
        binding.expected_byte_length, binding.asset_sha256, "image/png"
    )
    registration = r18_composition.owner.register(
        OwnerRegistrationMaterial(
            attempt_id=binding.attempt_id,
            provider_reference=binding.provider_reference,
            image_bytes=_IMAGE_BYTES,
        )
    )
    assert registration.outcome == "registered"
    r18_composition.journal._record_authenticated_asset_registered_v1(registration)
    state = i02_protocol._create_isolated_test_protocol_state_v1()
    bootstrap = state.take_bootstrap()
    bootstrap._register_production_journal_class_once_v1(i02_journal.PrivateRealAssetDeliveryJournal)
    journal_peer, verifier_peer = state.create_pair(r18_composition.journal)
    request = journal_peer._issue_registered_owner_verification_request_v1()
    completion = verifier_peer._consume_request_and_issue_completion_v1(
        request,
        i02_protocol._VerifiedOwnerAssetFactsV1(
            assets_root_identity=("assets", 1, 2),
            final_file_identity=("asset.png", 1, 3, binding.expected_byte_length),
            verified_sha256=binding.asset_sha256,
            verified_byte_length=binding.expected_byte_length,
            verified_media_type="image/png",
            owner_attempt_id=binding.attempt_id,
            owner_provider_reference=binding.provider_reference,
            owner_digest=binding.asset_sha256,
            owner_storage_name="a" * 32 + ".png",
        ),
    )
    assert verifier_peer._consume_completion_and_call_journal_v1(completion) is (
        i02_protocol._JournalCompletionCallbackResultV1.COMMITTED
    )
    evidence = GenerationEvidenceEnvelopeDTO(
        attempt_id=_ATTEMPT_ID,
        observed_at=datetime(2026, 9, 4, tzinfo=UTC),
        provenance_reference="provenance:r25:normal",
        input=GenerationInputEvidenceDTO(input_reference="input:r25:normal"),
        output=GenerationOutputEvidenceDTO(
            output_asset_id=_OUTPUT,
            output_content_hash=_known(_IMAGE_DIGEST),
            media_type="image/png",
        ),
        configuration=GenerationConfigurationEvidenceDTO(
            provider_id=_known(_PROVIDER),
            model_id=_known("model:r25:normal"),
            model_version=_known("v1"),
            workflow_id=_known("workflow:r25:normal"),
            workflow_version=_known("v1"),
            seed=_known("42"),
        ),
    )
    evidence_store = LocalGenerationEvidenceStore(
        repository._next_generation_normal_execution_owner_root() / "evidence"
    )
    persisted = evidence_store.persist(
        GenerationEvidenceStoreWriteRequest(
            attempt_id=_ATTEMPT_ID,
            provider_reference=_PROVIDER,
            evidence_status="ready",
            generation_evidence=evidence,
        )
    )
    assert persisted.outcome == "persisted"
    row = sqlite3.connect(evidence_store._database_path).execute(
        "SELECT payload_digest FROM generation_evidence WHERE attempt_id = ?", (_ATTEMPT_ID,)
    ).fetchone()
    assert row is not None
    authority._create_exact_v1(binding.delivery_identity)


def _prepared_repository(tmp_path: Path) -> LocalFileRepository:
    repository = LocalFileRepository(tmp_path)
    repository.save(
        Project(
            id=_PROJECT_ID,
            title="R25 normal",
            pages=[
                Page(
                    page_number=1,
                    state=PageState.PROMPT_BUILT,
                    page_design={},
                    review={},
                    storyboard={"panels": [{"id": "panel:r25:normal"}]},
                    prompt={"positive": "R25 normal page"},
                    metadata={"future_generation_target_reference": _TARGET},
                )
            ],
        )
    )
    _prepare_completed_r18_lineage(repository)
    return repository


def _repository_without_r25_predecessors(tmp_path: Path) -> LocalFileRepository:
    """Create only the authoritative page; no R18/R20/R27 predecessor exists."""

    repository = LocalFileRepository(tmp_path)
    repository.save(
        Project(
            id=_PROJECT_ID,
            title="R25 missing predecessor",
            pages=[
                Page(
                    page_number=1,
                    state=PageState.PROMPT_BUILT,
                    page_design={},
                    review={},
                    storyboard={"panels": [{"id": "panel:r25:normal"}]},
                    prompt={"positive": "R25 normal page"},
                    metadata={"future_generation_target_reference": _TARGET},
                )
            ],
        )
    )
    return repository


def _generated_repository_without_historical_predecessor(tmp_path: Path) -> LocalFileRepository:
    repository = LocalFileRepository(tmp_path)
    repository.save(
        Project(
            id=_PROJECT_ID,
            title="R30 absent restart",
            pages=[
                Page(
                    page_number=1,
                    state=PageState.GENERATED,
                    page_design={},
                    review={},
                    storyboard={"panels": [{"id": "panel:r30:absent"}]},
                    prompt={"positive": "R30 absent restart"},
                    image={"output_asset_id": _OUTPUT},
                    metadata={"future_generation_target_reference": _TARGET},
                    artifacts={PageState.GENERATED.value: _OUTPUT},
                )
            ],
        )
    )
    return repository


def test_canonical_normal_path_materializes_r25_before_existing_continuation(tmp_path: Path) -> None:
    repository = _prepared_repository(tmp_path)
    composition = build_localfile_external_generation_composition(
        repository, StateMachine(), MemoryEventBus()
    )

    result = composition.external_application.apply(_report(), _authorization())

    assert result.status == "application_applied_event_published"
    r25 = composition.external_application._r25_localfile_composition
    assert r25 is not None
    replay = composition.ledger_service.prepare(
        _report(), _authorization(), composition.ledger_store
    )
    assert replay.binding is not None
    record = r25._r25_store._replay_post_cas_attestation_exact_v1(
        _r27_application_binding_identity(replay.binding)
    )
    assert record is not None
    with sqlite3.connect(r25._r30_provenance_store._database_path) as connection:
        provenance_row = connection.execute(
            "SELECT application_binding_identity, expected_pre_cas_revision "
            "FROM r30_pre_cas_ledger_provenance WHERE attempt_id = ?",
            (_ATTEMPT_ID,),
        ).fetchone()
    with sqlite3.connect(composition.ledger_store._database_path) as connection:
        ledger_row = connection.execute(
            "SELECT lifecycle FROM workflow_application_ledger WHERE attempt_id = ?",
            (_ATTEMPT_ID,),
        ).fetchone()
    with sqlite3.connect(composition.receipt_store._database_path) as connection:
        receipt_row = connection.execute(
            "SELECT attempt_id FROM durable_application_commit_receipts WHERE attempt_id = ?",
            (_ATTEMPT_ID,),
        ).fetchone()
    replay_result = composition.external_application.apply(_report(), _authorization())
    with sqlite3.connect(r25._r25_store._database_path) as connection:
        r25_count = connection.execute(
            "SELECT COUNT(*) FROM post_cas_application_attestations"
        ).fetchone()
    assert ledger_row == ("applied",)
    assert receipt_row == (_ATTEMPT_ID,)
    assert provenance_row == (_r27_application_binding_identity(replay.binding), 1)
    assert replay_result.status == "application_replay_confirmed"
    assert replay_result.event_published is False
    assert r25_count == (1,)


def test_missing_r25_predecessor_blocks_receipt_ledger_continuation_and_event(tmp_path: Path) -> None:
    repository = _repository_without_r25_predecessors(tmp_path)
    event_bus = MemoryEventBus()
    composition = build_localfile_external_generation_composition(
        repository, StateMachine(), event_bus
    )

    result = composition.external_application.apply(_report(), _authorization())

    assert result.status == "application_not_applied"
    assert result.code == "EXTERNAL_APPLICATION_R25_MATERIALIZATION_FAILED"
    assert result.event_published is False
    assert event_bus.published == []
    with sqlite3.connect(composition.ledger_store._database_path) as connection:
        ledger_row = connection.execute(
            "SELECT lifecycle FROM workflow_application_ledger WHERE attempt_id = ?",
            (_ATTEMPT_ID,),
        ).fetchone()
    with sqlite3.connect(composition.receipt_store._database_path) as connection:
        receipt_row = connection.execute(
            "SELECT attempt_id FROM durable_application_commit_receipts WHERE attempt_id = ?",
            (_ATTEMPT_ID,),
        ).fetchone()
    assert ledger_row == ("prepared",)
    assert receipt_row is None


def test_restart_materializes_only_existing_pre_cas_prepared_provenance(tmp_path: Path, monkeypatch) -> None:
    """Model a crash after R27 CAS and before the normal R25 inlet."""

    repository = _prepared_repository(tmp_path)
    event_bus = MemoryEventBus()
    composition = build_localfile_external_generation_composition(
        repository, StateMachine(), event_bus
    )
    external = composition.external_application
    prepared = composition.ledger_service.prepare(_report(), _authorization(), composition.ledger_store)
    assert prepared.prepared is True
    assert prepared.binding is not None
    binding = prepared.binding
    snapshot = external._page_store.load_revisioned(_PROJECT_ID)
    context = external._page_store.context_from_snapshot(snapshot, binding.page_id)
    next_context = context.advance(
        state=PageState.GENERATED,
        events=[WorkflowEvent(event_type=EventType.IMAGE_GENERATED, data={"state": "Generated"})],
        artifact_name=PageState.GENERATED.value,
        payload=_descriptor(binding.output_asset_id),
    )
    project = external._page_store.project_from_context(snapshot, binding.page_id, next_context)
    assert external._record_r30_pre_cas_provenance(binding, snapshot) is True
    committed, intent_invalid = external._authoritative_commit(binding, snapshot, context, project)
    assert committed is not None
    assert intent_invalid is False
    ledger_before_restart = composition.ledger_store._database_path.read_bytes()

    r25 = external._r25_localfile_composition
    assert r25 is not None
    service_type = type(r25._r25_service)
    original_materialize = service_type._materialize_v1

    def lose_acknowledgement(service, request):
        original_materialize(service, request)
        raise RuntimeError("injected acknowledgement loss after durable R25 commit")

    monkeypatch.setattr(service_type, "_materialize_v1", lose_acknowledgement)
    acknowledgement_lost = external.apply(_report(), _authorization())
    monkeypatch.setattr(service_type, "_materialize_v1", original_materialize)
    result = external.apply(_report(), _authorization())
    replay = external.apply(_report(), _authorization())

    assert acknowledgement_lost.code == "EXTERNAL_APPLICATION_FAILED"
    assert result.status == "application_not_applied"
    assert result.code == "EXTERNAL_APPLICATION_RESTART_R25_MATERIALIZED"
    assert result.event_published is False
    assert replay.code == "EXTERNAL_APPLICATION_RESTART_R25_MATERIALIZED"
    assert r25._r25_store._replay_post_cas_attestation_exact_v1(
        _r27_application_binding_identity(binding)
    ) is not None
    with sqlite3.connect(composition.ledger_store._database_path) as connection:
        lifecycle = connection.execute(
            "SELECT lifecycle FROM workflow_application_ledger WHERE attempt_id = ?", (_ATTEMPT_ID,)
        ).fetchone()
    assert lifecycle == ("prepared",)
    assert composition.ledger_store._database_path.read_bytes() == ledger_before_restart
    with sqlite3.connect(r25._r25_store._database_path) as connection:
        r25_count = connection.execute("SELECT COUNT(*) FROM post_cas_application_attestations").fetchone()
    assert r25_count == (1,)
    assert event_bus.published == []
    with sqlite3.connect(r25._r25_store._database_path) as connection:
        connection.execute(
            "UPDATE post_cas_application_attestations SET record_digest = ?", ("0" * 64,)
        )
        connection.commit()
    corrupt_replay = external.apply(_report(), _authorization())
    assert corrupt_replay.code == "EXTERNAL_APPLICATION_RESTART_R25_MATERIALIZATION_FAILED"
    with sqlite3.connect(r25._r25_store._database_path) as connection:
        unchanged_count = connection.execute(
            "SELECT COUNT(*) FROM post_cas_application_attestations"
        ).fetchone()
    assert unchanged_count == (1,)


def test_generated_restart_with_absent_ledger_never_calls_prepare(tmp_path: Path) -> None:
    repository = _generated_repository_without_historical_predecessor(tmp_path)
    composition = build_localfile_external_generation_composition(
        repository, StateMachine(), MemoryEventBus()
    )

    first = composition.external_application.apply(_report(), _authorization())
    second = composition.external_application.apply(_report(), _authorization())

    assert first.code == "EXTERNAL_APPLICATION_PREPARED_GENERATED_AMBIGUOUS"
    assert second.code == "EXTERNAL_APPLICATION_PREPARED_GENERATED_AMBIGUOUS"
    with sqlite3.connect(composition.ledger_store._database_path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM workflow_application_ledger").fetchone()
    r25 = composition.external_application._r25_localfile_composition
    assert r25 is not None
    with sqlite3.connect(r25._r30_provenance_store._database_path) as connection:
        provenance_count = connection.execute(
            "SELECT COUNT(*) FROM r30_pre_cas_ledger_provenance"
        ).fetchone()
    assert count == (0,)
    assert provenance_count == (0,)


def test_idempotent_prepared_without_historical_provenance_is_ineligible(tmp_path: Path) -> None:
    repository = _generated_repository_without_historical_predecessor(tmp_path)
    composition = build_localfile_external_generation_composition(
        repository, StateMachine(), MemoryEventBus()
    )
    created = composition.ledger_service.prepare(_report(), _authorization(), composition.ledger_store)
    replay = composition.ledger_service.prepare(_report(), _authorization(), composition.ledger_store)

    first = composition.external_application.apply(_report(), _authorization())
    result = composition.external_application.apply(_report(), _authorization())
    third = composition.external_application.apply(_report(), _authorization())

    assert created.prepared is True
    assert replay.prepared is True
    assert replay.idempotent_replay is True
    assert first.code == "EXTERNAL_APPLICATION_PREPARED_GENERATED_AMBIGUOUS"
    assert result.code == "EXTERNAL_APPLICATION_PREPARED_GENERATED_AMBIGUOUS"
    assert third.code == "EXTERNAL_APPLICATION_PREPARED_GENERATED_AMBIGUOUS"
    r25 = composition.external_application._r25_localfile_composition
    assert r25 is not None
    with sqlite3.connect(r25._r25_store._database_path) as connection:
        r25_count = connection.execute("SELECT COUNT(*) FROM post_cas_application_attestations").fetchone()
    assert r25_count == (0,)


def test_concurrent_restart_materializers_create_one_r25_row(tmp_path: Path) -> None:
    repository = _prepared_repository(tmp_path)
    composition = build_localfile_external_generation_composition(
        repository, StateMachine(), MemoryEventBus()
    )
    external = composition.external_application
    prepared = composition.ledger_service.prepare(_report(), _authorization(), composition.ledger_store)
    assert prepared.binding is not None
    binding = prepared.binding
    snapshot = external._page_store.load_revisioned(_PROJECT_ID)
    context = external._page_store.context_from_snapshot(snapshot, binding.page_id)
    next_context = context.advance(
        state=PageState.GENERATED,
        events=[WorkflowEvent(event_type=EventType.IMAGE_GENERATED, data={"state": "Generated"})],
        artifact_name=PageState.GENERATED.value,
        payload=_descriptor(binding.output_asset_id),
    )
    project = external._page_store.project_from_context(snapshot, binding.page_id, next_context)
    assert external._record_r30_pre_cas_provenance(binding, snapshot) is True
    committed, invalid = external._authoritative_commit(binding, snapshot, context, project)
    assert committed is not None
    assert invalid is False

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _unused: external.apply(_report(), _authorization()), range(2)))

    assert {result.code for result in results} == {"EXTERNAL_APPLICATION_RESTART_R25_MATERIALIZED"}
    r25 = external._r25_localfile_composition
    assert r25 is not None
    with sqlite3.connect(r25._r25_store._database_path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM post_cas_application_attestations").fetchone()
    assert count == (1,)


def test_restart_rejects_existing_immutable_conflicting_r25_row(tmp_path: Path) -> None:
    """A valid, different durable row cannot be overwritten by restart materialization."""

    repository = _prepared_repository(tmp_path)
    event_bus = MemoryEventBus()
    composition = build_localfile_external_generation_composition(
        repository, StateMachine(), event_bus
    )
    external = composition.external_application
    prepared = composition.ledger_service.prepare(_report(), _authorization(), composition.ledger_store)
    assert prepared.binding is not None
    binding = prepared.binding
    snapshot = external._page_store.load_revisioned(_PROJECT_ID)
    context = external._page_store.context_from_snapshot(snapshot, binding.page_id)
    next_context = context.advance(
        state=PageState.GENERATED,
        events=[WorkflowEvent(event_type=EventType.IMAGE_GENERATED, data={"state": "Generated"})],
        artifact_name=PageState.GENERATED.value,
        payload=_descriptor(binding.output_asset_id),
    )
    project = external._page_store.project_from_context(snapshot, binding.page_id, next_context)
    assert external._record_r30_pre_cas_provenance(binding, snapshot) is True
    committed, invalid = external._authoritative_commit(binding, snapshot, context, project)
    assert committed is not None
    assert invalid is False

    r25 = external._r25_localfile_composition
    assert r25 is not None
    r27 = r25._r27_reader._read_exact_committed_v1(binding.project_id)
    r20 = r25._r20_reader._replay_for_binding_v1(binding)
    lineage = json.loads(r27.lineage_json)
    assert type(lineage) is dict
    conflicting = _canonical_r25_record_v1(
        delivery_identity="b" * 64,
        attempt_id=binding.attempt_id,
        application_binding_digest=_r27_application_binding_identity(binding),
        project_id=binding.project_id,
        page_id=binding.page_id,
        target_page_reference=binding.target_page_reference,
        provider_reference=binding.provider_reference,
        authorization_id=binding.authorization_id,
        output_asset_id=binding.output_asset_id,
        canonical_result_identity=r20.canonical_result_identity,
        logical_output_id=r20.logical_output_id,
        asset_identity=r20.asset_id,
        asset_sha256=r20.asset_sha256,
        expected_byte_length=r20.expected_byte_length,
        evidence_identity=r20.evidence_identity,
        evidence_persistence_digest=r20.evidence_persistence_identity,
        evidence_binding_fingerprint=r20.binding_digest,
        pre_commit_revision=lineage["expected_revision"],
        pre_commit_fingerprint=lineage["expected_aggregate_fingerprint"],
        post_commit_revision=r27.revision,
        post_commit_fingerprint=r27.physical_aggregate_fingerprint,
        application_binding_json=_r27_application_binding_json(binding),
    )
    stored, returned = r25._r25_store._create_or_confirm_v1(conflicting)
    assert stored == "ATTESTED"
    assert returned == conflicting
    bytes_before_restart = r25._r25_store._database_path.read_bytes()

    result = external.apply(_report(), _authorization())

    assert result.code == "EXTERNAL_APPLICATION_RESTART_R25_MATERIALIZATION_FAILED"
    assert r25._r25_store._database_path.read_bytes() == bytes_before_restart
    with sqlite3.connect(r25._r25_store._database_path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM post_cas_application_attestations").fetchone()
    assert count == (1,)
    assert event_bus.published == []


def test_restart_rejects_corrupt_durable_ledger_without_prepare_or_mutation(
    tmp_path: Path, monkeypatch
) -> None:
    """The real readonly Ledger observation fails closed before restart prepare."""

    repository = _prepared_repository(tmp_path)
    event_bus = MemoryEventBus()
    composition = build_localfile_external_generation_composition(
        repository, StateMachine(), event_bus
    )
    external = composition.external_application
    prepared = composition.ledger_service.prepare(_report(), _authorization(), composition.ledger_store)
    assert prepared.binding is not None
    binding = prepared.binding
    snapshot = external._page_store.load_revisioned(_PROJECT_ID)
    context = external._page_store.context_from_snapshot(snapshot, binding.page_id)
    next_context = context.advance(
        state=PageState.GENERATED,
        events=[WorkflowEvent(event_type=EventType.IMAGE_GENERATED, data={"state": "Generated"})],
        artifact_name=PageState.GENERATED.value,
        payload=_descriptor(binding.output_asset_id),
    )
    project = external._page_store.project_from_context(snapshot, binding.page_id, next_context)
    assert external._record_r30_pre_cas_provenance(binding, snapshot) is True
    committed, invalid = external._authoritative_commit(binding, snapshot, context, project)
    assert committed is not None
    assert invalid is False

    with sqlite3.connect(composition.ledger_store._database_path) as connection:
        connection.execute("UPDATE workflow_application_ledger SET binding_digest = ?", ("0" * 64,))
        connection.commit()
    ledger_before_restart = composition.ledger_store._database_path.read_bytes()
    aggregate_before_restart = repository._path(_PROJECT_ID).read_bytes()
    prepare_called = False
    service_type = type(composition.ledger_service)
    original_prepare = service_type.prepare

    def unexpected_prepare(*args):
        nonlocal prepare_called
        prepare_called = True
        return original_prepare(*args)

    monkeypatch.setattr(service_type, "prepare", unexpected_prepare)
    result = external.apply(_report(), _authorization())

    assert result.code == "EXTERNAL_APPLICATION_PREPARED_GENERATED_AMBIGUOUS"
    assert prepare_called is False
    assert composition.ledger_store._database_path.read_bytes() == ledger_before_restart
    assert repository._path(_PROJECT_ID).read_bytes() == aggregate_before_restart
    r25 = external._r25_localfile_composition
    assert r25 is not None
    with sqlite3.connect(r25._r25_store._database_path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM post_cas_application_attestations").fetchone()
    assert count == (0,)
    assert event_bus.published == []


def test_restart_rejects_applied_ledger_without_r25_or_receipt(
    tmp_path: Path, monkeypatch
) -> None:
    """A durable APPLIED row cannot bypass the frozen PREPARED restart predicate."""

    repository = _prepared_repository(tmp_path)
    event_bus = MemoryEventBus()
    composition = build_localfile_external_generation_composition(
        repository, StateMachine(), event_bus
    )
    external = composition.external_application
    prepared = composition.ledger_service.prepare(_report(), _authorization(), composition.ledger_store)
    assert prepared.binding is not None
    binding = prepared.binding
    snapshot = external._page_store.load_revisioned(_PROJECT_ID)
    context = external._page_store.context_from_snapshot(snapshot, binding.page_id)
    next_context = context.advance(
        state=PageState.GENERATED,
        events=[WorkflowEvent(event_type=EventType.IMAGE_GENERATED, data={"state": "Generated"})],
        artifact_name=PageState.GENERATED.value,
        payload=_descriptor(binding.output_asset_id),
    )
    project = external._page_store.project_from_context(snapshot, binding.page_id, next_context)
    assert external._record_r30_pre_cas_provenance(binding, snapshot) is True
    committed, invalid = external._authoritative_commit(binding, snapshot, context, project)
    assert committed is not None
    assert invalid is False

    applied_payload = _canonical_payload(binding, "applied")
    with sqlite3.connect(composition.ledger_store._database_path) as connection:
        connection.execute(
            "UPDATE workflow_application_ledger SET lifecycle = ?, binding_json = ?, binding_digest = ?",
            ("applied", applied_payload, hashlib.sha256(applied_payload.encode("utf-8")).hexdigest()),
        )
        connection.commit()
    ledger_before_restart = composition.ledger_store._database_path.read_bytes()
    aggregate_before_restart = repository._path(_PROJECT_ID).read_bytes()
    prepare_called = False
    service_type = type(composition.ledger_service)
    original_prepare = service_type.prepare

    def unexpected_prepare(*args):
        nonlocal prepare_called
        prepare_called = True
        return original_prepare(*args)

    monkeypatch.setattr(service_type, "prepare", unexpected_prepare)
    result = external.apply(_report(), _authorization())

    assert result.code == "EXTERNAL_APPLICATION_APPLIED_REPLAY_PROOF_INVALID"
    assert prepare_called is False
    assert composition.ledger_store._database_path.read_bytes() == ledger_before_restart
    assert repository._path(_PROJECT_ID).read_bytes() == aggregate_before_restart
    r25 = external._r25_localfile_composition
    assert r25 is not None
    with sqlite3.connect(r25._r25_store._database_path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM post_cas_application_attestations").fetchone()
    assert count == (0,)
    assert event_bus.published == []


def test_restart_rejects_durable_ledger_binding_substitution_without_mutation(
    tmp_path: Path, monkeypatch
) -> None:
    """A structurally valid Ledger row for another binding is not restart authority."""

    repository = _prepared_repository(tmp_path)
    event_bus = MemoryEventBus()
    composition = build_localfile_external_generation_composition(
        repository, StateMachine(), event_bus
    )
    external = composition.external_application
    prepared = composition.ledger_service.prepare(_report(), _authorization(), composition.ledger_store)
    assert prepared.binding is not None
    binding = prepared.binding
    snapshot = external._page_store.load_revisioned(_PROJECT_ID)
    context = external._page_store.context_from_snapshot(snapshot, binding.page_id)
    next_context = context.advance(
        state=PageState.GENERATED,
        events=[WorkflowEvent(event_type=EventType.IMAGE_GENERATED, data={"state": "Generated"})],
        artifact_name=PageState.GENERATED.value,
        payload=_descriptor(binding.output_asset_id),
    )
    project = external._page_store.project_from_context(snapshot, binding.page_id, next_context)
    assert external._record_r30_pre_cas_provenance(binding, snapshot) is True
    committed, invalid = external._authoritative_commit(binding, snapshot, context, project)
    assert committed is not None
    assert invalid is False

    substituted = WorkflowApplicationLedgerBindingDTO(
        attempt_id=binding.attempt_id,
        authorization_id=binding.authorization_id,
        project_id=binding.project_id,
        page_id=binding.page_id,
        target_page_reference=binding.target_page_reference,
        provider_reference=binding.provider_reference,
        output_asset_id="output:r25:substituted",
        source_state=binding.source_state,
        target_state=binding.target_state,
    )
    payload = _canonical_payload(substituted, "prepared")
    with sqlite3.connect(composition.ledger_store._database_path) as connection:
        connection.execute(
            "UPDATE workflow_application_ledger SET project_id = ?, page_id = ?, "
            "target_page_reference = ?, provider_reference = ?, output_asset_id = ?, "
            "source_state = ?, target_state = ?, binding_json = ?, binding_digest = ?",
            (
                substituted.project_id,
                substituted.page_id,
                substituted.target_page_reference,
                substituted.provider_reference,
                substituted.output_asset_id,
                substituted.source_state,
                substituted.target_state,
                payload,
                hashlib.sha256(payload.encode("utf-8")).hexdigest(),
            ),
        )
        connection.commit()
    ledger_before_restart = composition.ledger_store._database_path.read_bytes()
    aggregate_before_restart = repository._path(_PROJECT_ID).read_bytes()
    prepare_called = False
    service_type = type(composition.ledger_service)
    original_prepare = service_type.prepare

    def unexpected_prepare(*args):
        nonlocal prepare_called
        prepare_called = True
        return original_prepare(*args)

    monkeypatch.setattr(service_type, "prepare", unexpected_prepare)
    result = external.apply(_report(), _authorization())

    assert result.code == "EXTERNAL_APPLICATION_PREPARED_GENERATED_AMBIGUOUS"
    assert prepare_called is False
    assert composition.ledger_store._database_path.read_bytes() == ledger_before_restart
    assert repository._path(_PROJECT_ID).read_bytes() == aggregate_before_restart
    r25 = external._r25_localfile_composition
    assert r25 is not None
    with sqlite3.connect(r25._r25_store._database_path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM post_cas_application_attestations").fetchone()
    assert count == (0,)
    assert event_bus.published == []


def test_restart_fault_after_readonly_observation_never_mutates_predecessors(
    tmp_path: Path, monkeypatch
) -> None:
    """A failure at sealed-ingress issuance leaves the observed restart state untouched."""

    repository = _prepared_repository(tmp_path)
    event_bus = MemoryEventBus()
    composition = build_localfile_external_generation_composition(
        repository, StateMachine(), event_bus
    )
    external = composition.external_application
    prepared = composition.ledger_service.prepare(_report(), _authorization(), composition.ledger_store)
    assert prepared.binding is not None
    binding = prepared.binding
    snapshot = external._page_store.load_revisioned(_PROJECT_ID)
    context = external._page_store.context_from_snapshot(snapshot, binding.page_id)
    next_context = context.advance(
        state=PageState.GENERATED,
        events=[WorkflowEvent(event_type=EventType.IMAGE_GENERATED, data={"state": "Generated"})],
        artifact_name=PageState.GENERATED.value,
        payload=_descriptor(binding.output_asset_id),
    )
    project = external._page_store.project_from_context(snapshot, binding.page_id, next_context)
    assert external._record_r30_pre_cas_provenance(binding, snapshot) is True
    committed, invalid = external._authoritative_commit(binding, snapshot, context, project)
    assert committed is not None
    assert invalid is False

    aggregate_before_restart = repository._path(_PROJECT_ID).read_bytes()
    ledger_before_restart = composition.ledger_store._database_path.read_bytes()
    original_issue = external_application._issue_r30_restart_ingress_v1

    def fail_ingress(*args):
        del args
        raise ValueError("injected sealed ingress issuance fault")

    monkeypatch.setattr(external_application, "_issue_r30_restart_ingress_v1", fail_ingress)
    result = external.apply(_report(), _authorization())

    assert result.code == "EXTERNAL_APPLICATION_PREPARED_GENERATED_AMBIGUOUS"
    assert repository._path(_PROJECT_ID).read_bytes() == aggregate_before_restart
    assert composition.ledger_store._database_path.read_bytes() == ledger_before_restart
    r25 = external._r25_localfile_composition
    assert r25 is not None
    with sqlite3.connect(r25._r25_store._database_path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM post_cas_application_attestations").fetchone()
    assert count == (0,)
    assert event_bus.published == []
    monkeypatch.setattr(external_application, "_issue_r30_restart_ingress_v1", original_issue)
    reopened = build_localfile_external_generation_composition(
        repository, StateMachine(), MemoryEventBus()
    )
    replay = reopened.external_application.apply(_report(), _authorization())
    assert replay.code == "EXTERNAL_APPLICATION_RESTART_R25_MATERIALIZED"


def test_restart_rereads_provenance_after_ingress_before_r25_mutation(
    tmp_path: Path, monkeypatch
) -> None:
    """A provenance change after ingress issuance invalidates the sealed restart handoff."""

    repository = _prepared_repository(tmp_path)
    event_bus = MemoryEventBus()
    composition = build_localfile_external_generation_composition(
        repository, StateMachine(), event_bus
    )
    external = composition.external_application
    prepared = composition.ledger_service.prepare(_report(), _authorization(), composition.ledger_store)
    assert prepared.binding is not None
    binding = prepared.binding
    snapshot = external._page_store.load_revisioned(_PROJECT_ID)
    context = external._page_store.context_from_snapshot(snapshot, binding.page_id)
    next_context = context.advance(
        state=PageState.GENERATED,
        events=[WorkflowEvent(event_type=EventType.IMAGE_GENERATED, data={"state": "Generated"})],
        artifact_name=PageState.GENERATED.value,
        payload=_descriptor(binding.output_asset_id),
    )
    project = external._page_store.project_from_context(snapshot, binding.page_id, next_context)
    assert external._record_r30_pre_cas_provenance(binding, snapshot) is True
    committed, invalid = external._authoritative_commit(binding, snapshot, context, project)
    assert committed is not None
    assert invalid is False

    r25 = external._r25_localfile_composition
    assert r25 is not None
    aggregate_before_restart = repository._path(_PROJECT_ID).read_bytes()
    original_issue = external_application._issue_r30_restart_ingress_v1

    def issue_then_tamper_provenance(*args):
        ingress = original_issue(*args)
        with sqlite3.connect(r25._r30_provenance_store._database_path) as connection:
            connection.execute(
                "UPDATE r30_pre_cas_ledger_provenance SET record_digest = ?", ("0" * 64,)
            )
            connection.commit()
        return ingress

    monkeypatch.setattr(
        external_application, "_issue_r30_restart_ingress_v1", issue_then_tamper_provenance
    )
    result = external.apply(_report(), _authorization())

    assert result.code == "EXTERNAL_APPLICATION_RESTART_R25_MATERIALIZATION_FAILED"
    assert repository._path(_PROJECT_ID).read_bytes() == aggregate_before_restart
    with sqlite3.connect(composition.ledger_store._database_path) as connection:
        lifecycle = connection.execute(
            "SELECT lifecycle FROM workflow_application_ledger WHERE attempt_id = ?", (_ATTEMPT_ID,)
        ).fetchone()
    assert lifecycle == ("prepared",)
    with sqlite3.connect(r25._r25_store._database_path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM post_cas_application_attestations").fetchone()
    assert count == (0,)
    assert event_bus.published == []


def test_restart_rereads_committed_r27_lineage_after_ingress_before_r25_mutation(
    tmp_path: Path, monkeypatch
) -> None:
    """Loss of committed R27 authority after issuance cannot be bypassed by an ingress."""

    repository = _prepared_repository(tmp_path)
    event_bus = MemoryEventBus()
    composition = build_localfile_external_generation_composition(
        repository, StateMachine(), event_bus
    )
    external = composition.external_application
    prepared = composition.ledger_service.prepare(_report(), _authorization(), composition.ledger_store)
    assert prepared.binding is not None
    binding = prepared.binding
    snapshot = external._page_store.load_revisioned(_PROJECT_ID)
    context = external._page_store.context_from_snapshot(snapshot, binding.page_id)
    next_context = context.advance(
        state=PageState.GENERATED,
        events=[WorkflowEvent(event_type=EventType.IMAGE_GENERATED, data={"state": "Generated"})],
        artifact_name=PageState.GENERATED.value,
        payload=_descriptor(binding.output_asset_id),
    )
    project = external._page_store.project_from_context(snapshot, binding.page_id, next_context)
    assert external._record_r30_pre_cas_provenance(binding, snapshot) is True
    committed, invalid = external._authoritative_commit(binding, snapshot, context, project)
    assert committed is not None
    assert invalid is False

    r25 = external._r25_localfile_composition
    assert r25 is not None
    aggregate_before_restart = repository._path(_PROJECT_ID).read_bytes()
    original_issue = external_application._issue_r30_restart_ingress_v1

    def issue_then_remove_committed_lineage(*args):
        ingress = original_issue(*args)
        repository._revision_store._committed_path(_PROJECT_ID).unlink()
        return ingress

    monkeypatch.setattr(
        external_application, "_issue_r30_restart_ingress_v1", issue_then_remove_committed_lineage
    )
    result = external.apply(_report(), _authorization())

    assert result.code == "EXTERNAL_APPLICATION_RESTART_R25_MATERIALIZATION_FAILED"
    assert repository._path(_PROJECT_ID).read_bytes() == aggregate_before_restart
    with sqlite3.connect(composition.ledger_store._database_path) as connection:
        lifecycle = connection.execute(
            "SELECT lifecycle FROM workflow_application_ledger WHERE attempt_id = ?", (_ATTEMPT_ID,)
        ).fetchone()
    assert lifecycle == ("prepared",)
    with sqlite3.connect(r25._r25_store._database_path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM post_cas_application_attestations").fetchone()
    assert count == (0,)
    assert event_bus.published == []


@pytest.mark.parametrize("authority", ["r18", "r20"])
def test_restart_rereads_r18_and_r20_authority_before_r25_mutation(
    tmp_path: Path, monkeypatch, authority: str
) -> None:
    """Both R18 and R20 readers are re-entered after ingress issuance."""

    repository = _prepared_repository(tmp_path)
    event_bus = MemoryEventBus()
    composition = build_localfile_external_generation_composition(
        repository, StateMachine(), event_bus
    )
    external = composition.external_application
    prepared = composition.ledger_service.prepare(_report(), _authorization(), composition.ledger_store)
    assert prepared.binding is not None
    binding = prepared.binding
    snapshot = external._page_store.load_revisioned(_PROJECT_ID)
    context = external._page_store.context_from_snapshot(snapshot, binding.page_id)
    next_context = context.advance(
        state=PageState.GENERATED,
        events=[WorkflowEvent(event_type=EventType.IMAGE_GENERATED, data={"state": "Generated"})],
        artifact_name=PageState.GENERATED.value,
        payload=_descriptor(binding.output_asset_id),
    )
    project = external._page_store.project_from_context(snapshot, binding.page_id, next_context)
    assert external._record_r30_pre_cas_provenance(binding, snapshot) is True
    committed, invalid = external._authoritative_commit(binding, snapshot, context, project)
    assert committed is not None
    assert invalid is False

    r25 = external._r25_localfile_composition
    assert r25 is not None
    aggregate_before_restart = repository._path(_PROJECT_ID).read_bytes()
    calls = 0
    if authority == "r18":
        reader_type = type(r25._r18_authority)
        method_name = "_replay_historical_binding_for_attempt_v1"
    else:
        reader_type = type(r25._r20_reader)
        method_name = "_replay_for_binding_v1"
    original = getattr(reader_type, method_name)

    def fail_second_read(*args):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ValueError("injected stale authoritative replay")
        return original(*args)

    monkeypatch.setattr(reader_type, method_name, fail_second_read)
    result = external.apply(_report(), _authorization())

    assert calls == 2
    assert result.code == "EXTERNAL_APPLICATION_RESTART_R25_MATERIALIZATION_FAILED"
    assert repository._path(_PROJECT_ID).read_bytes() == aggregate_before_restart
    with sqlite3.connect(composition.ledger_store._database_path) as connection:
        lifecycle = connection.execute(
            "SELECT lifecycle FROM workflow_application_ledger WHERE attempt_id = ?", (_ATTEMPT_ID,)
        ).fetchone()
    assert lifecycle == ("prepared",)
    with sqlite3.connect(r25._r25_store._database_path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM post_cas_application_attestations").fetchone()
    assert count == (0,)
    assert event_bus.published == []


@pytest.mark.parametrize("orphan", ["provenance", "ledger", "r27", "r18", "r20", "composition"])
def test_existing_r25_never_grants_restart_authority_without_every_predecessor(
    tmp_path: Path, monkeypatch, orphan: str
) -> None:
    """R25 is downstream evidence, never a substitute for its missing predecessor."""

    repository = _prepared_repository(tmp_path)
    event_bus = MemoryEventBus()
    composition = build_localfile_external_generation_composition(
        repository, StateMachine(), event_bus
    )
    external = composition.external_application
    prepared = composition.ledger_service.prepare(_report(), _authorization(), composition.ledger_store)
    assert prepared.binding is not None
    binding = prepared.binding
    snapshot = external._page_store.load_revisioned(_PROJECT_ID)
    context = external._page_store.context_from_snapshot(snapshot, binding.page_id)
    next_context = context.advance(
        state=PageState.GENERATED,
        events=[WorkflowEvent(event_type=EventType.IMAGE_GENERATED, data={"state": "Generated"})],
        artifact_name=PageState.GENERATED.value,
        payload=_descriptor(binding.output_asset_id),
    )
    project = external._page_store.project_from_context(snapshot, binding.page_id, next_context)
    assert external._record_r30_pre_cas_provenance(binding, snapshot) is True
    committed, invalid = external._authoritative_commit(binding, snapshot, context, project)
    assert committed is not None
    assert invalid is False
    initial = external.apply(_report(), _authorization())
    assert initial.code == "EXTERNAL_APPLICATION_RESTART_R25_MATERIALIZED"

    r25 = external._r25_localfile_composition
    assert r25 is not None
    if orphan == "provenance":
        with sqlite3.connect(r25._r30_provenance_store._database_path) as connection:
            connection.execute(
                "UPDATE r30_pre_cas_ledger_provenance SET record_digest = ?", ("0" * 64,)
            )
            connection.commit()
    elif orphan == "ledger":
        with sqlite3.connect(composition.ledger_store._database_path) as connection:
            connection.execute("UPDATE workflow_application_ledger SET binding_digest = ?", ("0" * 64,))
            connection.commit()
    elif orphan == "r27":
        repository._revision_store._committed_path(_PROJECT_ID).unlink()
    elif orphan == "r18":
        authority_type = type(r25._r18_authority)
        monkeypatch.setattr(
            authority_type,
            "_replay_historical_binding_for_attempt_v1",
            lambda *args: (_ for _ in ()).throw(ValueError("injected missing R18 authority")),
        )
    elif orphan == "r20":
        reader_type = type(r25._r20_reader)
        monkeypatch.setattr(
            reader_type,
            "_replay_for_binding_v1",
            lambda *args: (_ for _ in ()).throw(ValueError("injected missing R20 authority")),
        )
    else:
        external._r25_localfile_composition = object()

    r25_bytes_before = r25._r25_store._database_path.read_bytes()
    aggregate_before = repository._path(_PROJECT_ID).read_bytes()
    result = external.apply(_report(), _authorization())

    assert result.status == "application_not_applied"
    assert result.code not in {
        "EXTERNAL_APPLICATION_RESTART_R25_MATERIALIZED",
        "EXTERNAL_APPLICATION_APPLIED_REPLAY_CONFIRMED",
    }
    assert r25._r25_store._database_path.read_bytes() == r25_bytes_before
    assert repository._path(_PROJECT_ID).read_bytes() == aggregate_before
    with sqlite3.connect(r25._r25_store._database_path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM post_cas_application_attestations").fetchone()
    assert count == (1,)
    assert event_bus.published == []
