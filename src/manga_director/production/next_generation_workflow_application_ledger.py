"""Private immutable Workflow Application Ledger infrastructure.

The ledger records only the logical reservation and application of an already
validated external generation result.  It is deliberately separate from
Generation Evidence, asset ownership, LocalFile durability, and workflow
execution.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from threading import RLock
from typing import Literal, Protocol, cast

from pydantic import ConfigDict, field_validator

from manga_director.production.director import DirectorModel
from manga_director.production.next_generation_durable_evidence_workflow_binding import (
    DurableEvidenceWorkflowBindingReport,
    WorkflowApplicationAuthorizationDTO,
)

FindingStatus = Literal["blocked"]
LedgerStatus = Literal["prepared", "applied", "blocked"]
Lifecycle = Literal["prepared", "applied"]
StoreWriteOutcome = Literal[
    "prepared",
    "applied",
    "confirmed_prepared",
    "confirmed_applied",
    "conflict",
    "missing",
    "failed",
]
LookupOutcome = Literal["found", "missing", "prepared", "ambiguous", "corrupt"]
ExactLookupOutcome = Literal["prepared", "applied", "missing", "conflict", "corrupt"]
_ObservationOutcome = Literal[
    "MISSING",
    "PREPARED",
    "APPLIED",
    "CONFLICT",
    "CORRUPT",
    "RECOVERY_REQUIRED",
    "AUTHORITY_REJECTED",
]
_R26PreparationOutcome = Literal[
    "prepared",
    "confirmed_prepared",
    "confirmed_applied",
    "conflict",
    "AUTHORITY_REJECTED",
    "CORRUPT",
    "UNAVAILABLE",
]

_R26_SCHEMA_VERSION = 2
_DATABASE_FILENAME = "workflow-application-ledger.sqlite3"
_TABLE_NAME = "workflow_application_ledger"
_LIFECYCLES = {"prepared", "applied"}
_WINDOWS_ABSOLUTE_PATH = ("/", "\\")
_PROOF_SEAL = object()
_R26_PREPARATION_ISSUER = object()
_R26_FINALIZER_ISSUER = object()
_R26_CAPABILITY_LOCK = RLock()
_R26_READY_ROOTS: dict[int, tuple[object, object, object]] = {}
_R26_PREPARATION_CAPABILITIES: dict[int, tuple[object, object, object, object]] = {}
_R26_OBSERVATION_CAPABILITIES: dict[int, tuple[object, object, object, object]] = {}
_R26_AUTHENTICATED_OBSERVATIONS: dict[object, tuple[object, object, object, object, object, object]] = {}
_R26_FINALIZER_AUTHORIZATIONS: dict[object, tuple[object, object, object, object, object, object]] = {}
_R21_DDL_V1 = (
    "CREATE TABLE workflow_application_ledger ("
    "attempt_id TEXT PRIMARY KEY, "
    "authorization_id TEXT NOT NULL UNIQUE, "
    "project_id TEXT NOT NULL, "
    "page_id TEXT NOT NULL, "
    "target_page_reference TEXT NOT NULL, "
    "provider_reference TEXT NOT NULL, "
    "output_asset_id TEXT NOT NULL, "
    "source_state TEXT NOT NULL CHECK(source_state = 'PromptBuilt'), "
    "target_state TEXT NOT NULL CHECK(target_state = 'Generated'), "
    "lifecycle TEXT NOT NULL CHECK(lifecycle IN ('prepared', 'applied')), "
    "binding_json TEXT NOT NULL, "
    "binding_digest TEXT NOT NULL"
    ")"
)
_R26_DDL_V2 = (
    "CREATE TABLE workflow_application_ledger ("
    "attempt_id TEXT PRIMARY KEY, "
    "authorization_id TEXT NOT NULL UNIQUE, "
    "project_id TEXT NOT NULL, "
    "page_id TEXT NOT NULL, "
    "target_page_reference TEXT NOT NULL, "
    "provider_reference TEXT NOT NULL, "
    "output_asset_id TEXT NOT NULL, "
    "source_state TEXT NOT NULL CHECK(source_state = 'PromptBuilt'), "
    "target_state TEXT NOT NULL CHECK(target_state = 'Generated'), "
    "lifecycle TEXT NOT NULL CHECK(lifecycle IN ('prepared', 'applied')), "
    "binding_json TEXT NOT NULL, "
    "binding_digest TEXT NOT NULL, "
    "post_cas_attestation_requirement_version INTEGER NOT NULL DEFAULT 0 "
    "CHECK(post_cas_attestation_requirement_version IN (0, 1)), "
    "r26_protocol_binding_digest TEXT NOT NULL DEFAULT ''"
    ")"
)
_SELECT_COLUMNS = (
    "attempt_id, authorization_id, project_id, page_id, target_page_reference, "
    "provider_reference, output_asset_id, source_state, target_state, lifecycle, "
    "binding_json, binding_digest, post_cas_attestation_requirement_version, "
    "r26_protocol_binding_digest"
)
_V1_SELECT_COLUMNS = (
    "attempt_id, authorization_id, project_id, page_id, target_page_reference, "
    "provider_reference, output_asset_id, source_state, target_state, lifecycle, "
    "binding_json, binding_digest"
)


class _WorkflowApplicationLedgerModel(DirectorModel):
    """Private base for immutable, closed ledger values."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class WorkflowApplicationLedgerBindingDTO(_WorkflowApplicationLedgerModel):
    """The complete immutable logical identity of one application."""

    attempt_id: str
    authorization_id: str
    project_id: str
    page_id: str
    target_page_reference: str
    provider_reference: str
    output_asset_id: str
    source_state: Literal["PromptBuilt"]
    target_state: Literal["Generated"]

    @field_validator(
        "attempt_id",
        "authorization_id",
        "project_id",
        "page_id",
        "target_page_reference",
        "provider_reference",
        "output_asset_id",
    )
    @classmethod
    def _validate_logical_reference(cls, value: str) -> str:
        return _logical_reference(value)


class WorkflowApplicationLedgerFindingDTO(_WorkflowApplicationLedgerModel):
    """One deterministic, redacted ledger finding."""

    code: str
    status: FindingStatus
    message: str
    attempt_id: str = ""
    authorization_id: str = ""
    project_id: str = ""
    page_id: str = ""
    target_page_reference: str = ""
    provider_reference: str = ""
    output_asset_id: str = ""


class WorkflowApplicationLedgerReport(_WorkflowApplicationLedgerModel):
    """Redacted result of one private ledger operation."""

    binding: WorkflowApplicationLedgerBindingDTO | None = None
    lifecycle: Lifecycle | None = None
    findings: tuple[WorkflowApplicationLedgerFindingDTO, ...] = ()
    status: LedgerStatus
    prepared: bool
    applied: bool
    idempotent_replay: bool
    persistence_performed: bool


@dataclass(frozen=True, slots=True)
class WorkflowApplicationLedgerStoreWriteResult:
    """Private result from one durable ledger mutation."""

    binding: WorkflowApplicationLedgerBindingDTO = field(repr=False)
    outcome: StoreWriteOutcome


@dataclass(frozen=True, slots=True)
class WorkflowApplicationLedgerAppliedLookupResult:
    """Private result used only for exact applied-proof checks."""

    outcome: LookupOutcome
    binding: WorkflowApplicationLedgerBindingDTO | None = field(default=None, repr=False)


@dataclass(frozen=True, slots=True)
class WorkflowApplicationLedgerExactLookupResult:
    """Private exact-binding lifecycle lookup for reconciliation only."""

    outcome: ExactLookupOutcome


@dataclass(frozen=True, slots=True)
class _WorkflowApplicationLedgerObservationV1:
    """Private R21 fact from one exact, read-only Ledger observation."""

    outcome: _ObservationOutcome


@dataclass(frozen=True, slots=True)
class _R26ProtocolObservationV2:
    """Private marker-aware, read-only R21 observation for future R26 only."""

    outcome: _ObservationOutcome
    marker_version: int | None = None
    protocol_binding_digest: str | None = None


class _R26AuthenticatedProtocolObservationV1:
    """One-use source-authenticated wrapper for a private R26 observation."""

    __slots__ = ("_binding", "_observation", "_repository", "_root", "_seal", "_store", "_used")

    _binding: WorkflowApplicationLedgerBindingDTO
    _observation: _R26ProtocolObservationV2
    _repository: object
    _root: object
    _seal: object
    _store: LocalWorkflowApplicationLedgerStore
    _used: bool

    def __init__(self, *args: object) -> None:
        del args
        raise ValueError("AUTHORITY_REJECTED")

    def __copy__(self) -> _R26AuthenticatedProtocolObservationV1:
        raise ValueError("AUTHORITY_REJECTED")

    def __deepcopy__(self, memo: dict[int, object]) -> _R26AuthenticatedProtocolObservationV1:
        del memo
        raise ValueError("AUTHORITY_REJECTED")

    @property
    def outcome(self) -> _ObservationOutcome:
        return self._observation.outcome

    @property
    def marker_version(self) -> int | None:
        return self._observation.marker_version

    @property
    def protocol_binding_digest(self) -> str | None:
        return self._observation.protocol_binding_digest


