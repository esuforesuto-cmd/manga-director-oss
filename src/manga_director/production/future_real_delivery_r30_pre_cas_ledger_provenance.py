"""Private R30 immutable pre-CAS Ledger provenance sidecar.

The sidecar is deliberately not an application authority.  It records only
the exact prepared Ledger binding observed by the canonical LocalFile
Coordinator before R27 publication, and exposes an exact read-only replay for
the later sealed restart inlet.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, cast

from manga_director.production.next_generation_workflow_application_ledger import (
    WorkflowApplicationLedgerBindingDTO,
)
from manga_director.repositories.local_file import LocalFileRepository

_SCHEMA_ID: Final = "manga_director.r30.pre_cas_ledger_provenance"
_SCHEMA_VERSION: Final = 1
_DIRECTORY: Final = "_r30_pre_cas_ledger_provenance"
_DATABASE: Final = "r30-pre-cas-ledger-provenance.sqlite3"
_META_TABLE: Final = "r30_pre_cas_ledger_provenance_schema_meta"
_TABLE: Final = "r30_pre_cas_ledger_provenance"

_DDL_META: Final = (
    "CREATE TABLE r30_pre_cas_ledger_provenance_schema_meta "
    "(schema_id TEXT PRIMARY KEY, schema_version INTEGER NOT NULL)"
)
_DDL_ROWS: Final = (
    "CREATE TABLE r30_pre_cas_ledger_provenance ("
    "provenance_identity TEXT PRIMARY KEY, "
    "application_binding_identity TEXT NOT NULL UNIQUE, "
    "attempt_id TEXT NOT NULL UNIQUE, authorization_id TEXT NOT NULL UNIQUE, "
    "project_id TEXT NOT NULL, page_id TEXT NOT NULL, "
    "target_page_reference TEXT NOT NULL, provider_reference TEXT NOT NULL, "
    "output_asset_id TEXT NOT NULL, "
    "source_state TEXT NOT NULL CHECK(source_state = 'PromptBuilt'), "
    "target_state TEXT NOT NULL CHECK(target_state = 'Generated'), "
    "expected_pre_cas_revision INTEGER NOT NULL, "
    "expected_pre_cas_fingerprint TEXT NOT NULL, "
    "ledger_binding_json TEXT NOT NULL, ledger_binding_digest TEXT NOT NULL, "
    "record_json TEXT NOT NULL, record_digest TEXT NOT NULL, "
    "UNIQUE(project_id, page_id, expected_pre_cas_revision, expected_pre_cas_fingerprint))"
)


@dataclass(frozen=True, slots=True)
class _R30PreCasProvenanceRecordV1:
    provenance_identity: str
    values: tuple[str | int, ...]
    record_json: str
    record_digest: str


def _corrupt() -> ValueError:
    return ValueError("CORRUPT")


def _recovery_required() -> ValueError:
    return ValueError("RECOVERY_REQUIRED")


class _R30PreCasLedgerProvenanceStoreV1:
    """Fixed-path SQLite owner; construction is restricted to LocalFile composition."""

    __slots__ = ("_database_path",)
    _database_path: Path

    def __init__(self, *args: object) -> None:
        del args
        raise ValueError("AUTHORITY_REJECTED")

    def _initialize_or_validate_v1(self) -> None:
        database = self._database_path
        if database.exists():
            if not _regular_file(database) or database.stat().st_size == 0:
                raise _corrupt()
            _validate_existing(database)
            return
        if not _create_empty_directory(database):
            raise _corrupt()
        connection: sqlite3.Connection | None = None
        try:
            connection = _open_write(database)
            connection.execute("BEGIN IMMEDIATE")
            if _objects(connection) or _user_version(connection) != 0:
                raise _corrupt()
            connection.execute(_DDL_META)
            connection.execute(_DDL_ROWS)
            connection.execute(
                f"INSERT INTO {_META_TABLE} (schema_id, schema_version) VALUES (?, ?)",
                (_SCHEMA_ID, _SCHEMA_VERSION),
            )
            connection.execute("PRAGMA user_version = 1")
            connection.commit()
            _validate_schema(connection)
        except ValueError:
            _rollback(connection)
            raise
        except (OSError, sqlite3.Error, TypeError) as error:
            _rollback(connection)
            raise _recovery_required() from error
        finally:
            _close(connection)

    def _create_or_confirm_v1(
        self, record: object
    ) -> tuple[Literal["CREATED", "EXACT_REPLAY", "CONFLICT", "CORRUPT"], _R30PreCasProvenanceRecordV1 | None]:
        if type(record) is not _R30PreCasProvenanceRecordV1:
            raise ValueError("AUTHORITY_REJECTED")
        canonical = record
        connection: sqlite3.Connection | None = None
        try:
            connection = _open_write(self._database_path)
            connection.execute("BEGIN IMMEDIATE")
            _validate_schema(connection)
            existing = _select_by_binding(connection, cast(str, canonical.values[1]))
            if existing is None:
                connection.execute(
                    f"INSERT INTO {_TABLE} ("
                    "provenance_identity, application_binding_identity, attempt_id, authorization_id, "
                    "project_id, page_id, target_page_reference, provider_reference, output_asset_id, "
                    "source_state, target_state, expected_pre_cas_revision, expected_pre_cas_fingerprint, "
                    "ledger_binding_json, ledger_binding_digest, record_json, record_digest) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    canonical.values,
                )
                connection.commit()
                return "CREATED", canonical
            if existing != canonical:
                connection.rollback()
                return "CONFLICT", None
            connection.rollback()
            return "EXACT_REPLAY", existing
        except ValueError:
            _rollback(connection)
            return "CORRUPT", None
        except (OSError, sqlite3.Error, TypeError):
            _rollback(connection)
            return "CORRUPT", None
        finally:
            _close(connection)

    def _read_exact_v1(self, binding: object) -> _R30PreCasProvenanceRecordV1 | None:
        if type(binding) is not WorkflowApplicationLedgerBindingDTO:
            raise ValueError("AUTHORITY_REJECTED")
        expected = _application_binding_identity(binding)
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(
                f"{self._database_path.as_uri()}?mode=ro", uri=True, timeout=0.0, isolation_level=None
            )
            connection.execute("PRAGMA query_only=ON")
            if connection.execute("PRAGMA query_only").fetchone() != (1,):
                raise _recovery_required()
            connection.execute("BEGIN")
            _validate_schema(connection)
            record = _select_by_binding(connection, expected)
            connection.rollback()
            return record
        except ValueError:
            _rollback(connection)
            raise
        except (OSError, sqlite3.Error, TypeError) as error:
            _rollback(connection)
            raise _recovery_required() from error
        finally:
            _close(connection)


def _construct_r30_pre_cas_ledger_provenance_store_v1(
    repository: object,
) -> _R30PreCasLedgerProvenanceStoreV1:
    if type(repository) is not LocalFileRepository:
        raise ValueError("AUTHORITY_REJECTED")
    root = repository._root.resolve()
    if not root.is_absolute() or not root.is_dir():
        raise _recovery_required()
    database = root / "_durability" / _DIRECTORY / _DATABASE
    if database.parent.parent != root / "_durability":
        raise _recovery_required()
    store = object.__new__(_R30PreCasLedgerProvenanceStoreV1)
    object.__setattr__(store, "_database_path", database)
    store._initialize_or_validate_v1()
    return store


def _canonical_r30_pre_cas_provenance_v1(
    binding: object, *, expected_pre_cas_revision: object, expected_pre_cas_fingerprint: object
) -> _R30PreCasProvenanceRecordV1:
    if (
        type(binding) is not WorkflowApplicationLedgerBindingDTO
        or type(expected_pre_cas_revision) is not int
        or expected_pre_cas_revision < 1
        or not _sha256(expected_pre_cas_fingerprint)
        or binding.source_state != "PromptBuilt"
        or binding.target_state != "Generated"
    ):
        raise ValueError("AUTHORITY_REJECTED")
    exact = binding
    fingerprint = cast(str, expected_pre_cas_fingerprint)
    binding_json = _canonical_json(exact.model_dump(mode="json"))
    binding_digest = _digest(binding_json)
    application_identity = _application_binding_identity(exact)
    identity_body = {
        "application_binding_identity": application_identity,
        "attempt_id": exact.attempt_id,
        "authorization_id": exact.authorization_id,
        "expected_pre_cas_fingerprint": fingerprint,
        "expected_pre_cas_revision": expected_pre_cas_revision,
        "page_id": exact.page_id,
        "project_id": exact.project_id,
        "schema_id": _SCHEMA_ID,
        "schema_version": _SCHEMA_VERSION,
        "target_page_reference": exact.target_page_reference,
    }
    identity = _digest(_canonical_json(identity_body))
    body = {
        **identity_body,
        "ledger_binding_digest": binding_digest,
        "ledger_binding_json": binding_json,
        "output_asset_id": exact.output_asset_id,
        "provider_reference": exact.provider_reference,
        "provenance_identity": identity,
        "source_state": exact.source_state,
        "target_state": exact.target_state,
    }
    record_json = _canonical_json(body)
    record_digest = _digest(record_json)
    return _R30PreCasProvenanceRecordV1(
        identity,
        (
            identity, application_identity, exact.attempt_id, exact.authorization_id,
            exact.project_id, exact.page_id, exact.target_page_reference, exact.provider_reference,
            exact.output_asset_id, exact.source_state, exact.target_state, expected_pre_cas_revision,
            fingerprint, binding_json, binding_digest, record_json, record_digest,
        ),
        record_json,
        record_digest,
    )


def _select_by_binding(
    connection: sqlite3.Connection, application_binding_identity: str
) -> _R30PreCasProvenanceRecordV1 | None:
    rows = connection.execute(
        f"SELECT provenance_identity, application_binding_identity, attempt_id, authorization_id, "
        "project_id, page_id, target_page_reference, provider_reference, output_asset_id, "
        "source_state, target_state, expected_pre_cas_revision, expected_pre_cas_fingerprint, "
        "ledger_binding_json, ledger_binding_digest, record_json, record_digest "
        f"FROM {_TABLE} WHERE application_binding_identity = ?",
        (application_binding_identity,),
    ).fetchall()
    if not isinstance(rows, list) or len(rows) > 1:
        raise _corrupt()
    if not rows:
        return None
    row = rows[0]
    if not isinstance(row, tuple) or len(row) != 17:
        raise _corrupt()
    try:
        binding = json.loads(cast(str, row[13]))
        if type(binding) is not dict:
            raise ValueError
        dto = WorkflowApplicationLedgerBindingDTO.model_validate(binding)
        rebuilt = _canonical_r30_pre_cas_provenance_v1(
            dto, expected_pre_cas_revision=row[11], expected_pre_cas_fingerprint=row[12]
        )
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise _corrupt() from error
    if rebuilt.values != tuple(row) or rebuilt.record_json != row[15] or rebuilt.record_digest != row[16]:
        raise _corrupt()
    return rebuilt


def _validate_existing(database: Path) -> None:
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(f"{database.as_uri()}?mode=ro", uri=True, timeout=0.0, isolation_level=None)
        connection.execute("PRAGMA query_only=ON")
        if connection.execute("PRAGMA query_only").fetchone() != (1,):
            raise _recovery_required()
        connection.execute("BEGIN")
        _validate_schema(connection)
        connection.rollback()
    except ValueError:
        _rollback(connection)
        raise
    except (OSError, sqlite3.Error, TypeError) as error:
        _rollback(connection)
        raise _recovery_required() from error
    finally:
        _close(connection)


def _validate_schema(connection: sqlite3.Connection) -> None:
    try:
        if _user_version(connection) != 1 or _objects(connection) != ((_TABLE, "table"), (_META_TABLE, "table")):
            raise _corrupt()
        if connection.execute("PRAGMA journal_mode").fetchone() != ("delete",):
            raise _corrupt()
        meta = connection.execute(f"SELECT schema_id, schema_version FROM {_META_TABLE}").fetchall()
        if meta != [(_SCHEMA_ID, _SCHEMA_VERSION)]:
            raise _corrupt()
        if _normalized_ddl(connection, _META_TABLE) != _normalize(_DDL_META) or _normalized_ddl(connection, _TABLE) != _normalize(_DDL_ROWS):
            raise _corrupt()
        expected_columns = (
            ("provenance_identity", "TEXT", 0, None, 1), ("application_binding_identity", "TEXT", 1, None, 0),
            ("attempt_id", "TEXT", 1, None, 0), ("authorization_id", "TEXT", 1, None, 0),
            ("project_id", "TEXT", 1, None, 0), ("page_id", "TEXT", 1, None, 0),
            ("target_page_reference", "TEXT", 1, None, 0), ("provider_reference", "TEXT", 1, None, 0),
            ("output_asset_id", "TEXT", 1, None, 0), ("source_state", "TEXT", 1, None, 0),
            ("target_state", "TEXT", 1, None, 0), ("expected_pre_cas_revision", "INTEGER", 1, None, 0),
            ("expected_pre_cas_fingerprint", "TEXT", 1, None, 0), ("ledger_binding_json", "TEXT", 1, None, 0),
            ("ledger_binding_digest", "TEXT", 1, None, 0), ("record_json", "TEXT", 1, None, 0), ("record_digest", "TEXT", 1, None, 0),
        )
        columns = tuple((r[1], r[2], r[3], r[4], r[5]) for r in connection.execute(f"PRAGMA table_info({_TABLE})").fetchall())
        if columns != expected_columns:
            raise _corrupt()
        expected_indexes = (
            ("sqlite_autoindex_r30_pre_cas_ledger_provenance_1", 1, "pk", 0, ("provenance_identity",)),
            ("sqlite_autoindex_r30_pre_cas_ledger_provenance_2", 1, "u", 0, ("application_binding_identity",)),
            ("sqlite_autoindex_r30_pre_cas_ledger_provenance_3", 1, "u", 0, ("attempt_id",)),
            ("sqlite_autoindex_r30_pre_cas_ledger_provenance_4", 1, "u", 0, ("authorization_id",)),
            (
                "sqlite_autoindex_r30_pre_cas_ledger_provenance_5",
                1,
                "u",
                0,
                ("project_id", "page_id", "expected_pre_cas_revision", "expected_pre_cas_fingerprint"),
            ),
        )
        actual_indexes = tuple(
            sorted(
                (
                    name,
                    unique,
                    origin,
                    partial,
                    tuple(row[2] for row in connection.execute(f"PRAGMA index_info({name})").fetchall()),
                )
                for _sequence, name, unique, origin, partial in connection.execute(f"PRAGMA index_list({_TABLE})").fetchall()
            )
        )
        if actual_indexes != expected_indexes:
            raise _corrupt()
    except sqlite3.Error as error:
        raise _corrupt() from error


def _application_binding_identity(binding: WorkflowApplicationLedgerBindingDTO) -> str:
    return _digest(_canonical_json({
        "attempt_id": binding.attempt_id, "authorization_id": binding.authorization_id,
        "output_asset_id": binding.output_asset_id, "page_id": binding.page_id,
        "project_id": binding.project_id, "provider_reference": binding.provider_reference,
        "schema": "manga_director.r27.application-binding", "source_state": binding.source_state,
        "target_page_reference": binding.target_page_reference, "target_state": binding.target_state,
        "version": 1,
    }))


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True, allow_nan=False)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256(value: object) -> bool:
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _regular_file(path: Path) -> bool:
    try:
        return path.is_file() and not path.is_symlink() and stat.S_ISREG(path.stat().st_mode)
    except OSError:
        return False


def _create_empty_directory(database: Path) -> bool:
    directory = database.parent
    try:
        if directory.exists():
            return directory.is_dir() and not any(directory.iterdir())
        directory.mkdir(parents=True, exist_ok=False)
        return True
    except OSError as error:
        raise _recovery_required() from error


def _open_write(database: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database, timeout=0.0, isolation_level=None)
    if connection.execute("PRAGMA journal_mode = DELETE").fetchone() != ("delete",):
        raise _recovery_required()
    connection.execute("PRAGMA synchronous = FULL")
    return connection


def _user_version(connection: sqlite3.Connection) -> int:
    value = connection.execute("PRAGMA user_version").fetchone()
    return int(value[0]) if isinstance(value, tuple) and len(value) == 1 else -1


def _objects(connection: sqlite3.Connection) -> tuple[tuple[str, str], ...]:
    rows = connection.execute("SELECT name, type FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
    return tuple((cast(str, row[0]), cast(str, row[1])) for row in rows)


def _normalized_ddl(connection: sqlite3.Connection, name: str) -> str:
    row = connection.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)).fetchone()
    if not isinstance(row, tuple) or len(row) != 1 or type(row[0]) is not str:
        raise _corrupt()
    return _normalize(row[0])


def _normalize(value: str) -> str:
    return "".join(character for character in value if character not in " \t\r\n\f\v")


def _rollback(connection: sqlite3.Connection | None) -> None:
    if connection is not None:
        try:
            connection.rollback()
        except sqlite3.Error:
            pass


def _close(connection: sqlite3.Connection | None) -> None:
    if connection is not None:
        connection.close()
