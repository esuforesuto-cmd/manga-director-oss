"""Private idempotent application ledger for deterministic Page composition."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import ConfigDict, field_validator, model_validator

from manga_director.production.director import DirectorModel
from manga_director.production.next_generation_page_generation_plan import (
    canonical_digest,
    logical_reference,
    sha256_digest,
)

ApplicationLifecycle = Literal["prepared", "applied"]
ApplicationLedgerOutcome = Literal[
    "prepared", "applied", "confirmed", "missing", "conflict", "corrupt", "failed"
]

_DATABASE_FILENAME = "page-composition-application-ledger.sqlite3"
_SCHEMA_VERSION = 1


class _ApplicationModel(DirectorModel):
    model_config = ConfigDict(
        frozen=True, extra="forbid", strict=True, validate_default=True
    )


class PageCompositionApplicationBinding(_ApplicationModel):
    application_id: str
    project_id: str
    page_id: str
    page_revision: str
    source_state: Literal["PromptBuilt"] = "PromptBuilt"
    target_state: Literal["Generated"] = "Generated"
    plan_id: str
    plan_fingerprint: str
    composition_attempt_id: str
    composition_provenance_reference: str
    request_fingerprint: str
    evidence_id: str
    evidence_sha256: str
    composite_asset_id: str
    composite_sha256: str
    binding_fingerprint: str | None = None

    @field_validator(
        "application_id",
        "project_id",
        "page_id",
        "page_revision",
        "plan_id",
        "composition_attempt_id",
        "composition_provenance_reference",
        "evidence_id",
        "composite_asset_id",
        mode="before",
    )
    @classmethod
    def _references(cls, value: object) -> str:
        return logical_reference(value, "composition application reference")

    @field_validator(
        "plan_fingerprint",
        "request_fingerprint",
        "evidence_sha256",
        "composite_sha256",
    )
    @classmethod
    def _digests(cls, value: str) -> str:
        return sha256_digest(value)

    @model_validator(mode="after")
    def _canonical_binding(self) -> PageCompositionApplicationBinding:
        expected = canonical_digest(
            self.model_dump(mode="json", exclude={"binding_fingerprint"})
        )
        if self.binding_fingerprint is not None:
            sha256_digest(self.binding_fingerprint)
            if self.binding_fingerprint != expected:
                raise ValueError("application binding fingerprint does not match content")
        object.__setattr__(self, "binding_fingerprint", expected)
        return self


@dataclass(frozen=True, slots=True)
class PageCompositionApplicationLedgerResult:
    application_id: str
    outcome: ApplicationLedgerOutcome
    lifecycle: ApplicationLifecycle | None = None
    binding: PageCompositionApplicationBinding | None = field(default=None, repr=False)


class LocalPageCompositionApplicationLedger:
    """Separate versioned sidecar; never creates Provider application rows."""

    def __init__(self, owner_root: Path) -> None:
        self._root = _prepare_root(owner_root)
        self._database_path = _prepare_database(self._root)
        self._initialize_schema()

    def prepare(
        self, binding: PageCompositionApplicationBinding
    ) -> PageCompositionApplicationLedgerResult:
        return self._write(binding, target="prepared")

    def mark_applied(
        self, binding: PageCompositionApplicationBinding
    ) -> PageCompositionApplicationLedgerResult:
        return self._write(binding, target="applied")

    def lookup_exact(
        self, binding: PageCompositionApplicationBinding
    ) -> PageCompositionApplicationLedgerResult:
        connection: sqlite3.Connection | None = None
        try:
            connection = self._connect()
            rows = connection.execute(
                "SELECT project_id, page_id, page_revision, lifecycle, payload_json, "
                "payload_digest, binding_fingerprint "
                "FROM composition_application"
            ).fetchall()
            verified = [_verified_row(row) for row in rows]
            if any(item is None for item in verified):
                return _result(binding, "corrupt")
            exact = [
                item
                for item in verified
                if item is not None and item[0].application_id == binding.application_id
            ]
            if not exact:
                return _result(binding, "missing")
            if len(exact) != 1:
                return _result(binding, "corrupt")
            existing = exact[0]
            existing_binding, lifecycle = existing
            if existing_binding != binding:
                return _result(binding, "conflict")
            return _result(binding, "confirmed", lifecycle)
        except Exception:
            return _result(binding, "corrupt")
        finally:
            if connection is not None:
                connection.close()

    def _write(  # noqa: C901
        self,
        binding: PageCompositionApplicationBinding,
        *,
        target: ApplicationLifecycle,
    ) -> PageCompositionApplicationLedgerResult:
        if not isinstance(binding, PageCompositionApplicationBinding):
            return PageCompositionApplicationLedgerResult("", "failed")
        payload = _canonical_json(binding)
        payload_digest = _digest(payload)
        connection: sqlite3.Connection | None = None
        try:
            connection = self._connect()
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                "SELECT project_id, page_id, page_revision, lifecycle, payload_json, "
                "payload_digest, binding_fingerprint "
                "FROM composition_application"
            ).fetchall()
            verified = [_verified_row(row) for row in rows]
            if any(item is None for item in verified):
                connection.rollback()
                return _result(binding, "corrupt")
            by_id = next(
                (
                    item
                    for item in verified
                    if item is not None and item[0].application_id == binding.application_id
                ),
                None,
            )
            if by_id is None:
                conflicting = [
                    item
                    for item in verified
                    if item is not None
                    and item[0].project_id == binding.project_id
                    and item[0].page_id == binding.page_id
                    and item[0].page_revision == binding.page_revision
                ]
                if conflicting:
                    connection.rollback()
                    return _result(binding, "conflict")
                if target == "applied":
                    connection.rollback()
                    return _result(binding, "missing")
                connection.execute(
                    "INSERT INTO composition_application VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        binding.application_id,
                        binding.project_id,
                        binding.page_id,
                        binding.page_revision,
                        "prepared",
                        payload,
                        payload_digest,
                        binding.binding_fingerprint,
                    ),
                )
                connection.commit()
                return _result(binding, "prepared", "prepared")
            existing_binding, lifecycle = by_id
            if existing_binding != binding:
                connection.rollback()
                return _result(binding, "conflict")
            if target == "prepared" or lifecycle == "applied":
                connection.rollback()
                return _result(binding, "confirmed", lifecycle)
            changed = connection.execute(
                "UPDATE composition_application SET lifecycle = 'applied' "
                "WHERE application_id = ? AND lifecycle = 'prepared'",
                (binding.application_id,),
            ).rowcount
            if changed != 1:
                raise ValueError("composition application changed concurrently")
            connection.commit()
            return _result(binding, "applied", "applied")
        except sqlite3.IntegrityError:
            if connection is not None:
                _rollback(connection)
            return _result(binding, "conflict")
        except Exception:
            if connection is not None:
                _rollback(connection)
            return _result(binding, "failed")
        finally:
            if connection is not None:
                connection.close()

    def _initialize_schema(self) -> None:
        connection: sqlite3.Connection | None = None
        try:
            connection = self._connect()
            connection.execute("BEGIN IMMEDIATE")
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            tables = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            if version == 0 and not tables:
                connection.execute(
                    "CREATE TABLE composition_application (application_id TEXT PRIMARY KEY, "
                    "project_id TEXT NOT NULL, page_id TEXT NOT NULL, page_revision TEXT NOT NULL, "
                    "lifecycle TEXT NOT NULL, payload_json TEXT NOT NULL, payload_digest TEXT NOT NULL, "
                    "binding_fingerprint TEXT NOT NULL, UNIQUE(project_id, page_id, page_revision))"
                )
                connection.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")
                connection.commit()
                return
            columns = {
                str(row[1])
                for row in connection.execute("PRAGMA table_info(composition_application)")
            }
            if version != _SCHEMA_VERSION or columns != {
                "application_id", "project_id", "page_id", "page_revision", "lifecycle",
                "payload_json", "payload_digest", "binding_fingerprint",
            }:
                raise ValueError("composition application ledger is unavailable")
            connection.commit()
        except Exception as error:
            if connection is not None:
                _rollback(connection)
            raise ValueError("composition application ledger is unavailable") from error
        finally:
            if connection is not None:
                connection.close()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=5.0, isolation_level=None)
        mode = str(connection.execute("PRAGMA journal_mode = DELETE").fetchone()[0]).lower()
        if mode != "delete":
            connection.close()
            raise ValueError("composition application ledger is unavailable")
        connection.execute("PRAGMA synchronous = FULL")
        return connection


def _result(
    binding: PageCompositionApplicationBinding,
    outcome: ApplicationLedgerOutcome,
    lifecycle: ApplicationLifecycle | None = None,
) -> PageCompositionApplicationLedgerResult:
    return PageCompositionApplicationLedgerResult(
        binding.application_id,
        outcome,
        lifecycle,
        binding if outcome in {"prepared", "applied", "confirmed"} else None,
    )


def _verified_row(
    row: object,
) -> tuple[PageCompositionApplicationBinding, ApplicationLifecycle] | None:
    if not isinstance(row, tuple) or len(row) != 7:
        return None
    (
        project_id,
        page_id,
        page_revision,
        lifecycle,
        payload,
        payload_digest,
        binding_fingerprint,
    ) = row
    if lifecycle not in {"prepared", "applied"}:
        return None
    if (
        not isinstance(payload, str)
        or not isinstance(payload_digest, str)
        or _digest(payload) != payload_digest
    ):
        return None
    try:
        binding = PageCompositionApplicationBinding.model_validate_json(payload)
    except Exception:
        return None
    if (
        binding.project_id != project_id
        or binding.page_id != page_id
        or binding.page_revision != page_revision
        or binding.binding_fingerprint != binding_fingerprint
    ):
        return None
    return binding, lifecycle


def _canonical_json(binding: PageCompositionApplicationBinding) -> str:
    return json.dumps(
        binding.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _prepare_root(root: Path) -> Path:
    if not isinstance(root, Path) or root.is_symlink() or _is_reparse(root):
        raise ValueError("composition application root is unavailable")
    root.mkdir(parents=True, exist_ok=True)
    resolved = root.resolve(strict=True)
    if not resolved.is_dir() or resolved.is_symlink() or _is_reparse(resolved):
        raise ValueError("composition application root is unavailable")
    return resolved


def _prepare_database(root: Path) -> Path:
    path = root / _DATABASE_FILENAME
    if path.exists() and (not path.is_file() or path.is_symlink() or _is_reparse(path)):
        raise ValueError("composition application ledger is unavailable")
    if path.resolve(strict=False).parent != root:
        raise ValueError("composition application ledger is unavailable")
    return path


def _is_reparse(path: Path) -> bool:
    try:
        attributes = path.lstat()
        return bool(
            getattr(attributes, "st_file_attributes", 0)
            & stat.FILE_ATTRIBUTE_REPARSE_POINT
        )
    except (FileNotFoundError, OSError):
        return False


def _rollback(connection: sqlite3.Connection) -> None:
    try:
        connection.rollback()
    except sqlite3.Error:
        pass