class _R26LedgerFinalizerAuthorizationV1:
    """Private construction-held authority for the IMP-10 Ledger inlet."""

    __slots__ = ("_issuer", "_used")

    _issuer: object
    _used: bool

    def __init__(self, *args: object) -> None:
        del args
        raise ValueError("AUTHORITY_REJECTED")

    def __copy__(self) -> _R26LedgerFinalizerAuthorizationV1:
        raise ValueError("AUTHORITY_REJECTED")

    def __deepcopy__(self, memo: dict[int, object]) -> _R26LedgerFinalizerAuthorizationV1:
        del memo
        raise ValueError("AUTHORITY_REJECTED")


@dataclass(frozen=True, slots=True)
class _R26ProtocolPreparationResultV1:
    """Private, exact outcome of a marker-1 preparation mutation."""

    binding: WorkflowApplicationLedgerBindingDTO = field(repr=False)
    outcome: _R26PreparationOutcome


@dataclass(frozen=True, slots=True)
class _R26LedgerFinalizationResultV1:
    """Closed structural result of one sealed R26 durable transition."""

    outcome: Literal[
        "APPLIED",
        "CALL_REJECTED",
        "CONFLICT",
        "CORRUPT",
        "RECOVERY_REQUIRED",
        "LEDGER_REPLAY_REQUIRED",
    ]


class _R26ProtocolV1PreparationCapability:
    """Opaque, one-use permission for the private marker-1 PREPARED insert."""

    __slots__ = ("_issuer", "_repository", "_root", "_store", "_used")

    _issuer: object
    _repository: object
    _root: object
    _store: LocalWorkflowApplicationLedgerStore
    _used: bool

    def __init__(self, *args: object) -> None:
        del args
        raise ValueError("AUTHORITY_REJECTED")


class _R26ProtocolV1ObservationCapability:
    """Opaque one-use authority for an exact private marker observation."""

    __slots__ = ("_issuer", "_repository", "_root", "_store", "_used")

    _issuer: object
    _repository: object
    _root: object
    _store: LocalWorkflowApplicationLedgerStore
    _used: bool

    def __init__(self, *args: object) -> None:
        del args
        raise ValueError("AUTHORITY_REJECTED")


class _AuthoritativeWorkflowApplicationCommitProof:
    """Non-serializable internal capability minted after an authoritative CAS."""

    __slots__ = ("_binding", "_seal")

    def __init__(self, binding: WorkflowApplicationLedgerBindingDTO, seal: object) -> None:
        self._binding = binding
        self._seal = seal

    def _matches(self, binding: WorkflowApplicationLedgerBindingDTO) -> bool:
        return self._seal is _PROOF_SEAL and self._binding == binding


class WorkflowApplicationLedgerStorePort(Protocol):
    """Private persistence boundary for immutable workflow applications."""

    def prepare(
        self, binding: WorkflowApplicationLedgerBindingDTO
    ) -> WorkflowApplicationLedgerStoreWriteResult: ...

    def finalize(
        self,
        binding: WorkflowApplicationLedgerBindingDTO,
        commit_proof: _AuthoritativeWorkflowApplicationCommitProof,
    ) -> WorkflowApplicationLedgerStoreWriteResult: ...

    def lookup_applied(
        self,
        project_id: str,
        page_id: str,
        output_asset_id: str,
    ) -> WorkflowApplicationLedgerAppliedLookupResult: ...

    def lookup_exact(
        self, binding: WorkflowApplicationLedgerBindingDTO
    ) -> WorkflowApplicationLedgerExactLookupResult: ...

def _authoritative_commit_proof(
    binding: WorkflowApplicationLedgerBindingDTO,
) -> _AuthoritativeWorkflowApplicationCommitProof:
    """Create the future coordinator-only proof after successful LocalFile CAS."""

    return _AuthoritativeWorkflowApplicationCommitProof(binding, _PROOF_SEAL)


class WorkflowApplicationLedgerService:
    """Validate and persist only private workflow-application reservations."""

    def prepare(
        self,
        binding_report: DurableEvidenceWorkflowBindingReport,
        authorization: WorkflowApplicationAuthorizationDTO,
        ledger_store: WorkflowApplicationLedgerStorePort,
    ) -> WorkflowApplicationLedgerReport:
        """Reserve one exact eligible application before any page-fence work."""

        binding = _binding_from_eligibility(binding_report, authorization)
        if binding is None:
            return _blocked_report(None, "LEDGER_PREPARE_BINDING_INVALID")
        try:
            result = ledger_store.prepare(binding)
        except Exception:
            return _blocked_report(binding, "LEDGER_PREPARE_FAILED", persistence_performed=True)
        if not isinstance(result, WorkflowApplicationLedgerStoreWriteResult) or result.binding != binding:
            return _blocked_report(binding, "LEDGER_PREPARE_RESULT_INVALID", persistence_performed=True)
        if result.outcome == "prepared":
            return _prepared_report(binding, idempotent_replay=False)
        if result.outcome == "confirmed_prepared":
            return _prepared_report(binding, idempotent_replay=True)
        if result.outcome in {"applied", "confirmed_applied"}:
            return _applied_report(binding, idempotent_replay=True)
        code = "LEDGER_PREPARE_CONFLICT" if result.outcome == "conflict" else "LEDGER_PREPARE_FAILED"
        return _blocked_report(binding, code, persistence_performed=True)

    def finalize(
        self,
        binding: WorkflowApplicationLedgerBindingDTO,
        commit_proof: object,
        ledger_store: WorkflowApplicationLedgerStorePort,
    ) -> WorkflowApplicationLedgerReport:
        """Finalize only a prepared binding proven committed by the coordinator."""

        if not isinstance(commit_proof, _AuthoritativeWorkflowApplicationCommitProof) or not commit_proof._matches(binding):
            return _blocked_report(binding, "AUTHORITATIVE_COMMIT_PROOF_INVALID")
        try:
            result = ledger_store.finalize(binding, commit_proof)
        except Exception:
            return _blocked_report(binding, "LEDGER_FINALIZE_FAILED", persistence_performed=True)
        if not isinstance(result, WorkflowApplicationLedgerStoreWriteResult) or result.binding != binding:
            return _blocked_report(binding, "LEDGER_FINALIZE_RESULT_INVALID", persistence_performed=True)
        if result.outcome == "applied":
            return _applied_report(binding, idempotent_replay=False)
        if result.outcome == "confirmed_applied":
            return _applied_report(binding, idempotent_replay=True)
        if result.outcome == "missing":
            return _blocked_report(binding, "LEDGER_PREPARED_RECORD_MISSING", persistence_performed=True)
        code = "LEDGER_FINALIZE_CONFLICT" if result.outcome == "conflict" else "LEDGER_FINALIZE_FAILED"
        return _blocked_report(binding, code, persistence_performed=True)

    def lookup_applied(
        self,
        project_id: str,
        page_id: str,
        output_asset_id: str,
        ledger_store: WorkflowApplicationLedgerStorePort,
    ) -> WorkflowApplicationLedgerReport:
        """Return a unique applied proof for a logical Page.image descriptor."""

        values = _lookup_values(project_id, page_id, output_asset_id)
        if values is None:
            return _blocked_report(None, "LEDGER_APPLIED_LOOKUP_INVALID")
        try:
            result = ledger_store.lookup_applied(*values)
        except Exception:
            return _blocked_report(_lookup_binding(*values), "LEDGER_APPLIED_LOOKUP_FAILED")
        if not isinstance(result, WorkflowApplicationLedgerAppliedLookupResult):
            return _blocked_report(_lookup_binding(*values), "LEDGER_APPLIED_LOOKUP_RESULT_INVALID")
        if result.outcome == "found" and result.binding is not None and _matches_lookup(result.binding, *values):
            return _applied_report(result.binding, idempotent_replay=True, persistence_performed=False)
        code = {
            "missing": "LEDGER_APPLIED_PROOF_MISSING",
            "prepared": "LEDGER_APPLIED_PROOF_NOT_APPLIED",
            "ambiguous": "LEDGER_APPLIED_PROOF_AMBIGUOUS",
            "corrupt": "LEDGER_APPLIED_PROOF_CORRUPT",
        }.get(result.outcome, "LEDGER_APPLIED_LOOKUP_RESULT_INVALID")
        return _blocked_report(_lookup_binding(*values), code)

    def lookup_exact(
        self,
        binding: WorkflowApplicationLedgerBindingDTO,
        ledger_store: WorkflowApplicationLedgerStorePort,
    ) -> WorkflowApplicationLedgerExactLookupResult:
        """Read the lifecycle of one complete binding without reserving or mutating it."""

        if not _valid_binding(binding):
            return WorkflowApplicationLedgerExactLookupResult("corrupt")
        try:
            result = ledger_store.lookup_exact(binding)
        except Exception:
            return WorkflowApplicationLedgerExactLookupResult("corrupt")
        if not isinstance(result, WorkflowApplicationLedgerExactLookupResult):
            return WorkflowApplicationLedgerExactLookupResult("corrupt")
        return result

