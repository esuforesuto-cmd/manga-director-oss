"""Focused D12-I01 tests for the provider-neutral submission journal."""

from __future__ import annotations

import inspect
import os
import sqlite3
import threading
from pathlib import Path

import pytest
from generation_admission_v1_fixtures import manifest

import manga_director
import manga_director.production as production
from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.production import future_external_provider_submission_journal as d12
from manga_director.production.future_durable_generation_boundary import ProviderDispatchRequestV1
from manga_director.production.future_generation_admission_contract import (
    ProviderRequestBindingV1,
    SnapshotIdentityV1,
    content_digest,
)
from manga_director.production.future_provider_capability_profile import (
    CAPABILITY_NAMES,
    classify_provider_capabilities,
    comfyui_capability_profile_fixture_v1,
)
from manga_director.repositories.local_file import LocalFileRepository


def _digest(value: str) -> str:
    return content_digest({"value": value})


def _dispatch(identity: str = "dispatch") -> ProviderDispatchRequestV1:
    return ProviderDispatchRequestV1(
        attempt_id=f"attempt:{identity}", project_id="project:d12", page_id="1",
        execution_target_reference="target:d12", manifest_digest=_digest("manifest"),
        provider_binding_digest=_digest("provider"), attempt_binding_digest=_digest("attempt"),
        consumption_sequence=1, dispatch_request_identity=_digest(identity),
        idempotency_identity=_digest(identity),
        provider_request=ProviderRequestBindingV1(provider_reference="provider:d12"),
    )


def _request() -> d12.ExternalProviderSubmissionRequestV1:
    return d12.ExternalProviderSubmissionRequestV1(
        provider_reference="provider:d12", request_digest=_digest("request"), metadata={"mode": "test"}
    )


def _profile() -> dict[str, object]:
    evidence = [
        {
            "capability": capability, "asserted_state": "SUPPORTED", "provenance_state": "CURRENT",
            "source_reference": f"test:source:{capability}", "claim_identifier": f"test:claim:{capability}",
            "source_digest": _digest(capability), "provider_revision": "provider:1",
            "source_revision": "source:1", "review_revision": "review:1",
        }
        for capability in CAPABILITY_NAMES
    ]
    return {
        "schema_name": "manga_director.future_provider_capability_profile", "schema_version": "1",
        "provider_reference": "provider:d12", "provider_revision": "provider:1", "adapter_version": "test:1",
        "review_revision": "review:1", "profile_revision": 1,
        "duplicate_submit_semantics": "IDEMPOTENT_SAME_OPERATION",
        "reviewed_source_applicability": [
            {"source_reference": item["source_reference"], "source_revision": "source:1",
             "provider_reference": "provider:d12", "provider_revision": "provider:1", "review_revision": "review:1"}
            for item in evidence
        ], "evidence": evidence,
    }


def _binding(identity: str = "dispatch") -> d12.ExternalProviderSubmissionBindingV1:
    classification = classify_provider_capabilities(_profile())
    return d12._binding(_dispatch(identity), classification.profile_identity, classification.provider_class, _request())


def _journal(tmp_path: Path) -> d12._ExternalProviderSubmissionJournal:
    return d12._ExternalProviderSubmissionJournal((tmp_path / "journal").resolve())


def _event_count(journal: d12._ExternalProviderSubmissionJournal) -> int:
    connection = sqlite3.connect(journal._database)
    try:
        return int(connection.execute("SELECT COUNT(*) FROM external_submission_events").fetchone()[0])
    finally:
        connection.close()


