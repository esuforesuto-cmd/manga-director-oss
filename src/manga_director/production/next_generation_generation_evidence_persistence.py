"""Internal durable sidecar persistence for bound Generation Evidence.

The Evidence store owns only canonical logical Evidence records and private
integrity metadata.  It never reads assets, invokes providers, or changes
workflow state.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol, cast

from pydantic import ConfigDict

from manga_director.production.director import DirectorModel
from manga_director.production.next_generation_attempt_to_evidence_binding import (
    AttemptToEvidenceBindingReport,
)
from manga_director.production.next_generation_attempt_to_evidence_construction import (
    AttemptToEvidenceConstructionReport,
)
from manga_director.production.next_generation_generation_evidence import (
    GenerationEvidenceEnvelopeDTO,
    GenerationEvidenceValidationReport,
)

FindingStatus = Literal["blocked"]
PersistenceStatus = Literal["persisted", "blocked"]
StoreOutcome = Literal["persisted", "confirmed", "conflict", "failed"]
LookupOutcome = Literal["found", "missing", "corrupt"]
EvidenceStatus = Literal["ready", "needs_evidence", "needs_review"]

_SCHEMA_VERSION = 1
_DATABASE_FILENAME = "generation-evidence.sqlite3"
_TABLE_NAME = "generation_evidence"
_WINDOWS_ABSOLUTE_PATH = ("/", "\\")


class _GenerationEvidencePersistenceModel(DirectorModel):
    """Private base for closed, immutable internal persistence DTOs."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class GenerationEvidencePersistenceFindingDTO(_GenerationEvidencePersistenceModel):
    """One deterministic, redacted persistence finding."""

    code: str
    status: FindingStatus
    message: str
    attempt_id: str = ""
    output_asset_id: str = ""


class GenerationEvidencePersistenceReport(_GenerationEvidencePersistenceModel):
    """Immutable persistence result without upstream reports or private metadata."""

    attempt_id: str = ""
    generation_evidence: GenerationEvidenceEnvelopeDTO | None = None
    findings: tuple[GenerationEvidencePersistenceFindingDTO, ...] = ()
    status: PersistenceStatus
    persisted: bool
    idempotent_replay: bool
    persistence_performed: bool


@dataclass(frozen=True, slots=True)
class GenerationEvidenceStoreWriteRequest:
    """Private store request containing only bound logical Evidence."""

    attempt_id: str
    provider_reference: str
    evidence_status: EvidenceStatus
    generation_evidence: GenerationEvidenceEnvelopeDTO = field(repr=False)


@dataclass(frozen=True, slots=True)
class GenerationEvidenceStoreWriteResult:
    """Private owner result that never reveals sidecar details."""

    attempt_id: str
    outcome: StoreOutcome


@dataclass(frozen=True, slots=True)
class GenerationEvidenceStoreLookupResult:
    """Private exact-attempt lookup result for integrity and replay checks."""

    attempt_id: str
    outcome: LookupOutcome
    generation_evidence: GenerationEvidenceEnvelopeDTO | None = field(default=None, repr=False)
    evidence_status: EvidenceStatus | None = None


class GenerationEvidenceStorePort(Protocol):
    """Internal immutable Evidence persistence and exact-attempt lookup port."""

    def persist(
        self, request: GenerationEvidenceStoreWriteRequest
    ) -> GenerationEvidenceStoreWriteResult: ...

    def lookup(self, attempt_id: str) -> GenerationEvidenceStoreLookupResult: ...


