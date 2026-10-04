"""Private R25 post-CAS attestation persistence.

This module owns only the fixed LocalFile SQLite store.  It deliberately has
no workflow, CAS, provider, Receipt, Ledger, or public-selection authority.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, cast

from manga_director.repositories.local_file import LocalFileRepository

_SCHEMA_ID: Final = "manga_director.post_cas_application_attestation"
_SCHEMA_VERSION: Final = 1
_STORE_DIRECTORY: Final = "_post_cas_application_attestations"
_DATABASE_FILENAME: Final = "post-cas-application-attestations.sqlite3"
_META_TABLE: Final = "post_cas_application_attestation_schema_meta"
_ATTESTATION_TABLE: Final = "post_cas_application_attestations"


class _R25ReplayFailureV1(ValueError):
    """Private structured result from the read-only R25 replay boundary."""

    __slots__ = ("outcome",)

    outcome: Literal["CORRUPT", "RECOVERY_REQUIRED"]

    def __init__(self, outcome: Literal["CORRUPT", "RECOVERY_REQUIRED"]) -> None:
        super().__init__(outcome)
        self.outcome = outcome


@dataclass(frozen=True, slots=True)
class _R25CanonicalRecordV1:
    """Canonical immutable R25 payload; it conveys no application authority."""

    attestation_identity: str
    values: tuple[str | int, ...]
    record_json: str
    record_digest: str


def _corrupt() -> _R25ReplayFailureV1:
    return _R25ReplayFailureV1("CORRUPT")


def _recovery_required() -> _R25ReplayFailureV1:
    return _R25ReplayFailureV1("RECOVERY_REQUIRED")


class _R25AttestationStoreV1:
    """Fixed-path, private R25 SQLite owner with strict v1 reopen validation."""

    __slots__ = ("_database_path",)

    _database_path: Path

    def __init__(self, *args: object) -> None:
        del args
        raise ValueError("AUTHORITY_REJECTED")

    def _initialize_or_validate_v1(self) -> None:
        database = self._database_path
        directory = database.parent
        if database.exists():
            if not _regular_file(database) or database.stat().st_size == 0:
                raise _corrupt()
            _validate_existing_store(database)
            return
        if not _create_empty_directory(database, directory):
            return
        connection: sqlite3.Connection | None = None
        try:
            connection = _open_write_connection(database)
            connection.execute("BEGIN IMMEDIATE")
            if _user_objects(connection) or _user_version(connection) != 0:
                raise _corrupt()
            _create_schema(connection)
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
    ) -> tuple[Literal["ATTESTED", "ATTESTED_REPLAY", "CONFLICT", "CORRUPT"], _R25CanonicalRecordV1 | None]:
        if type(record) is not _R25CanonicalRecordV1:
            raise ValueError("AUTHORITY_REJECTED")
        canonical = record
        connection: sqlite3.Connection | None = None
        try:
            connection = _open_write_connection(self._database_path)
            connection.execute("BEGIN IMMEDIATE")
            _validate_schema(connection)
            existing = _select_exact_record(connection, cast(str, canonical.values[3]))
            if existing is None:
                connection.execute(
                    f"INSERT INTO {_ATTESTATION_TABLE} ("
                    "attestation_identity, delivery_identity, attempt_id, application_binding_digest, "
                    "project_id, page_id, target_page_reference, provider_reference, authorization_id, "
                    "output_asset_id, canonical_result_identity, logical_output_id, asset_identity, "
                    "asset_sha256, expected_byte_length, media_type, evidence_identity, "
                    "evidence_persistence_digest, evidence_binding_fingerprint, pre_commit_revision, "
                    "pre_commit_fingerprint, post_commit_revision, post_commit_fingerprint, source_state, "
                    "target_state, application_binding_json, record_json, record_digest) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    canonical.values,
                )
                connection.commit()
                return "ATTESTED", canonical
            if existing != canonical:
                connection.rollback()
                return "CONFLICT", None
            connection.rollback()
            return "ATTESTED_REPLAY", existing
        except ValueError:
            _rollback(connection)
            return "CORRUPT", None
        except (OSError, sqlite3.Error, TypeError):
            _rollback(connection)
            return "CORRUPT", None
        finally:
            _close(connection)

    def _replay_post_cas_attestation_exact_v1(self, binding_digest: object) -> _R25CanonicalRecordV1 | None:
        if not _is_sha256(binding_digest):
            raise ValueError("AUTHORITY_REJECTED")
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
            record = _select_exact_record(connection, cast(str, binding_digest))
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


class _R25MaterializationRequestV1:
    """One-use private handoff to the R25 store, never a workflow capability."""

    __slots__ = ()

    def __init__(self, *args: object) -> None:
        del args
        raise ValueError("AUTHORITY_REJECTED")


class _R25MaterializationServiceV1:
    """Private create-or-confirm façade over one exact R25 store instance."""

    __slots__ = ("_requests", "_store")

    _requests: dict[_R25MaterializationRequestV1, _R25CanonicalRecordV1]
    _store: _R25AttestationStoreV1

    def __init__(self, *args: object) -> None:
        del args
        raise ValueError("AUTHORITY_REJECTED")

    def _issue_for_trusted_record_v1(self, record: object) -> _R25MaterializationRequestV1:
        """Seal one already-authenticated immutable record for exactly one call."""

        if type(record) is not _R25CanonicalRecordV1:
            raise ValueError("AUTHORITY_REJECTED")
        request = object.__new__(_R25MaterializationRequestV1)
        self._requests[request] = record
        return request

    def _materialize_v1(
        self, request: object
    ) -> tuple[Literal["ATTESTED", "ATTESTED_REPLAY", "CONFLICT", "CORRUPT"], _R25CanonicalRecordV1 | None]:
        """Consume before the SQLite operation, so failure cannot reissue a request."""

        if type(request) is not _R25MaterializationRequestV1:
            raise ValueError("AUTHORITY_REJECTED")
        record = self._requests.pop(request, None)
        if record is None:
            raise ValueError("AUTHORITY_REJECTED")
        return self._store._create_or_confirm_v1(record)


def _construct_r25_attestation_store_v1(repository: object) -> _R25AttestationStoreV1:
    """Construct only the fixed store derived from the exact LocalFile owner."""

    if type(repository) is not LocalFileRepository:
        raise ValueError("AUTHORITY_REJECTED")
    root = repository._root.resolve()
    if not root.is_absolute() or not root.is_dir():
        raise _recovery_required()
    database = root / "_durability" / _STORE_DIRECTORY / _DATABASE_FILENAME
    if database.parent.parent != root / "_durability":
        raise _recovery_required()
    store = object.__new__(_R25AttestationStoreV1)
    object.__setattr__(store, "_database_path", database)
    store._initialize_or_validate_v1()
    return store


def _construct_r25_materialization_service_v1(store: object) -> _R25MaterializationServiceV1:
    """Construct a private façade; composition pairing is enforced by its later owner."""

    if type(store) is not _R25AttestationStoreV1:
        raise ValueError("AUTHORITY_REJECTED")
    service = object.__new__(_R25MaterializationServiceV1)
    object.__setattr__(service, "_store", store)
    object.__setattr__(service, "_requests", {})
    return service


def _canonical_r25_record_v1(
    *,
    delivery_identity: str,
    attempt_id: str,
    application_binding_digest: str,
    project_id: str,
    page_id: str,
    target_page_reference: str,
    provider_reference: str,
    authorization_id: str,
    output_asset_id: str,
    canonical_result_identity: str,
    logical_output_id: str,
    asset_identity: str,
    asset_sha256: str,
    expected_byte_length: int,
    evidence_identity: str,
    evidence_persistence_digest: str,
    evidence_binding_fingerprint: str,
    pre_commit_revision: int,
    pre_commit_fingerprint: str,
    post_commit_revision: int,
    post_commit_fingerprint: str,
    application_binding_json: str,
) -> _R25CanonicalRecordV1:
    """Build the closed v1 row from already-authenticated private facts only."""

    text_values = (
        delivery_identity, attempt_id, application_binding_digest, project_id, page_id,
        target_page_reference, provider_reference, authorization_id, output_asset_id,
        canonical_result_identity, logical_output_id, asset_identity, asset_sha256,
        evidence_identity, evidence_persistence_digest, evidence_binding_fingerprint,
        pre_commit_fingerprint, post_commit_fingerprint,
    )
    if (
        not all(type(value) is str and value for value in text_values)
        or not all(_is_sha256(value) for value in (
            delivery_identity, application_binding_digest, asset_sha256, evidence_identity,
            evidence_persistence_digest, evidence_binding_fingerprint, pre_commit_fingerprint,
            post_commit_fingerprint,
        ))
        or type(expected_byte_length) is not int or expected_byte_length < 0
        or type(pre_commit_revision) is not int or pre_commit_revision < 1
        or type(post_commit_revision) is not int or post_commit_revision < 1
    ):
        raise ValueError("AUTHORITY_REJECTED")
    try:
        binding = json.loads(application_binding_json)
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError("AUTHORITY_REJECTED") from error
    if type(binding) is not dict or _canonical_json(cast(dict[str, object], binding)) != application_binding_json:
        raise ValueError("AUTHORITY_REJECTED")
    if _digest(application_binding_json) != application_binding_digest:
        raise ValueError("AUTHORITY_REJECTED")
    identity_body = {
        "application_binding_digest": application_binding_digest,
        "attempt_id": attempt_id,
        "delivery_identity": delivery_identity,
        "pre_commit_fingerprint": pre_commit_fingerprint,
        "pre_commit_revision": pre_commit_revision,
        "schema_id": _SCHEMA_ID,
        "schema_version": _SCHEMA_VERSION,
    }
    attestation_identity = _digest(_canonical_json(identity_body))
    body = {
        **identity_body,
        "attestation_identity": attestation_identity,
        "project_id": project_id,
        "page_id": page_id,
        "target_page_reference": target_page_reference,
        "provider_reference": provider_reference,
        "authorization_id": authorization_id,
        "output_asset_id": output_asset_id,
        "canonical_result_identity": canonical_result_identity,
        "logical_output_id": logical_output_id,
        "asset_identity": asset_identity,
        "asset_sha256": asset_sha256,
        "expected_byte_length": expected_byte_length,
        "media_type": "image/png",
        "evidence_identity": evidence_identity,
        "evidence_persistence_digest": evidence_persistence_digest,
        "evidence_binding_fingerprint": evidence_binding_fingerprint,
        "post_commit_revision": post_commit_revision,
        "post_commit_fingerprint": post_commit_fingerprint,
        "source_state": "PromptBuilt",
        "target_state": "Generated",
        "application_binding_json": application_binding_json,
    }
    record_json = _canonical_json(body)
    record_digest = _digest(record_json)
    values: tuple[str | int, ...] = (
        attestation_identity, delivery_identity, attempt_id, application_binding_digest,
        project_id, page_id, target_page_reference, provider_reference, authorization_id,
        output_asset_id, canonical_result_identity, logical_output_id, asset_identity,
        asset_sha256, expected_byte_length, "image/png", evidence_identity,
        evidence_persistence_digest, evidence_binding_fingerprint, pre_commit_revision,
        pre_commit_fingerprint, post_commit_revision, post_commit_fingerprint,
        "PromptBuilt", "Generated", application_binding_json, record_json, record_digest,
    )
    return _R25CanonicalRecordV1(attestation_identity, values, record_json, record_digest)


def _regular_file(path: Path) -> bool:
    try:
        return stat.S_ISREG(path.stat().st_mode)
    except OSError:
        return False


def _is_sha256(value: object) -> bool:
    return type(value) is str and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _canonical_json(value: dict[str, object]) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True, allow_nan=False)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _select_exact_record(connection: sqlite3.Connection, binding_digest: str) -> _R25CanonicalRecordV1 | None:
    rows = connection.execute(
        "SELECT attestation_identity, delivery_identity, attempt_id, application_binding_digest, "
        "project_id, page_id, target_page_reference, provider_reference, authorization_id, "
        "output_asset_id, canonical_result_identity, logical_output_id, asset_identity, asset_sha256, "
        "expected_byte_length, media_type, evidence_identity, evidence_persistence_digest, "
        "evidence_binding_fingerprint, pre_commit_revision, pre_commit_fingerprint, post_commit_revision, "
        "post_commit_fingerprint, source_state, target_state, application_binding_json, record_json, record_digest "
        f"FROM {_ATTESTATION_TABLE} WHERE application_binding_digest = ?",
        (binding_digest,),
    ).fetchall()
    if not rows:
        return None
    if len(rows) != 1 or len(rows[0]) != 28:
        raise _corrupt()
    row = rows[0]
    if any(type(value) is not str for value in (*row[:14], row[15], *row[16:19], row[20], *row[22:])) or type(row[14]) is not int or type(row[19]) is not int or type(row[21]) is not int:
        raise _corrupt()
    values = cast(tuple[str | int, ...], tuple(row))
    try:
        rebuilt = _canonical_r25_record_v1(
            delivery_identity=cast(str, row[1]), attempt_id=cast(str, row[2]),
            application_binding_digest=cast(str, row[3]), project_id=cast(str, row[4]),
            page_id=cast(str, row[5]), target_page_reference=cast(str, row[6]),
            provider_reference=cast(str, row[7]), authorization_id=cast(str, row[8]),
            output_asset_id=cast(str, row[9]), canonical_result_identity=cast(str, row[10]),
            logical_output_id=cast(str, row[11]), asset_identity=cast(str, row[12]),
            asset_sha256=cast(str, row[13]), expected_byte_length=row[14],
            evidence_identity=cast(str, row[16]), evidence_persistence_digest=cast(str, row[17]),
            evidence_binding_fingerprint=cast(str, row[18]), pre_commit_revision=row[19],
            pre_commit_fingerprint=cast(str, row[20]), post_commit_revision=row[21],
            post_commit_fingerprint=cast(str, row[22]), application_binding_json=cast(str, row[25]),
        )
    except ValueError as error:
        raise _corrupt() from error
    if values != rebuilt.values:
        raise _corrupt()
    return rebuilt


def _create_empty_directory(database: Path, directory: Path) -> bool:
    try:
        directory.parent.mkdir(exist_ok=True)
        directory.mkdir()
    except FileExistsError as error:
        if not directory.is_dir():
            raise _corrupt() from error
        if database.exists():
            if not _regular_file(database) or database.stat().st_size == 0:
                raise _corrupt() from error
            _validate_existing_store(database)
            return False
        raise _recovery_required() from error
    except OSError as error:
        raise _recovery_required() from error
    try:
        if any(directory.iterdir()):
            raise _corrupt()
    except OSError as error:
        raise _recovery_required() from error
    return True


def _validate_existing_store(database: Path) -> None:
    connection: sqlite3.Connection | None = None
    try:
        connection = _open_write_connection(database)
        _validate_schema(connection)
    except ValueError:
        raise
    except (OSError, sqlite3.Error, TypeError) as error:
        raise _recovery_required() from error
    finally:
        _close(connection)


def _open_write_connection(database: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(database), timeout=5.0, isolation_level=None)
    connection.execute("PRAGMA journal_mode=DELETE")
    connection.execute("PRAGMA synchronous=FULL")
    if connection.execute("PRAGMA journal_mode").fetchone() != ("delete",):
        raise _recovery_required()
    if connection.execute("PRAGMA synchronous").fetchone() != (2,):
        raise _recovery_required()
    return connection


def _create_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        f"CREATE TABLE {_META_TABLE} ("
        "schema_id TEXT PRIMARY KEY, schema_version INTEGER NOT NULL)"
    )
    connection.execute(
        f"CREATE TABLE {_ATTESTATION_TABLE} ("
        "attestation_identity TEXT PRIMARY KEY, "
        "delivery_identity TEXT NOT NULL UNIQUE, attempt_id TEXT NOT NULL UNIQUE, "
        "application_binding_digest TEXT NOT NULL UNIQUE, "
        "project_id TEXT NOT NULL, page_id TEXT NOT NULL, "
        "target_page_reference TEXT NOT NULL, provider_reference TEXT NOT NULL, "
        "authorization_id TEXT NOT NULL, output_asset_id TEXT NOT NULL, "
        "canonical_result_identity TEXT NOT NULL, logical_output_id TEXT NOT NULL, "
        "asset_identity TEXT NOT NULL, asset_sha256 TEXT NOT NULL, "
        "expected_byte_length INTEGER NOT NULL, "
        "media_type TEXT NOT NULL CHECK(media_type = 'image/png'), "
        "evidence_identity TEXT NOT NULL, evidence_persistence_digest TEXT NOT NULL, "
        "evidence_binding_fingerprint TEXT NOT NULL, "
        "pre_commit_revision INTEGER NOT NULL, pre_commit_fingerprint TEXT NOT NULL, "
        "post_commit_revision INTEGER NOT NULL, post_commit_fingerprint TEXT NOT NULL, "
        "source_state TEXT NOT NULL CHECK(source_state = 'PromptBuilt'), "
        "target_state TEXT NOT NULL CHECK(target_state = 'Generated'), "
        "application_binding_json TEXT NOT NULL, record_json TEXT NOT NULL, "
        "record_digest TEXT NOT NULL, "
        "UNIQUE(project_id, page_id, post_commit_revision, post_commit_fingerprint))"
    )
    connection.execute(f"INSERT INTO {_META_TABLE} (schema_id, schema_version) VALUES (?, ?)", (_SCHEMA_ID, _SCHEMA_VERSION))
    connection.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")


def _validate_schema(connection: sqlite3.Connection) -> None:
    if _user_version(connection) != _SCHEMA_VERSION:
        raise _corrupt()
    if _user_objects(connection) != tuple(sorted(((_ATTESTATION_TABLE, "table"), (_META_TABLE, "table")))):
        raise _corrupt()
    meta = connection.execute(f"SELECT schema_id, schema_version FROM {_META_TABLE}").fetchall()
    if meta != [(_SCHEMA_ID, _SCHEMA_VERSION)]:
        raise _corrupt()
    _validate_table(
        connection,
        _META_TABLE,
        (("schema_id", "TEXT", 0, None, 1), ("schema_version", "INTEGER", 1, None, 0)),
        ((f"sqlite_autoindex_{_META_TABLE}_1", 1, "pk", 0, "schema_id"),),
    )
    _validate_table(
        connection,
        _ATTESTATION_TABLE,
        (
            ("attestation_identity", "TEXT", 0, None, 1),
            ("delivery_identity", "TEXT", 1, None, 0),
            ("attempt_id", "TEXT", 1, None, 0),
            ("application_binding_digest", "TEXT", 1, None, 0),
            ("project_id", "TEXT", 1, None, 0),
            ("page_id", "TEXT", 1, None, 0),
            ("target_page_reference", "TEXT", 1, None, 0),
            ("provider_reference", "TEXT", 1, None, 0),
            ("authorization_id", "TEXT", 1, None, 0),
            ("output_asset_id", "TEXT", 1, None, 0),
            ("canonical_result_identity", "TEXT", 1, None, 0),
            ("logical_output_id", "TEXT", 1, None, 0),
            ("asset_identity", "TEXT", 1, None, 0),
            ("asset_sha256", "TEXT", 1, None, 0),
            ("expected_byte_length", "INTEGER", 1, None, 0),
            ("media_type", "TEXT", 1, None, 0),
            ("evidence_identity", "TEXT", 1, None, 0),
            ("evidence_persistence_digest", "TEXT", 1, None, 0),
            ("evidence_binding_fingerprint", "TEXT", 1, None, 0),
            ("pre_commit_revision", "INTEGER", 1, None, 0),
            ("pre_commit_fingerprint", "TEXT", 1, None, 0),
            ("post_commit_revision", "INTEGER", 1, None, 0),
            ("post_commit_fingerprint", "TEXT", 1, None, 0),
            ("source_state", "TEXT", 1, None, 0),
            ("target_state", "TEXT", 1, None, 0),
            ("application_binding_json", "TEXT", 1, None, 0),
            ("record_json", "TEXT", 1, None, 0),
            ("record_digest", "TEXT", 1, None, 0),
        ),
        (
            (f"sqlite_autoindex_{_ATTESTATION_TABLE}_1", 1, "pk", 0, "attestation_identity"),
            (f"sqlite_autoindex_{_ATTESTATION_TABLE}_2", 1, "u", 0, "delivery_identity"),
            (f"sqlite_autoindex_{_ATTESTATION_TABLE}_3", 1, "u", 0, "attempt_id"),
            (f"sqlite_autoindex_{_ATTESTATION_TABLE}_4", 1, "u", 0, "application_binding_digest"),
            (f"sqlite_autoindex_{_ATTESTATION_TABLE}_5", 1, "u", 0, "project_id,page_id,post_commit_revision,post_commit_fingerprint"),
        ),
    )


def _validate_table(
    connection: sqlite3.Connection,
    table: str,
    expected_columns: tuple[tuple[str, str, int, object | None, int], ...],
    expected_indexes: tuple[tuple[str, int, str, int, str], ...],
) -> None:
    columns = tuple(
        (row[1], row[2], row[3], row[4], row[5])
        for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
    )
    if columns != expected_columns:
        raise _corrupt()
    indexes = []
    for row in connection.execute(f"PRAGMA index_list({table})").fetchall():
        name, unique, origin, partial = row[1], row[2], row[3], row[4]
        columns_for_index = ",".join(item[2] for item in connection.execute(f"PRAGMA index_info({name})").fetchall())
        indexes.append((name, unique, origin, partial, columns_for_index))
    if tuple(sorted(indexes)) != tuple(sorted(expected_indexes)):
        raise _corrupt()


def _user_objects(connection: sqlite3.Connection) -> tuple[tuple[str, str], ...]:
    return tuple(
        sorted(
            (str(name), str(kind))
            for name, kind in connection.execute(
                "SELECT name, type FROM sqlite_master WHERE type IN ('table', 'index', 'trigger', 'view') "
                "AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        )
    )


def _user_version(connection: sqlite3.Connection) -> int:
    row = connection.execute("PRAGMA user_version").fetchone()
    if row is None or type(row[0]) is not int:
        raise _corrupt()
    return row[0]


def _rollback(connection: sqlite3.Connection | None) -> None:
    if connection is not None:
        try:
            connection.rollback()
        except sqlite3.Error:
            pass


def _close(connection: sqlite3.Connection | None) -> None:
    if connection is not None:
        connection.close()