def _replace_schema(
    root: Path,
    *,
    journal_columns: str | None = None,
    event_columns: str | None = None,
    dispatch_index: str | None = None,
) -> None:
    root.mkdir()
    connection = sqlite3.connect(root / "external-provider-submission.sqlite3")
    try:
        connection.execute(
            "CREATE TABLE external_submission_journal ("
            + (journal_columns or "journal_identity TEXT PRIMARY KEY, dispatch_identity TEXT NOT NULL, attempt_id TEXT NOT NULL, binding_json TEXT NOT NULL, binding_digest TEXT NOT NULL, phase TEXT NOT NULL, sequence INTEGER NOT NULL, terminal_observation_json TEXT, terminal_observation_digest TEXT")
            + ")"
        )
        connection.execute(
            dispatch_index
            or "CREATE UNIQUE INDEX ux_external_submission_dispatch ON external_submission_journal(dispatch_identity)"
        )
        connection.execute("CREATE UNIQUE INDEX ux_external_submission_attempt ON external_submission_journal(attempt_id)")
        connection.execute(
            "CREATE TABLE external_submission_events ("
            + (event_columns or "journal_identity TEXT NOT NULL, sequence INTEGER NOT NULL, phase TEXT NOT NULL, payload_json TEXT NOT NULL, payload_digest TEXT NOT NULL, PRIMARY KEY (journal_identity, sequence)")
            + ")"
        )
        connection.execute("CREATE INDEX ix_external_submission_events_phase ON external_submission_events(journal_identity, phase)")
        connection.execute("PRAGMA user_version = 1")
        connection.commit()
    finally:
        connection.close()


def _trusted_runtime(tmp_path: Path) -> tuple[d12.LocalFileExternalProviderSubmissionJournal, object, object]:
    admitted = manifest().model_copy(update={"project_id": "project-d12", "attempt_id": "attempt-d12"})
    repository = LocalFileRepository(tmp_path / "repository")
    repository.save(Project(
        id=admitted.project_id, title="D12", pages=[Page(
            page_number=1, state=PageState.PROMPT_BUILT, page_design={}, review={},
            storyboard=admitted.storyboard.model_dump(mode="json"), prompt=admitted.prompt.model_dump(mode="json"),
            metadata={"future_generation_target_reference": admitted.execution_target_reference,
                      "future_generation_provider_binding": admitted.provider_request.model_dump(mode="json")},
        )],
    ))
    snapshot = repository._load_revisioned(admitted.project_id)
    bound = admitted.model_copy(update={"page_id": "1", "snapshot": SnapshotIdentityV1(revision=snapshot.revision, fingerprint=snapshot.fingerprint)})
    runtime = d12.LocalFileExternalProviderSubmissionJournal(repository)
    assert runtime._d05.reserve(bound).code == "RESERVATION_RESERVED"
    permit = runtime._d05.prepare_provider_start(bound).permit
    assert permit is not None
    return runtime, bound, permit


def test_trusted_composition_consumes_d05_and_classifies_raw_d08(tmp_path: Path) -> None:
    runtime, admitted, permit = _trusted_runtime(tmp_path)
    request = d12.ExternalProviderSubmissionRequestV1(
        provider_reference=admitted.provider_request.provider_reference, request_digest=_digest("request"), metadata={}
    )
    first = runtime.begin(manifest=admitted, permit=permit, raw_provider_profile=_profile(), request=request)
    second = runtime.begin(manifest=admitted, permit=permit, raw_provider_profile=_profile(), request=request)

    assert first.status == "EDGE_GRANTED" and first.edge_grant is not None
    assert first.binding is not None and first.binding.provider_class == "A"
    assert second.status == "BLOCKED"


def test_standalone_dispatch_and_preclassified_d08_are_not_supported_authority(tmp_path: Path) -> None:
    runtime, admitted, permit = _trusted_runtime(tmp_path)
    assert "dispatch" not in inspect.signature(runtime.begin).parameters
    classified = classify_provider_capabilities(_profile())
    request = d12.ExternalProviderSubmissionRequestV1(
        provider_reference=admitted.provider_request.provider_reference, request_digest=_digest("request"), metadata={}
    )
    assert runtime.begin(manifest=admitted, permit=permit, raw_provider_profile=classified, request=request).status == "BLOCKED"