class GenerationEvidencePersistenceService:
    """Persist only an already constructed and bound Evidence record."""

    def persist(
        self,
        construction_report: AttemptToEvidenceConstructionReport,
        evidence_store: GenerationEvidenceStorePort,
    ) -> GenerationEvidencePersistenceReport:
        """Return one redacted durable-write result without rerunning upstream services."""

        eligibility = _eligible_evidence(construction_report)
        if isinstance(eligibility, GenerationEvidencePersistenceFindingDTO):
            return _blocked_report(construction_report, eligibility)
        evidence, status = eligibility
        request = GenerationEvidenceStoreWriteRequest(
            attempt_id=construction_report.attempt_id,
            provider_reference=construction_report.provider_reference,
            evidence_status=status,
            generation_evidence=evidence,
        )
        try:
            result = evidence_store.persist(request)
        except Exception:
            return _blocked_report(
                construction_report,
                _finding("EVIDENCE_PERSISTENCE_FAILED", construction_report, evidence),
                persistence_performed=True,
            )
        if not isinstance(result, GenerationEvidenceStoreWriteResult):
            return _blocked_report(
                construction_report,
                _finding("EVIDENCE_PERSISTENCE_RESULT_INVALID", construction_report, evidence),
                persistence_performed=True,
            )
        if result.attempt_id != construction_report.attempt_id:
            return _blocked_report(
                construction_report,
                _finding("EVIDENCE_PERSISTENCE_ATTEMPT_MISMATCH", construction_report, evidence),
                persistence_performed=True,
            )
        if result.outcome == "persisted":
            return _persisted_report(construction_report, evidence, idempotent_replay=False)
        if result.outcome == "confirmed":
            return _persisted_report(construction_report, evidence, idempotent_replay=True)
        code = "EVIDENCE_PERSISTENCE_CONFLICT" if result.outcome == "conflict" else "EVIDENCE_PERSISTENCE_FAILED"
        return _blocked_report(
            construction_report,
            _finding(code, construction_report, evidence),
            persistence_performed=True,
        )


