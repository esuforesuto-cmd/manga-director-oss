from __future__ import annotations

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import pytest

from manga_director.production import (
    next_generation_durable_human_visual_review_evidence as evidence_module,
)
from manga_director.production.next_generation_durable_human_visual_review_evidence import (
    DurableHumanVisualReviewEvidenceUnavailable,
    LocalDurableHumanVisualReviewEvidenceOwner,
    _EvidenceChecklistItem,
    _EvidenceFinding,
    _HumanVisualReviewEvidencePayload,
)

_CRITERIA = (
    "character_identity",
    "face",
    "costume",
    "props",
    "pose",
    "gaze",
    "emotion",
    "screen_direction",
    "location",
    "time",
    "composition",
    "panel_intent",
    "visible_corruption",
    "truncation",
    "watermark",
    "unsafe_content",
    "unintended_text",
    "continuity_comparison",
)


def _payload(
    review_id: str = "review:v7-10:001",
    *,
    status: str = "ready",
) -> _HumanVisualReviewEvidencePayload:
    ready = status == "ready"
    return _HumanVisualReviewEvidencePayload(
        review_id=review_id,
        project_id="project-v7-10",
        page_id="1",
        page_number=1,
        page_state="QualityChecked",
        attempt_id="attempt:v7-10:001",
        output_asset_id="asset:v7-10:001",
        provenance_reference="provenance:v7-10:001",
        qa_report_reference="qa-report:v7-10:001",
        reviewer_id="reviewer:local",
        reviewed_at=datetime(2026, 10, 19, 12, 0, tzinfo=UTC),
        checklist=tuple(
            _EvidenceChecklistItem(
                criterion=criterion,
                outcome="acceptable",
                rationale="Reviewed directly",
            )
            for criterion in sorted(_CRITERIA)
        ),
        overall_judgment="acceptable_for_approval_consideration",
        rationale="Complete local visual review",
        status=status,
        ready=ready,
        findings=(
            ()
            if ready
            else (
                _EvidenceFinding(
                    code="QUALITY_CHECK_REQUIRED",
                    status="needs_review",
                    message="Quality review required.",
                ),
            )
        ),
        missing_prerequisites=() if ready else ("QUALITY_CHECK_REQUIRED",),
    )


def _database(root: Path) -> Path:
    return root / "review-evidence" / "human-visual-review-evidence.sqlite3"


def test_append_exact_retry_distinct_review_and_restart_lookup(tmp_path: Path) -> None:
    root = tmp_path / "normal"
    root.mkdir()
    owner = LocalDurableHumanVisualReviewEvidenceOwner(root)

    first = owner.persist(_payload())
    replay = owner.persist(_payload())
    second = owner.persist(_payload("review:v7-10:002"))

    assert first.outcome == "recorded"
    assert replay.outcome == "confirmed"
    assert second.outcome == "recorded"
    restarted = LocalDurableHumanVisualReviewEvidenceOwner(root)
    assert restarted._read_exact("review:v7-10:001") == _payload()
    with sqlite3.connect(_database(root)) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM human_visual_review_evidence_records"
        ).fetchone() == (2,)


def test_page_history_is_empty_when_store_is_absent_without_creating_state(
    tmp_path: Path,
) -> None:
    root = tmp_path / "normal"
    root.mkdir()
    owner = LocalDurableHumanVisualReviewEvidenceOwner(root)

    assert owner.read_page_history("project-v7-10", "1", 1) == ()
    assert tuple(root.iterdir()) == ()


def test_page_history_is_complete_bound_and_canonically_ordered(
    tmp_path: Path,
) -> None:
    root = tmp_path / "normal"
    root.mkdir()
    owner = LocalDurableHumanVisualReviewEvidenceOwner(root)
    owner.persist(_payload("review:v7-10:003"))
    owner.persist(_payload("review:v7-10:001"))
    owner.persist(_payload("review:v7-10:002"))
    owner.persist(
        _payload("review:v7-10:other").model_copy(
            update={"project_id": "project-v7-10-other"}
        )
    )
    before = {
        path.relative_to(root): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in root.rglob("*")
        if path.is_file()
    }

    history = owner.read_page_history("project-v7-10", "1", 1)

    assert tuple(item.review_id for item in history) == (
        "review:v7-10:001",
        "review:v7-10:002",
        "review:v7-10:003",
    )
    assert all(
        item.project_id == "project-v7-10"
        and item.page_id == "1"
        and item.page_number == 1
        for item in history
    )
    assert {
        path.relative_to(root): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in root.rglob("*")
        if path.is_file()
    } == before


