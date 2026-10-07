"""Private LocalFileRepository revision/CAS infrastructure.

This module deliberately owns only repository-local persistence integrity.  It
does not know about workflow transitions, agents, assets, or events.
"""

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
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Protocol

from manga_director.domain.exceptions import RepositoryError
from manga_director.domain.project import Project
from manga_director.repositories.local_file_aggregate_envelope import (
    _build_r27_aggregate,
    _decode_r27_aggregate,
    _physical_fingerprint,
)

_SCHEMA_VERSION = 1
_WAIT_OBJECT_0 = 0
_WAIT_ABANDONED = 0x80
_WAIT_TIMEOUT = 0x102
_R27_PREPARED_KEYS = frozenset({"expected", "proposed", "r27_pending_lineage", "r27_phase", "schema_version"})
_R27_COMMITTED_KEYS = frozenset({"fingerprint", "project_id", "r27_pending_lineage", "r27_phase", "revision", "schema_version"})
_R27_LINEAGE_KEYS = frozenset({"schema", "version", "application_binding_identity", "attempt_id", "project_id", "page_id", "target_page_reference", "source_state", "target_state", "expected_revision", "expected_aggregate_fingerprint", "resulting_revision", "pending_lineage_identity", "pending_lineage_digest"})
_R29_ACTIVATION_KIND = "manga_director.r29.r01.activation-state"
_R29_ACTIVATION_PREPARED_KEYS = frozenset({"activation_binding_identity", "activation_page_id", "expected_aggregate_fingerprint", "expected_revision", "marker_kind", "project_id", "schema_version", "state"})
_R29_ACTIVATION_COMMITTED_KEYS = _R29_ACTIVATION_PREPARED_KEYS | frozenset({"committed_aggregate_fingerprint", "committed_revision", "source_lineage_identity"})


class LocalFileDurabilityError(RepositoryError):
    """Raised for redacted local durability failures."""


class StaleRevisionError(LocalFileDurabilityError):
    """Raised when an aggregate changed since a snapshot was loaded."""


@dataclass(frozen=True)
class RevisionedProjectSnapshot:
    """Private caller-owned view of one authoritative aggregate revision."""

    project: Project
    revision: int
    fingerprint: str


@dataclass(frozen=True)
class ConditionalCommitResult:
    """Private, redacted result of an authoritative conditional commit."""

    revision: int
    derived_warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class _RevisionRecord:
    project_id: str
    revision: int
    fingerprint: str

    def as_dict(self) -> dict[str, object]:
        return {
            "fingerprint": self.fingerprint,
            "project_id": self.project_id,
            "revision": self.revision,
            "schema_version": _SCHEMA_VERSION,
        }


@dataclass(frozen=True)
class _PreparedRecord:
    expected: _RevisionRecord
    proposed: _RevisionRecord

    def as_dict(self) -> dict[str, object]:
        return {
            "expected": self.expected.as_dict(),
            "proposed": self.proposed.as_dict(),
            "schema_version": _SCHEMA_VERSION,
        }


@dataclass(frozen=True, slots=True)
class _R27RevisionPublicationRequest:
    """Repository-paired private facts for one frozen R27 publication."""

    repository_pair: object
    application_binding_identity: str
    attempt_id: str
    project_id: str
    page_id: str
    target_page_reference: str
    source_state: str
    target_state: str
    expected_revision: int
    expected_aggregate_fingerprint: str


@dataclass(frozen=True, slots=True)
class _R27PreparedRecord:
    expected: _RevisionRecord
    proposed: _RevisionRecord
    lineage: dict[str, object]


@dataclass(frozen=True, slots=True)
class _R27CommittedRecord:
    record: _RevisionRecord
    lineage: dict[str, object]


@dataclass(frozen=True, slots=True)
class _R29ActivationState:
    """Private, closed R29 persistence-format selection evidence only."""

    activation_binding_identity: str
    activation_page_id: str
    expected_aggregate_fingerprint: str
    expected_revision: int
    project_id: str
    state: str
    committed_aggregate_fingerprint: str | None = None
    committed_revision: int | None = None
    source_lineage_identity: str | None = None

    def as_dict(self) -> dict[str, object]:
        value: dict[str, object] = {
            "activation_binding_identity": self.activation_binding_identity,
            "activation_page_id": self.activation_page_id,
            "expected_aggregate_fingerprint": self.expected_aggregate_fingerprint,
            "expected_revision": self.expected_revision,
            "marker_kind": _R29_ACTIVATION_KIND,
            "project_id": self.project_id,
            "schema_version": 1,
            "state": self.state,
        }
        if self.state == "R27_COMMITTED":
            assert self.committed_aggregate_fingerprint is not None
            assert self.committed_revision is not None
            assert self.source_lineage_identity is not None
            value.update(
                {
                    "committed_aggregate_fingerprint": self.committed_aggregate_fingerprint,
                    "committed_revision": self.committed_revision,
                    "source_lineage_identity": self.source_lineage_identity,
                }
            )
        return value


@dataclass(frozen=True, slots=True)
class _R29PreReconciliationSnapshot:
    """Read-only R29 restart observations captured under one project fence."""

    aggregate_payload: bytes
    aggregate_state: str
    activation: _R29ActivationState | None
    activation_state: str
    committed: _RevisionRecord | _R27CommittedRecord | None
    prepared: _PreparedRecord | _R27PreparedRecord | None
    metadata_state: str
    project_id: str
    aggregate_f0: str | None = None
    aggregate_f1: str | None = None
    binding_state: str = "EXACT"
    expected_f0_matches: bool | None = None
    proposed_f0_matches: bool | None = None
    lineage_identity: str | None = None
    activation_project_matches: bool | None = None
    revision_project_matches: bool | None = None


class _RawObject(list[tuple[str, object]]):
    """Duplicate-preserving private JSON object representation."""


@dataclass(frozen=True, slots=True)
class _RawNumber:
    text: str


class _ProjectCommitFence(Protocol):
    """Private context-managed fence for one exact LocalFile project binding."""

    def __enter__(self) -> _ProjectCommitFence: ...

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None: ...

    def release(self) -> None: ...


class WindowsProjectCommitFence:
    """A bounded, same-session project commit fence backed by a Local mutex."""

    def __init__(self, identity: str, *, timeout_ms: int = 1_000) -> None:
        self._identity = identity
        self._timeout_ms = timeout_ms
        self._handle: int | None = None
        self._acquired = False

    def __enter__(self) -> WindowsProjectCommitFence:
        if os.name != "nt":
            raise LocalFileDurabilityError("project_commit_fence_unavailable")
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        create_mutex = kernel32.CreateMutexW
        create_mutex.argtypes = (ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p)
        create_mutex.restype = ctypes.c_void_p
        handle = create_mutex(None, False, self._identity)
        if not handle:
            raise LocalFileDurabilityError("project_commit_fence_unavailable")
        wait_for_single_object = kernel32.WaitForSingleObject
        wait_for_single_object.argtypes = (ctypes.c_void_p, ctypes.c_uint32)
        wait_for_single_object.restype = ctypes.c_uint32
        result = wait_for_single_object(handle, self._timeout_ms)
        if result not in {_WAIT_OBJECT_0, _WAIT_ABANDONED}:
            kernel32.CloseHandle(handle)
            if result == _WAIT_TIMEOUT:
                raise LocalFileDurabilityError("project_commit_fence_contended")
            raise LocalFileDurabilityError("project_commit_fence_unavailable")
        self._handle = int(handle)
        # WAIT_ABANDONED grants ownership; serialization continues only through
        # the later fingerprint checks and prepared-record reconciliation.
        self._acquired = True
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.release()

    def release(self) -> None:
        """Release once; repeated release is intentionally a no-op."""

        handle = self._handle
        self._handle = None
        if handle is None:
            return
        try:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            if self._acquired:
                kernel32.ReleaseMutex(ctypes.c_void_p(handle))
        finally:
            kernel32.CloseHandle(ctypes.c_void_p(handle))
            self._acquired = False


_project_fence_process_guard = threading.Lock()
_project_fence_process_owned: set[tuple[int, str]] = set()


def _claim_project_fence_process_ownership(identity: str) -> bool:
    key = (os.getpid(), identity)
    with _project_fence_process_guard:
        if key in _project_fence_process_owned:
            return False
        _project_fence_process_owned.add(key)
        return True


def _release_project_fence_process_ownership(identity: str, owner_pid: int) -> None:
    with _project_fence_process_guard:
        _project_fence_process_owned.discard((owner_pid, identity))


def _effective_user_id() -> int | None:
    get_effective_user_id = getattr(os, "geteuid", None)
    return int(get_effective_user_id()) if callable(get_effective_user_id) else None


