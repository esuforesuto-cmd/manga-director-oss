from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from manga_director.domain.project import Project
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.repositories.local_file_durability import (
    LocalFileDurabilityError,
    LocalFileRevisionStore,
    _canonical_json_bytes,
    _classify_r29_pre_reconciliation,
    _parse_r29_activation_state,
    _R27RevisionPublicationRequest,
    _R29ActivationState,
    _R29PreReconciliationSnapshot,
)
from manga_director.workflow.durable_execution import LocalFileDurablePageStore
from manga_director.workflow.localfile_aggregate_mutation import LocalFileAggregateMutationStore


def _prepared() -> _R29ActivationState:
    return _R29ActivationState(
        activation_binding_identity="a" * 64,
        activation_page_id="page-01",
        expected_aggregate_fingerprint="b" * 64,
        expected_revision=7,
        project_id="project-01",
        state="ACTIVATION_PREPARED",
    )


def _r29_request(repository: LocalFileRepository, *, revision: int, fingerprint: str) -> _R27RevisionPublicationRequest:
    return _R27RevisionPublicationRequest(
        repository_pair=repository._r27_repository_pair,
        application_binding_identity="a" * 64,
        attempt_id="attempt-01",
        project_id="project-01",
        page_id="page-01",
        target_page_reference="page:1",
        source_state="PromptBuilt",
        target_state="Generated",
        expected_revision=revision,
        expected_aggregate_fingerprint=fingerprint,
    )


def test_r29_prepared_normative_vector_is_closed() -> None:
    value = _prepared()
    payload = _canonical_json_bytes(value.as_dict())

    assert len(payload) == 382
    assert hashlib.sha256(payload).hexdigest() == "df543bd409fbc91651b5aa8ed8d50847f352f9ccbf9d81a4660944a4d99cb441"
    assert _parse_r29_activation_state(value.as_dict()) == value


def test_r29_committed_normative_vector_is_closed() -> None:
    value = _R29ActivationState(
        activation_binding_identity="a" * 64,
        activation_page_id="page-01",
        expected_aggregate_fingerprint="b" * 64,
        expected_revision=7,
        project_id="project-01",
        state="R27_COMMITTED",
        committed_aggregate_fingerprint="c" * 64,
        committed_revision=8,
        source_lineage_identity="d" * 64,
    )
    payload = _canonical_json_bytes(value.as_dict())

    assert len(payload) == 593
    assert hashlib.sha256(payload).hexdigest() == "d4e11e673f5f5d62c8962c2189ec92f57dcc0255273c4f577ab37d515993977c"
    assert _parse_r29_activation_state(value.as_dict()) == value


def test_r29_activation_rejects_schema_and_binding_corruption() -> None:
    malformed = _prepared().as_dict()
    malformed["extra"] = "forbidden"
    with pytest.raises(LocalFileDurabilityError, match="r29_activation_schema_invalid"):
        _parse_r29_activation_state(malformed)

    invalid = _prepared().as_dict()
    invalid["expected_revision"] = True
    with pytest.raises(LocalFileDurabilityError, match="r29_activation_schema_invalid"):
        _parse_r29_activation_state(invalid)


def test_r29_activation_path_is_revisionstore_owned(tmp_path: Path) -> None:
    store = LocalFileRevisionStore(tmp_path)
    value = _prepared()

    store._write_r29_activation(value)

    assert store._read_r29_activation("project-01") == value
    assert store._activation_path("project-01").parent == tmp_path / "_durability"


def test_r29_activation_lifecycle_is_exact_and_monotonic(tmp_path: Path) -> None:
    store = LocalFileRevisionStore(tmp_path)
    prepared = _prepared()
    committed = _R29ActivationState(
        activation_binding_identity=prepared.activation_binding_identity,
        activation_page_id=prepared.activation_page_id,
        expected_aggregate_fingerprint=prepared.expected_aggregate_fingerprint,
        expected_revision=prepared.expected_revision,
        project_id=prepared.project_id,
        state="R27_COMMITTED",
        committed_aggregate_fingerprint="c" * 64,
        committed_revision=8,
        source_lineage_identity="d" * 64,
    )

    store._prepare_r29_activation(prepared)
    store._prepare_r29_activation(prepared)
    store._commit_r29_activation(committed)
    store._commit_r29_activation(committed)

    with pytest.raises(LocalFileDurabilityError, match="r29_activation_monotonicity_invalid"):
        store._remove_r29_prepared_activation("project-01")
    with pytest.raises(LocalFileDurabilityError, match="r29_activation_transition_invalid"):
        store._prepare_r29_activation(prepared)


