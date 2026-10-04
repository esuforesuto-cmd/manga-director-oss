from __future__ import annotations

from pathlib import Path

import pytest

from manga_director.domain.project import Project
from manga_director.production.future_real_delivery_r25_trusted_pairing import (
    _construct_localfile_r25_composition_v1,
    _consume_r30_restart_ingress_and_materialize_v1,
    _issue_r30_restart_ingress_v1,
    _require_exact_localfile_r25_composition_v1,
)
from manga_director.production.next_generation_workflow_application_ledger import (
    WorkflowApplicationLedgerBindingDTO,
    _WorkflowApplicationLedgerObservationV1,
)
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.repositories.local_file_durability import _R27RevisionPublicationRequest


def _repository_with_committed_r27(tmp_path: Path) -> LocalFileRepository:
    repository = LocalFileRepository(tmp_path)
    repository.save(Project(id="r25-pairing", title="legacy"))
    snapshot = repository._load_revisioned("r25-pairing")
    request = _R27RevisionPublicationRequest(
        repository_pair=repository._r27_repository_pair,
        application_binding_identity="a" * 64,
        attempt_id="attempt:r25-pairing",
        project_id="r25-pairing",
        page_id="page-01",
        target_page_reference="page:1",
        source_state="PromptBuilt",
        target_state="Generated",
        expected_revision=snapshot.revision,
        expected_aggregate_fingerprint=snapshot.fingerprint,
    )
    repository._activate_and_conditional_commit_r27(
        snapshot, Project(id="r25-pairing", title="framed"), request
    )
    return repository


def test_trusted_pairing_binds_one_exact_repository_instance(tmp_path: Path) -> None:
    repository = LocalFileRepository(tmp_path)

    pairing = _construct_localfile_r25_composition_v1(repository)

    assert _require_exact_localfile_r25_composition_v1(pairing, repository) is pairing
    assert pairing._r18_authority._repository is repository
    assert pairing._r20_reader._repository is repository
    assert pairing._r27_reader._repository is repository
    assert pairing._r25_service._store is pairing._r25_store


def test_trusted_pairing_rejects_same_root_replacement_repository(tmp_path: Path) -> None:
    repository = LocalFileRepository(tmp_path)
    replacement = LocalFileRepository(tmp_path)
    pairing = _construct_localfile_r25_composition_v1(repository)
    database_before = pairing._r25_store._database_path.read_bytes()

    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        _require_exact_localfile_r25_composition_v1(pairing, replacement)

    assert pairing._r25_store._database_path.read_bytes() == database_before


def test_trusted_pairing_rejects_cross_composition_tuple(tmp_path: Path) -> None:
    first = LocalFileRepository(tmp_path / "first")
    second = LocalFileRepository(tmp_path / "second")
    first_pairing = _construct_localfile_r25_composition_v1(first)
    second_pairing = _construct_localfile_r25_composition_v1(second)

    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        _require_exact_localfile_r25_composition_v1(first_pairing, second)
    assert _require_exact_localfile_r25_composition_v1(second_pairing, second) is second_pairing


def test_committed_r27_reader_returns_only_valid_durable_committed_lineage(tmp_path: Path) -> None:
    repository = _repository_with_committed_r27(tmp_path)
    pairing = _construct_localfile_r25_composition_v1(repository)

    facts = pairing._r27_reader._read_exact_committed_v1("r25-pairing")

    assert facts.project_id == "r25-pairing"
    assert facts.revision == 2
    assert len(facts.physical_aggregate_fingerprint) == 64
    assert len(facts.authoritative_envelope_fingerprint) == 64
    assert len(facts.lineage_identity) == 64


def test_committed_r27_reader_rejects_legacy_state(tmp_path: Path) -> None:
    repository = LocalFileRepository(tmp_path)
    repository.save(Project(id="legacy", title="legacy"))
    pairing = _construct_localfile_r25_composition_v1(repository)

    with pytest.raises(ValueError, match="RECOVERY_REQUIRED"):
        pairing._r27_reader._read_exact_committed_v1("legacy")


def test_committed_r27_reader_rejects_activation_and_frame_without_committed_record(
    tmp_path: Path,
) -> None:
    repository = _repository_with_committed_r27(tmp_path)
    repository._revision_store._committed_path("r25-pairing").unlink()
    pairing = _construct_localfile_r25_composition_v1(repository)

    with pytest.raises(ValueError, match="RECOVERY_REQUIRED"):
        pairing._r27_reader._read_exact_committed_v1("r25-pairing")


def test_restart_ingress_rejects_foreign_composition_and_lookalike(tmp_path: Path) -> None:
    first = LocalFileRepository(tmp_path / "first")
    second = LocalFileRepository(tmp_path / "second")
    first_pairing = _construct_localfile_r25_composition_v1(first)
    observation = object.__new__(_WorkflowApplicationLedgerObservationV1)
    object.__setattr__(observation, "outcome", "PREPARED")
    binding = WorkflowApplicationLedgerBindingDTO(
        attempt_id="attempt:r30:ingress",
        authorization_id="authorization:r30:ingress",
        project_id="project:r30:ingress",
        page_id="1",
        target_page_reference="page:1",
        provider_reference="provider:r30:ingress",
        output_asset_id="output:r30:ingress",
        source_state="PromptBuilt",
        target_state="Generated",
    )

    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        _issue_r30_restart_ingress_v1(first_pairing, second, binding, observation)
    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        _consume_r30_restart_ingress_and_materialize_v1(first_pairing, first, object(), object())