class _PosixProjectCommitFence:
    """Bounded POSIX kernel lock over one private, zero-payload artifact."""

    def __init__(
        self,
        identity: str,
        durability_root: Path,
        *,
        timeout_ms: int = 1_000,
    ) -> None:
        self._identity = identity
        self._durability_root = durability_root
        self._timeout_ms = timeout_ms
        self._descriptor: int | None = None
        self._owner_pid: int | None = None
        self._fcntl: object | None = None

    def __enter__(self) -> _PosixProjectCommitFence:
        if os.name != "posix":
            raise LocalFileDurabilityError("project_commit_fence_unavailable")
        owner_pid = os.getpid()
        if not _claim_project_fence_process_ownership(self._identity):
            raise LocalFileDurabilityError("project_commit_fence_contended")
        descriptor: int | None = None
        try:
            fcntl = importlib.import_module("fcntl")
            lock_path = self._prepare_lock_path()
            descriptor = self._open_verified_artifact(lock_path)
            deadline = time.monotonic() + max(self._timeout_ms, 0) / 1_000
            while True:
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError as error:
                    if error.errno not in {errno.EACCES, errno.EAGAIN}:
                        raise LocalFileDurabilityError(
                            "project_commit_fence_unavailable"
                        ) from error
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise LocalFileDurabilityError(
                            "project_commit_fence_contended"
                        ) from None
                    time.sleep(min(0.01, remaining))
            self._verify_artifact(descriptor, lock_path)
        except LocalFileDurabilityError:
            if descriptor is not None:
                os.close(descriptor)
            _release_project_fence_process_ownership(self._identity, owner_pid)
            raise
        except (ImportError, OSError) as error:
            if descriptor is not None:
                os.close(descriptor)
            _release_project_fence_process_ownership(self._identity, owner_pid)
            raise LocalFileDurabilityError("project_commit_fence_unavailable") from error
        self._descriptor = descriptor
        self._owner_pid = owner_pid
        self._fcntl = fcntl
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.release()

    def release(self) -> None:
        """Release only this owner's lock; repeated release is a no-op."""

        descriptor = self._descriptor
        owner_pid = self._owner_pid
        fcntl = self._fcntl
        self._descriptor = None
        self._owner_pid = None
        self._fcntl = None
        if descriptor is None or owner_pid is None:
            return
        try:
            if owner_pid == os.getpid() and fcntl is not None:
                fcntl.flock(descriptor, fcntl.LOCK_UN)  # type: ignore[attr-defined]
        except OSError:
            pass
        finally:
            os.close(descriptor)
            if owner_pid == os.getpid():
                _release_project_fence_process_ownership(self._identity, owner_pid)

    def _prepare_lock_path(self) -> Path:
        try:
            self._durability_root.mkdir(parents=True, exist_ok=True)
            status = self._durability_root.lstat()
        except OSError as error:
            raise LocalFileDurabilityError("project_commit_fence_unavailable") from error
        owner_id = _effective_user_id()
        if (
            not stat.S_ISDIR(status.st_mode)
            or stat.S_ISLNK(status.st_mode)
            or owner_id is None
            or status.st_uid != owner_id
            or stat.S_IMODE(status.st_mode) & 0o022
        ):
            raise LocalFileDurabilityError("project_commit_fence_unavailable")
        return self._durability_root / f"{self._identity}.project-commit.lock"

    def _open_verified_artifact(self, lock_path: Path) -> int:
        flags = os.O_RDWR | os.O_CREAT
        flags |= getattr(os, "O_CLOEXEC", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        flags |= getattr(os, "O_NONBLOCK", 0)
        descriptor = os.open(lock_path, flags, 0o600)
        try:
            self._verify_artifact(descriptor, lock_path)
        except BaseException:
            os.close(descriptor)
            raise
        return descriptor

    @staticmethod
    def _verify_artifact(descriptor: int, lock_path: Path) -> None:
        descriptor_status = os.fstat(descriptor)
        path_status = lock_path.lstat()
        owner_id = _effective_user_id()
        if (
            not stat.S_ISREG(descriptor_status.st_mode)
            or stat.S_ISLNK(path_status.st_mode)
            or not stat.S_ISREG(path_status.st_mode)
            or descriptor_status.st_dev != path_status.st_dev
            or descriptor_status.st_ino != path_status.st_ino
            or owner_id is None
            or descriptor_status.st_uid != owner_id
            or stat.S_IMODE(descriptor_status.st_mode) & 0o077
            or descriptor_status.st_nlink != 1
            or descriptor_status.st_size != 0
        ):
            raise LocalFileDurabilityError("project_commit_fence_unavailable")


def _project_commit_identity(root: Path, project_id: str) -> str:
    binding = f"{root.resolve()}\x00{project_id}".encode()
    return hashlib.sha256(binding).hexdigest()


def _select_project_commit_fence(
    root: Path, project_id: str, *, timeout_ms: int = 1_000
) -> _ProjectCommitFence:
    identity = _project_commit_identity(root, project_id)
    if os.name == "nt":
        return WindowsProjectCommitFence(
            f"Local\\MangaDirectorProjectCommit-{identity}", timeout_ms=timeout_ms
        )
    if os.name == "posix":
        durability_root = root.resolve() / "_durability"
        return _PosixProjectCommitFence(identity, durability_root, timeout_ms=timeout_ms)
    raise LocalFileDurabilityError("project_commit_fence_unavailable")


class LocalFileRevisionStore:
    """Own revision records, staged aggregate replacement, and reconciliation."""

    def __init__(
        self,
        root: Path,
        *,
        fence_factory: Callable[[str], _ProjectCommitFence] | None = None,
    ) -> None:
        self._root = root
        self._fence_factory = fence_factory
        self._r27_fault_injector: Callable[[str], None] | None = None

    def load_snapshot(
        self,
        project_id: str,
        aggregate_path: Path,
        deserialize: Callable[[bytes], Project],
        *,
        requires_existing_revision: Callable[[bytes], bool] | None = None,
        validate_revision_record: Callable[[bytes, str, int, str], None] | None = None,
    ) -> RevisionedProjectSnapshot:
        with self._project_fence(project_id):
            payload = self._read_aggregate(aggregate_path)
            if self._r29_restart_applies(project_id, payload):
                return self._load_r29_aware_snapshot(
                    project_id,
                    aggregate_path,
                    deserialize,
                    requires_existing_revision=requires_existing_revision,
                    validate_revision_record=validate_revision_record,
                )
            requires_existing = (
                requires_existing_revision(payload) if requires_existing_revision is not None else False
            )
            record = self._reconcile_or_initialize(
                project_id,
                payload,
                allow_initialization=not requires_existing,
                validate_record=validate_revision_record if requires_existing else None,
            )
            return RevisionedProjectSnapshot(
                project=deserialize(payload),
                revision=record.revision,
                fingerprint=record.fingerprint,
            )

    def _capture_r29_pre_reconciliation_snapshot(
        self, project_id: str, aggregate_path: Path
    ) -> _R29PreReconciliationSnapshot:
        """Capture R29 restart facts without invoking any reconciliation path."""

        with self._project_fence(project_id):
            return self._capture_r29_pre_reconciliation_snapshot_locked(project_id, aggregate_path)

    def _capture_r29_pre_reconciliation_snapshot_locked(
        self, project_id: str, aggregate_path: Path
    ) -> _R29PreReconciliationSnapshot:
        """Read one complete R29 tuple while the caller owns the project fence."""

        payload = self._read_aggregate(aggregate_path)
        envelope = None
        try:
            envelope = _decode_r27_aggregate(payload)
            aggregate_state = "R27" if envelope is not None else "RAW"
        except ValueError:
            aggregate_state = "CORRUPT"
        try:
            activation = self._read_r29_activation(project_id)
            activation_state = "ABSENT" if activation is None else activation.state
        except LocalFileDurabilityError:
            activation = None
            activation_state = "CORRUPT"
        try:
            prepared = self._read_prepared_for(project_id)
            committed = self._read_committed(project_id)
            metadata_state = _r29_metadata_state(prepared, committed)
        except LocalFileDurabilityError:
            prepared = None
            committed = None
            metadata_state = "CORRUPT"
        binding = _r29_allocate_binding(
            project_id,
            payload,
            aggregate_state,
            envelope,
            activation,
            prepared,
            committed,
            metadata_state,
        )
        return _R29PreReconciliationSnapshot(
            aggregate_payload=payload,
            aggregate_state=aggregate_state,
            activation=activation,
            activation_state=activation_state,
            committed=committed,
            prepared=prepared,
            metadata_state=metadata_state,
            project_id=project_id,
            aggregate_f0=binding.aggregate_f0,
            aggregate_f1=binding.aggregate_f1,
            binding_state=binding.state,
            expected_f0_matches=binding.expected_f0_matches,
            proposed_f0_matches=binding.proposed_f0_matches,
            lineage_identity=binding.lineage_identity,
            activation_project_matches=binding.activation_project_matches,
            revision_project_matches=binding.revision_project_matches,
        )

    def _r29_restart_applies(self, project_id: str, payload: bytes) -> bool:
        """Select the private R29 inlet without changing pre-R29 framed tests."""

        if self._activation_path(project_id).exists():
            return True
        try:
            framed = _decode_r27_aggregate(payload) is not None
        except ValueError:
            return False
        if framed:
            return False
        try:
            return isinstance(self._read_prepared_for(project_id), _R27PreparedRecord)
        except LocalFileDurabilityError:
            # The established generic loader owns legacy malformed-sidecar
            # reporting until an R29 activation record exists.
            return False

    def _load_r29_aware_snapshot(
        self,
        project_id: str,
        aggregate_path: Path,
        deserialize: Callable[[bytes], Project],
        *,
        requires_existing_revision: Callable[[bytes], bool] | None,
        validate_revision_record: Callable[[bytes, str, int, str], None] | None,
    ) -> RevisionedProjectSnapshot:
        """Apply exactly one R29 classifier result before any recovery mutation."""

        snapshot = self._capture_r29_pre_reconciliation_snapshot_locked(project_id, aggregate_path)
        result = _classify_r29_pre_reconciliation(snapshot)
        if result == "FAIL_CLOSED":
            raise LocalFileDurabilityError("r29_restart_fail_closed")

        requires_existing = (
            requires_existing_revision(snapshot.aggregate_payload)
            if requires_existing_revision is not None
            else False
        )
        record = self._apply_r29_restart_result(
            snapshot,
            result,
            aggregate_path,
            allow_initialization=not requires_existing,
            validate_record=validate_revision_record if requires_existing else None,
        )
        reread = self._read_aggregate(aggregate_path)
        if _fingerprint(reread) != record.fingerprint:
            raise LocalFileDurabilityError("r29_restart_post_action_stale")
        return RevisionedProjectSnapshot(
            project=deserialize(reread),
            revision=record.revision,
            fingerprint=record.fingerprint,
        )

    def _apply_r29_restart_result(
        self,
        snapshot: _R29PreReconciliationSnapshot,
        result: str,
        aggregate_path: Path,
        *,
        allow_initialization: bool,
        validate_record: Callable[[bytes, str, int, str], None] | None,
    ) -> _RevisionRecord:
        """Perform only the recovery action selected by one immutable snapshot."""

        if result == "LEGACY":
            return self._reconcile_or_initialize(
                snapshot.project_id,
                snapshot.aggregate_payload,
                allow_initialization=allow_initialization,
                validate_record=validate_record,
            )
        activation = snapshot.activation
        if activation is None or activation.state != "ACTIVATION_PREPARED":
            if result == "R27":
                return self._reconcile_or_initialize(
                    snapshot.project_id,
                    snapshot.aggregate_payload,
                    allow_initialization=allow_initialization,
                    validate_record=validate_record,
                )
            raise LocalFileDurabilityError("r29_restart_action_invalid")
        current = self._read_aggregate(aggregate_path)
        if result == "ACTIVATION_RECOVERY" and snapshot.aggregate_state == "RAW":
            if _decode_r27_aggregate(current) is not None:
                raise LocalFileDurabilityError("r29_restart_post_action_stale")
            record = self._reconcile_or_initialize(
                snapshot.project_id,
                snapshot.aggregate_payload,
                allow_initialization=allow_initialization,
                validate_record=validate_record,
            )
            self._remove_r29_prepared_activation(snapshot.project_id)
            return record
        if result not in {"ACTIVATION_RECOVERY", "R27_RECONCILE"}:
            raise LocalFileDurabilityError("r29_restart_action_invalid")
        if isinstance(snapshot.prepared, _R27PreparedRecord):
            record = self._r29_finalize_selected_r27_prepared(
                snapshot, current, validate_record=validate_record
            )
        else:
            record = self._reconcile_or_initialize(
                snapshot.project_id,
                snapshot.aggregate_payload,
                allow_initialization=allow_initialization,
                validate_record=validate_record,
            )
        committed = self._read_committed(snapshot.project_id)
        if not isinstance(committed, _R27CommittedRecord):
            raise LocalFileDurabilityError("r29_restart_action_invalid")
        if _physical_fingerprint(current) != committed.record.fingerprint:
            raise LocalFileDurabilityError("r29_restart_post_action_stale")
        _validate_r27_aggregate(current, committed.record, committed.lineage)
        final = _R29ActivationState(
            activation_binding_identity=activation.activation_binding_identity,
            activation_page_id=activation.activation_page_id,
            expected_aggregate_fingerprint=activation.expected_aggregate_fingerprint,
            expected_revision=activation.expected_revision,
            project_id=snapshot.project_id,
            state="R27_COMMITTED",
            committed_aggregate_fingerprint=committed.record.fingerprint,
            committed_revision=committed.record.revision,
            source_lineage_identity=_r27_lineage_identity(committed.lineage),
        )
        self._commit_r29_activation(final)
        return record

    def _r29_finalize_selected_r27_prepared(
        self,
        snapshot: _R29PreReconciliationSnapshot,
        current: bytes,
        *,
        validate_record: Callable[[bytes, str, int, str], None] | None,
    ) -> _RevisionRecord:
        """Finish only the R28 v2 lineage selected by the immutable snapshot."""

        prepared = snapshot.prepared
        if not isinstance(prepared, _R27PreparedRecord):
            raise LocalFileDurabilityError("r29_restart_action_invalid")
        if _physical_fingerprint(current) != prepared.proposed.fingerprint:
            raise LocalFileDurabilityError("r29_restart_post_action_stale")
        _validate_prepared_commit_pair(snapshot.committed, prepared.expected, prepared.proposed, prepared.lineage)
        _validate_r27_aggregate(current, prepared.proposed, prepared.lineage)
        _validate_record(current, prepared.proposed, validate_record)
        existing = self._read_committed(snapshot.project_id)
        if existing is None or _committed_record(existing) == prepared.expected:
            self._write_committed(_R27CommittedRecord(record=prepared.proposed, lineage=prepared.lineage))
        elif not isinstance(existing, _R27CommittedRecord) or existing.record != prepared.proposed or existing.lineage != prepared.lineage:
            raise LocalFileDurabilityError("r29_restart_post_action_stale")
        self._remove_prepared(snapshot.project_id)
        return prepared.proposed

    def conditional_replace(
        self,
        snapshot: RevisionedProjectSnapshot,
        aggregate_path: Path,
        proposed_payload: bytes,
        verify: Callable[[bytes], bool],
    ) -> int:
        """Replace one aggregate only while its exact expected revision is current."""

        project_id = snapshot.project.id
        if project_id != self._project_id_from_path(project_id):
            raise LocalFileDurabilityError("invalid_revision_snapshot")
        with self._project_fence(project_id):
            current_payload = self._read_aggregate(aggregate_path)
            self._assert_r29_raw_replacement_allowed(project_id, current_payload)
            current = self._reconcile_or_initialize(project_id, current_payload)
            if current.revision != snapshot.revision or current.fingerprint != snapshot.fingerprint:
                raise StaleRevisionError("stale_authoritative_revision")

            proposed = _RevisionRecord(
                project_id=project_id,
                revision=current.revision + 1,
                fingerprint=_fingerprint(proposed_payload),
            )
            self._write_prepared(_PreparedRecord(expected=current, proposed=proposed))
            staged = self._stage(aggregate_path, proposed_payload)
            try:
                os.replace(staged, aggregate_path)
            except OSError as exc:
                _discard(staged)
                raise LocalFileDurabilityError("authoritative_replace_failed") from exc

            self._sync_file(aggregate_path)
            reread = self._read_aggregate(aggregate_path)
            if _fingerprint(reread) != proposed.fingerprint or not verify(reread):
                raise LocalFileDurabilityError("authoritative_reread_verification_failed")
            self._write_committed(proposed)
            self._remove_prepared(project_id)
            return proposed.revision

    def _replace_raw_legacy(
        self,
        project_id: str,
        aggregate_path: Path,
        proposed_payload: bytes,
    ) -> None:
        """Privately replace one legacy aggregate through the R29 format gate.

        ``LocalFileRepository.save`` is an established non-CAS entry point.
        It must nevertheless hold the RevisionStore fence from format
        classification through atomic replacement so an activation state cannot
        appear between a successful gate check and the raw write.
        """

        if project_id != self._project_id_from_path(project_id):
            raise LocalFileDurabilityError("invalid_revision_snapshot")
        with self._project_fence(project_id):
            try:
                current_payload = self._read_aggregate(aggregate_path)
            except LocalFileDurabilityError as exc:
                if str(exc) != "authoritative_aggregate_missing":
                    raise
                # A new legacy aggregate is permitted only while no activation
                # state exists.  The proposed bytes are repository-serialized
                # legacy content, never a caller-provided publication format.
                if self._read_r29_activation(project_id) is not None:
                    raise LocalFileDurabilityError("r29_raw_replacement_forbidden") from None
                current_payload = None
            if current_payload is not None:
                self._assert_r29_raw_replacement_allowed(project_id, current_payload)
                if current_payload == proposed_payload:
                    return

            staged = self._stage(aggregate_path, proposed_payload)
            try:
                os.replace(staged, aggregate_path)
            except OSError as exc:
                _discard(staged)
                raise LocalFileDurabilityError("authoritative_replace_failed") from exc
            self._sync_file(aggregate_path)
            if self._read_aggregate(aggregate_path) != proposed_payload:
                raise LocalFileDurabilityError("authoritative_reread_verification_failed")

    def _conditional_replace_r27(
        self,
        snapshot: RevisionedProjectSnapshot,
        aggregate_path: Path,
        project_payload: bytes,
        request: _R27RevisionPublicationRequest,
        verify: Callable[[bytes], bool],
    ) -> int:
        """Privately publish one frozen R27 aggregate under the existing CAS fence.

        This is intentionally not a replacement for ``conditional_replace``.
        Callers must arrive through the private composition handoff; the store
        still owns only local publication and revision metadata.
        """

        project_id = snapshot.project.id
        _validate_r27_request(request, snapshot, project_id)
        with self._project_fence(project_id):
            current_payload = self._read_aggregate(aggregate_path)
            current = self._reconcile_or_initialize(project_id, current_payload)
            if current.revision != snapshot.revision or current.fingerprint != snapshot.fingerprint:
                committed = self._read_committed(project_id)
                if (
                    isinstance(committed, _R27CommittedRecord)
                    and _r27_request_matches_lineage(request, snapshot, committed.lineage)
                    and committed.record.revision == snapshot.revision + 1
                    and _physical_fingerprint(current_payload) == committed.record.fingerprint
                ):
                    _validate_r27_aggregate(current_payload, committed.record, committed.lineage)
                    return committed.record.revision
                raise StaleRevisionError("stale_authoritative_revision")

            lineage = _r27_lineage(request, resulting_revision=current.revision + 1)
            witness_inputs = {
                "application_binding_identity": request.application_binding_identity,
                "expected_aggregate_fingerprint": request.expected_aggregate_fingerprint,
                "expected_revision": request.expected_revision,
                "pending_lineage_digest": lineage["pending_lineage_digest"],
                "pending_lineage_identity": lineage["pending_lineage_identity"],
                "protocol_version": 1,
                "resulting_revision": current.revision + 1,
                "schema": "manga_director.r27.same-cas-witness",
                "version": 1,
            }
            proposed_payload = _build_r27_aggregate(project_payload, witness_inputs)
            proposed = _RevisionRecord(
                project_id=project_id,
                revision=current.revision + 1,
                fingerprint=_physical_fingerprint(proposed_payload),
            )
            prepared = _R27PreparedRecord(expected=current, proposed=proposed, lineage=lineage)
            self._write_prepared(prepared)
            staged = self._stage_r27(aggregate_path, proposed_payload)
            self._r27_fault("before_aggregate_replace")
            try:
                os.replace(staged, aggregate_path)
            except OSError as exc:
                _discard(staged)
                raise LocalFileDurabilityError("authoritative_replace_failed") from exc

            self._r27_fault("immediately_after_aggregate_replace")
            self._sync_file(aggregate_path)
            self._r27_fault("after_aggregate_durability_sync")
            self._r27_fault("before_persisted_byte_reread")
            reread = self._read_aggregate(aggregate_path)
            if _physical_fingerprint(reread) != proposed.fingerprint or not verify(reread):
                raise LocalFileDurabilityError("authoritative_reread_verification_failed")
            _validate_r27_aggregate(reread, proposed, lineage)
            self._r27_fault("after_reread_verification")
            self._r27_fault("before_committed_metadata_write")
            self._write_committed(_R27CommittedRecord(record=proposed, lineage=lineage))
            self._r27_fault("before_prepared_cleanup")
            self._remove_prepared(project_id)
            self._r27_fault("after_prepared_cleanup")
            self._r27_fault("before_caller_acknowledgement")
            return proposed.revision

    def _activate_and_conditional_replace_r27(
        self,
        snapshot: RevisionedProjectSnapshot,
        aggregate_path: Path,
        project_payload: bytes,
        request: _R27RevisionPublicationRequest,
        verify: Callable[[bytes], bool],
    ) -> int:
        """Privately perform the first R27 publication for one raw project.

        This narrow wrapper owns only the R29 state around the frozen R28
        publication sequence.  It deliberately leaves the ordinary R28 method
        untouched for its existing unactivated test/replay contract.
        """

        project_id = snapshot.project.id
        _validate_r27_request(request, snapshot, project_id)
        prepared_activation = _R29ActivationState(
            activation_binding_identity=request.application_binding_identity,
            activation_page_id=request.page_id,
            expected_aggregate_fingerprint=snapshot.fingerprint,
            expected_revision=snapshot.revision,
            project_id=project_id,
            state="ACTIVATION_PREPARED",
        )
        with self._project_fence(project_id):
            current_payload = self._read_aggregate(aggregate_path)
            self._assert_r29_raw_replacement_allowed(project_id, current_payload)
            current = self._reconcile_or_initialize(project_id, current_payload)
            if current.revision != snapshot.revision or current.fingerprint != snapshot.fingerprint:
                raise StaleRevisionError("stale_authoritative_revision")
            self._prepare_r29_activation(prepared_activation)
            self._r27_fault("after_activation_prepared_durability_before_r28_prepared")

            lineage = _r27_lineage(request, resulting_revision=current.revision + 1)
            witness_inputs = {
                "application_binding_identity": request.application_binding_identity,
                "expected_aggregate_fingerprint": request.expected_aggregate_fingerprint,
                "expected_revision": request.expected_revision,
                "pending_lineage_digest": lineage["pending_lineage_digest"],
                "pending_lineage_identity": lineage["pending_lineage_identity"],
                "protocol_version": 1,
                "resulting_revision": current.revision + 1,
                "schema": "manga_director.r27.same-cas-witness",
                "version": 1,
            }
            proposed_payload = _build_r27_aggregate(project_payload, witness_inputs)
            proposed = _RevisionRecord(
                project_id=project_id,
                revision=current.revision + 1,
                fingerprint=_physical_fingerprint(proposed_payload),
            )
            prepared = _R27PreparedRecord(expected=current, proposed=proposed, lineage=lineage)
            self._write_prepared(prepared)
            staged = self._stage_r27(aggregate_path, proposed_payload)
            self._r27_fault("before_aggregate_replace")
            try:
                os.replace(staged, aggregate_path)
            except OSError as exc:
                _discard(staged)
                raise LocalFileDurabilityError("authoritative_replace_failed") from exc
            self._r27_fault("immediately_after_aggregate_replace")
            self._sync_file(aggregate_path)
            self._r27_fault("after_aggregate_durability_sync")
            self._r27_fault("before_persisted_byte_reread")
            reread = self._read_aggregate(aggregate_path)
            if _physical_fingerprint(reread) != proposed.fingerprint or not verify(reread):
                raise LocalFileDurabilityError("authoritative_reread_verification_failed")
            _validate_r27_aggregate(reread, proposed, lineage)
            self._r27_fault("after_reread_verification")
            self._write_committed(_R27CommittedRecord(record=proposed, lineage=lineage))
            self._r27_fault("before_prepared_cleanup")
            self._remove_prepared(project_id)
            self._r27_fault("after_prepared_cleanup")
            final_activation = _R29ActivationState(
                activation_binding_identity=prepared_activation.activation_binding_identity,
                activation_page_id=prepared_activation.activation_page_id,
                expected_aggregate_fingerprint=prepared_activation.expected_aggregate_fingerprint,
                expected_revision=prepared_activation.expected_revision,
                project_id=project_id,
                state="R27_COMMITTED",
                committed_aggregate_fingerprint=proposed.fingerprint,
                committed_revision=proposed.revision,
                source_lineage_identity=_r27_lineage_identity(lineage),
            )
            self._commit_r29_activation(final_activation)
            self._r27_fault("before_caller_acknowledgement")
            return proposed.revision

    def _reconcile_or_initialize(
        self,
        project_id: str,
        aggregate_payload: bytes,
        *,
        allow_initialization: bool = True,
        validate_record: Callable[[bytes, str, int, str], None] | None = None,
    ) -> _RevisionRecord:
        prepared = self._read_prepared_for(project_id)
        committed = self._read_committed(project_id)
        current_fingerprint = _fingerprint(aggregate_payload)
        if prepared is not None:
            return self._reconcile_prepared(
                project_id,
                aggregate_payload,
                current_fingerprint,
                prepared,
                committed,
                allow_initialization,
                validate_record,
            )

        if committed is None:
            if not allow_initialization:
                raise LocalFileDurabilityError("r27_revision_record_required")
            initialized = _RevisionRecord(project_id=project_id, revision=1, fingerprint=current_fingerprint)
            _validate_record(aggregate_payload, initialized, validate_record)
            self._write_committed(initialized)
            return initialized
        committed_record = _committed_record(committed)
        if committed_record.fingerprint != current_fingerprint:
            raise LocalFileDurabilityError("authoritative_fingerprint_mismatch")
        _validate_record(aggregate_payload, committed_record, validate_record)
        if isinstance(committed, _R27CommittedRecord):
            _validate_r27_aggregate(aggregate_payload, committed.record, committed.lineage)
        return committed_record

    def _reconcile_prepared(
        self,
        project_id: str,
        aggregate_payload: bytes,
        current_fingerprint: str,
        prepared: _PreparedRecord | _R27PreparedRecord,
        committed: _RevisionRecord | _R27CommittedRecord | None,
        allow_initialization: bool,
        validate_record: Callable[[bytes, str, int, str], None] | None,
    ) -> _RevisionRecord:
        expected, proposed, lineage = _prepared_parts(prepared)
        if expected.project_id != project_id or proposed.project_id != project_id:
            raise LocalFileDurabilityError("prepared_revision_binding_invalid")
        if current_fingerprint == proposed.fingerprint:
            return self._finalize_prepared(
                project_id, aggregate_payload, expected, proposed, lineage, committed, validate_record
            )
        if current_fingerprint == expected.fingerprint:
            return self._abort_unpublished_prepared(project_id, expected, lineage, committed)
        raise LocalFileDurabilityError("prepared_revision_ambiguous")

    def _finalize_prepared(
        self,
        project_id: str,
        aggregate_payload: bytes,
        expected: _RevisionRecord,
        proposed: _RevisionRecord,
        lineage: dict[str, object] | None,
        committed: _RevisionRecord | _R27CommittedRecord | None,
        validate_record: Callable[[bytes, str, int, str], None] | None,
    ) -> _RevisionRecord:
        _validate_prepared_commit_pair(committed, expected, proposed, lineage)
        _validate_record(aggregate_payload, proposed, validate_record)
        if lineage is not None:
            _validate_r27_aggregate(aggregate_payload, proposed, lineage)
            if committed is None:
                self._write_committed(_R27CommittedRecord(record=proposed, lineage=lineage))
        else:
            self._write_committed(proposed)
        self._remove_prepared(project_id)
        return proposed

    def _abort_unpublished_prepared(
        self,
        project_id: str,
        expected: _RevisionRecord,
        lineage: dict[str, object] | None,
        committed: _RevisionRecord | _R27CommittedRecord | None,
    ) -> _RevisionRecord:
        if lineage is not None:
            _validate_unpublished_r27_prepared_pair(committed, expected, lineage)
            self._remove_prepared(project_id)
            return expected
        raise LocalFileDurabilityError("prepared_revision_unresolved")

    def _durability_directory(self) -> Path:
        return self._root / "_durability"

    def _record_stem(self, project_id: str) -> str:
        return _project_commit_identity(self._root, project_id)

    def _committed_path(self, project_id: str) -> Path:
        return self._durability_directory() / f"{self._record_stem(project_id)}.revision.json"

    def _prepared_path(self, project_id: str) -> Path:
        return self._durability_directory() / f"{self._record_stem(project_id)}.prepared.json"

    def _activation_path(self, project_id: str) -> Path:
        return self._durability_directory() / f"{self._record_stem(project_id)}.r27-activation.json"

    def _fence_name(self, project_id: str) -> str:
        return f"Local\\MangaDirectorProjectCommit-{self._record_stem(project_id)}"

    def _project_fence(self, project_id: str) -> _ProjectCommitFence:
        if self._fence_factory is not None:
            return self._fence_factory(self._fence_name(project_id))
        return _select_project_commit_fence(self._root, project_id)

    def _read_committed(self, project_id: str) -> _RevisionRecord | _R27CommittedRecord | None:
        try:
            kind, data = _read_revision_metadata(self._committed_path(project_id))
        except FileNotFoundError:
            return None
        record: _RevisionRecord | _R27CommittedRecord
        if kind == "LEGACY_V1":
            record = _parse_revision_record(data)
        else:
            record = _parse_r27_committed_record(data)
        if _committed_record(record).project_id != project_id:
            raise LocalFileDurabilityError("revision_record_binding_invalid")
        return record

    def _read_prepared_for(self, project_id: str) -> _PreparedRecord | _R27PreparedRecord | None:
        try:
            kind, data = _read_revision_metadata(self._prepared_path(project_id))
        except FileNotFoundError:
            return None
        if kind == "LEGACY_V1":
            if not isinstance(data, dict) or data.get("schema_version") != _SCHEMA_VERSION:
                raise LocalFileDurabilityError("prepared_revision_schema_invalid")
            expected = _parse_revision_record(data.get("expected"))
            proposed = _parse_revision_record(data.get("proposed"))
            return _PreparedRecord(expected=expected, proposed=proposed)
        return _parse_r27_prepared_record(data)

    def _write_committed(self, record: _RevisionRecord | _R27CommittedRecord) -> None:
        if isinstance(record, _R27CommittedRecord):
            self._write_r27_metadata_atomic(
                self._committed_path(record.record.project_id),
                _r27_committed_dict(record),
                "before_committed_metadata_write",
                "during_committed_metadata_write",
                "after_committed_metadata_durability",
            )
            return
        _write_json_atomic(self._committed_path(record.project_id), record.as_dict())

    def _write_prepared(self, record: _PreparedRecord | _R27PreparedRecord) -> None:
        if isinstance(record, _R27PreparedRecord):
            self._write_r27_metadata_atomic(
                self._prepared_path(record.expected.project_id),
                _r27_prepared_dict(record),
                "before_prepared_metadata_write",
                "during_prepared_metadata_write",
                "after_prepared_metadata_durability",
            )
            return
        _write_json_atomic(self._prepared_path(record.expected.project_id), record.as_dict())

    def _remove_prepared(self, project_id: str) -> None:
        # The caller already owns the project commit fence.  A surviving
        # prepared record is safe to reconcile on a later access.
        _discard(self._prepared_path(project_id))

    def _read_r29_activation(self, project_id: str) -> _R29ActivationState | None:
        try:
            value = _read_closed_json_object(self._activation_path(project_id))
        except FileNotFoundError:
            return None
        state = _parse_r29_activation_state(value)
        if state.project_id != project_id:
            raise LocalFileDurabilityError("r29_activation_project_invalid")
        return state

    def _write_r29_activation(
        self,
        value: _R29ActivationState,
        *,
        before: str | None = None,
        during: str | None = None,
        after: str | None = None,
    ) -> None:
        """Persist closed R29 evidence; caller must already own the project fence."""

        _parse_r29_activation_state(value.as_dict())
        if before is None or during is None or after is None:
            _write_json_atomic(self._activation_path(value.project_id), value.as_dict())
            return
        self._write_r27_metadata_atomic(
            self._activation_path(value.project_id), value.as_dict(), before, during, after
        )

    def _prepare_r29_activation(self, value: _R29ActivationState) -> None:
        """Create one exact prepared state; caller must already own the fence."""

        if value.state != "ACTIVATION_PREPARED":
            raise LocalFileDurabilityError("r29_activation_transition_invalid")
        existing = self._read_r29_activation(value.project_id)
        if existing is None:
            self._write_r29_activation(
                value,
                before="before_activation_prepared_persistence",
                during="during_activation_prepared_persistence",
                after="after_activation_prepared_durability",
            )
            return
        if existing == value:
            return
        raise LocalFileDurabilityError("r29_activation_transition_invalid")

    def _commit_r29_activation(self, value: _R29ActivationState) -> None:
        """Advance one exact prepared state to final evidence, never backwards."""

        if value.state != "R27_COMMITTED":
            raise LocalFileDurabilityError("r29_activation_transition_invalid")
        existing = self._read_r29_activation(value.project_id)
        if existing == value:
            return
        if (
            existing is None
            or existing.state != "ACTIVATION_PREPARED"
            or existing.activation_binding_identity != value.activation_binding_identity
            or existing.activation_page_id != value.activation_page_id
            or existing.expected_aggregate_fingerprint != value.expected_aggregate_fingerprint
            or existing.expected_revision != value.expected_revision
        ):
            raise LocalFileDurabilityError("r29_activation_transition_invalid")
        self._write_r29_activation(
            value,
            before="before_activation_committed_persistence",
            during="during_activation_committed_persistence",
            after="after_activation_committed_durability",
        )

    def _remove_r29_prepared_activation(self, project_id: str) -> None:
        """Remove only a valid prepared activation; final evidence is monotonic."""

        state = self._read_r29_activation(project_id)
        if state is None:
            return
        if state.state != "ACTIVATION_PREPARED":
            raise LocalFileDurabilityError("r29_activation_monotonicity_invalid")
        _discard(self._activation_path(project_id))

    def _assert_r29_raw_replacement_allowed(self, project_id: str, payload: bytes) -> None:
        """Private lower write gate for a normal raw aggregate replacement.

        The caller holds the RevisionStore project fence through the eventual
        replacement.  Sealed R27 publication does not call this legacy-only
        gate; it remains on `_conditional_replace_r27`.
        """

        activation = self._read_r29_activation(project_id)
        if activation is not None:
            raise LocalFileDurabilityError("r29_raw_replacement_forbidden")
        try:
            framed = _decode_r27_aggregate(payload)
        except ValueError as exc:
            raise LocalFileDurabilityError("r29_aggregate_classification_invalid") from exc
        if framed is not None:
            raise LocalFileDurabilityError("r29_raw_replacement_forbidden")

    @staticmethod
    def _project_id_from_path(project_id: str) -> str:
        return project_id

    @staticmethod
    def _read_aggregate(path: Path) -> bytes:
        try:
            return path.read_bytes()
        except FileNotFoundError as exc:
            raise LocalFileDurabilityError("authoritative_aggregate_missing") from exc

    @staticmethod
    def _stage(path: Path, payload: bytes) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".tmp", delete=False) as handle:
                handle.write(payload)
                handle.flush()
                _flush_file_handle(handle.fileno())
                return Path(handle.name)
        except OSError as exc:
            raise LocalFileDurabilityError("authoritative_staging_failed") from exc

    def _stage_r27(self, path: Path, payload: bytes) -> Path:
        """Stage frozen R27 bytes while exposing private test-only durability seams."""

        self._r27_fault("before_aggregate_staging_write")
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".tmp", delete=False) as handle:
                self._r27_fault("during_aggregate_staging_write")
                handle.write(payload)
                self._r27_fault("after_aggregate_staging_write")
                handle.flush()
                _flush_file_handle(handle.fileno())
                self._r27_fault("after_aggregate_staging_file_sync")
                return Path(handle.name)
        except OSError as exc:
            raise LocalFileDurabilityError("authoritative_staging_failed") from exc

    def _write_r27_metadata_atomic(
        self,
        path: Path,
        value: dict[str, object],
        before: str,
        during: str,
        after: str,
    ) -> None:
        self._r27_fault(before)
        payload = _canonical_json_bytes(value)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".tmp", delete=False) as handle:
                handle.write(payload)
                self._r27_fault(during)
                handle.flush()
                _flush_file_handle(handle.fileno())
                staged = Path(handle.name)
        except OSError as exc:
            raise LocalFileDurabilityError("private_revision_write_failed") from exc
        try:
            os.replace(staged, path)
        except OSError as exc:
            _discard(staged)
            raise LocalFileDurabilityError("private_revision_write_failed") from exc
        self._sync_file(path)
        self._r27_fault(after)

    def _r27_fault(self, boundary: str) -> None:
        injector = self._r27_fault_injector
        if injector is not None:
            injector(boundary)

    @staticmethod
    def _sync_file(path: Path) -> None:
        try:
            # Windows FlushFileBuffers requires a writable file handle.
            with path.open("r+b") as handle:
                _flush_file_handle(handle.fileno())
        except OSError as exc:
            raise LocalFileDurabilityError("authoritative_sync_failed") from exc


