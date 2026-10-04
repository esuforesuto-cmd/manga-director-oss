"""Private durable authority for one normal generation attempt.

This module deliberately owns only the pre-provider execution fence.  It does
not select a provider, resolve inputs, or apply workflow state.  A durable
``PROVIDER_STARTED`` record consumes the provider-call opportunity forever.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol, cast

from pydantic import ConfigDict, field_validator

from manga_director.production.director import DirectorModel

AttemptState = Literal["RESERVED", "PROVIDER_STARTED", "PROVIDER_COMPLETED", "COMPLETED"]
AttemptStatus = Literal["reserved", "provider_started", "provider_completed", "completed", "blocked"]
CompletionKind = Literal["provider_declared_failure", "application_event_published"]


class _AttemptModel(DirectorModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class NormalExecutionAttemptReservationDTO(_AttemptModel):
    """The redacted logical identity of one billable normal execution."""

    attempt_id: str
    request_id: str
    project_id: str
    page_id: str
    target_page_reference: str
    provider_reference: str
    execution_fingerprint: str

    @field_validator(
        "attempt_id", "request_id", "project_id", "page_id", "target_page_reference", "provider_reference"
    )
    @classmethod
    def _logical_reference(cls, value: str) -> str:
        if not isinstance(value, str) or not value or value != value.strip():
            raise ValueError("logical reference must be non-empty")
        if any(part in value.lower() for part in ("\\", "/", "://", "api_key", "token", "secret")):
            raise ValueError("logical reference is not safe")
        return value

    @field_validator("execution_fingerprint")
    @classmethod
    def _fingerprint(cls, value: str) -> str:
        if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
            raise ValueError("execution_fingerprint must be a lowercase SHA-256 digest")
        return value


class NormalExecutionAttemptFindingDTO(_AttemptModel):
    code: str
    status: Literal["blocked"]
    message: str
    attempt_id: str = ""
    project_id: str = ""
    page_id: str = ""
    target_page_reference: str = ""


class NormalExecutionAttemptReport(_AttemptModel):
    reservation: NormalExecutionAttemptReservationDTO | None = None
    state: AttemptState | None = None
    completion_kind: CompletionKind | None = None
    findings: tuple[NormalExecutionAttemptFindingDTO, ...] = ()
    status: AttemptStatus
    reservation_confirmed: bool
    provider_invocation_permitted: bool = False


@dataclass(frozen=True, slots=True)
class NormalExecutionAttemptRecord:
    reservation: NormalExecutionAttemptReservationDTO
    state: AttemptState
    completion_kind: CompletionKind | None = None


AttemptStoreOutcome = Literal[
    "reserved", "confirmed", "conflict", "target_conflict", "started", "already_started",
    "provider_completed", "completed", "invalid", "not_found",
]


@dataclass(frozen=True, slots=True)
class NormalExecutionAttemptStoreResult:
    outcome: AttemptStoreOutcome
    record: NormalExecutionAttemptRecord | None = None


class NormalExecutionAttemptStorePort(Protocol):
    def reserve(self, reservation: NormalExecutionAttemptReservationDTO) -> NormalExecutionAttemptStoreResult: ...
    def start_provider(self, reservation: NormalExecutionAttemptReservationDTO) -> NormalExecutionAttemptStoreResult: ...
    def record_provider_success(self, reservation: NormalExecutionAttemptReservationDTO) -> NormalExecutionAttemptStoreResult: ...
    def record_provider_declared_failure(self, reservation: NormalExecutionAttemptReservationDTO) -> NormalExecutionAttemptStoreResult: ...
    def complete_after_application(self, reservation: NormalExecutionAttemptReservationDTO) -> NormalExecutionAttemptStoreResult: ...
    def lookup(self, attempt_id: str) -> NormalExecutionAttemptRecord | None: ...


class NormalExecutionAttemptService:
    """Small fail-closed facade over a private durable Attempt Authority store."""

    def reserve(self, reservation: NormalExecutionAttemptReservationDTO, store: NormalExecutionAttemptStorePort) -> NormalExecutionAttemptReport:
        return self._operation(reservation, store, "reserve")

    def begin_provider(self, reservation: NormalExecutionAttemptReservationDTO, store: NormalExecutionAttemptStorePort) -> NormalExecutionAttemptReport:
        return self._operation(reservation, store, "start_provider")

    def record_provider_success(self, reservation: NormalExecutionAttemptReservationDTO, store: NormalExecutionAttemptStorePort) -> NormalExecutionAttemptReport:
        return self._operation(reservation, store, "record_provider_success")

    def record_provider_declared_failure(self, reservation: NormalExecutionAttemptReservationDTO, store: NormalExecutionAttemptStorePort) -> NormalExecutionAttemptReport:
        return self._operation(reservation, store, "record_provider_declared_failure")

    def complete_after_application(self, reservation: NormalExecutionAttemptReservationDTO, store: NormalExecutionAttemptStorePort) -> NormalExecutionAttemptReport:
        return self._operation(reservation, store, "complete_after_application")

    def lookup(self, attempt_id: str, store: NormalExecutionAttemptStorePort) -> NormalExecutionAttemptReport:
        try:
            record = store.lookup(attempt_id)
        except Exception:
            return _blocked(None, "ATTEMPT_STORE_UNAVAILABLE")
        return _report(record, "confirmed") if record is not None else _blocked(None, "ATTEMPT_NOT_FOUND")

    def _operation(self, reservation: NormalExecutionAttemptReservationDTO, store: NormalExecutionAttemptStorePort, method: str) -> NormalExecutionAttemptReport:
        try:
            result = getattr(store, method)(reservation)
        except Exception:
            return _blocked(reservation, "ATTEMPT_STORE_UNAVAILABLE")
        if result.outcome in {"conflict", "target_conflict", "invalid", "not_found"}:
            return _blocked(reservation, f"ATTEMPT_{result.outcome.upper()}")
        if result.record is None:
            return _blocked(reservation, "ATTEMPT_STORE_INVALID_RESULT")
        return _report(result.record, result.outcome)


def derive_execution_fingerprint(projection: Mapping[str, object]) -> str:
    """Hash only a canonical, redacted logical execution projection."""

    encoded = json.dumps(
        _canonical_projection(projection), ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _canonical_projection(value: object) -> object:
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key in sorted(value):
            if not isinstance(key, str) or any(token in key.lower() for token in ("prompt", "secret", "credential", "payload", "bytes", "path", "url", "header")):
                raise ValueError("unsafe execution fingerprint projection")
            result[key] = _canonical_projection(value[key])
        return result
    if isinstance(value, (tuple, list, set, frozenset)):
        normalized = [_canonical_projection(item) for item in value]
        return sorted(normalized, key=lambda item: json.dumps(item, separators=(",", ":"), sort_keys=True))
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ValueError("execution fingerprint projection must be logical JSON")


class LocalNormalExecutionAttemptStore:
    """Private SQLite sidecar; only redacted logical bindings are durable."""

    _SCHEMA_VERSION = 1

    def __init__(self, root: Path) -> None:
        if not root.is_absolute():
            raise ValueError("attempt-store root must be absolute")
        self._root = root
        self._database = root / "normal_execution_attempts.sqlite3"

    def reserve(self, reservation: NormalExecutionAttemptReservationDTO) -> NormalExecutionAttemptStoreResult:
        with self._transaction() as connection:
            existing = self._read(connection, reservation.attempt_id)
            if existing is not None:
                return NormalExecutionAttemptStoreResult("confirmed" if existing.reservation == reservation else "conflict", existing)
            try:
                connection.execute(
                    "INSERT INTO normal_execution_attempts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    _row(reservation, "RESERVED"),
                )
            except sqlite3.IntegrityError:
                return NormalExecutionAttemptStoreResult("target_conflict")
            return NormalExecutionAttemptStoreResult("reserved", NormalExecutionAttemptRecord(reservation, "RESERVED"))

    def start_provider(self, reservation: NormalExecutionAttemptReservationDTO) -> NormalExecutionAttemptStoreResult:
        return self._transition(reservation, "RESERVED", "PROVIDER_STARTED", None, "started", "already_started")

    def record_provider_success(self, reservation: NormalExecutionAttemptReservationDTO) -> NormalExecutionAttemptStoreResult:
        return self._transition(reservation, "PROVIDER_STARTED", "PROVIDER_COMPLETED", None, "provider_completed", "invalid")

    def record_provider_declared_failure(self, reservation: NormalExecutionAttemptReservationDTO) -> NormalExecutionAttemptStoreResult:
        return self._transition(reservation, "PROVIDER_STARTED", "COMPLETED", "provider_declared_failure", "completed", "invalid")

    def complete_after_application(self, reservation: NormalExecutionAttemptReservationDTO) -> NormalExecutionAttemptStoreResult:
        return self._transition(reservation, "PROVIDER_COMPLETED", "COMPLETED", "application_event_published", "completed", "invalid")

    def lookup(self, attempt_id: str) -> NormalExecutionAttemptRecord | None:
        self._initialize()
        with sqlite3.connect(self._database) as connection:
            return self._read(connection, attempt_id)

    def _transition(self, reservation: NormalExecutionAttemptReservationDTO, expected: AttemptState, target: AttemptState, completion: CompletionKind | None, success: AttemptStoreOutcome, already: AttemptStoreOutcome) -> NormalExecutionAttemptStoreResult:
        with self._transaction() as connection:
            existing = self._read(connection, reservation.attempt_id)
            if existing is None:
                return NormalExecutionAttemptStoreResult("not_found")
            if existing.reservation != reservation:
                return NormalExecutionAttemptStoreResult("conflict", existing)
            if existing.state != expected:
                return NormalExecutionAttemptStoreResult(already if existing.state == target else "invalid", existing)
            connection.execute("UPDATE normal_execution_attempts SET state=?, completion_kind=? WHERE attempt_id=?", (target, completion, reservation.attempt_id))
            return NormalExecutionAttemptStoreResult(success, NormalExecutionAttemptRecord(reservation, target, completion))

    def _initialize(self) -> None:
        self._root.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._database) as connection:
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("CREATE TABLE IF NOT EXISTS normal_execution_attempt_schema (version INTEGER NOT NULL)")
            row = connection.execute("SELECT version FROM normal_execution_attempt_schema").fetchone()
            if row is None:
                connection.execute("INSERT INTO normal_execution_attempt_schema VALUES (?)", (self._SCHEMA_VERSION,))
            elif row[0] != self._SCHEMA_VERSION:
                raise RuntimeError("unsupported attempt-store schema")
            connection.execute("""CREATE TABLE IF NOT EXISTS normal_execution_attempts (
                attempt_id TEXT PRIMARY KEY, request_id TEXT NOT NULL, project_id TEXT NOT NULL,
                page_id TEXT NOT NULL, target_page_reference TEXT NOT NULL, provider_reference TEXT NOT NULL,
                execution_fingerprint TEXT NOT NULL, state TEXT NOT NULL, completion_kind TEXT NULL)""")
            connection.execute("""CREATE UNIQUE INDEX IF NOT EXISTS active_normal_execution_target
                ON normal_execution_attempts(project_id, page_id, target_page_reference)
                WHERE state <> 'COMPLETED'""")

    def _transaction(self) -> AbstractContextManager[sqlite3.Connection]:
        self._initialize()
        connection = sqlite3.connect(self._database, isolation_level=None)
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("BEGIN IMMEDIATE")
        return _Transaction(connection)

    @staticmethod
    def _read(connection: sqlite3.Connection, attempt_id: str) -> NormalExecutionAttemptRecord | None:
        row = connection.execute("SELECT * FROM normal_execution_attempts WHERE attempt_id=?", (attempt_id,)).fetchone()
        if row is None:
            return None
        reservation = NormalExecutionAttemptReservationDTO(**dict(zip(("attempt_id", "request_id", "project_id", "page_id", "target_page_reference", "provider_reference", "execution_fingerprint"), row[:7], strict=True)))
        return NormalExecutionAttemptRecord(reservation, row[7], row[8])


class _Transaction:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
    def __enter__(self) -> sqlite3.Connection:
        return self._connection
    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self._connection.execute("COMMIT" if exc_type is None else "ROLLBACK")
        self._connection.close()


def _row(reservation: NormalExecutionAttemptReservationDTO, state: AttemptState) -> tuple[str | None, ...]:
    return (*reservation.model_dump().values(), state, None)


def _report(record: NormalExecutionAttemptRecord, outcome: str) -> NormalExecutionAttemptReport:
    state = record.state
    return NormalExecutionAttemptReport(
        reservation=record.reservation, state=state, completion_kind=record.completion_kind,
        status=cast(AttemptStatus, {"RESERVED": "reserved", "PROVIDER_STARTED": "provider_started", "PROVIDER_COMPLETED": "provider_completed", "COMPLETED": "completed"}[state]),
        reservation_confirmed=True,
        provider_invocation_permitted=outcome == "started" and state == "PROVIDER_STARTED",
    )


def _blocked(reservation: NormalExecutionAttemptReservationDTO | None, code: str) -> NormalExecutionAttemptReport:
    values = reservation.model_dump() if reservation is not None else {}
    finding = NormalExecutionAttemptFindingDTO(code=code, status="blocked", message="attempt authority rejected the request", **{key: values.get(key, "") for key in ("attempt_id", "project_id", "page_id", "target_page_reference")})
    return NormalExecutionAttemptReport(reservation=reservation, findings=(finding,), status="blocked", reservation_confirmed=False)
