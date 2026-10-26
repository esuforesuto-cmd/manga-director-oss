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
AppliedBindingLookupOutcome = Literal[
    "found",
    "missing",
    "prepared",
    "asset_mismatch",
    "ambiguous",
    "corrupt",
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


@dataclass(frozen=True, slots=True)
class PageCompositionAppliedBindingLookupResult:
    outcome: AppliedBindingLookupOutcome
    binding: PageCompositionApplicationBinding | None = field(
        default=None, repr=False
    )


@dataclass(frozen=True, slots=True)
class PageCompositionApplicationObservation:
    outcome: Literal["found", "missing", "corrupt", "ambiguous", "prepared"]
    plan_ids: tuple[str, ...] = ()
    composition_attempt_ids: tuple[str, ...] = ()
    bindings: tuple[PageCompositionApplicationBinding, ...] = field(
        default=(), repr=False
    )


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

    def lookup_applied(
        self,
        project_id: str,
        page_id: str,
        output_asset_id: str,
    ) -> PageCompositionAppliedBindingLookupResult:
        """Return one canonical applied binding without mutating the ledger."""

        try:
            project = logical_reference(project_id, "composition application project")
            page = logical_reference(page_id, "composition application Page")
            asset = logical_reference(output_asset_id, "composite asset")
        except ValueError:
            return PageCompositionAppliedBindingLookupResult("corrupt")
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
                return PageCompositionAppliedBindingLookupResult("corrupt")
            matching_page = [
                item
                for item in verified
                if item is not None
                and item[0].project_id == project
                and item[0].page_id == page
            ]
            if not matching_page:
                return PageCompositionAppliedBindingLookupResult("missing")
            if len(matching_page) != 1:
                return PageCompositionAppliedBindingLookupResult("ambiguous")
            binding, lifecycle = matching_page[0]
            if binding.composite_asset_id != asset:
                return PageCompositionAppliedBindingLookupResult("asset_mismatch")
            if lifecycle != "applied":
                return PageCompositionAppliedBindingLookupResult("prepared")
            return PageCompositionAppliedBindingLookupResult("found", binding)
        except Exception:
            return PageCompositionAppliedBindingLookupResult("corrupt")
        finally:
            if connection is not None:
                connection.close()

    def observe_page(
        self, project_id: str, page_id: str
    ) -> PageCompositionApplicationObservation:
        path_status = _readonly_application_status(self._root, self._database_path)
        if path_status == "missing":
            return PageCompositionApplicationObservation("missing")
        if path_status == "corrupt":
            return PageCompositionApplicationObservation("corrupt")
        try:
            uri = f"{self._database_path.as_uri()}?mode=ro"
            with sqlite3.connect(uri, uri=True) as connection:
                connection.execute("PRAGMA query_only = ON")
                if int(connection.execute("PRAGMA user_version").fetchone()[0]) != _SCHEMA_VERSION:
                    return PageCompositionApplicationObservation("corrupt")
                columns = tuple(
                    (str(row[1]), str(row[2]).upper(), int(row[3]), row[4], int(row[5]))
                    for row in connection.execute(
                        "PRAGMA table_info(composition_application)"
                    )
                )
                if not _application_schema_objects_are_exact(connection) or columns != (
                    ("application_id", "TEXT", 0, None, 1),
                    ("project_id", "TEXT", 1, None, 0),
                    ("page_id", "TEXT", 1, None, 0),
                    ("page_revision", "TEXT", 1, None, 0),
                    ("lifecycle", "TEXT", 1, None, 0),
                    ("payload_json", "TEXT", 1, None, 0),
                    ("payload_digest", "TEXT", 1, None, 0),
                    ("binding_fingerprint", "TEXT", 1, None, 0),
                ):
                    return PageCompositionApplicationObservation("corrupt")
                rows = connection.execute(
                    "SELECT project_id, page_id, page_revision, lifecycle, payload_json, "
                    "payload_digest, binding_fingerprint FROM composition_application"
                ).fetchall()
            verified = tuple(_verified_row(row) for row in rows)
            if any(item is None for item in verified):
                return PageCompositionApplicationObservation("corrupt")
            matching = tuple(
                item
                for item in verified
                if item is not None
                and item[0].project_id == project_id
                and item[0].page_id == page_id
            )
        except Exception:
            return PageCompositionApplicationObservation("corrupt")
        if not matching:
            return PageCompositionApplicationObservation("missing")
        if len(matching) != 1:
            return PageCompositionApplicationObservation("ambiguous")
        binding, lifecycle = matching[0]
        return PageCompositionApplicationObservation(
            "prepared" if lifecycle == "prepared" else "found",
            (binding.plan_id,),
            (binding.composition_attempt_id,),
            (binding,),
        )

    @classmethod
    def observe_page_at(
        cls, owner_root: Path, project_id: str, page_id: str
    ) -> PageCompositionApplicationObservation:
        ledger = object.__new__(cls)
        ledger._root = owner_root
        ledger._database_path = owner_root / _DATABASE_FILENAME
        return ledger.observe_page(project_id, page_id)

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


def _readonly_application_status(
    root: Path, database: Path
) -> Literal["found", "missing", "corrupt"]:
    try:
        root_kind = _readonly_path_kind(root)
        if root_kind == "missing":
            return "missing"
        parent = root.parent
        if (
            not root.is_absolute()
            or root_kind != "directory"
            or _readonly_path_kind(parent) != "directory"
        ):
            return "corrupt"
        if (
            _readonly_path_kind(database) != "file"
            or database.resolve(strict=True).parent != root.resolve(strict=True)
        ):
            return "corrupt"
        return "found"
    except OSError:
        return "corrupt"


def _readonly_path_kind(
    path: Path,
) -> Literal["missing", "file", "directory", "unsafe"]:
    try:
        status = path.lstat()
    except FileNotFoundError:
        return "missing"
    except OSError:
        return "unsafe"
    attributes = getattr(status, "st_file_attributes", 0)
    if stat.S_ISLNK(status.st_mode) or bool(
        attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    ):
        return "unsafe"
    if stat.S_ISREG(status.st_mode):
        return "file"
    if stat.S_ISDIR(status.st_mode):
        return "directory"
    return "unsafe"


def _application_schema_objects_are_exact(connection: sqlite3.Connection) -> bool:
    objects = connection.execute(
        "SELECT type, name, tbl_name FROM sqlite_master "
        "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
    ).fetchall()
    if objects != [
        ("table", "composition_application", "composition_application")
    ]:
        return False
    indexes = connection.execute(
        "PRAGMA index_list(composition_application)"
    ).fetchall()
    observed: set[tuple[int, str, int, tuple[str, ...]]] = set()
    for index in indexes:
        if len(index) != 5 or not isinstance(index[1], str):
            return False
        columns = tuple(
            str(row[2])
            for row in connection.execute(
                f"PRAGMA index_info({index[1]})"
            ).fetchall()
        )
        observed.add((int(index[2]), str(index[3]), int(index[4]), columns))
    return observed == {
        (1, "pk", 0, ("application_id",)),
        (1, "u", 0, ("project_id", "page_id", "page_revision")),
    }


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
