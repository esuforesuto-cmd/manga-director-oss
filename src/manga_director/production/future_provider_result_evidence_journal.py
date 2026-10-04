"""Private D09-I02 provider-free durable result evidence journal.

This module consumes only owner-read, replay-validated D09-I01 accepted
histories.  It never invokes a provider, changes a workflow, or exposes a
public API.  Every result it can emit has UNVERIFIED provider origin.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import ConfigDict, Field, field_validator

from manga_director.production import future_fake_provider_receipt_journal as d09
from manga_director.production.director import DirectorModel
from manga_director.repositories.local_file import LocalFileRepository

ProviderOriginAssurance = Literal["UNVERIFIED", "AUTHENTICATED"]
ResultStatus = Literal[
    "RESULT_NOT_AVAILABLE",
    "RESULT_CAPTURED",
    "RESULT_REJECTED",
    "RESULT_MALFORMED",
    "RESULT_AMBIGUOUS",
    "RECOVERY_REQUIRED",
    "CORRUPT",
]
_Phase = Literal[
    "RESERVED",
    "CAPTURE_STARTED",
    "OBSERVATION_RECORDED",
    "RESULT_CAPTURED",
    "RESULT_REJECTED",
    "RESULT_MALFORMED",
    "CONFLICT_RECORDED",
    "RECOVERY_REQUIRED",
]
_EventType = _Phase

_SCHEMA_VERSION = 1
_DATABASE_NAME = "future-provider-result-evidence.sqlite3"
_MAX_LOGICAL_ID = 96
_MAX_PROVIDER_ID = 160
_MAX_OUTPUTS = 4
_MAX_METADATA_ENTRIES = 16
_MAX_METADATA_KEY_BYTES = 48
_MAX_METADATA_VALUE_BYTES = 256
_MAX_METADATA_BYTES = 2048
_MAX_EVENTS = 32
_MAX_EVENT_BYTES = 8192
_MEDIA_TYPES = frozenset({"image/png", "image/jpeg", "image/webp"})
_SECRET_PARTS = ("api_key", "apikey", "authorization", "credential", "password", "secret", "token", "bearer")


class _StrictModel(DirectorModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True, allow_nan=False)


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _sha256(value: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ValueError("D09-I02 requires lowercase SHA-256 digests")
    return value


def _logical(value: str, *, maximum: int = _MAX_LOGICAL_ID) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > maximum
        or any(char.isspace() or ord(char) < 32 for char in value)
        or value.startswith(("/", "\\"))
        or ".." in value
        or "://" in value
        or (len(value) > 2 and value[1] == ":")
    ):
        raise ValueError("D09-I02 requires bounded logical identifiers")
    lowered = value.lower()
    if any(part in lowered for part in _SECRET_PARTS) or "@" in value:
        raise ValueError("D09-I02 rejects secret-shaped logical identifiers")
    return value


def _safe_text(value: str, *, maximum: int) -> str:
    if not isinstance(value, str) or len(value.encode("utf-8")) > maximum or any(ord(char) < 32 for char in value):
        raise ValueError("D09-I02 metadata value is invalid")
    lowered = value.lower()
    if (
        any(part in lowered for part in _SECRET_PARTS)
        or "://" in value
        or "?" in value
        or value.startswith(("/", "\\"))
        or "\\" in value
        or "/" in value
        or ".." in value
        or (len(value) > 2 and value[1] == ":")
    ):
        raise ValueError("D09-I02 metadata contains a forbidden value")
    return value


def _metadata(value: object) -> dict[str, str]:
    if type(value) is not dict:
        raise ValueError("D09-I02 metadata must be a primitive flat mapping")
    raw = cast(dict[object, object], value)
    if len(raw) > _MAX_METADATA_ENTRIES:
        raise ValueError("D09-I02 metadata has too many entries")
    result: dict[str, str] = {}
    for key, item in raw.items():
        if not isinstance(key, str) or not isinstance(item, str):
            raise ValueError("D09-I02 metadata must contain strings only")
        safe_key = _safe_text(key, maximum=_MAX_METADATA_KEY_BYTES)
        safe_value = _safe_text(item, maximum=_MAX_METADATA_VALUE_BYTES)
        result[safe_key] = safe_value
    if len(result) != len(raw) or len(_canonical(result).encode("utf-8")) > _MAX_METADATA_BYTES:
        raise ValueError("D09-I02 metadata is oversized or ambiguous")
    return dict(sorted(result.items()))


class OutputEvidenceV1(_StrictModel):
    """One bounded logical output; it is not an asset capability."""

    logical_output_id: str
    sha256: str
    media_type: Literal["image/png", "image/jpeg", "image/webp"]
    metadata: dict[str, str]
    metadata_digest: str

    @field_validator("logical_output_id")
    @classmethod
    def _output_id(cls, value: str) -> str:
        return _logical(value)

    @field_validator("sha256", "metadata_digest")
    @classmethod
    def _output_digest(cls, value: str) -> str:
        return _sha256(value)

    @field_validator("metadata")
    @classmethod
    def _output_metadata(cls, value: dict[str, str]) -> dict[str, str]:
        return _metadata(value)

    def model_post_init(self, __context: object) -> None:
        if self.media_type not in _MEDIA_TYPES or self.metadata_digest != _digest(self.metadata):
            raise ValueError("D09-I02 output evidence is invalid")


class ProviderResultEvidenceV1(_StrictModel):
    """Private immutable result evidence; it has zero operational authority."""

    schema_id: Literal["manga_director.future_provider_result_evidence"] = "manga_director.future_provider_result_evidence"
    schema_version: Literal["1"] = "1"
    provider_origin_assurance: ProviderOriginAssurance
    project_id: str
    page_id: str
    execution_target_reference: str
    attempt_id: str
    manifest_digest: str
    dispatch_identity: str
    idempotency_identity: str
    attempt_binding_digest: str
    provider_binding_digest: str
    journal_identity: str
    receipt_identity: str
    receipt_digest: str
    receipt_sequence: int = Field(ge=1)
    submission_evidence_digest: str
    profile_identity: str
    provider_class: Literal["A", "B", "C"]
    provider_identifier: str
    provider_job_identity: str | None = None
    output_evidence: tuple[OutputEvidenceV1, ...]
    capture_mode: Literal["FAKE_OBSERVATION"]
    capture_metadata: dict[str, str]
    capture_metadata_digest: str
    evidence_identity: str
    evidence_digest: str

    @field_validator("project_id", "page_id", "execution_target_reference", "attempt_id")
    @classmethod
    def _reference(cls, value: str) -> str:
        return _logical(value, maximum=_MAX_PROVIDER_ID)

    @field_validator("provider_identifier", "provider_job_identity")
    @classmethod
    def _provider_reference(cls, value: str | None) -> str | None:
        return None if value is None else _logical(value, maximum=_MAX_PROVIDER_ID)

    @field_validator(
        "manifest_digest", "dispatch_identity", "idempotency_identity", "attempt_binding_digest", "provider_binding_digest",
        "journal_identity", "receipt_identity", "receipt_digest", "submission_evidence_digest", "profile_identity",
        "capture_metadata_digest", "evidence_identity", "evidence_digest",
    )
    @classmethod
    def _evidence_digest(cls, value: str) -> str:
        return _sha256(value)

    @field_validator("capture_metadata")
    @classmethod
    def _capture_metadata(cls, value: dict[str, str]) -> dict[str, str]:
        return _metadata(value)

    @field_validator("output_evidence")
    @classmethod
    def _outputs(cls, value: tuple[OutputEvidenceV1, ...]) -> tuple[OutputEvidenceV1, ...]:
        if not 1 <= len(value) <= _MAX_OUTPUTS:
            raise ValueError("D09-I02 output count is invalid")
        ordered = tuple(sorted(value, key=lambda item: item.logical_output_id))
        if ordered != value or len({item.logical_output_id for item in value}) != len(value) or len({item.sha256 for item in value}) != len(value):
            raise ValueError("D09-I02 output evidence is ambiguous")
        return value

    def model_post_init(self, __context: object) -> None:
        if self.provider_origin_assurance != "UNVERIFIED" or self.capture_metadata_digest != _digest(self.capture_metadata):
            raise ValueError("D09-I02 cannot issue authenticated provenance")
        payload = self.model_dump(mode="json", exclude={"evidence_identity", "evidence_digest"})
        if self.evidence_identity != _digest(payload) or self.evidence_digest != self.evidence_identity:
            raise ValueError("D09-I02 evidence digest is invalid")


@dataclass(frozen=True, slots=True)
class ProviderResultJournalReport:
    status: ResultStatus
    evidence: ProviderResultEvidenceV1 | None = None


@dataclass(frozen=True, slots=True)
class _I01Accepted:
    binding: d09.D09DispatchBindingV1
    receipt: d09.ProviderSubmissionReceiptV1
    receipt_identity: str


class _I01Reader:
    """Read only the frozen I01 schema and replay validators; never opens it writable."""

    def __init__(self, repository: LocalFileRepository) -> None:
        root = repository._root
        if not root.is_absolute():
            raise ValueError("trusted LocalFile durability root is unavailable")
        self._database = root.resolve() / "_durability" / "_future_durable_generation" / "provider_receipts" / "fake_provider_receipts.sqlite3"

    def accepted(self, attempt_id: str) -> _I01Accepted | None:
        try:
            _logical(attempt_id, maximum=_MAX_PROVIDER_ID)
            if not self._database.is_file():
                return None
            connection = sqlite3.connect(f"{self._database.as_uri()}?mode=ro", uri=True)
            connection.row_factory = sqlite3.Row
            try:
                d09._LocalFakeProviderReceiptJournal._validate_schema(connection)
                d09._LocalFakeProviderReceiptJournal._validate_schema_version(connection)
                matches: list[_I01Accepted] = []
                for row in connection.execute("SELECT * FROM d09_journals").fetchall():
                    binding = d09.D09DispatchBindingV1.model_validate_json(cast(str, row["binding_json"]))
                    if binding.attempt_id != attempt_id or row["lifecycle"] != "ACCEPTED":
                        continue
                    sequence = int(row["sequence"])
                    receipt = d09._replayed_receipt(row, binding, "ACCEPTED", sequence)
                    d09._validate_replayed_events(connection, binding, "ACCEPTED", sequence)
                    if receipt is None or receipt.lifecycle != "ACCEPTED":
                        raise ValueError("accepted I01 receipt is unavailable")
                    matches.append(_I01Accepted(binding, receipt, _digest(receipt.model_dump(mode="json"))))
                return matches[0] if len(matches) == 1 else None
            finally:
                connection.close()
        except Exception:
            return None


class _ResultJournal:
    """Private exact-schema SQLite journal; all errors are fail-closed."""

    def __init__(self, owner_root: Path) -> None:
        if not owner_root.is_absolute():
            raise ValueError("D09-I02 requires a trusted absolute owner root")
        self._root = owner_root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        self._database = self._root / _DATABASE_NAME
        self._initialize()

    def capture(self, source: _I01Accepted, observation: object) -> ProviderResultJournalReport:
        try:
            existing = self._reserve(source)
            if existing is not None:
                return self._after_existing(source, observation, existing)
            self._transition(source, "RESERVED", "CAPTURE_STARTED", None)
            parsed = _observation(observation, source)
            self._transition(source, "CAPTURE_STARTED", "OBSERVATION_RECORDED", _digest(parsed))
            evidence = _evidence(source, parsed)
            return self._accept(source, evidence)
        except ValueError:
            try:
                state, _ = self._state(source)
                if state is not None and state[0] in {"RESERVED", "CAPTURE_STARTED", "OBSERVATION_RECORDED"}:
                    self._transition(source, cast(_Phase, state[0]), "RESULT_MALFORMED", None)
            except Exception:
                return ProviderResultJournalReport("CORRUPT")
            return ProviderResultJournalReport("RESULT_MALFORMED")
        except Exception:
            return ProviderResultJournalReport("CORRUPT")

    def reopen(self, source: _I01Accepted) -> ProviderResultJournalReport:
        try:
            state, evidence = self._state(source)
            if state is None:
                return ProviderResultJournalReport("RESULT_NOT_AVAILABLE")
            phase, gate, _ = state
            if phase in {"CAPTURE_STARTED", "OBSERVATION_RECORDED", "CONFLICT_RECORDED"}:
                self._transition(source, cast(_Phase, phase), "RECOVERY_REQUIRED", None)
                return ProviderResultJournalReport("RECOVERY_REQUIRED")
            if phase == "RECOVERY_REQUIRED":
                return ProviderResultJournalReport("RECOVERY_REQUIRED")
            if phase == "RESULT_CAPTURED" and gate == "CLEAR" and evidence is not None:
                return ProviderResultJournalReport("RESULT_CAPTURED", evidence)
            if phase == "RESULT_CAPTURED":
                return ProviderResultJournalReport("RECOVERY_REQUIRED")
            if phase == "RESULT_REJECTED":
                return ProviderResultJournalReport("RESULT_REJECTED")
            if phase == "RESULT_MALFORMED":
                return ProviderResultJournalReport("RESULT_MALFORMED")
            return ProviderResultJournalReport("CORRUPT")
        except Exception:
            return ProviderResultJournalReport("CORRUPT")

    def _after_existing(self, source: _I01Accepted, observation: object, state: tuple[str, str, int]) -> ProviderResultJournalReport:
        phase, gate, _ = state
        if phase == "RESULT_CAPTURED" and gate == "CLEAR":
            current = self._accepted(source)
            if current is None:
                return ProviderResultJournalReport("CORRUPT")
            try:
                candidate = _evidence(source, _observation(observation, source))
            except ValueError:
                return ProviderResultJournalReport("RESULT_MALFORMED")
            if candidate == current:
                return ProviderResultJournalReport("RESULT_CAPTURED", current)
            self._transition(
                source,
                "RESULT_CAPTURED",
                "CONFLICT_RECORDED",
                _digest(candidate.model_dump(mode="json")),
                gate="CLOSED",
            )
            return ProviderResultJournalReport("RESULT_AMBIGUOUS")
        if phase in {"RESERVED", "CAPTURE_STARTED", "OBSERVATION_RECORDED"}:
            # A concurrent writer may still commit an immutable result.  This
            # caller must not turn that live operation into recovery.
            return ProviderResultJournalReport("RECOVERY_REQUIRED")
        return self.reopen(source)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database, timeout=5.0, isolation_level=None)
        connection.row_factory = sqlite3.Row
        if str(connection.execute("PRAGMA journal_mode = DELETE").fetchone()[0]).lower() != "delete":
            raise ValueError("D09-I02 journal mode is unavailable")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    def _initialize(self) -> None:
        existed = self._database.exists()
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                objects = {(row["type"], row["name"]) for row in connection.execute("SELECT type, name FROM sqlite_master WHERE type IN ('table','index') AND name NOT LIKE 'sqlite_%'")}
                if existed and objects:
                    self._validate_schema(connection)
                    connection.commit()
                    return
                if existed and not objects:
                    raise ValueError("D09-I02 store is partial")
                connection.execute("CREATE TABLE d09i02_schema_meta (version INTEGER NOT NULL PRIMARY KEY)")
                connection.execute("INSERT INTO d09i02_schema_meta VALUES (1)")
                connection.execute("CREATE TABLE d09i02_journal_bindings (journal_identity TEXT NOT NULL PRIMARY KEY, receipt_identity TEXT NOT NULL, binding_json TEXT NOT NULL, binding_digest TEXT NOT NULL)")
                connection.execute("CREATE UNIQUE INDEX d09i02_receipt_identity_unique ON d09i02_journal_bindings(receipt_identity)")
                connection.execute("CREATE TABLE d09i02_journal_state (journal_identity TEXT NOT NULL PRIMARY KEY, phase TEXT NOT NULL, availability_gate TEXT NOT NULL, sequence INTEGER NOT NULL, last_event_digest TEXT NOT NULL)")
                connection.execute("CREATE TABLE d09i02_events (journal_identity TEXT NOT NULL, sequence INTEGER NOT NULL, event_type TEXT NOT NULL, event_json TEXT NOT NULL, event_digest TEXT NOT NULL, PRIMARY KEY (journal_identity, sequence))")
                connection.execute("CREATE TABLE d09i02_accepted_results (journal_identity TEXT NOT NULL PRIMARY KEY, result_identity TEXT NOT NULL, evidence_json TEXT NOT NULL, evidence_digest TEXT NOT NULL)")
                connection.execute("CREATE UNIQUE INDEX d09i02_result_identity_unique ON d09i02_accepted_results(result_identity)")
                self._validate_schema(connection)
                connection.commit()
        except (OSError, sqlite3.Error, ValueError) as error:
            raise ValueError("D09-I02 journal is unavailable") from error

    @staticmethod
    def _validate_schema(connection: sqlite3.Connection) -> None:
        required = {("table", "d09i02_schema_meta"), ("table", "d09i02_journal_bindings"), ("table", "d09i02_journal_state"), ("table", "d09i02_events"), ("table", "d09i02_accepted_results"), ("index", "d09i02_receipt_identity_unique"), ("index", "d09i02_result_identity_unique")}
        actual = {(row["type"], row["name"]) for row in connection.execute("SELECT type, name FROM sqlite_master WHERE type IN ('table','index') AND name NOT LIKE 'sqlite_%'")}
        versions = [int(row["version"]) for row in connection.execute("SELECT version FROM d09i02_schema_meta")]
        if actual != required or versions != [_SCHEMA_VERSION]:
            raise ValueError("D09-I02 schema is invalid")
        expected = {"d09i02_schema_meta": {"version"}, "d09i02_journal_bindings": {"journal_identity", "receipt_identity", "binding_json", "binding_digest"}, "d09i02_journal_state": {"journal_identity", "phase", "availability_gate", "sequence", "last_event_digest"}, "d09i02_events": {"journal_identity", "sequence", "event_type", "event_json", "event_digest"}, "d09i02_accepted_results": {"journal_identity", "result_identity", "evidence_json", "evidence_digest"}}
        primary_keys = {"d09i02_schema_meta": [("version", 1)], "d09i02_journal_bindings": [("journal_identity", 1)], "d09i02_journal_state": [("journal_identity", 1)], "d09i02_events": [("journal_identity", 1), ("sequence", 2)], "d09i02_accepted_results": [("journal_identity", 1)]}
        for table, columns in expected.items():
            metadata = connection.execute(f"PRAGMA table_info({table})").fetchall()
            actual_primary_key = [(str(row["name"]), int(row["pk"])) for row in metadata if int(row["pk"]) > 0]
            if {row["name"] for row in metadata} != columns or actual_primary_key != primary_keys[table]:
                raise ValueError("D09-I02 table schema is invalid")
        for table, index, index_columns in (("d09i02_journal_bindings", "d09i02_receipt_identity_unique", ["receipt_identity"]), ("d09i02_accepted_results", "d09i02_result_identity_unique", ["result_identity"])):
            indexes = {row["name"]: row["unique"] for row in connection.execute(f"PRAGMA index_list({table})")}
            if indexes.get(index) != 1 or [row["name"] for row in connection.execute(f"PRAGMA index_info({index})")] != index_columns:
                raise ValueError("D09-I02 unique index is invalid")

    def _reserve(self, source: _I01Accepted) -> tuple[str, str, int] | None:
        binding = _binding(source)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._validate_schema(connection)
            rows = connection.execute("SELECT * FROM d09i02_journal_bindings WHERE receipt_identity = ?", (source.receipt_identity,)).fetchall()
            if rows:
                row = rows[0]
                if row["binding_digest"] != _digest(binding) or row["binding_json"] != _canonical(binding):
                    raise ValueError("D09-I02 binding conflict")
                state = connection.execute("SELECT * FROM d09i02_journal_state WHERE journal_identity = ?", (source.binding.binding_identity,)).fetchone()
                if state is None:
                    raise ValueError("D09-I02 state is missing")
                connection.commit()
                return str(state["phase"]), str(state["availability_gate"]), int(state["sequence"])
            connection.execute("INSERT INTO d09i02_journal_bindings VALUES (?, ?, ?, ?)", (source.binding.binding_identity, source.receipt_identity, _canonical(binding), _digest(binding)))
            event = _event(source, 0, "RESERVED", "", "")
            connection.execute("INSERT INTO d09i02_events VALUES (?, ?, ?, ?, ?)", (source.binding.binding_identity, 0, "RESERVED", _canonical(event), event["event_digest"]))
            connection.execute("INSERT INTO d09i02_journal_state VALUES (?, ?, ?, ?, ?)", (source.binding.binding_identity, "RESERVED", "CLEAR", 0, event["event_digest"]))
            connection.commit()
            return None

    def _transition(self, source: _I01Accepted, expected: _Phase, target: _Phase, payload_digest: str | None, *, gate: str = "CLEAR") -> None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._validate_schema(connection)
            state = connection.execute("SELECT * FROM d09i02_journal_state WHERE journal_identity = ?", (source.binding.binding_identity,)).fetchone()
            if state is None or state["phase"] != expected or not _legal(expected, target):
                raise ValueError("D09-I02 transition is invalid")
            sequence = int(state["sequence"]) + 1
            event = _event(source, sequence, target, str(state["last_event_digest"]), payload_digest or "")
            if len(_canonical(event).encode("utf-8")) > _MAX_EVENT_BYTES or sequence >= _MAX_EVENTS:
                raise ValueError("D09-I02 event limit exceeded")
            updated = connection.execute("UPDATE d09i02_journal_state SET phase=?, availability_gate=?, sequence=?, last_event_digest=? WHERE journal_identity=? AND sequence=?", (target, gate, sequence, event["event_digest"], source.binding.binding_identity, int(state["sequence"])))
            if updated.rowcount != 1:
                raise ValueError("D09-I02 sequence CAS failed")
            connection.execute("INSERT INTO d09i02_events VALUES (?, ?, ?, ?, ?)", (source.binding.binding_identity, sequence, target, _canonical(event), event["event_digest"]))
            connection.commit()

    def _accept(self, source: _I01Accepted, evidence: ProviderResultEvidenceV1) -> ProviderResultJournalReport:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._validate_schema(connection)
            state = connection.execute("SELECT * FROM d09i02_journal_state WHERE journal_identity = ?", (source.binding.binding_identity,)).fetchone()
            if state is None or state["phase"] != "OBSERVATION_RECORDED":
                raise ValueError("D09-I02 acceptance is unavailable")
            sequence = int(state["sequence"]) + 1
            event = _event(source, sequence, "RESULT_CAPTURED", str(state["last_event_digest"]), evidence.evidence_digest)
            connection.execute("INSERT INTO d09i02_accepted_results VALUES (?, ?, ?, ?)", (source.binding.binding_identity, evidence.evidence_identity, evidence.model_dump_json(), evidence.evidence_digest))
            updated = connection.execute("UPDATE d09i02_journal_state SET phase='RESULT_CAPTURED', sequence=?, last_event_digest=? WHERE journal_identity=? AND sequence=?", (sequence, event["event_digest"], source.binding.binding_identity, int(state["sequence"])))
            if updated.rowcount != 1:
                raise ValueError("D09-I02 acceptance CAS failed")
            connection.execute("INSERT INTO d09i02_events VALUES (?, ?, ?, ?, ?)", (source.binding.binding_identity, sequence, "RESULT_CAPTURED", _canonical(event), event["event_digest"]))
            connection.commit()
            return ProviderResultJournalReport("RESULT_CAPTURED", evidence)

    def _state(self, source: _I01Accepted) -> tuple[tuple[str, str, int] | None, ProviderResultEvidenceV1 | None]:
        with self._connect() as connection:
            self._validate_schema(connection)
            row = connection.execute("SELECT * FROM d09i02_journal_state WHERE journal_identity = ?", (source.binding.binding_identity,)).fetchone()
            if row is None:
                return None, None
            self._replay(connection, source, row)
            return (str(row["phase"]), str(row["availability_gate"]), int(row["sequence"])), self._accepted(source, connection)

    def _accepted(self, source: _I01Accepted, connection: sqlite3.Connection | None = None) -> ProviderResultEvidenceV1 | None:
        own = connection is None
        active = connection or self._connect()
        try:
            self._validate_schema(active)
            row = active.execute("SELECT * FROM d09i02_accepted_results WHERE journal_identity = ?", (source.binding.binding_identity,)).fetchone()
            if row is None:
                return None
            evidence = ProviderResultEvidenceV1.model_validate_json(cast(str, row["evidence_json"]))
            if evidence.evidence_identity != row["result_identity"] or evidence.evidence_digest != row["evidence_digest"] or not _matches(source, evidence):
                raise ValueError("D09-I02 accepted result is corrupt")
            return evidence
        finally:
            if own:
                active.close()

    def _replay(self, connection: sqlite3.Connection, source: _I01Accepted, state: sqlite3.Row) -> None:
        binding = connection.execute("SELECT * FROM d09i02_journal_bindings WHERE journal_identity = ?", (source.binding.binding_identity,)).fetchone()
        if binding is None or binding["receipt_identity"] != source.receipt_identity or binding["binding_json"] != _canonical(_binding(source)) or binding["binding_digest"] != _digest(_binding(source)):
            raise ValueError("D09-I02 binding replay failed")
        events = connection.execute("SELECT * FROM d09i02_events WHERE journal_identity = ? ORDER BY sequence", (source.binding.binding_identity,)).fetchall()
        if not events or len(events) != int(state["sequence"]) + 1 or len(events) > _MAX_EVENTS:
            raise ValueError("D09-I02 event sequence is corrupt")
        previous: _Phase | None = None
        previous_digest = ""
        for raw in events:
            event = json.loads(cast(str, raw["event_json"]))
            if not isinstance(event, dict) or event != _event(source, int(raw["sequence"]), cast(_EventType, raw["event_type"]), previous_digest, cast(str, event.get("payload_digest", ""))) or raw["event_digest"] != event["event_digest"]:
                raise ValueError("D09-I02 event is corrupt")
            current = cast(_Phase, raw["event_type"])
            if (previous is None and current != "RESERVED") or (previous is not None and not _legal(previous, current)):
                raise ValueError("D09-I02 event transition is corrupt")
            previous, previous_digest = current, cast(str, event["event_digest"])
        if previous != state["phase"] or previous_digest != state["last_event_digest"]:
            raise ValueError("D09-I02 final state is corrupt")


class _LocalFileProviderResultEvidenceJournal:
    """Supported private composition: owner-derived I01 reader plus I02 journal."""

    def __init__(self, repository: LocalFileRepository) -> None:
        root = repository._root
        if not root.is_absolute():
            raise ValueError("trusted LocalFile durability root is unavailable")
        self._reader = _I01Reader(repository)
        owner = root.resolve() / "_durability" / "_future_durable_generation" / "provider_result_evidence"
        self._journal = _ResultJournal(owner)

    def capture(self, *, attempt_id: str, observation: object) -> ProviderResultJournalReport:
        source = self._reader.accepted(attempt_id)
        return ProviderResultJournalReport("RESULT_NOT_AVAILABLE") if source is None else self._journal.capture(source, observation)

    def reopen(self, *, attempt_id: str) -> ProviderResultJournalReport:
        source = self._reader.accepted(attempt_id)
        return ProviderResultJournalReport("RESULT_NOT_AVAILABLE") if source is None else self._journal.reopen(source)


def _binding(source: _I01Accepted) -> dict[str, object]:
    return {"binding": source.binding.model_dump(mode="json"), "receipt": source.receipt.model_dump(mode="json"), "receipt_identity": source.receipt_identity}


def _observation(value: object, source: _I01Accepted) -> dict[str, object]:
    if type(value) is not dict:
        raise ValueError("D09-I02 observation must be a primitive mapping")
    raw = cast(dict[object, object], value)
    if set(raw) != {"provider_job_identity", "outputs", "capture_metadata"}:
        raise ValueError("D09-I02 observation fields are invalid")
    job = raw["provider_job_identity"]
    if job is not None and (not isinstance(job, str) or _logical(job, maximum=_MAX_PROVIDER_ID) != job):
        raise ValueError("D09-I02 observation job identity is invalid")
    if source.receipt.provider_job_identity != job:
        raise ValueError("D09-I02 observation job identity does not match I01")
    outputs_raw = raw["outputs"]
    if type(outputs_raw) is not list or not 1 <= len(outputs_raw) <= _MAX_OUTPUTS:
        raise ValueError("D09-I02 observation outputs are invalid")
    outputs: list[OutputEvidenceV1] = []
    total_entries = 0
    for item in cast(list[object], outputs_raw):
        if type(item) is not dict:
            raise ValueError("D09-I02 output observation is invalid")
        output = cast(dict[object, object], item)
        if set(output) != {"logical_output_id", "sha256", "media_type", "metadata"}:
            raise ValueError("D09-I02 output observation fields are invalid")
        metadata = _metadata(output["metadata"])
        total_entries += len(metadata)
        outputs.append(OutputEvidenceV1(logical_output_id=cast(str, output["logical_output_id"]), sha256=cast(str, output["sha256"]), media_type=cast(Any, output["media_type"]), metadata=metadata, metadata_digest=_digest(metadata)))
    if total_entries > _MAX_METADATA_ENTRIES:
        raise ValueError("D09-I02 metadata count is invalid")
    ordered = tuple(sorted(outputs, key=lambda item: item.logical_output_id))
    if len({item.logical_output_id for item in ordered}) != len(ordered) or len({item.sha256 for item in ordered}) != len(ordered):
        raise ValueError("D09-I02 outputs are ambiguous")
    capture_metadata = _metadata(raw["capture_metadata"])
    return {"provider_job_identity": job, "outputs": [item.model_dump(mode="json") for item in ordered], "capture_metadata": capture_metadata}


def _evidence(source: _I01Accepted, observation: dict[str, object]) -> ProviderResultEvidenceV1:
    binding = source.binding
    receipt = source.receipt
    unsigned: dict[str, object] = {"provider_origin_assurance": "UNVERIFIED", "project_id": binding.project_id, "page_id": binding.page_id, "execution_target_reference": binding.execution_target_reference, "attempt_id": binding.attempt_id, "manifest_digest": binding.manifest_digest, "dispatch_identity": binding.dispatch_identity, "idempotency_identity": binding.idempotency_identity, "attempt_binding_digest": binding.attempt_binding_digest, "provider_binding_digest": binding.provider_binding_digest, "journal_identity": binding.binding_identity, "receipt_identity": source.receipt_identity, "receipt_digest": receipt.submission_evidence_digest, "receipt_sequence": receipt.sequence, "submission_evidence_digest": receipt.submission_evidence_digest, "profile_identity": binding.profile_identity, "provider_class": binding.provider_class, "provider_identifier": binding.provider_identifier, "provider_job_identity": observation["provider_job_identity"], "output_evidence": observation["outputs"], "capture_mode": "FAKE_OBSERVATION", "capture_metadata": observation["capture_metadata"], "capture_metadata_digest": _digest(observation["capture_metadata"])}
    identity = _digest({"schema_id": "manga_director.future_provider_result_evidence", "schema_version": "1", **unsigned})
    return ProviderResultEvidenceV1.model_validate(
        {**unsigned, "evidence_identity": identity, "evidence_digest": identity}
    )


def _matches(source: _I01Accepted, evidence: ProviderResultEvidenceV1) -> bool:
    return evidence.journal_identity == source.binding.binding_identity and evidence.receipt_identity == source.receipt_identity and evidence.receipt_digest == source.receipt.submission_evidence_digest and evidence.provider_origin_assurance == "UNVERIFIED"


def _event(source: _I01Accepted, sequence: int, event_type: _EventType, previous_digest: str, payload_digest: str) -> dict[str, object]:
    unsigned = {"schema_id": "manga_director.future_provider_result_journal_event", "schema_version": "1", "journal_identity": source.binding.binding_identity, "receipt_identity": source.receipt_identity, "binding_digest": _digest(_binding(source)), "sequence": sequence, "event_type": event_type, "previous_event_digest": previous_digest, "payload_digest": payload_digest}
    return {**unsigned, "event_digest": _digest(unsigned)}


def _legal(source: _Phase, target: _Phase) -> bool:
    return {"RESERVED": {"CAPTURE_STARTED", "RESULT_MALFORMED"}, "CAPTURE_STARTED": {"OBSERVATION_RECORDED", "RESULT_REJECTED", "RESULT_MALFORMED", "RECOVERY_REQUIRED"}, "OBSERVATION_RECORDED": {"RESULT_CAPTURED", "RESULT_REJECTED", "RESULT_MALFORMED", "RECOVERY_REQUIRED"}, "RESULT_CAPTURED": {"CONFLICT_RECORDED"}, "CONFLICT_RECORDED": {"RECOVERY_REQUIRED"}}.get(source, set()).__contains__(target)
