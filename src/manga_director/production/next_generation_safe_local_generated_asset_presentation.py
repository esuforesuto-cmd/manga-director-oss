"""Private read-only proof chain for one Page-bound generated PNG."""

from __future__ import annotations

import sqlite3
import stat
from pathlib import Path
from typing import cast

from manga_director.production.future_real_delivery_i01 import StrictPngStructuralValidatorV1
from manga_director.production.next_generation_generation_evidence import (
    GenerationEvidenceEnvelopeDTO,
)
from manga_director.production.next_generation_generation_evidence_persistence import (
    _TABLE_NAME as _EVIDENCE_TABLE,
)
from manga_director.production.next_generation_generation_evidence_persistence import (
    _validated_evidence,
    _verified_row,
)
from manga_director.production.next_generation_local_durable_asset_owner import (
    LocalDurableAssetOwner,
    _AssetPresentationBytesLease,
    _require_rollback_journal_database,
)
from manga_director.production.next_generation_workflow_application_ledger import (
    _TABLE_NAME as _LEDGER_TABLE,
)
from manga_director.production.next_generation_workflow_application_ledger import (
    WorkflowApplicationLedgerBindingDTO,
    _open_r21_readonly_connection,
    _record_from_row,
    _select_columns,
    _validate_r21_schema,
)

_EVIDENCE_DATABASE = "generation-evidence.sqlite3"
_LEDGER_DATABASE = "workflow-application-ledger.sqlite3"
_MEDIA_TYPE = "image/png"
_EVIDENCE_DDL = (
    "CREATE TABLE generation_evidence ("
    "attempt_id TEXT PRIMARY KEY, "
    "payload_json TEXT NOT NULL, "
    "payload_digest TEXT NOT NULL, "
    "provider_reference TEXT NOT NULL, "
    "binding_fingerprint TEXT NOT NULL, "
    "evidence_status TEXT NOT NULL"
    ")"
)
_EVIDENCE_COLUMNS = (
    ("attempt_id", "TEXT", 1),
    ("payload_json", "TEXT", 0),
    ("payload_digest", "TEXT", 0),
    ("provider_reference", "TEXT", 0),
    ("binding_fingerprint", "TEXT", 0),
    ("evidence_status", "TEXT", 0),
)


class SafeLocalGeneratedAssetPresentationError(ValueError):
    """Redacted fail-closed presentation boundary."""


class SafeLocalGeneratedAssetPresenter:
    """Resolve immutable local authorities and return one fully verified PNG."""

    def __init__(self, *, ledger_root: Path, evidence_root: Path, asset_root: Path) -> None:
        self._ledger_database = ledger_root / _LEDGER_DATABASE
        self._evidence_database = evidence_root / _EVIDENCE_DATABASE
        self._asset_root = asset_root

    def present(
        self, project_id: str, page_id: str, output_asset_id: str
    ) -> _AssetPresentationBytesLease:
        try:
            binding = self._read_applied_binding(project_id, page_id, output_asset_id)
            evidence, provider_reference, digest = self._read_generation_evidence(
                binding.attempt_id
            )
            if (
                binding.provider_reference != provider_reference
                or evidence.provenance_reference == ""
                or evidence.output.output_asset_id != binding.output_asset_id
                or evidence.output.media_type != _MEDIA_TYPE
            ):
                raise SafeLocalGeneratedAssetPresentationError(
                    "generated asset presentation is unavailable"
                )
            owner = LocalDurableAssetOwner._open_existing_for_presentation(self._asset_root)
            presentation = owner._read_verified_presentation_bytes(
                attempt_id=binding.attempt_id,
                provider_reference=binding.provider_reference,
                output_asset_id=binding.output_asset_id,
                expected_sha256=digest,
                expected_media_type=_MEDIA_TYPE,
            )
            try:
                StrictPngStructuralValidatorV1().validate(presentation.image_bytes)
            except Exception:
                presentation.release()
                raise
            return presentation
        except SafeLocalGeneratedAssetPresentationError:
            raise
        except Exception as error:
            raise SafeLocalGeneratedAssetPresentationError(
                "generated asset presentation is unavailable"
            ) from error

    def _read_applied_binding(
        self, project_id: str, page_id: str, output_asset_id: str
    ) -> WorkflowApplicationLedgerBindingDTO:
        if not all(_logical_reference(value) for value in (project_id, page_id, output_asset_id)):
            raise SafeLocalGeneratedAssetPresentationError(
                "generated asset presentation is unavailable"
            )
        database = _existing_database(self._ledger_database)
        connection: sqlite3.Connection | None = None
        began = False
        try:
            _require_rollback_journal_database(database)
            connection = _open_r21_readonly_connection(database)
            connection.execute("PRAGMA query_only = ON")
            if connection.execute("PRAGMA query_only").fetchall() != [(1,)]:
                raise SafeLocalGeneratedAssetPresentationError(
                    "generated asset presentation is unavailable"
                )
            connection.execute("BEGIN")
            began = True
            _validate_r21_schema(connection)
            rows = connection.execute(
                f"SELECT {_select_columns(connection)} FROM {_LEDGER_TABLE} "
                "WHERE project_id = ? AND page_id = ? LIMIT 2",
                (project_id, page_id),
            ).fetchall()
            records = tuple(_record_from_row(row) for row in rows)
            if len(records) != 1 or records[0] is None or records[0].lifecycle != "applied":
                raise SafeLocalGeneratedAssetPresentationError(
                    "generated asset presentation is unavailable"
                )
            binding = records[0].binding
            if (
                binding.project_id != project_id
                or binding.page_id != page_id
                or binding.output_asset_id != output_asset_id
                or binding.source_state != "PromptBuilt"
                or binding.target_state != "Generated"
            ):
                raise SafeLocalGeneratedAssetPresentationError(
                    "generated asset presentation is unavailable"
                )
            connection.commit()
            began = False
            return binding
        finally:
            if connection is not None:
                if began:
                    try:
                        connection.rollback()
                    except sqlite3.Error:
                        pass
                connection.close()

    def _read_generation_evidence(
        self, attempt_id: str
    ) -> tuple[GenerationEvidenceEnvelopeDTO, str, str]:
        database = _existing_database(self._evidence_database)
        connection: sqlite3.Connection | None = None
        began = False
        try:
            connection = _open_readonly_database(database)
            connection.execute("BEGIN")
            began = True
            _validate_evidence_schema(connection)
            rows = connection.execute(
                "SELECT payload_json, payload_digest, provider_reference, "
                "binding_fingerprint, evidence_status "
                f"FROM {_EVIDENCE_TABLE} WHERE attempt_id = ?",
                (attempt_id,),
            ).fetchall()
            if len(rows) != 1:
                raise SafeLocalGeneratedAssetPresentationError(
                    "generated asset presentation is unavailable"
                )
            verified = _verified_row(attempt_id, rows[0])
            if verified is None or verified[4] != "ready":
                raise SafeLocalGeneratedAssetPresentationError(
                    "generated asset presentation is unavailable"
                )
            payload, _payload_digest, provider_reference, _fingerprint, _status = verified
            evidence = _validated_evidence(payload)
            if evidence is None:
                raise SafeLocalGeneratedAssetPresentationError(
                    "generated asset presentation is unavailable"
                )
            content_hash = getattr(evidence.output.output_content_hash, "value", None)
            if (
                evidence.attempt_id != attempt_id
                or getattr(evidence.output.output_content_hash, "availability", None) != "known"
                or not _sha256(content_hash)
            ):
                raise SafeLocalGeneratedAssetPresentationError(
                    "generated asset presentation is unavailable"
                )
            connection.commit()
            began = False
            return evidence, provider_reference, cast(str, content_hash)
        finally:
            if connection is not None:
                if began:
                    try:
                        connection.rollback()
                    except sqlite3.Error:
                        pass
                connection.close()


