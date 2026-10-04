"""Focused D09-I02-I01 tests for the private provider-free result journal."""

from __future__ import annotations

import inspect
import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, cast

import pytest
from generation_admission_v1_fixtures import manifest

import manga_director
import manga_director.production as production
from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.production import future_fake_provider_receipt_journal as d09
from manga_director.production import future_provider_result_evidence_journal as i02
from manga_director.production.future_generation_admission_contract import (
    SnapshotIdentityV1,
    content_digest,
)
from manga_director.production.future_provider_capability_profile import CAPABILITY_NAMES
from manga_director.repositories.local_file import LocalFileRepository


def _digest(value: str) -> str:
    return content_digest({"value": value})


def _profile() -> dict[str, object]:
    evidence = [
        {
            "capability": capability,
            "asserted_state": "SUPPORTED",
            "provenance_state": "CURRENT",
            "source_reference": f"test:source:{capability}",
            "claim_identifier": f"test:claim:{capability}",
            "source_digest": _digest(capability),
            "provider_revision": "provider:1",
            "source_revision": "source:1",
            "review_revision": "review:1",
        }
        for capability in CAPABILITY_NAMES
    ]
    return {
        "schema_name": "manga_director.future_provider_capability_profile",
        "schema_version": "1",
        "provider_reference": "test:provider",
        "provider_revision": "provider:1",
        "adapter_version": "fixture:1",
        "review_revision": "review:1",
        "profile_revision": 1,
        "duplicate_submit_semantics": "IDEMPOTENT_SAME_OPERATION",
        "reviewed_source_applicability": [
            {
                "source_reference": item["source_reference"],
                "source_revision": item["source_revision"],
                "provider_reference": "test:provider",
                "provider_revision": "provider:1",
                "review_revision": "review:1",
            }
            for item in evidence
        ],
        "evidence": evidence,
    }


def _accepted_runtime(tmp_path: Path) -> tuple[LocalFileRepository, str]:
    admitted = manifest().model_copy(update={"project_id": "project-i02", "attempt_id": "attempt-i02"})
    repository = LocalFileRepository(tmp_path / "repository")
    repository.save(
        Project(
            id=admitted.project_id,
            title="I02",
            pages=[
                Page(
                    page_number=1,
                    state=PageState.PROMPT_BUILT,
                    page_design={},
                    review={},
                    storyboard=admitted.storyboard.model_dump(mode="json"),
                    prompt=admitted.prompt.model_dump(mode="json"),
                    metadata={
                        "future_generation_target_reference": admitted.execution_target_reference,
                        "future_generation_provider_binding": admitted.provider_request.model_dump(mode="json"),
                    },
                )
            ],
        )
    )
    snapshot = repository._load_revisioned(admitted.project_id)
    bound = admitted.model_copy(
        update={"page_id": "1", "snapshot": SnapshotIdentityV1(revision=snapshot.revision, fingerprint=snapshot.fingerprint)}
    )
    runtime = d09._LocalFileFakeProviderReceiptJournal(repository)
    assert runtime._d05.reserve(bound).code == "RESERVATION_RESERVED"
    permit = runtime._d05.prepare_provider_start(bound).permit
    assert permit is not None
    assert runtime.submit(manifest=bound, permit=permit, raw_provider_profile=_profile()).status == "ACCEPTED"
    return repository, bound.attempt_id


def _observation(*, outputs: list[dict[str, object]] | None = None) -> dict[str, object]:
    return {
        "provider_job_identity": None,
        "outputs": outputs
        or [
            {
                "logical_output_id": "output:one",
                "sha256": "a" * 64,
                "media_type": "image/png",
                "metadata": {"kind": "fake"},
            }
        ],
        "capture_metadata": {"fixture": "provider-free"},
    }


def _composition(tmp_path: Path) -> tuple[i02._LocalFileProviderResultEvidenceJournal, str]:
    repository, attempt_id = _accepted_runtime(tmp_path)
    return i02._LocalFileProviderResultEvidenceJournal(repository), attempt_id


def _accepted_result_count(journal: i02._LocalFileProviderResultEvidenceJournal) -> int:
    with sqlite3.connect(journal._journal._database) as connection:
        return int(connection.execute("SELECT COUNT(*) FROM d09i02_accepted_results").fetchone()[0])


