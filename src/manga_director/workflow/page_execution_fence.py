"""Private same-page execution fencing for durable local composition."""

from __future__ import annotations

import ctypes
import errno
import hashlib
import importlib
import json
import os
import stat
import tempfile
import threading
from pathlib import Path
from typing import Any, Protocol

_WAIT_OBJECT_0 = 0
_WAIT_ABANDONED = 0x80
_WAIT_TIMEOUT = 0x102
_DEFAULT_TIMEOUT_MS = 1_000
_POSIX_LOCK_DIRECTORY_PREFIX = "manga-director-page-execution-fences"


class PageExecutionFenceError(RuntimeError):
    """Redacted failure to acquire a durable page execution fence."""


class PageExecutionFencePort(Protocol):
    """Private exclusive fence for one exact project/page decision."""

    def acquire(self) -> None: ...

    def release(self) -> None: ...


class WindowsPageExecutionFence(PageExecutionFencePort):
    """Bounded Local mutex with a hash-derived, non-caller-controlled identity."""

    _process_guard = threading.Lock()
    _process_owned: set[str] = set()

    def __init__(self, project_id: str, page_id: str, *, timeout_ms: int = _DEFAULT_TIMEOUT_MS) -> None:
        if timeout_ms < 1:
            raise ValueError("page execution fence timeout must be positive")
        self._identity = _mutex_identity(project_id, page_id)
        self._timeout_ms = timeout_ms
        self._handle: int | None = None
        self._owned = False

    def acquire(self) -> None:
        """Acquire once or fail closed without busy waiting."""

        if self._owned:
            return
        if os.name != "nt":
            raise PageExecutionFenceError("page_execution_fence_unavailable")
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        create_mutex = kernel32.CreateMutexW
        create_mutex.argtypes = (ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p)
        create_mutex.restype = ctypes.c_void_p
        handle = create_mutex(None, False, self._identity)
        if not handle:
            raise PageExecutionFenceError("page_execution_fence_unavailable")
        wait_for_single_object = kernel32.WaitForSingleObject
        wait_for_single_object.argtypes = (ctypes.c_void_p, ctypes.c_uint32)
        wait_for_single_object.restype = ctypes.c_uint32
        result = wait_for_single_object(handle, self._timeout_ms)
        if result == _WAIT_OBJECT_0:
            if not self._claim_process_ownership():
                # Windows mutexes are recursive for the owning thread.  Durable
                # executions must nevertheless remain non-reentrant per page.
                kernel32.ReleaseMutex(ctypes.c_void_p(handle))
                kernel32.CloseHandle(ctypes.c_void_p(handle))
                raise PageExecutionFenceError("page_execution_fence_contended")
            self._handle = int(handle)
            self._owned = True
            return
        if result == _WAIT_ABANDONED:
            # Windows grants ownership for WAIT_ABANDONED.  This contract treats
            # it as invalid, relinquishes it, and requires a later clean attempt.
            kernel32.ReleaseMutex(ctypes.c_void_p(handle))
        kernel32.CloseHandle(ctypes.c_void_p(handle))
        if result == _WAIT_TIMEOUT:
            raise PageExecutionFenceError("page_execution_fence_contended")
        raise PageExecutionFenceError("page_execution_fence_unavailable")

    def release(self) -> None:
        """Release only acquired ownership; repeated release is a no-op."""

        handle = self._handle
        self._handle = None
        if handle is None:
            return
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        released = not self._owned
        try:
            if self._owned:
                # Keep the process claim until the OS mutex is released, while
                # preventing a newly awakened thread from observing the stale
                # claim between those two operations.
                with self._process_guard:
                    released = bool(kernel32.ReleaseMutex(ctypes.c_void_p(handle)))
                    if released:
                        self._process_owned.discard(self._identity)
        finally:
            try:
                kernel32.CloseHandle(ctypes.c_void_p(handle))
            finally:
                self._owned = False
        if not released:
            raise PageExecutionFenceError("page_execution_fence_unavailable")

    def _r26_is_held_for(self, project_id: str, page_id: str) -> bool:
        """Report only this fence's live ownership for the private R26 inlet."""

        return self._owned and self._identity == _mutex_identity(project_id, page_id)

    def __enter__(self) -> WindowsPageExecutionFence:
        self.acquire()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.release()

    def _claim_process_ownership(self) -> bool:
        with self._process_guard:
            if self._identity in self._process_owned:
                return False
            self._process_owned.add(self._identity)
            return True

    def _release_process_ownership(self) -> None:
        with self._process_guard:
            self._process_owned.discard(self._identity)