def _fingerprint(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _r29_metadata_state(
    prepared: _PreparedRecord | _R27PreparedRecord | None,
    committed: _RevisionRecord | _R27CommittedRecord | None,
) -> str:
    """Classify metadata shape only; binding checks remain classifier input."""

    if isinstance(committed, _R27CommittedRecord):
        return "V2_COMMITTED_WITH_PREPARED" if isinstance(prepared, _R27PreparedRecord) else "V2_COMMITTED"
    if isinstance(prepared, _R27PreparedRecord):
        return "V2_PREPARED"
    if isinstance(prepared, _PreparedRecord):
        return "V1_PREPARED"
    if isinstance(committed, _RevisionRecord):
        return "V1_COMMITTED"
    return "ABSENT"


@dataclass(frozen=True, slots=True)
class _R29BindingFacts:
    """Closed, non-durable exactness observations for one restart tuple."""

    state: str
    aggregate_f0: str | None
    aggregate_f1: str | None
    expected_f0_matches: bool | None
    proposed_f0_matches: bool | None
    lineage_identity: str | None
    activation_project_matches: bool | None
    revision_project_matches: bool | None


def _r29_allocate_binding(
    project_id: str,
    payload: bytes,
    aggregate_state: str,
    envelope: object | None,
    activation: _R29ActivationState | None,
    prepared: _PreparedRecord | _R27PreparedRecord | None,
    committed: _RevisionRecord | _R27CommittedRecord | None,
    metadata_state: str,
) -> _R29BindingFacts:
    """Allocate one frozen R29 exactness class from already-parsed records.

    Parsing itself proves the closed schemas and record-local digests.  This
    allocator proves only cross-record facts, in the frozen first-failure
    precedence, without repairing or persisting anything.
    """

    base = _r29_binding_base(project_id, payload, aggregate_state, envelope, activation, prepared, committed)
    if aggregate_state == "CORRUPT" or metadata_state == "CORRUPT":
        return replace(base, state="STALE_METADATA")
    if not base.activation_project_matches or not base.revision_project_matches:
        return replace(base, state="WRONG_PROJECT")
    if not isinstance(prepared, _R27PreparedRecord) and not isinstance(committed, _R27CommittedRecord):
        return base
    return _r29_allocate_v2_binding(base, payload, aggregate_state, activation, prepared, committed)


def _r29_binding_base(
    project_id: str,
    payload: bytes,
    aggregate_state: str,
    envelope: object | None,
    activation: _R29ActivationState | None,
    prepared: _PreparedRecord | _R27PreparedRecord | None,
    committed: _RevisionRecord | _R27CommittedRecord | None,
) -> _R29BindingFacts:
    """Collect the common non-durable R29 facts for one parsed tuple."""

    activation_project_matches = activation is None or activation.project_id == project_id
    revision_project_matches = _r29_revision_projects_match(project_id, prepared, committed)
    aggregate_f1 = getattr(envelope, "authoritative_envelope_fingerprint", None)
    return _R29BindingFacts(
        state="EXACT",
        aggregate_f0=_physical_fingerprint(payload) if aggregate_state != "CORRUPT" else None,
        aggregate_f1=aggregate_f1 if isinstance(aggregate_f1, str) else None,
        expected_f0_matches=None,
        proposed_f0_matches=None,
        lineage_identity=None,
        activation_project_matches=activation_project_matches,
        revision_project_matches=revision_project_matches,
    )


def _r29_revision_projects_match(
    project_id: str,
    prepared: _PreparedRecord | _R27PreparedRecord | None,
    committed: _RevisionRecord | _R27CommittedRecord | None,
) -> bool:
    if prepared is not None and _prepared_parts(prepared)[0].project_id != project_id:
        return False
    return committed is None or _committed_record(committed).project_id == project_id


def _r29_allocate_v2_binding(
    base: _R29BindingFacts,
    payload: bytes,
    aggregate_state: str,
    activation: _R29ActivationState | None,
    prepared: _PreparedRecord | _R27PreparedRecord | None,
    committed: _RevisionRecord | _R27CommittedRecord | None,
) -> _R29BindingFacts:
    """Apply the frozen R29 cross-record exactness precedence for R28 v2."""

    prepared_v2 = prepared if isinstance(prepared, _R27PreparedRecord) else None
    committed_v2 = committed if isinstance(committed, _R27CommittedRecord) else None
    assert prepared_v2 is not None or committed_v2 is not None
    if prepared_v2 is not None:
        lineage = prepared_v2.lineage
    else:
        assert committed_v2 is not None
        lineage = committed_v2.lineage
    lineage_identity = _r27_lineage_identity(lineage)
    base = replace(base, lineage_identity=lineage_identity)
    if prepared_v2 is not None and committed_v2 is not None and prepared_v2.lineage != committed_v2.lineage:
        return replace(base, state="CROSS_LINEAGE")
    activation_binds_current_lineage = (
        activation is not None
        and (
            activation.state == "ACTIVATION_PREPARED"
            or (
                committed_v2 is not None
                and activation.committed_revision == committed_v2.record.revision
            )
        )
    )
    if activation_binds_current_lineage and activation is not None and activation.activation_binding_identity != lineage["application_binding_identity"]:
        return replace(base, state="WRONG_ACTIVATION_BINDING")
    if prepared_v2 is not None:
        expected, proposed, _ = _prepared_parts(prepared_v2)
    else:
        assert committed_v2 is not None
        expected = _r29_lineage_expected_record(lineage)
        proposed = committed_v2.record
    if activation_binds_current_lineage and activation is not None and activation.expected_revision != expected.revision:
        return replace(base, state="WRONG_REVISION")
    if (
        activation_binds_current_lineage
        and activation is not None
        and activation.expected_aggregate_fingerprint != expected.fingerprint
    ):
        return replace(base, state="WRONG_EXPECTED_F0")
    if base.aggregate_f0 is None:
        return replace(base, state="STALE_METADATA")
    expected_matches = base.aggregate_f0 == expected.fingerprint if aggregate_state == "RAW" else True
    proposed_matches = base.aggregate_f0 == proposed.fingerprint if aggregate_state == "R27" else True
    base = replace(
        base,
        expected_f0_matches=expected_matches,
        proposed_f0_matches=proposed_matches,
    )
    if not expected_matches:
        return replace(base, state="WRONG_EXPECTED_F0")
    if not proposed_matches:
        return replace(base, state="WRONG_PROPOSED_F0")
    return _r29_validate_v2_frame(
        base, payload, aggregate_state, activation, committed_v2, proposed, lineage, lineage_identity
    )


def _r29_lineage_expected_record(lineage: dict[str, object]) -> _RevisionRecord:
    """Reconstruct only validated record facts from a closed R28 lineage."""

    project_id = lineage["project_id"]
    revision = lineage["expected_revision"]
    fingerprint = lineage["expected_aggregate_fingerprint"]
    assert isinstance(project_id, str)
    assert type(revision) is int
    assert isinstance(fingerprint, str)
    return _RevisionRecord(project_id=project_id, revision=revision, fingerprint=fingerprint)


def _r29_validate_v2_frame(
    base: _R29BindingFacts,
    payload: bytes,
    aggregate_state: str,
    activation: _R29ActivationState | None,
    committed: _R27CommittedRecord | None,
    proposed: _RevisionRecord,
    lineage: dict[str, object],
    lineage_identity: str,
) -> _R29BindingFacts:
    """Validate R27 frame and final-activation facts after F0 exactness."""

    try:
        if aggregate_state == "R27":
            _validate_r27_aggregate(payload, proposed, lineage)
    except LocalFileDurabilityError:
        return replace(base, state="STALE_METADATA")
    if committed is not None and activation is not None and activation.state == "R27_COMMITTED":
        assert activation.committed_revision is not None
        assert activation.committed_aggregate_fingerprint is not None
        if committed.record.revision < activation.committed_revision:
            return replace(base, state="WRONG_REVISION")
        if committed.record.revision == activation.committed_revision and (
            activation.committed_aggregate_fingerprint != committed.record.fingerprint
            or activation.source_lineage_identity != lineage_identity
        ):
            return replace(base, state="CROSS_LINEAGE")
    return base


def _classify_r29_pre_reconciliation(snapshot: _R29PreReconciliationSnapshot) -> str:
    """Select one frozen R29 result from a read-only durable observation."""

    if "CORRUPT" in {
        snapshot.aggregate_state,
        snapshot.activation_state,
        snapshot.metadata_state,
    }:
        return "FAIL_CLOSED"
    if snapshot.binding_state != "EXACT":
        return "FAIL_CLOSED"
    matrix: dict[tuple[str, str], dict[str, str]] = {
        ("RAW", "ABSENT"): {
            "ABSENT": "LEGACY",
            "V1_COMMITTED": "LEGACY",
            "V1_PREPARED": "LEGACY",
            "V2_PREPARED": "LEGACY",
            "V2_COMMITTED": "FAIL_CLOSED",
            "V2_COMMITTED_WITH_PREPARED": "FAIL_CLOSED",
        },
        ("RAW", "ACTIVATION_PREPARED"): {
            "ABSENT": "ACTIVATION_RECOVERY",
            "V1_COMMITTED": "ACTIVATION_RECOVERY",
            "V1_PREPARED": "ACTIVATION_RECOVERY",
            "V2_PREPARED": "ACTIVATION_RECOVERY",
            "V2_COMMITTED": "FAIL_CLOSED",
            "V2_COMMITTED_WITH_PREPARED": "FAIL_CLOSED",
        },
        ("RAW", "R27_COMMITTED"): {},
        ("R27", "ABSENT"): {},
        ("R27", "ACTIVATION_PREPARED"): {
            "V2_PREPARED": "R27_RECONCILE",
            "V2_COMMITTED": "ACTIVATION_RECOVERY",
            "V2_COMMITTED_WITH_PREPARED": "ACTIVATION_RECOVERY",
        },
        ("R27", "R27_COMMITTED"): {"V2_COMMITTED": "R27"},
    }
    return matrix.get((snapshot.aggregate_state, snapshot.activation_state), {}).get(
        snapshot.metadata_state, "FAIL_CLOSED"
    )


def _validate_record(
    aggregate_payload: bytes,
    record: _RevisionRecord,
    validator: Callable[[bytes, str, int, str], None] | None,
) -> None:
    if validator is not None:
        validator(aggregate_payload, record.project_id, record.revision, record.fingerprint)


def _write_json_atomic(path: Path, value: dict[str, object]) -> None:
    payload = _canonical_json_bytes(value)
    staged = LocalFileRevisionStore._stage(path, payload)
    try:
        os.replace(staged, path)
    except OSError as exc:
        _discard(staged)
        raise LocalFileDurabilityError("private_revision_write_failed") from exc
    LocalFileRevisionStore._sync_file(path)


def _parse_revision_record(value: object) -> _RevisionRecord:
    if not isinstance(value, dict) or value.get("schema_version") != _SCHEMA_VERSION:
        raise LocalFileDurabilityError("revision_record_schema_invalid")
    project_id = value.get("project_id")
    revision = value.get("revision")
    fingerprint = value.get("fingerprint")
    if (
        not isinstance(project_id, str)
        or not project_id
        or type(revision) is not int
        or revision < 1
        or not _is_sha256(fingerprint)
    ):
        raise LocalFileDurabilityError("revision_record_invalid")
    assert isinstance(project_id, str)
    assert type(revision) is int
    assert isinstance(fingerprint, str)
    return _RevisionRecord(project_id=project_id, revision=revision, fingerprint=fingerprint)


def _canonical_json_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, UnicodeEncodeError, ValueError) as exc:
        raise LocalFileDurabilityError("revision_metadata_corrupt") from exc