def test_r29_common_raw_gate_rejects_activation_state(tmp_path: Path) -> None:
    store = LocalFileRevisionStore(tmp_path)
    store._prepare_r29_activation(_prepared())

    with pytest.raises(LocalFileDurabilityError, match="r29_raw_replacement_forbidden"):
        store._assert_r29_raw_replacement_allowed("project-01", b'{"id":"project-01"}')


def test_r29_public_save_is_gated_for_an_active_project(tmp_path: Path) -> None:
    repository = LocalFileRepository(tmp_path)
    original = Project(id="project-01", title="Original")
    repository.save(original)
    repository._revision_store._prepare_r29_activation(_prepared())

    with pytest.raises(LocalFileDurabilityError, match="r29_raw_replacement_forbidden"):
        repository.save(Project(id="project-01", title="Blocked"))

    assert repository.load("project-01") == original


def test_r29_public_save_allows_a_new_legacy_project_without_activation(tmp_path: Path) -> None:
    repository = LocalFileRepository(tmp_path)
    project = Project(id="project-01", title="Legacy")

    repository.save(project)

    assert repository.load("project-01") == project


def test_r29_first_private_publication_commits_activation_after_framing(tmp_path: Path) -> None:
    repository = LocalFileRepository(tmp_path)
    initial = Project(id="project-01", title="Legacy")
    replacement = Project(id="project-01", title="Framed")
    repository.save(initial)
    snapshot = repository._load_revisioned("project-01")
    request = _R27RevisionPublicationRequest(
        repository_pair=repository._r27_repository_pair,
        application_binding_identity="a" * 64,
        attempt_id="attempt-01",
        project_id="project-01",
        page_id="page-01",
        target_page_reference="page:1",
        source_state="PromptBuilt",
        target_state="Generated",
        expected_revision=snapshot.revision,
        expected_aggregate_fingerprint=snapshot.fingerprint,
    )

    result = repository._activate_and_conditional_commit_r27(snapshot, replacement, request)

    activation = repository._revision_store._read_r29_activation("project-01")
    assert result.revision == snapshot.revision + 1
    assert activation is not None
    assert activation.state == "R27_COMMITTED"
    assert activation.committed_revision == result.revision
    assert (tmp_path / "projects" / "project-01.json").read_bytes().startswith(
        bytes.fromhex("894D445232370D0A01")
    )


@pytest.mark.parametrize(
    "adapter_type",
    (LocalFileDurablePageStore, LocalFileAggregateMutationStore),
)
def test_r29_real_durable_adapters_reject_raw_commit_while_activation_is_prepared(
    tmp_path: Path, adapter_type: type[LocalFileDurablePageStore] | type[LocalFileAggregateMutationStore]
) -> None:
    repository = LocalFileRepository(tmp_path)
    original = Project(id="project-01", title="Legacy")
    repository.save(original)
    adapter = adapter_type(repository)
    snapshot = adapter.load_revisioned("project-01")
    repository._revision_store._prepare_r29_activation(_prepared())
    aggregate_path = tmp_path / "projects" / "project-01.json"
    aggregate_before = aggregate_path.read_bytes()

    with pytest.raises(LocalFileDurabilityError, match="r29_raw_replacement_forbidden"):
        adapter.conditional_commit(snapshot, Project(id="project-01", title="Blocked"))

    assert aggregate_path.read_bytes() == aggregate_before
    assert not list(aggregate_path.parent.glob("*.tmp"))


