from __future__ import annotations

import json
import multiprocessing
import time
from pathlib import Path
from queue import Empty
from typing import Any

import pytest

from manga_director.domain.project import Page, Project
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.repositories.local_file_durability import (
    LocalFileDurabilityError,
    StaleRevisionError,
    _select_project_commit_fence,
)


def _project(*, image: dict[str, object] | None = None) -> Project:
    return Project(id="durable-demo", title="Durable Demo", pages=[Page(page_number=1, image=image)])


def _repository(tmp_path: Path) -> LocalFileRepository:
    repository = LocalFileRepository(tmp_path)
    repository.save(_project())
    return repository


def _renamed(project: Project, title: str) -> Project:
    return project.model_copy(update={"title": title}, deep=True)


def _hold_fence(
    root: Path,
    project_id: str,
    ready: multiprocessing.Queue[bool],
    diagnostics: Any,
) -> None:
    diagnostics[0] = time.perf_counter_ns()
    diagnostics[1] = time.perf_counter_ns()
    with _select_project_commit_fence(root, project_id, timeout_ms=1_000):
        diagnostics[2] = time.perf_counter_ns()
        diagnostics[3] = time.perf_counter_ns()
        ready.put(True)
        diagnostics[4] = time.perf_counter_ns()
        time.sleep(0.5)


def _snapshot_diagnostic_values(
    diagnostics: Any,
) -> tuple[list[int], bool, Exception | None]:
    try:
        lock = diagnostics.get_lock()
        if not lock.acquire(timeout=0.1):
            return [0] * 5, False, None
        try:
            return list(diagnostics.get_obj()[:]), True, None
        finally:
            lock.release()
    except Exception as error:
        return [0] * 5, False, error


def _reap_diagnostic_child(
    holder: multiprocessing.Process, diagnostics: Any
) -> tuple[list[int], bool, bool, Exception | None]:
    cleanup_error: Exception | None = None

    def is_alive() -> bool:
        nonlocal cleanup_error
        try:
            return holder.is_alive()
        except Exception as error:
            cleanup_error = cleanup_error or error
            return True

    try:
        holder.join(timeout=2)
    except Exception as error:
        cleanup_error = error
    diagnostic_snapshot, snapshot_available, snapshot_error = _snapshot_diagnostic_values(
        diagnostics
    )
    cleanup_error = cleanup_error or snapshot_error
    if is_alive():
        for stop_process in (holder.terminate, holder.kill):
            if not is_alive():
                break
            try:
                stop_process()
            except Exception as error:
                cleanup_error = cleanup_error or error
            try:
                holder.join(timeout=2)
            except Exception as error:
                cleanup_error = cleanup_error or error
        return diagnostic_snapshot, snapshot_available, is_alive(), cleanup_error
    return diagnostic_snapshot, snapshot_available, False, cleanup_error


def test_legacy_aggregate_lazily_receives_private_revision(tmp_path: Path) -> None:
    repository = _repository(tmp_path)

    snapshot = repository._load_revisioned("durable-demo")

    assert snapshot.revision == 1
    assert "revision" not in snapshot.project.model_dump(mode="json")
    assert "_durability" not in (tmp_path / "projects" / "durable-demo.json").read_text(
        encoding="utf-8"
    )


