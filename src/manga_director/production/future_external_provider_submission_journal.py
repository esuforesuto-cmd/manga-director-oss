"""Private provider-neutral durable submission journal for future external edges.

This successor boundary is deliberately provider-free.  It consumes the
existing D05 capability once, classifies raw D08 evidence inside trusted
composition, persists the pre-edge lifecycle, and returns a process-local
grant.  It never sends a request, reconciles a provider, or applies Generated.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, NoReturn, cast

from pydantic import ConfigDict, field_validator, model_validator

from manga_director.production.director import DirectorModel
from manga_director.production.future_durable_generation_boundary import (
    ProviderDispatchRequestV1,
    ProviderInvocationPermitV1,
)
from manga_director.production.future_generation_admission_contract import (
    GenerationAdmissionManifestV1,
)
from manga_director.production.future_localfile_durable_generation_boundary import (
    LocalFileDurableGenerationBoundary,
)
from manga_director.production.future_provider_capability_profile import (
    ProviderCapabilityClass,
    classify_provider_capabilities,
)
from manga_director.repositories.local_file import LocalFileRepository

_SCHEMA_VERSION = 1
_DATABASE_NAME = "external-provider-submission.sqlite3"
_MAX_ID = 160
_MAX_PROVIDER_ID = 160
_MAX_METADATA_ITEMS = 12
_MAX_METADATA_BYTES = 1536
_MAX_EVENTS = 24
_SECRET_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "password",
    "secret",
    "token",
    "bearer",
)

SubmissionPhase = Literal[
    "DISPATCH_CONSUMED",
    "SUBMISSION_STARTED",
    "EDGE_ISSUED",
    "FAILED_PRE_SEND",
    "REJECTED",
    "ACCEPTED_IDENTIFIED",
    "RECOVERY_REQUIRED",
]
SubmissionStatus = Literal[
    "EDGE_GRANTED",
    "FAILED_PRE_SEND",
    "REJECTED",
    "ACCEPTED_IDENTIFIED",
    "RECOVERY_REQUIRED",
    "CORRUPT",
    "BLOCKED",
    "CONFLICT",
]
ObservationKind = Literal[
    "FAILED_PRE_SEND",
    "REJECTED",
    "ACCEPTED_IDENTIFIED",
    "ACCEPTED_UNIDENTIFIED",
    "AMBIGUOUS",
    "MALFORMED",
    "PROCESS_LOSS",
    "PROVIDER_UNAVAILABLE",
]

_TERMINAL: frozenset[SubmissionPhase] = frozenset(
    {"FAILED_PRE_SEND", "REJECTED", "ACCEPTED_IDENTIFIED", "RECOVERY_REQUIRED"}
)
_ISSUER = object()


class _Model(DirectorModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True, allow_nan=False)


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _logical(value: object, field: str, maximum: int = _MAX_ID) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > maximum
        or any(character.isspace() or ord(character) < 32 for character in value)
        or value.startswith(("/", "\\"))
        or "://" in value
        or ".." in value
        or (len(value) > 2 and value[1] == ":")
        or "@" in value
        or any(part in value.lower() for part in _SECRET_PARTS)
    ):
        raise ValueError(f"external submission {field} is invalid")
    return value


def _sha256(value: object, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"external submission {field} must be SHA-256")
    return value


def _metadata(value: object) -> dict[str, str]:
    if type(value) is not dict:
        raise ValueError("external submission metadata is invalid")
    raw = cast(dict[object, object], value)
    if len(raw) > _MAX_METADATA_ITEMS:
        raise ValueError("external submission metadata is oversized")
    result: dict[str, str] = {}
    for key, item in raw.items():
        if not isinstance(key, str) or not isinstance(item, str):
            raise ValueError("external submission metadata is invalid")
        result[_logical(key, "metadata key", 48)] = _logical(item, "metadata value", 160)
    if len(_canonical(result).encode("utf-8")) > _MAX_METADATA_BYTES:
        raise ValueError("external submission metadata is oversized")
    return dict(sorted(result.items()))


class ExternalProviderSubmissionRequestV1(_Model):
    """Bounded non-secret provider-neutral request identity, never a client."""

    provider_reference: str
    request_digest: str
    metadata: dict[str, str] = {}

    @field_validator("provider_reference")
    @classmethod
    def _provider(cls, value: str) -> str:
        return _logical(value, "provider reference", _MAX_PROVIDER_ID)

    @field_validator("request_digest")
    @classmethod
    def _request_digest(cls, value: str) -> str:
        return _sha256(value, "request digest")

    @field_validator("metadata")
    @classmethod
    def _request_metadata(cls, value: dict[str, str]) -> dict[str, str]:
        return _metadata(value)


class ExternalProviderSubmissionBindingV1(_Model):
    """One immutable successor binding derived only by trusted composition."""

    schema_id: Literal["manga_director.future_external_provider_submission_binding"] = (
        "manga_director.future_external_provider_submission_binding"
    )
    schema_version: Literal["1"] = "1"
    journal_identity: str
    dispatch_identity: str
    idempotency_identity: str
    attempt_id: str
    project_id: str
    page_id: str
    target_page_reference: str
    manifest_digest: str
    provider_binding_digest: str
    attempt_binding_digest: str
    profile_identity: str
    provider_class: ProviderCapabilityClass
    provider_reference: str
    request_digest: str
    metadata_digest: str
    binding_digest: str

    @field_validator(
        "attempt_id", "project_id", "page_id", "target_page_reference", "provider_reference"
    )
    @classmethod
    def _references(cls, value: str) -> str:
        return _logical(value, "binding reference")

    @field_validator(
        "journal_identity", "dispatch_identity", "idempotency_identity", "manifest_digest",
        "provider_binding_digest", "attempt_binding_digest", "profile_identity", "request_digest",
        "metadata_digest", "binding_digest",
    )
    @classmethod
    def _digests(cls, value: str) -> str:
        return _sha256(value, "binding digest")

    @model_validator(mode="after")
    def _integrity(self) -> ExternalProviderSubmissionBindingV1:
        payload = self.model_dump(mode="json", exclude={"journal_identity", "binding_digest"})
        expected = _digest(payload)
        if self.journal_identity != expected or self.binding_digest != expected:
            raise ValueError("external submission binding digest is invalid")
        return self


class ExternalProviderSubmissionObservationV1(_Model):
    """Normalized provider observation.  It grants neither retry nor execution."""

    kind: ObservationKind
    provider_identity: str | None = None
    metadata: dict[str, str] = {}

    @field_validator("provider_identity")
    @classmethod
    def _provider_identity(cls, value: str | None) -> str | None:
        return None if value is None else _logical(value, "provider identity", _MAX_PROVIDER_ID)

    @field_validator("metadata")
    @classmethod
    def _observation_metadata(cls, value: dict[str, str]) -> dict[str, str]:
        return _metadata(value)

    @model_validator(mode="after")
    def _outcome_identity(self) -> ExternalProviderSubmissionObservationV1:
        if self.kind == "ACCEPTED_IDENTIFIED" and self.provider_identity is None:
            raise ValueError("accepted submission requires provider identity")
        if self.kind != "ACCEPTED_IDENTIFIED" and self.provider_identity is not None:
            raise ValueError("provider identity is only retained for accepted submission")
        return self


class _ExternalProviderEdgeGrant:
    """Process-local, non-serializable authority for a future provider adapter."""

    __slots__ = ("_journal_identity", "_dispatch_identity", "_sequence", "_issuer", "_token")

    def __init__(
        self, journal_identity: str, dispatch_identity: str, sequence: int, issuer: object, capability: bytes
    ) -> None:
        self._journal_identity = journal_identity
        self._dispatch_identity = dispatch_identity
        self._sequence = sequence
        self._issuer = issuer
        self._token = capability

    def _matches(
        self, binding: ExternalProviderSubmissionBindingV1, sequence: int, capability: bytes
    ) -> bool:
        return (
            self._issuer is _ISSUER
            and self._journal_identity == binding.journal_identity
            and self._dispatch_identity == binding.dispatch_identity
            and self._sequence == sequence
            and secrets.compare_digest(self._token, capability)
        )

    def __reduce__(self) -> NoReturn:
        raise TypeError("external provider edge grants are not serializable")


@dataclass(frozen=True, slots=True)
class ExternalProviderSubmissionReport:
    status: SubmissionStatus
    phase: SubmissionPhase | None
    binding: ExternalProviderSubmissionBindingV1 | None = None
    edge_grant: _ExternalProviderEdgeGrant | None = None


@dataclass(frozen=True, slots=True)
class _JournalRow:
    binding: ExternalProviderSubmissionBindingV1
    phase: SubmissionPhase
    sequence: int
    terminal_observation: ExternalProviderSubmissionObservationV1 | None


@dataclass(frozen=True, slots=True)
class _GrantRegistration:
    binding: ExternalProviderSubmissionBindingV1
    sequence: int
    capability: bytes


class _ExternalProviderSubmissionJournal:
    """Exact-schema SQLite owner; all replay and schema failures close authority."""

    def __init__(self, owner_root: Path) -> None:
        if not owner_root.is_absolute():
            raise ValueError("external submission owner root is unavailable")
        self._root = owner_root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        self._database = self._root / _DATABASE_NAME
        self._grant_lock = threading.Lock()
        self._issued_grants: dict[_ExternalProviderEdgeGrant, _GrantRegistration] = {}
        self._initialize()

    def begin(self, binding: ExternalProviderSubmissionBindingV1) -> ExternalProviderSubmissionReport:
        try:
            with self._connection() as connection:
                connection.execute("BEGIN IMMEDIATE")
                self._validate_schema(connection)
                existing = self._row(connection, binding.dispatch_identity)
                if existing is not None:
                    if existing.binding != binding:
                        connection.rollback()
                        return ExternalProviderSubmissionReport("CONFLICT", existing.phase, existing.binding)
                    connection.rollback()
                    return self._report(existing)
                self._insert(connection, binding)
                connection.commit()
            self._transition(binding, "DISPATCH_CONSUMED", "SUBMISSION_STARTED")
            issued = self._transition(binding, "SUBMISSION_STARTED", "EDGE_ISSUED")
            if issued is None:
                return ExternalProviderSubmissionReport("CORRUPT", None)
            return ExternalProviderSubmissionReport(
                "EDGE_GRANTED", issued.phase, issued.binding,
                self._issue_grant(issued),
            )
        except Exception:
            return ExternalProviderSubmissionReport("CORRUPT", None)

    def record(
        self, grant: _ExternalProviderEdgeGrant, observation: ExternalProviderSubmissionObservationV1
    ) -> ExternalProviderSubmissionReport:
        if type(grant) is not _ExternalProviderEdgeGrant or type(observation) is not ExternalProviderSubmissionObservationV1:
            return ExternalProviderSubmissionReport("BLOCKED", None)
        try:
            with self._connection() as connection:
                connection.execute("BEGIN IMMEDIATE")
                self._validate_schema(connection)
                row = self._row_by_identity(connection, grant._journal_identity)
                if row is None or row.phase != "EDGE_ISSUED" or not self._consume_grant(grant, row):
                    connection.rollback()
                    return ExternalProviderSubmissionReport("BLOCKED", row.phase if row else None, row.binding if row else None)
                phase = _phase_for_observation(observation)
                updated = self._append(connection, row, phase, observation)
                connection.commit()
                return self._report(updated)
        except Exception:
            return ExternalProviderSubmissionReport("CORRUPT", None)

    def reopen(self, dispatch_identity: str) -> ExternalProviderSubmissionReport:
        try:
            _sha256(dispatch_identity, "dispatch identity")
            with self._connection() as connection:
                self._validate_schema(connection)
                row = self._row(connection, dispatch_identity)
                if row is None:
                    return ExternalProviderSubmissionReport("BLOCKED", None)
                return self._report(row)
        except Exception:
            return ExternalProviderSubmissionReport("CORRUPT", None)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database, timeout=5.0, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode = DELETE")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        exists = self._database.exists()
        connection: sqlite3.Connection | None = None
        try:
            connection = self._connect()
            tables = {
                str(row[0]) for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
                ).fetchall()
            }
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if not exists:
                if version != 0 or tables:
                    raise ValueError("external submission schema is unavailable")
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    "CREATE TABLE external_submission_journal ("
                    "journal_identity TEXT PRIMARY KEY, dispatch_identity TEXT NOT NULL, attempt_id TEXT NOT NULL, "
                    "binding_json TEXT NOT NULL, binding_digest TEXT NOT NULL, phase TEXT NOT NULL, sequence INTEGER NOT NULL, "
                    "terminal_observation_json TEXT, terminal_observation_digest TEXT)"
                )
                connection.execute("CREATE UNIQUE INDEX ux_external_submission_dispatch ON external_submission_journal(dispatch_identity)")
                connection.execute("CREATE UNIQUE INDEX ux_external_submission_attempt ON external_submission_journal(attempt_id)")
                connection.execute(
                    "CREATE TABLE external_submission_events ("
                    "journal_identity TEXT NOT NULL, sequence INTEGER NOT NULL, phase TEXT NOT NULL, payload_json TEXT NOT NULL, "
                    "payload_digest TEXT NOT NULL, PRIMARY KEY (journal_identity, sequence))"
                )
                connection.execute("CREATE INDEX ix_external_submission_events_phase ON external_submission_events(journal_identity, phase)")
                connection.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")
                connection.commit()
            else:
                self._validate_schema(connection)
        except Exception as error:
            if connection is not None:
                try:
                    connection.rollback()
                except sqlite3.Error:
                    pass
            raise ValueError("external submission schema is unavailable") from error
        finally:
            if connection is not None:
                connection.close()

    @classmethod
    def _validate_schema(cls, connection: sqlite3.Connection) -> None:
        if int(connection.execute("PRAGMA user_version").fetchone()[0]) != _SCHEMA_VERSION:
            raise ValueError("external submission schema version is invalid")
        objects = {
            str(row[0]): str(row[1]) for row in connection.execute(
                "SELECT name, type FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
            ).fetchall()
        }
        if objects != {
            "external_submission_journal": "table",
            "external_submission_events": "table",
            "ux_external_submission_dispatch": "index",
            "ux_external_submission_attempt": "index",
            "ix_external_submission_events_phase": "index",
        }:
            raise ValueError("external submission schema objects are invalid")
        cls._table(
            connection, "external_submission_journal",
            (("journal_identity", "TEXT", False, None, 1), ("dispatch_identity", "TEXT", True, None, 0),
             ("attempt_id", "TEXT", True, None, 0), ("binding_json", "TEXT", True, None, 0),
             ("binding_digest", "TEXT", True, None, 0), ("phase", "TEXT", True, None, 0),
             ("sequence", "INTEGER", True, None, 0), ("terminal_observation_json", "TEXT", False, None, 0),
             ("terminal_observation_digest", "TEXT", False, None, 0)),
        )
        cls._table(
            connection, "external_submission_events",
            (("journal_identity", "TEXT", True, None, 1), ("sequence", "INTEGER", True, None, 2),
             ("phase", "TEXT", True, None, 0), ("payload_json", "TEXT", True, None, 0),
             ("payload_digest", "TEXT", True, None, 0)),
        )
        cls._indexes(
            connection,
            "external_submission_journal",
            {
                "sqlite_autoindex_external_submission_journal_1": (True, "pk", False, ("journal_identity",)),
                "ux_external_submission_dispatch": (True, "c", False, ("dispatch_identity",)),
                "ux_external_submission_attempt": (True, "c", False, ("attempt_id",)),
            },
        )
        cls._indexes(
            connection,
            "external_submission_events",
            {
                "sqlite_autoindex_external_submission_events_1": (True, "pk", False, ("journal_identity", "sequence")),
                "ix_external_submission_events_phase": (False, "c", False, ("journal_identity", "phase")),
            },
        )

    @staticmethod
    def _table(
        connection: sqlite3.Connection,
        name: str,
        expected: tuple[tuple[str, str, bool, str | None, int], ...],
    ) -> None:
        rows = tuple(
            (str(row[1]), str(row[2]).upper(), bool(row[3]), None if row[4] is None else str(row[4]), int(row[5]))
            for row in connection.execute(f"PRAGMA table_info({name})")
        )
        if rows != expected:
            raise ValueError("external submission schema columns are invalid")

    @staticmethod
    def _indexes(
        connection: sqlite3.Connection,
        table: str,
        expected: dict[str, tuple[bool, str, bool, tuple[str, ...]]],
    ) -> None:
        indexes = {
            str(row[1]): (bool(row[2]), str(row[3]), bool(row[4]))
            for row in connection.execute(f"PRAGMA index_list({table})")
        }
        if indexes != {name: (unique, origin, partial) for name, (unique, origin, partial, _) in expected.items()}:
            raise ValueError("external submission schema indexes are invalid")
        for name, (_, _, _, columns) in expected.items():
            values = tuple(str(row[2]) for row in connection.execute(f"PRAGMA index_info({name})"))
            if values != columns:
                raise ValueError("external submission schema index order is invalid")

    @staticmethod
    def _insert(connection: sqlite3.Connection, binding: ExternalProviderSubmissionBindingV1) -> None:
        event = _event(binding, 0, "DISPATCH_CONSUMED", None)
        connection.execute(
            "INSERT INTO external_submission_journal VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (binding.journal_identity, binding.dispatch_identity, binding.attempt_id, binding.model_dump_json(),
             binding.binding_digest, "DISPATCH_CONSUMED", 0, None, None),
        )
        connection.execute(
            "INSERT INTO external_submission_events VALUES (?, ?, ?, ?, ?)",
            (binding.journal_identity, 0, "DISPATCH_CONSUMED", _canonical(event), event["event_digest"]),
        )

    def _transition(
        self, binding: ExternalProviderSubmissionBindingV1, expected: SubmissionPhase, target: SubmissionPhase
    ) -> _JournalRow | None:
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._validate_schema(connection)
            row = self._row_by_identity(connection, binding.journal_identity)
            if row is None or row.binding != binding or row.phase != expected or not _legal(expected, target):
                connection.rollback()
                return None
            updated = self._append(connection, row, target, None)
            connection.commit()
            return updated

    def _issue_grant(self, row: _JournalRow) -> _ExternalProviderEdgeGrant:
        capability = secrets.token_bytes(32)
        grant = _ExternalProviderEdgeGrant(
            row.binding.journal_identity, row.binding.dispatch_identity, row.sequence, _ISSUER, capability
        )
        with self._grant_lock:
            self._issued_grants[grant] = _GrantRegistration(row.binding, row.sequence, capability)
        return grant

    def _consume_grant(self, grant: _ExternalProviderEdgeGrant, row: _JournalRow) -> bool:
        with self._grant_lock:
            registration = self._issued_grants.get(grant)
            if registration is None or registration.binding != row.binding or registration.sequence != row.sequence:
                return False
            if not grant._matches(row.binding, row.sequence, registration.capability):
                return False
            del self._issued_grants[grant]
            return True

    def _append(
        self, connection: sqlite3.Connection, row: _JournalRow, target: SubmissionPhase,
        observation: ExternalProviderSubmissionObservationV1 | None,
    ) -> _JournalRow:
        if not _legal(row.phase, target):
            raise ValueError("external submission transition is invalid")
        sequence = row.sequence + 1
        if sequence >= _MAX_EVENTS:
            raise ValueError("external submission event limit exceeded")
        event = _event(row.binding, sequence, target, observation)
        receipt_json: str | None = None
        receipt_digest: str | None = None
        if target in _TERMINAL:
            if observation is None:
                raise ValueError("external submission terminal observation is unavailable")
            receipt_json = observation.model_dump_json()
            receipt_digest = _digest(observation.model_dump(mode="json"))
        updated = connection.execute(
            "UPDATE external_submission_journal SET phase=?, sequence=?, terminal_observation_json=?, terminal_observation_digest=? "
            "WHERE journal_identity=? AND sequence=? AND phase=?",
            (target, sequence, receipt_json, receipt_digest, row.binding.journal_identity, row.sequence, row.phase),
        )
        if updated.rowcount != 1:
            raise ValueError("external submission sequence CAS failed")
        connection.execute(
            "INSERT INTO external_submission_events VALUES (?, ?, ?, ?, ?)",
            (row.binding.journal_identity, sequence, target, _canonical(event), event["event_digest"]),
        )
        return _JournalRow(row.binding, target, sequence, observation if receipt_json is not None else None)

    def _row(self, connection: sqlite3.Connection, dispatch_identity: str) -> _JournalRow | None:
        row = connection.execute(
            "SELECT * FROM external_submission_journal WHERE dispatch_identity=?", (dispatch_identity,)
        ).fetchone()
        return None if row is None else self._replay(connection, row)

    def _row_by_identity(self, connection: sqlite3.Connection, journal_identity: str) -> _JournalRow | None:
        row = connection.execute(
            "SELECT * FROM external_submission_journal WHERE journal_identity=?", (journal_identity,)
        ).fetchone()
        return None if row is None else self._replay(connection, row)

    def _replay(self, connection: sqlite3.Connection, raw: sqlite3.Row) -> _JournalRow:
        try:
            binding = ExternalProviderSubmissionBindingV1.model_validate_json(str(raw["binding_json"]))
            if not self._row_matches_binding(raw, binding):
                raise ValueError("external submission binding mismatch")
            events = connection.execute(
                "SELECT * FROM external_submission_events WHERE journal_identity=? ORDER BY sequence", (binding.journal_identity,)
            ).fetchall()
            previous, observation = self._replay_events(binding, events)
            if previous != raw["phase"] or len(events) - 1 != int(raw["sequence"]):
                raise ValueError("external submission final state is invalid")
            terminal = self._replay_terminal(raw, previous, observation)
            return _JournalRow(binding, previous, int(raw["sequence"]), terminal)
        except Exception as error:
            raise ValueError("external submission replay is invalid") from error

    @staticmethod
    def _row_matches_binding(raw: sqlite3.Row, binding: ExternalProviderSubmissionBindingV1) -> bool:
        return (
            binding.journal_identity == str(raw["journal_identity"])
            and binding.dispatch_identity == str(raw["dispatch_identity"])
            and binding.attempt_id == str(raw["attempt_id"])
            and binding.binding_digest == str(raw["binding_digest"])
        )

    @staticmethod
    def _replay_events(
        binding: ExternalProviderSubmissionBindingV1, events: list[sqlite3.Row]
    ) -> tuple[SubmissionPhase, ExternalProviderSubmissionObservationV1 | None]:
        if not events:
            raise ValueError("external submission events missing")
        previous: SubmissionPhase | None = None
        observation: ExternalProviderSubmissionObservationV1 | None = None
        for expected_sequence, event_row in enumerate(events):
            if int(event_row["sequence"]) != expected_sequence:
                raise ValueError("external submission event sequence is invalid")
            phase = cast(SubmissionPhase, str(event_row["phase"]))
            payload = json.loads(str(event_row["payload_json"]))
            if not isinstance(payload, dict) or _canonical(payload) != event_row["payload_json"]:
                raise ValueError("external submission event payload is invalid")
            if payload.get("event_digest") != event_row["payload_digest"]:
                raise ValueError("external submission event digest is invalid")
            parsed_observation = payload.get("observation")
            if payload != _event(binding, expected_sequence, phase, parsed_observation):
                raise ValueError("external submission event digest is invalid")
            if previous is None and phase != "DISPATCH_CONSUMED":
                raise ValueError("external submission initial event is invalid")
            if previous is not None and not _legal(previous, phase):
                raise ValueError("external submission event transition is invalid")
            if parsed_observation is not None:
                observation = ExternalProviderSubmissionObservationV1.model_validate(parsed_observation)
            previous = phase
        if previous is None:
            raise ValueError("external submission event sequence is invalid")
        return previous, observation

    @staticmethod
    def _replay_terminal(
        raw: sqlite3.Row,
        phase: SubmissionPhase,
        observation: ExternalProviderSubmissionObservationV1 | None,
    ) -> ExternalProviderSubmissionObservationV1 | None:
        terminal = _terminal_from_row(raw)
        if phase in _TERMINAL and (terminal is None or observation != terminal):
            raise ValueError("external submission terminal receipt is invalid")
        if phase not in _TERMINAL and (terminal is not None or observation is not None):
            raise ValueError("external submission nonterminal receipt is invalid")
        return terminal

    @staticmethod
    def _report(row: _JournalRow) -> ExternalProviderSubmissionReport:
        if row.phase == "ACCEPTED_IDENTIFIED":
            return ExternalProviderSubmissionReport("ACCEPTED_IDENTIFIED", row.phase, row.binding)
        if row.phase == "REJECTED":
            return ExternalProviderSubmissionReport("REJECTED", row.phase, row.binding)
        if row.phase == "FAILED_PRE_SEND":
            return ExternalProviderSubmissionReport("FAILED_PRE_SEND", row.phase, row.binding)
        return ExternalProviderSubmissionReport("RECOVERY_REQUIRED", row.phase, row.binding)


class LocalFileExternalProviderSubmissionJournal:
    """The sole supported LocalFile composition for D12-I01; no provider client exists here."""

    def __init__(self, repository: LocalFileRepository) -> None:
        if not isinstance(repository, LocalFileRepository) or not repository._root.is_absolute():
            raise ValueError("trusted LocalFile repository is required")
        root = repository._root.resolve() / "_durability" / "_future_durable_generation" / "external_provider_submission"
        self._d05 = LocalFileDurableGenerationBoundary(repository)
        self._journal = _ExternalProviderSubmissionJournal(root)

    def begin(
        self,
        *,
        manifest: GenerationAdmissionManifestV1,
        permit: ProviderInvocationPermitV1,
        raw_provider_profile: object,
        request: ExternalProviderSubmissionRequestV1,
    ) -> ExternalProviderSubmissionReport:
        try:
            if type(manifest) is not GenerationAdmissionManifestV1 or type(permit) is not ProviderInvocationPermitV1:
                return ExternalProviderSubmissionReport("BLOCKED", None)
            classification = classify_provider_capabilities(raw_provider_profile)
            dispatch = self._d05.consume_for_dispatch(manifest, permit)
            if dispatch is None:
                return ExternalProviderSubmissionReport("BLOCKED", None)
            binding = _binding(dispatch, classification.profile_identity, classification.provider_class, request)
            return self._journal.begin(binding)
        except Exception:
            return ExternalProviderSubmissionReport("BLOCKED", None)

    def record(
        self, grant: _ExternalProviderEdgeGrant, observation: ExternalProviderSubmissionObservationV1
    ) -> ExternalProviderSubmissionReport:
        if not isinstance(grant, _ExternalProviderEdgeGrant) or type(observation) is not ExternalProviderSubmissionObservationV1:
            return ExternalProviderSubmissionReport("BLOCKED", None)
        return self._journal.record(grant, observation)

    def reopen(self, dispatch_identity: str) -> ExternalProviderSubmissionReport:
        return self._journal.reopen(dispatch_identity)


def _binding(
    dispatch: ProviderDispatchRequestV1, profile_identity: str, provider_class: ProviderCapabilityClass,
    request: ExternalProviderSubmissionRequestV1,
) -> ExternalProviderSubmissionBindingV1:
    if type(dispatch) is not ProviderDispatchRequestV1 or request.provider_reference != dispatch.provider_request.provider_reference:
        raise ValueError("external submission provider binding is invalid")
    payload: dict[str, object] = {
        "schema_id": "manga_director.future_external_provider_submission_binding",
        "schema_version": "1",
        "dispatch_identity": dispatch.dispatch_request_identity,
        "idempotency_identity": dispatch.idempotency_identity,
        "attempt_id": dispatch.attempt_id,
        "project_id": dispatch.project_id,
        "page_id": dispatch.page_id,
        "target_page_reference": dispatch.execution_target_reference,
        "manifest_digest": dispatch.manifest_digest,
        "provider_binding_digest": dispatch.provider_binding_digest,
        "attempt_binding_digest": dispatch.attempt_binding_digest,
        "profile_identity": profile_identity,
        "provider_class": provider_class,
        "provider_reference": request.provider_reference,
        "request_digest": request.request_digest,
        "metadata_digest": _digest(request.metadata),
    }
    identity = _digest(payload)
    return ExternalProviderSubmissionBindingV1.model_validate({**payload, "journal_identity": identity, "binding_digest": identity})


def _phase_for_observation(observation: ExternalProviderSubmissionObservationV1) -> SubmissionPhase:
    mapping: dict[ObservationKind, SubmissionPhase] = {
        "FAILED_PRE_SEND": "FAILED_PRE_SEND",
        "REJECTED": "REJECTED",
        "ACCEPTED_IDENTIFIED": "ACCEPTED_IDENTIFIED",
        "ACCEPTED_UNIDENTIFIED": "RECOVERY_REQUIRED",
        "AMBIGUOUS": "RECOVERY_REQUIRED",
        "MALFORMED": "RECOVERY_REQUIRED",
        "PROCESS_LOSS": "RECOVERY_REQUIRED",
        "PROVIDER_UNAVAILABLE": "RECOVERY_REQUIRED",
    }
    return mapping[observation.kind]


def _legal(previous: SubmissionPhase, target: SubmissionPhase) -> bool:
    return (
        (previous == "DISPATCH_CONSUMED" and target == "SUBMISSION_STARTED")
        or (previous == "SUBMISSION_STARTED" and target == "EDGE_ISSUED")
        or (previous == "EDGE_ISSUED" and target in _TERMINAL)
    )


def _event(
    binding: ExternalProviderSubmissionBindingV1, sequence: int, phase: SubmissionPhase,
    observation: object | None,
) -> dict[str, object]:
    parsed = None
    if observation is not None:
        parsed = ExternalProviderSubmissionObservationV1.model_validate(observation).model_dump(mode="json")
    unsigned = {
        "schema_id": "manga_director.future_external_provider_submission_event",
        "schema_version": "1",
        "journal_identity": binding.journal_identity,
        "binding_digest": binding.binding_digest,
        "sequence": sequence,
        "phase": phase,
        "observation": parsed,
    }
    return {**unsigned, "event_digest": _digest(unsigned)}


def _terminal_from_row(row: sqlite3.Row) -> ExternalProviderSubmissionObservationV1 | None:
    payload = row["terminal_observation_json"]
    digest = row["terminal_observation_digest"]
    if payload is None and digest is None:
        return None
    if not isinstance(payload, str) or not isinstance(digest, str):
        raise ValueError("external submission terminal receipt is invalid")
    observation = ExternalProviderSubmissionObservationV1.model_validate_json(payload)
    if _digest(observation.model_dump(mode="json")) != digest:
        raise ValueError("external submission terminal receipt digest is invalid")
    return observation
