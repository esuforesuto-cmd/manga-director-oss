"""Private durable correlation evidence for one externally applied generation.

This sidecar is intentionally not a workflow, authorization, ledger, asset,
quality, recovery, or event-delivery authority.  It records only that an
already verified LocalFile aggregate commit belongs to one exact immutable
workflow-application binding.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol, cast

from pydantic import ConfigDict

from manga_director.production.director import DirectorModel
from manga_director.production.future_real_delivery_r26_reconciliation import (
    _consume_r26_receipt_projection_for_receipt_v1,
)
from manga_director.production.next_generation_workflow_application_ledger import (
    WorkflowApplicationLedgerBindingDTO,
    _AuthoritativeWorkflowApplicationCommitProof,
)

ReceiptStatus = Literal["committed", "blocked"]
ReceiptWriteOutcome = Literal["committed", "confirmed", "conflict", "failed"]
ReceiptLookupOutcome = Literal["found", "missing", "conflict", "corrupt"]

_SCHEMA_VERSION = 1
_DATABASE_FILENAME = "durable-application-commit-receipts.sqlite3"
_TABLE_NAME = "durable_application_commit_receipts"
_ARTIFACT_KIND: Literal["logical_output_asset"] = "logical_output_asset"
_RESULTING_STATE: Literal["Generated"] = "Generated"

_R26ReceiptOutcome = Literal[
    "RECEIPT_CONFIRMED",
    "AUTHORITY_REJECTED",
    "CONSUMED",
    "RESTART_REQUIRED",
    "CORRUPT",
    "CONFLICT",
    "RECOVERY_REQUIRED",
]


class _ReceiptModel(DirectorModel):
    """Private immutable, closed receipt values."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class DurableApplicationCommitReceiptFindingDTO(_ReceiptModel):
    """One redacted private Receipt finding."""

    code: str
    status: Literal["blocked"]
    message: str


class DurableApplicationCommitReceiptReport(_ReceiptModel):
    """Redacted private outcome; private storage integrity data never escapes."""

    attempt_id: str
    authorization_id: str
    project_id: str
    page_id: str
    status: ReceiptStatus
    committed: bool
    idempotent_confirmation: bool
    findings: tuple[DurableApplicationCommitReceiptFindingDTO, ...] = ()


@dataclass(frozen=True, slots=True)
class _DurableApplicationCommitReceipt:
    """Complete private correlation record, including storage-only integrity facts."""

    binding: WorkflowApplicationLedgerBindingDTO = field(repr=False)
    artifact_kind: Literal["logical_output_asset"] = _ARTIFACT_KIND
    resulting_state: Literal["Generated"] = _RESULTING_STATE
    post_commit_revision: int = field(default=0, repr=False)
    post_commit_fingerprint: str = field(default="", repr=False)
    canonical_digest: str = field(default="", repr=False)


@dataclass(frozen=True, slots=True)
class DurableApplicationCommitReceiptStoreWriteResult:
    """Private durable-store result; it never exposes storage integrity facts."""

    receipt: _DurableApplicationCommitReceipt = field(repr=False)
    outcome: ReceiptWriteOutcome


@dataclass(frozen=True, slots=True)
class DurableApplicationCommitReceiptExactLookupResult:
    """Private, redacted outcome for one exact immutable Receipt lookup."""

    outcome: ReceiptLookupOutcome


@dataclass(frozen=True, slots=True)
class _R26ReceiptCommitOutcomeV1:
    """Ordinary Receipt outcome data; it conveys no confirmation authority."""

    outcome: _R26ReceiptOutcome


class DurableApplicationCommitReceiptStorePort(Protocol):
    """Private immutable persistence boundary for application correlations."""

    def commit(
        self, receipt: _DurableApplicationCommitReceipt
    ) -> DurableApplicationCommitReceiptStoreWriteResult: ...

    def lookup_exact(
        self,
        binding: WorkflowApplicationLedgerBindingDTO,
        post_commit_revision: int,
        post_commit_fingerprint: str,
    ) -> DurableApplicationCommitReceiptExactLookupResult: ...