class LocalGenerationEvidenceStore(GenerationEvidenceStorePort):
    """Dedicated private SQLite owner for immutable canonical Evidence records."""

    def __init__(self, owner_root: Path) -> None:
        self._root = _prepare_owner_root(owner_root)
        self._database_path = _prepare_database_path(self._root)
        self._initialize_schema()

    def persist(
        self, request: GenerationEvidenceStoreWriteRequest
    ) -> GenerationEvidenceStoreWriteResult:
        """Insert or confirm one immutable exact-attempt Evidence record."""

        if not _valid_write_request(request):
            return GenerationEvidenceStoreWriteResult(request.attempt_id, "failed")
        payload = _canonical_json(request.generation_evidence)
        payload_digest = _digest(payload)
        binding_fingerprint = _binding_fingerprint(request)
        connection: sqlite3.Connection | None = None
        try:
            connection = self._connect()
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT payload_json, payload_digest, provider_reference, binding_fingerprint, "
                "evidence_status "
                f"FROM {_TABLE_NAME} WHERE attempt_id = ?",
                (request.attempt_id,),
            ).fetchone()
            if row is None:
                self._insert(connection, request, payload, payload_digest, binding_fingerprint)
                connection.commit()
                return GenerationEvidenceStoreWriteResult(request.attempt_id, "persisted")
            connection.rollback()
            existing = _verified_row(request.attempt_id, row)
            if existing is None:
                return GenerationEvidenceStoreWriteResult(request.attempt_id, "failed")
            (
                existing_payload,
                existing_digest,
                existing_provider_reference,
                existing_fingerprint,
                existing_status,
            ) = existing
            if (
                existing_payload == payload
                and existing_digest == payload_digest
                and existing_provider_reference == request.provider_reference
                and existing_fingerprint == binding_fingerprint
                and existing_status == request.evidence_status
            ):
                return GenerationEvidenceStoreWriteResult(request.attempt_id, "confirmed")
            return GenerationEvidenceStoreWriteResult(request.attempt_id, "conflict")
        except Exception:
            if connection is not None:
                _rollback_quietly(connection)
            return GenerationEvidenceStoreWriteResult(request.attempt_id, "failed")
        finally:
            if connection is not None:
                connection.close()

    def lookup(self, attempt_id: str) -> GenerationEvidenceStoreLookupResult:
        """Return a verified internal exact-attempt record, never a public API result."""

        if not _is_logical_reference(attempt_id):
            return GenerationEvidenceStoreLookupResult("", "corrupt")
        connection: sqlite3.Connection | None = None
        try:
            connection = self._connect()
            row = connection.execute(
                "SELECT payload_json, payload_digest, provider_reference, binding_fingerprint, "
                "evidence_status "
                f"FROM {_TABLE_NAME} WHERE attempt_id = ?",
                (attempt_id,),
            ).fetchone()
            if row is None:
                return GenerationEvidenceStoreLookupResult(attempt_id, "missing")
            verified = _verified_row(attempt_id, row)
            if verified is None:
                return GenerationEvidenceStoreLookupResult(attempt_id, "corrupt")
            payload, _, _, _, evidence_status = verified
            evidence = _validated_evidence(payload)
            if evidence is None or evidence.attempt_id != attempt_id:
                return GenerationEvidenceStoreLookupResult(attempt_id, "corrupt")
            return GenerationEvidenceStoreLookupResult(
                attempt_id,
                "found",
                generation_evidence=evidence,
                evidence_status=evidence_status,
            )
        except Exception:
            return GenerationEvidenceStoreLookupResult(attempt_id, "corrupt")
        finally:
            if connection is not None:
                connection.close()

    def _initialize_schema(self) -> None:
        connection: sqlite3.Connection | None = None
        try:
            connection = self._connect()
            connection.execute("BEGIN IMMEDIATE")
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            has_user_tables = _has_user_tables(connection)
            if version == 0 and not has_user_tables:
                connection.execute(
                    f"CREATE TABLE {_TABLE_NAME} ("
                    "attempt_id TEXT PRIMARY KEY, "
                    "payload_json TEXT NOT NULL, "
                    "payload_digest TEXT NOT NULL, "
                    "provider_reference TEXT NOT NULL, "
                    "binding_fingerprint TEXT NOT NULL, "
                    "evidence_status TEXT NOT NULL"
                    ")"
                )
                connection.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")
                connection.commit()
                return
            if version != _SCHEMA_VERSION or not _schema_is_valid(connection):
                raise ValueError("evidence store is unavailable")
            connection.commit()
        except (sqlite3.Error, TypeError, ValueError) as error:
            if connection is not None:
                _rollback_quietly(connection)
            raise ValueError("evidence store is unavailable") from error
        finally:
            if connection is not None:
                connection.close()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=5.0, isolation_level=None)
        mode = str(connection.execute("PRAGMA journal_mode = DELETE").fetchone()[0]).lower()
        if mode != "delete":
            connection.close()
            raise ValueError("evidence store is unavailable")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    @staticmethod
    def _insert(
        connection: sqlite3.Connection,
        request: GenerationEvidenceStoreWriteRequest,
        payload: str,
        payload_digest: str,
        binding_fingerprint: str,
    ) -> None:
        connection.execute(
            f"INSERT INTO {_TABLE_NAME} "
            "(attempt_id, payload_json, payload_digest, provider_reference, binding_fingerprint, "
            "evidence_status) VALUES (?, ?, ?, ?, ?, ?)",
            (
                request.attempt_id,
                payload,
                payload_digest,
                request.provider_reference,
                binding_fingerprint,
                request.evidence_status,
            ),
        )