class LocalWorkflowApplicationLedgerStore(WorkflowApplicationLedgerStorePort):
    """Independent private SQLite owner for immutable workflow applications."""

    def __init__(self, owner_root: Path) -> None:
        self._root = _prepare_owner_root(owner_root)
        self._database_path = self._root / _DATABASE_FILENAME
        self._initialize_schema()

    def prepare(
        self, binding: WorkflowApplicationLedgerBindingDTO) -> WorkflowApplicationLedgerStoreWriteResult:
        connection: sqlite3.Connection | None = None
        try:
            connection = _open_ledger_connection(self._database_path)
            connection.execute("BEGIN IMMEDIATE")
            existing = self._by_attempt(connection, binding.attempt_id)
            if existing is not None:
                connection.rollback()
                return _existing_prepare_result(binding, existing)
            if not _valid_binding(binding):
                connection.rollback()
                return WorkflowApplicationLedgerStoreWriteResult(binding, "failed")
            reserved = self._by_authorization(connection, binding.authorization_id)
            if reserved is not None:
                connection.rollback()
                return WorkflowApplicationLedgerStoreWriteResult(binding, "conflict")
            self._insert(connection, binding, "prepared")
            connection.commit()
            return WorkflowApplicationLedgerStoreWriteResult(binding, "prepared")
        except Exception:
            _rollback_quietly(connection)
            return WorkflowApplicationLedgerStoreWriteResult(binding, "failed")
        finally:
            _close_quietly(connection)

    def finalize(
        self,
        binding: WorkflowApplicationLedgerBindingDTO,
        commit_proof: _AuthoritativeWorkflowApplicationCommitProof,
    ) -> WorkflowApplicationLedgerStoreWriteResult:
        connection: sqlite3.Connection | None = None
        try:
            if (
                not isinstance(commit_proof, _AuthoritativeWorkflowApplicationCommitProof)
                or not commit_proof._matches(binding)
            ):
                return WorkflowApplicationLedgerStoreWriteResult(binding, "failed")
            connection = _open_ledger_connection(self._database_path)
            connection.execute("BEGIN IMMEDIATE")
            existing = self._by_attempt(connection, binding.attempt_id)
            if existing is None:
                connection.rollback()
                return WorkflowApplicationLedgerStoreWriteResult(binding, "missing")
            if existing.binding != binding:
                connection.rollback()
                return WorkflowApplicationLedgerStoreWriteResult(binding, "conflict")
            if not _valid_binding(binding):
                connection.rollback()
                return WorkflowApplicationLedgerStoreWriteResult(binding, "failed")
            if existing.lifecycle == "applied":
                connection.rollback()
                return WorkflowApplicationLedgerStoreWriteResult(binding, "confirmed_applied")
            if existing.lifecycle != "prepared":
                connection.rollback()
                return WorkflowApplicationLedgerStoreWriteResult(binding, "failed")
            payload = _canonical_payload(binding, "applied")
            binding_digest = _digest(payload)
            if _ledger_schema_version(connection) == _R26_SCHEMA_VERSION:
                cursor = connection.execute(
                    f"UPDATE {_TABLE_NAME} SET lifecycle = ?, binding_json = ?, binding_digest = ?, "
                    "r26_protocol_binding_digest = ? WHERE attempt_id = ? AND lifecycle = 'prepared'",
                    (
                        "applied",
                        payload,
                        binding_digest,
                        _r26_protocol_digest(binding_digest, existing.marker_version),
                        binding.attempt_id,
                    ),
                )
            else:
                cursor = connection.execute(
                    f"UPDATE {_TABLE_NAME} SET lifecycle = ?, binding_json = ?, binding_digest = ? "
                    "WHERE attempt_id = ? AND lifecycle = 'prepared'",
                    ("applied", payload, binding_digest, binding.attempt_id),
                )
            if cursor.rowcount != 1:
                raise ValueError("workflow application ledger unavailable")
            connection.commit()
            return WorkflowApplicationLedgerStoreWriteResult(binding, "applied")
        except Exception:
            _rollback_quietly(connection)
            return WorkflowApplicationLedgerStoreWriteResult(binding, "failed")
        finally:
            _close_quietly(connection)

    def lookup_applied(
        self,
        project_id: str,
        page_id: str,
        output_asset_id: str,
    ) -> WorkflowApplicationLedgerAppliedLookupResult:
        values = _lookup_values(project_id, page_id, output_asset_id)
        if values is None:
            return WorkflowApplicationLedgerAppliedLookupResult("corrupt")
        connection: sqlite3.Connection | None = None
        try:
            connection = _open_ledger_connection(self._database_path)
            rows = connection.execute(
                f"SELECT {_select_columns(connection)} FROM {_TABLE_NAME} "
                "WHERE project_id = ? AND page_id = ? AND output_asset_id = ?",
                values,
            ).fetchall()
            if not rows:
                return WorkflowApplicationLedgerAppliedLookupResult("missing")
            records = tuple(_record_from_row(row) for row in rows)
            if any(record is None for record in records):
                return WorkflowApplicationLedgerAppliedLookupResult("corrupt")
            verified = tuple(record for record in records if record is not None)
            if len(verified) != 1:
                return WorkflowApplicationLedgerAppliedLookupResult("ambiguous")
            record = verified[0]
            if record.lifecycle != "applied":
                return WorkflowApplicationLedgerAppliedLookupResult("prepared")
            return WorkflowApplicationLedgerAppliedLookupResult("found", record.binding)
        except Exception:
            return WorkflowApplicationLedgerAppliedLookupResult("corrupt")
        finally:
            _close_quietly(connection)

    def lookup_exact(
        self, binding: WorkflowApplicationLedgerBindingDTO
    ) -> WorkflowApplicationLedgerExactLookupResult:
        if not _valid_binding(binding):
            return WorkflowApplicationLedgerExactLookupResult("corrupt")
        connection: sqlite3.Connection | None = None
        try:
            connection = _open_ledger_connection(self._database_path)
            by_attempt = self._by_attempt(connection, binding.attempt_id)
            by_authorization = self._by_authorization(connection, binding.authorization_id)
            records = tuple(
                record
                for record in (by_attempt, by_authorization)
                if record is not None
            )
            if not records:
                return WorkflowApplicationLedgerExactLookupResult("missing")
            if any(record.binding != binding for record in records):
                return WorkflowApplicationLedgerExactLookupResult("conflict")
            if len(records) == 2 and records[0] != records[1]:
                return WorkflowApplicationLedgerExactLookupResult("conflict")
            lifecycle = records[0].lifecycle
            if lifecycle == "prepared":
                return WorkflowApplicationLedgerExactLookupResult("prepared")
            if lifecycle == "applied":
                return WorkflowApplicationLedgerExactLookupResult("applied")
            return WorkflowApplicationLedgerExactLookupResult("corrupt")
        except Exception:
            return WorkflowApplicationLedgerExactLookupResult("corrupt")
        finally:
            _close_quietly(connection)

    def _observe_exact_readonly_v1(
        self, binding: object
    ) -> _WorkflowApplicationLedgerObservationV1:
        """Observe exactly one binding without invoking any Ledger write path.

        This is R21's private low-level boundary.  It deliberately does not
        reuse ``lookup_exact``: that legacy operation collapses all failures
        into ``corrupt`` and opens the owner through the writable connection
        helper.
        """

        if type(self) is not LocalWorkflowApplicationLedgerStore or not _valid_r21_binding(binding):
            return _WorkflowApplicationLedgerObservationV1("AUTHORITY_REJECTED")
        exact_binding = cast(WorkflowApplicationLedgerBindingDTO, binding)
        database_path = self._database_path
        if not _r21_regular_file(database_path):
            return _WorkflowApplicationLedgerObservationV1("RECOVERY_REQUIRED")

        connection: sqlite3.Connection | None = None
        began = False
        try:
            connection = _open_r21_readonly_connection(database_path)
            connection.execute("PRAGMA query_only = ON")
            query_only = connection.execute("PRAGMA query_only").fetchall()
            if query_only != [(1,)]:
                return _WorkflowApplicationLedgerObservationV1("RECOVERY_REQUIRED")
            connection.execute("BEGIN")
            began = True
            _validate_r21_schema(connection)
            rows = connection.execute(
                f"SELECT {_select_columns(connection)} FROM {_TABLE_NAME} "
                "WHERE attempt_id = ? OR authorization_id = ?",
                (exact_binding.attempt_id, exact_binding.authorization_id),
            ).fetchall()
            observation = _r21_observation_from_rows(exact_binding, rows)
            connection.commit()
            began = False
            return observation
        except _R21CorruptError:
            return _WorkflowApplicationLedgerObservationV1("CORRUPT")
        except sqlite3.DatabaseError as error:
            return _WorkflowApplicationLedgerObservationV1(_r21_sqlite_outcome(error))
        except (OSError, ValueError, TypeError):
            return _WorkflowApplicationLedgerObservationV1("RECOVERY_REQUIRED")
        finally:
            if began:
                _rollback_quietly(connection)
            _close_quietly(connection)

    def _prepare_r26_protocol_v1_under_existing_transaction(
        self,
        binding: object,
        capability: object,
        *,
        repository: object,
        root: object = None,
    ) -> _R26ProtocolPreparationResultV1:
        """Create or confirm an exact marker-1 PREPARED row in one transaction.

        The public-compatible binding bytes stay unchanged.  Only the opaque
        private capability can select marker ``1``; generic prepare continues
        to create marker ``0``.
        """

        if (
            type(self) is not LocalWorkflowApplicationLedgerStore
            or not _valid_binding(binding)
            or not _consume_r26_preparation_capability(capability, self, repository, root)
        ):
            return _R26ProtocolPreparationResultV1(
                cast(WorkflowApplicationLedgerBindingDTO, binding), "AUTHORITY_REJECTED"
            )
        exact_binding = cast(WorkflowApplicationLedgerBindingDTO, binding)
        connection: sqlite3.Connection | None = None
        try:
            self._migrate_r26_protocol_v1()
            connection = _open_ledger_connection(self._database_path)
            connection.execute("BEGIN IMMEDIATE")
            existing = self._by_attempt(connection, exact_binding.attempt_id)
            if existing is not None:
                connection.rollback()
                if existing.marker_version != 1:
                    return _R26ProtocolPreparationResultV1(exact_binding, "conflict")
                return _existing_r26_prepare_result(exact_binding, existing)
            reserved = self._by_authorization(connection, exact_binding.authorization_id)
            if reserved is not None:
                connection.rollback()
                return _R26ProtocolPreparationResultV1(exact_binding, "conflict")
            self._insert(connection, exact_binding, "prepared", marker_version=1)
            connection.commit()
            return _R26ProtocolPreparationResultV1(exact_binding, "prepared")
        except _R26MarkerCorruptError:
            _rollback_quietly(connection)
            return _R26ProtocolPreparationResultV1(exact_binding, "CORRUPT")
        except _R26MarkerUnavailableError:
            _rollback_quietly(connection)
            return _R26ProtocolPreparationResultV1(exact_binding, "UNAVAILABLE")
        except _R21CorruptError:
            _rollback_quietly(connection)
            return _R26ProtocolPreparationResultV1(exact_binding, "CORRUPT")
        except sqlite3.DatabaseError as error:
            _rollback_quietly(connection)
            return _R26ProtocolPreparationResultV1(
                exact_binding,
                "CORRUPT" if _r21_sqlite_outcome(error) == "CORRUPT" else "UNAVAILABLE",
            )
        except (OSError, TypeError):
            _rollback_quietly(connection)
            return _R26ProtocolPreparationResultV1(exact_binding, "UNAVAILABLE")
        except ValueError:
            _rollback_quietly(connection)
            return _R26ProtocolPreparationResultV1(exact_binding, "CORRUPT")
        finally:
            _close_quietly(connection)

    def _observe_r26_protocol_exact_readonly_v2(
        self,
        binding: object,
        capability: object = None,
        *,
        repository: object = None,
        root: object = None,
    ) -> _R26ProtocolObservationV2:
        """Read one v2 marker without any mutation, migration, or fallback."""

        if (
            type(self) is not LocalWorkflowApplicationLedgerStore
            or not _valid_r21_binding(binding)
            or not _consume_r26_observation_capability(capability, self, repository, root)
        ):
            return _R26ProtocolObservationV2("AUTHORITY_REJECTED")
        exact_binding = cast(WorkflowApplicationLedgerBindingDTO, binding)
        if not _r21_regular_file(self._database_path):
            return _R26ProtocolObservationV2("RECOVERY_REQUIRED")
        connection: sqlite3.Connection | None = None
        began = False
        try:
            connection = _open_r21_readonly_connection(self._database_path)
            connection.execute("PRAGMA query_only = ON")
            if connection.execute("PRAGMA query_only").fetchall() != [(1,)]:
                return _R26ProtocolObservationV2("RECOVERY_REQUIRED")
            connection.execute("BEGIN")
            began = True
            _validate_r26_schema_v2(connection)
            rows = connection.execute(
                f"SELECT {_SELECT_COLUMNS} FROM {_TABLE_NAME} "
                "WHERE attempt_id = ? OR authorization_id = ?",
                (exact_binding.attempt_id, exact_binding.authorization_id),
            ).fetchall()
            observation = _r26_observation_from_rows(exact_binding, rows)
            connection.commit()
            began = False
            return observation
        except _R21CorruptError:
            return _R26ProtocolObservationV2("CORRUPT")
        except sqlite3.DatabaseError as error:
            return _R26ProtocolObservationV2(_r21_sqlite_outcome(error))
        except (OSError, ValueError, TypeError):
            return _R26ProtocolObservationV2("RECOVERY_REQUIRED")
        finally:
            if began:
                _rollback_quietly(connection)
            _close_quietly(connection)

    def _observe_r26_protocol_authenticated_readonly_v1(
        self,
        binding: object,
        capability: object = None,
        *,
        repository: object = None,
        root: object = None,
    ) -> _R26AuthenticatedProtocolObservationV1 | _R26ProtocolObservationV2:
        """Bind one read-only R21 observation to its exact private source."""

        observation = self._observe_r26_protocol_exact_readonly_v2(
            binding, capability, repository=repository, root=root
        )
        if (
            type(self) is not LocalWorkflowApplicationLedgerStore
            or type(binding) is not WorkflowApplicationLedgerBindingDTO
            or _R26_READY_ROOTS.get(id(root)) != (root, self, repository)
        ):
            return observation
        authenticated = object.__new__(_R26AuthenticatedProtocolObservationV1)
        object.__setattr__(authenticated, "_binding", binding)
        object.__setattr__(authenticated, "_observation", observation)
        object.__setattr__(authenticated, "_repository", repository)
        object.__setattr__(authenticated, "_root", root)
        object.__setattr__(authenticated, "_seal", _R26_PREPARATION_ISSUER)
        object.__setattr__(authenticated, "_store", self)
        object.__setattr__(authenticated, "_used", False)
        with _R26_CAPABILITY_LOCK:
            _R26_AUTHENTICATED_OBSERVATIONS[authenticated] = (
                authenticated,
                self,
                repository,
                root,
                binding,
                observation,
            )
        return authenticated

    def _initialize_schema(self) -> None:
        connection: sqlite3.Connection | None = None
        try:
            connection = _open_ledger_connection(self._database_path)
            connection.execute("BEGIN IMMEDIATE")
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            has_tables = _has_user_tables(connection)
            if version == 0 and not has_tables:
                connection.execute(_R21_DDL_V1)
                connection.execute("PRAGMA user_version = 1")
                connection.commit()
                return
            if version == 1 and _schema_is_valid_v1(connection):
                connection.commit()
                return
            if version == _R26_SCHEMA_VERSION and _schema_is_valid_v2(connection):
                connection.commit()
                return
            raise ValueError("workflow application ledger unavailable")
        except (sqlite3.Error, TypeError, ValueError) as error:
            _rollback_quietly(connection)
            raise ValueError("workflow application ledger unavailable") from error
        finally:
            _close_quietly(connection)

    def _migrate_r26_protocol_v1(self) -> None:
        """Perform the private v1-to-v2 marker migration only after root READY."""

        connection: sqlite3.Connection | None = None
        try:
            connection = _open_ledger_connection(self._database_path)
            connection.execute("BEGIN IMMEDIATE")
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if version == 1:
                if not _schema_is_valid_v1(connection):
                    raise _R21CorruptError()
                _migrate_v1_to_v2(connection)
            elif version != _R26_SCHEMA_VERSION or not _schema_is_valid_v2(connection):
                raise _R21CorruptError()
            connection.commit()
        except _R21CorruptError as error:
            _rollback_quietly(connection)
            raise _R26MarkerCorruptError() from error
        except sqlite3.DatabaseError as error:
            _rollback_quietly(connection)
            if _r21_sqlite_outcome(error) == "CORRUPT":
                raise _R26MarkerCorruptError() from error
            raise _R26MarkerUnavailableError() from error
        except OSError as error:
            _rollback_quietly(connection)
            raise _R26MarkerUnavailableError() from error
        except (TypeError, ValueError) as error:
            _rollback_quietly(connection)
            raise _R26MarkerCorruptError() from error
        finally:
            _close_quietly(connection)

    @staticmethod
    def _by_attempt(connection: sqlite3.Connection, attempt_id: str) -> _LedgerRecord | None:
        row = connection.execute(
            f"SELECT {_select_columns(connection)} FROM {_TABLE_NAME} WHERE attempt_id = ?",
            (attempt_id,),
        ).fetchone()
        if row is None:
            return None
        record = _record_from_row(row)
        if record is None:
            raise ValueError("workflow application ledger unavailable")
        return record

    @staticmethod
    def _by_authorization(connection: sqlite3.Connection, authorization_id: str) -> _LedgerRecord | None:
        row = connection.execute(
            f"SELECT {_select_columns(connection)} FROM {_TABLE_NAME} WHERE authorization_id = ?",
            (authorization_id,),
        ).fetchone()
        if row is None:
            return None
        record = _record_from_row(row)
        if record is None:
            raise ValueError("workflow application ledger unavailable")
        return record

    @staticmethod
    def _insert(
        connection: sqlite3.Connection,
        binding: WorkflowApplicationLedgerBindingDTO,
        lifecycle: Lifecycle,
        *,
        marker_version: int = 0,
    ) -> None:
        payload = _canonical_payload(binding, lifecycle)
        if _ledger_schema_version(connection) == 1:
            if marker_version != 0:
                raise ValueError("workflow application ledger unavailable")
            connection.execute(
                f"INSERT INTO {_TABLE_NAME} ("
                "attempt_id, authorization_id, project_id, page_id, target_page_reference, "
                "provider_reference, output_asset_id, source_state, target_state, lifecycle, "
                "binding_json, binding_digest) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (*_binding_columns(binding), lifecycle, payload, _digest(payload)),
            )
            return
        protocol_digest = _r26_protocol_digest(_digest(payload), marker_version)
        connection.execute(
            f"INSERT INTO {_TABLE_NAME} ("
            "attempt_id, authorization_id, project_id, page_id, target_page_reference, "
            "provider_reference, output_asset_id, source_state, target_state, lifecycle, "
            "binding_json, binding_digest, post_cas_attestation_requirement_version, "
            "r26_protocol_binding_digest) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (*_binding_columns(binding), lifecycle, payload, _digest(payload), marker_version, protocol_digest),
        )