class DurableApplicationCommitReceiptService:
    """Require the existing opaque authoritative proof before persisting correlation."""

    def commit(
        self,
        binding: WorkflowApplicationLedgerBindingDTO,
        commit_proof: object,
        *,
        post_commit_revision: int,
        post_commit_fingerprint: str,
        receipt_store: DurableApplicationCommitReceiptStorePort,
    ) -> DurableApplicationCommitReceiptReport:
        """Persist only an exact correlation from a verified authoritative commit."""

        if not isinstance(commit_proof, _AuthoritativeWorkflowApplicationCommitProof) or not commit_proof._matches(
            binding
        ):
            return _blocked_report(binding, "RECEIPT_AUTHORITATIVE_COMMIT_PROOF_INVALID")
        receipt = _receipt(binding, post_commit_revision, post_commit_fingerprint)
        if receipt is None:
            return _blocked_report(binding, "RECEIPT_POST_COMMIT_CORRELATION_INVALID")
        try:
            result = receipt_store.commit(receipt)
        except Exception:
            return _blocked_report(binding, "RECEIPT_COMMIT_FAILED")
        if not isinstance(result, DurableApplicationCommitReceiptStoreWriteResult) or result.receipt != receipt:
            return _blocked_report(binding, "RECEIPT_COMMIT_RESULT_INVALID")
        if result.outcome == "committed":
            return _committed_report(binding, idempotent_confirmation=False)
        if result.outcome == "confirmed":
            return _committed_report(binding, idempotent_confirmation=True)
        if result.outcome == "conflict":
            return _blocked_report(binding, "RECEIPT_COMMIT_CONFLICT")
        return _blocked_report(binding, "RECEIPT_COMMIT_FAILED")

    def lookup_exact(
        self,
        binding: WorkflowApplicationLedgerBindingDTO,
        *,
        post_commit_revision: int,
        post_commit_fingerprint: str,
        receipt_store: DurableApplicationCommitReceiptStorePort,
    ) -> DurableApplicationCommitReceiptExactLookupResult:
        """Read one exact immutable Receipt without exposing integrity internals."""

        if _receipt(binding, post_commit_revision, post_commit_fingerprint) is None:
            return DurableApplicationCommitReceiptExactLookupResult("corrupt")
        try:
            result = receipt_store.lookup_exact(
                binding, post_commit_revision, post_commit_fingerprint
            )
        except Exception:
            return DurableApplicationCommitReceiptExactLookupResult("corrupt")
        if not isinstance(result, DurableApplicationCommitReceiptExactLookupResult):
            return DurableApplicationCommitReceiptExactLookupResult("corrupt")
        return result

    def _commit_consumed_r26_projection_v1(  # noqa: C901
        self,
        projection: object,
        factory: object,
        binding: object,
        *,
        repository: object,
        composition: object,
        coordinator: object,
        invocation_authority: object,
        receipt_store: object,
    ) -> _R26ReceiptCommitOutcomeV1:
        """Commit/replay from one exact projection, then freshly read it back."""

        if type(receipt_store) is not LocalDurableApplicationCommitReceiptStore:
            return _R26ReceiptCommitOutcomeV1("AUTHORITY_REJECTED")
        if getattr(coordinator, "_receipt_service", None) is not self or getattr(
            coordinator, "_receipt_store", None
        ) is not receipt_store:
            return _R26ReceiptCommitOutcomeV1("AUTHORITY_REJECTED")
        exact_receipt_store = cast(DurableApplicationCommitReceiptStorePort, receipt_store)
        facts = _consume_r26_receipt_projection_for_receipt_v1(
            projection,
            factory,
            binding,
            repository=repository,
            composition=composition,
            coordinator=coordinator,
            invocation_authority=invocation_authority,
        )
        if facts.outcome != "SEALED_RECONCILIATION_PROOF_ISSUED":
            return _R26ReceiptCommitOutcomeV1(_receipt_outcome(facts.outcome))
        exact_binding = facts.binding
        if (
            exact_binding is None
            or facts.binding_digest is None
            or facts.output_asset_id != exact_binding.output_asset_id
            or facts.post_commit_revision is None
            or facts.post_commit_fingerprint is None
        ):
            return _R26ReceiptCommitOutcomeV1("CORRUPT")
        receipt = _receipt(exact_binding, facts.post_commit_revision, facts.post_commit_fingerprint)
        if receipt is None:
            return _R26ReceiptCommitOutcomeV1("CORRUPT")
        try:
            write_result = exact_receipt_store.commit(receipt)
        except Exception:
            return _R26ReceiptCommitOutcomeV1("RECOVERY_REQUIRED")
        if not isinstance(write_result, DurableApplicationCommitReceiptStoreWriteResult):
            return _R26ReceiptCommitOutcomeV1("RECOVERY_REQUIRED")
        if write_result.receipt != receipt:
            return _R26ReceiptCommitOutcomeV1("CORRUPT")
        if write_result.outcome == "conflict":
            return _R26ReceiptCommitOutcomeV1("CONFLICT")
        if write_result.outcome not in {"committed", "confirmed"}:
            return _R26ReceiptCommitOutcomeV1("RECOVERY_REQUIRED")
        try:
            readback = exact_receipt_store.lookup_exact(
                exact_binding, facts.post_commit_revision, facts.post_commit_fingerprint
            )
        except Exception:
            return _R26ReceiptCommitOutcomeV1("RECOVERY_REQUIRED")
        if not isinstance(readback, DurableApplicationCommitReceiptExactLookupResult):
            return _R26ReceiptCommitOutcomeV1("CORRUPT")
        if readback.outcome == "conflict":
            return _R26ReceiptCommitOutcomeV1("CONFLICT")
        if readback.outcome == "corrupt":
            return _R26ReceiptCommitOutcomeV1("CORRUPT")
        if readback.outcome != "found":
            return _R26ReceiptCommitOutcomeV1("RECOVERY_REQUIRED")
        return _R26ReceiptCommitOutcomeV1("RECEIPT_CONFIRMED")