def _accepted_evidence_row(journal: i02._LocalFileProviderResultEvidenceJournal) -> dict[str, Any]:
    with sqlite3.connect(journal._journal._database) as connection:
        raw = connection.execute("SELECT evidence_json FROM d09i02_accepted_results").fetchone()[0]
    return cast(dict[str, Any], json.loads(raw))


def _replace_accepted_evidence(
    journal: i02._LocalFileProviderResultEvidenceJournal, evidence: dict[str, Any]
) -> None:
    with sqlite3.connect(journal._journal._database) as connection:
        connection.execute(
            "UPDATE d09i02_accepted_results SET evidence_json = ?", (json.dumps(evidence),)
        )


def _create_pk_variant_schema(root: Path, primary_keys: dict[str, str]) -> Path:
    root.mkdir(parents=True)
    database = root / "future-provider-result-evidence.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            ";\n".join(
                (
                    f"CREATE TABLE d09i02_schema_meta (version INTEGER NOT NULL {primary_keys['meta']})",
                    "INSERT INTO d09i02_schema_meta VALUES (1)",
                    "CREATE TABLE d09i02_journal_bindings (journal_identity TEXT NOT NULL "
                    f"{primary_keys['binding']}, receipt_identity TEXT NOT NULL, binding_json TEXT NOT NULL, binding_digest TEXT NOT NULL)",
                    "CREATE UNIQUE INDEX d09i02_receipt_identity_unique ON d09i02_journal_bindings(receipt_identity)",
                    "CREATE TABLE d09i02_journal_state (journal_identity TEXT NOT NULL "
                    f"{primary_keys['state']}, phase TEXT NOT NULL, availability_gate TEXT NOT NULL, sequence INTEGER NOT NULL, last_event_digest TEXT NOT NULL)",
                    "CREATE TABLE d09i02_events (journal_identity TEXT NOT NULL, sequence INTEGER NOT NULL, "
                    f"event_type TEXT NOT NULL, event_json TEXT NOT NULL, event_digest TEXT NOT NULL{primary_keys['event']})",
                    "CREATE TABLE d09i02_accepted_results (journal_identity TEXT NOT NULL, "
                    f"result_identity TEXT NOT NULL, evidence_json TEXT NOT NULL, evidence_digest TEXT NOT NULL{primary_keys['result']})",
                    "CREATE UNIQUE INDEX d09i02_result_identity_unique ON d09i02_accepted_results(result_identity)",
                )
            )
            + ";"
        )
    return database


def _approved_primary_keys() -> dict[str, str]:
    return {
        "meta": "PRIMARY KEY",
        "binding": "PRIMARY KEY",
        "state": "PRIMARY KEY",
        "event": ", PRIMARY KEY (journal_identity, sequence)",
        "result": ", PRIMARY KEY (journal_identity)",
    }


def test_accepted_i01_history_captures_unverified_canonical_multi_output(tmp_path: Path) -> None:
    journal, attempt_id = _composition(tmp_path)
    result = journal.capture(
        attempt_id=attempt_id,
        observation=_observation(
            outputs=[
                {"logical_output_id": "output:two", "sha256": "b" * 64, "media_type": "image/webp", "metadata": {}},
                {"logical_output_id": "output:one", "sha256": "a" * 64, "media_type": "image/png", "metadata": {"kind": "fake"}},
            ]
        ),
    )
    assert result.status == "RESULT_CAPTURED"
    assert result.evidence is not None
    assert result.evidence.provider_origin_assurance == "UNVERIFIED"
    assert [item.logical_output_id for item in result.evidence.output_evidence] == ["output:one", "output:two"]


def test_missing_or_non_authoritative_i01_history_never_creates_capture_authority(tmp_path: Path) -> None:
    journal = i02._LocalFileProviderResultEvidenceJournal(LocalFileRepository(tmp_path / "repository"))
    assert journal.capture(attempt_id="attempt:missing", observation=_observation()).status == "RESULT_NOT_AVAILABLE"


def test_nonaccepted_i01_history_never_creates_capture_authority(tmp_path: Path) -> None:
    journal, attempt_id = _composition(tmp_path)
    with sqlite3.connect(journal._reader._database) as connection:
        connection.execute("UPDATE d09_journals SET lifecycle = 'REJECTED' WHERE lifecycle = 'ACCEPTED'")

    assert journal.capture(attempt_id=attempt_id, observation=_observation()).status == "RESULT_NOT_AVAILABLE"