def test_r29_pre_reconciliation_snapshot_observes_without_cleanup(tmp_path: Path) -> None:
    repository = LocalFileRepository(tmp_path)
    repository.save(Project(id="project-01", title="Legacy"))
    repository._revision_store._prepare_r29_activation(_prepared())
    aggregate_path = tmp_path / "projects" / "project-01.json"
    activation_path = repository._revision_store._activation_path("project-01")
    aggregate_before = aggregate_path.read_bytes()
    activation_before = activation_path.read_bytes()

    captured = repository._revision_store._capture_r29_pre_reconciliation_snapshot(
        "project-01", aggregate_path
    )

    assert captured.aggregate_state == "RAW"
    assert captured.activation_state == "ACTIVATION_PREPARED"
    assert captured.metadata_state == "ABSENT"
    assert aggregate_path.read_bytes() == aggregate_before
    assert activation_path.read_bytes() == activation_before


@pytest.mark.parametrize(
    ("boundary", "expected_result"),
    (
        ("before_aggregate_staging_write", "ACTIVATION_RECOVERY"),
        ("after_aggregate_durability_sync", "R27_RECONCILE"),
        ("after_committed_metadata_durability", "ACTIVATION_RECOVERY"),
    ),
)
def test_r29_reopen_classifies_before_authorized_r28_recovery(
    tmp_path: Path, boundary: str, expected_result: str
) -> None:
    repository = LocalFileRepository(tmp_path)
    repository.save(Project(id="project-01", title="Legacy"))
    snapshot = repository._load_revisioned("project-01")

    def interrupt(value: str) -> None:
        if value == boundary:
            raise LocalFileDurabilityError("injected_r29_interruption")

    repository._revision_store._r27_fault_injector = interrupt
    with pytest.raises(LocalFileDurabilityError, match="injected_r29_interruption"):
        repository._activate_and_conditional_commit_r27(
            snapshot,
            Project(id="project-01", title="Framed"),
            _r29_request(repository, revision=snapshot.revision, fingerprint=snapshot.fingerprint),
        )
    repository._revision_store._r27_fault_injector = None
    aggregate_path = tmp_path / "projects" / "project-01.json"
    before = repository._revision_store._capture_r29_pre_reconciliation_snapshot("project-01", aggregate_path)

    assert _classify_r29_pre_reconciliation(before) == expected_result
    reopened = repository._load_revisioned("project-01")

    if before.aggregate_state == "RAW":
        assert reopened.project.title == "Legacy"
        assert repository._revision_store._read_r29_activation("project-01") is None
    else:
        activation = repository._revision_store._read_r29_activation("project-01")
        assert reopened.project.title == "Framed"
        assert activation is not None and activation.state == "R27_COMMITTED"


def test_r29_ordinary_raw_v2_prepared_is_observed_before_existing_reconciliation(
    tmp_path: Path,
) -> None:
    repository = LocalFileRepository(tmp_path)
    repository.save(Project(id="project-01", title="Legacy"))
    snapshot = repository._load_revisioned("project-01")

    def interrupt(value: str) -> None:
        if value == "before_aggregate_staging_write":
            raise LocalFileDurabilityError("injected_r28_interruption")

    repository._revision_store._r27_fault_injector = interrupt
    with pytest.raises(LocalFileDurabilityError, match="injected_r28_interruption"):
        repository._conditional_commit_r27(
            snapshot,
            Project(id="project-01", title="Framed"),
            _r29_request(repository, revision=snapshot.revision, fingerprint=snapshot.fingerprint),
        )
    repository._revision_store._r27_fault_injector = None
    aggregate_path = tmp_path / "projects" / "project-01.json"
    before = repository._revision_store._capture_r29_pre_reconciliation_snapshot("project-01", aggregate_path)

    assert before.metadata_state == "V2_PREPARED"
    assert before.activation_state == "ABSENT"
    assert _classify_r29_pre_reconciliation(before) == "LEGACY"
    assert repository._load_revisioned("project-01").project.title == "Legacy"
    assert not repository._revision_store._prepared_path("project-01").exists()
    assert repository._revision_store._read_r29_activation("project-01") is None