def _receipt_outcome(outcome: str) -> _R26ReceiptOutcome:
    if outcome in {"AUTHORITY_REJECTED", "CONSUMED", "RESTART_REQUIRED", "CORRUPT", "CONFLICT"}:
        return cast(_R26ReceiptOutcome, outcome)
    return "RECOVERY_REQUIRED"


class LocalDurableApplicationCommitReceiptStore(DurableApplicationCommitReceiptStorePort):
    """Dedicated private SQLite sidecar for immutable application correlations."""

    def __init__(self, owner_root: Path) -> None:
        self._root = _prepare_owner_root(owner_root)
        self._database_path = self._root / _DATABASE_FILENAME
        self._initialize_schema()

    def commit(
        self, receipt: _DurableApplicationCommitReceipt
    ) -> DurableApplicationCommitReceiptStoreWriteResult:
        connection: sqlite3.Connection | None = None
        try:
            connection = self._connect()
            connection.execute("BEGIN IMMEDIATE")
            existing = self._existing_claims(connection, receipt)
            if existing:
                connection.rollback()
                if len(existing) == 1 and existing[0] == receipt:
                    return DurableApplicationCommitReceiptStoreWriteResult(receipt, "confirmed")
                return DurableApplicationCommitReceiptStoreWriteResult(receipt, "conflict")
            if not _valid_receipt(receipt):
                connection.rollback()
                return DurableApplicationCommitReceiptStoreWriteResult(receipt, "failed")
            self._insert(connection, receipt)
            connection.commit()
            return DurableApplicationCommitReceiptStoreWriteResult(receipt, "committed")
        except Exception:
            _rollback_quietly(connection)
            return DurableApplicationCommitReceiptStoreWriteResult(receipt, "failed")
        finally:
            _close_quietly(connection)

    def lookup_exact(
        self,
        binding: WorkflowApplicationLedgerBindingDTO,
        post_commit_revision: int,
        post_commit_fingerprint: str,
    ) -> DurableApplicationCommitReceiptExactLookupResult:
        expected = _receipt(binding, post_commit_revision, post_commit_fingerprint)
        if expected is None:
            return DurableApplicationCommitReceiptExactLookupResult("corrupt")
        connection: sqlite3.Connection | None = None
        try:
            connection = self._connect()
            records = self._existing_claims(connection, expected)
            if not records:
                return DurableApplicationCommitReceiptExactLookupResult("missing")
            if len(records) == 1 and records[0] == expected:
                return DurableApplicationCommitReceiptExactLookupResult("found")
            return DurableApplicationCommitReceiptExactLookupResult("conflict")
        except Exception:
            return DurableApplicationCommitReceiptExactLookupResult("corrupt")
        finally:
            _close_quietly(connection)

    def _initialize_schema(self) -> None:
        connection: sqlite3.Connection | None = None
        try:
            connection = self._connect()
            connection.execute("BEGIN IMMEDIATE")
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            has_tables = _has_user_tables(connection)
            if version == 0 and not has_tables:
                connection.execute(
                    f"CREATE TABLE {_TABLE_NAME} ("
                    "attempt_id TEXT PRIMARY KEY, "
                    "authorization_id TEXT NOT NULL UNIQUE, "
                    "project_id TEXT NOT NULL, "
                    "page_id TEXT NOT NULL, "
                    "target_page_reference TEXT NOT NULL, "
                    "provider_reference TEXT NOT NULL, "
                    "output_asset_id TEXT NOT NULL, "
                    "source_state TEXT NOT NULL CHECK(source_state = 'PromptBuilt'), "
                    "target_state TEXT NOT NULL CHECK(target_state = 'Generated'), "
                    "artifact_kind TEXT NOT NULL CHECK(artifact_kind = 'logical_output_asset'), "
                    "resulting_state TEXT NOT NULL CHECK(resulting_state = 'Generated'), "
                    "post_commit_revision INTEGER NOT NULL, "
                    "post_commit_fingerprint TEXT NOT NULL, "
                    "receipt_json TEXT NOT NULL, "
                    "receipt_digest TEXT NOT NULL, "
                    "UNIQUE(project_id, page_id, post_commit_revision, post_commit_fingerprint)"
                    ")"
                )
                connection.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")
                connection.commit()
                return
            if version != _SCHEMA_VERSION or not _schema_is_valid(connection):
                raise ValueError("durable application commit receipt unavailable")
            connection.commit()
        except (sqlite3.Error, TypeError, ValueError) as error:
            _rollback_quietly(connection)
            raise ValueError("durable application commit receipt unavailable") from error
        finally:
            _close_quietly(connection)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=5.0, isolation_level=None)
        mode = str(connection.execute("PRAGMA journal_mode = DELETE").fetchone()[0]).lower()
        if mode != "delete":
            connection.close()
            raise ValueError("durable application commit receipt unavailable")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    @staticmethod
    def _existing_claims(
        connection: sqlite3.Connection, receipt: _DurableApplicationCommitReceipt
    ) -> tuple[_DurableApplicationCommitReceipt, ...]:
        rows = connection.execute(
            "SELECT attempt_id, authorization_id, project_id, page_id, target_page_reference, "
            "provider_reference, output_asset_id, source_state, target_state, artifact_kind, "
            "resulting_state, post_commit_revision, post_commit_fingerprint, receipt_json, receipt_digest "
            f"FROM {_TABLE_NAME} WHERE attempt_id = ? OR authorization_id = ? "
            "OR (project_id = ? AND page_id = ? AND post_commit_revision = ? "
            "AND post_commit_fingerprint = ?)",
            (
                receipt.binding.attempt_id,
                receipt.binding.authorization_id,
                receipt.binding.project_id,
                receipt.binding.page_id,
                receipt.post_commit_revision,
                receipt.post_commit_fingerprint,
            ),
        ).fetchall()
        parsed = tuple(_receipt_from_row(row) for row in rows)
        if any(record is None for record in parsed):
            raise ValueError("durable application commit receipt unavailable")
        return tuple(record for record in parsed if record is not None)

    @staticmethod
    def _insert(connection: sqlite3.Connection, receipt: _DurableApplicationCommitReceipt) -> None:
        binding = receipt.binding
        connection.execute(
            f"INSERT INTO {_TABLE_NAME} ("
            "attempt_id, authorization_id, project_id, page_id, target_page_reference, provider_reference, "
            "output_asset_id, source_state, target_state, artifact_kind, resulting_state, "
            "post_commit_revision, post_commit_fingerprint, receipt_json, receipt_digest"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                binding.attempt_id,
                binding.authorization_id,
                binding.project_id,
                binding.page_id,
                binding.target_page_reference,
                binding.provider_reference,
                binding.output_asset_id,
                binding.source_state,
                binding.target_state,
                receipt.artifact_kind,
                receipt.resulting_state,
                receipt.post_commit_revision,
                receipt.post_commit_fingerprint,
                _canonical_receipt_json(receipt),
                receipt.canonical_digest,
            ),
        )