class _PosixPageExecutionFence(PageExecutionFencePort):
    """One non-blocking advisory lock over a verified private lock artifact."""

    _process_guard = threading.Lock()
    _process_owned: set[str] = set()

    def __init__(
        self,
        project_id: str,
        page_id: str,
        *,
        timeout_ms: int = _DEFAULT_TIMEOUT_MS,
        lock_root: Path | None = None,
    ) -> None:
        if timeout_ms < 1:
            raise ValueError("page execution fence timeout must be positive")
        self._identity = _page_identity_digest(project_id, page_id)
        self._lock_root = lock_root
        self._descriptor: int | None = None
        self._fcntl: Any | None = None
        self._owned = False

    def acquire(self) -> None:
        """Acquire once without retrying, waiting, sleeping, or polling."""

        if os.name != "posix":
            raise PageExecutionFenceError("page_execution_fence_unavailable")
        if self._owned or not self._claim_process_ownership():
            raise PageExecutionFenceError("page_execution_fence_contended")
        root_descriptor: int | None = None
        lock_descriptor: int | None = None
        try:
            fcntl = importlib.import_module("fcntl")
            root = self._lock_root or _posix_page_fence_root()
            root_descriptor = _open_verified_posix_lock_root(root)
            lock_descriptor = _open_verified_posix_lock_artifact(
                root_descriptor, f"{self._identity}.lock"
            )
            try:
                fcntl.flock(lock_descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as error:
                if error.errno in {errno.EACCES, errno.EAGAIN}:
                    raise PageExecutionFenceError(
                        "page_execution_fence_contended"
                    ) from None
                raise
            if not _posix_lock_artifact_matches(
                root_descriptor, f"{self._identity}.lock", lock_descriptor
            ) or not _posix_lock_root_matches(root, root_descriptor):
                raise PageExecutionFenceError("page_execution_fence_unavailable")
            self._descriptor = lock_descriptor
            self._fcntl = fcntl
            self._owned = True
            lock_descriptor = None
        except PageExecutionFenceError:
            raise
        except (ImportError, OSError, TypeError, ValueError):
            raise PageExecutionFenceError("page_execution_fence_unavailable") from None
        finally:
            if lock_descriptor is not None:
                os.close(lock_descriptor)
            if root_descriptor is not None:
                os.close(root_descriptor)
            if not self._owned:
                self._release_process_ownership()

    def release(self) -> None:
        """Release ownership and the descriptor even when unlock reports failure."""

        descriptor = self._descriptor
        fcntl = self._fcntl
        self._descriptor = None
        self._fcntl = None
        if descriptor is None:
            return
        unlock_failed = False
        close_failed = False
        try:
            if self._owned and fcntl is not None:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
        except OSError:
            unlock_failed = True
        finally:
            try:
                os.close(descriptor)
            except OSError:
                close_failed = True
            finally:
                if self._owned:
                    self._release_process_ownership()
                self._owned = False
        if unlock_failed or close_failed:
            raise PageExecutionFenceError("page_execution_fence_unavailable")

    def _r26_is_held_for(self, project_id: str, page_id: str) -> bool:
        return self._owned and self._identity == _page_identity_digest(
            project_id, page_id
        )

    def _claim_process_ownership(self) -> bool:
        with self._process_guard:
            if self._identity in self._process_owned:
                return False
            self._process_owned.add(self._identity)
            return True

    def _release_process_ownership(self) -> None:
        with self._process_guard:
            self._process_owned.discard(self._identity)

    def __enter__(self) -> _PosixPageExecutionFence:
        self.acquire()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.release()


def local_page_execution_fence(
    project_id: str,
    page_id: str,
    *,
    timeout_ms: int = _DEFAULT_TIMEOUT_MS,
) -> PageExecutionFencePort:
    """Select the canonical local Page fence for the current operating system."""

    if os.name == "nt":
        return WindowsPageExecutionFence(
            project_id, page_id, timeout_ms=timeout_ms
        )
    return _PosixPageExecutionFence(
        project_id, page_id, timeout_ms=timeout_ms
    )


def _mutex_identity(project_id: str, page_id: str) -> str:
    """Return a stable local-only mutex identity without exposing input values."""

    return f"Local\\MangaDirectorPageExecution-{_page_identity_digest(project_id, page_id)}"


def _page_identity_digest(project_id: str, page_id: str) -> str:
    if not _logical_identifier(project_id) or not _logical_identifier(page_id):
        raise ValueError("page execution fence requires logical project and page identifiers")
    canonical = json.dumps(
        {"page_id": page_id, "project_id": project_id},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _posix_page_fence_root() -> Path:
    get_effective_user_id = getattr(os, "geteuid", None)
    if not callable(get_effective_user_id):
        raise PageExecutionFenceError("page_execution_fence_unavailable")
    effective_user_id = int(get_effective_user_id())
    return Path(tempfile.gettempdir()) / (
        f"{_POSIX_LOCK_DIRECTORY_PREFIX}-{effective_user_id}"
    )


def _open_verified_posix_lock_root(root: Path) -> int:
    no_follow = getattr(os, "O_NOFOLLOW", None)
    directory = getattr(os, "O_DIRECTORY", None)
    get_effective_user_id = getattr(os, "geteuid", None)
    if (
        not root.is_absolute()
        or not isinstance(no_follow, int)
        or not isinstance(directory, int)
        or not callable(get_effective_user_id)
    ):
        raise PageExecutionFenceError("page_execution_fence_unavailable")
    try:
        os.mkdir(root, mode=0o700)
    except FileExistsError:
        pass
    descriptor = os.open(
        root,
        os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | no_follow | directory,
    )
    try:
        if not _posix_lock_root_matches(root, descriptor):
            raise PageExecutionFenceError("page_execution_fence_unavailable")
        return descriptor
    except Exception:
        os.close(descriptor)
        raise


def _posix_lock_root_matches(root: Path, descriptor: int) -> bool:
    get_effective_user_id = getattr(os, "geteuid", None)
    if not callable(get_effective_user_id):
        return False
    try:
        descriptor_status = os.fstat(descriptor)
        path_status = root.lstat()
    except OSError:
        return False
    return bool(
        stat.S_ISDIR(descriptor_status.st_mode)
        and not stat.S_ISLNK(path_status.st_mode)
        and stat.S_ISDIR(path_status.st_mode)
        and _same_posix_identity(descriptor_status, path_status)
        and descriptor_status.st_uid == int(get_effective_user_id())
        and stat.S_IMODE(descriptor_status.st_mode) & 0o077 == 0
    )


def _open_verified_posix_lock_artifact(
    root_descriptor: int, lock_name: str
) -> int:
    no_follow = getattr(os, "O_NOFOLLOW", None)
    if not isinstance(no_follow, int):
        raise PageExecutionFenceError("page_execution_fence_unavailable")
    descriptor = os.open(
        lock_name,
        os.O_RDWR | os.O_CREAT | getattr(os, "O_CLOEXEC", 0) | no_follow,
        0o600,
        dir_fd=root_descriptor,
    )
    if not _posix_lock_artifact_matches(
        root_descriptor, lock_name, descriptor
    ):
        os.close(descriptor)
        raise PageExecutionFenceError("page_execution_fence_unavailable")
    return descriptor


def _posix_lock_artifact_matches(
    root_descriptor: int, lock_name: str, descriptor: int
) -> bool:
    get_effective_user_id = getattr(os, "geteuid", None)
    if not callable(get_effective_user_id):
        return False
    try:
        descriptor_status = os.fstat(descriptor)
        path_status = os.stat(
            lock_name, dir_fd=root_descriptor, follow_symlinks=False
        )
    except OSError:
        return False
    return bool(
        stat.S_ISREG(descriptor_status.st_mode)
        and not stat.S_ISLNK(path_status.st_mode)
        and stat.S_ISREG(path_status.st_mode)
        and _same_posix_identity(descriptor_status, path_status)
        and descriptor_status.st_uid == int(get_effective_user_id())
        and descriptor_status.st_nlink == 1
        and descriptor_status.st_size == 0
        and stat.S_IMODE(descriptor_status.st_mode) & 0o077 == 0
    )


def _same_posix_identity(left: os.stat_result, right: os.stat_result) -> bool:
    return bool(
        left.st_dev == right.st_dev
        and left.st_ino == right.st_ino
        and left.st_mode == right.st_mode
        and left.st_uid == right.st_uid
        and left.st_nlink == right.st_nlink
        and left.st_size == right.st_size
    )


def _logical_identifier(value: str) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and value == value.strip()
        and not value.startswith(("/", "\\"))
        and "://" not in value
        and "@" not in value
    )