@dataclass(frozen=True, slots=True)
class _LedgerRecord:
    binding: WorkflowApplicationLedgerBindingDTO
    lifecycle: Lifecycle
    marker_version: int = 0
    protocol_binding_digest: str = ""


class _R21CorruptError(Exception):
    """Internal marker for a reached-but-invalid durable Ledger."""


class _R26MarkerCorruptError(Exception):
    """The private marker migration reached durable corruption."""


class _R26MarkerUnavailableError(Exception):
    """The private marker migration could not obtain durable access."""


def _valid_r21_binding(binding: object) -> bool:
    """Accept only the existing closed DTO, including an equal reconstruction."""

    return type(binding) is WorkflowApplicationLedgerBindingDTO and _valid_binding(binding)


def _r21_regular_file(path: Path) -> bool:
    try:
        return path.is_file() and not path.is_symlink()
    except OSError:
        return False


def _open_r21_readonly_connection(database_path: Path) -> sqlite3.Connection:
    """Open only the fixed owner database through SQLite's read-only URI."""

    if not database_path.is_absolute() or not _r21_regular_file(database_path):
        raise OSError("authoritative ledger database is unavailable")
    return sqlite3.connect(
        f"{database_path.as_uri()}?mode=ro",
        uri=True,
        timeout=0.0,
        isolation_level=None,
    )