def test_page_history_rejects_conflicting_missing_database_and_oversized_history(
    tmp_path: Path,
) -> None:
    conflicting_root = tmp_path / "conflicting"
    conflicting_root.mkdir()
    (conflicting_root / "review-evidence").mkdir()
    conflicting = LocalDurableHumanVisualReviewEvidenceOwner(conflicting_root)
    before_conflict = tuple((conflicting_root / "review-evidence").iterdir())

    with pytest.raises(DurableHumanVisualReviewEvidenceUnavailable):
        conflicting.read_page_history("project-v7-10", "1", 1)
    assert tuple((conflicting_root / "review-evidence").iterdir()) == before_conflict

    exact_root = tmp_path / "exact-bound"
    exact_root.mkdir()
    exact = LocalDurableHumanVisualReviewEvidenceOwner(exact_root)
    for index in range(32):
        exact.persist(_payload(f"review:v7-10:{index:03d}"))
    exact_before = _database(exact_root).read_bytes()

    exact_history = exact.read_page_history("project-v7-10", "1", 1)

    assert len(exact_history) == 32
    assert _database(exact_root).read_bytes() == exact_before

    bounded_root = tmp_path / "bounded"
    bounded_root.mkdir()
    bounded = LocalDurableHumanVisualReviewEvidenceOwner(bounded_root)
    for index in range(33):
        bounded.persist(_payload(f"review:v7-10:{index:03d}"))
    before_database = _database(bounded_root).read_bytes()

    with pytest.raises(DurableHumanVisualReviewEvidenceUnavailable):
        bounded.read_page_history("project-v7-10", "1", 1)
    assert _database(bounded_root).read_bytes() == before_database


def test_page_history_rejects_ambiguous_page_identity_without_partial_result(
    tmp_path: Path,
) -> None:
    root = tmp_path / "normal"
    root.mkdir()
    owner = LocalDurableHumanVisualReviewEvidenceOwner(root)
    owner.persist(_payload("review:v7-10:matching"))
    owner.persist(
        _payload("review:v7-10:ambiguous").model_copy(
            update={"page_id": "different-page-id"}
        )
    )
    before = _database(root).read_bytes()

    with pytest.raises(DurableHumanVisualReviewEvidenceUnavailable):
        owner.read_page_history("project-v7-10", "1", 1)

    assert _database(root).read_bytes() == before


def test_page_history_fails_whole_read_on_corruption_lock_or_budget_exhaustion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    corrupt_root = tmp_path / "corrupt"
    corrupt_root.mkdir()
    corrupt = LocalDurableHumanVisualReviewEvidenceOwner(corrupt_root)
    corrupt.persist(_payload())
    corrupt.persist(
        _payload("review:v7-10:other").model_copy(
            update={"project_id": "project-v7-10-other"}
        )
    )
    with sqlite3.connect(_database(corrupt_root)) as connection:
        connection.execute(
            "UPDATE human_visual_review_evidence_records SET payload_digest = ? "
            "WHERE review_id = ?",
            ("0" * 64, "review:v7-10:other"),
        )
    corrupt_before = _database(corrupt_root).read_bytes()
    with pytest.raises(DurableHumanVisualReviewEvidenceUnavailable):
        corrupt.read_page_history("project-v7-10", "1", 1)
    assert _database(corrupt_root).read_bytes() == corrupt_before

    busy_root = tmp_path / "busy-history"
    busy_root.mkdir()
    busy = LocalDurableHumanVisualReviewEvidenceOwner(busy_root)
    busy.persist(_payload())
    with sqlite3.connect(_database(busy_root), timeout=0.0, isolation_level=None) as lock:
        lock.execute("BEGIN EXCLUSIVE")
        with pytest.raises(DurableHumanVisualReviewEvidenceUnavailable):
            busy.read_page_history("project-v7-10", "1", 1)
        lock.rollback()

    budget_root = tmp_path / "budget"
    budget_root.mkdir()
    budget = LocalDurableHumanVisualReviewEvidenceOwner(budget_root)
    budget.persist(_payload())
    budget_before = _database(budget_root).read_bytes()
    monkeypatch.setattr(evidence_module, "_READ_PROGRESS_GRANULARITY", 1)
    monkeypatch.setattr(evidence_module, "_MAX_READ_PROGRESS_CALLBACKS", 0)
    with pytest.raises(DurableHumanVisualReviewEvidenceUnavailable):
        budget.read_page_history("project-v7-10", "1", 1)
    assert _database(budget_root).read_bytes() == budget_before