def test_trusted_entry_has_no_caller_selected_root_or_class_authority() -> None:
    parameters = inspect.signature(d12.LocalFileExternalProviderSubmissionJournal.begin).parameters
    assert {"dispatch", "provider_class", "profile_identity", "owner_root", "database"}.isdisjoint(parameters)
    assert set(inspect.signature(d12.LocalFileExternalProviderSubmissionJournal).parameters) == {"repository"}


def test_binding_is_immutable_and_rejects_provider_or_secret_mismatch() -> None:
    binding = _binding()
    assert binding.journal_identity == binding.binding_digest
    with pytest.raises(ValueError):
        d12.ExternalProviderSubmissionRequestV1(provider_reference="https://host", request_digest=_digest("x"))
    with pytest.raises(ValueError):
        d12.ExternalProviderSubmissionRequestV1(provider_reference="provider:d12", request_digest=_digest("x"), metadata={"token": "x"})
    with pytest.raises(ValueError):
        d12._binding(_dispatch(), binding.profile_identity, binding.provider_class, d12.ExternalProviderSubmissionRequestV1(provider_reference="other", request_digest=_digest("x")))
    with pytest.raises(ValueError):
        d12.ExternalProviderSubmissionObservationV1(kind="REJECTED", metadata={"nested": {"no": "nested"}})  # type: ignore[arg-type]


def test_edge_is_durable_one_shot_and_grant_is_nonserializable(tmp_path: Path) -> None:
    journal = _journal(tmp_path)
    first = journal.begin(_binding())
    duplicate = journal.begin(_binding())
    assert first.status == "EDGE_GRANTED" and first.edge_grant is not None
    assert duplicate.status == "RECOVERY_REQUIRED"
    with pytest.raises(TypeError):
        first.edge_grant.__reduce__()
    accepted = journal.record(first.edge_grant, d12.ExternalProviderSubmissionObservationV1(kind="ACCEPTED_IDENTIFIED", provider_identity="job:one"))
    assert accepted.status == "ACCEPTED_IDENTIFIED"
    assert journal.record(first.edge_grant, d12.ExternalProviderSubmissionObservationV1(kind="REJECTED")).status == "BLOCKED"
    assert journal.reopen(_binding().dispatch_identity).status == "ACCEPTED_IDENTIFIED"


@pytest.mark.parametrize(
    "forged",
    [
        lambda binding, grant: d12._ExternalProviderEdgeGrant(
            binding.journal_identity, binding.dispatch_identity, 2, d12._ISSUER, b"f" * 32
        ),
        lambda binding, grant: d12._ExternalProviderEdgeGrant(
            grant._journal_identity, grant._dispatch_identity, grant._sequence, d12._ISSUER, grant._token
        ),
        lambda binding, grant: d12._ExternalProviderEdgeGrant(
            "f" * 64, binding.dispatch_identity, 2, d12._ISSUER, b"f" * 32
        ),
        lambda binding, grant: d12._ExternalProviderEdgeGrant(
            binding.journal_identity, "f" * 64, 2, d12._ISSUER, b"f" * 32
        ),
        lambda binding, grant: d12._ExternalProviderEdgeGrant(
            binding.journal_identity, binding.dispatch_identity, 1, d12._ISSUER, b"f" * 32
        ),
    ],
    ids=["direct", "copied_fields", "wrong_journal", "wrong_dispatch", "wrong_sequence"],
)
def test_forged_grants_cannot_mutate_or_consume_registered_authority(
    tmp_path: Path,
    forged: object,
) -> None:
    journal = _journal(tmp_path)
    binding = _binding()
    issued = journal.begin(binding)
    assert issued.edge_grant is not None
    assert len(journal._issued_grants) == 1
    before = _event_count(journal)

    result = journal.record(
        forged(binding, issued.edge_grant),
        d12.ExternalProviderSubmissionObservationV1(kind="ACCEPTED_IDENTIFIED", provider_identity="job:forged"),
    )

    assert result.status == "BLOCKED"
    assert _event_count(journal) == before
    assert journal.reopen(binding.dispatch_identity).status == "RECOVERY_REQUIRED"
    assert len(journal._issued_grants) == 1
    assert journal.record(
        issued.edge_grant,
        d12.ExternalProviderSubmissionObservationV1(kind="REJECTED"),
    ).status == "REJECTED"