def _r21_sqlite_outcome(error: sqlite3.DatabaseError) -> _ObservationOutcome:
    """Keep reached-byte corruption distinct from unavailable read access."""

    code = getattr(error, "sqlite_errorcode", None)
    if code in {sqlite3.SQLITE_CORRUPT, sqlite3.SQLITE_NOTADB}:
        return "CORRUPT"
    return "RECOVERY_REQUIRED"


def _validate_r21_schema(connection: sqlite3.Connection) -> None:
    """Accept only exact v1 or exact migrated-v2 lifecycle schemas."""

    version = connection.execute("PRAGMA user_version").fetchall()
    if version == [(1,)]:
        _validate_schema(connection, version=1)
        return
    if version == [(2,)]:
        _validate_schema(connection, version=2)
        return
    raise _R21CorruptError()


def _validate_r26_schema_v2(connection: sqlite3.Connection) -> None:
    """Require the exact v2 marker schema; v1 is never marker-compatible."""

    if connection.execute("PRAGMA user_version").fetchall() != [(2,)]:
        raise _R21CorruptError()
    _validate_schema(connection, version=2)


def _validate_schema(connection: sqlite3.Connection, *, version: int) -> None:
    """Require exact known Ledger schema bytes and autoindexes."""

    try:
        journal_mode = connection.execute("PRAGMA journal_mode").fetchall()
        objects = connection.execute(
            "SELECT type, name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
        ).fetchall()
        ddl_rows = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?", (_TABLE_NAME,)
        ).fetchall()
        table_info = connection.execute(f"PRAGMA table_info({_TABLE_NAME})").fetchall()
        index_list = connection.execute(f"PRAGMA index_list({_TABLE_NAME})").fetchall()
    except sqlite3.DatabaseError as error:
        if _r21_sqlite_outcome(error) == "CORRUPT":
            raise _R21CorruptError() from error
        raise

    expected_columns_v1 = (
        ("attempt_id", "TEXT", 0, None, 1),
        ("authorization_id", "TEXT", 1, None, 0),
        ("project_id", "TEXT", 1, None, 0),
        ("page_id", "TEXT", 1, None, 0),
        ("target_page_reference", "TEXT", 1, None, 0),
        ("provider_reference", "TEXT", 1, None, 0),
        ("output_asset_id", "TEXT", 1, None, 0),
        ("source_state", "TEXT", 1, None, 0),
        ("target_state", "TEXT", 1, None, 0),
        ("lifecycle", "TEXT", 1, None, 0),
        ("binding_json", "TEXT", 1, None, 0),
        ("binding_digest", "TEXT", 1, None, 0),
    )
    expected_columns_v2 = expected_columns_v1 + (
        ("post_cas_attestation_requirement_version", "INTEGER", 1, "0", 0),
        ("r26_protocol_binding_digest", "TEXT", 1, "''", 0),
    )
    expected_columns = expected_columns_v1 if version == 1 else expected_columns_v2
    expected_ddl = _R21_DDL_V1 if version == 1 else _R26_DDL_V2
    columns = tuple((row[1], row[2], row[3], row[4], row[5]) for row in table_info)
    if (
        journal_mode != [("delete",)]
        or objects != [("table", _TABLE_NAME)]
        or len(ddl_rows) != 1
        or type(ddl_rows[0][0]) is not str
        or _without_ascii_whitespace(ddl_rows[0][0]) != _without_ascii_whitespace(expected_ddl)
        or columns != expected_columns
    ):
        raise _R21CorruptError()

    expected_indexes = (
        (f"sqlite_autoindex_{_TABLE_NAME}_1", 1, "pk", 0, "attempt_id"),
        (f"sqlite_autoindex_{_TABLE_NAME}_2", 1, "u", 0, "authorization_id"),
    )
    observed_indexes: list[tuple[str, int, str, int, str]] = []
    for index in index_list:
        if len(index) != 5 or type(index[1]) is not str:
            raise _R21CorruptError()
        name = index[1]
        columns_for_index = connection.execute(f"PRAGMA index_info({name})").fetchall()
        if len(columns_for_index) != 1 or columns_for_index[0][0] != 0:
            raise _R21CorruptError()
        observed_indexes.append((name, index[2], index[3], index[4], columns_for_index[0][2]))
    if tuple(sorted(observed_indexes)) != expected_indexes:
        raise _R21CorruptError()


def _without_ascii_whitespace(value: str) -> str:
    return "".join(character for character in value if character not in " \t\r\n\f\v")


def _r21_observation_from_rows(
    binding: WorkflowApplicationLedgerBindingDTO,
    rows: object,
) -> _WorkflowApplicationLedgerObservationV1:
    if not isinstance(rows, list):
        raise _R21CorruptError()
    if not rows:
        return _WorkflowApplicationLedgerObservationV1("MISSING")
    if len(rows) > 2:
        raise _R21CorruptError()
    records = tuple(_record_from_row(row) for row in rows)
    if any(record is None for record in records):
        raise _R21CorruptError()
    exact_records = tuple(record for record in records if record is not None)
    if len(exact_records) == 2 and exact_records[0] != exact_records[1]:
        return _WorkflowApplicationLedgerObservationV1("CONFLICT")
    if any(record.binding != binding for record in exact_records):
        return _WorkflowApplicationLedgerObservationV1("CONFLICT")
    lifecycle = exact_records[0].lifecycle
    if lifecycle == "prepared":
        return _WorkflowApplicationLedgerObservationV1("PREPARED")
    if lifecycle == "applied":
        return _WorkflowApplicationLedgerObservationV1("APPLIED")
    raise _R21CorruptError()


def _r26_observation_from_rows(
    binding: WorkflowApplicationLedgerBindingDTO,
    rows: object,
) -> _R26ProtocolObservationV2:
    if not isinstance(rows, list):
        raise _R21CorruptError()
    if not rows:
        return _R26ProtocolObservationV2("MISSING")
    if len(rows) > 2:
        raise _R21CorruptError()
    records = tuple(_record_from_row(row) for row in rows)
    if any(record is None for record in records):
        raise _R21CorruptError()
    exact_records = tuple(record for record in records if record is not None)
    if len(exact_records) == 2 and exact_records[0] != exact_records[1]:
        return _R26ProtocolObservationV2("CONFLICT")
    if any(record.binding != binding for record in exact_records):
        return _R26ProtocolObservationV2("CONFLICT")
    record = exact_records[0]
    if record.lifecycle == "applied":
        return _R26ProtocolObservationV2("APPLIED")
    if record.lifecycle != "prepared":
        raise _R21CorruptError()
    return _R26ProtocolObservationV2(
        "PREPARED", record.marker_version, record.protocol_binding_digest
    )