def test_exact_id_conflict_and_corrupt_payload_fail_without_repair(tmp_path: Path) -> None:
    root = tmp_path / "normal"
    root.mkdir()
    owner = LocalDurableHumanVisualReviewEvidenceOwner(root)
    owner.persist(_payload())
    database = _database(root)
    with sqlite3.connect(database) as connection:
        raw = connection.execute(
            "SELECT payload_json FROM human_visual_review_evidence_records"
        ).fetchone()[0]
        changed = json.loads(raw)
        changed["rationale"] = "Different human judgment"
        connection.execute(
            "UPDATE human_visual_review_evidence_records SET payload_json = ?",
            (json.dumps(changed, separators=(",", ":"), sort_keys=True),),
        )
    before = database.read_bytes()

    with pytest.raises(DurableHumanVisualReviewEvidenceUnavailable):
        owner.persist(_payload())

    assert database.read_bytes() == before


def test_schema_mismatch_busy_database_and_missing_reader_fail_closed(
    tmp_path: Path,
) -> None:
    missing_root = tmp_path / "missing"
    missing_root.mkdir()
    missing = LocalDurableHumanVisualReviewEvidenceOwner(missing_root)
    before = tuple(missing_root.iterdir())
    with pytest.raises(DurableHumanVisualReviewEvidenceUnavailable):
        missing._read_exact("review:v7-10:missing")
    assert tuple(missing_root.iterdir()) == before

    schema_root = tmp_path / "schema"
    schema_root.mkdir()
    schema = LocalDurableHumanVisualReviewEvidenceOwner(schema_root)
    schema.persist(_payload())
    database = _database(schema_root)
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA user_version=99")
    before_schema = database.read_bytes()
    with pytest.raises(DurableHumanVisualReviewEvidenceUnavailable):
        schema.persist(_payload("review:v7-10:002"))
    assert database.read_bytes() == before_schema

    busy_root = tmp_path / "busy"
    busy_root.mkdir()
    busy = LocalDurableHumanVisualReviewEvidenceOwner(busy_root)
    busy.persist(_payload())
    with sqlite3.connect(_database(busy_root), timeout=0.0, isolation_level=None) as lock:
        lock.execute("BEGIN EXCLUSIVE")
        with pytest.raises(DurableHumanVisualReviewEvidenceUnavailable):
            busy.persist(_payload("review:v7-10:002"))
        lock.rollback()
    with sqlite3.connect(_database(busy_root)) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM human_visual_review_evidence_records"
        ).fetchone() == (1,)


