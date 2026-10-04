"""Focused R18 trusted-construction tests."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.production import future_real_delivery_binding_authority as binding_authority
from manga_director.production import (
    future_real_delivery_i02_real_asset_delivery_journal as i02_journal,
)
from manga_director.production import future_real_delivery_i02a_protocol as i02_protocol
from manga_director.production import future_real_delivery_r18_construction as r18_construction
from manga_director.production.future_real_delivery_binding_authority import (
    RealDeliveryBindingAuthorityV1,
)
from manga_director.production.future_real_delivery_r18_construction import (
    PrivateR18CompositionFactoryV1,
    _R18CompositionV1,
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
    LocalDurableAssetOwner,
    OwnerRegistrationMaterial,
    _AssetVerificationIntegrityFailure,
)
from manga_director.repositories.local_file import LocalFileRepository

_IMAGE_BYTES = b"\x89PNG\r\n\x1a\n" + b"r18" * 64
_IMAGE_DIGEST = hashlib.sha256(_IMAGE_BYTES).hexdigest()


def _factory_composition(tmp_path: Path) -> tuple[PrivateR18CompositionFactoryV1, _R18CompositionV1]:
    factory = PrivateR18CompositionFactoryV1()
    return factory, factory.create(tmp_path.resolve())


def _known(value: str) -> EvidenceValueDTO:
    return EvidenceValueDTO(availability="known", value=value)


def _persist_exact_evidence(
    authority: RealDeliveryBindingAuthorityV1,
    *,
    attempt_id: str = "attempt:r18:001",
    provider_reference: str = "provider:r18:001",
    logical_output_id: str = "output:r18:001",
    asset_sha256: str = "a" * 64,
) -> tuple[LocalGenerationEvidenceStore, str]:
    repository = authority._repository
    evidence = GenerationEvidenceEnvelopeDTO(
        attempt_id=attempt_id,
        observed_at=datetime(2026, 8, 30, 12, 0, tzinfo=UTC),
        provenance_reference="provenance:r18:001",
        input=GenerationInputEvidenceDTO(input_reference="input:r18:001"),
        output=GenerationOutputEvidenceDTO(
            output_asset_id=logical_output_id,
            output_content_hash=_known(asset_sha256),
            media_type="image/png",
        ),
        configuration=GenerationConfigurationEvidenceDTO(
            provider_id=_known("provider:r18:001"),
            model_id=_known("model:r18:001"),
            model_version=_known("v1"),
            workflow_id=_known("workflow:r18:001"),
            workflow_version=_known("v1"),
            seed=_known("42"),
        ),
    )
    store = LocalGenerationEvidenceStore(
        repository._next_generation_normal_execution_owner_root() / "evidence"
    )
    result = store.persist(
        GenerationEvidenceStoreWriteRequest(
            attempt_id=evidence.attempt_id,
            provider_reference=provider_reference,
            evidence_status="ready",
            generation_evidence=evidence,
        )
    )
    assert result.outcome == "persisted"
    connection = sqlite3.connect(store._database_path)
    try:
        row = connection.execute(
            "SELECT payload_digest FROM generation_evidence WHERE attempt_id = ?",
            (evidence.attempt_id,),
        ).fetchone()
    finally:
        connection.close()
    assert row is not None
    return store, row[0]


def _i02_binding() -> i02_journal._DeliveryBindingInputV1:
    return _i02_binding_for_digest(_IMAGE_DIGEST, len(_IMAGE_BYTES))


def _i02_binding_for_digest(digest: str, length: int) -> i02_journal._DeliveryBindingInputV1:
    return i02_journal._DeliveryBindingInputV1(
        attempt_id="attempt:r18:001",
        project_id="project-r18-001",
        page_id="1",
        target_page_reference="target:r18:001",
        provider_reference="provider:r18:001",
        dispatch_identity="dispatch:r18:001",
        idempotency_identity="idempotency:r18:001",
        submission_receipt_identity="receipt:r18:001",
        logical_output_id="output:r18:001",
        canonical_result_identity=i02_journal._canonical_result_identity_v1(
            attempt_id="attempt:r18:001",
            project_id="project-r18-001",
            page_id="1",
            target_page_reference="target:r18:001",
            provider_reference="provider:r18:001",
            dispatch_identity="dispatch:r18:001",
            idempotency_identity="idempotency:r18:001",
            submission_receipt_identity="receipt:r18:001",
            logical_output_id="output:r18:001",
            asset_sha256=digest,
            expected_byte_length=length,
        ),
        asset_sha256=digest,
        expected_byte_length=length,
    )


def _completed_lineage(
    tmp_path: Path,
) -> tuple[RealDeliveryBindingAuthorityV1, i02_journal._DeliveryBindingInputV1]:
    factory, composition = _factory_composition(tmp_path)
    binding = _i02_binding()
    composition.repository.save(
        Project(
            id=binding.project_id,
            title="R18 focused lineage",
            pages=[
                Page(
                    page_number=1,
                    state=PageState.PROMPT_BUILT,
                    page_design={},
                    review={},
                    storyboard={"panels": [{"id": "panel:r18:001"}]},
                    prompt={"positive": "R18 focused page"},
                    metadata={"future_generation_target_reference": binding.target_page_reference},
                )
            ],
        )
    )
    authority = factory.construct_authority(composition)
    composition.journal._begin_delivery_v1(binding)
    composition.journal._record_bytes_validated_v1(
        binding.expected_byte_length, binding.asset_sha256, "image/png"
    )
    registered = composition.owner.register(
        OwnerRegistrationMaterial(
            attempt_id=binding.attempt_id,
            provider_reference=binding.provider_reference,
            image_bytes=_IMAGE_BYTES,
        )
    )
    assert registered.outcome == "registered"
    asset_replay = composition.journal._record_authenticated_asset_registered_v1(registered)
    assert asset_replay.status is i02_journal._DeliveryStatusV1.ASSET_REGISTERED
    state = i02_protocol._create_isolated_test_protocol_state_v1()
    bootstrap = state.take_bootstrap()
    bootstrap._register_production_journal_class_once_v1(i02_journal.PrivateRealAssetDeliveryJournal)
    journal_peer, verifier_peer = state.create_pair(composition.journal)
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
    _persist_exact_evidence(
        authority,
        attempt_id=binding.attempt_id,
        provider_reference=binding.provider_reference,
        logical_output_id=binding.logical_output_id,
        asset_sha256=binding.asset_sha256,
    )
    return authority, binding


def _replace_stored_projection_dimension(
    authority: RealDeliveryBindingAuthorityV1,
    delivery_identity: str,
    *,
    key: str,
    value: object,
) -> None:
    """Rewrite exactly one frozen projection fact with derived digests kept coherent."""

    connection = sqlite3.connect(authority._database_path)
    try:
        row = connection.execute(
            "SELECT binding_json FROM real_delivery_binding_records WHERE delivery_identity = ?",
            (delivery_identity,),
        ).fetchone()
        assert row is not None
        projection = json.loads(row[0])
        assert type(projection) is dict
        projection[key] = value
        binding_json = binding_authority._canonical_json(projection)
        binding_identity = binding_authority._digest_text(binding_json)
        connection.execute(
            "UPDATE real_delivery_binding_records "
            "SET binding_identity = ?, binding_json = ?, binding_digest = ? "
            "WHERE delivery_identity = ?",
            (binding_identity, binding_json, binding_identity, delivery_identity),
        )
        connection.commit()
    finally:
        connection.close()


def _synthetic_binding_record(provider_reference: str) -> binding_authority._BindingRecordV1:
    i02 = binding_authority._CompletedI02FactsV1(
        delivery_identity="a" * 64,
        binding_digest="a" * 64,
        completion_sequence=3,
        completion_event_digest="b" * 64,
        attempt_id="attempt:r18:size",
        project_id="project:r18:size",
        page_id="1",
        target_page_reference="target:r18:size",
        provider_reference=provider_reference,
        dispatch_identity="c" * 64,
        idempotency_identity="d" * 64,
        submission_receipt_identity="e" * 64,
        logical_output_id="output:r18:size",
        canonical_result_identity="f" * 64,
        asset_sha256="1" * 64,
        expected_byte_length=123,
        media_type="image/png",
        asset_id="asset:r18:size",
        asset_registration_digest="2" * 64,
    )
    evidence = binding_authority._EvidenceFactsV1(
        attempt_id=i02.attempt_id,
        provider_reference=i02.provider_reference,
        logical_output_id=i02.logical_output_id,
        asset_sha256=i02.asset_sha256,
        media_type=i02.media_type,
        evidence_identity="3" * 64,
        evidence_persistence_identity="4" * 64,
        evidence_status="ready",
    )
    page = binding_authority._CurrentPageFactsV1(
        project_id=i02.project_id,
        page_id=i02.page_id,
        target_page_reference=i02.target_page_reference,
        storyboard_digest="5" * 64,
        prompt_digest="6" * 64,
        revision=7,
        fingerprint="7" * 64,
    )
    return binding_authority._binding_record_from_projection(i02, evidence, page)


def test_factory_constructs_exact_private_tuple(tmp_path: Path) -> None:
    factory, composition = _factory_composition(tmp_path)

    authority = factory.construct_authority(composition)

    assert authority.__class__.__name__ == "RealDeliveryBindingAuthorityV1"


def test_r31_existing_repository_inlet_preserves_exact_repository_identity(
    tmp_path: Path,
) -> None:
    repository = LocalFileRepository(tmp_path.resolve())
    factory = PrivateR18CompositionFactoryV1()

    composition = factory._create_for_existing_repository_v1(repository)
    authority = factory.construct_authority(composition)

    assert composition.repository is repository
    assert authority._repository is repository


def test_r31_existing_repository_inlet_keeps_legacy_create_root_behavior(
    tmp_path: Path,
) -> None:
    repository = LocalFileRepository(tmp_path.resolve())
    factory = PrivateR18CompositionFactoryV1()

    existing = factory._create_for_existing_repository_v1(repository)
    legacy = factory.create(tmp_path.resolve())

    assert existing.repository is repository
    assert legacy.repository is not repository
    assert legacy.repository._root == repository._root


def test_r31_existing_repository_inlet_rejects_non_exact_repository_objects(
    tmp_path: Path,
) -> None:
    factory = PrivateR18CompositionFactoryV1()

    for value in (tmp_path.resolve(), object(), cast(object, SimpleNamespace())):
        with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
            factory._create_for_existing_repository_v1(value)


def test_capability_is_tombstoned_after_success(tmp_path: Path) -> None:
    factory, composition = _factory_composition(tmp_path)
    factory.construct_authority(composition)

    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        factory.construct_authority(composition)


def test_substituted_composition_is_rejected(tmp_path: Path) -> None:
    factory, composition = _factory_composition(tmp_path)
    other_factory, other = _factory_composition(tmp_path / "other")
    del other_factory
    substituted = _R18CompositionV1(
        repository=composition.repository,
        owner=other.owner,
        journal=composition.journal,
        capability=composition.capability,
    )

    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        factory.construct_authority(substituted)


def test_wrong_owner_root_identity_is_rejected_before_authority_construction(
    tmp_path: Path,
) -> None:
    factory, composition = _factory_composition(tmp_path)
    composition.owner._root = tmp_path / "other-assets"

    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        factory.construct_authority(composition)


def test_exact_v1_authority_store_reopens_from_a_fresh_composition(tmp_path: Path) -> None:
    factory, composition = _factory_composition(tmp_path)
    authority = factory.construct_authority(composition)

    reopened_factory, reopened_composition = _factory_composition(tmp_path)
    reopened = reopened_factory.construct_authority(reopened_composition)

    assert reopened.__class__ is authority.__class__


def test_schema_alteration_fails_closed_on_reopen(tmp_path: Path) -> None:
    factory, composition = _factory_composition(tmp_path)
    authority = factory.construct_authority(composition)
    connection = sqlite3.connect(authority._database_path)
    try:
        connection.execute("CREATE TABLE unexpected_r18_object (value TEXT)")
        connection.commit()
    finally:
        connection.close()

    reopened_factory, reopened_composition = _factory_composition(tmp_path)
    with pytest.raises(ValueError, match="CORRUPT"):
        reopened_factory.construct_authority(reopened_composition)


def test_authenticated_construction_failure_tombstones_capability(tmp_path: Path) -> None:
    factory, composition = _factory_composition(tmp_path)
    directory = (
        composition.owner._root
        / "_durability"
        / "_post_lts_real_delivery_binding"
    )
    directory.mkdir(parents=True)

    with pytest.raises(ValueError, match="RECOVERY_REQUIRED"):
        factory.construct_authority(composition)
    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        factory.construct_authority(composition)


def test_reader_replays_one_exact_existing_evidence_record_read_only(tmp_path: Path) -> None:
    factory, composition = _factory_composition(tmp_path)
    authority = factory.construct_authority(composition)
    store, evidence_identity = _persist_exact_evidence(authority)
    before = store._database_path.read_bytes()

    facts = authority._replay_evidence_record_exact_v1(evidence_identity)

    assert facts.attempt_id == "attempt:r18:001"
    assert facts.provider_reference == "provider:r18:001"
    assert facts.logical_output_id == "output:r18:001"
    assert facts.asset_sha256 == "a" * 64
    assert store._database_path.read_bytes() == before


def test_reader_rejects_extra_evidence_object_as_corrupt(tmp_path: Path) -> None:
    factory, composition = _factory_composition(tmp_path)
    authority = factory.construct_authority(composition)
    store, evidence_identity = _persist_exact_evidence(authority)
    connection = sqlite3.connect(store._database_path)
    try:
        connection.execute("CREATE TABLE unexpected_evidence_object (value TEXT)")
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(ValueError, match="CORRUPT"):
        authority._replay_evidence_record_exact_v1(evidence_identity)


def test_reader_requires_existing_evidence_store(tmp_path: Path) -> None:
    factory, composition = _factory_composition(tmp_path)
    authority = factory.construct_authority(composition)

    with pytest.raises(ValueError, match="RECOVERY_REQUIRED"):
        authority._replay_evidence_record_exact_v1("a" * 64)


def test_i02_reread_rejects_a_non_completed_delivery(tmp_path: Path) -> None:
    factory, composition = _factory_composition(tmp_path)
    authority = factory.construct_authority(composition)
    binding = _i02_binding()
    composition.journal._begin_delivery_v1(binding)

    with pytest.raises(ValueError, match="RECOVERY_REQUIRED"):
        authority._replay_completed_i02_v1(binding.delivery_identity)


def test_canonical_binding_projection_is_deterministic_and_codepoint_exact() -> None:
    i02 = binding_authority._CompletedI02FactsV1(
        delivery_identity="a" * 64,
        binding_digest="a" * 64,
        completion_sequence=3,
        completion_event_digest="b" * 64,
        attempt_id="attempt:r18:001",
        project_id="project:r18:001",
        page_id="1",
        target_page_reference="target:r18:001",
        provider_reference="provider:r18:001",
        dispatch_identity="c" * 64,
        idempotency_identity="d" * 64,
        submission_receipt_identity="e" * 64,
        logical_output_id="output:r18:001",
        canonical_result_identity="f" * 64,
        asset_sha256="1" * 64,
        expected_byte_length=123,
        media_type="image/png",
        asset_id="asset:r18:001",
        asset_registration_digest="2" * 64,
    )
    evidence = binding_authority._EvidenceFactsV1(
        attempt_id=i02.attempt_id,
        provider_reference=i02.provider_reference,
        logical_output_id=i02.logical_output_id,
        asset_sha256=i02.asset_sha256,
        media_type=i02.media_type,
        evidence_identity="3" * 64,
        evidence_persistence_identity="4" * 64,
        evidence_status="ready",
    )
    page = binding_authority._CurrentPageFactsV1(
        project_id=i02.project_id,
        page_id=i02.page_id,
        target_page_reference=i02.target_page_reference,
        storyboard_digest="5" * 64,
        prompt_digest="6" * 64,
        revision=7,
        fingerprint="7" * 64,
    )

    first = binding_authority._binding_record_from_projection(i02, evidence, page)
    second = binding_authority._binding_record_from_projection(i02, evidence, page)
    altered = binding_authority._binding_record_from_projection(
        i02, evidence, replace(page, prompt_digest="8" * 64)
    )

    assert first == second
    assert first.binding_identity == first.binding_digest
    assert altered.binding_identity != first.binding_identity


def test_completed_lineage_creates_and_replays_one_exact_immutable_binding(tmp_path: Path) -> None:
    authority, binding = _completed_lineage(tmp_path)

    created = authority._create_exact_v1(binding.delivery_identity)
    replayed = authority._replay_exact_v1(binding.delivery_identity)
    duplicate = authority._create_exact_v1(binding.delivery_identity)

    assert replayed == created
    assert duplicate == created
    assert created.projection["attempt_id"] == binding.attempt_id
    assert created.projection["workflow_source_state"] == "PromptBuilt"
    assert created.projection["workflow_target_state"] == "Generated"


def test_replay_rejects_an_immutable_binding_digest_tamper(tmp_path: Path) -> None:
    authority, binding = _completed_lineage(tmp_path)
    authority._create_exact_v1(binding.delivery_identity)
    connection = sqlite3.connect(authority._database_path)
    try:
        connection.execute(
            "UPDATE real_delivery_binding_records SET binding_digest = ?",
            ("0" * 64,),
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(ValueError, match="CORRUPT"):
        authority._replay_exact_v1(binding.delivery_identity)


def test_exact_reopen_replays_read_only_and_preserves_idempotency(tmp_path: Path) -> None:
    authority, binding = _completed_lineage(tmp_path)
    created = authority._create_exact_v1(binding.delivery_identity)
    binding_before = authority._database_path.read_bytes()
    evidence_path = authority._evidence_database_path()
    evidence_before = evidence_path.read_bytes()

    factory, composition = _factory_composition(tmp_path)
    reopened = factory.construct_authority(composition)
    replayed = reopened._replay_exact_v1(binding.delivery_identity)
    duplicate = reopened._create_exact_v1(binding.delivery_identity)

    assert replayed == created
    assert duplicate == created
    assert reopened._database_path.read_bytes() == binding_before
    assert evidence_path.read_bytes() == evidence_before


def test_concurrent_first_creators_leave_one_exact_durable_binding(tmp_path: Path) -> None:
    authority, binding = _completed_lineage(tmp_path)
    factory, composition = _factory_composition(tmp_path)
    peer = factory.construct_authority(composition)
    barrier = threading.Barrier(2)
    records: list[object] = []
    failures: list[str] = []

    def create(candidate: RealDeliveryBindingAuthorityV1) -> None:
        try:
            barrier.wait()
            records.append(candidate._create_exact_v1(binding.delivery_identity))
        except ValueError as error:
            failures.append(str(error))

    first = threading.Thread(target=create, args=(authority,))
    second = threading.Thread(target=create, args=(peer,))
    first.start()
    second.start()
    first.join()
    second.join()

    assert records
    assert all(failure == "RECOVERY_REQUIRED" for failure in failures)
    assert authority._replay_exact_v1(binding.delivery_identity) == records[0]
    connection = sqlite3.connect(authority._database_path)
    try:
        count = connection.execute(
            "SELECT COUNT(*) FROM real_delivery_binding_records WHERE delivery_identity = ?",
            (binding.delivery_identity,),
        ).fetchone()
    finally:
        connection.close()
    assert count == (1,)


@pytest.mark.parametrize(
    ("statement", "parameters"),
    (
        ("UPDATE real_delivery_binding_records SET binding_identity = ?", ("0" * 64,)),
        ("UPDATE real_delivery_binding_records SET canonical_result_identity = ?", ("0" * 64,)),
        ("UPDATE real_delivery_binding_records SET binding_json = ?", ("{}",)),
        ("UPDATE real_delivery_binding_schema_meta SET schema_version = 2", ()),
        (
            "UPDATE real_delivery_binding_schema_meta SET schema_version = 'not-an-integer'",
            (),
        ),
        ("PRAGMA user_version = 2", ()),
        ("CREATE TABLE readable_unexpected_r18_object (value TEXT)", ()),
    ),
)
def test_readable_r18_durable_tamper_is_corrupt(
    tmp_path: Path, statement: str, parameters: tuple[str, ...]
) -> None:
    authority, binding = _completed_lineage(tmp_path)
    authority._create_exact_v1(binding.delivery_identity)
    connection = sqlite3.connect(authority._database_path)
    try:
        connection.execute(statement, parameters)
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(ValueError, match="CORRUPT"):
        authority._replay_exact_v1(binding.delivery_identity)


def test_prebinding_i02_failure_leaves_no_partial_r18_record(tmp_path: Path) -> None:
    factory, composition = _factory_composition(tmp_path)
    authority = factory.construct_authority(composition)

    with pytest.raises(ValueError, match="RECOVERY_REQUIRED"):
        authority._create_exact_v1("a" * 64)
    connection = sqlite3.connect(authority._database_path)
    try:
        count = connection.execute("SELECT COUNT(*) FROM real_delivery_binding_records").fetchone()
    finally:
        connection.close()
    assert count == (0,)


def test_readable_stale_page_binding_disagreement_is_corrupt(tmp_path: Path) -> None:
    authority, binding = _completed_lineage(tmp_path)
    authority._create_exact_v1(binding.delivery_identity)
    snapshot = authority._repository._load_revisioned(binding.project_id)
    page = snapshot.project.page(1).model_copy(update={"prompt": {"positive": "changed"}})
    authority._repository._conditional_commit(snapshot, snapshot.project.replace_page(page))

    with pytest.raises(ValueError, match="CORRUPT"):
        authority._replay_exact_v1(binding.delivery_identity)


def test_r20_historical_replay_authenticates_history_after_current_page_changes(
    tmp_path: Path,
) -> None:
    authority, binding = _completed_lineage(tmp_path)
    created = authority._create_exact_v1(binding.delivery_identity)
    snapshot = authority._repository._load_revisioned(binding.project_id)
    changed_page = snapshot.project.page(1).model_copy(
        update={
            "state": PageState.GENERATED,
            "prompt": {"positive": "current generated page"},
            "image": {"synthetic": "R20 has no application authority"},
        }
    )
    authority._repository._conditional_commit(snapshot, snapshot.project.replace_page(changed_page))

    historical = authority._replay_historical_binding_exact_v1(binding.delivery_identity)

    assert historical.binding_identity == created.binding_identity
    assert historical.application_binding_identity == created.projection["application_binding_identity"]
    assert historical.historical_prompt_digest == created.projection["prompt_digest"]
    assert historical.historical_page_revision == created.projection["page_revision"]
    with pytest.raises(ValueError, match="CORRUPT"):
        authority._replay_exact_v1(binding.delivery_identity)


def test_r20_historical_replay_never_reads_current_page(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, binding = _completed_lineage(tmp_path)
    authority._create_exact_v1(binding.delivery_identity)

    def current_page_read_is_forbidden(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("R20 historical replay must not read the current page")

    monkeypatch.setattr(
        RealDeliveryBindingAuthorityV1, "_reread_current_page_exact_v1", current_page_read_is_forbidden
    )

    historical = authority._replay_historical_binding_exact_v1(binding.delivery_identity)

    assert historical.delivery_identity == binding.delivery_identity
    assert historical.project_id == binding.project_id
    assert historical.page_id == binding.page_id


def test_r20_private_attempt_selector_replays_the_same_exact_historical_binding(
    tmp_path: Path,
) -> None:
    authority, binding = _completed_lineage(tmp_path)
    authority._create_exact_v1(binding.delivery_identity)

    historical = authority._replay_historical_binding_for_attempt_v1(binding.attempt_id)

    assert historical.delivery_identity == binding.delivery_identity
    assert historical.attempt_id == binding.attempt_id


def test_r20_historical_replay_reopens_read_only_and_is_restart_stable(tmp_path: Path) -> None:
    authority, binding = _completed_lineage(tmp_path)
    authority._create_exact_v1(binding.delivery_identity)
    binding_before = authority._database_path.read_bytes()
    evidence_path = authority._evidence_database_path()
    evidence_before = evidence_path.read_bytes()

    factory, composition = _factory_composition(tmp_path)
    reopened = factory.construct_authority(composition)
    historical = reopened._replay_historical_binding_exact_v1(binding.delivery_identity)

    assert historical.delivery_identity == binding.delivery_identity
    assert reopened._database_path.read_bytes() == binding_before
    assert evidence_path.read_bytes() == evidence_before


@pytest.mark.parametrize(
    ("key", "value"),
    (
        ("delivery_identity", "b" * 64),
        ("attempt_id", "attempt:r20:other"),
        ("asset_id", "asset:r20:other"),
        ("evidence_identity", "e" * 64),
        ("application_binding_identity", "1" * 64),
    ),
)
def test_r20_historical_replay_rejects_cross_binding_substitution(
    tmp_path: Path, key: str, value: object
) -> None:
    authority, binding = _completed_lineage(tmp_path)
    authority._create_exact_v1(binding.delivery_identity)
    _replace_stored_projection_dimension(
        authority, binding.delivery_identity, key=key, value=value
    )

    with pytest.raises(ValueError, match="CORRUPT"):
        authority._replay_historical_binding_exact_v1(binding.delivery_identity)


def test_r20_historical_replay_missing_record_has_one_closed_outcome(tmp_path: Path) -> None:
    authority, _binding = _completed_lineage(tmp_path)

    with pytest.raises(ValueError, match="NOT_FOUND"):
        authority._replay_historical_binding_exact_v1("a" * 64)


def test_r20_historical_replay_completed_i02_without_r18_record_requires_recovery(
    tmp_path: Path,
) -> None:
    authority, binding = _completed_lineage(tmp_path)

    with pytest.raises(ValueError, match="RECOVERY_REQUIRED"):
        authority._replay_historical_binding_exact_v1(binding.delivery_identity)


def test_r20_historical_replay_missing_fixed_evidence_requires_recovery(tmp_path: Path) -> None:
    authority, binding = _completed_lineage(tmp_path)
    authority._create_exact_v1(binding.delivery_identity)
    authority._evidence_database_path().unlink()

    with pytest.raises(ValueError, match="RECOVERY_REQUIRED"):
        authority._replay_historical_binding_exact_v1(binding.delivery_identity)


def test_r20_historical_replay_rejects_live_lease_size_disagreement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, binding = _completed_lineage(tmp_path)
    authority._create_exact_v1(binding.delivery_identity)

    class WrongSizeLease:
        _identity = SimpleNamespace(size=len(_IMAGE_BYTES) + 1)

        def release(self) -> None:
            return None

    def wrong_size_lease(*args: object, **kwargs: object) -> WrongSizeLease:
        del args, kwargs
        return WrongSizeLease()

    monkeypatch.setattr(
        LocalDurableAssetOwner, "_verify_for_generated_application", wrong_size_lease
    )

    with pytest.raises(ValueError, match="CORRUPT"):
        authority._replay_historical_binding_exact_v1(binding.delivery_identity)


def test_r20_historical_replay_binding_store_lock_requires_recovery(tmp_path: Path) -> None:
    authority, binding = _completed_lineage(tmp_path)
    authority._create_exact_v1(binding.delivery_identity)
    lock = sqlite3.connect(authority._database_path, timeout=0.0, isolation_level=None)
    try:
        lock.execute("BEGIN EXCLUSIVE")
        with pytest.raises(ValueError, match="RECOVERY_REQUIRED"):
            authority._replay_historical_binding_exact_v1(binding.delivery_identity)
    finally:
        lock.rollback()
        lock.close()


def test_r20_historical_replay_rejects_malformed_selector(tmp_path: Path) -> None:
    authority, _binding = _completed_lineage(tmp_path)

    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        authority._replay_historical_binding_exact_v1("not-a-delivery-identity")


@pytest.mark.parametrize(
    ("key", "value"),
    (
        ("delivery_identity", "b" * 64),
        ("attempt_id", "attempt:r18:other"),
        ("canonical_result_identity", "c" * 64),
        ("i02_completion_sequence", 999),
        ("i02_completion_event_digest", "d" * 64),
        ("logical_output_id", "output:r18:other"),
        ("evidence_identity", "e" * 64),
        ("evidence_persistence_identity", "f" * 64),
        ("asset_id", "asset:generated:other"),
        ("asset_registration_digest", "1" * 64),
        ("asset_sha256", "2" * 64),
        ("expected_byte_length", 999),
        ("media_type", "image/jpeg"),
        ("project_id", "project-r18-other"),
        ("page_id", "2"),
        ("target_page_reference", "target:r18:other"),
        ("page_revision", 999),
        ("page_fingerprint", "3" * 64),
        ("application_binding_identity", "4" * 64),
    ),
)
def test_each_readable_stored_cross_binding_dimension_is_corrupt(
    tmp_path: Path, key: str, value: object
) -> None:
    """One altered source fact must never authenticate through a coherent forged row."""

    authority, binding = _completed_lineage(tmp_path)
    authority._create_exact_v1(binding.delivery_identity)
    _replace_stored_projection_dimension(
        authority, binding.delivery_identity, key=key, value=value
    )

    with pytest.raises(ValueError, match="CORRUPT"):
        authority._replay_exact_v1(binding.delivery_identity)


@pytest.mark.parametrize(
    ("column", "replacement"),
    (
        ("provider_reference", "provider:r18:other"),
        ("binding_fingerprint", "0" * 64),
    ),
)
def test_readable_evidence_provider_or_fingerprint_disagreement_is_corrupt(
    tmp_path: Path, column: str, replacement: str
) -> None:
    authority, binding = _completed_lineage(tmp_path)
    authority._create_exact_v1(binding.delivery_identity)
    connection = sqlite3.connect(authority._evidence_database_path())
    try:
        connection.execute(
            f"UPDATE generation_evidence SET {column} = ? WHERE attempt_id = ?",
            (replacement, binding.attempt_id),
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(ValueError, match="CORRUPT"):
        authority._replay_exact_v1(binding.delivery_identity)


def test_readable_wrong_live_lease_size_is_corrupt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, binding = _completed_lineage(tmp_path)
    authority._create_exact_v1(binding.delivery_identity)

    class WrongSizeLease:
        _identity = SimpleNamespace(size=len(_IMAGE_BYTES) + 1)

        def release(self) -> None:
            return None

    def wrong_size_lease(*args: object, **kwargs: object) -> WrongSizeLease:
        del args, kwargs
        return WrongSizeLease()

    monkeypatch.setattr(
        LocalDurableAssetOwner, "_verify_for_generated_application", wrong_size_lease
    )

    with pytest.raises(ValueError, match="CORRUPT"):
        authority._replay_exact_v1(binding.delivery_identity)


def test_unavailable_evidence_prevents_creation_without_partial_r18_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, binding = _completed_lineage(tmp_path)
    missing = tmp_path / "unavailable" / "generation-evidence.sqlite3"
    monkeypatch.setattr(
        RealDeliveryBindingAuthorityV1, "_evidence_database_path", lambda _self: missing
    )

    with pytest.raises(ValueError, match="RECOVERY_REQUIRED"):
        authority._create_exact_v1(binding.delivery_identity)
    connection = sqlite3.connect(authority._database_path)
    try:
        count = connection.execute("SELECT COUNT(*) FROM real_delivery_binding_records").fetchone()
    finally:
        connection.close()
    assert count == (0,)


def test_temporary_owner_read_failure_is_recovery_required_and_read_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, binding = _completed_lineage(tmp_path)
    authority._create_exact_v1(binding.delivery_identity)
    before = authority._database_path.read_bytes()

    def unavailable_owner(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise OSError("temporary owner read failure")

    monkeypatch.setattr(
        LocalDurableAssetOwner, "_verify_for_generated_application", unavailable_owner
    )

    with pytest.raises(ValueError, match="RECOVERY_REQUIRED"):
        authority._replay_exact_v1(binding.delivery_identity)
    assert authority._database_path.read_bytes() == before


@pytest.mark.parametrize("target", ("binding", "evidence"))
def test_locked_authoritative_store_is_recovery_required(
    tmp_path: Path, target: str
) -> None:
    authority, binding = _completed_lineage(tmp_path)
    authority._create_exact_v1(binding.delivery_identity)
    database = (
        authority._database_path if target == "binding" else authority._evidence_database_path()
    )
    connection = sqlite3.connect(database, timeout=0.0, isolation_level=None)
    try:
        connection.execute("BEGIN EXCLUSIVE")
        with pytest.raises(ValueError, match="RECOVERY_REQUIRED"):
            authority._replay_exact_v1(binding.delivery_identity)
    finally:
        connection.rollback()
        connection.close()


def test_conflicting_current_facts_do_not_overwrite_a_valid_binding(tmp_path: Path) -> None:
    authority, binding = _completed_lineage(tmp_path)
    created = authority._create_exact_v1(binding.delivery_identity)
    before = authority._database_path.read_bytes()
    connection = sqlite3.connect(authority._evidence_database_path())
    try:
        connection.execute(
            "UPDATE generation_evidence SET provider_reference = ? WHERE attempt_id = ?",
            ("provider:r18:other", binding.attempt_id),
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(ValueError, match="CORRUPT"):
        authority._create_exact_v1(binding.delivery_identity)
    assert authority._database_path.read_bytes() == before
    connection = sqlite3.connect(authority._database_path)
    try:
        row = connection.execute(
            "SELECT binding_identity FROM real_delivery_binding_records WHERE delivery_identity = ?",
            (binding.delivery_identity,),
        ).fetchone()
    finally:
        connection.close()
    assert row == (created.binding_identity,)


def test_raw_tuple_cannot_bypass_the_factory_issued_grant(tmp_path: Path) -> None:
    factory, composition = _factory_composition(tmp_path)
    raw_constructor = binding_authority._construct_from_factory_issued_grant_v1

    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        raw_constructor(
            cast(PrivateR18CompositionFactoryV1, composition.repository),
            cast(r18_construction._R18ConstructionGrantV1, composition.owner),
        )
    authority = factory.construct_authority(composition)
    assert isinstance(authority, RealDeliveryBindingAuthorityV1)
    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        raw_constructor(
            factory,
            cast(r18_construction._R18ConstructionGrantV1, composition.capability),
        )
    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        RealDeliveryBindingAuthorityV1(
            cast(PrivateR18CompositionFactoryV1, composition),
            cast(r18_construction._R18ConstructionGrantV1, composition),
        )


def test_imported_marker_and_manually_constructed_grant_are_not_authority(tmp_path: Path) -> None:
    factory, composition = _factory_composition(tmp_path)

    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        r18_construction._R18ConstructionGrantV1(
            r18_construction._GRANT_MARKER,
            composition.repository,
            composition.owner,
            composition.journal,
            composition.repository._next_generation_normal_execution_owner_root(),
        )
    forged = object.__new__(r18_construction._R18ConstructionGrantV1)
    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        binding_authority._construct_from_factory_issued_grant_v1(factory, forged)
    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        RealDeliveryBindingAuthorityV1(factory, forged)
    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        RealDeliveryBindingAuthorityV1(cast(PrivateR18CompositionFactoryV1, forged))
    assert isinstance(factory.construct_authority(composition), RealDeliveryBindingAuthorityV1)


def test_factory_registry_rejects_cross_factory_or_copied_grant(tmp_path: Path) -> None:
    first_factory, first = _factory_composition(tmp_path / "first")
    second_factory, _ = _factory_composition(tmp_path / "second")
    grant = first_factory._consume_exact_v1(first)

    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        binding_authority._construct_from_factory_issued_grant_v1(second_factory, grant)
    with pytest.raises(TypeError, match="not copyable"):
        __import__("copy").copy(grant)
    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        binding_authority._construct_from_factory_issued_grant_v1(first_factory, grant)


def test_private_helper_chain_cannot_construct_without_live_lock_invocation(tmp_path: Path) -> None:
    """A consumed or armed grant alone never reaches the final R18 inlet."""

    factory, composition = _factory_composition(tmp_path)
    grant = factory._consume_exact_v1(composition)

    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        factory._arm_issued_grant_under_root_lock_v1(grant)
    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        binding_authority._construct_from_factory_issued_grant_v1(factory, grant)


def test_forged_or_copied_lock_invocation_is_not_authority(tmp_path: Path) -> None:
    factory, composition = _factory_composition(tmp_path)
    grant = factory._consume_exact_v1(composition)
    forged = object.__new__(r18_construction._R18LockHeldInvocationV1)

    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        binding_authority._construct_from_factory_issued_grant_v1(factory, grant, forged)
    with pytest.raises(TypeError, match="not copyable"):
        __import__("copy").copy(forged)


def test_lock_invocation_rejects_cross_factory_and_cross_root_substitution(tmp_path: Path) -> None:
    first_factory, first = _factory_composition(tmp_path / "first")
    second_factory, second = _factory_composition(tmp_path / "second")
    first_grant = first_factory._consume_exact_v1(first)
    second_grant = second_factory._consume_exact_v1(second)
    first_root = first_factory._normal_root_for_issued_grant_v1(first_grant)
    first_lock = r18_construction._normal_root_lock_v1(first_root)

    with first_lock:
        invocation = first_factory._active_lock_invocation_v1(first_grant, first_root, first_lock)
        try:
            with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
                binding_authority._construct_from_factory_issued_grant_v1(
                    second_factory, second_grant, invocation
                )
        finally:
            first_factory._invalidate_lock_invocation_v1(invocation)

    same_factory, one = _factory_composition(tmp_path / "same-factory")
    two = same_factory.create((tmp_path / "same-factory-other").resolve())
    one_grant = same_factory._consume_exact_v1(one)
    two_grant = same_factory._consume_exact_v1(two)
    one_root = same_factory._normal_root_for_issued_grant_v1(one_grant)
    one_lock = r18_construction._normal_root_lock_v1(one_root)
    with one_lock:
        invocation = same_factory._active_lock_invocation_v1(one_grant, one_root, one_lock)
        try:
            with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
                binding_authority._construct_from_factory_issued_grant_v1(
                    same_factory, two_grant, invocation
                )
        finally:
            same_factory._invalidate_lock_invocation_v1(invocation)


def test_expired_or_reused_lock_invocation_is_not_authority(tmp_path: Path) -> None:
    factory, composition = _factory_composition(tmp_path / "first")
    grant = factory._consume_exact_v1(composition)
    root = factory._normal_root_for_issued_grant_v1(grant)
    root_lock = r18_construction._normal_root_lock_v1(root)
    with root_lock:
        invocation = factory._active_lock_invocation_v1(grant, root, root_lock)
        factory._arm_issued_grant_under_root_lock_v1(grant, invocation)
        factory._invalidate_lock_invocation_v1(invocation)

        with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
            binding_authority._construct_from_factory_issued_grant_v1(factory, grant, invocation)

    next_composition = factory.create((tmp_path / "second").resolve())
    next_grant = factory._consume_exact_v1(next_composition)
    next_root = factory._normal_root_for_issued_grant_v1(next_grant)
    with r18_construction._normal_root_lock_v1(next_root):
        with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
            binding_authority._construct_from_factory_issued_grant_v1(
                factory, next_grant, invocation
            )


def test_canonical_factory_construction_uses_a_live_root_lock(tmp_path: Path) -> None:
    factory, composition = _factory_composition(tmp_path)
    observed: list[bool] = []
    inlet = binding_authority._construct_from_factory_issued_grant_v1

    def observe_live_lock(
        supplied_factory: PrivateR18CompositionFactoryV1,
        grant: r18_construction._R18ConstructionGrantV1,
        invocation: r18_construction._R18LockHeldInvocationV1 | None = None,
    ) -> RealDeliveryBindingAuthorityV1:
        assert invocation is not None
        supplied_factory._require_active_lock_invocation_v1(grant, invocation)
        observed.append(True)
        return inlet(supplied_factory, grant, invocation)

    binding_authority._construct_from_factory_issued_grant_v1 = observe_live_lock
    try:
        authority = factory.construct_authority(composition)
    finally:
        binding_authority._construct_from_factory_issued_grant_v1 = inlet

    assert isinstance(authority, RealDeliveryBindingAuthorityV1)
    assert observed == [True]


def test_exact_limit_binding_json_is_accepted_and_over_limit_is_rejected() -> None:
    base = _synthetic_binding_record("")
    padding = binding_authority._MAX_BINDING_JSON_BYTES - len(base.binding_json.encode("utf-8"))
    exact = _synthetic_binding_record("p" * padding)

    assert len(exact.binding_json.encode("utf-8")) == binding_authority._MAX_BINDING_JSON_BYTES
    with pytest.raises(ValueError, match="CORRUPT"):
        _synthetic_binding_record("p" * (padding + 1))


def test_oversized_readable_binding_json_is_corrupt(tmp_path: Path) -> None:
    authority, binding = _completed_lineage(tmp_path)
    authority._create_exact_v1(binding.delivery_identity)
    connection = sqlite3.connect(authority._database_path)
    try:
        connection.execute(
            "UPDATE real_delivery_binding_records SET binding_json = ?",
            ("x" * (binding_authority._MAX_BINDING_JSON_BYTES + 1),),
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(ValueError, match="CORRUPT"):
        authority._replay_exact_v1(binding.delivery_identity)


def test_oversized_creation_record_is_rejected_without_partial_durable_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, binding = _completed_lineage(tmp_path)
    valid = _synthetic_binding_record("provider:r18:size")
    oversized = replace(
        valid,
        binding_json="x" * (binding_authority._MAX_BINDING_JSON_BYTES + 1),
    )

    def oversized_record(*args: object, **kwargs: object) -> binding_authority._BindingRecordV1:
        del args, kwargs
        return oversized

    monkeypatch.setattr(
        RealDeliveryBindingAuthorityV1, "_authenticated_record_v1", oversized_record
    )
    with pytest.raises(ValueError, match="CORRUPT"):
        authority._create_exact_v1(binding.delivery_identity)
    connection = sqlite3.connect(authority._database_path)
    try:
        count = connection.execute("SELECT COUNT(*) FROM real_delivery_binding_records").fetchone()
    finally:
        connection.close()
    assert count == (0,)


def test_replay_with_no_r18_record_and_no_i02_lineage_is_not_found(tmp_path: Path) -> None:
    factory, composition = _factory_composition(tmp_path)
    authority = factory.construct_authority(composition)
    before = authority._database_path.read_bytes()

    with pytest.raises(ValueError, match="NOT_FOUND"):
        authority._replay_exact_v1("a" * 64)
    assert authority._database_path.read_bytes() == before


def test_replay_with_missing_r18_and_incomplete_or_completed_i02_is_recovery_required(
    tmp_path: Path,
) -> None:
    factory, composition = _factory_composition(tmp_path / "incomplete")
    incomplete = factory.construct_authority(composition)
    binding = _i02_binding()
    composition.journal._begin_delivery_v1(binding)
    with pytest.raises(ValueError, match="RECOVERY_REQUIRED"):
        incomplete._replay_exact_v1(binding.delivery_identity)

    completed, completed_binding = _completed_lineage(tmp_path / "completed")
    with pytest.raises(ValueError, match="RECOVERY_REQUIRED"):
        completed._replay_exact_v1(completed_binding.delivery_identity)


def test_missing_readable_evidence_row_is_recovery_required_without_r18_write(tmp_path: Path) -> None:
    authority, binding = _completed_lineage(tmp_path)
    connection = sqlite3.connect(authority._evidence_database_path())
    try:
        connection.execute("DELETE FROM generation_evidence WHERE attempt_id = ?", (binding.attempt_id,))
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(ValueError, match="RECOVERY_REQUIRED"):
        authority._create_exact_v1(binding.delivery_identity)
    connection = sqlite3.connect(authority._database_path)
    try:
        count = connection.execute("SELECT COUNT(*) FROM real_delivery_binding_records").fetchone()
    finally:
        connection.close()
    assert count == (0,)


def test_readable_owner_structural_integrity_failure_is_corrupt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, binding = _completed_lineage(tmp_path)
    authority._create_exact_v1(binding.delivery_identity)

    def mismatch(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise _AssetVerificationIntegrityFailure("unrelated diagnostic text")

    monkeypatch.setattr(LocalDurableAssetOwner, "_verify_for_generated_application", mismatch)
    with pytest.raises(ValueError, match="CORRUPT"):
        authority._replay_exact_v1(binding.delivery_identity)


def test_actual_owner_binding_integrity_failure_is_structural_and_corrupt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, binding = _completed_lineage(tmp_path)
    authority._create_exact_v1(binding.delivery_identity)
    original = LocalDurableAssetOwner._verify_for_generated_application

    def wrong_provider(
        owner: LocalDurableAssetOwner, **kwargs: object
    ) -> object:
        kwargs["provider_reference"] = "provider:other"
        return original(owner, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(LocalDurableAssetOwner, "_verify_for_generated_application", wrong_provider)
    with pytest.raises(ValueError, match="CORRUPT"):
        authority._replay_exact_v1(binding.delivery_identity)


@pytest.mark.parametrize(
    "owner_error",
    ("AUTHORITY_REJECTED", "CORRUPT", "CONFLICT", "RECOVERY_REQUIRED"),
)
def test_readable_owner_message_text_cannot_select_r18_taxonomy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, owner_error: str
) -> None:
    authority, binding = _completed_lineage(tmp_path)
    authority._create_exact_v1(binding.delivery_identity)

    def unavailable(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise ValueError(owner_error)

    monkeypatch.setattr(LocalDurableAssetOwner, "_verify_for_generated_application", unavailable)
    with pytest.raises(ValueError, match="RECOVERY_REQUIRED"):
        authority._replay_exact_v1(binding.delivery_identity)


def test_readable_target_or_state_page_mismatch_is_corrupt(tmp_path: Path) -> None:
    authority, binding = _completed_lineage(tmp_path)
    authority._create_exact_v1(binding.delivery_identity)
    snapshot = authority._repository._load_revisioned(binding.project_id)
    page = snapshot.project.page(1).model_copy(
        update={"metadata": {"future_generation_target_reference": "target:r18:other"}}
    )
    authority._repository._conditional_commit(snapshot, snapshot.project.replace_page(page))

    with pytest.raises(ValueError, match="CORRUPT"):
        authority._replay_exact_v1(binding.delivery_identity)


def test_unavailable_page_read_is_recovery_required(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, binding = _completed_lineage(tmp_path)
    authority._create_exact_v1(binding.delivery_identity)

    def unavailable_page(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise OSError("temporary page read failure")

    monkeypatch.setattr(type(authority._repository), "_load_revisioned", unavailable_page)
    with pytest.raises(ValueError, match="RECOVERY_REQUIRED"):
        authority._replay_exact_v1(binding.delivery_identity)


def test_cross_factory_same_root_construction_serializes_and_different_roots_do_not_share_lock(
    tmp_path: Path,
) -> None:
    first_factory, first = _factory_composition(tmp_path / "same")
    second_factory, second = _factory_composition(tmp_path / "same")
    barrier = threading.Barrier(2)
    authorities: list[RealDeliveryBindingAuthorityV1] = []
    failures: list[BaseException] = []

    def construct(
        factory: PrivateR18CompositionFactoryV1, composition: _R18CompositionV1
    ) -> None:
        try:
            barrier.wait()
            authorities.append(factory.construct_authority(composition))
        except BaseException as error:
            failures.append(error)

    one = threading.Thread(target=construct, args=(first_factory, first))
    two = threading.Thread(target=construct, args=(second_factory, second))
    one.start()
    two.start()
    one.join()
    two.join()

    assert not failures
    assert len(authorities) == 2
    other_factory, other = _factory_composition(tmp_path / "other")
    assert r18_construction._normal_root_lock_v1(
        first.repository._next_generation_normal_execution_owner_root()
    ) is not r18_construction._normal_root_lock_v1(
        other.repository._next_generation_normal_execution_owner_root()
    )
    other_factory.construct_authority(other)


@pytest.mark.parametrize("foreign_field", ("repository", "owner", "journal"))
def test_invalid_tuple_component_preserves_the_live_capability(
    tmp_path: Path, foreign_field: str
) -> None:
    factory, composition = _factory_composition(tmp_path / "valid")
    _, foreign = _factory_composition(tmp_path / "foreign")
    presentation = _R18CompositionV1(
        repository=foreign.repository if foreign_field == "repository" else composition.repository,
        owner=foreign.owner if foreign_field == "owner" else composition.owner,
        journal=foreign.journal if foreign_field == "journal" else composition.journal,
        capability=composition.capability,
    )

    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        factory.construct_authority(presentation)
    assert isinstance(factory.construct_authority(composition), RealDeliveryBindingAuthorityV1)
    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        factory.construct_authority(composition)


@pytest.mark.parametrize("foreign_root", ("same", "other"))
def test_same_root_or_cross_composition_rejection_preserves_valid_capability(
    tmp_path: Path, foreign_root: str
) -> None:
    factory, composition = _factory_composition(tmp_path / "same")
    other_path = tmp_path / ("same" if foreign_root == "same" else "other")
    _, foreign = _factory_composition(other_path)
    presentation = _R18CompositionV1(
        repository=foreign.repository,
        owner=foreign.owner,
        journal=foreign.journal,
        capability=composition.capability,
    )

    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        factory.construct_authority(presentation)
    assert isinstance(factory.construct_authority(composition), RealDeliveryBindingAuthorityV1)


def test_invalid_presentation_does_not_mutate_unrelated_live_capability(tmp_path: Path) -> None:
    factory, first = _factory_composition(tmp_path / "first")
    second = factory.create((tmp_path / "second").resolve())
    presentation = _R18CompositionV1(
        repository=second.repository,
        owner=second.owner,
        journal=second.journal,
        capability=first.capability,
    )

    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        factory.construct_authority(presentation)
    assert isinstance(factory.construct_authority(first), RealDeliveryBindingAuthorityV1)
    assert isinstance(factory.construct_authority(second), RealDeliveryBindingAuthorityV1)
