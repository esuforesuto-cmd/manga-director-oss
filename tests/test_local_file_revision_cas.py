from __future__ import annotations

import json
import multiprocessing
import time
from pathlib import Path
from typing import Any

import pytest

from manga_director.domain.project import Page, Project
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.repositories.local_file_durability import (
    LocalFileDurabilityError,
    StaleRevisionError,
    WindowsProjectCommitFence,
)


def _project(*, image: dict[str, object] | None = None) -> Project:
    return Project(id="durable-demo", title="Durable Demo", pages=[Page(page_number=1, image=image)])


def _repository(tmp_path: Path) -> LocalFileRepository:
    repository = LocalFileRepository(tmp_path)
    repository.save(_project())
    return repository


def _renamed(project: Project, title: str) -> Project:
    return project.model_copy(update={"title": title}, deep=True)


def _hold_fence(identity: str, ready: multiprocessing.Queue[bool]) -> None:
    with WindowsProjectCommitFence(identity, timeout_ms=1_000):
        ready.put(True)
        time.sleep(0.5)


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


def test_project_commit_fence_contends_and_repeated_release_is_safe() -> None:
    identity = "Local\\MangaDirectorTestRevisionFence"
    ready: multiprocessing.Queue[bool] = multiprocessing.Queue()
    holder = multiprocessing.Process(target=_hold_fence, args=(identity, ready))
    holder.start()
    assert ready.get(timeout=2) is True
    try:
        with pytest.raises(LocalFileDurabilityError, match="project_commit_fence_contended"):
            with WindowsProjectCommitFence(identity, timeout_ms=1):
                pass
    finally:
        holder.join(timeout=2)
    assert holder.exitcode == 0
    first = WindowsProjectCommitFence(identity, timeout_ms=50)
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
