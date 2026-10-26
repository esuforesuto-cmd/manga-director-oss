"""Immutable, exact-binding evidence contracts for Panel outputs."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import ConfigDict, Field, field_validator, model_validator

from manga_director.production.director import DirectorModel
from manga_director.production.next_generation_page_generation_plan import (
    logical_reference,
    sha256_digest,
)
from manga_director.production.next_generation_panel_execution_attempt import (
    PanelAttemptRecord,
    PanelAttemptReservation,
    PanelAttemptState,
)

PanelAuthorityOutcome = Literal[
    "created", "updated", "confirmed", "missing", "conflict", "corrupt", "failed"
]

_AUTHORITY_DATABASE = "panel-generation-authority.sqlite3"
_AUTHORITY_SCHEMA_VERSION = 1
_NON_TERMINAL_STATES = (
    "RESERVED",
    "PROVIDER_STARTED",
    "PROVIDER_COMPLETED",
    "ASSET_REGISTERED",
    "EVIDENCE_COMMITTED",
    "RECOVERY_REQUIRED",
)


class _PanelEvidenceModel(DirectorModel):
    model_config = ConfigDict(
        frozen=True, extra="forbid", strict=True, validate_default=True
    )


class PanelAsset(_PanelEvidenceModel):
    """One accepted Provider output bound to one exact Panel attempt."""

    asset_id: str
    plan_id: str
    plan_fingerprint: str
    project_id: str
    page_id: str
    panel_id: str
    panel_order: int = Field(ge=1, le=16)
    request_id: str
    request_fingerprint: str
    attempt_id: str
    media_type: Literal["image/png"] = "image/png"
    width: int = Field(gt=0, le=4096)
    height: int = Field(gt=0, le=4096)
    content_sha256: str

    @field_validator(
        "asset_id",
        "plan_id",
        "project_id",
        "page_id",
        "panel_id",
        "request_id",
        "attempt_id",
        mode="before",
    )
    @classmethod
    def _references(cls, value: object) -> str:
        return logical_reference(value, "Panel asset reference")

    @field_validator("plan_fingerprint", "request_fingerprint", "content_sha256")
    @classmethod
    def _digests(cls, value: str) -> str:
        return sha256_digest(value)


class PanelGenerationEvidence(_PanelEvidenceModel):
    evidence_id: str
    plan_id: str
    plan_fingerprint: str
    project_id: str
    page_id: str
    panel_id: str
    panel_order: int = Field(ge=1, le=16)
    request_id: str
    request_fingerprint: str
    attempt_id: str
    input_reference: str
    input_sha256: str
    provider_reference: str
    provider_configuration_fingerprint: str
    provenance_reference: str
    output_asset_id: str | None = None
    output_sha256: str | None = None
    media_type: Literal["image/png"] | None = None
    width: int | None = Field(default=None, gt=0, le=4096)
    height: int | None = Field(default=None, gt=0, le=4096)
    outcome: Literal["accepted", "declared_failure", "recovery_required"]
    attempt_state: Literal["PANEL_ACCEPTED", "DECLARED_FAILURE", "RECOVERY_REQUIRED"]

    @field_validator(
        "evidence_id", "plan_id", "project_id", "page_id", "panel_id", "request_id", "attempt_id",
        "input_reference", "provider_reference", "provenance_reference",
        mode="before",
    )
    @classmethod
    def _logical_reference(cls, value: object) -> str:
        return logical_reference(value, "Panel evidence reference")

    @field_validator("output_asset_id")
    @classmethod
    def _optional_reference(cls, value: str | None) -> str | None:
        return None if value is None else logical_reference(value, "output asset")

    @field_validator(
        "plan_fingerprint",
        "request_fingerprint",
        "input_sha256",
        "provider_configuration_fingerprint",
    )
    @classmethod
    def _digest(cls, value: str) -> str:
        return sha256_digest(value)

    @field_validator("output_sha256")
    @classmethod
    def _optional_digest(cls, value: str | None) -> str | None:
        return None if value is None else sha256_digest(value)

    @model_validator(mode="after")
    def _accepted_output_is_complete(self) -> PanelGenerationEvidence:
        output_fields = (
            self.output_asset_id,
            self.output_sha256,
            self.media_type,
            self.width,
            self.height,
        )
        expected_state = {
            "accepted": "PANEL_ACCEPTED",
            "declared_failure": "DECLARED_FAILURE",
            "recovery_required": "RECOVERY_REQUIRED",
        }[self.outcome]
        if self.attempt_state != expected_state:
            raise ValueError("evidence outcome must match the exact terminal attempt state")
        if self.outcome == "accepted" and any(value is None for value in output_fields):
            raise ValueError("accepted Panel evidence requires one complete PNG output")
        if self.outcome != "accepted" and any(value is not None for value in output_fields):
            raise ValueError("non-success Panel evidence cannot name an accepted output")
        return self


@dataclass(frozen=True, slots=True)
class PanelGenerationAuthorityResult:
    attempt_id: str
    outcome: PanelAuthorityOutcome
    record: PanelAttemptRecord | None = field(default=None, repr=False)


@dataclass(frozen=True, slots=True)
class PanelGenerationEvidenceLookupResult:
    attempt_id: str
    outcome: Literal["found", "missing", "corrupt"]
    evidence: PanelGenerationEvidence | None = field(default=None, repr=False)


@dataclass(frozen=True, slots=True)
class PanelGenerationPageObservation:
    outcome: Literal["found", "missing", "corrupt", "ambiguous"]
    plan_ids: tuple[str, ...] = ()
    attempt_ids: tuple[str, ...] = ()
    records: tuple[PanelAttemptRecord, ...] = field(default=(), repr=False)
    evidence: tuple[PanelGenerationEvidence, ...] = field(default=(), repr=False)
    authority_attempt_ids: tuple[str, ...] = ()


class LocalPanelGenerationAuthority:
    """Private Panel-keyed attempt and immutable evidence sidecar."""

    def __init__(self, owner_root: Path) -> None:
        self._root = _prepare_authority_root(owner_root)
        self._database_path = _prepare_authority_database(self._root)
        self._initialize_schema()

    def reserve(self, reservation: PanelAttemptReservation) -> PanelGenerationAuthorityResult:
        record = PanelAttemptRecord(
            reservation=reservation, state="RESERVED", provider_start_consumed=False
        )
        return self._create_or_confirm(record)

    def start_provider(
        self, reservation: PanelAttemptReservation
    ) -> PanelGenerationAuthorityResult:
        return self._transition(reservation, {"RESERVED"}, "PROVIDER_STARTED")

    def record_provider_completed(
        self, reservation: PanelAttemptReservation
    ) -> PanelGenerationAuthorityResult:
        return self._transition(
            reservation, {"PROVIDER_STARTED"}, "PROVIDER_COMPLETED"
        )

    def record_asset_registered(
        self, reservation: PanelAttemptReservation, output_asset_id: str
    ) -> PanelGenerationAuthorityResult:
        try:
            asset_id = logical_reference(output_asset_id, "Panel output asset")
        except ValueError:
            return PanelGenerationAuthorityResult(reservation.attempt_id, "failed")
        return self._transition(
            reservation,
            {"PROVIDER_COMPLETED"},
            "ASSET_REGISTERED",
            output_asset_id=asset_id,
        )

    def commit_evidence(
        self, reservation: PanelAttemptReservation, evidence: PanelGenerationEvidence
    ) -> PanelGenerationAuthorityResult:
        if not _evidence_matches_reservation(evidence, reservation):
            return PanelGenerationAuthorityResult(reservation.attempt_id, "conflict")
        connection: sqlite3.Connection | None = None
        try:
            connection = self._connect()
            connection.execute("BEGIN IMMEDIATE")
            current = self._read_record(connection, reservation.attempt_id)
            if current is None:
                connection.rollback()
                return PanelGenerationAuthorityResult(reservation.attempt_id, "missing")
            if current.reservation != reservation:
                connection.rollback()
                return PanelGenerationAuthorityResult(reservation.attempt_id, "conflict")
            existing = self._read_evidence(connection, reservation.attempt_id)
            if isinstance(existing, str):
                connection.rollback()
                return PanelGenerationAuthorityResult(reservation.attempt_id, "corrupt")
            if existing is not None:
                connection.rollback()
                if existing == evidence and current.evidence_id == evidence.evidence_id:
                    return PanelGenerationAuthorityResult(
                        reservation.attempt_id, "confirmed", current
                    )
                return PanelGenerationAuthorityResult(reservation.attempt_id, "conflict")
            if current.state not in {"ASSET_REGISTERED", "RECOVERY_REQUIRED"}:
                connection.rollback()
                return PanelGenerationAuthorityResult(reservation.attempt_id, "conflict")
            if evidence.output_asset_id != current.output_asset_id:
                connection.rollback()
                return PanelGenerationAuthorityResult(reservation.attempt_id, "conflict")
            next_record = current.model_copy(
                update={"state": "EVIDENCE_COMMITTED", "evidence_id": evidence.evidence_id}
            )
            self._insert_evidence(connection, evidence)
            self._replace_record(connection, next_record)
            connection.commit()
            return PanelGenerationAuthorityResult(
                reservation.attempt_id, "updated", next_record
            )
        except Exception:
            if connection is not None:
                _rollback_authority(connection)
            return PanelGenerationAuthorityResult(reservation.attempt_id, "failed")
        finally:
            if connection is not None:
                connection.close()

    def accept_panel(
        self, reservation: PanelAttemptReservation
    ) -> PanelGenerationAuthorityResult:
        current = self.lookup_attempt(reservation.attempt_id)
        accepted_asset_id = current.record.output_asset_id if current.record is not None else None
        return self._transition(
            reservation,
            {"EVIDENCE_COMMITTED"},
            "PANEL_ACCEPTED",
            accepted_asset_id=accepted_asset_id,
        )

    def declare_failure(
        self, reservation: PanelAttemptReservation
    ) -> PanelGenerationAuthorityResult:
        return self._transition(
            reservation,
            {"PROVIDER_STARTED", "PROVIDER_COMPLETED"},
            "DECLARED_FAILURE",
        )

    def require_recovery(
        self, reservation: PanelAttemptReservation
    ) -> PanelGenerationAuthorityResult:
        return self._transition(
            reservation,
            {"PROVIDER_STARTED", "PROVIDER_COMPLETED", "ASSET_REGISTERED"},
            "RECOVERY_REQUIRED",
        )

    def lookup_attempt(self, attempt_id: str) -> PanelGenerationAuthorityResult:
        try:
            resolved = logical_reference(attempt_id, "Panel attempt")
        except ValueError:
            return PanelGenerationAuthorityResult("", "corrupt")
        connection: sqlite3.Connection | None = None
        try:
            connection = self._connect()
            row = connection.execute(
                "SELECT project_id, page_id, plan_id, panel_id, state, payload_json, "
                "payload_digest FROM panel_attempts WHERE attempt_id = ?",
                (resolved,),
            ).fetchone()
            if row is None:
                return PanelGenerationAuthorityResult(resolved, "missing")
            record = _validated_record(row)
            if record is None or record.reservation.attempt_id != resolved:
                return PanelGenerationAuthorityResult(resolved, "corrupt")
            return PanelGenerationAuthorityResult(resolved, "confirmed", record)
        except Exception:
            return PanelGenerationAuthorityResult(resolved, "corrupt")
        finally:
            if connection is not None:
                connection.close()

    def lookup_evidence(self, attempt_id: str) -> PanelGenerationEvidenceLookupResult:
        connection: sqlite3.Connection | None = None
        try:
            resolved = logical_reference(attempt_id, "Panel attempt")
            connection = self._connect()
            evidence = self._read_evidence(connection, resolved)
            if isinstance(evidence, str):
                return PanelGenerationEvidenceLookupResult(resolved, "corrupt")
            if evidence is None:
                return PanelGenerationEvidenceLookupResult(resolved, "missing")
            return PanelGenerationEvidenceLookupResult(resolved, "found", evidence)
        except Exception:
            return PanelGenerationEvidenceLookupResult(attempt_id, "corrupt")
        finally:
            if connection is not None:
                connection.close()

    def observe_page(  # noqa: C901 - one closed Page integrity inventory.
        self, project_id: str, page_id: str
    ) -> PanelGenerationPageObservation:
        """Return one verified Page inventory without changing authority state."""

        path_status = _readonly_authority_status(self._root, self._database_path)
        if path_status == "missing":
            return PanelGenerationPageObservation("missing")
        if path_status == "corrupt":
            return PanelGenerationPageObservation("corrupt")
        try:
            uri = f"{self._database_path.as_uri()}?mode=ro"
            with sqlite3.connect(uri, uri=True) as connection:
                connection.execute("PRAGMA query_only = ON")
                if int(connection.execute("PRAGMA user_version").fetchone()[0]) != _AUTHORITY_SCHEMA_VERSION:
                    return PanelGenerationPageObservation("corrupt")
                attempt_columns = tuple(
                    (str(row[1]), str(row[2]).upper(), int(row[3]), row[4], int(row[5]))
                    for row in connection.execute("PRAGMA table_info(panel_attempts)")
                )
                evidence_columns = tuple(
                    (str(row[1]), str(row[2]).upper(), int(row[3]), row[4], int(row[5]))
                    for row in connection.execute("PRAGMA table_info(panel_evidence)")
                )
                if not _panel_schema_objects_are_exact(connection) or attempt_columns != (
                    ("attempt_id", "TEXT", 0, None, 1),
                    ("project_id", "TEXT", 1, None, 0),
                    ("page_id", "TEXT", 1, None, 0),
                    ("plan_id", "TEXT", 1, None, 0),
                    ("panel_id", "TEXT", 1, None, 0),
                    ("state", "TEXT", 1, None, 0),
                    ("payload_json", "TEXT", 1, None, 0),
                    ("payload_digest", "TEXT", 1, None, 0),
                ) or evidence_columns != (
                    ("attempt_id", "TEXT", 0, None, 1),
                    ("evidence_id", "TEXT", 1, None, 0),
                    ("payload_json", "TEXT", 1, None, 0),
                    ("payload_digest", "TEXT", 1, None, 0),
                ):
                    return PanelGenerationPageObservation("corrupt")
                attempt_rows = connection.execute(
                    "SELECT project_id, page_id, plan_id, panel_id, state, payload_json, payload_digest "
                    "FROM panel_attempts"
                ).fetchall()
                evidence_rows = connection.execute(
                    "SELECT attempt_id, evidence_id, payload_json, payload_digest FROM panel_evidence"
                ).fetchall()
            attempts = tuple(_validated_record(row) for row in attempt_rows)
            if any(record is None for record in attempts):
                return PanelGenerationPageObservation("corrupt")
            evidence = tuple(_validated_evidence(row) for row in evidence_rows)
            if any(item is None for item in evidence):
                return PanelGenerationPageObservation("corrupt")
            attempt_by_id = {
                record.reservation.attempt_id: record
                for record in attempts
                if record is not None
            }
            if len(attempt_by_id) != len(attempts):
                return PanelGenerationPageObservation("ambiguous")
            for item in evidence:
                assert item is not None
                record = attempt_by_id.get(item.attempt_id)
                if record is None or not _evidence_matches_reservation(
                    item, record.reservation
                ) or (
                    record.evidence_id != item.evidence_id
                    or record.output_asset_id != item.output_asset_id
                    or record.state not in {"EVIDENCE_COMMITTED", "PANEL_ACCEPTED"}
                ):
                    return PanelGenerationPageObservation("corrupt")
            evidence_attempt_ids = {
                item.attempt_id for item in evidence if item is not None
            }
            if any(
                (record.state in {"EVIDENCE_COMMITTED", "PANEL_ACCEPTED"})
                != (record.reservation.attempt_id in evidence_attempt_ids)
                for record in attempt_by_id.values()
            ):
                return PanelGenerationPageObservation("corrupt")
            page_records = tuple(
                record
                for record in attempts
                if record is not None
                and record.reservation.project_id == project_id
                and record.reservation.page_id == page_id
            )
        except Exception:
            return PanelGenerationPageObservation("corrupt")
        if not page_records:
            return PanelGenerationPageObservation(
                "missing", authority_attempt_ids=tuple(sorted(attempt_by_id))
            )
        plans = tuple(sorted({record.reservation.plan_id for record in page_records}))
        attempt_ids = tuple(
            sorted(record.reservation.attempt_id for record in page_records)
        )
        if len(plans) != 1:
            return PanelGenerationPageObservation(
                "ambiguous",
                plans,
                attempt_ids,
                page_records,
                (),
                tuple(sorted(attempt_by_id)),
            )
        page_evidence = tuple(
            sorted(
                (
                    item
                    for item in evidence
                    if item is not None and item.attempt_id in attempt_ids
                ),
                key=lambda item: item.attempt_id,
            )
        )
        return PanelGenerationPageObservation(
            "found",
            plans,
            attempt_ids,
            page_records,
            page_evidence,
            tuple(sorted(attempt_by_id)),
        )

    @classmethod
    def observe_page_at(
        cls, owner_root: Path, project_id: str, page_id: str
    ) -> PanelGenerationPageObservation:
        authority = object.__new__(cls)
        authority._root = owner_root
        authority._database_path = owner_root / _AUTHORITY_DATABASE
        return authority.observe_page(project_id, page_id)

    def _create_or_confirm(
        self, record: PanelAttemptRecord
    ) -> PanelGenerationAuthorityResult:
        connection: sqlite3.Connection | None = None
        try:
            connection = self._connect()
            connection.execute("BEGIN IMMEDIATE")
            existing = self._read_record(connection, record.reservation.attempt_id)
            if existing is not None:
                connection.rollback()
                return PanelGenerationAuthorityResult(
                    record.reservation.attempt_id,
                    "confirmed" if existing == record else "conflict",
                    existing,
                )
            active = connection.execute(
                "SELECT project_id, page_id, plan_id, panel_id, state, payload_json, payload_digest "
                "FROM panel_attempts",
            ).fetchall()
            verified = tuple(_validated_record(row) for row in active)
            if any(item is None for item in verified):
                connection.rollback()
                return PanelGenerationAuthorityResult(record.reservation.attempt_id, "corrupt")
            if any(
                item is not None
                and item.reservation.project_id == record.reservation.project_id
                and item.reservation.page_id == record.reservation.page_id
                and item.reservation.panel_id == record.reservation.panel_id
                and item.reservation.plan_id != record.reservation.plan_id
                for item in verified
            ):
                connection.rollback()
                return PanelGenerationAuthorityResult(record.reservation.attempt_id, "conflict")
            if any(
                item is not None
                and item.reservation.project_id == record.reservation.project_id
                and item.reservation.page_id == record.reservation.page_id
                and item.reservation.panel_id == record.reservation.panel_id
                and item.state in _NON_TERMINAL_STATES
                for item in verified
            ):
                connection.rollback()
                return PanelGenerationAuthorityResult(record.reservation.attempt_id, "conflict")
            self._insert_record(connection, record)
            connection.commit()
            return PanelGenerationAuthorityResult(
                record.reservation.attempt_id, "created", record
            )
        except sqlite3.IntegrityError:
            if connection is not None:
                _rollback_authority(connection)
            return PanelGenerationAuthorityResult(record.reservation.attempt_id, "conflict")
        except Exception:
            if connection is not None:
                _rollback_authority(connection)
            return PanelGenerationAuthorityResult(record.reservation.attempt_id, "failed")
        finally:
            if connection is not None:
                connection.close()

    def _transition(
        self,
        reservation: PanelAttemptReservation,
        expected: set[PanelAttemptState],
        target: PanelAttemptState,
        *,
        output_asset_id: str | None = None,
        accepted_asset_id: str | None = None,
    ) -> PanelGenerationAuthorityResult:
        connection: sqlite3.Connection | None = None
        try:
            connection = self._connect()
            connection.execute("BEGIN IMMEDIATE")
            current = self._read_record(connection, reservation.attempt_id)
            if current is None:
                connection.rollback()
                return PanelGenerationAuthorityResult(reservation.attempt_id, "missing")
            if current.reservation != reservation:
                connection.rollback()
                return PanelGenerationAuthorityResult(reservation.attempt_id, "conflict")
            if current.state == target:
                connection.rollback()
                if (
                    (output_asset_id is None or current.output_asset_id == output_asset_id)
                    and (
                        accepted_asset_id is None
                        or current.accepted_asset_id == accepted_asset_id
                    )
                ):
                    return PanelGenerationAuthorityResult(
                        reservation.attempt_id, "confirmed", current
                    )
                return PanelGenerationAuthorityResult(reservation.attempt_id, "conflict")
            if current.state not in expected:
                connection.rollback()
                return PanelGenerationAuthorityResult(reservation.attempt_id, "conflict")
            next_record = current.model_copy(
                update={
                    "state": target,
                    "provider_start_consumed": target != "RESERVED",
                    "output_asset_id": output_asset_id or current.output_asset_id,
                    "accepted_asset_id": accepted_asset_id,
                }
            )
            self._replace_record(connection, next_record)
            connection.commit()
            return PanelGenerationAuthorityResult(
                reservation.attempt_id, "updated", next_record
            )
        except Exception:
            if connection is not None:
                _rollback_authority(connection)
            return PanelGenerationAuthorityResult(reservation.attempt_id, "failed")
        finally:
            if connection is not None:
                connection.close()

    def _initialize_schema(self) -> None:
        connection: sqlite3.Connection | None = None
        try:
            connection = self._connect()
            connection.execute("BEGIN IMMEDIATE")
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            tables = {
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
                )
            }
            if version == 0 and not tables:
                connection.execute(
                    "CREATE TABLE panel_attempts (attempt_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, "
                    "page_id TEXT NOT NULL, plan_id TEXT NOT NULL, panel_id TEXT NOT NULL, "
                    "state TEXT NOT NULL, payload_json TEXT NOT NULL, "
                    "payload_digest TEXT NOT NULL)"
                )
                states = ",".join(f"'{value}'" for value in _NON_TERMINAL_STATES)
                connection.execute(
                    "CREATE UNIQUE INDEX one_nonterminal_panel_attempt "
                    "ON panel_attempts(project_id, page_id, panel_id) "
                    f"WHERE state IN ({states})"
                )
                connection.execute(
                    "CREATE TABLE panel_evidence (attempt_id TEXT PRIMARY KEY, evidence_id TEXT UNIQUE NOT NULL, "
                    "payload_json TEXT NOT NULL, payload_digest TEXT NOT NULL)"
                )
                connection.execute(f"PRAGMA user_version = {_AUTHORITY_SCHEMA_VERSION}")
                connection.commit()
                return
            if version != _AUTHORITY_SCHEMA_VERSION or tables != {
                "panel_attempts", "panel_evidence"
            }:
                raise ValueError("Panel generation authority is unavailable")
            connection.commit()
        except Exception as error:
            if connection is not None:
                _rollback_authority(connection)
            raise ValueError("Panel generation authority is unavailable") from error
        finally:
            if connection is not None:
                connection.close()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=5.0, isolation_level=None)
        mode = str(connection.execute("PRAGMA journal_mode = DELETE").fetchone()[0]).lower()
        if mode != "delete":
            connection.close()
            raise ValueError("Panel generation authority is unavailable")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    @staticmethod
    def _read_record(
        connection: sqlite3.Connection, attempt_id: str
    ) -> PanelAttemptRecord | None:
        row = connection.execute(
            "SELECT project_id, page_id, plan_id, panel_id, state, payload_json, payload_digest "
            "FROM panel_attempts WHERE attempt_id = ?",
            (attempt_id,),
        ).fetchone()
        return None if row is None else _validated_record(row)

    @staticmethod
    def _insert_record(connection: sqlite3.Connection, record: PanelAttemptRecord) -> None:
        payload = _canonical_model_json(record)
        connection.execute(
            "INSERT INTO panel_attempts VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                record.reservation.attempt_id,
                record.reservation.project_id,
                record.reservation.page_id,
                record.reservation.plan_id,
                record.reservation.panel_id,
                record.state,
                payload,
                _authority_digest(payload),
            ),
        )

    @staticmethod
    def _replace_record(connection: sqlite3.Connection, record: PanelAttemptRecord) -> None:
        payload = _canonical_model_json(record)
        changed = connection.execute(
            "UPDATE panel_attempts SET state = ?, payload_json = ?, payload_digest = ? "
            "WHERE attempt_id = ?",
            (record.state, payload, _authority_digest(payload), record.reservation.attempt_id),
        ).rowcount
        if changed != 1:
            raise ValueError("Panel attempt disappeared during transition")

    @staticmethod
    def _read_evidence(
        connection: sqlite3.Connection, attempt_id: str
    ) -> PanelGenerationEvidence | str | None:
        row = connection.execute(
            "SELECT payload_json, payload_digest FROM panel_evidence WHERE attempt_id = ?",
            (attempt_id,),
        ).fetchone()
        if row is None:
            return None
        if not isinstance(row[0], str) or not isinstance(row[1], str):
            return "corrupt"
        if _authority_digest(row[0]) != row[1]:
            return "corrupt"
        try:
            return PanelGenerationEvidence.model_validate_json(row[0])
        except Exception:
            return "corrupt"

    @staticmethod
    def _insert_evidence(
        connection: sqlite3.Connection, evidence: PanelGenerationEvidence
    ) -> None:
        payload = _canonical_model_json(evidence)
        connection.execute(
            "INSERT INTO panel_evidence VALUES (?, ?, ?, ?)",
            (
                evidence.attempt_id,
                evidence.evidence_id,
                payload,
                _authority_digest(payload),
            ),
        )


def _evidence_matches_reservation(
    evidence: PanelGenerationEvidence, reservation: PanelAttemptReservation
) -> bool:
    return isinstance(evidence, PanelGenerationEvidence) and (
        evidence.attempt_id,
        evidence.plan_id,
        evidence.plan_fingerprint,
        evidence.project_id,
        evidence.page_id,
        evidence.panel_id,
        evidence.panel_order,
        evidence.request_id,
        evidence.request_fingerprint,
    ) == (
        reservation.attempt_id,
        reservation.plan_id,
        reservation.plan_fingerprint,
        reservation.project_id,
        reservation.page_id,
        reservation.panel_id,
        reservation.panel_order,
        reservation.request_id,
        reservation.request_fingerprint,
    )


def _validated_record(row: object) -> PanelAttemptRecord | None:
    if not isinstance(row, tuple) or len(row) != 7:
        return None
    project_id, page_id, plan_id, panel_id, state, payload, digest = row
    if not isinstance(payload, str) or not isinstance(digest, str):
        return None
    if _authority_digest(payload) != digest:
        return None
    try:
        record = PanelAttemptRecord.model_validate_json(payload)
    except Exception:
        return None
    if (
        record.reservation.project_id != project_id
        or record.reservation.page_id != page_id
        or record.reservation.plan_id != plan_id
        or record.reservation.panel_id != panel_id
        or record.state != state
    ):
        return None
    return record


def _validated_evidence(row: object) -> PanelGenerationEvidence | None:
    if not isinstance(row, tuple) or len(row) != 4:
        return None
    attempt_id, evidence_id, payload, digest = row
    if not isinstance(payload, str) or not isinstance(digest, str):
        return None
    if _authority_digest(payload) != digest:
        return None
    try:
        evidence = PanelGenerationEvidence.model_validate_json(payload)
    except Exception:
        return None
    if evidence.attempt_id != attempt_id or evidence.evidence_id != evidence_id:
        return None
    return evidence


def _panel_schema_objects_are_exact(connection: sqlite3.Connection) -> bool:
    objects = connection.execute(
        "SELECT type, name, tbl_name FROM sqlite_master "
        "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
    ).fetchall()
    if objects != [
        ("index", "one_nonterminal_panel_attempt", "panel_attempts"),
        ("table", "panel_attempts", "panel_attempts"),
        ("table", "panel_evidence", "panel_evidence"),
    ]:
        return False
    expected: dict[str, set[tuple[int, str, int, tuple[str, ...]]]] = {
        "panel_attempts": {
            (1, "pk", 0, ("attempt_id",)),
            (1, "c", 1, ("project_id", "page_id", "panel_id")),
        },
        "panel_evidence": {
            (1, "pk", 0, ("attempt_id",)),
            (1, "u", 0, ("evidence_id",)),
        },
    }
    for table, expected_indexes in expected.items():
        observed: set[tuple[int, str, int, tuple[str, ...]]] = set()
        for index in connection.execute(f"PRAGMA index_list({table})").fetchall():
            if len(index) != 5 or not isinstance(index[1], str):
                return False
            columns = tuple(
                str(row[2])
                for row in connection.execute(
                    f"PRAGMA index_info({index[1]})"
                ).fetchall()
            )
            observed.add((int(index[2]), str(index[3]), int(index[4]), columns))
        if observed != expected_indexes:
            return False
    row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'index' "
        "AND name = 'one_nonterminal_panel_attempt'"
    ).fetchone()
    states = ",".join(f"'{value}'" for value in _NON_TERMINAL_STATES)
    expected_sql = (
        "CREATE UNIQUE INDEX one_nonterminal_panel_attempt "
        "ON panel_attempts(project_id, page_id, panel_id) "
        f"WHERE state IN ({states})"
    )
    return bool(
        isinstance(row, tuple)
        and len(row) == 1
        and isinstance(row[0], str)
        and _without_ascii_whitespace(row[0]).lower()
        == _without_ascii_whitespace(expected_sql).lower()
    )


def _without_ascii_whitespace(value: str) -> str:
    return "".join(
        character for character in value if character not in " \t\r\n\f\v"
    )


def _readonly_authority_status(
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


def _canonical_model_json(model: DirectorModel) -> str:
    return json.dumps(
        model.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )


def _authority_digest(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _prepare_authority_root(root: Path) -> Path:
    if not isinstance(root, Path) or root.is_symlink() or _authority_reparse(root):
        raise ValueError("Panel generation authority root is unavailable")
    root.mkdir(parents=True, exist_ok=True)
    resolved = root.resolve(strict=True)
    if not resolved.is_dir() or resolved.is_symlink() or _authority_reparse(resolved):
        raise ValueError("Panel generation authority root is unavailable")
    return resolved


def _prepare_authority_database(root: Path) -> Path:
    path = root / _AUTHORITY_DATABASE
    if path.exists() and (
        not path.is_file() or path.is_symlink() or _authority_reparse(path)
    ):
        raise ValueError("Panel generation authority is unavailable")
    if path.resolve(strict=False).parent != root:
        raise ValueError("Panel generation authority is unavailable")
    return path


def _authority_reparse(path: Path) -> bool:
    try:
        attributes = path.lstat()
        return bool(
            getattr(attributes, "st_file_attributes", 0)
            & stat.FILE_ATTRIBUTE_REPARSE_POINT
        )
    except (FileNotFoundError, OSError):
        return False


def _rollback_authority(connection: sqlite3.Connection) -> None:
    try:
        connection.rollback()
    except sqlite3.Error:
        pass