def _eligible_evidence(
    report: AttemptToEvidenceConstructionReport,
) -> tuple[GenerationEvidenceEnvelopeDTO, EvidenceStatus] | GenerationEvidencePersistenceFindingDTO:
    evidence = report.generation_evidence
    if report.constructed is not True:
        return _finding("EVIDENCE_CONSTRUCTION_NOT_COMPLETED", report, evidence)
    if evidence is None:
        return _finding("EVIDENCE_CANDIDATE_MISSING", report, None)
    validation = report.generation_evidence_validation_report
    binding = report.attempt_to_evidence_binding_report
    if not _valid_evidence_validation(validation, report.attempt_id, evidence):
        return _finding("EVIDENCE_VALIDATION_NOT_ELIGIBLE", report, evidence)
    if not _valid_binding(binding, report.attempt_id, validation):
        return _finding("EVIDENCE_BINDING_NOT_ELIGIBLE", report, evidence)
    if binding is None:
        return _finding("EVIDENCE_BINDING_NOT_ELIGIBLE", report, evidence)
    if report.bound is not True or report.status == "blocked":
        return _finding("EVIDENCE_BINDING_NOT_ELIGIBLE", report, evidence)
    if report.provider_reference != binding.output_asset_registration_report.provider_reference:
        return _finding("EVIDENCE_BINDING_NOT_ELIGIBLE", report, evidence)
    status = binding.status
    if status not in {"ready", "needs_evidence", "needs_review"}:
        return _finding("EVIDENCE_BINDING_NOT_ELIGIBLE", report, evidence)
    return evidence, cast(EvidenceStatus, status)


def _valid_evidence_validation(
    validation: GenerationEvidenceValidationReport | None,
    attempt_id: str,
    evidence: GenerationEvidenceEnvelopeDTO,
) -> bool:
    if validation is None or validation.status == "blocked":
        return False
    matching = tuple(item for item in validation.envelopes if item.attempt_id == attempt_id)
    return len(matching) == 1 and _canonical_json(matching[0]) == _canonical_json(evidence)


def _valid_binding(
    binding: AttemptToEvidenceBindingReport | None,
    attempt_id: str,
    validation: GenerationEvidenceValidationReport | None,
) -> bool:
    if (
        binding is None
        or validation is None
        or binding.status == "blocked"
        or binding.bound is not True
        or binding.attempt_id != attempt_id
        or binding.generation_evidence_validation_report != validation
    ):
        return False
    try:
        provider_reference = binding.output_asset_registration_report.provider_reference
    except AttributeError:
        return False
    return (
        isinstance(provider_reference, str)
        and _is_logical_reference(provider_reference)
    )


def _persisted_report(
    construction: AttemptToEvidenceConstructionReport,
    evidence: GenerationEvidenceEnvelopeDTO,
    *,
    idempotent_replay: bool,
) -> GenerationEvidencePersistenceReport:
    return GenerationEvidencePersistenceReport(
        attempt_id=construction.attempt_id,
        generation_evidence=evidence,
        status="persisted",
        persisted=True,
        idempotent_replay=idempotent_replay,
        persistence_performed=True,
    )


def _blocked_report(
    construction: AttemptToEvidenceConstructionReport,
    finding: GenerationEvidencePersistenceFindingDTO,
    *,
    persistence_performed: bool = False,
) -> GenerationEvidencePersistenceReport:
    return GenerationEvidencePersistenceReport(
        attempt_id=_safe_value(construction.attempt_id),
        findings=(finding,),
        status="blocked",
        persisted=False,
        idempotent_replay=False,
        persistence_performed=persistence_performed,
    )


def _finding(
    code: str,
    construction: AttemptToEvidenceConstructionReport,
    evidence: GenerationEvidenceEnvelopeDTO | None,
) -> GenerationEvidencePersistenceFindingDTO:
    return GenerationEvidencePersistenceFindingDTO(
        code=code,
        status="blocked",
        message=code.replace("_", " ").lower(),
        attempt_id=_safe_value(construction.attempt_id),
        output_asset_id=_safe_value(evidence.output.output_asset_id) if evidence is not None else "",
    )


def _valid_write_request(request: GenerationEvidenceStoreWriteRequest) -> bool:
    return (
        _is_logical_reference(request.attempt_id)
        and _is_logical_reference(request.provider_reference)
        and request.generation_evidence.attempt_id == request.attempt_id
        and request.evidence_status in {"ready", "needs_evidence", "needs_review"}
    )