def test_process_restart_invalidates_outstanding_process_local_grant(tmp_path: Path) -> None:
    journal = _journal(tmp_path)
    binding = _binding()
    issued = journal.begin(binding)
    assert issued.edge_grant is not None
    restarted = d12._ExternalProviderSubmissionJournal(journal._root)

    assert restarted.record(issued.edge_grant, d12.ExternalProviderSubmissionObservationV1(kind="REJECTED")).status == "BLOCKED"
    assert restarted.reopen(binding.dispatch_identity).status == "RECOVERY_REQUIRED"
    assert _event_count(restarted) == 3


def test_concurrent_consumers_of_one_grant_have_exactly_one_terminal_winner(tmp_path: Path) -> None:
    journal = _journal(tmp_path)
    issued = journal.begin(_binding())
    assert issued.edge_grant is not None
    barrier = threading.Barrier(3)
    reports: list[d12.ExternalProviderSubmissionReport] = []
    lock = threading.Lock()

    def consume() -> None:
        barrier.wait()
        report = journal.record(
            issued.edge_grant,
            d12.ExternalProviderSubmissionObservationV1(kind="REJECTED"),
        )
        with lock:
            reports.append(report)

    threads = [threading.Thread(target=consume) for _ in range(2)]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join()
    assert [report.status for report in reports].count("REJECTED") == 1
    assert [report.status for report in reports].count("BLOCKED") == 1
    assert _event_count(journal) == 4


@pytest.mark.parametrize(
    ("kind", "status"),
    [("ACCEPTED_IDENTIFIED", "ACCEPTED_IDENTIFIED"), ("REJECTED", "REJECTED")],
)
def test_terminal_history_reopens_deterministically_without_another_grant(
    tmp_path: Path, kind: str, status: str
) -> None:
    journal = _journal(tmp_path)
    binding = _binding(kind)
    started = journal.begin(binding)
    assert started.edge_grant is not None
    identity = "provider:accepted" if kind == "ACCEPTED_IDENTIFIED" else None
    recorded = journal.record(
        started.edge_grant,
        d12.ExternalProviderSubmissionObservationV1(kind=kind, provider_identity=identity),
    )
    reopened = journal.reopen(binding.dispatch_identity)
    assert recorded.status == reopened.status == status
    assert reopened.edge_grant is None


@pytest.mark.parametrize("phase", ["DISPATCH_CONSUMED", "SUBMISSION_STARTED", "EDGE_ISSUED"])
def test_crash_window_reopen_is_recovery_only_and_never_reissues_grant(
    tmp_path: Path, phase: d12.SubmissionPhase
) -> None:
    journal = _journal(tmp_path)
    binding = _binding(f"crash:{phase}")
    with journal._connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        journal._validate_schema(connection)
        journal._insert(connection, binding)
        if phase != "DISPATCH_CONSUMED":
            row = journal._row_by_identity(connection, binding.journal_identity)
            assert row is not None
            journal._append(connection, row, "SUBMISSION_STARTED", None)
        if phase == "EDGE_ISSUED":
            row = journal._row_by_identity(connection, binding.journal_identity)
            assert row is not None
            journal._append(connection, row, "EDGE_ISSUED", None)
        connection.commit()
    reopened = journal.reopen(binding.dispatch_identity)
    duplicate = journal.begin(binding)
    assert reopened.status == duplicate.status == "RECOVERY_REQUIRED"
    assert duplicate.edge_grant is None