def _binding_from_eligibility(
    report: DurableEvidenceWorkflowBindingReport,
    authorization: WorkflowApplicationAuthorizationDTO,
) -> WorkflowApplicationLedgerBindingDTO | None:
    if (
        report.status != "eligible"
        or report.eligible is not True
        or report.analysis_only is not True
        or report.findings
        or authorization.source_state != "PromptBuilt"
        or authorization.target_state != "Generated"
    ):
        return None
    if (
        report.attempt_id != authorization.attempt_id
        or report.provider_reference != authorization.provider_reference
        or report.project_id != authorization.project_id
        or report.page_id != authorization.page_id
        or report.target_page_reference != authorization.target_page_reference
    ):
        return None
    try:
        return WorkflowApplicationLedgerBindingDTO(
            attempt_id=authorization.attempt_id,
            authorization_id=authorization.authorization_id,
            project_id=authorization.project_id,
            page_id=authorization.page_id,
            target_page_reference=authorization.target_page_reference,
            provider_reference=authorization.provider_reference,
            output_asset_id=report.output_asset_id,
            source_state=authorization.source_state,
            target_state=authorization.target_state,
        )
    except ValueError:
        return None


def _existing_prepare_result(
    binding: WorkflowApplicationLedgerBindingDTO,
    existing: _LedgerRecord,
) -> WorkflowApplicationLedgerStoreWriteResult:
    if existing.binding != binding:
        return WorkflowApplicationLedgerStoreWriteResult(binding, "conflict")
    if existing.lifecycle == "prepared":
        return WorkflowApplicationLedgerStoreWriteResult(binding, "confirmed_prepared")
    if existing.lifecycle == "applied":
        return WorkflowApplicationLedgerStoreWriteResult(binding, "confirmed_applied")
    return WorkflowApplicationLedgerStoreWriteResult(binding, "failed")


def _record_from_row(row: object) -> _LedgerRecord | None:
    if not isinstance(row, tuple) or len(row) not in {12, 14}:
        return None
    values = row[:9]
    lifecycle = row[9]
    payload = row[10]
    digest = row[11]
    if (
        not all(isinstance(value, str) for value in values)
        or lifecycle not in _LIFECYCLES
        or not isinstance(payload, str)
        or not isinstance(digest, str)
    ):
        return None
    try:
        binding = WorkflowApplicationLedgerBindingDTO(
            attempt_id=values[0],
            authorization_id=values[1],
            project_id=values[2],
            page_id=values[3],
            target_page_reference=values[4],
            provider_reference=values[5],
            output_asset_id=values[6],
            source_state=values[7],
            target_state=values[8],
        )
    except ValueError:
        return None
    canonical = _canonical_payload(binding, lifecycle)
    if payload != canonical or digest != _digest(canonical):
        return None
    if len(row) == 12:
        return _LedgerRecord(binding, lifecycle, 0, _r26_protocol_digest(digest, 0))
    marker_version = row[12]
    protocol_digest = row[13]
    if (
        type(marker_version) is not int
        or marker_version not in {0, 1}
        or type(protocol_digest) is not str
        or protocol_digest != _r26_protocol_digest(digest, marker_version)
    ):
        return None
    return _LedgerRecord(binding, lifecycle, marker_version, protocol_digest)


def _binding_columns(binding: WorkflowApplicationLedgerBindingDTO) -> tuple[str, ...]:
    return (
        binding.attempt_id,
        binding.authorization_id,
        binding.project_id,
        binding.page_id,
        binding.target_page_reference,
        binding.provider_reference,
        binding.output_asset_id,
        binding.source_state,
        binding.target_state,
    )


def _valid_binding(binding: object) -> bool:
    if not isinstance(binding, WorkflowApplicationLedgerBindingDTO):
        return False
    try:
        return WorkflowApplicationLedgerBindingDTO.model_validate(binding.model_dump()) == binding
    except ValueError:
        return False