def test_r29_f0_mismatch_fails_closed_without_prepared_cleanup(tmp_path: Path) -> None:
    repository = LocalFileRepository(tmp_path)
    repository.save(Project(id="project-01", title="Legacy"))
    snapshot = repository._load_revisioned("project-01")

    def interrupt(value: str) -> None:
        if value == "before_aggregate_staging_write":
            raise LocalFileDurabilityError("injected_r28_interruption")

    repository._revision_store._r27_fault_injector = interrupt
    with pytest.raises(LocalFileDurabilityError, match="injected_r28_interruption"):
        repository._conditional_commit_r27(
            snapshot,
            Project(id="project-01", title="Framed"),
            _r29_request(repository, revision=snapshot.revision, fingerprint=snapshot.fingerprint),
        )
    repository._revision_store._r27_fault_injector = None
    aggregate_path = tmp_path / "projects" / "project-01.json"
    prepared_path = repository._revision_store._prepared_path("project-01")
    committed_path = repository._revision_store._committed_path("project-01")
    aggregate_path.write_bytes(repository._serializer.dumps(Project(id="project-01", title="Tampered")).encode())
    before_prepared = prepared_path.read_bytes()
    before_committed = committed_path.read_bytes()
    captured = repository._revision_store._capture_r29_pre_reconciliation_snapshot("project-01", aggregate_path)

    assert captured.binding_state == "WRONG_EXPECTED_F0"
    assert _classify_r29_pre_reconciliation(captured) == "FAIL_CLOSED"
    with pytest.raises(LocalFileDurabilityError, match="r29_restart_fail_closed"):
        repository._load_revisioned("project-01")

    assert prepared_path.read_bytes() == before_prepared
    assert committed_path.read_bytes() == before_committed


def test_r29_corrupt_activation_fails_closed_without_normalization(tmp_path: Path) -> None:
    repository = LocalFileRepository(tmp_path)
    repository.save(Project(id="project-01", title="Legacy"))
    aggregate_path = tmp_path / "projects" / "project-01.json"
    activation_path = repository._revision_store._activation_path("project-01")
    activation_path.parent.mkdir(parents=True, exist_ok=True)
    activation_path.write_bytes(b'{"state":"ACTIVATION_PREPARED"}')
    aggregate_before = aggregate_path.read_bytes()
    activation_before = activation_path.read_bytes()

    captured = repository._revision_store._capture_r29_pre_reconciliation_snapshot("project-01", aggregate_path)

    assert captured.activation_state == "CORRUPT"
    assert _classify_r29_pre_reconciliation(captured) == "FAIL_CLOSED"
    with pytest.raises(LocalFileDurabilityError, match="r29_restart_fail_closed"):
        repository._load_revisioned("project-01")

    assert aggregate_path.read_bytes() == aggregate_before
    assert activation_path.read_bytes() == activation_before


_R29_ACTIVATION_CRASH_MATRIX = (
    ("before_activation_prepared_persistence", "LEGACY"),
    ("during_activation_prepared_persistence", "LEGACY"),
    ("after_activation_prepared_durability", "ACTIVATION_RECOVERY"),
    ("after_activation_prepared_durability_before_r28_prepared", "ACTIVATION_RECOVERY"),
    ("before_prepared_metadata_write", "ACTIVATION_RECOVERY"),
    ("during_prepared_metadata_write", "ACTIVATION_RECOVERY"),
    ("after_prepared_metadata_durability", "ACTIVATION_RECOVERY"),
    ("before_aggregate_staging_write", "ACTIVATION_RECOVERY"),
    ("during_aggregate_staging_write", "ACTIVATION_RECOVERY"),
    ("after_aggregate_staging_write", "ACTIVATION_RECOVERY"),
    ("after_aggregate_staging_file_sync", "ACTIVATION_RECOVERY"),
    ("before_aggregate_replace", "ACTIVATION_RECOVERY"),
    ("immediately_after_aggregate_replace", "R27_RECONCILE"),
    ("after_aggregate_durability_sync", "R27_RECONCILE"),
    ("before_persisted_byte_reread", "R27_RECONCILE"),
    ("after_reread_verification", "R27_RECONCILE"),
    ("before_committed_metadata_write", "R27_RECONCILE"),
    ("during_committed_metadata_write", "R27_RECONCILE"),
    ("after_committed_metadata_durability", "ACTIVATION_RECOVERY"),
    ("before_prepared_cleanup", "ACTIVATION_RECOVERY"),
    ("after_prepared_cleanup", "ACTIVATION_RECOVERY"),
    ("before_activation_committed_persistence", "ACTIVATION_RECOVERY"),
    ("during_activation_committed_persistence", "ACTIVATION_RECOVERY"),
    ("after_activation_committed_durability", "R27"),
    ("before_caller_acknowledgement", "R27"),
)


