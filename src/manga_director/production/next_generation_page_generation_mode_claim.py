"""Private durable authority for one Page generation mode per revision."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol

from pydantic import ConfigDict, field_validator, model_validator

from manga_director.production.director import DirectorModel
from manga_director.production.next_generation_page_generation_plan import (
    canonical_digest,
    logical_reference,
    sha256_digest,
)

GenerationMode = Literal["legacy_single_canvas", "panel_aware"]
ClaimStatus = Literal["active", "recovery_required"]
ClaimStoreOutcome = Literal["created", "confirmed", "conflict", "corrupt", "failed"]
ClaimLookupOutcome = Literal["found", "missing", "ambiguous", "corrupt"]

_DATABASE_FILENAME = "page-generation-mode-claims.sqlite3"
_SCHEMA_VERSION = 1
_TABLE_NAME = "page_generation_mode_claims"


class _ModeClaimModel(DirectorModel):
    model_config = ConfigDict(
        frozen=True, extra="forbid", strict=True, validate_default=True
    )


class PageGenerationModeClaim(_ModeClaimModel):
    """Immutable claim binding one Page revision to one generation route."""

    claim_id: str
    project_id: str
    page_id: str
    page_revision: str
    page_fingerprint: str
    source_state: Literal["PromptBuilt"] = "PromptBuilt"
    mode: GenerationMode
    mode_binding_reference: str
    authorizer_reference: str
    status: ClaimStatus = "active"
    binding_fingerprint: str | None = None

    @field_validator(
        "claim_id",
        "project_id",
        "page_id",
        "page_revision",
        "mode_binding_reference",
        "authorizer_reference",
        mode="before",
    )
    @classmethod
    def _references(cls, value: object) -> str:
        return logical_reference(value, "Page generation mode claim reference")

    @field_validator("page_fingerprint")
    @classmethod
    def _page_digest(cls, value: str) -> str:
        return sha256_digest(value)

    @model_validator(mode="after")
    def _canonical_binding(self) -> PageGenerationModeClaim:
        expected = canonical_digest(
            self.model_dump(mode="json", exclude={"binding_fingerprint"})
        )
        if self.binding_fingerprint is not None:
            sha256_digest(self.binding_fingerprint)
            if self.binding_fingerprint != expected:
                raise ValueError("claim binding fingerprint does not match its content")
        object.__setattr__(self, "binding_fingerprint", expected)
        return self


@dataclass(frozen=True, slots=True)
class PageGenerationModeClaimStoreResult:
    claim_id: str
    outcome: ClaimStoreOutcome


@dataclass(frozen=True, slots=True)
class PageGenerationModeClaimLookupResult:
    outcome: ClaimLookupOutcome
    claim: PageGenerationModeClaim | None = field(default=None, repr=False)


class PageGenerationModeClaimStorePort(Protocol):
    def create_or_confirm(
        self, claim: PageGenerationModeClaim
    ) -> PageGenerationModeClaimStoreResult: ...

    def lookup_active(
        self, project_id: str, page_id: str, page_revision: str
    ) -> PageGenerationModeClaimLookupResult: ...


class LocalPageGenerationModeClaimStore(PageGenerationModeClaimStorePort):
    """Versioned SQLite sidecar with atomic create-or-confirm semantics."""

    def __init__(self, owner_root: Path) -> None:
        self._root = _prepare_root(owner_root)
        self._database_path = _prepare_database_path(self._root)
        self._initialize_schema()

    def create_or_confirm(  # noqa: C901
        self, claim: PageGenerationModeClaim
    ) -> PageGenerationModeClaimStoreResult:
        if not isinstance(claim, PageGenerationModeClaim):
            return PageGenerationModeClaimStoreResult("", "failed")
        payload = _canonical_json(claim)
        payload_digest = _digest(payload)
        connection: sqlite3.Connection | None = None
        try:
            connection = self._connect()
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                f"SELECT claim_id, project_id, page_id, page_revision, status, payload_json, "
                f"payload_digest, binding_fingerprint FROM {_TABLE_NAME}"
            ).fetchall()
            verified = [_verified_claim(row) for row in rows]
            if any(item is None for item in verified):
                connection.rollback()
                return PageGenerationModeClaimStoreResult(claim.claim_id, "corrupt")
            active = [
                item
                for item in verified
                if item is not None
                and item.project_id == claim.project_id
                and item.page_id == claim.page_id
            ]
            if len(active) > 1:
                connection.rollback()
                return PageGenerationModeClaimStoreResult(claim.claim_id, "corrupt")
            if active:
                existing = active[0]
                connection.rollback()
                if existing == claim and payload == _canonical_json(existing):
                    return PageGenerationModeClaimStoreResult(claim.claim_id, "confirmed")
                return PageGenerationModeClaimStoreResult(claim.claim_id, "conflict")
            same_id = next(
                (item for item in verified if item is not None and item.claim_id == claim.claim_id),
                None,
            )
            if same_id is not None:
                connection.rollback()
                if same_id == claim:
                    return PageGenerationModeClaimStoreResult(claim.claim_id, "confirmed")
                return PageGenerationModeClaimStoreResult(claim.claim_id, "conflict")
            connection.execute(
                f"INSERT INTO {_TABLE_NAME} "
                "(claim_id, project_id, page_id, page_revision, status, payload_json, payload_digest, binding_fingerprint) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    claim.claim_id,
                    claim.project_id,
                    claim.page_id,
                    claim.page_revision,
                    claim.status,
                    payload,
                    payload_digest,
                    claim.binding_fingerprint,
                ),
            )
            connection.commit()
            return PageGenerationModeClaimStoreResult(claim.claim_id, "created")
        except sqlite3.IntegrityError:
            if connection is not None:
                _rollback(connection)
            return PageGenerationModeClaimStoreResult(claim.claim_id, "conflict")
        except Exception:
            if connection is not None:
                _rollback(connection)
            return PageGenerationModeClaimStoreResult(claim.claim_id, "failed")
        finally:
            if connection is not None:
                connection.close()

    def lookup_active(
        self, project_id: str, page_id: str, page_revision: str
    ) -> PageGenerationModeClaimLookupResult:
        try:
            project = logical_reference(project_id, "project")
            page = logical_reference(page_id, "Page")
            revision = logical_reference(page_revision, "Page revision")
        except ValueError:
            return PageGenerationModeClaimLookupResult("corrupt")
        connection: sqlite3.Connection | None = None
        try:
            connection = self._connect()
            rows = connection.execute(
                f"SELECT claim_id, project_id, page_id, page_revision, status, payload_json, "
                f"payload_digest, binding_fingerprint FROM {_TABLE_NAME}"
            ).fetchall()
            verified = [_verified_claim(row) for row in rows]
            if any(item is None for item in verified):
                return PageGenerationModeClaimLookupResult("corrupt")
            active = [
                item
                for item in verified
                if item is not None and item.project_id == project and item.page_id == page
            ]
            if not active:
                return PageGenerationModeClaimLookupResult("missing")
            if len(active) != 1:
                return PageGenerationModeClaimLookupResult("ambiguous")
            claim = active[0]
            if claim.page_revision != revision:
                return PageGenerationModeClaimLookupResult("corrupt")
            return PageGenerationModeClaimLookupResult("found", claim)
        except Exception:
            return PageGenerationModeClaimLookupResult("corrupt")
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
                    f"CREATE TABLE {_TABLE_NAME} ("
                    "claim_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, page_id TEXT NOT NULL, "
                    "page_revision TEXT NOT NULL, status TEXT NOT NULL, payload_json TEXT NOT NULL, "
                    "payload_digest TEXT NOT NULL, binding_fingerprint TEXT NOT NULL)"
                )
                connection.execute(
                    f"CREATE UNIQUE INDEX one_live_mode_per_page ON {_TABLE_NAME}(project_id, page_id) "
                    "WHERE status IN ('active', 'recovery_required')"
                )
                connection.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")
                connection.commit()
                return
            expected = {
                "claim_id", "project_id", "page_id", "page_revision", "status",
                "payload_json", "payload_digest", "binding_fingerprint",
            }
            columns = {
                str(row[1]) for row in connection.execute(f"PRAGMA table_info({_TABLE_NAME})")
            }
            if version != _SCHEMA_VERSION or columns != expected:
                raise ValueError("mode claim store is unavailable")
            connection.commit()
        except Exception as error:
            if connection is not None:
                _rollback(connection)
            raise ValueError("mode claim store is unavailable") from error
        finally:
            if connection is not None:
                connection.close()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=5.0, isolation_level=None)
        mode = str(connection.execute("PRAGMA journal_mode = DELETE").fetchone()[0]).lower()
        if mode != "delete":
            connection.close()
            raise ValueError("mode claim store is unavailable")
        connection.execute("PRAGMA synchronous = FULL")
        return connection


def _verified_claim(row: object) -> PageGenerationModeClaim | None:
    if not isinstance(row, tuple) or len(row) != 8:
        return None
    (
        claim_id,
        project_id,
        page_id,
        page_revision,
        status,
        payload,
        digest,
        binding_fingerprint,
    ) = row
    if not all(isinstance(value, str) for value in row) or _digest(payload) != digest:
        return None
    try:
        claim = PageGenerationModeClaim.model_validate_json(payload)
    except Exception:
        return None
    return (
        claim
        if claim.claim_id == claim_id
        and claim.project_id == project_id
        and claim.page_id == page_id
        and claim.page_revision == page_revision
        and claim.status == status
        and claim.binding_fingerprint == binding_fingerprint
        else None
    )


def _canonical_json(claim: PageGenerationModeClaim) -> str:
    return json.dumps(
        claim.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _prepare_root(root: Path) -> Path:
    if not isinstance(root, Path) or root.is_symlink() or _is_reparse(root):
        raise ValueError("mode claim root is unavailable")
    root.mkdir(parents=True, exist_ok=True)
    resolved = root.resolve(strict=True)
    if not resolved.is_dir() or resolved.is_symlink() or _is_reparse(resolved):
        raise ValueError("mode claim root is unavailable")
    return resolved


def _prepare_database_path(root: Path) -> Path:
    path = root / _DATABASE_FILENAME
    if path.exists() and (not path.is_file() or path.is_symlink() or _is_reparse(path)):
        raise ValueError("mode claim store is unavailable")
    if path.resolve(strict=False).parent != root:
        raise ValueError("mode claim store is unavailable")
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
