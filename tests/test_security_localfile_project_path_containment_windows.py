from __future__ import annotations

import ctypes
import gc
import os
import stat
import subprocess
import threading
import time
from pathlib import Path

import pytest

from manga_director.domain.exceptions import ValidationError
from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.repositories import LocalFileRepository
from manga_director.repositories import _windows_safe_filesystem as safe_fs

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows handle containment only")


def _project(project_id: str = "victim", *, title: str = "Inside") -> Project:
    return Project(
        id=project_id,
        title=title,
        pages=[Page(page_number=1, state=PageState.DESIGNED, page_design={"purpose": "hook"})],
    )


def _prepare_outside_victim(
    repository: LocalFileRepository,
    outside: Path,
) -> bytes:
    repository.save(_project(title="Outside victim"))
    aggregate = repository._path("victim")
    payload = aggregate.read_bytes()
    aggregate.unlink()
    outside.mkdir(parents=True)
    (outside / aggregate.name).write_bytes(payload)
    return payload


def _create_junction(link: Path, target: Path) -> None:
    result = subprocess.run(
        ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise OSError(result.returncode, "junction creation failed")


def _remove_junction(link: Path) -> None:
    if (
        os.path.lexists(link)
        and os.lstat(link).st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT
    ):
        os.rmdir(link)


def _swap_to_junction(path: Path, target: Path) -> Path:
    moved = path.with_name(f"{path.name}-original")
    path.rename(moved)
    try:
        _create_junction(path, target)
    except Exception:
        moved.rename(path)
        raise
    return moved


def _restore_swap(path: Path, moved: Path | None) -> None:
    if moved is None:
        return
    _remove_junction(path)
    if moved.exists() and not path.exists():
        moved.rename(path)


@pytest.mark.parametrize("operation", ("exists", "load", "delete"))
def test_root_swap_after_identifier_validation_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    repository = LocalFileRepository(tmp_path / "owner")
    outside = tmp_path / "outside-projects"
    payload = _prepare_outside_victim(repository, outside)
    root = repository._root
    original_validate = LocalFileRepository._validate_project_id
    moved: Path | None = None

    def validate_and_swap(project_id: str) -> None:
        nonlocal moved
        original_validate(project_id)
        if project_id == "victim" and moved is None:
            moved = _swap_to_junction(root, outside)

    monkeypatch.setattr(
        LocalFileRepository,
        "_validate_project_id",
        staticmethod(validate_and_swap),
    )
    try:
        with pytest.raises(ValidationError):
            getattr(repository, operation)("victim")
        assert (outside / "victim.json").read_bytes() == payload
    finally:
        _restore_swap(root, moved)


def test_owner_parent_swap_after_identifier_validation_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = tmp_path / "owner"
    repository = LocalFileRepository(owner)
    outside_owner = tmp_path / "outside-owner"
    outside_projects = outside_owner / "projects"
    payload = _prepare_outside_victim(repository, outside_projects)
    original_validate = LocalFileRepository._validate_project_id
    moved: Path | None = None

    def validate_and_swap(project_id: str) -> None:
        nonlocal moved
        original_validate(project_id)
        if project_id == "victim" and moved is None:
            moved = _swap_to_junction(owner, outside_owner)

    monkeypatch.setattr(
        LocalFileRepository,
        "_validate_project_id",
        staticmethod(validate_and_swap),
    )
    try:
        with pytest.raises(ValidationError):
            repository.load("victim")
        assert (outside_projects / "victim.json").read_bytes() == payload
    finally:
        _restore_swap(owner, moved)


def test_ancestor_swap_after_owner_handle_open_cannot_redirect_child_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    namespace = tmp_path / "namespace"
    owner = namespace / "owner"
    repository = LocalFileRepository(owner)
    outside_namespace = tmp_path / "outside-namespace"
    outside_projects = outside_namespace / "owner" / "projects"
    payload = _prepare_outside_victim(repository, outside_projects)
    moved = namespace.with_name("namespace-original")
    attempted = False

    def attack_after_component(self: object, path: Path) -> None:
        nonlocal attempted
        if path != owner or attempted:
            return
        attempted = True
        try:
            namespace.rename(moved)
            _create_junction(namespace, outside_namespace)
        except OSError:
            pass

    monkeypatch.setattr(
        safe_fs._WindowsSafeSession,
        "_after_component_open",
        attack_after_component,
    )
    try:
        assert repository.exists("victim") is False
        assert attempted is True
        assert (outside_projects / "victim.json").read_bytes() == payload
    finally:
        _remove_junction(namespace)
        if moved.exists() and not namespace.exists():
            moved.rename(namespace)


def test_root_handle_blocks_swap_before_target_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = LocalFileRepository(tmp_path / "owner")
    outside = tmp_path / "outside-projects"
    payload = _prepare_outside_victim(repository, outside)
    root = repository._root
    moved: Path | None = None
    attempted = False
    blocked = False

    def attack_after_component(self: object, path: Path) -> None:
        nonlocal attempted, blocked, moved
        if path != root or attempted:
            return
        attempted = True
        try:
            moved = _swap_to_junction(root, outside)
        except OSError:
            blocked = True

    monkeypatch.setattr(
        safe_fs._WindowsSafeSession,
        "_after_component_open",
        attack_after_component,
    )
    try:
        try:
            result = repository.exists("victim")
        except ValidationError:
            result = False
        assert attempted is True
        assert blocked is True
        assert moved is None
        assert result is False
        assert (outside / "victim.json").read_bytes() == payload
    finally:
        _restore_swap(root, moved)


@pytest.mark.parametrize("operation", ("load", "delete"))
def test_target_handle_is_used_after_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    repository = LocalFileRepository(tmp_path / "owner")
    project = _project()
    repository.save(project)
    aggregate = repository._path(project.id)
    moved = aggregate.with_suffix(".moved")
    outside = tmp_path / "outside.json"
    outside.write_text("outside sentinel", encoding="utf-8")
    attempted = False
    blocked = False

    def attack_after_target(self: object, path: Path, directory: bool) -> None:
        nonlocal attempted, blocked
        if directory or path != aggregate or attempted:
            return
        attempted = True
        try:
            path.rename(moved)
        except OSError:
            blocked = True

    monkeypatch.setattr(
        safe_fs._WindowsSafeSession,
        "_after_target_open",
        attack_after_target,
    )
    if operation == "load":
        assert repository.load(project.id) == project
        assert aggregate.is_file()
    else:
        repository.delete(project.id)
        assert not aggregate.exists()
    assert attempted is True
    assert blocked is True
    assert outside.read_text(encoding="utf-8") == "outside sentinel"


def test_delete_rejects_reparse_page_parent_without_touching_outside(
    tmp_path: Path,
) -> None:
    repository = LocalFileRepository(tmp_path / "owner")
    repository.save(_project())
    pages = repository._root / "_pages"
    moved = pages.with_name("_pages-original")
    outside = tmp_path / "outside-pages"
    outside.mkdir()
    victim = outside / "1.json"
    victim.write_text("outside sentinel", encoding="utf-8")
    pages.rename(moved)
    _create_junction(pages, outside)
    try:
        with pytest.raises(ValidationError):
            repository.delete("victim")
        assert victim.read_text(encoding="utf-8") == "outside sentinel"
    finally:
        _remove_junction(pages)
        moved.rename(pages)


def test_success_and_failure_paths_do_not_leak_handles(tmp_path: Path) -> None:
    repository = LocalFileRepository(tmp_path / "owner")
    repository.save(_project())
    assert repository.load("victim").id == "victim"
    before = _process_handle_count()
    for _ in range(100):
        assert repository.exists("victim") is True
        assert repository.load("victim").id == "victim"
    gc.collect()
    assert _process_handle_count() <= before

    root = repository._root
    outside = tmp_path / "outside-projects"
    outside.mkdir()
    moved = _swap_to_junction(root, outside)
    try:
        before_failure = _process_handle_count()
        for _ in range(100):
            with pytest.raises(ValidationError):
                repository.exists("victim")
        gc.collect()
        assert _process_handle_count() <= before_failure
    finally:
        _restore_swap(root, moved)


def test_unc_root_is_rejected_without_path_fallback() -> None:
    with pytest.raises(ValidationError):
        LocalFileRepository(Path(r"\\server\share\owner"))


def _attack_with_root_swaps(
    root: Path,
    moved: Path,
    outside: Path,
    stop: threading.Event,
    started: threading.Event,
    swaps: list[None],
    failures: list[BaseException],
) -> None:
    while not stop.is_set():
        try:
            if os.path.lexists(root) and (
                os.lstat(root).st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT
            ):
                _remove_junction(root)
            elif moved.exists() and not root.exists():
                moved.rename(root)
            else:
                root.rename(moved)
                _create_junction(root, outside)
                swaps.append(None)
                started.set()
        except OSError:
            time.sleep(0)
        except BaseException as error:  # pragma: no cover - defensive thread capture
            failures.append(error)


def test_concurrent_root_swaps_never_reveal_outside_victim(tmp_path: Path) -> None:
    repository = LocalFileRepository(tmp_path / "owner")
    outside = tmp_path / "outside-projects"
    payload = _prepare_outside_victim(repository, outside)
    root = repository._root
    moved = root.with_name("projects-concurrent-original")
    stop = threading.Event()
    started = threading.Event()
    swaps: list[None] = []
    failures: list[BaseException] = []
    worker = threading.Thread(
        target=_attack_with_root_swaps,
        args=(root, moved, outside, stop, started, swaps, failures),
        daemon=True,
    )
    worker.start()
    try:
        assert started.wait(timeout=5) is True
        for _ in range(200):
            try:
                assert repository.exists("victim") is False
            except ValidationError:
                pass
    finally:
        stop.set()
        worker.join(timeout=10)
        _remove_junction(root)
        if moved.exists() and not root.exists():
            moved.rename(root)
    assert not failures
    assert len(swaps) >= 2
    assert (outside / "victim.json").read_bytes() == payload


def _process_handle_count() -> int:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_current_process = kernel32.GetCurrentProcess
    get_current_process.restype = ctypes.c_void_p
    get_process_handle_count = kernel32.GetProcessHandleCount
    get_process_handle_count.argtypes = (ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32))
    get_process_handle_count.restype = ctypes.c_bool
    count = ctypes.c_uint32()
    if not get_process_handle_count(get_current_process(), ctypes.byref(count)):
        raise OSError(ctypes.get_last_error(), "GetProcessHandleCount failed")
    return int(count.value)