def _receipt(
    binding: WorkflowApplicationLedgerBindingDTO,
    post_commit_revision: int,
    post_commit_fingerprint: str,
) -> _DurableApplicationCommitReceipt | None:
    if (
        not isinstance(post_commit_revision, int)
        or isinstance(post_commit_revision, bool)
        or post_commit_revision < 1
        or not _valid_fingerprint(post_commit_fingerprint)
    ):
        return None
    provisional = _DurableApplicationCommitReceipt(
        binding=binding,
        post_commit_revision=post_commit_revision,
        post_commit_fingerprint=post_commit_fingerprint,
    )
    return _DurableApplicationCommitReceipt(
        binding=binding,
        post_commit_revision=post_commit_revision,
        post_commit_fingerprint=post_commit_fingerprint,
        canonical_digest=_digest(_canonical_receipt_json(provisional)),
    )


def _valid_receipt(receipt: _DurableApplicationCommitReceipt) -> bool:
    expected = _receipt(
        receipt.binding, receipt.post_commit_revision, receipt.post_commit_fingerprint
    )
    return expected == receipt


def _receipt_from_row(row: object) -> _DurableApplicationCommitReceipt | None:
    if not isinstance(row, tuple) or len(row) != 15:
        return None
    (
        attempt_id,
        authorization_id,
        project_id,
        page_id,
        target_page_reference,
        provider_reference,
        output_asset_id,
        source_state,
        target_state,
        artifact_kind,
        resulting_state,
        post_commit_revision,
        post_commit_fingerprint,
        receipt_json,
        receipt_digest,
    ) = row
    try:
        binding = WorkflowApplicationLedgerBindingDTO(
            attempt_id=attempt_id,
            authorization_id=authorization_id,
            project_id=project_id,
            page_id=page_id,
            target_page_reference=target_page_reference,
            provider_reference=provider_reference,
            output_asset_id=output_asset_id,
            source_state=source_state,
            target_state=target_state,
        )
    except Exception:
        return None
    if artifact_kind != _ARTIFACT_KIND or resulting_state != _RESULTING_STATE:
        return None
    receipt = _receipt(binding, post_commit_revision, post_commit_fingerprint)
    if (
        receipt is None
        or not isinstance(receipt_json, str)
        or not isinstance(receipt_digest, str)
        or receipt.canonical_digest != receipt_digest
        or _canonical_receipt_json(receipt) != receipt_json
    ):
        return None
    return receipt