def test_failed_initialization_leaves_no_sidecar(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "normal"
    root.mkdir()
    owner = LocalDurableHumanVisualReviewEvidenceOwner(root)

    def fail_schema(_connection: sqlite3.Connection) -> None:
        raise sqlite3.OperationalError("injected")

    monkeypatch.setattr(evidence_module, "_create_schema", fail_schema)
    with pytest.raises(DurableHumanVisualReviewEvidenceUnavailable):
        owner.persist(_payload())

    assert not (root / "review-evidence").exists()


def test_first_commit_failure_leaves_no_schema_or_sidecar(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "normal"
    root.mkdir()
    owner = LocalDurableHumanVisualReviewEvidenceOwner(root)

    def fail_commit(_connection: sqlite3.Connection) -> None:
        raise sqlite3.OperationalError("injected")

    monkeypatch.setattr(evidence_module, "_commit", fail_commit)
    with pytest.raises(DurableHumanVisualReviewEvidenceUnavailable):
        owner.persist(_payload())

    assert not (root / "review-evidence").exists()


def test_existing_wal_store_fails_closed_without_mutation(tmp_path: Path) -> None:
    root = tmp_path / "normal"
    root.mkdir()
    owner = LocalDurableHumanVisualReviewEvidenceOwner(root)
    owner.persist(_payload())
    database = _database(root)
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA journal_mode=WAL").fetchone() == ("wal",)
    before = {
        path.relative_to(root): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }

    with pytest.raises(DurableHumanVisualReviewEvidenceUnavailable):
        owner.persist(_payload("review:v7-10:wal"))
    with pytest.raises(DurableHumanVisualReviewEvidenceUnavailable):
        owner._read_exact("review:v7-10:001")

    after = {
        path.relative_to(root): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }
    assert after == before


def test_concurrent_writers_serialize_without_lost_records(tmp_path: Path) -> None:
    root = tmp_path / "normal"
    root.mkdir()
    owner = LocalDurableHumanVisualReviewEvidenceOwner(root)
    owner.persist(_payload())

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(
            executor.map(
                owner.persist,
                (_payload("review:v7-10:002"), _payload("review:v7-10:003")),
            )
        )

    assert tuple(result.outcome for result in results) == ("recorded", "recorded")
    with sqlite3.connect(_database(root)) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM human_visual_review_evidence_records"
        ).fetchone() == (3,)


@pytest.mark.parametrize("column", ("binding_fingerprint", "payload_digest"))
def test_binding_and_digest_corruption_fail_without_repair(
    tmp_path: Path,
    column: str,
) -> None:
    root = tmp_path / "normal"
    root.mkdir()
    owner = LocalDurableHumanVisualReviewEvidenceOwner(root)
    owner.persist(_payload())
    database = _database(root)
    with sqlite3.connect(database) as connection:
        connection.execute(
            f"UPDATE human_visual_review_evidence_records SET {column} = ?",
            ("0" * 64,),
        )
    before = database.read_bytes()

    with pytest.raises(DurableHumanVisualReviewEvidenceUnavailable):
        owner._read_exact("review:v7-10:001")

    assert database.read_bytes() == before


def test_private_payload_repr_redacts_human_and_binding_data() -> None:
    payload = _payload()

    assert repr(payload) == "_HumanVisualReviewEvidencePayload(<redacted>)"
    assert repr(payload.checklist[0]) == "_EvidenceChecklistItem(<redacted>)"
    assert not any(
        value in repr(payload)
        for value in (
            payload.rationale,
            payload.reviewer_id,
            payload.attempt_id,
            payload.output_asset_id,
        )
    )


def test_symlinked_sidecar_root_is_rejected_when_supported(tmp_path: Path) -> None:
    root = tmp_path / "normal"
    root.mkdir()
    target = tmp_path / "target"
    target.mkdir()
    directory = root / "review-evidence"
    try:
        directory.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are unavailable")

    owner = LocalDurableHumanVisualReviewEvidenceOwner(root)
    with pytest.raises(DurableHumanVisualReviewEvidenceUnavailable):
        owner.persist(_payload())

    assert not _database(root).exists()


def test_symlinked_database_is_rejected_when_supported(tmp_path: Path) -> None:
    target_root = tmp_path / "target-root"
    target_root.mkdir()
    LocalDurableHumanVisualReviewEvidenceOwner(target_root).persist(_payload())

    root = tmp_path / "normal"
    root.mkdir()
    directory = root / "review-evidence"
    directory.mkdir()
    database = _database(root)
    try:
        database.symlink_to(_database(target_root))
    except OSError:
        pytest.skip("file symlinks are unavailable")

    owner = LocalDurableHumanVisualReviewEvidenceOwner(root)
    with pytest.raises(DurableHumanVisualReviewEvidenceUnavailable):
        owner.persist(_payload("review:v7-10:linked"))

    assert database.is_symlink()