@pytest.mark.parametrize(
    "outputs",
    [
        [{"logical_output_id": "", "sha256": "a" * 64, "media_type": "image/png", "metadata": {}}],
        [{"logical_output_id": "one", "sha256": "not-a-digest", "media_type": "image/png", "metadata": {}}],
        [{"logical_output_id": "one", "sha256": "a" * 64, "media_type": "image/gif", "metadata": {}}],
        [
            {"logical_output_id": "one", "sha256": "a" * 64, "media_type": "image/png", "metadata": {}},
            {"logical_output_id": "one", "sha256": "b" * 64, "media_type": "image/png", "metadata": {}},
        ],
        [
            {"logical_output_id": "one", "sha256": "a" * 64, "media_type": "image/png", "metadata": {}},
            {"logical_output_id": "two", "sha256": "a" * 64, "media_type": "image/png", "metadata": {}},
        ],
    ],
)
def test_malformed_output_observations_fail_closed(tmp_path: Path, outputs: list[dict[str, object]]) -> None:
    journal, attempt_id = _composition(tmp_path)
    assert journal.capture(attempt_id=attempt_id, observation=_observation(outputs=outputs)).status == "RESULT_MALFORMED"


def test_metadata_and_prebuilt_evidence_fields_are_rejected(tmp_path: Path) -> None:
    journal, attempt_id = _composition(tmp_path)
    bad = _observation()
    bad["capture_metadata"] = {"Authorization": "Bearer secret"}
    assert journal.capture(attempt_id=attempt_id, observation=bad).status == "RESULT_MALFORMED"
    forged = _observation()
    forged["evidence_identity"] = "a" * 64
    assert journal.capture(attempt_id=attempt_id, observation=forged).status == "RESULT_MALFORMED"


def test_reordered_equivalent_replays_and_conflict_is_immutable(tmp_path: Path) -> None:
    journal, attempt_id = _composition(tmp_path)
    first = journal.capture(attempt_id=attempt_id, observation=_observation())
    assert first.status == "RESULT_CAPTURED" and first.evidence is not None
    assert journal.capture(attempt_id=attempt_id, observation=_observation()).evidence == first.evidence
    changed = _observation()
    changed["outputs"] = [{"logical_output_id": "output:one", "sha256": "b" * 64, "media_type": "image/png", "metadata": {"kind": "fake"}}]
    assert journal.capture(attempt_id=attempt_id, observation=changed).status == "RESULT_AMBIGUOUS"
    assert journal.reopen(attempt_id=attempt_id).status == "RECOVERY_REQUIRED"