def _read_revision_metadata(path: Path) -> tuple[str, dict[str, object]]:
    """Classify raw metadata before normalizing its object representation."""

    try:
        raw = path.read_text(encoding="utf-8")
        value = json.loads(
            raw,
            object_pairs_hook=_RawObject,
            parse_float=_raw_number,
            parse_constant=_reject_json_constant,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        if isinstance(exc, FileNotFoundError):
            raise
        raise LocalFileDurabilityError("revision_metadata_corrupt") from exc
    if not isinstance(value, _RawObject):
        raise LocalFileDurabilityError("revision_metadata_corrupt")
    versions = [item for key, item in value if key == "schema_version"]
    if len(versions) != 1:
        raise LocalFileDurabilityError("revision_metadata_corrupt")
    version = versions[0]
    if type(version) is int and version == 1:
        return "LEGACY_V1", _legacy_json_object(value)
    if type(version) is int and version == 2:
        strict = _strict_json_object(value)
        if _canonical_json_bytes(strict) != raw.encode("utf-8"):
            raise LocalFileDurabilityError("revision_metadata_corrupt")
        return "R27_V2", strict
    # Preserve the established v1 diagnostic for a well-formed but unsupported
    # schema while still rejecting it before any normalization or recovery.
    raise LocalFileDurabilityError("revision_record_schema_invalid")


def _read_closed_json_object(path: Path) -> dict[str, object]:
    """Read one closed canonical JSON object without legacy normalization."""

    try:
        raw = path.read_text(encoding="utf-8")
        value = json.loads(
            raw,
            object_pairs_hook=_RawObject,
            parse_float=_raw_number,
            parse_constant=_reject_json_constant,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        if isinstance(exc, FileNotFoundError):
            raise
        raise LocalFileDurabilityError("r29_activation_corrupt") from exc
    if not isinstance(value, _RawObject):
        raise LocalFileDurabilityError("r29_activation_corrupt")
    strict = _strict_json_object(value)
    if _canonical_json_bytes(strict) != raw.encode("utf-8"):
        raise LocalFileDurabilityError("r29_activation_corrupt")
    return strict


def _raw_number(text: str) -> _RawNumber:
    return _RawNumber(text)


def _reject_json_constant(value: str) -> object:
    del value
    raise ValueError("non-finite JSON number")


def _legacy_json_object(value: _RawObject) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, item in value:
        result[key] = _legacy_json_value(item)
    return result


def _legacy_json_value(value: object) -> object:
    if isinstance(value, _RawObject):
        return _legacy_json_object(value)
    if isinstance(value, _RawNumber):
        try:
            return float(value.text)
        except ValueError as exc:
            raise LocalFileDurabilityError("revision_metadata_corrupt") from exc
    if isinstance(value, list):
        return [_legacy_json_value(item) for item in value]
    return value


def _strict_json_object(value: _RawObject) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, item in value:
        if key in result:
            raise LocalFileDurabilityError("revision_metadata_corrupt")
        result[key] = _strict_json_value(item)
    return result


def _strict_json_value(value: object) -> object:
    if isinstance(value, _RawObject):
        return _strict_json_object(value)
    if isinstance(value, _RawNumber):
        raise LocalFileDurabilityError("revision_metadata_corrupt")
    if isinstance(value, list):
        return [_strict_json_value(item) for item in value]
    return value


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def _parse_r29_activation_state(value: object) -> _R29ActivationState:
    if not isinstance(value, dict):
        raise LocalFileDurabilityError("r29_activation_schema_invalid")
    state = value.get("state")
    expected_keys = (
        _R29_ACTIVATION_PREPARED_KEYS
        if state == "ACTIVATION_PREPARED"
        else _R29_ACTIVATION_COMMITTED_KEYS
        if state == "R27_COMMITTED"
        else frozenset()
    )
    if set(value) != expected_keys or value.get("marker_kind") != _R29_ACTIVATION_KIND:
        raise LocalFileDurabilityError("r29_activation_schema_invalid")
    project_id = value.get("project_id")
    page_id = value.get("activation_page_id")
    expected_revision = value.get("expected_revision")
    binding = value.get("activation_binding_identity")
    expected_fingerprint = value.get("expected_aggregate_fingerprint")
    if (
        value.get("schema_version") != 1
        or type(value.get("schema_version")) is not int
        or not isinstance(project_id, str)
        or not project_id
        or not isinstance(page_id, str)
        or not page_id
        or type(expected_revision) is not int
        or expected_revision < 1
        or not _is_sha256(binding)
        or not _is_sha256(expected_fingerprint)
    ):
        raise LocalFileDurabilityError("r29_activation_schema_invalid")
    assert isinstance(project_id, str)
    assert isinstance(page_id, str)
    assert isinstance(expected_revision, int)
    assert isinstance(binding, str)
    assert isinstance(expected_fingerprint, str)
    assert isinstance(state, str)
    if state == "ACTIVATION_PREPARED":
        return _R29ActivationState(
            activation_binding_identity=binding,
            activation_page_id=page_id,
            expected_aggregate_fingerprint=expected_fingerprint,
            expected_revision=expected_revision,
            project_id=project_id,
            state=state,
        )
    committed_fingerprint = value.get("committed_aggregate_fingerprint")
    committed_revision = value.get("committed_revision")
    lineage = value.get("source_lineage_identity")
    if (
        not _is_sha256(committed_fingerprint)
        or type(committed_revision) is not int
        or committed_revision < 1
        or not _is_sha256(lineage)
    ):
        raise LocalFileDurabilityError("r29_activation_schema_invalid")
    assert isinstance(committed_fingerprint, str)
    assert isinstance(committed_revision, int)
    assert isinstance(lineage, str)
    return _R29ActivationState(
        activation_binding_identity=binding,
        activation_page_id=page_id,
        expected_aggregate_fingerprint=expected_fingerprint,
        expected_revision=expected_revision,
        project_id=project_id,
        state=state,
        committed_aggregate_fingerprint=committed_fingerprint,
        committed_revision=committed_revision,
        source_lineage_identity=lineage,
    )


def _prepared_parts(
    record: _PreparedRecord | _R27PreparedRecord,
) -> tuple[_RevisionRecord, _RevisionRecord, dict[str, object] | None]:
    if isinstance(record, _R27PreparedRecord):
        return record.expected, record.proposed, record.lineage
    return record.expected, record.proposed, None


def _committed_record(record: _RevisionRecord | _R27CommittedRecord) -> _RevisionRecord:
    if isinstance(record, _R27CommittedRecord):
        return record.record
    return record


def _validate_prepared_commit_pair(
    committed: _RevisionRecord | _R27CommittedRecord | None,
    expected: _RevisionRecord,
    proposed: _RevisionRecord,
    lineage: dict[str, object] | None,
) -> None:
    if lineage is None:
        if committed is not None and _committed_record(committed) not in {expected, proposed}:
            raise LocalFileDurabilityError("prepared_revision_ambiguous")
        return
    if committed is None:
        return
    if isinstance(committed, _RevisionRecord) and committed == expected:
        return
    if (
        not isinstance(committed, _R27CommittedRecord)
        or committed.record != proposed
        or committed.lineage != lineage
    ):
        raise LocalFileDurabilityError("r27_revision_metadata_corrupt")


def _validate_unpublished_r27_prepared_pair(
    committed: _RevisionRecord | _R27CommittedRecord | None,
    expected: _RevisionRecord,
    lineage: dict[str, object],
) -> None:
    if committed is None:
        return
    if isinstance(committed, _RevisionRecord) and committed == expected:
        return
    if not isinstance(committed, _R27CommittedRecord):
        raise LocalFileDurabilityError("r27_revision_metadata_corrupt")
    if committed.record != expected or committed.lineage != lineage:
        raise LocalFileDurabilityError("r27_revision_metadata_corrupt")


def _r27_request_matches_lineage(
    request: _R27RevisionPublicationRequest,
    snapshot: RevisionedProjectSnapshot,
    lineage: dict[str, object],
) -> bool:
    return (
        request.project_id == snapshot.project.id == lineage["project_id"]
        and request.application_binding_identity == lineage["application_binding_identity"]
        and request.attempt_id == lineage["attempt_id"]
        and request.page_id == lineage["page_id"]
        and request.target_page_reference == lineage["target_page_reference"]
        and request.source_state == lineage["source_state"]
        and request.target_state == lineage["target_state"]
        and request.expected_revision == snapshot.revision == lineage["expected_revision"]
        and request.expected_aggregate_fingerprint
        == snapshot.fingerprint
        == lineage["expected_aggregate_fingerprint"]
    )


def _parse_r27_prepared_record(value: dict[str, object]) -> _R27PreparedRecord:
    if set(value) != _R27_PREPARED_KEYS or value.get("schema_version") != 2 or value.get("r27_phase") != "PREPARED":
        raise LocalFileDurabilityError("prepared_revision_schema_invalid")
    expected = _parse_revision_record(value.get("expected"))
    proposed = _parse_revision_record(value.get("proposed"))
    lineage = _parse_r27_lineage(value.get("r27_pending_lineage"))
    _validate_r27_lineage_records(expected, proposed, lineage)
    return _R27PreparedRecord(expected=expected, proposed=proposed, lineage=lineage)


def _parse_r27_committed_record(value: dict[str, object]) -> _R27CommittedRecord:
    if set(value) != _R27_COMMITTED_KEYS or value.get("schema_version") != 2 or value.get("r27_phase") != "COMMITTED":
        raise LocalFileDurabilityError("revision_record_schema_invalid")
    record = _parse_revision_record(
        {
            "fingerprint": value.get("fingerprint"),
            "project_id": value.get("project_id"),
            "revision": value.get("revision"),
            "schema_version": 1,
        }
    )
    lineage = _parse_r27_lineage(value.get("r27_pending_lineage"))
    if lineage["project_id"] != record.project_id or lineage["resulting_revision"] != record.revision:
        raise LocalFileDurabilityError("revision_record_binding_invalid")
    return _R27CommittedRecord(record=record, lineage=lineage)


def _parse_r27_lineage(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != _R27_LINEAGE_KEYS:
        raise LocalFileDurabilityError("revision_lineage_invalid")
    _validate_r27_lineage_field_types(value)
    if value["schema"] != "manga_director.r27.pending-lineage":
        raise LocalFileDurabilityError("revision_lineage_invalid")
    if value["source_state"] != "PromptBuilt" or value["target_state"] != "Generated":
        raise LocalFileDurabilityError("revision_lineage_invalid")
    if value["expected_revision"] < 1 or value["resulting_revision"] != value["expected_revision"] + 1:
        raise LocalFileDurabilityError("revision_lineage_invalid")
    identity_body = _r27_lineage_identity_body(value)
    if value["pending_lineage_identity"] != _fingerprint(_canonical_json_bytes(identity_body)):
        raise LocalFileDurabilityError("revision_lineage_invalid")
    digest_body = {**identity_body, "pending_lineage_identity": value["pending_lineage_identity"], "resulting_revision": value["resulting_revision"]}
    if value["pending_lineage_digest"] != _fingerprint(_canonical_json_bytes(digest_body)):
        raise LocalFileDurabilityError("revision_lineage_invalid")
    return value


def _validate_r27_lineage_field_types(value: dict[str, object]) -> None:
    for key in ("schema", "source_state", "target_state", "attempt_id", "project_id", "page_id", "target_page_reference"):
        if not isinstance(value.get(key), str) or not value[key]:
            raise LocalFileDurabilityError("revision_lineage_invalid")
    for key in (
        "application_binding_identity",
        "expected_aggregate_fingerprint",
        "pending_lineage_identity",
        "pending_lineage_digest",
    ):
        if not _is_sha256(value.get(key)):
            raise LocalFileDurabilityError("revision_lineage_invalid")
    if type(value.get("version")) is not int or value["version"] != 1:
        raise LocalFileDurabilityError("revision_lineage_invalid")
    if type(value.get("expected_revision")) is not int or type(value.get("resulting_revision")) is not int:
        raise LocalFileDurabilityError("revision_lineage_invalid")


def _validate_r27_lineage_records(
    expected: _RevisionRecord,
    proposed: _RevisionRecord,
    lineage: dict[str, object],
) -> None:
    if (
        expected.project_id != proposed.project_id
        or lineage["project_id"] != expected.project_id
        or lineage["expected_revision"] != expected.revision
        or lineage["resulting_revision"] != proposed.revision
        or lineage["expected_aggregate_fingerprint"] != expected.fingerprint
    ):
        raise LocalFileDurabilityError("revision_lineage_binding_invalid")


def _r27_lineage_identity_body(value: dict[str, object]) -> dict[str, object]:
    return {
        key: value[key]
        for key in (
            "schema",
            "version",
            "application_binding_identity",
            "attempt_id",
            "project_id",
            "page_id",
            "target_page_reference",
            "source_state",
            "target_state",
            "expected_revision",
            "expected_aggregate_fingerprint",
        )
    }


def _r27_lineage(request: _R27RevisionPublicationRequest, *, resulting_revision: int) -> dict[str, object]:
    result: dict[str, object] = {
        "schema": "manga_director.r27.pending-lineage",
        "version": 1,
        "application_binding_identity": request.application_binding_identity,
        "attempt_id": request.attempt_id,
        "project_id": request.project_id,
        "page_id": request.page_id,
        "target_page_reference": request.target_page_reference,
        "source_state": request.source_state,
        "target_state": request.target_state,
        "expected_revision": request.expected_revision,
        "expected_aggregate_fingerprint": request.expected_aggregate_fingerprint,
        "resulting_revision": resulting_revision,
        "pending_lineage_identity": "",
        "pending_lineage_digest": "",
    }
    identity = _fingerprint(_canonical_json_bytes(_r27_lineage_identity_body(result)))
    result["pending_lineage_identity"] = identity
    digest_body = {
        **_r27_lineage_identity_body(result),
        "pending_lineage_identity": identity,
        "resulting_revision": resulting_revision,
    }
    result["pending_lineage_digest"] = _fingerprint(_canonical_json_bytes(digest_body))
    return result


def _r27_lineage_identity(lineage: dict[str, object]) -> str:
    """Return the already-validated immutable R28 lineage identity."""

    value = lineage.get("pending_lineage_identity")
    if not isinstance(value, str) or not _is_sha256(value):
        raise LocalFileDurabilityError("r27_lineage_schema_invalid")
    return value


def _r27_prepared_dict(record: _R27PreparedRecord) -> dict[str, object]:
    return {
        "expected": record.expected.as_dict(),
        "proposed": record.proposed.as_dict(),
        "r27_pending_lineage": record.lineage,
        "r27_phase": "PREPARED",
        "schema_version": 2,
    }


def _r27_committed_dict(record: _R27CommittedRecord) -> dict[str, object]:
    return {
        "fingerprint": record.record.fingerprint,
        "project_id": record.record.project_id,
        "r27_pending_lineage": record.lineage,
        "r27_phase": "COMMITTED",
        "revision": record.record.revision,
        "schema_version": 2,
    }


def _validate_r27_request(
    request: _R27RevisionPublicationRequest,
    snapshot: RevisionedProjectSnapshot,
    project_id: str,
) -> None:
    if type(request) is not _R27RevisionPublicationRequest:
        raise LocalFileDurabilityError("r27_publication_request_invalid")
    if (
        request.project_id != project_id
        or request.expected_revision != snapshot.revision
        or request.expected_aggregate_fingerprint != snapshot.fingerprint
        or not _is_sha256(request.application_binding_identity)
        or not _is_sha256(request.expected_aggregate_fingerprint)
        or type(request.expected_revision) is not int
        or request.expected_revision < 1
    ):
        raise LocalFileDurabilityError("r27_publication_request_invalid")
    for value in (request.attempt_id, request.page_id, request.target_page_reference):
        if not isinstance(value, str) or not value:
            raise LocalFileDurabilityError("r27_publication_request_invalid")
    if request.source_state != "PromptBuilt" or request.target_state != "Generated":
        raise LocalFileDurabilityError("r27_publication_request_invalid")


def _validate_r27_aggregate(
    aggregate_payload: bytes,
    record: _RevisionRecord,
    lineage: dict[str, object],
) -> None:
    try:
        envelope = _decode_r27_aggregate(aggregate_payload)
    except ValueError as exc:
        raise LocalFileDurabilityError("r27_aggregate_invalid") from exc
    if envelope is None or _physical_fingerprint(aggregate_payload) != record.fingerprint:
        raise LocalFileDurabilityError("r27_aggregate_invalid")
    witness = envelope.witness
    expected = {
        "application_binding_identity": lineage["application_binding_identity"],
        "expected_aggregate_fingerprint": lineage["expected_aggregate_fingerprint"],
        "expected_revision": lineage["expected_revision"],
        "pending_lineage_digest": lineage["pending_lineage_digest"],
        "pending_lineage_identity": lineage["pending_lineage_identity"],
        "resulting_revision": lineage["resulting_revision"],
        "schema": "manga_director.r27.same-cas-witness",
        "version": 1,
        "protocol_version": 1,
    }
    if any(witness.get(key) != item for key, item in expected.items()):
        raise LocalFileDurabilityError("r27_aggregate_binding_invalid")


def _discard(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def _flush_file_handle(file_descriptor: int) -> None:
    """Synchronize one file through the platform-supported primitive."""

    if os.name != "nt":
        os.fsync(file_descriptor)
        return
    import msvcrt

    handle = msvcrt.get_osfhandle(file_descriptor)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    flush_file_buffers = kernel32.FlushFileBuffers
    flush_file_buffers.argtypes = (ctypes.c_void_p,)
    flush_file_buffers.restype = ctypes.c_bool
    if not flush_file_buffers(ctypes.c_void_p(handle)):
        raise OSError(ctypes.get_last_error(), "FlushFileBuffers failed")
