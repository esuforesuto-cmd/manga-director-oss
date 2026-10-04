"""Private same-page execution fencing for durable Windows composition."""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import threading
from typing import Protocol

_WAIT_OBJECT_0 = 0
_WAIT_ABANDONED = 0x80
_WAIT_TIMEOUT = 0x102
_DEFAULT_TIMEOUT_MS = 1_000


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
        try:
            if self._owned:
                kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
                kernel32.ReleaseMutex(ctypes.c_void_p(handle))
        finally:
            if self._owned:
                self._release_process_ownership()
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.CloseHandle(ctypes.c_void_p(handle))
            self._owned = False

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


def _mutex_identity(project_id: str, page_id: str) -> str:
    """Return a stable local-only mutex identity without exposing input values."""

    if not _logical_identifier(project_id) or not _logical_identifier(page_id):
        raise ValueError("page execution fence requires logical project and page identifiers")
    canonical = json.dumps(
        {"page_id": page_id, "project_id": project_id},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"Local\\MangaDirectorPageExecution-{hashlib.sha256(canonical.encode()).hexdigest()}"


def _logical_identifier(value: str) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and value == value.strip()
        and not value.startswith(("/", "\\"))
        and "://" not in value
        and "@" not in value
    )