def test_concurrent_equivalent_capture_has_one_immutable_result(tmp_path: Path) -> None:
    journal, attempt_id = _composition(tmp_path)
    results: list[i02.ProviderResultJournalReport] = []
    lock = threading.Lock()

    def capture() -> None:
        result = journal.capture(attempt_id=attempt_id, observation=_observation())
        with lock:
            results.append(result)

    workers = [threading.Thread(target=capture) for _ in range(4)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()
    assert journal.reopen(attempt_id=attempt_id).status == "RESULT_CAPTURED"
    assert all(item.status in {"RESULT_CAPTURED", "RECOVERY_REQUIRED"} for item in results)


def test_capture_started_reopens_recovery_only(tmp_path: Path) -> None:
    journal, attempt_id = _composition(tmp_path)
    source = journal._reader.accepted(attempt_id)
    assert source is not None
    assert journal._journal._reserve(source) is None
    journal._journal._transition(source, "RESERVED", "CAPTURE_STARTED", None)
    assert journal.reopen(attempt_id=attempt_id).status == "RECOVERY_REQUIRED"


def test_schema_and_intermediate_event_corruption_fail_closed(tmp_path: Path) -> None:
    journal, attempt_id = _composition(tmp_path)
    assert journal.capture(attempt_id=attempt_id, observation=_observation()).status == "RESULT_CAPTURED"
    database = journal._journal._database
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE d09i02_events SET event_digest = '0' WHERE sequence = 1")
    assert journal.reopen(attempt_id=attempt_id).status == "CORRUPT"


def test_private_module_has_no_provider_network_or_public_exports() -> None:
    source = inspect.getsource(i02)
    assert not hasattr(manga_director, "ProviderResultEvidenceV1")
    assert not hasattr(production, "ProviderResultEvidenceV1")
    assert "requests" not in source and "urllib" not in source and "subprocess" not in source and "socket" not in source
    assert tuple(inspect.signature(i02._LocalFileProviderResultEvidenceJournal).parameters) == ("repository",)


@pytest.mark.parametrize(
    ("scenario", "primary_keys"),
    [
        ("all_tables_without_primary_keys", {key: "" for key in _approved_primary_keys()}),
        ("accepted_result_without_primary_key", {**_approved_primary_keys(), "result": ""}),
        ("accepted_result_wrong_primary_key", {**_approved_primary_keys(), "result": ", PRIMARY KEY (journal_identity, result_identity)"}),
        ("event_without_composite_primary_key", {**_approved_primary_keys(), "event": ""}),
        ("event_with_one_primary_key_component", {**_approved_primary_keys(), "event": ", PRIMARY KEY (journal_identity)"}),
        ("event_with_reversed_primary_key_order", {**_approved_primary_keys(), "event": ", PRIMARY KEY (sequence, journal_identity)"}),
        ("binding_with_wrong_primary_key", {**_approved_primary_keys(), "binding": ""}),
        ("state_with_wrong_primary_key", {**_approved_primary_keys(), "state": ""}),
        ("schema_metadata_without_primary_key", {**_approved_primary_keys(), "meta": ""}),
    ],
)
def test_primary_key_corruption_is_rejected_before_any_journal_operation(
    tmp_path: Path, scenario: str, primary_keys: dict[str, str]
) -> None:
    root = (tmp_path / scenario).resolve()
    _create_pk_variant_schema(root, primary_keys)

    with pytest.raises(ValueError, match="journal is unavailable"):
        i02._ResultJournal(root)


def test_duplicate_row_capable_schema_is_rejected_before_replay_or_capture(tmp_path: Path) -> None:
    root = (tmp_path / "duplicate-rows").resolve()
    database = _create_pk_variant_schema(root, {key: "" for key in _approved_primary_keys()})
    with sqlite3.connect(database) as connection:
        connection.executemany(
            "INSERT INTO d09i02_accepted_results VALUES (?, ?, ?, ?)",
            (("journal", "result-a", "{}", "a" * 64), ("journal", "result-b", "{}", "b" * 64)),
        )
        connection.executemany(
            "INSERT INTO d09i02_events VALUES (?, ?, ?, ?, ?)",
            (("journal", 0, "RESERVED", "{}", "a" * 64), ("journal", 0, "RESERVED", "{}", "b" * 64)),
        )

    with pytest.raises(ValueError, match="journal is unavailable"):
        i02._ResultJournal(root)


def test_existing_journal_revalidates_schema_before_capture(tmp_path: Path) -> None:
    journal, attempt_id = _composition(tmp_path)
    with sqlite3.connect(journal._journal._database) as connection:
        connection.execute("DROP INDEX d09i02_result_identity_unique")

    assert journal.capture(attempt_id=attempt_id, observation=_observation()).status == "CORRUPT"


def test_single_output_remains_unverified_and_authenticated_cannot_be_issued(tmp_path: Path) -> None:
    journal, attempt_id = _composition(tmp_path)
    result = journal.capture(attempt_id=attempt_id, observation=_observation())

    assert result.status == "RESULT_CAPTURED" and result.evidence is not None
    assert result.evidence.provider_origin_assurance == "UNVERIFIED"
    with pytest.raises(ValueError, match="authenticated"):
        i02.ProviderResultEvidenceV1.model_validate(
            {**result.evidence.model_dump(mode="json"), "provider_origin_assurance": "AUTHENTICATED"}
        )


@pytest.mark.parametrize(
    ("scenario", "outputs"),
    [
        (
            "same_hash_different_logical_id",
            [{"logical_output_id": "output:two", "sha256": "a" * 64, "media_type": "image/png", "metadata": {"kind": "fake"}}],
        ),
        (
            "same_logical_id_different_hash",
            [{"logical_output_id": "output:one", "sha256": "b" * 64, "media_type": "image/png", "metadata": {"kind": "fake"}}],
        ),
        (
            "same_output_different_metadata",
            [{"logical_output_id": "output:one", "sha256": "a" * 64, "media_type": "image/png", "metadata": {"kind": "changed"}}],
        ),
        (
            "same_output_different_media_type",
            [{"logical_output_id": "output:one", "sha256": "a" * 64, "media_type": "image/jpeg", "metadata": {"kind": "fake"}}],
        ),
        (
            "partial_overlap",
            [
                {"logical_output_id": "output:one", "sha256": "a" * 64, "media_type": "image/png", "metadata": {"kind": "fake"}},
                {"logical_output_id": "output:two", "sha256": "b" * 64, "media_type": "image/png", "metadata": {}},
            ],
        ),
        (
            "completely_different_outputs",
            [{"logical_output_id": "output:two", "sha256": "b" * 64, "media_type": "image/webp", "metadata": {}}],
        ),
    ],
)
def test_conflict_matrix_never_replaces_accepted_result(
    tmp_path: Path, scenario: str, outputs: list[dict[str, object]]
) -> None:
    del scenario
    journal, attempt_id = _composition(tmp_path)
    first = journal.capture(attempt_id=attempt_id, observation=_observation())

    assert first.status == "RESULT_CAPTURED" and first.evidence is not None
    assert journal.capture(attempt_id=attempt_id, observation=_observation(outputs=outputs)).status == "RESULT_AMBIGUOUS"
    assert _accepted_result_count(journal) == 1
    assert journal.reopen(attempt_id=attempt_id).status == "RECOVERY_REQUIRED"


@pytest.mark.parametrize(
    "metadata",
    [
        {f"key-{index}": "value" for index in range(17)},
        {"x" * 49: "value"},
        {"key": "x" * 257},
        {"nested": {"not": "flat"}},
    ],
    ids=("count", "key_size", "value_size", "depth"),
)
def test_metadata_bounds_and_depth_fail_closed(tmp_path: Path, metadata: dict[str, object]) -> None:
    journal, attempt_id = _composition(tmp_path)
    observation = _observation()
    observation["capture_metadata"] = metadata

    assert journal.capture(attempt_id=attempt_id, observation=observation).status == "RESULT_MALFORMED"


@pytest.mark.parametrize(
    "metadata",
    [
        {"token": "not-a-credential"},
        {"path": "C:\\\\private"},
        {"url": "https://provider.invalid/result"},
        {"reference": "../escape"},
    ],
    ids=("secret", "path", "url", "traversal"),
)
def test_secret_path_and_url_shaped_inputs_fail_closed(
    tmp_path: Path, metadata: dict[str, str]
) -> None:
    journal, attempt_id = _composition(tmp_path)
    observation = _observation()
    observation["capture_metadata"] = metadata

    assert journal.capture(attempt_id=attempt_id, observation=observation).status == "RESULT_MALFORMED"


@pytest.mark.parametrize(
    "tamper",
    [
        lambda evidence: evidence.__setitem__("evidence_digest", "f" * 64),
        lambda evidence: evidence.__setitem__("provider_origin_assurance", "AUTHENTICATED"),
        lambda evidence: evidence["output_evidence"][0].__setitem__("sha256", "b" * 64),
        lambda evidence: evidence["output_evidence"][0].__setitem__("metadata_digest", "c" * 64),
    ],
    ids=("accepted_digest", "assurance", "output_hash", "metadata_digest"),
)
def test_accepted_result_tampering_fails_closed(
    tmp_path: Path, tamper: Any
) -> None:
    journal, attempt_id = _composition(tmp_path)
    assert journal.capture(attempt_id=attempt_id, observation=_observation()).status == "RESULT_CAPTURED"
    evidence = _accepted_evidence_row(journal)
    tamper(evidence)
    _replace_accepted_evidence(journal, evidence)

    assert journal.reopen(attempt_id=attempt_id).status == "CORRUPT"


@pytest.mark.parametrize(
    "tamper",
    [
        lambda connection: connection.execute("UPDATE d09i02_events SET sequence = 7 WHERE sequence = 1"),
        lambda connection: connection.execute("UPDATE d09i02_events SET event_json = '{}' WHERE sequence = 1"),
        lambda connection: connection.execute("UPDATE d09i02_events SET event_digest = '0' WHERE sequence = 1"),
        lambda connection: connection.execute("UPDATE d09i02_journal_bindings SET binding_digest = '0'"),
    ],
    ids=("event_sequence", "event_payload", "event_digest", "immutable_binding"),
)
def test_event_and_binding_tampering_fails_closed(tmp_path: Path, tamper: Any) -> None:
    journal, attempt_id = _composition(tmp_path)
    assert journal.capture(attempt_id=attempt_id, observation=_observation()).status == "RESULT_CAPTURED"
    with sqlite3.connect(journal._journal._database) as connection:
        tamper(connection)

    assert journal.reopen(attempt_id=attempt_id).status == "CORRUPT"


@pytest.mark.parametrize(
    "statement",
    [
        "DROP INDEX d09i02_receipt_identity_unique",
        "DROP INDEX d09i02_result_identity_unique",
        "DELETE FROM d09i02_schema_meta",
    ],
    ids=("receipt_unique_index", "result_unique_index", "schema_version"),
)
def test_schema_and_index_tampering_fails_closed(tmp_path: Path, statement: str) -> None:
    journal, attempt_id = _composition(tmp_path)
    assert journal.capture(attempt_id=attempt_id, observation=_observation()).status == "RESULT_CAPTURED"
    with sqlite3.connect(journal._journal._database) as connection:
        connection.execute(statement)

    assert journal.reopen(attempt_id=attempt_id).status == "CORRUPT"


def test_tampered_i01_receipt_binding_removes_result_capture_authority(tmp_path: Path) -> None:
    journal, attempt_id = _composition(tmp_path)
    with sqlite3.connect(journal._reader._database) as connection:
        connection.execute("UPDATE d09_journals SET binding_json = '{}' WHERE lifecycle = 'ACCEPTED'")

    assert journal.capture(attempt_id=attempt_id, observation=_observation()).status == "RESULT_NOT_AVAILABLE"
    assert journal.reopen(attempt_id=attempt_id).status == "RESULT_NOT_AVAILABLE"


@pytest.mark.parametrize("round_number", range(3))
def test_synchronized_concurrent_equivalent_capture_replays_one_result(
    tmp_path: Path, round_number: int
) -> None:
    del round_number
    journal, attempt_id = _composition(tmp_path)
    results: list[i02.ProviderResultJournalReport] = []
    lock = threading.Lock()
    barrier = threading.Barrier(3)

    def capture() -> None:
        barrier.wait()
        result = journal.capture(attempt_id=attempt_id, observation=_observation())
        with lock:
            results.append(result)

    workers = [threading.Thread(target=capture) for _ in range(2)]
    for worker in workers:
        worker.start()
    barrier.wait()
    for worker in workers:
        worker.join()

    assert _accepted_result_count(journal) == 1
    assert all(item.status in {"RESULT_CAPTURED", "RECOVERY_REQUIRED"} for item in results)
    assert journal.reopen(attempt_id=attempt_id).status == "RESULT_CAPTURED"


@pytest.mark.parametrize("round_number", range(3))
def test_synchronized_concurrent_conflicting_capture_keeps_one_auditable_result(
    tmp_path: Path, round_number: int
) -> None:
    del round_number
    journal, attempt_id = _composition(tmp_path)
    first = _observation()
    second = _observation(outputs=[{"logical_output_id": "output:two", "sha256": "b" * 64, "media_type": "image/png", "metadata": {}}])
    results: list[i02.ProviderResultJournalReport] = []
    lock = threading.Lock()
    barrier = threading.Barrier(3)

    def capture(observation: dict[str, object]) -> None:
        barrier.wait()
        result = journal.capture(attempt_id=attempt_id, observation=observation)
        with lock:
            results.append(result)

    workers = [threading.Thread(target=capture, args=(observation,)) for observation in (first, second)]
    for worker in workers:
        worker.start()
    barrier.wait()
    for worker in workers:
        worker.join()

    assert _accepted_result_count(journal) == 1
    assert all(item.status in {"RESULT_CAPTURED", "RECOVERY_REQUIRED", "RESULT_AMBIGUOUS"} for item in results)
    replayed = journal.reopen(attempt_id=attempt_id)
    if replayed.status == "RESULT_CAPTURED":
        loser = second if replayed.evidence is not None and replayed.evidence.output_evidence[0].logical_output_id == "output:one" else first
        assert journal.capture(attempt_id=attempt_id, observation=loser).status == "RESULT_AMBIGUOUS"
    assert _accepted_result_count(journal) == 1
    assert journal.reopen(attempt_id=attempt_id).status == "RECOVERY_REQUIRED"


def test_reopen_without_capture_has_no_false_result_and_preserves_private_boundaries(tmp_path: Path) -> None:
    journal, attempt_id = _composition(tmp_path)

    assert journal.reopen(attempt_id=attempt_id).status == "RESULT_NOT_AVAILABLE"
    source = inspect.getsource(i02)
    for forbidden in (
        "domain.state_machine",
        "Generated",
        "generated_application",
        "manga_director.cli",
        "manga_director.mcp",
        "requests",
        "urllib",
        "subprocess",
        "socket",
    ):
        assert forbidden not in source