def test_exact_conditional_commit_advances_private_revision(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    snapshot = repository._load_revisioned("durable-demo")

    result = repository._conditional_commit(snapshot, _renamed(snapshot.project, "Committed"))

    assert result.revision == 2
    assert result.derived_warnings == ()
    assert repository.load("durable-demo").title == "Committed"
    assert repository._load_revisioned("durable-demo").revision == 2


def test_stale_snapshot_fails_before_authoritative_replacement(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    first = repository._load_revisioned("durable-demo")
    stale = repository._load_revisioned("durable-demo")
    repository._conditional_commit(first, _renamed(first.project, "First"))

    with pytest.raises(StaleRevisionError, match="stale_authoritative_revision"):
        repository._conditional_commit(stale, _renamed(stale.project, "Stale"))

    assert repository.load("durable-demo").title == "First"


def test_project_commit_fence_contends_and_repeated_release_is_safe(tmp_path: Path) -> None:
    root = tmp_path / "projects"
    root.mkdir()
    project_id = "durable-demo"
    ready: multiprocessing.Queue[bool] = multiprocessing.Queue()
    # Shared timestamps are independent of Queue delivery; the parent snapshots
    # them with a bounded lock wait before attempting child termination.
    diagnostics = multiprocessing.Array("q", 5, lock=True)
    holder = multiprocessing.Process(
        target=_hold_fence, args=(root, project_id, ready, diagnostics)
    )
    start_started_ns: int | None = None
    start_completed_ns: int | None = None
    ready_received_ns: int | None = None
    ready_wait_ended_ns: int | None = None
    ready_value: bool | None = None
    diagnostic_snapshot: list[int] = [0] * 5
    diagnostic_snapshot_available = False
    process_started = False
    cleanup_failed = False
    cleanup_error: Exception | None = None
    try:
        start_started_ns = time.perf_counter_ns()
        holder.start()
        process_started = True
        start_completed_ns = time.perf_counter_ns()
        try:
            ready_value = ready.get(timeout=2)
        except Empty:
            ready_wait_ended_ns = time.perf_counter_ns()
            raise
        else:
            ready_received_ns = time.perf_counter_ns()
        assert ready_value is True
        with pytest.raises(LocalFileDurabilityError, match="project_commit_fence_contended"):
            with _select_project_commit_fence(root, project_id, timeout_ms=1):
                pass
    finally:
        if process_started:
            (
                diagnostic_snapshot,
                diagnostic_snapshot_available,
                cleanup_failed,
                cleanup_error,
            ) = _reap_diagnostic_child(holder, diagnostics)
        try:
            ready.close()
        except Exception as error:
            cleanup_error = cleanup_error or error

        (
            child_started_ns,
            fence_started_ns,
            fence_acquired_ns,
            ready_send_started_ns,
            ready_put_returned_ns,
        ) = diagnostic_snapshot

        def elapsed(start: int | None, end: int | None) -> int | None:
            return end - start if start is not None and end is not None else None

        try:
            child_exitcode = holder.exitcode if process_started else None
        except Exception as error:
            child_exitcode = None
            cleanup_error = cleanup_error or error
            cleanup_failed = True
        print(
            "windows_fence_diagnostic="
            + json.dumps(
                {
                    "process_start_call_ns": elapsed(start_started_ns, start_completed_ns),
                    "child_start_delay_ns": elapsed(start_started_ns, child_started_ns or None),
                    "fence_acquire_ns": elapsed(
                        fence_started_ns or None, fence_acquired_ns or None
                    ),
                    "ready_send_to_receive_ns": elapsed(
                        ready_send_started_ns or None, ready_received_ns
                    ),
                    "ready_send_to_timeout_ns": elapsed(
                        ready_send_started_ns or None, ready_wait_ended_ns
                    ),
                    "ready_put_returned_ns": ready_put_returned_ns or None,
                    "ready_put_return_to_receive_ns": elapsed(
                        ready_put_returned_ns or None, ready_received_ns
                    ),
                    "ready_received": ready_received_ns is not None and ready_value is True,
                    "child_exitcode": child_exitcode,
                    "diagnostic_snapshot_available": diagnostic_snapshot_available,
                    "child_cleanup_failed": cleanup_failed,
                    "child_cleanup_error": (
                        type(cleanup_error).__name__ if cleanup_error is not None else None
                    ),
                },
                sort_keys=True,
            ),
            flush=True,
        )
        if cleanup_error is not None:
            raise RuntimeError("diagnostic child cleanup raised an error") from cleanup_error
        if cleanup_failed:
            raise RuntimeError("diagnostic child process could not be reaped")
    assert holder.exitcode == 0
    first = _select_project_commit_fence(root, project_id, timeout_ms=50)
    with first:
        pass
    first.release()


def test_malformed_or_unsupported_revision_sidecar_fails_closed(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    repository._load_revisioned("durable-demo")
    path = repository._revision_store._committed_path("durable-demo")
    path.write_text('{"schema_version": 99}', encoding="utf-8")

    with pytest.raises(LocalFileDurabilityError, match="revision_record_schema_invalid"):
        repository._load_revisioned("durable-demo")


def test_aggregate_fingerprint_mismatch_fails_closed(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    repository._load_revisioned("durable-demo")
    aggregate = tmp_path / "projects" / "durable-demo.json"
    aggregate.write_text(repository._serializer.dumps(_renamed(_project(), "External")), encoding="utf-8")

    with pytest.raises(LocalFileDurabilityError, match="authoritative_fingerprint_mismatch"):
        repository._load_revisioned("durable-demo")


def test_committed_sidecar_failure_is_safely_reconciled_when_new_aggregate_is_exact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository(tmp_path)
    snapshot = repository._load_revisioned("durable-demo")
    original = repository._revision_store._write_committed

    def fail_finalization(record: Any) -> None:
        if record.revision == 2:
            raise LocalFileDurabilityError("private_revision_write_failed")
        original(record)

    monkeypatch.setattr(repository._revision_store, "_write_committed", fail_finalization)
    with pytest.raises(LocalFileDurabilityError, match="private_revision_write_failed"):
        repository._conditional_commit(snapshot, _renamed(snapshot.project, "Committed"))
    monkeypatch.setattr(repository._revision_store, "_write_committed", original)

    reconciled = repository._load_revisioned("durable-demo")
    assert reconciled.revision == 2
    assert reconciled.project.title == "Committed"


def test_unreplaced_prepared_record_remains_fail_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repository = _repository(tmp_path)
    snapshot = repository._load_revisioned("durable-demo")
    original_stage = repository._revision_store._stage
    calls = 0

    def fail_aggregate_stage(path: Path, payload: bytes) -> Path:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise LocalFileDurabilityError("authoritative_staging_failed")
        return original_stage(path, payload)

    monkeypatch.setattr(repository._revision_store, "_stage", fail_aggregate_stage)
    with pytest.raises(LocalFileDurabilityError, match="authoritative_staging_failed"):
        repository._conditional_commit(snapshot, _renamed(snapshot.project, "Blocked"))

    with pytest.raises(LocalFileDurabilityError, match="prepared_revision_unresolved"):
        repository._load_revisioned("durable-demo")


def test_derived_failures_are_redacted_and_cannot_change_authoritative_aggregate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository(tmp_path)
    snapshot = repository._load_revisioned("durable-demo")
    monkeypatch.setattr(
        repository,
        "_save_page_documents",
        lambda project: (_ for _ in ()).throw(OSError("private path detail")),
    )
    monkeypatch.setattr(
        repository,
        "_read_index",
        lambda: (_ for _ in ()).throw(OSError("private path detail")),
    )

    result = repository._conditional_commit(snapshot, _renamed(snapshot.project, "Authoritative"))

    assert result.revision == 2
    assert result.derived_warnings == (
        "derived_page_update_failed",
        "derived_metadata_index_update_failed",
    )
    assert "private path detail" not in repr(result)
    assert repository.load("durable-demo").title == "Authoritative"


def test_authoritative_page_read_bypasses_a_stale_derived_page_document(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    snapshot = repository._load_revisioned("durable-demo")
    changed_page = snapshot.project.page(1).model_copy(update={"metadata": {"fresh": True}})
    changed_project = snapshot.project.replace_page(changed_page)
    repository._conditional_commit(snapshot, changed_project)
    stale = Page(page_number=1, metadata={"fresh": False})
    page_path = tmp_path / "projects" / "_pages" / "durable-demo" / "1.json"
    page_path.write_text(stale.model_dump_json(), encoding="utf-8")

    assert repository._load_authoritative_page("durable-demo", 1).metadata == {"fresh": True}


@pytest.mark.parametrize(
    "image",
    [
        {"artifact_kind": "logical_output_asset", "output_asset_id": "asset-001"},
        {"image_path": "legacy/approved.png"},
    ],
)
def test_image_payloads_round_trip_without_private_revision_leak(
    tmp_path: Path, image: dict[str, object]
) -> None:
    repository = LocalFileRepository(tmp_path)
    project = _project(image=image)
    repository.save(project)
    snapshot = repository._load_revisioned(project.id)
    result = repository._conditional_commit(snapshot, snapshot.project)

    assert repository.load(project.id).page(1).image == image
    assert result.revision == 2
    payload = json.loads((tmp_path / "projects" / "durable-demo.json").read_text(encoding="utf-8"))
    assert "revision" not in payload
    assert "fingerprint" not in payload


def test_snapshot_and_input_project_are_not_mutated(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    snapshot = repository._load_revisioned("durable-demo")
    before = snapshot.project.model_dump(mode="json")
    proposed = _renamed(snapshot.project, "Immutable")

    repository._conditional_commit(snapshot, proposed)

    assert snapshot.project.model_dump(mode="json") == before
    assert proposed.title == "Immutable"