@pytest.mark.parametrize(("boundary", "expected"), _R29_ACTIVATION_CRASH_MATRIX)
def test_r29_activation_crash_boundaries_have_one_recoverable_durable_outcome(
    tmp_path: Path, boundary: str, expected: str
) -> None:
    repository = LocalFileRepository(tmp_path)
    repository.save(Project(id="project-01", title="Legacy"))
    snapshot = repository._load_revisioned("project-01")
    aggregate_path = tmp_path / "projects" / "project-01.json"
    prepared_path = repository._revision_store._prepared_path("project-01")
    committed_path = repository._revision_store._committed_path("project-01")

    def interrupt(value: str) -> None:
        if value == boundary:
            raise LocalFileDurabilityError(f"injected:{boundary}")

    repository._revision_store._r27_fault_injector = interrupt
    with pytest.raises(LocalFileDurabilityError, match=f"injected:{boundary}"):
        repository._activate_and_conditional_commit_r27(
            snapshot,
            Project(id="project-01", title="Framed"),
            _r29_request(repository, revision=snapshot.revision, fingerprint=snapshot.fingerprint),
        )
    repository._revision_store._r27_fault_injector = None
    captured = repository._revision_store._capture_r29_pre_reconciliation_snapshot("project-01", aggregate_path)

    assert _classify_r29_pre_reconciliation(captured) == expected
    assert all(item.suffix == ".tmp" for item in aggregate_path.parent.glob("*.tmp"))
    assert all(item.suffix == ".tmp" for item in prepared_path.parent.glob("*.tmp"))
    assert committed_path.exists()
    repository._load_revisioned("project-01")

    final_activation = repository._revision_store._read_r29_activation("project-01")
    if expected in {"R27_RECONCILE", "R27"} or captured.aggregate_state == "R27":
        assert aggregate_path.read_bytes().startswith(bytes.fromhex("894D445232370D0A01"))
        assert final_activation is not None and final_activation.state == "R27_COMMITTED"
        assert not prepared_path.exists()
    else:
        assert final_activation is None
        assert not prepared_path.exists()


def test_r29_acknowledgement_loss_cannot_create_a_second_first_publication(tmp_path: Path) -> None:
    repository = LocalFileRepository(tmp_path)
    repository.save(Project(id="project-01", title="Legacy"))
    snapshot = repository._load_revisioned("project-01")
    request = _r29_request(repository, revision=snapshot.revision, fingerprint=snapshot.fingerprint)
    aggregate_path = tmp_path / "projects" / "project-01.json"
    activation_path = repository._revision_store._activation_path("project-01")
    committed_path = repository._revision_store._committed_path("project-01")

    def interrupt(value: str) -> None:
        if value == "before_caller_acknowledgement":
            raise LocalFileDurabilityError("injected_acknowledgement_loss")

    repository._revision_store._r27_fault_injector = interrupt
    with pytest.raises(LocalFileDurabilityError, match="injected_acknowledgement_loss"):
        repository._activate_and_conditional_commit_r27(snapshot, Project(id="project-01", title="Framed"), request)
    repository._revision_store._r27_fault_injector = None
    aggregate_before = aggregate_path.read_bytes()
    activation_before = activation_path.read_bytes()
    committed_before = committed_path.read_bytes()

    assert repository._load_revisioned("project-01").revision == snapshot.revision + 1
    with pytest.raises(LocalFileDurabilityError, match="r29_raw_replacement_forbidden"):
        repository._activate_and_conditional_commit_r27(snapshot, Project(id="project-01", title="Framed"), request)

    assert aggregate_path.read_bytes() == aggregate_before
    assert activation_path.read_bytes() == activation_before
    assert committed_path.read_bytes() == committed_before


