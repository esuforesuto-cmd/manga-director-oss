"""Private append-only owner for durable local human visual review evidence."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import stat
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from manga_director.production.next_generation_human_visual_qa_approval_readiness import (
    HumanVisualCriterion,
    HumanVisualOutcome,
    OverallHumanJudgment,
)

_SCHEMA_ID = "manga-director.human-visual-review-evidence"
_SCHEMA_VERSION = 1
_DIRECTORY_NAME = "review-evidence"
_DATABASE_NAME = "human-visual-review-evidence.sqlite3"
_META_TABLE = "human_visual_review_evidence_schema_meta"
_RECORD_TABLE = "human_visual_review_evidence_records"
_MAX_PAYLOAD_BYTES = 65_536
_MAX_HISTORY_RECORDS = 32
_READ_PROGRESS_GRANULARITY = 100
_MAX_READ_PROGRESS_CALLBACKS = 10_000
_SQLITE_HEADER = b"SQLite format 3\x00"
_SQLITE_ROLLBACK_JOURNAL_VERSIONS = b"\x01\x01"
_WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:[\\\\/]")
_SECRET_LIKE_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "endpoint",
    "password",
    "secret",
    "token",
)
_REQUIRED_CRITERIA = {
    "character_identity",
    "face",
    "costume",
    "props",
    "pose",
    "gaze",
    "emotion",
    "screen_direction",
    "location",
    "time",
    "composition",
    "panel_intent",
    "visible_corruption",
    "truncation",
    "watermark",
    "unsafe_content",
    "unintended_text",
    "continuity_comparison",
}


class DurableHumanVisualReviewEvidenceUnavailable(ValueError):
    """Redacted fail-closed persistence boundary."""


class _EvidenceModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    def __repr__(self) -> str:
        return f"{type(self).__name__}(<redacted>)"

    def __str__(self) -> str:
        return f"{type(self).__name__}(<redacted>)"


class _EvidenceChecklistItem(_EvidenceModel):
    criterion: HumanVisualCriterion
    outcome: HumanVisualOutcome
    rationale: str = Field(min_length=1, max_length=500)

    @field_validator("rationale")
    @classmethod
    def _validate_rationale(cls, value: str) -> str:
        return _safe_text(value)

class _EvidenceFinding(_EvidenceModel):
    code: str
    status: Literal["needs_review", "blocked"]
    message: str
    criterion: str = ""


class _HumanVisualReviewEvidencePayload(_EvidenceModel):
    schema_id: Literal["manga-director.human-visual-review-evidence"] = (
        "manga-director.human-visual-review-evidence"
    )
    schema_version: Literal[1] = 1
    review_id: str
    project_id: str
    page_id: str
    page_number: int = Field(ge=1, le=2_147_483_647)
    page_state: Literal["Generated", "QualityChecked"]
    attempt_id: str
    output_asset_id: str
    provenance_reference: str
    qa_report_reference: str
    reviewer_id: str
    reviewed_at: datetime
    checklist: tuple[_EvidenceChecklistItem, ...] = Field(min_length=18, max_length=18)
    overall_judgment: OverallHumanJudgment
    rationale: str = Field(min_length=1, max_length=500)
    status: Literal["ready", "needs_review", "blocked"]
    ready: bool
    findings: tuple[_EvidenceFinding, ...]
    missing_prerequisites: tuple[str, ...]
    analysis_only: Literal[True] = True

    @field_validator(
        "review_id",
        "project_id",
        "page_id",
        "attempt_id",
        "output_asset_id",
        "provenance_reference",
        "qa_report_reference",
        "reviewer_id",
    )
    @classmethod
    def _validate_reference(cls, value: str) -> str:
        return _logical_reference(value)

    @field_validator("reviewed_at")
    @classmethod
    def _validate_reviewed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("reviewed_at must be timezone-aware")
        return value

    @field_validator("rationale")
    @classmethod
    def _validate_rationale(cls, value: str) -> str:
        return _safe_text(value)

    @model_validator(mode="after")
    def _validate_canonical_report(self) -> _HumanVisualReviewEvidencePayload:
        criteria = tuple(item.criterion for item in self.checklist)
        if set(criteria) != _REQUIRED_CRITERIA or len(set(criteria)) != len(criteria):
            raise ValueError("checklist must contain each criterion exactly once")
        if self.checklist != tuple(
            sorted(
                self.checklist,
                key=lambda item: (item.criterion, item.outcome, item.rationale),
            )
        ):
            raise ValueError("checklist must use canonical order")
        if self.ready != (self.status == "ready"):
            raise ValueError("ready must match status")
        if self.page_state == "Generated" and self.ready:
            raise ValueError("Generated evidence cannot be ready")
        if self.missing_prerequisites != tuple(sorted(set(self.missing_prerequisites))):
            raise ValueError("missing prerequisites must use canonical order")
        return self


@dataclass(frozen=True, slots=True)
class _EvidenceWriteResult:
    outcome: Literal["recorded", "confirmed"]


class LocalDurableHumanVisualReviewEvidenceOwner:
    """Own one isolated versioned SQLite sidecar under the trusted local root."""

    def __init__(self, normal_execution_root: Path) -> None:
        self._normal_execution_root = normal_execution_root
        self._directory = normal_execution_root / _DIRECTORY_NAME
        self._database = self._directory / _DATABASE_NAME

    def persist(
        self, payload: _HumanVisualReviewEvidencePayload
    ) -> _EvidenceWriteResult:
        if type(payload) is not _HumanVisualReviewEvidencePayload:
            raise DurableHumanVisualReviewEvidenceUnavailable(
                "human visual review evidence persistence is unavailable"
            )
        payload_json = _canonical_payload(payload)
        payload_digest = _sha256_text(payload_json)
        binding_fingerprint = _binding_fingerprint(payload)
        expected = _row_values(payload, binding_fingerprint, payload_json, payload_digest)
        connection: sqlite3.Connection | None = None
        began = False
        created_directory = False
        completed = False
        try:
            connection, created_directory = self._open_for_persist()
            connection.execute("BEGIN IMMEDIATE")
            began = True
            if created_directory:
                if _user_objects(connection) or _user_version(connection) != 0:
                    raise DurableHumanVisualReviewEvidenceUnavailable(
                        "human visual review evidence persistence is unavailable"
                    )
                _create_schema(connection)
            _validate_schema(connection)
            _validate_all_rows(connection)
            rows = connection.execute(
                f"SELECT {_record_columns()} FROM {_RECORD_TABLE} WHERE review_id = ?",
                (payload.review_id,),
            ).fetchall()
            if rows:
                if len(rows) != 1 or tuple(rows[0]) != expected:
                    raise DurableHumanVisualReviewEvidenceUnavailable(
                        "human visual review evidence persistence is unavailable"
                    )
                connection.rollback()
                began = False
                completed = True
                return _EvidenceWriteResult("confirmed")
            connection.execute(
                f"INSERT INTO {_RECORD_TABLE} ({_record_columns()}) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                expected,
            )
            inserted = connection.execute(
                f"SELECT {_record_columns()} FROM {_RECORD_TABLE} WHERE review_id = ?",
                (payload.review_id,),
            ).fetchall()
            if len(inserted) != 1 or tuple(inserted[0]) != expected:
                raise DurableHumanVisualReviewEvidenceUnavailable(
                    "human visual review evidence persistence is unavailable"
                )
            _commit(connection)
            began = False
            completed = True
            return _EvidenceWriteResult("recorded")
        except DurableHumanVisualReviewEvidenceUnavailable:
            _rollback(connection, began)
            raise
        except (OSError, sqlite3.Error, TypeError, ValueError) as error:
            _rollback(connection, began)
            raise DurableHumanVisualReviewEvidenceUnavailable(
                "human visual review evidence persistence is unavailable"
            ) from error
        finally:
            if connection is not None:
                connection.close()
            if created_directory and not completed:
                _remove_failed_initialization(self._directory, self._database)

    def _open_for_persist(self) -> tuple[sqlite3.Connection, bool]:
        root = self._normal_execution_root
        created_directory = False
        connection: sqlite3.Connection | None = None
        try:
            if not _safe_directory(root):
                raise DurableHumanVisualReviewEvidenceUnavailable(
                    "human visual review evidence persistence is unavailable"
                )
            if self._database.exists():
                _require_existing_store(root, self._directory, self._database)
                _require_rollback_journal_database(self._database)
            else:
                if self._directory.exists():
                    raise DurableHumanVisualReviewEvidenceUnavailable(
                        "human visual review evidence persistence is unavailable"
                    )
                self._directory.mkdir()
                created_directory = True
                if not _safe_directory(self._directory) or self._directory.parent != root:
                    raise DurableHumanVisualReviewEvidenceUnavailable(
                        "human visual review evidence persistence is unavailable"
                    )
            connection = sqlite3.connect(
                str(self._database), timeout=5.0, isolation_level=None
            )
            if created_directory:
                _configure_new_connection(connection)
            else:
                _configure_existing_connection(connection)
            return connection, created_directory
        except DurableHumanVisualReviewEvidenceUnavailable:
            if connection is not None:
                connection.close()
            if created_directory:
                _remove_failed_initialization(self._directory, self._database)
            raise
        except (OSError, sqlite3.Error, TypeError, ValueError) as error:
            if connection is not None:
                connection.close()
            if created_directory:
                _remove_failed_initialization(self._directory, self._database)
            raise DurableHumanVisualReviewEvidenceUnavailable(
                "human visual review evidence persistence is unavailable"
            ) from error

    def _read_exact(
        self, review_id: str
    ) -> _HumanVisualReviewEvidencePayload | None:
        """Read one existing exact record without creating or repairing state."""

        try:
            _logical_reference(review_id)
            _require_existing_store(self._normal_execution_root, self._directory, self._database)
            _require_rollback_journal_database(self._database)
            connection = sqlite3.connect(
                f"{self._database.as_uri()}?mode=ro",
                uri=True,
                timeout=0.0,
                isolation_level=None,
            )
        except (OSError, sqlite3.Error, TypeError, ValueError) as error:
            raise DurableHumanVisualReviewEvidenceUnavailable(
                "human visual review evidence persistence is unavailable"
            ) from error
        began = False
        try:
            connection.execute("PRAGMA query_only=ON")
            if connection.execute("PRAGMA query_only").fetchall() != [(1,)]:
                raise DurableHumanVisualReviewEvidenceUnavailable(
                    "human visual review evidence persistence is unavailable"
                )
            _validate_journal_mode(connection)
            connection.execute("BEGIN")
            began = True
            _validate_schema(connection)
            _validate_all_rows(connection)
            rows = connection.execute(
                f"SELECT {_record_columns()} FROM {_RECORD_TABLE} WHERE review_id = ?",
                (review_id,),
            ).fetchall()
            if not rows:
                connection.rollback()
                began = False
                return None
            payload = _payload_from_row(rows)
            connection.rollback()
            began = False
            return payload
        except DurableHumanVisualReviewEvidenceUnavailable:
            _rollback(connection, began)
            raise
        except (OSError, sqlite3.Error, TypeError, ValueError) as error:
            _rollback(connection, began)
            raise DurableHumanVisualReviewEvidenceUnavailable(
                "human visual review evidence persistence is unavailable"
            ) from error
        finally:
            connection.close()

    def read_page_history(
        self,
        project_id: str,
        page_id: str,
        page_number: int,
    ) -> tuple[_HumanVisualReviewEvidencePayload, ...]:
        """Read one complete bounded Page history without creating state."""

        connection: sqlite3.Connection | None = None
        began = False
        try:
            _logical_reference(project_id)
            _logical_reference(page_id)
            if type(page_number) is not int or not 1 <= page_number <= 2_147_483_647:
                raise ValueError("page_number is invalid")
            if (
                self._directory.parent != self._normal_execution_root
                or self._database.parent != self._directory
                or not _safe_directory(self._normal_execution_root)
            ):
                raise DurableHumanVisualReviewEvidenceUnavailable(
                    "human visual review evidence persistence is unavailable"
                )
            directory_present = self._directory.exists() or _is_link_or_reparse(
                self._directory
            )
            database_present = self._database.exists() or _is_link_or_reparse(
                self._database
            )
            if not directory_present and not database_present:
                return ()
            _require_existing_store(
                self._normal_execution_root,
                self._directory,
                self._database,
            )
            _require_rollback_journal_database(self._database)
            connection = sqlite3.connect(
                f"{self._database.as_uri()}?mode=ro",
                uri=True,
                timeout=0.0,
                isolation_level=None,
            )
            remaining_callbacks = _MAX_READ_PROGRESS_CALLBACKS

            def bounded_read_work() -> int:
                nonlocal remaining_callbacks
                remaining_callbacks -= 1
                return int(remaining_callbacks < 0)

            connection.set_progress_handler(
                bounded_read_work,
                _READ_PROGRESS_GRANULARITY,
            )
            connection.execute("PRAGMA query_only=ON")
            if connection.execute("PRAGMA query_only").fetchall() != [(1,)]:
                raise DurableHumanVisualReviewEvidenceUnavailable(
                    "human visual review evidence persistence is unavailable"
                )
            _validate_journal_mode(connection)
            connection.execute("BEGIN")
            began = True
            _validate_schema(connection)
            _validate_all_rows(
                connection,
                expected_page=(project_id, page_id, page_number),
            )
            rows = connection.execute(
                f"SELECT {_record_columns()} FROM {_RECORD_TABLE} "
                "WHERE project_id = ? AND page_id = ? AND page_number = ? "
                "ORDER BY review_id LIMIT ?",
                (project_id, page_id, page_number, _MAX_HISTORY_RECORDS + 1),
            ).fetchall()
            if len(rows) > _MAX_HISTORY_RECORDS:
                raise DurableHumanVisualReviewEvidenceUnavailable(
                    "human visual review evidence persistence is unavailable"
                )
            payloads = tuple(_payload_from_row([row]) for row in rows)
            if any(
                payload.project_id != project_id
                or payload.page_id != page_id
                or payload.page_number != page_number
                for payload in payloads
            ):
                raise DurableHumanVisualReviewEvidenceUnavailable(
                    "human visual review evidence persistence is unavailable"
                )
            connection.rollback()
            began = False
            return payloads
        except DurableHumanVisualReviewEvidenceUnavailable:
            _rollback(connection, began)
            raise
        except (OSError, sqlite3.Error, TypeError, ValueError) as error:
            _rollback(connection, began)
            raise DurableHumanVisualReviewEvidenceUnavailable(
                "human visual review evidence persistence is unavailable"
            ) from error
        finally:
            if connection is not None:
                connection.set_progress_handler(None, 0)
                connection.close()

def _canonical_payload(payload: _HumanVisualReviewEvidencePayload) -> str:
    value = json.dumps(
        payload.model_dump(mode="json"),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    if len(value.encode("utf-8")) > _MAX_PAYLOAD_BYTES:
        raise DurableHumanVisualReviewEvidenceUnavailable(
            "human visual review evidence persistence is unavailable"
        )
    return value


def _binding_fingerprint(payload: _HumanVisualReviewEvidencePayload) -> str:
    return _sha256_text(
        json.dumps(
            {
                "attempt_id": payload.attempt_id,
                "output_asset_id": payload.output_asset_id,
                "page_id": payload.page_id,
                "page_number": payload.page_number,
                "project_id": payload.project_id,
                "provenance_reference": payload.provenance_reference,
                "qa_report_reference": payload.qa_report_reference,
                "review_id": payload.review_id,
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    )


def _row_values(
    payload: _HumanVisualReviewEvidencePayload,
    binding_fingerprint: str,
    payload_json: str,
    payload_digest: str,
) -> tuple[object, ...]:
    return (
        payload.review_id,
        payload.project_id,
        payload.page_id,
        payload.page_number,
        payload.attempt_id,
        payload.output_asset_id,
        binding_fingerprint,
        payload_json,
        payload_digest,
    )


def _payload_from_row(rows: object) -> _HumanVisualReviewEvidencePayload:
    if not isinstance(rows, list) or len(rows) != 1:
        raise DurableHumanVisualReviewEvidenceUnavailable(
            "human visual review evidence persistence is unavailable"
        )
    row = rows[0]
    if not isinstance(row, tuple) or len(row) != 9:
        raise DurableHumanVisualReviewEvidenceUnavailable(
            "human visual review evidence persistence is unavailable"
        )
    review_id, project_id, page_id, page_number, attempt_id, output_asset_id, binding, raw, digest = row
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > _MAX_PAYLOAD_BYTES:
        raise DurableHumanVisualReviewEvidenceUnavailable(
            "human visual review evidence persistence is unavailable"
        )
    try:
        payload = _HumanVisualReviewEvidencePayload.model_validate_json(raw)
    except ValueError as error:
        raise DurableHumanVisualReviewEvidenceUnavailable(
            "human visual review evidence persistence is unavailable"
        ) from error
    if (
        _canonical_payload(payload) != raw
        or _sha256_text(raw) != digest
        or _binding_fingerprint(payload) != binding
        or _row_values(payload, cast(str, binding), raw, cast(str, digest)) != tuple(row)
        or review_id != payload.review_id
        or project_id != payload.project_id
        or page_id != payload.page_id
        or page_number != payload.page_number
        or attempt_id != payload.attempt_id
        or output_asset_id != payload.output_asset_id
    ):
        raise DurableHumanVisualReviewEvidenceUnavailable(
            "human visual review evidence persistence is unavailable"
        )
    return payload


def _validate_all_rows(
    connection: sqlite3.Connection,
    *,
    expected_page: tuple[str, str, int] | None = None,
) -> None:
    for row in connection.execute(
        f"SELECT {_record_columns()} FROM {_RECORD_TABLE} ORDER BY review_id"
    ):
        payload = _payload_from_row([row])
        if expected_page is None:
            continue
        project_id, page_id, page_number = expected_page
        if payload.project_id == project_id and (
            (payload.page_id == page_id) != (payload.page_number == page_number)
        ):
            raise DurableHumanVisualReviewEvidenceUnavailable(
                "human visual review evidence persistence is unavailable"
            )


def _record_columns() -> str:
    return (
        "review_id, project_id, page_id, page_number, attempt_id, output_asset_id, "
        "binding_fingerprint, payload_json, payload_digest"
    )


def _configure_new_connection(connection: sqlite3.Connection) -> None:
    mode = connection.execute("PRAGMA journal_mode=DELETE").fetchall()
    if mode != [("delete",)]:
        raise DurableHumanVisualReviewEvidenceUnavailable(
            "human visual review evidence persistence is unavailable"
        )
    connection.execute("PRAGMA synchronous=FULL")


def _configure_existing_connection(connection: sqlite3.Connection) -> None:
    _validate_journal_mode(connection)
    connection.execute("PRAGMA synchronous=FULL")


def _validate_journal_mode(connection: sqlite3.Connection) -> None:
    if connection.execute("PRAGMA journal_mode").fetchall() != [("delete",)]:
        raise DurableHumanVisualReviewEvidenceUnavailable(
            "human visual review evidence persistence is unavailable"
        )


def _create_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        f"CREATE TABLE {_META_TABLE} ("
        "schema_id TEXT PRIMARY KEY, schema_version INTEGER NOT NULL)"
    )
    connection.execute(
        f"CREATE TABLE {_RECORD_TABLE} ("
        "review_id TEXT PRIMARY KEY, "
        "project_id TEXT NOT NULL, "
        "page_id TEXT NOT NULL, "
        "page_number INTEGER NOT NULL, "
        "attempt_id TEXT NOT NULL, "
        "output_asset_id TEXT NOT NULL, "
        "binding_fingerprint TEXT NOT NULL, "
        "payload_json TEXT NOT NULL, "
        "payload_digest TEXT NOT NULL)"
    )
    connection.execute(
        f"INSERT INTO {_META_TABLE} (schema_id, schema_version) VALUES (?, ?)",
        (_SCHEMA_ID, _SCHEMA_VERSION),
    )
    connection.execute(f"PRAGMA user_version={_SCHEMA_VERSION}")


def _validate_schema(connection: sqlite3.Connection) -> None:
    if _user_version(connection) != _SCHEMA_VERSION:
        raise DurableHumanVisualReviewEvidenceUnavailable(
            "human visual review evidence persistence is unavailable"
        )
    if _user_objects(connection) != (
        ("table", _RECORD_TABLE),
        ("table", _META_TABLE),
    ):
        raise DurableHumanVisualReviewEvidenceUnavailable(
            "human visual review evidence persistence is unavailable"
        )
    _validate_table(
        connection,
        _META_TABLE,
        (
            (0, "schema_id", "TEXT", 0, None, 1),
            (1, "schema_version", "INTEGER", 1, None, 0),
        ),
        ((f"sqlite_autoindex_{_META_TABLE}_1", 1, "pk", 0, "schema_id"),),
    )
    _validate_table(
        connection,
        _RECORD_TABLE,
        (
            (0, "review_id", "TEXT", 0, None, 1),
            (1, "project_id", "TEXT", 1, None, 0),
            (2, "page_id", "TEXT", 1, None, 0),
            (3, "page_number", "INTEGER", 1, None, 0),
            (4, "attempt_id", "TEXT", 1, None, 0),
            (5, "output_asset_id", "TEXT", 1, None, 0),
            (6, "binding_fingerprint", "TEXT", 1, None, 0),
            (7, "payload_json", "TEXT", 1, None, 0),
            (8, "payload_digest", "TEXT", 1, None, 0),
        ),
        ((f"sqlite_autoindex_{_RECORD_TABLE}_1", 1, "pk", 0, "review_id"),),
    )
    meta = connection.execute(
        f"SELECT schema_id, schema_version FROM {_META_TABLE} ORDER BY schema_id"
    ).fetchall()
    if meta != [(_SCHEMA_ID, _SCHEMA_VERSION)]:
        raise DurableHumanVisualReviewEvidenceUnavailable(
            "human visual review evidence persistence is unavailable"
        )


def _validate_table(
    connection: sqlite3.Connection,
    table: str,
    columns: tuple[tuple[object, ...], ...],
    indexes: tuple[tuple[str, int, str, int, str], ...],
) -> None:
    if tuple(connection.execute(f"PRAGMA table_info({table})").fetchall()) != columns:
        raise DurableHumanVisualReviewEvidenceUnavailable(
            "human visual review evidence persistence is unavailable"
        )
    actual = tuple(
        sorted(
            (
                str(row[1]),
                int(row[2]),
                str(row[3]),
                int(row[4]),
                _index_column(connection, str(row[1])),
            )
            for row in connection.execute(f"PRAGMA index_list({table})").fetchall()
            if len(row) == 5
        )
    )
    if actual != indexes:
        raise DurableHumanVisualReviewEvidenceUnavailable(
            "human visual review evidence persistence is unavailable"
        )


def _index_column(connection: sqlite3.Connection, name: str) -> str:
    rows = connection.execute(f"PRAGMA index_info({name})").fetchall()
    if len(rows) != 1 or rows[0][0] != 0 or rows[0][1] < 0 or rows[0][2] is None:
        raise DurableHumanVisualReviewEvidenceUnavailable(
            "human visual review evidence persistence is unavailable"
        )
    return str(rows[0][2])


def _user_objects(connection: sqlite3.Connection) -> tuple[tuple[str, str], ...]:
    return tuple(
        (str(row[0]), str(row[1]))
        for row in connection.execute(
            "SELECT type, name FROM sqlite_master "
            "WHERE name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        if len(row) == 2
    )


def _user_version(connection: sqlite3.Connection) -> int:
    row = connection.execute("PRAGMA user_version").fetchone()
    if row is None or len(row) != 1 or type(row[0]) is not int:
        raise DurableHumanVisualReviewEvidenceUnavailable(
            "human visual review evidence persistence is unavailable"
        )
    return row[0]


def _require_existing_store(root: Path, directory: Path, database: Path) -> None:
    if (
        directory.parent != root
        or database.parent != directory
        or not _safe_directory(root)
        or not _safe_directory(directory)
        or not _regular_file(database)
    ):
        raise DurableHumanVisualReviewEvidenceUnavailable(
            "human visual review evidence persistence is unavailable"
        )


def _require_rollback_journal_database(path: Path) -> None:
    """Reject WAL before SQLite can checkpoint or create support files."""

    try:
        with path.open("rb") as stream:
            header = stream.read(20)
    except OSError as error:
        raise DurableHumanVisualReviewEvidenceUnavailable(
            "human visual review evidence persistence is unavailable"
        ) from error
    if (
        header[: len(_SQLITE_HEADER)] != _SQLITE_HEADER
        or header[18:20] != _SQLITE_ROLLBACK_JOURNAL_VERSIONS
    ):
        raise DurableHumanVisualReviewEvidenceUnavailable(
            "human visual review evidence persistence is unavailable"
        )


def _safe_directory(path: Path) -> bool:
    if not path.is_absolute():
        return False
    try:
        return path.is_dir() and not any(
            _is_link_or_reparse(candidate) for candidate in (path, *path.parents)
        )
    except OSError:
        return False


def _regular_file(path: Path) -> bool:
    try:
        value = path.lstat()
        return stat.S_ISREG(value.st_mode) and not _is_link_or_reparse(path)
    except OSError:
        return False


def _is_link_or_reparse(path: Path) -> bool:
    try:
        value = path.lstat()
    except OSError:
        return False
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISLNK(value.st_mode) or bool(
        getattr(value, "st_file_attributes", 0) & reparse
    )


def _remove_failed_initialization(directory: Path, database: Path) -> None:
    try:
        if _regular_file(database):
            database.unlink()
        journal = database.with_name(f"{database.name}-journal")
        if _regular_file(journal):
            journal.unlink()
        directory.rmdir()
    except OSError:
        pass


def _rollback(connection: sqlite3.Connection | None, began: bool) -> None:
    if connection is None or not began:
        return
    try:
        connection.rollback()
    except sqlite3.Error:
        pass


def _commit(connection: sqlite3.Connection) -> None:
    connection.commit()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _logical_reference(value: str) -> str:
    if (
        not value
        or value != value.strip()
        or any(character.isspace() for character in value)
        or value.startswith(("/", "\\"))
        or "://" in value
        or _WINDOWS_ABSOLUTE_PATH.match(value)
        or "@" in value
        or len(value) > 200
        or any(part in value.lower() for part in _SECRET_LIKE_PARTS)
    ):
        raise ValueError("evidence reference is invalid")
    return value


def _safe_text(value: str) -> str:
    if (
        not value
        or value != value.strip()
        or any(unicodedata.category(character) == "Cc" for character in value)
        or "/" in value
        or "\\" in value
        or "://" in value
        or _WINDOWS_ABSOLUTE_PATH.search(value)
        or "@" in value
        or any(part in value.lower() for part in _SECRET_LIKE_PARTS)
    ):
        raise ValueError("evidence text is invalid")
    return value


__all__ = ()