def _canonical_receipt_json(receipt: _DurableApplicationCommitReceipt) -> str:
    binding = receipt.binding
    return json.dumps(
        {
            "artifact_kind": receipt.artifact_kind,
            "attempt_id": binding.attempt_id,
            "authorization_id": binding.authorization_id,
            "output_asset_id": binding.output_asset_id,
            "page_id": binding.page_id,
            "post_commit_fingerprint": receipt.post_commit_fingerprint,
            "post_commit_revision": receipt.post_commit_revision,
            "project_id": binding.project_id,
            "provider_reference": binding.provider_reference,
            "resulting_state": receipt.resulting_state,
            "source_state": binding.source_state,
            "target_page_reference": binding.target_page_reference,
            "target_state": binding.target_state,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _valid_fingerprint(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _prepare_owner_root(owner_root: Path) -> Path:
    if not isinstance(owner_root, Path) or not owner_root.is_absolute():
        raise ValueError("durable application commit receipt unavailable")
    resolved = owner_root.resolve()
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _has_user_tables(connection: sqlite3.Connection) -> bool:
    return bool(
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchone()
    )


def _schema_is_valid(connection: sqlite3.Connection) -> bool:
    columns = tuple(
        row[1] for row in connection.execute(f"PRAGMA table_info({_TABLE_NAME})").fetchall()
    )
    return columns == (
        "attempt_id",
        "authorization_id",
        "project_id",
        "page_id",
        "target_page_reference",
        "provider_reference",
        "output_asset_id",
        "source_state",
        "target_state",
        "artifact_kind",
        "resulting_state",
        "post_commit_revision",
        "post_commit_fingerprint",
        "receipt_json",
        "receipt_digest",
    )


def _committed_report(
    binding: WorkflowApplicationLedgerBindingDTO, *, idempotent_confirmation: bool
) -> DurableApplicationCommitReceiptReport:
    return DurableApplicationCommitReceiptReport(
        attempt_id=binding.attempt_id,
        authorization_id=binding.authorization_id,
        project_id=binding.project_id,
        page_id=binding.page_id,
        status="committed",
        committed=True,
        idempotent_confirmation=idempotent_confirmation,
    )


def _blocked_report(
    binding: WorkflowApplicationLedgerBindingDTO, code: str
) -> DurableApplicationCommitReceiptReport:
    return DurableApplicationCommitReceiptReport(
        attempt_id=binding.attempt_id,
        authorization_id=binding.authorization_id,
        project_id=binding.project_id,
        page_id=binding.page_id,
        status="blocked",
        committed=False,
        idempotent_confirmation=False,
        findings=(
            DurableApplicationCommitReceiptFindingDTO(
                code=code,
                status="blocked",
                message="durable application commit correlation is unavailable",
            ),
        ),
    )


def _rollback_quietly(connection: sqlite3.Connection | None) -> None:
    if connection is None:
        return
    try:
        connection.rollback()
    except sqlite3.Error:
        pass


def _close_quietly(connection: sqlite3.Connection | None) -> None:
    if connection is None:
        return
    try:
        connection.close()
    except sqlite3.Error:
        pass