def _canonical_payload(binding: WorkflowApplicationLedgerBindingDTO, lifecycle: Lifecycle) -> str:
    value = {**binding.model_dump(mode="json"), "lifecycle": lifecycle}
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _digest(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _r26_protocol_digest(ledger_binding_digest: str, marker_version: int) -> str:
    """Return the frozen marker digest without changing public binding bytes."""

    if not _sha256_digest(ledger_binding_digest) or marker_version not in {0, 1}:
        raise ValueError("r26 protocol marker is invalid")
    payload = json.dumps(
        {
            "ledger_binding_digest": ledger_binding_digest,
            "post_cas_attestation_requirement_version": marker_version,
            "schema_id": "manga_director.r26.protocol-marker",
            "schema_version": 1,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    )
    return _digest(payload)


def _sha256_digest(value: object) -> bool:
    return type(value) is str and len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def _lookup_values(project_id: str, page_id: str, output_asset_id: str) -> tuple[str, str, str] | None:
    try:
        return (
            _logical_reference(project_id),
            _logical_reference(page_id),
            _logical_reference(output_asset_id),
        )
    except ValueError:
        return None


def _lookup_binding(project_id: str, page_id: str, output_asset_id: str) -> WorkflowApplicationLedgerBindingDTO | None:
    # A lookup failure has no authoritative attempt or authorization identity.
    del project_id, page_id, output_asset_id
    return None


def _matches_lookup(
    binding: WorkflowApplicationLedgerBindingDTO,
    project_id: str,
    page_id: str,
    output_asset_id: str,
) -> bool:
    return (
        binding.project_id == project_id
        and binding.page_id == page_id
        and binding.output_asset_id == output_asset_id
    )


def _prepared_report(
    binding: WorkflowApplicationLedgerBindingDTO,
    *,
    idempotent_replay: bool,
) -> WorkflowApplicationLedgerReport:
    return WorkflowApplicationLedgerReport(
        binding=binding,
        lifecycle="prepared",
        status="prepared",
        prepared=True,
        applied=False,
        idempotent_replay=idempotent_replay,
        persistence_performed=True,
    )


def _applied_report(
    binding: WorkflowApplicationLedgerBindingDTO,
    *,
    idempotent_replay: bool,
    persistence_performed: bool = True,
) -> WorkflowApplicationLedgerReport:
    return WorkflowApplicationLedgerReport(
        binding=binding,
        lifecycle="applied",
        status="applied",
        prepared=False,
        applied=True,
        idempotent_replay=idempotent_replay,
        persistence_performed=persistence_performed,
    )


def _blocked_report(
    binding: WorkflowApplicationLedgerBindingDTO | None,
    code: str,
    *,
    persistence_performed: bool = False,
) -> WorkflowApplicationLedgerReport:
    return WorkflowApplicationLedgerReport(
        binding=binding,
        findings=(_finding(code, binding),),
        status="blocked",
        prepared=False,
        applied=False,
        idempotent_replay=False,
        persistence_performed=persistence_performed,
    )


def _finding(
    code: str,
    binding: WorkflowApplicationLedgerBindingDTO | None,
) -> WorkflowApplicationLedgerFindingDTO:
    values = binding.model_dump() if binding is not None else {}
    return WorkflowApplicationLedgerFindingDTO(
        code=code,
        status="blocked",
        message=code.replace("_", " ").lower(),
        attempt_id=values.get("attempt_id", ""),
        authorization_id=values.get("authorization_id", ""),
        project_id=values.get("project_id", ""),
        page_id=values.get("page_id", ""),
        target_page_reference=values.get("target_page_reference", ""),
        provider_reference=values.get("provider_reference", ""),
        output_asset_id=values.get("output_asset_id", ""),
    )


def _prepare_owner_root(owner_root: Path) -> Path:
    if not owner_root.is_absolute():
        raise ValueError("workflow application ledger unavailable")
    try:
        owner_root.mkdir(parents=True, exist_ok=True)
        return owner_root.resolve(strict=True)
    except OSError as error:
        raise ValueError("workflow application ledger unavailable") from error


def _has_user_tables(connection: sqlite3.Connection) -> bool:
    return bool(
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchone()
    )


def _schema_is_valid_v1(connection: sqlite3.Connection) -> bool:
    rows = connection.execute(f"PRAGMA table_info({_TABLE_NAME})").fetchall()
    expected = (
        "attempt_id",
        "authorization_id",
        "project_id",
        "page_id",
        "target_page_reference",
        "provider_reference",
        "output_asset_id",
        "source_state",
        "target_state",
        "lifecycle",
        "binding_json",
        "binding_digest",
    )
    if tuple(row[1] for row in rows) != expected:
        return False
    primary_keys = tuple(row[1] for row in rows if row[5] == 1)
    if primary_keys != ("attempt_id",):
        return False
    indexes = connection.execute(f"PRAGMA index_list({_TABLE_NAME})").fetchall()
    for index in indexes:
        if index[2] != 1:
            continue
        columns = tuple(
            row[2]
            for row in connection.execute(f"PRAGMA index_info({index[1]})").fetchall()
        )
        if columns == ("authorization_id",):
            return True
    return False


def _schema_is_valid_v2(connection: sqlite3.Connection) -> bool:
    try:
        _validate_r26_schema_v2(connection)
    except (sqlite3.DatabaseError, _R21CorruptError):
        return False
    return True


def _ledger_schema_version(connection: sqlite3.Connection) -> int:
    value = connection.execute("PRAGMA user_version").fetchone()
    if not isinstance(value, tuple) or len(value) != 1 or type(value[0]) is not int:
        raise ValueError("workflow application ledger unavailable")
    return value[0]


def _select_columns(connection: sqlite3.Connection) -> str:
    version = _ledger_schema_version(connection)
    if version == 1:
        return _V1_SELECT_COLUMNS
    if version == _R26_SCHEMA_VERSION:
        return _SELECT_COLUMNS
    raise ValueError("workflow application ledger unavailable")


def _migrate_v1_to_v2(connection: sqlite3.Connection) -> None:
    """Atomically extend every valid v1 row with its immutable marker-0 fact."""

    _validate_schema(connection, version=1)
    connection.execute(
        f"ALTER TABLE {_TABLE_NAME} ADD COLUMN "
        "post_cas_attestation_requirement_version INTEGER NOT NULL DEFAULT 0 "
        "CHECK(post_cas_attestation_requirement_version IN (0, 1))"
    )
    connection.execute(
        f"ALTER TABLE {_TABLE_NAME} ADD COLUMN r26_protocol_binding_digest TEXT NOT NULL DEFAULT ''"
    )
    rows = connection.execute(
        f"SELECT attempt_id, authorization_id, project_id, page_id, target_page_reference, "
        "provider_reference, output_asset_id, source_state, target_state, lifecycle, "
        f"binding_json, binding_digest FROM {_TABLE_NAME}"
    ).fetchall()
    for row in rows:
        record = _record_from_row(row)
        if record is None:
            raise ValueError("workflow application ledger unavailable")
        cursor = connection.execute(
            f"UPDATE {_TABLE_NAME} SET r26_protocol_binding_digest = ? "
            "WHERE attempt_id = ? AND authorization_id = ? "
            "AND post_cas_attestation_requirement_version = 0 AND r26_protocol_binding_digest = ''",
            (record.protocol_binding_digest, record.binding.attempt_id,
             record.binding.authorization_id),
        )
        if cursor.rowcount != 1:
            raise ValueError("workflow application ledger unavailable")
    connection.execute(f"PRAGMA user_version = {_R26_SCHEMA_VERSION}")
    _validate_r26_schema_v2(connection)
    verified = connection.execute(f"SELECT {_SELECT_COLUMNS} FROM {_TABLE_NAME}").fetchall()
    if any(_record_from_row(row) is None for row in verified):
        raise ValueError("workflow application ledger unavailable")


def _issue_r26_protocol_v1_preparation_capability(
    ledger_store: object,
    repository: object,
    *,
    root: object,
    _issuer: object,
) -> _R26ProtocolV1PreparationCapability:
    """Mint one private capability only for a retained canonical owner tuple."""

    if _issuer is not _R26_PREPARATION_ISSUER or type(ledger_store) is not LocalWorkflowApplicationLedgerStore:
        raise ValueError("AUTHORITY_REJECTED")
    with _R26_CAPABILITY_LOCK:
        if _R26_READY_ROOTS.get(id(root)) != (root, ledger_store, repository):
            raise ValueError("AUTHORITY_REJECTED")
        capability = object.__new__(_R26ProtocolV1PreparationCapability)
        object.__setattr__(capability, "_issuer", _issuer)
        object.__setattr__(capability, "_store", ledger_store)
        object.__setattr__(capability, "_repository", repository)
        object.__setattr__(capability, "_root", root)
        object.__setattr__(capability, "_used", False)
        _R26_PREPARATION_CAPABILITIES[id(capability)] = (
            capability,
            ledger_store,
            repository,
            root,
        )
        return capability


def _issue_r26_protocol_v1_observation_capability(
    ledger_store: object,
    repository: object,
    *,
    root: object,
    _issuer: object,
) -> _R26ProtocolV1ObservationCapability:
    """Mint one read-only marker authority for an exact READY private root."""

    if _issuer is not _R26_PREPARATION_ISSUER or type(ledger_store) is not LocalWorkflowApplicationLedgerStore:
        raise ValueError("AUTHORITY_REJECTED")
    with _R26_CAPABILITY_LOCK:
        if _R26_READY_ROOTS.get(id(root)) != (root, ledger_store, repository):
            raise ValueError("AUTHORITY_REJECTED")
        capability = object.__new__(_R26ProtocolV1ObservationCapability)
        object.__setattr__(capability, "_issuer", _issuer)
        object.__setattr__(capability, "_store", ledger_store)
        object.__setattr__(capability, "_repository", repository)
        object.__setattr__(capability, "_root", root)
        object.__setattr__(capability, "_used", False)
        _R26_OBSERVATION_CAPABILITIES[id(capability)] = (
            capability,
            ledger_store,
            repository,
            root,
        )
        return capability


def _register_r26_protocol_v1_ready_root(
    root: object,
    ledger_store: object,
    repository: object,
    *,
    _issuer: object,
) -> None:
    """Register a fully constructed root before its READY publication."""

    if _issuer is not _R26_PREPARATION_ISSUER or type(ledger_store) is not LocalWorkflowApplicationLedgerStore:
        raise ValueError("AUTHORITY_REJECTED")
    with _R26_CAPABILITY_LOCK:
        existing = _R26_READY_ROOTS.get(id(root))
        if existing is not None and existing != (root, ledger_store, repository):
            raise ValueError("AUTHORITY_REJECTED")
        _R26_READY_ROOTS[id(root)] = (root, ledger_store, repository)


def _existing_r26_prepare_result(
    binding: WorkflowApplicationLedgerBindingDTO,
    existing: _LedgerRecord,
) -> _R26ProtocolPreparationResultV1:
    if existing.binding != binding:
        return _R26ProtocolPreparationResultV1(binding, "conflict")
    if existing.lifecycle == "prepared":
        return _R26ProtocolPreparationResultV1(binding, "confirmed_prepared")
    if existing.lifecycle == "applied":
        return _R26ProtocolPreparationResultV1(binding, "confirmed_applied")
    return _R26ProtocolPreparationResultV1(binding, "CORRUPT")


def _consume_r26_preparation_capability(
    capability: object,
    ledger_store: LocalWorkflowApplicationLedgerStore,
    repository: object,
    root: object,
) -> bool:
    """Tombstone before mutation and require exact private issuance identity."""

    if type(capability) is not _R26ProtocolV1PreparationCapability:
        return False
    exact = capability
    with _R26_CAPABILITY_LOCK:
        issued = _R26_PREPARATION_CAPABILITIES.get(id(exact))
        if issued != (exact, ledger_store, repository, root):
            return False
        if (
            getattr(exact, "_issuer", None) is not _R26_PREPARATION_ISSUER
            or getattr(exact, "_store", None) is not ledger_store
            or getattr(exact, "_repository", None) is not repository
            or getattr(exact, "_root", None) is not root
            or getattr(exact, "_used", None) is not False
            or _R26_READY_ROOTS.get(id(root)) != (root, ledger_store, repository)
        ):
            return False
        del _R26_PREPARATION_CAPABILITIES[id(exact)]
        object.__setattr__(exact, "_used", True)
        return True


def _consume_r26_observation_capability(
    capability: object,
    ledger_store: LocalWorkflowApplicationLedgerStore,
    repository: object,
    root: object,
) -> bool:
    """Tombstone one read-only observation capability after exact validation."""

    if type(capability) is not _R26ProtocolV1ObservationCapability:
        return False
    exact = capability
    with _R26_CAPABILITY_LOCK:
        issued = _R26_OBSERVATION_CAPABILITIES.get(id(exact))
        if issued != (exact, ledger_store, repository, root):
            return False
        if (
            getattr(exact, "_issuer", None) is not _R26_PREPARATION_ISSUER
            or getattr(exact, "_store", None) is not ledger_store
            or getattr(exact, "_repository", None) is not repository
            or getattr(exact, "_root", None) is not root
            or getattr(exact, "_used", None) is not False
            or _R26_READY_ROOTS.get(id(root)) != (root, ledger_store, repository)
        ):
            return False
        del _R26_OBSERVATION_CAPABILITIES[id(exact)]
        object.__setattr__(exact, "_used", True)
        return True


def _consume_r26_authenticated_observation_for_proof_v1(
    source: object,
    ledger_store: object,
    repository: object,
    root: object,
    binding: object,
) -> _R26ProtocolObservationV2 | None:
    """Tombstone one exact R21 source wrapper before R26 proof issuance."""

    if (
        type(source) is not _R26AuthenticatedProtocolObservationV1
        or type(ledger_store) is not LocalWorkflowApplicationLedgerStore
        or type(binding) is not WorkflowApplicationLedgerBindingDTO
    ):
        return None
    exact = source
    with _R26_CAPABILITY_LOCK:
        issued = _R26_AUTHENTICATED_OBSERVATIONS.get(exact)
        if issued is None or len(issued) != 6:
            return None
        issued_source, issued_store, issued_repository, issued_root, issued_binding, observation = issued
        if (
            issued_source is not exact
            or issued_store is not ledger_store
            or issued_repository is not repository
            or issued_root is not root
            or issued_binding is not binding
            or type(observation) is not _R26ProtocolObservationV2
        ):
            return None
        if (
            getattr(exact, "_seal", None) is not _R26_PREPARATION_ISSUER
            or getattr(exact, "_store", None) is not ledger_store
            or getattr(exact, "_repository", None) is not repository
            or getattr(exact, "_root", None) is not root
            or getattr(exact, "_binding", None) is not binding
            or getattr(exact, "_observation", None) is not observation
            or getattr(exact, "_used", None) is not False
            or _R26_READY_ROOTS.get(id(root)) != (root, ledger_store, repository)
        ):
            return None
        del _R26_AUTHENTICATED_OBSERVATIONS[exact]
        object.__setattr__(exact, "_used", True)
        return observation


def _issue_r26_ledger_finalizer_authorization_v1(
    ledger_service: object,
    ledger_store: object,
    repository: object,
    coordinator: object,
    composition: object,
    *,
    _issuer: object,
) -> _R26LedgerFinalizerAuthorizationV1:
    """Issue the one reusable finalizer seal for an exact private composition."""

    if (
        _issuer is not _R26_FINALIZER_ISSUER
        or type(ledger_service) is not WorkflowApplicationLedgerService
        or type(ledger_store) is not LocalWorkflowApplicationLedgerStore
        or repository is None
        or coordinator is None
        or composition is None
    ):
        raise ValueError("AUTHORITY_REJECTED")
    authorization = object.__new__(_R26LedgerFinalizerAuthorizationV1)
    object.__setattr__(authorization, "_issuer", _R26_FINALIZER_ISSUER)
    object.__setattr__(authorization, "_used", False)
    with _R26_CAPABILITY_LOCK:
        _R26_FINALIZER_AUTHORIZATIONS[authorization] = (
            authorization,
            ledger_service,
            ledger_store,
            repository,
            coordinator,
            composition,
        )
    return authorization


def _finalize_r26_ledger_reconciliation_v1(  # noqa: C901
    finalizer_authorization: object,
    prepared_observation: object,
) -> _R26LedgerFinalizationResultV1:
    """Finalize one exact R26 marker without accepting Coordinator authority.

    The only caller-controlled values are two opaque objects.  Both must be
    the precise, strongly retained objects of the same private composition;
    all durable facts are derived from the authenticated R21 observation.
    """

    if (
        type(finalizer_authorization) is not _R26LedgerFinalizerAuthorizationV1
        or type(prepared_observation) is not _R26AuthenticatedProtocolObservationV1
    ):
        return _R26LedgerFinalizationResultV1("CALL_REJECTED")
    authorization = finalizer_authorization
    source = prepared_observation
    with _R26_CAPABILITY_LOCK:
        registered_authorization = _R26_FINALIZER_AUTHORIZATIONS.get(authorization)
        registered_source = _R26_AUTHENTICATED_OBSERVATIONS.get(source)
        if (
            registered_authorization is None
            or len(registered_authorization) != 6
            or registered_source is None
            or len(registered_source) != 6
        ):
            return _R26LedgerFinalizationResultV1("CALL_REJECTED")
        (
            issued_authorization,
            ledger_service,
            ledger_store,
            repository,
            coordinator,
            composition,
        ) = registered_authorization
        (
            issued_source,
            source_store,
            source_repository,
            root,
            binding,
            observation,
        ) = registered_source
        exact_observation = cast(_R26ProtocolObservationV2, observation)
        if (
            issued_authorization is not authorization
            or getattr(authorization, "_issuer", None) is not _R26_FINALIZER_ISSUER
            or getattr(authorization, "_used", None) is not False
            or type(ledger_service) is not WorkflowApplicationLedgerService
            or type(ledger_store) is not LocalWorkflowApplicationLedgerStore
            or repository is None
            or coordinator is None
            or composition is None
            or issued_source is not source
            or source_store is not ledger_store
            or source_repository is not repository
            or _R26_READY_ROOTS.get(id(root)) != (root, ledger_store, repository)
            or type(binding) is not WorkflowApplicationLedgerBindingDTO
            or type(observation) is not _R26ProtocolObservationV2
            or getattr(source, "_seal", None) is not _R26_PREPARATION_ISSUER
            or getattr(source, "_store", None) is not ledger_store
            or getattr(source, "_repository", None) is not repository
            or getattr(source, "_root", None) is not root
            or getattr(source, "_binding", None) is not binding
            or getattr(source, "_observation", None) is not observation
            or getattr(source, "_used", None) is not False
            or exact_observation.outcome != "PREPARED"
            or exact_observation.marker_version != 1
            or not _sha256_digest(exact_observation.protocol_binding_digest)
        ):
            return _R26LedgerFinalizationResultV1("CALL_REJECTED")
        del _R26_AUTHENTICATED_OBSERVATIONS[source]
        object.__setattr__(source, "_used", True)
        exact_ledger_store = cast(LocalWorkflowApplicationLedgerStore, ledger_store)
        exact_binding = cast(WorkflowApplicationLedgerBindingDTO, binding)
        expected_protocol_digest = cast(str, exact_observation.protocol_binding_digest)

    connection: sqlite3.Connection | None = None
    began = False
    durable_attempted = False
    try:
        if (
            not _valid_binding(exact_binding)
            or not _sha256_digest(expected_protocol_digest)
        ):
            return _R26LedgerFinalizationResultV1("CALL_REJECTED")
        if not _r21_regular_file(exact_ledger_store._database_path):
            return _R26LedgerFinalizationResultV1("RECOVERY_REQUIRED")
        connection = _open_ledger_connection(exact_ledger_store._database_path)
        connection.execute("BEGIN IMMEDIATE")
        began = True
        _validate_r26_schema_v2(connection)
        by_attempt = exact_ledger_store._by_attempt(connection, exact_binding.attempt_id)
        by_authorization = exact_ledger_store._by_authorization(
            connection, exact_binding.authorization_id
        )
        records = tuple(
            record for record in (by_attempt, by_authorization) if record is not None
        )
        if not records:
            connection.rollback()
            began = False
            return _R26LedgerFinalizationResultV1("RECOVERY_REQUIRED")
        if len(records) != 2 or records[0] != records[1]:
            connection.rollback()
            began = False
            return _R26LedgerFinalizationResultV1("CONFLICT")
        existing = records[0]
        prepared_payload = _canonical_payload(exact_binding, "prepared")
        prepared_digest = _digest(prepared_payload)
        if (
            existing.binding != exact_binding
            or existing.marker_version != 1
            or existing.protocol_binding_digest != expected_protocol_digest
            or expected_protocol_digest != _r26_protocol_digest(prepared_digest, 1)
        ):
            connection.rollback()
            began = False
            return _R26LedgerFinalizationResultV1("CONFLICT")
        if existing.lifecycle == "applied":
            connection.rollback()
            began = False
            return _R26LedgerFinalizationResultV1("LEDGER_REPLAY_REQUIRED")
        if existing.lifecycle != "prepared":
            connection.rollback()
            began = False
            return _R26LedgerFinalizationResultV1("CORRUPT")
        applied_payload = _canonical_payload(exact_binding, "applied")
        applied_digest = _digest(applied_payload)
        durable_attempted = True
        cursor = connection.execute(
            f"UPDATE {_TABLE_NAME} SET lifecycle = ?, binding_json = ?, binding_digest = ?, "
            "r26_protocol_binding_digest = ? WHERE attempt_id = ? AND authorization_id = ? "
            "AND lifecycle = 'prepared' AND post_cas_attestation_requirement_version = 1 "
            "AND binding_digest = ? AND r26_protocol_binding_digest = ?",
            (
                "applied",
                applied_payload,
                applied_digest,
                _r26_protocol_digest(applied_digest, 1),
                exact_binding.attempt_id,
                exact_binding.authorization_id,
                prepared_digest,
                expected_protocol_digest,
            ),
        )
        if cursor.rowcount != 1:
            connection.rollback()
            began = False
            return _R26LedgerFinalizationResultV1("LEDGER_REPLAY_REQUIRED")
        connection.commit()
        began = False
        return _R26LedgerFinalizationResultV1("APPLIED")
    except _R21CorruptError:
        return _R26LedgerFinalizationResultV1("CORRUPT")
    except sqlite3.DatabaseError as error:
        if durable_attempted:
            return _R26LedgerFinalizationResultV1("LEDGER_REPLAY_REQUIRED")
        return _R26LedgerFinalizationResultV1(
            "CORRUPT" if _r21_sqlite_outcome(error) == "CORRUPT" else "RECOVERY_REQUIRED"
        )
    except ValueError:
        return _R26LedgerFinalizationResultV1("CORRUPT")
    except (OSError, TypeError):
        return _R26LedgerFinalizationResultV1("RECOVERY_REQUIRED")
    finally:
        if began:
            _rollback_quietly(connection)
        _close_quietly(connection)


def _open_ledger_connection(database_path: Path) -> sqlite3.Connection:
    """Open the private SQLite owner with the frozen durability settings."""

    connection = sqlite3.connect(database_path, timeout=5.0, isolation_level=None)
    mode = str(connection.execute("PRAGMA journal_mode = DELETE").fetchone()[0]).lower()
    if mode != "delete":
        connection.close()
        raise ValueError("workflow application ledger unavailable")
    connection.execute("PRAGMA synchronous = FULL")
    return connection


def _rollback_quietly(connection: sqlite3.Connection | None) -> None:
    if connection is None:
        return
    try:
        connection.rollback()
    except sqlite3.Error:
        pass


def _close_quietly(connection: sqlite3.Connection | None) -> None:
    if connection is not None:
        connection.close()


def _logical_reference(value: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError("logical reference must be nonblank")
    if value.startswith(_WINDOWS_ABSOLUTE_PATH) or "://" in value or "@" in value:
        raise ValueError("logical reference must not be a path, URL, or email")
    return value
