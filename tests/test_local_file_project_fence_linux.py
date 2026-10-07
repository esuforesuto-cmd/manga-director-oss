from __future__ import annotations

import hashlib
import importlib
import multiprocessing
import os
import time
from pathlib import Path

import pytest

from manga_director.repositories.local_file_durability import (
    LocalFileDurabilityError,
    _project_commit_identity,
    _select_project_commit_fence,
)


def _lock_path(root: Path, project_id: str) -> Path:
    identity = _project_commit_identity(root, project_id)
    return root.resolve() / "_durability" / f"{identity}.project-commit.lock"


def _race_for_fence(
    root: Path,
    project_id: str,
    start: multiprocessing.synchronize.Event,
    release: multiprocessing.synchronize.Event,
    results: multiprocessing.Queue[str],
) -> None:
    assert start.wait(timeout=5)
    try:
        with _select_project_commit_fence(root, project_id, timeout_ms=150):
            results.put("acquired")
            assert release.wait(timeout=5)
    except LocalFileDurabilityError as error:
        results.put(str(error))


def _hold_until_terminated(
    root: Path, project_id: str, ready: multiprocessing.synchronize.Event
) -> None:
    with _select_project_commit_fence(root, project_id):
        ready.set()
        time.sleep(30)


@pytest.mark.skipif(os.name != "posix", reason="POSIX project fence contract")
def test_linux_project_fence_identity_and_artifact_are_private_and_zero_payload(
    tmp_path: Path,
) -> None:
    root = tmp_path / "projects"
    root.mkdir()
    project_id = "private-project-token"
    identity = _project_commit_identity(root, project_id)
    expected = hashlib.sha256(f"{root.resolve()}\x00{project_id}".encode()).hexdigest()

    with _select_project_commit_fence(root, project_id):
        path = _lock_path(root, project_id)
        assert path.is_file()
        assert path.read_bytes() == b""

    assert identity == expected
    assert project_id not in path.name
    assert str(root) not in path.name


@pytest.mark.skipif(os.name != "posix", reason="POSIX project fence contract")
def test_linux_project_fence_is_nonreentrant_owner_only_and_binding_scoped(
    tmp_path: Path,
) -> None:
    root = tmp_path / "projects"
    root.mkdir()
    first = _select_project_commit_fence(root, "same", timeout_ms=20)
    nonowner = _select_project_commit_fence(root, "same", timeout_ms=20)

    with first:
        nonowner.release()
        with pytest.raises(LocalFileDurabilityError, match="project_commit_fence_contended"):
            with _select_project_commit_fence(root, "same", timeout_ms=20):
                pass
        with _select_project_commit_fence(root, "different", timeout_ms=20):
            pass

    first.release()
    with _select_project_commit_fence(root, "same", timeout_ms=20):
        pass


@pytest.mark.skipif(os.name != "posix", reason="POSIX project fence contract")
def test_linux_project_fence_subprocess_race_has_one_winner_and_bounded_loser(
    tmp_path: Path,
) -> None:
    root = tmp_path / "projects"
    root.mkdir()
    context = multiprocessing.get_context("spawn")
    start = context.Event()
    release = context.Event()
    results: multiprocessing.Queue[str] = context.Queue()
    workers = [
        context.Process(target=_race_for_fence, args=(root, "race", start, release, results))
        for _ in range(2)
    ]
    for worker in workers:
        worker.start()
    started = time.monotonic()
    start.set()
    observed = [results.get(timeout=5), results.get(timeout=5)]
    release.set()
    for worker in workers:
        worker.join(timeout=5)

    assert sorted(observed) == ["acquired", "project_commit_fence_contended"]
    assert time.monotonic() - started < 2
    assert all(worker.exitcode == 0 for worker in workers)


@pytest.mark.skipif(os.name != "posix", reason="POSIX project fence contract")
def test_linux_project_fence_process_death_releases_kernel_ownership(tmp_path: Path) -> None:
    root = tmp_path / "projects"
    root.mkdir()
    context = multiprocessing.get_context("spawn")
    ready = context.Event()
    holder = context.Process(target=_hold_until_terminated, args=(root, "crash", ready))
    holder.start()
    assert ready.wait(timeout=5)
    holder.terminate()
    holder.join(timeout=5)
    assert not holder.is_alive()

    with _select_project_commit_fence(root, "crash", timeout_ms=500):
        pass


@pytest.mark.skipif(os.name != "posix", reason="POSIX project fence contract")
def test_linux_project_fence_accepts_stale_artifact_and_rejects_tampering(
    tmp_path: Path,
) -> None:
    root = tmp_path / "projects"
    root.mkdir()
    path = _lock_path(root, "artifact")
    path.parent.mkdir(mode=0o700)
    path.touch(mode=0o600)

    with _select_project_commit_fence(root, "artifact"):
        pass

    path.chmod(0o644)
    with pytest.raises(LocalFileDurabilityError, match="project_commit_fence_unavailable"):
        with _select_project_commit_fence(root, "artifact"):
            pass
    path.chmod(0o600)
    path.write_bytes(b"tampered")
    with pytest.raises(LocalFileDurabilityError, match="project_commit_fence_unavailable"):
        with _select_project_commit_fence(root, "artifact"):
            pass
    path.unlink()
    path.mkdir()
    with pytest.raises(LocalFileDurabilityError, match="project_commit_fence_unavailable"):
        with _select_project_commit_fence(root, "artifact"):
            pass


@pytest.mark.skipif(os.name != "posix", reason="POSIX project fence contract")
def test_linux_project_fence_rejects_symlink_artifact(tmp_path: Path) -> None:
    root = tmp_path / "projects"
    root.mkdir()
    path = _lock_path(root, "symlink")
    path.parent.mkdir(mode=0o700)
    target = tmp_path / "outside"
    target.touch()
    path.symlink_to(target)

    with pytest.raises(LocalFileDurabilityError, match="project_commit_fence_unavailable"):
        with _select_project_commit_fence(root, "symlink"):
            pass


@pytest.mark.skipif(os.name != "posix", reason="POSIX project fence contract")
def test_linux_project_fence_maps_unsupported_kernel_locking_to_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "projects"
    root.mkdir()

    class _UnsupportedFcntl:
        LOCK_EX = 1
        LOCK_NB = 2

        @staticmethod
        def flock(descriptor: int, operation: int) -> None:
            del descriptor, operation
            raise OSError("unsupported filesystem locking")

    original_import = importlib.import_module
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda name: _UnsupportedFcntl if name == "fcntl" else original_import(name),
    )

    with pytest.raises(LocalFileDurabilityError, match="project_commit_fence_unavailable"):
        with _select_project_commit_fence(root, "unsupported"):
            pass
