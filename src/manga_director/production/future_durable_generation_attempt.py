"""Private, future-only durable generation-attempt persistence.

This module records local intent and synthetic test evidence only.  It has no
provider adapter, credential, network, StateMachine, or public-export surface.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeAlias

from pydantic import ConfigDict, Field, field_validator

from manga_director.production.director import DirectorModel
from manga_director.production.future_generation_admission_contract import SnapshotIdentityV1

AttemptLifecycle = Literal[
    "RESERVED",
    "PROVIDER_STARTING",
    "PROVIDER_STARTED",
    "RESULT_CAPTURED",
    "APPLIED",
    "FAILED",
    "RECOVERY_REQUIRED",
]
StoreOutcome = Literal[
    "reserved",
    "confirmed",
    "conflict",
    "target_conflict",
    "transitioned",
    "consumed",
    "invalid",
    "missing",
    "corrupt",
]
CanonicalValue: TypeAlias = None | bool | int | float | str | tuple["CanonicalValue", ...] | dict[str, "CanonicalValue"]

_DATABASE_FILENAME = "future-generation-attempts.sqlite3"
_SCHEMA_VERSION = 3
_TABLE = "future_generation_attempts"
_ACTIVE_STATES = ("RESERVED", "PROVIDER_STARTING", "PROVIDER_STARTED", "RESULT_CAPTURED")
_TERMINAL_STATES = ("APPLIED", "FAILED")
_BLOCKING_STATES = (*_ACTIVE_STATES, "RECOVERY_REQUIRED")
_REQUIRED_INDEX = "active_or_recovery_future_generation_target"
_SHA256_LENGTH = 64
_SECRET_PARTS = ("api_key", "apikey", "authorization", "credential", "endpoint", "password", "secret", "token")


class _AttemptModel(DirectorModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class FutureGenerationAttemptV1(_AttemptModel):
    """Redacted immutable binding plus the private durable lifecycle state."""

    schema_id: Literal["manga_director.future_generation_attempt"] = "manga_director.future_generation_attempt"
    schema_version: Literal["1"] = "1"
    attempt_id: str
    project_id: str
    page_id: str
    execution_target_reference: str
    manifest_digest: str
    snapshot: SnapshotIdentityV1
    provider_binding_digest: str
    lifecycle: AttemptLifecycle = "RESERVED"
    sequence: int = Field(default=0, ge=0)
    evidence_digest: str | None = None
    dispatch_consumed_sequence: int | None = Field(default=None, ge=0)
    dispatch_request_identity: str | None = None

    @field_validator("attempt_id", "project_id", "page_id", "execution_target_reference")
    @classmethod
    def _logical_reference(cls, value: str) -> str:
        return _safe_reference(value)

    @field_validator("manifest_digest", "provider_binding_digest", "evidence_digest")
    @classmethod
    def _digest(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _safe_digest(value)

    @field_validator("dispatch_request_identity")
    @classmethod
    def _dispatch_request_identity(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _safe_digest(value)

    def model_post_init(self, __context: object) -> None:
        if (self.dispatch_consumed_sequence is None) != (self.dispatch_request_identity is None):
            raise ValueError("dispatch consumption metadata must be complete")
        if self.dispatch_consumed_sequence is not None and self.dispatch_consumed_sequence > self.sequence:
            raise ValueError("dispatch consumption sequence must not exceed attempt sequence")

    def binding_projection(self) -> dict[str, CanonicalValue]:
        return {
            "attempt_id": self.attempt_id,
            "execution_target_reference": self.execution_target_reference,
            "manifest_digest": self.manifest_digest,
            "page_id": self.page_id,
            "project_id": self.project_id,
            "provider_binding_digest": self.provider_binding_digest,
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "snapshot": {"fingerprint": self.snapshot.fingerprint, "revision": self.snapshot.revision},
        }

    @property
    def binding_digest(self) -> str:
        return _digest_json(self.binding_projection())


@dataclass(frozen=True, slots=True)
class FutureGenerationAttemptStoreResult:
    outcome: StoreOutcome
    attempt: FutureGenerationAttemptV1 | None = None


class _LocalFutureGenerationAttemptStore:
    """Test-only low-level SQLite store; trusted composition owns its root."""

    def __init__(self, owner_root: Path) -> None:
        self._root = _prepare_owner_root(owner_root)
        self._database = _prepare_database_path(self._root)
        self._initialize_schema()

    def reserve(self, attempt: FutureGenerationAttemptV1) -> FutureGenerationAttemptStoreResult:
        if attempt.lifecycle != "RESERVED" or attempt.sequence != 0 or attempt.evidence_digest is not None:
            return FutureGenerationAttemptStoreResult("invalid")
        try:
            with self._transaction() as connection:
                existing = self._read_by_attempt(connection, attempt.attempt_id)
                if existing is not None:
                    return FutureGenerationAttemptStoreResult(
                        "confirmed" if existing == attempt else "conflict", existing
                    )
                active = self._read_active_target(
                    connection, attempt.project_id, attempt.page_id, attempt.execution_target_reference
                )
                if active is not None:
                    return FutureGenerationAttemptStoreResult("target_conflict", active)
                self._insert(connection, attempt)
                return FutureGenerationAttemptStoreResult("reserved", attempt)
        except (sqlite3.Error, TypeError, ValueError):
            return FutureGenerationAttemptStoreResult("corrupt")

    def lookup(self, attempt_id: str) -> FutureGenerationAttemptStoreResult:
        try:
            _safe_reference(attempt_id)
            with self._connect() as connection:
                attempt = self._read_by_attempt(connection, attempt_id)
        except (sqlite3.Error, TypeError, ValueError):
            return FutureGenerationAttemptStoreResult("corrupt")
        if attempt is None:
            return FutureGenerationAttemptStoreResult("missing")
        return FutureGenerationAttemptStoreResult("confirmed", attempt)

    def transition(
        self,
        attempt: FutureGenerationAttemptV1,
        target: AttemptLifecycle,
        *,
        evidence_digest: str | None = None,
    ) -> FutureGenerationAttemptStoreResult:
        if not _legal_transition(attempt.lifecycle, target, evidence_digest):
            return FutureGenerationAttemptStoreResult("invalid")
        if evidence_digest is not None:
            try:
                _safe_digest(evidence_digest)
            except ValueError:
                return FutureGenerationAttemptStoreResult("invalid")
        try:
            with self._transaction() as connection:
                current = self._read_by_attempt(connection, attempt.attempt_id)
                if current is None:
                    return FutureGenerationAttemptStoreResult("missing")
                if current != attempt:
                    return FutureGenerationAttemptStoreResult("conflict", current)
                updated = current.model_copy(
                    update={"lifecycle": target, "sequence": current.sequence + 1, "evidence_digest": evidence_digest}
                )
                self._update(connection, updated)
                return FutureGenerationAttemptStoreResult("transitioned", updated)
        except (sqlite3.Error, TypeError, ValueError):
            return FutureGenerationAttemptStoreResult("corrupt")

    def consume(
        self, attempt: FutureGenerationAttemptV1, dispatch_request_identity: str
    ) -> FutureGenerationAttemptStoreResult:
        if (
            attempt.lifecycle != "PROVIDER_STARTING"
            or attempt.dispatch_consumed_sequence is not None
            or attempt.dispatch_request_identity is not None
        ):
            return FutureGenerationAttemptStoreResult("invalid")
        try:
            _safe_digest(dispatch_request_identity)
            with self._transaction() as connection:
                current = self._read_by_attempt(connection, attempt.attempt_id)
                if current is None:
                    return FutureGenerationAttemptStoreResult("missing")
                if current != attempt:
                    return FutureGenerationAttemptStoreResult("conflict", current)
                if (
                    current.lifecycle != "PROVIDER_STARTING"
                    or current.dispatch_consumed_sequence is not None
                    or current.dispatch_request_identity is not None
                ):
                    return FutureGenerationAttemptStoreResult("invalid", current)
                consumed = current.model_copy(
                    update={
                        "dispatch_consumed_sequence": current.sequence,
                        "dispatch_request_identity": dispatch_request_identity,
                    }
                )
                self._update(connection, consumed)
                return FutureGenerationAttemptStoreResult("consumed", consumed)
        except (sqlite3.Error, TypeError, ValueError):
            return FutureGenerationAttemptStoreResult("corrupt")

    def _initialize_schema(self) -> None:
        try:
            with self._transaction() as connection:
                version = int(connection.execute("PRAGMA user_version").fetchone()[0])
                if version == 0 and not _has_user_tables(connection):
                    connection.execute(
                        f"CREATE TABLE {_TABLE} (attempt_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, "
                        "page_id TEXT NOT NULL, target_reference TEXT NOT NULL, lifecycle TEXT NOT NULL, binding_digest TEXT NOT NULL, "
                        "payload_json TEXT NOT NULL, payload_digest TEXT NOT NULL)"
                    )
                    connection.execute(
                        f"CREATE UNIQUE INDEX {_REQUIRED_INDEX} ON {_TABLE} "
                        "(project_id, page_id, target_reference) "
                        "WHERE lifecycle IN ('RESERVED', 'PROVIDER_STARTING', 'PROVIDER_STARTED', "
                        "'RESULT_CAPTURED', 'RECOVERY_REQUIRED')"
                    )
                    connection.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")
                    return
                if version != _SCHEMA_VERSION or not _schema_is_valid(connection):
                    raise ValueError("attempt store is unavailable")
        except (sqlite3.Error, TypeError, ValueError) as error:
            raise ValueError("attempt store is unavailable") from error

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database, timeout=5.0, isolation_level=None)
        mode = str(connection.execute("PRAGMA journal_mode = DELETE").fetchone()[0]).lower()
        if mode != "delete":
            connection.close()
            raise ValueError("attempt store is unavailable")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    @staticmethod
    def _insert(connection: sqlite3.Connection, attempt: FutureGenerationAttemptV1) -> None:
        payload = _canonical_json(attempt.model_dump(mode="json"))
        connection.execute(
            f"INSERT INTO {_TABLE} VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                attempt.attempt_id,
                attempt.project_id,
                attempt.page_id,
                attempt.execution_target_reference,
                attempt.lifecycle,
                attempt.binding_digest,
                payload,
                _digest_text(payload),
            ),
        )

    @staticmethod
    def _update(connection: sqlite3.Connection, attempt: FutureGenerationAttemptV1) -> None:
        payload = _canonical_json(attempt.model_dump(mode="json"))
        connection.execute(
            f"UPDATE {_TABLE} SET lifecycle=?, binding_digest=?, payload_json=?, payload_digest=? WHERE attempt_id=?",
            (attempt.lifecycle, attempt.binding_digest, payload, _digest_text(payload), attempt.attempt_id),
        )

    @staticmethod
    def _read_by_attempt(connection: sqlite3.Connection, attempt_id: str) -> FutureGenerationAttemptV1 | None:
        row = connection.execute(
            f"SELECT attempt_id, project_id, page_id, target_reference, lifecycle, binding_digest, payload_json, payload_digest "
            f"FROM {_TABLE} WHERE attempt_id=?", (attempt_id,)
        ).fetchone()
        return _verified_row(row)

    @staticmethod
    def _read_active_target(
        connection: sqlite3.Connection, project_id: str, page_id: str, target_reference: str
    ) -> FutureGenerationAttemptV1 | None:
        rows = connection.execute(
            f"SELECT attempt_id, project_id, page_id, target_reference, lifecycle, binding_digest, payload_json, payload_digest "
            f"FROM {_TABLE} WHERE project_id=? AND page_id=? AND target_reference=?",
            (project_id, page_id, target_reference),
        ).fetchall()
        for row in rows:
            attempt = _verified_row(row)
            if attempt is None:
                raise ValueError("attempt store is unavailable")
            if attempt.lifecycle in _BLOCKING_STATES:
                return attempt
        return None


def _legal_transition(source: AttemptLifecycle, target: AttemptLifecycle, evidence_digest: str | None) -> bool:
    if source == "RESERVED":
        return target == "PROVIDER_STARTING" and evidence_digest is None
    if source == "PROVIDER_STARTING":
        return (target == "PROVIDER_STARTED" and evidence_digest is not None) or (
            target == "RECOVERY_REQUIRED" and evidence_digest is None
        )
    if source == "PROVIDER_STARTED":
        return (target == "RESULT_CAPTURED" and evidence_digest is not None) or (
            target == "FAILED" and evidence_digest is None
        )
    if source == "RESULT_CAPTURED":
        return target == "APPLIED" and evidence_digest is None
    return False


def _verified_row(row: object) -> FutureGenerationAttemptV1 | None:
    if row is None:
        return None
    if not isinstance(row, tuple) or len(row) != 8:
        raise ValueError("attempt row is corrupt")
    attempt_id, project_id, page_id, target, lifecycle, binding_digest, payload, payload_digest = row
    if not all(isinstance(item, str) for item in row):
        raise ValueError("attempt row is corrupt")
    if _digest_text(payload) != payload_digest:
        raise ValueError("attempt row is corrupt")
    try:
        attempt = FutureGenerationAttemptV1.model_validate_json(payload)
    except (TypeError, ValueError) as error:
        raise ValueError("attempt row is corrupt") from error
    if (
        attempt.attempt_id != attempt_id
        or attempt.project_id != project_id
        or attempt.page_id != page_id
        or attempt.execution_target_reference != target
        or attempt.lifecycle != lifecycle
        or attempt.binding_digest != binding_digest
        or _canonical_json(attempt.model_dump(mode="json")) != payload
    ):
        raise ValueError("attempt row is corrupt")
    return attempt


def _prepare_owner_root(owner_root: Path) -> Path:
    if not isinstance(owner_root, Path) or not owner_root.is_absolute() or ".." in owner_root.parts:
        raise ValueError("attempt store is unavailable")
    try:
        owner_root.mkdir(parents=True, exist_ok=True)
        _assert_private_path(owner_root, owner_root.parent)
    except OSError as error:
        raise ValueError("attempt store is unavailable") from error
    return owner_root


def _prepare_database_path(owner_root: Path) -> Path:
    path = owner_root / _DATABASE_FILENAME
    try:
        _assert_private_path(path, owner_root)
    except OSError as error:
        raise ValueError("attempt store is unavailable") from error
    return path


def _assert_private_path(path: Path, parent: Path) -> None:
    if path.parent != parent or _is_link_or_reparse_point(path):
        raise OSError("attempt store is unavailable")
    if parent.exists() and _is_link_or_reparse_point(parent):
        raise OSError("attempt store is unavailable")


def _is_link_or_reparse_point(path: Path) -> bool:
    try:
        status = path.lstat()
    except OSError:
        return False
    attributes = getattr(status, "st_file_attributes", 0)
    reparse_point = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return stat.S_ISLNK(status.st_mode) or bool(attributes & reparse_point)


def _has_user_tables(connection: sqlite3.Connection) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' LIMIT 1"
    ).fetchone() is not None


def _schema_is_valid(connection: sqlite3.Connection) -> bool:
    rows = connection.execute(f"PRAGMA table_info({_TABLE})").fetchall()
    expected = (
        ("attempt_id", "TEXT", 1),
        ("project_id", "TEXT", 0),
        ("page_id", "TEXT", 0),
        ("target_reference", "TEXT", 0),
        ("lifecycle", "TEXT", 0),
        ("binding_digest", "TEXT", 0),
        ("payload_json", "TEXT", 0),
        ("payload_digest", "TEXT", 0),
    )
    actual = tuple((str(row[1]), str(row[2]).upper(), int(row[5])) for row in rows)
    if actual != expected:
        return False
    row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type='index' AND name=?", (_REQUIRED_INDEX,)
    ).fetchone()
    if not isinstance(row, tuple) or len(row) != 1 or not isinstance(row[0], str):
        return False
    actual_index = " ".join(row[0].upper().split())
    expected_index = (
        f"CREATE UNIQUE INDEX {_REQUIRED_INDEX.upper()} ON {_TABLE.upper()} "
        "(PROJECT_ID, PAGE_ID, TARGET_REFERENCE) WHERE LIFECYCLE IN "
        "('RESERVED', 'PROVIDER_STARTING', 'PROVIDER_STARTED', 'RESULT_CAPTURED', "
        "'RECOVERY_REQUIRED')"
    )
    return actual_index == expected_index


def _safe_reference(value: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or any(char.isspace() for char in value):
        raise ValueError("attempt reference must be a nonblank logical reference")
    if value.startswith(("/", "\\")) or "://" in value or (len(value) > 2 and value[1] == ":"):
        raise ValueError("attempt reference must not be a path or URL")
    if any(part in value.lower() for part in _SECRET_PARTS):
        raise ValueError("attempt reference is secret-shaped")
    return value


def _safe_digest(value: str) -> str:
    if not isinstance(value, str) or len(value) != _SHA256_LENGTH or any(char not in "0123456789abcdef" for char in value):
        raise ValueError("attempt digest must be a lowercase SHA-256 digest")
    return value


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True, allow_nan=False)


def _digest_json(value: object) -> str:
    return _digest_text(_canonical_json(value))


def _digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