def test_d05_consumption_without_successor_binding_cannot_create_d12_authority(tmp_path: Path) -> None:
    runtime, admitted, permit = _trusted_runtime(tmp_path)
    assert runtime._d05.consume_for_dispatch(admitted, permit) is not None
    request = d12.ExternalProviderSubmissionRequestV1(
        provider_reference=admitted.provider_request.provider_reference,
        request_digest=_digest("request"),
    )
    result = runtime.begin(manifest=admitted, permit=permit, raw_provider_profile=_profile(), request=request)
    assert result.status == "BLOCKED" and result.edge_grant is None


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("FAILED_PRE_SEND", "FAILED_PRE_SEND"), ("REJECTED", "REJECTED"),
        ("ACCEPTED_UNIDENTIFIED", "RECOVERY_REQUIRED"), ("AMBIGUOUS", "RECOVERY_REQUIRED"),
        ("MALFORMED", "RECOVERY_REQUIRED"), ("PROCESS_LOSS", "RECOVERY_REQUIRED"),
        ("PROVIDER_UNAVAILABLE", "RECOVERY_REQUIRED"),
    ],
)
def test_normalized_outcomes_never_create_retry_authority(tmp_path: Path, kind: str, expected: str) -> None:
    journal = _journal(tmp_path)
    started = journal.begin(_binding(kind))
    assert started.edge_grant is not None
    result = journal.record(started.edge_grant, d12.ExternalProviderSubmissionObservationV1(kind=kind))
    assert result.status == expected
    assert journal.begin(_binding(kind)).edge_grant is None


def test_class_c_ambiguity_reopens_recovery_only(tmp_path: Path) -> None:
    journal = _journal(tmp_path)
    dispatch = _dispatch("class-c")
    classification = classify_provider_capabilities(comfyui_capability_profile_fixture_v1())
    result = journal.begin(d12._binding(dispatch, classification.profile_identity, classification.provider_class, _request()))
    assert result.binding is not None and result.binding.provider_class == "C" and result.edge_grant is not None
    assert journal.record(result.edge_grant, d12.ExternalProviderSubmissionObservationV1(kind="AMBIGUOUS")).status == "RECOVERY_REQUIRED"


@pytest.mark.parametrize("mutation", ["version", "missing_table", "wrong_pk", "missing_index", "event_sequence", "event_payload", "binding_digest"])
def test_schema_and_replay_corruption_fail_closed(tmp_path: Path, mutation: str) -> None:
    journal = _journal(tmp_path)
    binding = _binding(mutation)
    started = journal.begin(binding)
    assert started.edge_grant is not None
    with sqlite3.connect(journal._database) as connection:
        if mutation == "version":
            connection.execute("PRAGMA user_version = 99")
        elif mutation == "missing_table":
            connection.execute("DROP TABLE external_submission_events")
        elif mutation == "wrong_pk":
            connection.execute("DROP TABLE external_submission_events")
            connection.execute("CREATE TABLE external_submission_events (journal_identity TEXT, sequence INTEGER, phase TEXT, payload_json TEXT, payload_digest TEXT)")
        elif mutation == "missing_index":
            connection.execute("DROP INDEX ux_external_submission_dispatch")
        elif mutation == "event_sequence":
            connection.execute("UPDATE external_submission_events SET sequence = 9 WHERE sequence = 1")
        elif mutation == "event_payload":
            connection.execute("UPDATE external_submission_events SET payload_digest = 'f' || substr(payload_digest, 2) WHERE sequence = 0")
        else:
            connection.execute("UPDATE external_submission_journal SET binding_digest = 'f' || substr(binding_digest, 2)")
    assert journal.reopen(binding.dispatch_identity).status == "CORRUPT"


