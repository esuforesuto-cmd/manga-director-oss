"""Private D09 fake-only durable provider-submission receipt journal.

This future-only module accepts a consumed D05 dispatch request, classifies a
primitive D08 profile inside its trusted composition, and records a fake
submission receipt.  It intentionally has no network, provider SDK, result
capture, StateMachine transition, or public export.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from pydantic import ConfigDict, Field, field_validator

from manga_director.production.director import DirectorModel
from manga_director.production.future_durable_generation_boundary import (
    ProviderDispatchRequestV1,
    ProviderInvocationPermitV1,
)
from manga_director.production.future_generation_admission_contract import (
    GenerationAdmissionManifestV1,
    content_digest,
)
from manga_director.production.future_localfile_durable_generation_boundary import (
    LocalFileDurableGenerationBoundary,
)
from manga_director.production.future_provider_capability_profile import (
    ProviderCapabilityClass,
    classify_provider_capabilities,
)
from manga_director.repositories.local_file import LocalFileRepository

JournalLifecycle = Literal[
    "DISPATCH_RECEIVED",
    "SUBMISSION_STARTED",
    "ACCEPTED",
    "REJECTED",
    "FAILED_BEFORE_SEND",
    "AMBIGUOUS",
    "RECOVERY_REQUIRED",
]
FakeOutcome = Literal["ACCEPTED", "REJECTED", "FAILED_BEFORE_SEND", "AMBIGUOUS", "MALFORMED"]
JournalStatus = Literal[
    "ACCEPTED",
    "REJECTED",
    "FAILED_BEFORE_SEND",
    "AMBIGUOUS",
    "RECOVERY_REQUIRED",
    "IN_PROGRESS",
    "CONFLICT",
    "CORRUPT",
    "BLOCKED",
]

_MAX_LOGICAL_IDENTIFIER_LENGTH = 160

_TERMINAL: frozenset[JournalLifecycle] = frozenset(
    {"ACCEPTED", "REJECTED", "FAILED_BEFORE_SEND", "RECOVERY_REQUIRED"}
)


class _StrictModel(DirectorModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


def _logical(value: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or any(char.isspace() for char in value)
        or len(value) > _MAX_LOGICAL_IDENTIFIER_LENGTH
        or value.startswith(("/", "\\"))
        or "://" in value
        or (len(value) > 2 and value[1] == ":")
    ):
        raise ValueError("D09 requires bounded non-secret logical identifiers")
    lowered = value.lower()
    if any(part in lowered for part in ("api_key", "authorization", "credential", "password", "secret", "token")):
        raise ValueError("D09 does not retain secret-shaped values")
    return value


def _digest(value: str) -> str:
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ValueError("D09 requires SHA-256 identities")
    return value


class D09DispatchBindingV1(_StrictModel):
    """Immutable D09 binding derived only from D05 and D08 inputs."""

    schema_id: Literal["manga_director.future_d09_dispatch_binding"] = (
        "manga_director.future_d09_dispatch_binding"
    )
    schema_version: Literal["1"] = "1"
    attempt_id: str
    project_id: str
    page_id: str
    execution_target_reference: str
    manifest_digest: str
    provider_binding_digest: str
    attempt_binding_digest: str
    dispatch_identity: str
    idempotency_identity: str
    profile_identity: str
    provider_class: ProviderCapabilityClass
    provider_identifier: Literal["fake:deterministic"] = "fake:deterministic"

    @field_validator(
        "attempt_id",
        "project_id",
        "page_id",
        "execution_target_reference",
        "provider_identifier",
    )
    @classmethod
    def _reference(cls, value: str) -> str:
        return _logical(value)

    @field_validator(
        "manifest_digest",
        "provider_binding_digest",
        "attempt_binding_digest",
        "dispatch_identity",
        "idempotency_identity",
        "profile_identity",
    )
    @classmethod
    def _identity(cls, value: str) -> str:
        return _digest(value)

    def canonical_projection(self) -> dict[str, object]:
        return self.model_dump(mode="json")

    @property
    def binding_identity(self) -> str:
        return content_digest(self.canonical_projection())


class FakeSubmissionPlanV1(_StrictModel):
    """Bounded fake-only outcome selector; it contains no provider request data."""

    outcome: FakeOutcome
    provider_job_identity: str | None = None

    @field_validator("provider_job_identity")
    @classmethod
    def _job_identity(cls, value: str | None) -> str | None:
        return None if value is None else _logical(value)


class ProviderSubmissionReceiptV1(_StrictModel):
    """Redacted immutable receipt of fake submission, never a provider result."""

    schema_id: Literal["manga_director.future_provider_submission_receipt"] = (
        "manga_director.future_provider_submission_receipt"
    )
    schema_version: Literal["1"] = "1"
    journal_identity: str
    dispatch_identity: str
    idempotency_identity: str
    attempt_id: str
    manifest_digest: str
    provider_binding_digest: str
    profile_identity: str
    provider_class: ProviderCapabilityClass
    provider_identifier: Literal["fake:deterministic"] = "fake:deterministic"
    provider_job_identity: str | None = None
    lifecycle: Literal["ACCEPTED", "REJECTED", "FAILED_BEFORE_SEND"]
    sequence: int = Field(ge=1)
    submission_evidence_digest: str

    @field_validator(
        "journal_identity",
        "dispatch_identity",
        "idempotency_identity",
        "manifest_digest",
        "provider_binding_digest",
        "profile_identity",
        "submission_evidence_digest",
    )
    @classmethod
    def _receipt_identity(cls, value: str) -> str:
        return _digest(value)

    @field_validator("provider_identifier", "provider_job_identity")
    @classmethod
    def _receipt_reference(cls, value: str | None) -> str | None:
        return None if value is None else _logical(value)

    @field_validator("attempt_id")
    @classmethod
    def _receipt_attempt(cls, value: str) -> str:
        return _logical(value)


class _JournalEventV1(_StrictModel):
    """One complete immutable lifecycle event replayed on every journal read."""

    schema_id: Literal["manga_director.future_provider_receipt_journal_event"] = (
        "manga_director.future_provider_receipt_journal_event"
    )
    schema_version: Literal["1"] = "1"
    event_type: Literal["JOURNAL_LIFECYCLE"] = "JOURNAL_LIFECYCLE"
    journal_identity: str
    dispatch_identity: str
    idempotency_identity: str
    attempt_id: str
    manifest_digest: str
    provider_binding_digest: str
    profile_identity: str
    provider_class: ProviderCapabilityClass
    lifecycle: JournalLifecycle
    sequence: int = Field(ge=0)
    event_payload_digest: str

    @field_validator(
        "journal_identity",
        "dispatch_identity",
        "idempotency_identity",
        "manifest_digest",
        "provider_binding_digest",
        "profile_identity",
        "event_payload_digest",
    )
    @classmethod
    def _event_identity(cls, value: str) -> str:
        return _digest(value)

    @field_validator("attempt_id")
    @classmethod
    def _event_attempt(cls, value: str) -> str:
        return _logical(value)


@dataclass(frozen=True, slots=True)
class FakeProviderJournalReport:
    status: JournalStatus
    lifecycle: JournalLifecycle | None
    receipt: ProviderSubmissionReceiptV1 | None = None
    edge_invoked: bool = False
    durable_start_sequence: int | None = None


@dataclass(frozen=True, slots=True)
class _JournalRow:
    binding: D09DispatchBindingV1
    lifecycle: JournalLifecycle
    sequence: int
    receipt: ProviderSubmissionReceiptV1 | None


class _LocalFakeProviderReceiptJournal:
    """Dedicated SQLite owner; corruption and schema drift fail closed."""

    _DATABASE_NAME = "fake_provider_receipts.sqlite3"

    def __init__(self, root: Path) -> None:
        if not root.is_absolute():
            raise ValueError("D09 journal requires a trusted absolute owner root")
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        self._database = self._root / self._DATABASE_NAME
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database, timeout=5, isolation_level=None)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        try:
            existed = self._database.exists()
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                objects = self._d09_objects(connection)
                if existed and objects:
                    self._validate_schema(connection)
                    self._validate_schema_version(connection)
                elif existed and not objects:
                    other_objects = connection.execute(
                        "SELECT name FROM sqlite_master WHERE type IN ('table', 'index') AND name NOT LIKE 'sqlite_%'"
                    ).fetchall()
                    if other_objects:
                        raise ValueError("D09 journal store is not empty")
                connection.execute("CREATE TABLE IF NOT EXISTS d09_schema_meta (version INTEGER NOT NULL)")
                rows = connection.execute("SELECT version FROM d09_schema_meta").fetchall()
                if not existed and not rows:
                    connection.execute("INSERT INTO d09_schema_meta(version) VALUES (1)")
                elif existed:
                    self._validate_schema_version(connection)
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS d09_journals ("
                    "journal_identity TEXT PRIMARY KEY, dispatch_identity TEXT NOT NULL, "
                    "binding_json TEXT NOT NULL, binding_digest TEXT NOT NULL, lifecycle TEXT NOT NULL, "
                    "sequence INTEGER NOT NULL, receipt_json TEXT)"
                )
                connection.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS d09_dispatch_identity_unique "
                    "ON d09_journals(dispatch_identity)"
                )
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS d09_journal_events ("
                    "journal_identity TEXT NOT NULL, sequence INTEGER NOT NULL, lifecycle TEXT NOT NULL, "
                    "event_json TEXT NOT NULL, PRIMARY KEY(journal_identity, sequence))"
                )
                self._validate_schema(connection)
                self._validate_schema_version(connection)
                connection.commit()
        except (OSError, sqlite3.Error) as error:
            raise ValueError("D09 journal is unavailable") from error

    @staticmethod
    def _d09_objects(connection: sqlite3.Connection) -> set[tuple[str, str]]:
        return {
            (str(row["type"]), str(row["name"]))
            for row in connection.execute(
                "SELECT type, name FROM sqlite_master WHERE type IN ('table', 'index') AND name LIKE 'd09_%'"
            )
        }

    @classmethod
    def _validate_schema(cls, connection: sqlite3.Connection) -> None:
        objects = cls._d09_objects(connection)
        required = {
            ("table", "d09_schema_meta"),
            ("table", "d09_journals"),
            ("table", "d09_journal_events"),
            ("index", "d09_dispatch_identity_unique"),
        }
        if objects != required:
            raise ValueError("D09 journal schema is incomplete")
        expected_columns = {
            "d09_schema_meta": {"version"},
            "d09_journals": {
                "journal_identity",
                "dispatch_identity",
                "binding_json",
                "binding_digest",
                "lifecycle",
                "sequence",
                "receipt_json",
            },
            "d09_journal_events": {"journal_identity", "sequence", "lifecycle", "event_json"},
        }
        for table, columns in expected_columns.items():
            actual = {str(item["name"]) for item in connection.execute(f"PRAGMA table_info({table})")}
            if actual != columns:
                raise ValueError("D09 journal table schema is invalid")
        index_columns = [
            str(item["name"])
            for item in connection.execute("PRAGMA index_info(d09_dispatch_identity_unique)")
        ]
        if index_columns != ["dispatch_identity"]:
            raise ValueError("D09 journal dispatch index is invalid")
        index_list = {
            str(item["name"]): int(item["unique"])
            for item in connection.execute("PRAGMA index_list(d09_journals)")
        }
        if index_list.get("d09_dispatch_identity_unique") != 1:
            raise ValueError("D09 journal dispatch index must be unique")
        primary_keys = {
            "d09_journals": {"journal_identity": 1},
            "d09_journal_events": {"journal_identity": 1, "sequence": 2},
        }
        for table, expected in primary_keys.items():
            primary_key_values = {
                str(item["name"]): int(item["pk"])
                for item in connection.execute(f"PRAGMA table_info({table})")
                if int(item["pk"]) > 0
            }
            if primary_key_values != expected:
                raise ValueError("D09 journal primary key is invalid")

    @staticmethod
    def _validate_schema_version(connection: sqlite3.Connection) -> None:
        rows = connection.execute("SELECT version FROM d09_schema_meta").fetchall()
        if len(rows) != 1 or rows[0]["version"] != 1:
            raise ValueError("D09 schema version is invalid")

    def reserve(self, binding: D09DispatchBindingV1) -> tuple[str, _JournalRow | None]:
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                rows = connection.execute(
                    "SELECT * FROM d09_journals WHERE dispatch_identity = ?", (binding.dispatch_identity,)
                ).fetchall()
                if len(rows) > 1:
                    raise ValueError("D09 dispatch identity is not unique")
                if rows:
                    existing = self._row(connection, rows[0])
                    connection.commit()
                    return ("existing" if existing.binding == binding else "conflict", existing)
                journal_identity = binding.binding_identity
                payload = json.dumps(binding.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
                connection.execute(
                    "INSERT INTO d09_journals VALUES (?, ?, ?, ?, ?, ?, NULL)",
                    (
                        journal_identity,
                        binding.dispatch_identity,
                        payload,
                        binding.binding_identity,
                        "DISPATCH_RECEIVED",
                        0,
                    ),
                )
                self._event(connection, binding, 0, "DISPATCH_RECEIVED")
                created = _JournalRow(binding, "DISPATCH_RECEIVED", 0, None)
                connection.commit()
                return "reserved", created
        except (OSError, sqlite3.Error, ValueError, json.JSONDecodeError):
            return "corrupt", None

    def transition(
        self,
        binding: D09DispatchBindingV1,
        expected: JournalLifecycle,
        lifecycle: JournalLifecycle,
        receipt: ProviderSubmissionReceiptV1 | None = None,
    ) -> tuple[str, _JournalRow | None]:
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                database_rows = connection.execute(
                    "SELECT * FROM d09_journals WHERE dispatch_identity = ?", (binding.dispatch_identity,)
                ).fetchall()
                if len(database_rows) > 1:
                    raise ValueError("D09 dispatch identity is not unique")
                if not database_rows:
                    connection.commit()
                    return "missing", None
                current = self._row(connection, database_rows[0])
                if current.binding != binding:
                    connection.commit()
                    return "conflict", current
                if current.lifecycle != expected:
                    connection.commit()
                    return "existing", current
                sequence = current.sequence + 1
                receipt_json = None if receipt is None else receipt.model_dump_json()
                connection.execute(
                    "UPDATE d09_journals SET lifecycle = ?, sequence = ?, receipt_json = ? "
                    "WHERE journal_identity = ? AND sequence = ?",
                    (lifecycle, sequence, receipt_json, current.binding.binding_identity, current.sequence),
                )
                if connection.total_changes != 1:
                    raise ValueError("D09 sequence compare-and-swap failed")
                self._event(connection, current.binding, sequence, lifecycle)
                updated = _JournalRow(binding, lifecycle, sequence, receipt)
                connection.commit()
                return "transitioned", updated
        except (OSError, sqlite3.Error, ValueError, json.JSONDecodeError):
            return "corrupt", None

    def reopen(self, binding: D09DispatchBindingV1) -> FakeProviderJournalReport:
        outcome, row = self.reserve(binding)
        if outcome == "conflict":
            return FakeProviderJournalReport("CONFLICT", row.lifecycle if row else None)
        if outcome == "corrupt" or row is None:
            return FakeProviderJournalReport("CORRUPT", None)
        if row.lifecycle in {"SUBMISSION_STARTED", "AMBIGUOUS"}:
            outcome, row = self.transition(binding, row.lifecycle, "RECOVERY_REQUIRED")
            if outcome != "transitioned" or row is None:
                return FakeProviderJournalReport("CORRUPT", None)
        return _report(row)

    @staticmethod
    def _event(
        connection: sqlite3.Connection,
        binding: D09DispatchBindingV1,
        sequence: int,
        lifecycle: JournalLifecycle,
    ) -> None:
        event = _JournalEventV1(
            journal_identity=binding.binding_identity,
            dispatch_identity=binding.dispatch_identity,
            idempotency_identity=binding.idempotency_identity,
            attempt_id=binding.attempt_id,
            manifest_digest=binding.manifest_digest,
            provider_binding_digest=binding.provider_binding_digest,
            profile_identity=binding.profile_identity,
            provider_class=binding.provider_class,
            lifecycle=lifecycle,
            sequence=sequence,
            event_payload_digest=_event_payload_digest(binding, lifecycle, sequence),
        )
        connection.execute(
            "INSERT INTO d09_journal_events VALUES (?, ?, ?, ?)",
            (binding.binding_identity, sequence, lifecycle, event.model_dump_json()),
        )

    @staticmethod
    def _row(connection: sqlite3.Connection, row: sqlite3.Row) -> _JournalRow:
        binding = D09DispatchBindingV1.model_validate_json(cast(str, row["binding_json"]))
        if binding.binding_identity != row["binding_digest"] or binding.binding_identity != row["journal_identity"]:
            raise ValueError("D09 durable binding is corrupt")
        lifecycle = cast(JournalLifecycle, row["lifecycle"])
        if lifecycle not in {"DISPATCH_RECEIVED", "SUBMISSION_STARTED", *_TERMINAL, "AMBIGUOUS"}:
            raise ValueError("D09 lifecycle is invalid")
        sequence = int(row["sequence"])
        receipt = _replayed_receipt(row, binding, lifecycle, sequence)
        _validate_replayed_events(connection, binding, lifecycle, sequence)
        return _JournalRow(binding, lifecycle, sequence, receipt)


class _ReceiptJournalCore:
    """Internal D09 mechanics; only trusted runtime and test harness construct it."""

    def __init__(self, journal: _LocalFakeProviderReceiptJournal) -> None:
        self._journal = journal

    def submit_consumed_dispatch(
        self,
        dispatch: ProviderDispatchRequestV1,
        raw_provider_profile: object,
        plan: FakeSubmissionPlanV1,
    ) -> FakeProviderJournalReport:
        try:
            if type(dispatch) is not ProviderDispatchRequestV1:
                return FakeProviderJournalReport("CORRUPT", None)
            validated_dispatch = ProviderDispatchRequestV1.model_validate(dispatch.model_dump(mode="json"))
            classification = classify_provider_capabilities(raw_provider_profile)
            binding = D09DispatchBindingV1(
                attempt_id=validated_dispatch.attempt_id,
                project_id=validated_dispatch.project_id,
                page_id=validated_dispatch.page_id,
                execution_target_reference=validated_dispatch.execution_target_reference,
                manifest_digest=validated_dispatch.manifest_digest,
                provider_binding_digest=validated_dispatch.provider_binding_digest,
                attempt_binding_digest=validated_dispatch.attempt_binding_digest,
                dispatch_identity=validated_dispatch.dispatch_request_identity,
                idempotency_identity=validated_dispatch.idempotency_identity,
                profile_identity=classification.profile_identity,
                provider_class=classification.provider_class,
            )
        except Exception:
            return FakeProviderJournalReport("CORRUPT", None)

        reservation, row = self._journal.reserve(binding)
        if reservation == "conflict":
            return FakeProviderJournalReport("CONFLICT", row.lifecycle if row else None)
        if reservation == "corrupt" or row is None:
            return FakeProviderJournalReport("CORRUPT", None)
        if reservation == "existing":
            if row.lifecycle in {"DISPATCH_RECEIVED", "SUBMISSION_STARTED"}:
                return FakeProviderJournalReport("IN_PROGRESS", row.lifecycle)
            return _report(row)
        started, row = self._journal.transition(binding, "DISPATCH_RECEIVED", "SUBMISSION_STARTED")
        if started != "transitioned" or row is None:
            return FakeProviderJournalReport("CORRUPT", None)

        # The deterministic fake edge has no injectable callback and is reached only after commit.
        returned = _deterministic_fake_submission(binding, plan, row.sequence)
        if returned.outcome in {"AMBIGUOUS", "MALFORMED"}:
            outcome, ambiguous = self._journal.transition(binding, "SUBMISSION_STARTED", "AMBIGUOUS")
            if outcome != "transitioned" or ambiguous is None:
                return FakeProviderJournalReport("CORRUPT", None)
            if binding.provider_class == "C":
                outcome, recovery = self._journal.transition(binding, "AMBIGUOUS", "RECOVERY_REQUIRED")
                return _edge_report(recovery, row.sequence) if outcome == "transitioned" and recovery else FakeProviderJournalReport("CORRUPT", None)
            return _edge_report(ambiguous, row.sequence)
        lifecycle = cast(Literal["ACCEPTED", "REJECTED", "FAILED_BEFORE_SEND"], returned.outcome)
        receipt = _receipt(binding, lifecycle, row.sequence + 1, returned.provider_job_identity)
        outcome, completed = self._journal.transition(binding, "SUBMISSION_STARTED", lifecycle, receipt)
        return _edge_report(completed, row.sequence) if outcome == "transitioned" and completed else FakeProviderJournalReport("CORRUPT", None)

    def reopen_consumed_dispatch(
        self, dispatch: ProviderDispatchRequestV1, raw_provider_profile: object
    ) -> FakeProviderJournalReport:
        # Reuses the same validation path but never invokes the fake edge.
        try:
            classification = classify_provider_capabilities(raw_provider_profile)
            binding = D09DispatchBindingV1(
                attempt_id=dispatch.attempt_id,
                project_id=dispatch.project_id,
                page_id=dispatch.page_id,
                execution_target_reference=dispatch.execution_target_reference,
                manifest_digest=dispatch.manifest_digest,
                provider_binding_digest=dispatch.provider_binding_digest,
                attempt_binding_digest=dispatch.attempt_binding_digest,
                dispatch_identity=dispatch.dispatch_request_identity,
                idempotency_identity=dispatch.idempotency_identity,
                profile_identity=classification.profile_identity,
                provider_class=classification.provider_class,
            )
        except Exception:
            return FakeProviderJournalReport("CORRUPT", None)
        return self._journal.reopen(binding)


class _LocalFileFakeProviderReceiptJournal:
    """Supported trusted runtime: consume D05 locally, then invoke the internal fake once."""

    def __init__(self, repository: LocalFileRepository) -> None:
        root = repository._root
        if not root.is_absolute():
            raise ValueError("trusted LocalFile durability root is unavailable")
        owner = root.resolve() / "_durability" / "_future_durable_generation" / "provider_receipts"
        self._d05 = LocalFileDurableGenerationBoundary(repository)
        self._core = _ReceiptJournalCore(_LocalFakeProviderReceiptJournal(owner))

    def submit(
        self,
        *,
        manifest: GenerationAdmissionManifestV1,
        permit: ProviderInvocationPermitV1,
        raw_provider_profile: object,
    ) -> FakeProviderJournalReport:
        dispatch = self._d05.consume_for_dispatch(manifest, permit)
        if dispatch is None:
            return FakeProviderJournalReport("BLOCKED", None)
        return self._core.submit_consumed_dispatch(
            dispatch, raw_provider_profile, FakeSubmissionPlanV1(outcome="ACCEPTED")
        )


class _D09TestOnlyHarness:
    """Focused-test seam, not reachable from the supported LocalFile runtime."""

    def __init__(self, root: Path) -> None:
        self._core = _ReceiptJournalCore(_LocalFakeProviderReceiptJournal(root))

    def submit_consumed_dispatch(
        self, dispatch: ProviderDispatchRequestV1, raw_provider_profile: object, plan: FakeSubmissionPlanV1
    ) -> FakeProviderJournalReport:
        return self._core.submit_consumed_dispatch(dispatch, raw_provider_profile, plan)

    def reopen_consumed_dispatch(
        self, dispatch: ProviderDispatchRequestV1, raw_provider_profile: object
    ) -> FakeProviderJournalReport:
        return self._core.reopen_consumed_dispatch(dispatch, raw_provider_profile)


def _deterministic_fake_submission(
    binding: D09DispatchBindingV1, plan: FakeSubmissionPlanV1, durable_start_sequence: int
) -> FakeSubmissionPlanV1:
    """Inert internal edge; its input carries no raw provider request or callback."""

    del binding
    if durable_start_sequence < 1:
        raise ValueError("D09 fake edge requires durable submission start")
    return plan


def _replayed_receipt(
    row: sqlite3.Row,
    binding: D09DispatchBindingV1,
    lifecycle: JournalLifecycle,
    sequence: int,
) -> ProviderSubmissionReceiptV1 | None:
    receipt_json = row["receipt_json"]
    receipt = None if receipt_json is None else ProviderSubmissionReceiptV1.model_validate_json(cast(str, receipt_json))
    if receipt is not None and (
        not _receipt_matches_binding(receipt, binding)
        or receipt.submission_evidence_digest != _receipt_payload_digest(receipt)
    ):
        raise ValueError("D09 receipt is corrupt")
    if lifecycle in {"ACCEPTED", "REJECTED", "FAILED_BEFORE_SEND"}:
        if receipt is None or receipt.lifecycle != lifecycle or receipt.sequence != sequence:
            raise ValueError("D09 terminal receipt is corrupt")
    elif receipt is not None:
        raise ValueError("D09 non-terminal receipt is corrupt")
    return receipt


def _validate_replayed_events(
    connection: sqlite3.Connection,
    binding: D09DispatchBindingV1,
    lifecycle: JournalLifecycle,
    sequence: int,
) -> None:
    events = connection.execute(
        "SELECT sequence, lifecycle, event_json FROM d09_journal_events "
        "WHERE journal_identity = ? ORDER BY sequence",
        (binding.binding_identity,),
    ).fetchall()
    if len(events) != sequence + 1 or [event["sequence"] for event in events] != list(range(sequence + 1)):
        raise ValueError("D09 journal event sequence is corrupt")
    previous: JournalLifecycle | None = None
    for raw_event in events:
        event = _JournalEventV1.model_validate_json(cast(str, raw_event["event_json"]))
        if event.sequence != raw_event["sequence"] or event.lifecycle != raw_event["lifecycle"]:
            raise ValueError("D09 journal event row is corrupt")
        if not _event_matches_binding(event, binding):
            raise ValueError("D09 journal event binding is corrupt")
        if event.event_payload_digest != _event_payload_digest(binding, event.lifecycle, event.sequence):
            raise ValueError("D09 journal event digest is corrupt")
        if not _allowed_event_transition(previous, event.lifecycle, event.sequence):
            raise ValueError("D09 journal event transition is corrupt")
        previous = event.lifecycle
    if previous != lifecycle:
        raise ValueError("D09 journal event lifecycle is corrupt")


def _receipt_payload_digest(receipt: ProviderSubmissionReceiptV1) -> str:
    return content_digest(receipt.model_dump(mode="json", exclude={"submission_evidence_digest"}))


def _receipt_matches_binding(receipt: ProviderSubmissionReceiptV1, binding: D09DispatchBindingV1) -> bool:
    return (
        receipt.journal_identity == binding.binding_identity
        and receipt.dispatch_identity == binding.dispatch_identity
        and receipt.idempotency_identity == binding.idempotency_identity
        and receipt.attempt_id == binding.attempt_id
        and receipt.manifest_digest == binding.manifest_digest
        and receipt.provider_binding_digest == binding.provider_binding_digest
        and receipt.profile_identity == binding.profile_identity
        and receipt.provider_class == binding.provider_class
        and receipt.provider_identifier == binding.provider_identifier
    )


def _event_payload_digest(binding: D09DispatchBindingV1, lifecycle: JournalLifecycle, sequence: int) -> str:
    return content_digest(
        {
            "attempt_id": binding.attempt_id,
            "dispatch_identity": binding.dispatch_identity,
            "event_type": "JOURNAL_LIFECYCLE",
            "idempotency_identity": binding.idempotency_identity,
            "journal_identity": binding.binding_identity,
            "lifecycle": lifecycle,
            "manifest_digest": binding.manifest_digest,
            "profile_identity": binding.profile_identity,
            "provider_binding_digest": binding.provider_binding_digest,
            "provider_class": binding.provider_class,
            "schema_id": "manga_director.future_provider_receipt_journal_event",
            "schema_version": "1",
            "sequence": sequence,
        }
    )


def _event_matches_binding(event: _JournalEventV1, binding: D09DispatchBindingV1) -> bool:
    return (
        event.journal_identity == binding.binding_identity
        and event.dispatch_identity == binding.dispatch_identity
        and event.idempotency_identity == binding.idempotency_identity
        and event.attempt_id == binding.attempt_id
        and event.manifest_digest == binding.manifest_digest
        and event.provider_binding_digest == binding.provider_binding_digest
        and event.profile_identity == binding.profile_identity
        and event.provider_class == binding.provider_class
    )


def _allowed_event_transition(
    previous: JournalLifecycle | None, lifecycle: JournalLifecycle, sequence: int
) -> bool:
    if sequence == 0:
        return previous is None and lifecycle == "DISPATCH_RECEIVED"
    if previous == "DISPATCH_RECEIVED":
        return lifecycle == "SUBMISSION_STARTED"
    if previous == "SUBMISSION_STARTED":
        return lifecycle in {"ACCEPTED", "REJECTED", "FAILED_BEFORE_SEND", "AMBIGUOUS", "RECOVERY_REQUIRED"}
    if previous == "AMBIGUOUS":
        return lifecycle == "RECOVERY_REQUIRED"
    return False


def _receipt(
    binding: D09DispatchBindingV1,
    lifecycle: Literal["ACCEPTED", "REJECTED", "FAILED_BEFORE_SEND"],
    sequence: int,
    provider_job_identity: str | None,
) -> ProviderSubmissionReceiptV1:
    unsigned = ProviderSubmissionReceiptV1(
        journal_identity=binding.binding_identity,
        dispatch_identity=binding.dispatch_identity,
        idempotency_identity=binding.idempotency_identity,
        attempt_id=binding.attempt_id,
        manifest_digest=binding.manifest_digest,
        provider_binding_digest=binding.provider_binding_digest,
        profile_identity=binding.profile_identity,
        provider_class=binding.provider_class,
        provider_job_identity=provider_job_identity,
        lifecycle=lifecycle,
        sequence=sequence,
        submission_evidence_digest="0" * 64,
    )
    return unsigned.model_copy(
        update={"submission_evidence_digest": _receipt_payload_digest(unsigned)}
    )


def _report(row: _JournalRow | None) -> FakeProviderJournalReport:
    if row is None:
        return FakeProviderJournalReport("CORRUPT", None)
    status: JournalStatus = "IN_PROGRESS" if row.lifecycle in {"DISPATCH_RECEIVED", "SUBMISSION_STARTED"} else cast(
        JournalStatus, row.lifecycle
    )
    return FakeProviderJournalReport(status, row.lifecycle, row.receipt)


def _edge_report(row: _JournalRow | None, durable_start_sequence: int) -> FakeProviderJournalReport:
    report = _report(row)
    return FakeProviderJournalReport(
        report.status,
        report.lifecycle,
        report.receipt,
        edge_invoked=True,
        durable_start_sequence=durable_start_sequence,
    )