def test_r29_competing_first_activation_has_one_winner_and_no_legacy_successor(tmp_path: Path) -> None:
    repository = LocalFileRepository(tmp_path)
    repository.save(Project(id="project-01", title="Legacy"))
    winner = repository._load_revisioned("project-01")
    loser = repository._load_revisioned("project-01")
    winner_request = _r29_request(repository, revision=winner.revision, fingerprint=winner.fingerprint)
    loser_request = _R27RevisionPublicationRequest(
        repository_pair=repository._r27_repository_pair,
        application_binding_identity="c" * 64,
        attempt_id="attempt-02",
        project_id="project-01",
        page_id="page-02",
        target_page_reference="page:2",
        source_state="PromptBuilt",
        target_state="Generated",
        expected_revision=loser.revision,
        expected_aggregate_fingerprint=loser.fingerprint,
    )

    assert repository._activate_and_conditional_commit_r27(
        winner, Project(id="project-01", title="Winner"), winner_request
    ).revision == winner.revision + 1
    aggregate_path = tmp_path / "projects" / "project-01.json"
    aggregate_before = aggregate_path.read_bytes()

    with pytest.raises(LocalFileDurabilityError, match="r29_raw_replacement_forbidden"):
        repository._activate_and_conditional_commit_r27(
            loser, Project(id="project-01", title="Loser"), loser_request
        )
    with pytest.raises(LocalFileDurabilityError, match="r29_raw_replacement_forbidden"):
        repository.save(Project(id="project-01", title="Legacy Loser"))

    assert repository._load_revisioned("project-01").project.title == "Winner"
    assert aggregate_path.read_bytes() == aggregate_before


_R29_EXACT_MATRIX = (
    ("RAW", "ABSENT", "ABSENT", "LEGACY"),
    ("RAW", "ABSENT", "V1_COMMITTED", "LEGACY"),
    ("RAW", "ABSENT", "V1_PREPARED", "LEGACY"),
    ("RAW", "ABSENT", "V2_PREPARED", "LEGACY"),
    ("RAW", "ABSENT", "V2_COMMITTED", "FAIL_CLOSED"),
    ("RAW", "ABSENT", "V2_COMMITTED_WITH_PREPARED", "FAIL_CLOSED"),
    ("RAW", "ACTIVATION_PREPARED", "ABSENT", "ACTIVATION_RECOVERY"),
    ("RAW", "ACTIVATION_PREPARED", "V1_COMMITTED", "ACTIVATION_RECOVERY"),
    ("RAW", "ACTIVATION_PREPARED", "V1_PREPARED", "ACTIVATION_RECOVERY"),
    ("RAW", "ACTIVATION_PREPARED", "V2_PREPARED", "ACTIVATION_RECOVERY"),
    ("RAW", "ACTIVATION_PREPARED", "V2_COMMITTED", "FAIL_CLOSED"),
    ("RAW", "ACTIVATION_PREPARED", "V2_COMMITTED_WITH_PREPARED", "FAIL_CLOSED"),
    ("RAW", "R27_COMMITTED", "ABSENT", "FAIL_CLOSED"),
    ("RAW", "R27_COMMITTED", "V1_COMMITTED", "FAIL_CLOSED"),
    ("RAW", "R27_COMMITTED", "V1_PREPARED", "FAIL_CLOSED"),
    ("RAW", "R27_COMMITTED", "V2_PREPARED", "FAIL_CLOSED"),
    ("RAW", "R27_COMMITTED", "V2_COMMITTED", "FAIL_CLOSED"),
    ("RAW", "R27_COMMITTED", "V2_COMMITTED_WITH_PREPARED", "FAIL_CLOSED"),
    ("R27", "ABSENT", "ABSENT", "FAIL_CLOSED"),
    ("R27", "ABSENT", "V1_COMMITTED", "FAIL_CLOSED"),
    ("R27", "ABSENT", "V1_PREPARED", "FAIL_CLOSED"),
    ("R27", "ABSENT", "V2_PREPARED", "FAIL_CLOSED"),
    ("R27", "ABSENT", "V2_COMMITTED", "FAIL_CLOSED"),
    ("R27", "ABSENT", "V2_COMMITTED_WITH_PREPARED", "FAIL_CLOSED"),
    ("R27", "ACTIVATION_PREPARED", "ABSENT", "FAIL_CLOSED"),
    ("R27", "ACTIVATION_PREPARED", "V1_COMMITTED", "FAIL_CLOSED"),
    ("R27", "ACTIVATION_PREPARED", "V1_PREPARED", "FAIL_CLOSED"),
    ("R27", "ACTIVATION_PREPARED", "V2_PREPARED", "R27_RECONCILE"),
    ("R27", "ACTIVATION_PREPARED", "V2_COMMITTED", "ACTIVATION_RECOVERY"),
    ("R27", "ACTIVATION_PREPARED", "V2_COMMITTED_WITH_PREPARED", "ACTIVATION_RECOVERY"),
    ("R27", "R27_COMMITTED", "ABSENT", "FAIL_CLOSED"),
    ("R27", "R27_COMMITTED", "V1_COMMITTED", "FAIL_CLOSED"),
    ("R27", "R27_COMMITTED", "V1_PREPARED", "FAIL_CLOSED"),
    ("R27", "R27_COMMITTED", "V2_PREPARED", "FAIL_CLOSED"),
    ("R27", "R27_COMMITTED", "V2_COMMITTED", "R27"),
    ("R27", "R27_COMMITTED", "V2_COMMITTED_WITH_PREPARED", "FAIL_CLOSED"),
)