@pytest.mark.parametrize("mutation", ["wrong_dispatch_index", "wrong_event_pk_order", "unknown_index"])
def test_partial_or_altered_index_and_pk_constraints_fail_closed(tmp_path: Path, mutation: str) -> None:
    journal = _journal(tmp_path)
    binding = _binding(mutation)
    assert journal.begin(binding).edge_grant is not None
    with sqlite3.connect(journal._database) as connection:
        if mutation == "wrong_dispatch_index":
            connection.execute("DROP INDEX ux_external_submission_dispatch")
            connection.execute("CREATE UNIQUE INDEX ux_external_submission_dispatch ON external_submission_journal(attempt_id)")
        elif mutation == "wrong_event_pk_order":
            connection.execute("DROP TABLE external_submission_events")
            connection.execute(
                "CREATE TABLE external_submission_events (journal_identity TEXT NOT NULL, sequence INTEGER NOT NULL, phase TEXT NOT NULL, payload_json TEXT NOT NULL, payload_digest TEXT NOT NULL, PRIMARY KEY (sequence, journal_identity))"
            )
            connection.execute("CREATE INDEX ix_external_submission_events_phase ON external_submission_events(journal_identity, phase)")
        else:
            connection.execute("CREATE INDEX ix_unexpected ON external_submission_journal(phase)")
    assert journal.reopen(binding.dispatch_identity).status == "CORRUPT"


@pytest.mark.parametrize(
    ("journal_columns", "event_columns", "dispatch_index"),
    [
        ("journal_identity TEXT PRIMARY KEY, dispatch_identity TEXT, attempt_id TEXT NOT NULL, binding_json TEXT NOT NULL, binding_digest TEXT NOT NULL, phase TEXT NOT NULL, sequence INTEGER NOT NULL, terminal_observation_json TEXT, terminal_observation_digest TEXT", None, None),
        ("journal_identity TEXT PRIMARY KEY, dispatch_identity TEXT NOT NULL, attempt_id TEXT NOT NULL, binding_json TEXT NOT NULL, binding_digest TEXT NOT NULL, phase TEXT NOT NULL, sequence INTEGER NOT NULL DEFAULT 0, terminal_observation_json TEXT, terminal_observation_digest TEXT", None, None),
        ("journal_identity TEXT PRIMARY KEY, dispatch_identity TEXT NOT NULL, attempt_id TEXT NOT NULL, binding_json TEXT NOT NULL, binding_digest TEXT NOT NULL, phase TEXT NOT NULL, sequence INTEGER NOT NULL, terminal_observation_json TEXT NOT NULL, terminal_observation_digest TEXT", None, None),
        (None, "journal_identity TEXT NOT NULL, sequence INTEGER NOT NULL, phase TEXT NOT NULL, payload_json TEXT NOT NULL, payload_digest TEXT NOT NULL, PRIMARY KEY (sequence, journal_identity)", None),
        (None, None, "CREATE INDEX ux_external_submission_dispatch ON external_submission_journal(dispatch_identity)"),
        (None, None, "CREATE UNIQUE INDEX ux_external_submission_dispatch ON external_submission_journal(dispatch_identity) WHERE dispatch_identity IS NOT NULL"),
    ],
    ids=["nullable_required", "default", "altered_not_null", "reversed_pk", "nonunique_index", "partial_index"],
)
def test_complete_looking_altered_schema_is_rejected_before_use(
    tmp_path: Path,
    journal_columns: str | None,
    event_columns: str | None,
    dispatch_index: str | None,
) -> None:
    root = (tmp_path / "altered").resolve()
    _replace_schema(
        root,
        journal_columns=journal_columns,
        event_columns=event_columns,
        dispatch_index=dispatch_index,
    )
    with pytest.raises(ValueError):
        d12._ExternalProviderSubmissionJournal(root)