def _canonical_json(evidence: GenerationEvidenceEnvelopeDTO) -> str:
    return json.dumps(
        evidence.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _binding_fingerprint(request: GenerationEvidenceStoreWriteRequest) -> str:
    value = "\x00".join(
        (
            request.attempt_id,
            request.provider_reference,
            request.generation_evidence.output.output_asset_id,
        )
    )
    return _digest(value)


def _verified_row(
    attempt_id: str, row: object
) -> tuple[str, str, str, str, EvidenceStatus] | None:
    if not isinstance(row, tuple) or len(row) != 5 or not all(isinstance(value, str) for value in row):
        return None
    payload, payload_digest, provider_reference, binding_fingerprint, evidence_status = row
    if evidence_status not in {"ready", "needs_evidence", "needs_review"}:
        return None
    evidence = _validated_evidence(payload)
    if evidence is None or evidence.attempt_id != attempt_id:
        return None
    if _canonical_json(evidence) != payload or _digest(payload) != payload_digest:
        return None
    if not _is_logical_reference(provider_reference) or binding_fingerprint != _digest(
        "\x00".join((attempt_id, provider_reference, evidence.output.output_asset_id))
    ):
        return None
    return payload, payload_digest, provider_reference, binding_fingerprint, evidence_status


def _validated_evidence(payload: str) -> GenerationEvidenceEnvelopeDTO | None:
    try:
        return GenerationEvidenceEnvelopeDTO.model_validate_json(payload)
    except (TypeError, ValueError):
        return None


def _prepare_owner_root(owner_root: Path) -> Path:
    if not isinstance(owner_root, Path) or not owner_root.is_absolute() or ".." in owner_root.parts:
        raise ValueError("evidence store is unavailable")
    try:
        owner_root.mkdir(parents=True, exist_ok=True)
        _assert_private_path(owner_root, owner_root.parent)
        return owner_root
    except OSError as error:
        raise ValueError("evidence store is unavailable") from error


def _prepare_database_path(owner_root: Path) -> Path:
    path = owner_root / _DATABASE_FILENAME
    try:
        _assert_private_path(path, owner_root)
        return path
    except OSError as error:
        raise ValueError("evidence store is unavailable") from error


def _assert_private_path(path: Path, parent: Path) -> None:
    if path.parent != parent or _is_link_or_reparse_point(path):
        raise OSError("evidence store path is unavailable")
    if parent.exists() and _is_link_or_reparse_point(parent):
        raise OSError("evidence store path is unavailable")


def _is_link_or_reparse_point(path: Path) -> bool:
    try:
        status = path.lstat()
    except OSError:
        return False
    attributes = getattr(status, "st_file_attributes", 0)
    reparse_point = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return stat.S_ISLNK(status.st_mode) or bool(attributes & reparse_point)


def _has_user_tables(connection: sqlite3.Connection) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' LIMIT 1"
    ).fetchone() is not None


def _schema_is_valid(connection: sqlite3.Connection) -> bool:
    rows = connection.execute(f"PRAGMA table_info({_TABLE_NAME})").fetchall()
    expected = (
        ("attempt_id", "TEXT", 1),
        ("payload_json", "TEXT", 0),
        ("payload_digest", "TEXT", 0),
        ("provider_reference", "TEXT", 0),
        ("binding_fingerprint", "TEXT", 0),
        ("evidence_status", "TEXT", 0),
    )
    actual = tuple((str(row[1]), str(row[2]).upper(), int(row[5])) for row in rows)
    return actual == expected


def _rollback_quietly(connection: sqlite3.Connection) -> None:
    try:
        connection.rollback()
    except sqlite3.Error:
        pass


def _safe_value(value: object) -> str:
    return value if isinstance(value, str) and _is_logical_reference(value) else ""


def _is_logical_reference(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and value == value.strip()
        and not value.startswith(_WINDOWS_ABSOLUTE_PATH)
        and "://" not in value
        and not any(character.isspace() for character in value)
    )