@pytest.mark.parametrize(("aggregate", "activation", "metadata", "expected"), _R29_EXACT_MATRIX)
def test_r29_pre_reconciliation_classifier_is_total_and_exclusive_for_all_exact_cells(
    aggregate: str, activation: str, metadata: str, expected: str
) -> None:
    snapshot = _R29PreReconciliationSnapshot(
        aggregate_payload=b"fixture",
        aggregate_state=aggregate,
        activation=None,
        activation_state=activation,
        committed=None,
        prepared=None,
        metadata_state=metadata,
        project_id="project-01",
    )

    assert _classify_r29_pre_reconciliation(snapshot) == expected


@pytest.mark.parametrize(
    "binding_state",
    (
        "WRONG_PROJECT",
        "WRONG_ACTIVATION_BINDING",
        "WRONG_REVISION",
        "WRONG_EXPECTED_F0",
        "WRONG_PROPOSED_F0",
        "CROSS_LINEAGE",
        "STALE_METADATA",
    ),
)
def test_r29_pre_reconciliation_classifier_rejects_every_non_exact_binding(binding_state: str) -> None:
    snapshot = _R29PreReconciliationSnapshot(
        aggregate_payload=b"fixture",
        aggregate_state="RAW",
        activation=None,
        activation_state="ABSENT",
        committed=None,
        prepared=None,
        metadata_state="V2_PREPARED",
        project_id="project-01",
        binding_state=binding_state,
    )

    assert _classify_r29_pre_reconciliation(snapshot) == "FAIL_CLOSED"


@pytest.mark.parametrize(
    ("aggregate", "activation", "metadata"),
    (
        ("CORRUPT", "ABSENT", "ABSENT"),
        ("RAW", "CORRUPT", "ABSENT"),
        ("RAW", "ABSENT", "CORRUPT"),
        ("R27", "R27_COMMITTED", "V2_COMMITTED_WITH_PREPARED"),
    ),
)
def test_r29_pre_reconciliation_classifier_fails_closed_without_reclassification(
    aggregate: str, activation: str, metadata: str
) -> None:
    snapshot = _R29PreReconciliationSnapshot(
        aggregate_payload=b"fixture",
        aggregate_state=aggregate,
        activation=None,
        activation_state=activation,
        committed=None,
        prepared=None,
        metadata_state=metadata,
        project_id="project-01",
    )

    assert _classify_r29_pre_reconciliation(snapshot) == "FAIL_CLOSED"