def _existing_database(path: Path) -> Path:
    if not path.is_absolute() or path.name == "" or _is_link_or_reparse(path):
        raise SafeLocalGeneratedAssetPresentationError(
            "generated asset presentation is unavailable"
        )
    try:
        if not path.is_file() or _is_link_or_reparse(path.parent):
            raise SafeLocalGeneratedAssetPresentationError(
                "generated asset presentation is unavailable"
            )
        return path.resolve(strict=True)
    except OSError as error:
        raise SafeLocalGeneratedAssetPresentationError(
            "generated asset presentation is unavailable"
        ) from error


def _open_readonly_database(path: Path) -> sqlite3.Connection:
    _require_rollback_journal_database(path)
    connection = sqlite3.connect(
        f"{path.as_uri()}?mode=ro", uri=True, timeout=0.0, isolation_level=None
    )
    try:
        connection.execute("PRAGMA query_only = ON")
        if connection.execute("PRAGMA query_only").fetchall() != [(1,)]:
            raise SafeLocalGeneratedAssetPresentationError(
                "generated asset presentation is unavailable"
            )
        return connection
    except Exception:
        connection.close()
        raise


def _validate_evidence_schema(connection: sqlite3.Connection) -> None:
    version = connection.execute("PRAGMA user_version").fetchall()
    journal_mode = connection.execute("PRAGMA journal_mode").fetchall()
    objects = connection.execute(
        "SELECT type, name FROM sqlite_master "
        "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
    ).fetchall()
    ddl = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
        (_EVIDENCE_TABLE,),
    ).fetchall()
    rows = connection.execute(f"PRAGMA table_info({_EVIDENCE_TABLE})").fetchall()
    columns = tuple((str(row[1]), str(row[2]).upper(), int(row[5])) for row in rows)
    indexes = connection.execute(f"PRAGMA index_list({_EVIDENCE_TABLE})").fetchall()
    primary_key_indexes = []
    for index in indexes:
        if len(index) != 5 or index[2] != 1 or index[3] != "pk":
            raise SafeLocalGeneratedAssetPresentationError(
                "generated asset presentation is unavailable"
            )
        index_columns = connection.execute(f"PRAGMA index_info({index[1]})").fetchall()
        primary_key_indexes.append(index_columns)
    if (
        version != [(1,)]
        or journal_mode != [("delete",)]
        or objects != [("table", _EVIDENCE_TABLE)]
        or len(ddl) != 1
        or not isinstance(ddl[0][0], str)
        or _without_ascii_whitespace(ddl[0][0])
        != _without_ascii_whitespace(_EVIDENCE_DDL)
        or columns != _EVIDENCE_COLUMNS
        or primary_key_indexes != [[(0, 0, "attempt_id")]]
    ):
        raise SafeLocalGeneratedAssetPresentationError(
            "generated asset presentation is unavailable"
        )


def _is_link_or_reparse(path: Path) -> bool:
    try:
        status = path.lstat()
    except OSError:
        return False
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISLNK(status.st_mode) or bool(
        getattr(status, "st_file_attributes", 0) & reparse
    )


def _logical_reference(value: object) -> bool:
    return bool(
        isinstance(value, str)
        and value
        and value == value.strip()
        and not any(character.isspace() for character in value)
        and not value.startswith(("/", "\\"))
        and "://" not in value
    )


def _sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def _without_ascii_whitespace(value: str) -> str:
    return "".join(character for character in value if character not in " \t\r\n\f\v")