def test_unexpected_schema_object_fails_closed_before_replay(tmp_path: Path) -> None:
    journal = _journal(tmp_path)
    binding = _binding()
    assert journal.begin(binding).edge_grant is not None
    connection = sqlite3.connect(journal._database)
    try:
        connection.execute(
            "CREATE TRIGGER unexpected_schema_trigger AFTER INSERT ON external_submission_events BEGIN SELECT 1; END"
        )
        connection.commit()
    finally:
        connection.close()
    assert journal.reopen(binding.dispatch_identity).status == "CORRUPT"


@pytest.mark.skipif(os.name != "nt", reason="Windows SQLite handle release contract")
@pytest.mark.parametrize("operation", ["begin", "duplicate", "record", "rejected", "reopen", "schema_failure"])
def test_windows_operations_release_sqlite_handles_without_gc(tmp_path: Path, operation: str) -> None:
    journal = _journal(tmp_path)
    binding = _binding(operation)
    issued = journal.begin(binding)
    assert issued.edge_grant is not None
    if operation == "duplicate":
        assert journal.begin(binding).status == "RECOVERY_REQUIRED"
    elif operation == "record":
        assert journal.record(issued.edge_grant, d12.ExternalProviderSubmissionObservationV1(kind="REJECTED")).status == "REJECTED"
    elif operation == "rejected":
        forged = d12._ExternalProviderEdgeGrant(
            binding.journal_identity, binding.dispatch_identity, 2, d12._ISSUER, b"f" * 32
        )
        assert journal.record(forged, d12.ExternalProviderSubmissionObservationV1(kind="REJECTED")).status == "BLOCKED"
    elif operation == "reopen":
        assert journal.reopen(binding.dispatch_identity).status == "RECOVERY_REQUIRED"
    elif operation == "schema_failure":
        connection = sqlite3.connect(journal._database)
        try:
            connection.execute("PRAGMA user_version = 99")
            connection.commit()
        finally:
            connection.close()
        assert journal.reopen(binding.dispatch_identity).status == "CORRUPT"
    journal._database.unlink()
    assert not journal._database.exists()


def test_nonempty_partial_store_cannot_be_initialized(tmp_path: Path) -> None:
    root = (tmp_path / "partial").resolve()
    root.mkdir()
    with sqlite3.connect(root / "external-provider-submission.sqlite3") as connection:
        connection.execute("CREATE TABLE partial_state (id TEXT PRIMARY KEY)")
    with pytest.raises(ValueError):
        d12._ExternalProviderSubmissionJournal(root)


def test_synchronized_repeated_contenders_issue_exactly_one_grant(tmp_path: Path) -> None:
    for round_number in range(3):
        journal = _journal(tmp_path / str(round_number))
        binding = _binding(f"concurrent:{round_number}")
        barrier = threading.Barrier(6)
        reports: list[d12.ExternalProviderSubmissionReport] = []
        lock = threading.Lock()

        def contender(
            contender_barrier: threading.Barrier = barrier,
            contender_journal: d12._ExternalProviderSubmissionJournal = journal,
            contender_binding: d12.ExternalProviderSubmissionBindingV1 = binding,
            contender_lock: threading.Lock = lock,
            contender_reports: list[d12.ExternalProviderSubmissionReport] = reports,
        ) -> None:
            contender_barrier.wait()
            report = contender_journal.begin(contender_binding)
            with contender_lock:
                contender_reports.append(report)

        threads = [threading.Thread(target=contender) for _ in range(5)]
        for thread in threads:
            thread.start()
        barrier.wait()
        for thread in threads:
            thread.join()
        assert sum(report.edge_grant is not None for report in reports) == 1
        assert all(report.status in {"EDGE_GRANTED", "RECOVERY_REQUIRED"} for report in reports)


def test_public_surfaces_remain_unmodified() -> None:
    assert not hasattr(manga_director, "ExternalProviderSubmissionBindingV1")
    assert not hasattr(production, "ExternalProviderSubmissionBindingV1")
    assert "StateMachine" not in inspect.getsource(d12)
    assert "requests" not in inspect.getsource(d12)
