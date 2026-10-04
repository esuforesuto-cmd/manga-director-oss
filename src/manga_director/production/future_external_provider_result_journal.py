"""Private D12-I02 storage ownership and read-only D12-I01 source access."""

from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
import threading
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, NoReturn, cast

from pydantic import ConfigDict, Field, field_validator

from manga_director.production.director import DirectorModel
from manga_director.repositories.local_file import LocalFileRepository

_DURABILITY = ("_durability", "_future_durable_generation")
_SOURCE_PARTS = (*_DURABILITY, "external_provider_submission", "external-provider-submission.sqlite3")
_RESULT_PARTS = (*_DURABILITY, "external_provider_result_evidence")
_RESULT_DB = "external-provider-result-evidence.sqlite3"
_CAPABILITY_ISSUER = object()
_AUDIT_CAPABILITY_ISSUER = object()
_SCHEMA_ID = "manga_director.future_external_provider_result_evidence"
_EVENT_SCHEMA_ID = "manga_director.future_external_result_event"
_MAX_EVENTS = 32
_MAX_EVENT_BYTES = 8192
_SECRET_PARTS = ("api_key", "apikey", "authorization", "credential", "password", "secret", "token", "bearer")


class _StrictModel(DirectorModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


def _sha256(value: str) -> str:
    if type(value) is not str or len(value) != 64 or any(item not in "0123456789abcdef" for item in value):
        raise ValueError("lowercase SHA-256 required")
    return value


def _logical(value: str, maximum: int = 160) -> str:
    if (
        type(value) is not str
        or not value
        or value != value.strip()
        or len(value.encode("utf-8")) > maximum
        or any(item.isspace() or ord(item) < 32 for item in value)
        or value.startswith(("/", "\\"))
        or ".." in value
        or "://" in value
        or (len(value) > 2 and value[1] == ":")
        or "@" in value
        or any(item in value.lower() for item in _SECRET_PARTS)
    ):
        raise ValueError("invalid logical identifier")
    return value


def _metadata(value: object) -> dict[str, str]:
    if type(value) is not dict or len(value) > 16:
        raise ValueError("invalid metadata")
    result: dict[str, str] = {}
    for key, item in value.items():
        if type(key) is not str or type(item) is not str or not key or not item:
            raise ValueError("invalid metadata")
        if unicodedata.normalize("NFC", key) != key or unicodedata.normalize("NFC", item) != item:
            raise ValueError("invalid metadata")
        if len(key.encode("utf-8")) > 48 or len(item.encode("utf-8")) > 256:
            raise ValueError("invalid metadata")
        if any(char.isspace() or ord(char) < 32 for char in key) or any(ord(char) < 32 for char in item):
            raise ValueError("invalid metadata")
        lowered = f"{key}:{item}".lower()
        if any(part in lowered for part in _SECRET_PARTS) or "://" in item or "?" in item or "/" in item or "\\" in item or ".." in item or (len(item) > 2 and item[1] == ":"):
            raise ValueError("unsafe metadata")
        result[key] = item
    if len(_canonical(result).encode("utf-8")) > 2048:
        raise ValueError("invalid metadata")
    return dict(sorted(result.items()))


class OutputEvidenceV1(_StrictModel):
    logical_output_id: str
    sha256: str
    media_type: Literal["image/png", "image/jpeg", "image/webp"]
    byte_length: int = Field(ge=1, le=2147483647)
    metadata: dict[str, str]
    metadata_digest: str

    @field_validator("logical_output_id")
    @classmethod
    def _logical_output_id(cls, value: str) -> str:
        return _logical(value, 96)

    @field_validator("sha256", "metadata_digest")
    @classmethod
    def _digest_value(cls, value: str) -> str:
        return _sha256(value)

    @field_validator("metadata")
    @classmethod
    def _metadata_value(cls, value: dict[str, str]) -> dict[str, str]:
        return _metadata(value)

    def model_post_init(self, __context: object) -> None:
        if self.metadata_digest != _digest(self.metadata):
            raise ValueError("metadata digest mismatch")


class AcceptedObservationInputV1(_StrictModel):
    outputs: tuple[OutputEvidenceV1, ...]

    @field_validator("outputs")
    @classmethod
    def _outputs(cls, value: tuple[OutputEvidenceV1, ...]) -> tuple[OutputEvidenceV1, ...]:
        if not 1 <= len(value) <= 4:
            raise ValueError("invalid output count")
        if tuple(sorted(value, key=lambda item: item.logical_output_id)) != value:
            raise ValueError("outputs must be ordered")
        if len({item.logical_output_id for item in value}) != len(value) or len({item.sha256 for item in value}) != len(value):
            raise ValueError("ambiguous outputs")
        return value


class RejectedObservationInputV1(_StrictModel):
    rejection_code: Literal["SYNTHETIC_REJECTED"]


class AmbiguousObservationInputV1(_StrictModel):
    reason_code: Literal["SYNTHETIC_OBSERVATION_AMBIGUOUS"]


class MalformedObservationInputV1(_StrictModel):
    failure_code: Literal["SYNTHETIC_MALFORMED", "INVALID_OUTPUT", "INVALID_METADATA"]


class PostAcceptCandidateProjectionV1(_StrictModel):
    provider_reference: str
    provider_job_identity: str
    provenance_assurance: Literal["UNVERIFIED"]
    outputs: tuple[OutputEvidenceV1, ...]

    @field_validator("provider_reference", "provider_job_identity")
    @classmethod
    def _candidate_reference(cls, value: str) -> str:
        return _logical(value)

    @field_validator("outputs")
    @classmethod
    def _candidate_outputs(cls, value: tuple[OutputEvidenceV1, ...]) -> tuple[OutputEvidenceV1, ...]:
        return AcceptedObservationInputV1(outputs=value).outputs


class ExternalProviderResultEvidenceV1(_StrictModel):
    schema_id: Literal["manga_director.future_external_provider_result_evidence"] = "manga_director.future_external_provider_result_evidence"
    schema_version: Literal[1] = 1
    source_projection: dict[str, object]
    source_projection_digest: str
    submission_receipt_projection: dict[str, object]
    submission_receipt_identity: str
    result_observation_identity: str
    canonical_result_projection: dict[str, object]
    canonical_result_identity: str
    evidence_identity: str
    evidence_digest: str

    @field_validator("source_projection_digest", "submission_receipt_identity", "result_observation_identity", "canonical_result_identity", "evidence_identity", "evidence_digest")
    @classmethod
    def _identity(cls, value: str) -> str:
        return _sha256(value)

    def model_post_init(self, __context: object) -> None:
        if self.source_projection_digest != _digest(self.source_projection):
            raise ValueError("source digest mismatch")
        if self.submission_receipt_identity != _digest(self.submission_receipt_projection):
            raise ValueError("receipt identity mismatch")
        if self.canonical_result_identity != _digest(self.canonical_result_projection):
            raise ValueError("canonical result digest mismatch")
        unsigned = self.model_dump(mode="json", exclude={"evidence_identity", "evidence_digest"})
        if self.evidence_identity != _digest(unsigned) or self.evidence_digest != self.evidence_identity:
            raise ValueError("evidence digest mismatch")


@dataclass(frozen=True, slots=True)
class ResultJournalReport:
    status: str
    evidence: ExternalProviderResultEvidenceV1 | None = None


class _ResultObservationCapability:
    __slots__ = ("journal", "receipt", "sequence", "issuer", "nonce")
    def __init__(self, journal: str, receipt: str, sequence: int, nonce: bytes) -> None:
        self.journal, self.receipt, self.sequence, self.issuer, self.nonce = journal, receipt, sequence, _CAPABILITY_ISSUER, nonce
    def __reduce__(self) -> NoReturn:
        raise TypeError("capability is not serializable")


class _PostAcceptAuditCapability:
    __slots__ = ("journal", "receipt", "evidence", "sequence", "issuer", "nonce")

    def __init__(self, journal: str, receipt: str, evidence: str, sequence: int, nonce: bytes) -> None:
        self.journal, self.receipt, self.evidence, self.sequence = journal, receipt, evidence, sequence
        self.issuer, self.nonce = _AUDIT_CAPABILITY_ISSUER, nonce

    def __reduce__(self) -> NoReturn:
        raise TypeError("capability is not serializable")


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True, allow_nan=False)


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _output(value: object) -> dict[str, object]:
    return OutputEvidenceV1.model_validate(value).model_dump(mode="json")


def _observation_identity(receipt_identity: str, source_digest: str, kind: str, sequence: int) -> str:
    if kind not in {"ACCEPTED", "REJECTED", "AMBIGUOUS", "MALFORMED"}:
        raise ValueError("invalid observation kind")
    return _digest({"schema_id":"manga_director.future_external_result_observation_identity", "schema_version":1, "submission_receipt_identity":receipt_identity, "source_projection_digest":source_digest, "observation_kind":kind, "observation_sequence":sequence})


def _evidence_identity(receipt: str, canonical_result: str, observation: str) -> str:
    return _digest({"schema_id":"manga_director.future_external_provider_result_evidence_identity", "schema_version":1, "submission_receipt_identity":receipt, "canonical_result_identity":canonical_result, "result_observation_identity":observation})


def _canonical_result(binding: dict[str, object], outputs: list[dict[str, object]]) -> tuple[dict[str, object], str]:
    normalized = [_output(item) for item in outputs]
    logical_ids = [cast(str, item["logical_output_id"]) for item in normalized]
    digests = [cast(str, item["sha256"]) for item in normalized]
    if not 1 <= len(normalized) <= 4 or logical_ids != sorted(logical_ids) or len(set(logical_ids)) != len(normalized) or len(set(digests)) != len(normalized):
        raise ValueError("invalid output set")
    source = binding["source_projection"]
    if type(source) is not dict:
        raise ValueError("invalid source projection")
    result = {
        "schema_id": "manga_director.future_external_provider_canonical_result",
        "schema_version": 1,
        "dispatch_identity": source["dispatch_identity"],
        "idempotency_identity": source["idempotency_identity"],
        "attempt_id": source["attempt_id"],
        "project_id": source["project_id"],
        "page_id": source["page_id"],
        "target_page_reference": source["target_page_reference"],
        "manifest_digest": source["manifest_digest"],
        "provider_binding_digest": source["provider_binding_digest"],
        "attempt_binding_digest": source["attempt_binding_digest"],
        "profile_identity": source["profile_identity"],
        "provider_class": source["provider_class"],
        "request_digest": source["request_digest"],
        "request_metadata_digest": source["request_metadata_digest"],
        "source_projection_digest": binding["source_projection_digest"],
        "submission_journal_identity": source["submission_journal_identity"],
        "submission_receipt_identity": binding["submission_receipt_identity"],
        "source_terminal_sequence": source["terminal_sequence"],
        "source_terminal_event_digest": source["terminal_event_digest"],
        "source_terminal_observation_digest": source["terminal_observation_digest"],
        "provider_reference": source["provider_reference"],
        "provider_job_identity": source["provider_job_identity"],
        "provenance_assurance": "UNVERIFIED",
        "outputs": normalized,
    }
    return result, _digest(result)


def _table_signature(connection: sqlite3.Connection, table: str) -> tuple[tuple[object, ...], ...]:
    return tuple((row[1], row[2].upper(), bool(row[3]), row[4], row[5]) for row in connection.execute(f"PRAGMA table_info({table})"))


def _index_signature(connection: sqlite3.Connection, table: str) -> dict[str, tuple[bool, str, bool, tuple[str, ...]]]:
    result = {}
    for row in connection.execute(f"PRAGMA index_list({table})"):
        result[row[1]] = (bool(row[2]), row[3], bool(row[4]), tuple(item[2] for item in connection.execute(f"PRAGMA index_info({row[1]})")))
    return result


def _within(root: Path, target: Path) -> Path:
    resolved_root = root.resolve()
    resolved_target = target.resolve()
    if resolved_target != resolved_root and resolved_root not in resolved_target.parents:
        raise ValueError("D12-I02 owner escapes LocalFile root")
    return resolved_target


def _d12_i01_database(repository: LocalFileRepository) -> Path:
    """Verbatim frozen D12-I01 LocalFile owner derivation; never opens it."""
    if type(repository) is not LocalFileRepository:
        raise ValueError("trusted LocalFile repository required")
    return _within(repository._root, repository._root.resolve().joinpath(*_SOURCE_PARTS))


def _d12_i02_database(repository: LocalFileRepository) -> Path:
    if type(repository) is not LocalFileRepository:
        raise ValueError("trusted LocalFile repository required")
    root = _within(repository._root, repository._root.resolve().joinpath(*_RESULT_PARTS))
    if root.exists() and not root.is_dir():
        raise ValueError("D12-I02 owner collision")
    target = root / _RESULT_DB
    if target.exists() and target.is_dir():
        raise ValueError("D12-I02 database collision")
    return target


def _open_d12_i01_read_only(repository: LocalFileRepository) -> sqlite3.Connection:
    path = _d12_i01_database(repository)
    if not path.is_file():
        raise ValueError("D12-I01 source is unavailable")
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _read_accepted_source(repository: LocalFileRepository, journal_identity: str) -> dict[str, object]:
    """Read the frozen terminal D12-I01 row without invoking D12-I01 code."""
    connection = _open_d12_i01_read_only(repository)
    try:
        objects = {r[0]: r[1] for r in connection.execute("SELECT name,type FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'")}
        if int(connection.execute("PRAGMA user_version").fetchone()[0]) != 1 or objects != {"external_submission_journal":"table", "external_submission_events":"table", "ux_external_submission_dispatch":"index", "ux_external_submission_attempt":"index", "ix_external_submission_events_phase":"index"}:
            raise ValueError("D12-I01 schema is invalid")
        if _table_signature(connection, "external_submission_journal") != (("journal_identity","TEXT",False,None,1),("dispatch_identity","TEXT",True,None,0),("attempt_id","TEXT",True,None,0),("binding_json","TEXT",True,None,0),("binding_digest","TEXT",True,None,0),("phase","TEXT",True,None,0),("sequence","INTEGER",True,None,0),("terminal_observation_json","TEXT",False,None,0),("terminal_observation_digest","TEXT",False,None,0)):
            raise ValueError("D12-I01 schema is invalid")
        if _table_signature(connection, "external_submission_events") != (("journal_identity","TEXT",True,None,1),("sequence","INTEGER",True,None,2),("phase","TEXT",True,None,0),("payload_json","TEXT",True,None,0),("payload_digest","TEXT",True,None,0)):
            raise ValueError("D12-I01 schema is invalid")
        if _index_signature(connection, "external_submission_journal") != {"sqlite_autoindex_external_submission_journal_1":(True,"pk",False,("journal_identity",)),"ux_external_submission_dispatch":(True,"c",False,("dispatch_identity",)),"ux_external_submission_attempt":(True,"c",False,("attempt_id",))} or _index_signature(connection, "external_submission_events") != {"sqlite_autoindex_external_submission_events_1":(True,"pk",False,("journal_identity","sequence")),"ix_external_submission_events_phase":(False,"c",False,("journal_identity","phase"))}:
            raise ValueError("D12-I01 indexes are invalid")
        row = connection.execute("SELECT dispatch_identity,attempt_id,binding_json,binding_digest,phase,sequence,terminal_observation_json,terminal_observation_digest FROM external_submission_journal WHERE journal_identity=?", (journal_identity,)).fetchone()
        if row is None or row["phase"] != "ACCEPTED_IDENTIFIED":
            raise ValueError("D12-I01 source is ineligible")
        binding = json.loads(row["binding_json"])
        observation = json.loads(row["terminal_observation_json"])
        if type(binding) is not dict or _canonical(binding) != row["binding_json"] or type(observation) is not dict or _canonical(observation) != row["terminal_observation_json"]:
            raise ValueError("D12-I01 source is malformed")
        binding_payload = {key: value for key, value in binding.items() if key not in {"journal_identity", "binding_digest"}}
        if set(binding) != {"schema_id", "schema_version", "journal_identity", "dispatch_identity", "idempotency_identity", "attempt_id", "project_id", "page_id", "target_page_reference", "manifest_digest", "provider_binding_digest", "attempt_binding_digest", "profile_identity", "provider_class", "provider_reference", "request_digest", "metadata_digest", "binding_digest"} or binding.get("schema_id") != "manga_director.future_external_provider_submission_binding" or binding.get("schema_version") != "1" or binding.get("journal_identity") != journal_identity or binding.get("binding_digest") != _digest(binding_payload) or binding.get("journal_identity") != _digest(binding_payload) or row["binding_digest"] != binding["binding_digest"] or row["dispatch_identity"] != binding["dispatch_identity"] or row["attempt_id"] != binding["attempt_id"]:
            raise ValueError("D12-I01 binding is invalid")
        if observation.get("kind") != "ACCEPTED_IDENTIFIED" or type(observation.get("provider_identity")) is not str or not observation["provider_identity"] or set(observation) != {"kind", "provider_identity", "metadata"} or type(observation["metadata"]) is not dict or _digest(observation) != row["terminal_observation_digest"]:
            raise ValueError("D12-I01 source is malformed")
        terminal_event_digest = _replay_d12_i01_events(connection, binding, journal_identity, int(row["sequence"]), observation)
        fields = {"dispatch_identity":"dispatch_identity", "idempotency_identity":"idempotency_identity", "attempt_id":"attempt_id", "project_id":"project_id", "page_id":"page_id", "target_page_reference":"target_page_reference", "manifest_digest":"manifest_digest", "provider_binding_digest":"provider_binding_digest", "attempt_binding_digest":"attempt_binding_digest", "profile_identity":"profile_identity", "provider_class":"provider_class", "request_digest":"request_digest", "request_metadata_digest":"metadata_digest"}
        source = {key: binding[value] for key, value in fields.items()}
        source.update({"submission_journal_identity": journal_identity, "terminal_sequence": row["sequence"], "terminal_event_digest": terminal_event_digest, "terminal_observation_digest": row["terminal_observation_digest"], "provider_reference": binding["provider_reference"], "provider_job_identity": observation["provider_identity"]})
        return source
    finally:
        connection.close()


def _replay_d12_i01_events(connection: sqlite3.Connection, binding: dict[str, object], journal_identity: str, final_sequence: int, terminal_observation: dict[str, object]) -> str:
    events = connection.execute("SELECT sequence,phase,payload_json,payload_digest FROM external_submission_events WHERE journal_identity=? ORDER BY sequence", (journal_identity,)).fetchall()
    if len(events) != final_sequence + 1:
        raise ValueError("D12-I01 event chain is invalid")
    legal = {"DISPATCH_CONSUMED": {"SUBMISSION_STARTED"}, "SUBMISSION_STARTED": {"EDGE_ISSUED"}, "EDGE_ISSUED": {"FAILED_PRE_SEND", "REJECTED", "ACCEPTED_IDENTIFIED", "RECOVERY_REQUIRED"}}
    previous: str | None = None
    observed: dict[str, object] | None = None
    for sequence, item in enumerate(events):
        payload = _d12_i01_event(item, binding, journal_identity, sequence, previous, legal)
        value = payload["observation"]
        if value is not None:
            if type(value) is not dict:
                raise ValueError("D12-I01 event observation is invalid")
            observed = value
        previous = cast(str, payload["phase"])
    if previous != "ACCEPTED_IDENTIFIED" or observed != terminal_observation:
        raise ValueError("D12-I01 terminal event missing")
    return str(events[-1]["payload_digest"])


def _d12_i01_event(item: sqlite3.Row, binding: dict[str, object], journal_identity: str, sequence: int, previous: str | None, legal: dict[str, set[str]]) -> dict[str, object]:
    payload = json.loads(item["payload_json"])
    required = {"schema_id", "schema_version", "journal_identity", "binding_digest", "sequence", "phase", "observation", "event_digest"}
    if type(payload) is not dict or _canonical(payload) != item["payload_json"] or item["sequence"] != sequence or set(payload) != required:
        raise ValueError("D12-I01 event chain is invalid")
    unsigned = {key: value for key, value in payload.items() if key != "event_digest"}
    phase = payload["phase"]
    valid = (
        payload["schema_id"] == "manga_director.future_external_provider_submission_event",
        payload["schema_version"] == "1",
        payload["journal_identity"] == journal_identity,
        payload["binding_digest"] == binding["binding_digest"],
        payload["sequence"] == sequence,
        item["phase"] == phase,
        payload["event_digest"] == item["payload_digest"] == _digest(unsigned),
        type(phase) is str,
        (previous is None and phase == "DISPATCH_CONSUMED") or (previous is not None and phase in legal.get(previous, set())),
    )
    if not all(valid):
        raise ValueError("D12-I01 event chain is invalid")
    return cast(dict[str, object], payload)


def _receipt(source: dict[str, object]) -> tuple[dict[str, object], str]:
    projection = {"schema_id":"manga_director.future_external_accepted_submission_receipt", "schema_version":1, "source_projection_digest":_digest(source), "submission_journal_identity":source["submission_journal_identity"], "terminal_sequence":source["terminal_sequence"], "terminal_event_digest":source["terminal_event_digest"], "terminal_observation_digest":source["terminal_observation_digest"], "provider_reference":source["provider_reference"], "provider_job_identity":source["provider_job_identity"]}
    return projection, _digest(projection)


def _result_binding(source: dict[str, object]) -> dict[str, object]:
    receipt, receipt_identity = _receipt(source)
    source_digest = _digest(source)
    identity = _digest({"schema_id":"manga_director.future_external_provider_result_journal_identity","schema_version":1,"submission_receipt_identity":receipt_identity,"source_projection_digest":source_digest,"submission_journal_identity":source["submission_journal_identity"],"dispatch_identity":source["dispatch_identity"],"provider_reference":source["provider_reference"],"provider_job_identity":source["provider_job_identity"]})
    binding = {"schema_id":"manga_director.future_external_provider_result_binding","schema_version":1,"result_journal_identity":identity,"source_projection":source,"source_projection_digest":source_digest,"submission_receipt_projection":receipt,"submission_receipt_identity":receipt_identity,**source}
    binding["binding_digest"] = _digest(binding)
    return binding


class LocalFileExternalProviderResultJournal:
    """Private owner derivation only; result-journal lifecycle follows next patch."""

    def __init__(self, repository: LocalFileRepository) -> None:
        self._repository = repository
        self._database = _d12_i02_database(repository)
        self._initialize()
        self._lock = threading.Lock()
        self._issued: dict[object, tuple[str, str, int, bytes]] = {}
        self._tombstones: set[tuple[str, str, int]] = set()
        self._audit_lock = threading.Lock()
        self._audit_issued: dict[object, tuple[str, str, str, int, bytes]] = {}
        self._audit_tombstones: set[tuple[str, str, str, int]] = set()

    def _issue_observation_capability(self, journal: str, receipt: str, sequence: int) -> object:
        nonce = secrets.token_bytes(32)
        token = _ResultObservationCapability(journal, receipt, sequence, nonce)
        with self._lock:
            key = (journal, receipt, sequence)
            if key in self._tombstones:
                raise ValueError("normal authority consumed")
            self._issued[token] = (*key, nonce)
        return token

    def _consume_observation_capability(self, token: object) -> tuple[str, str, int] | None:
        if type(token) is not _ResultObservationCapability:
            return None
        with self._lock:
            record = self._issued.pop(token, None)
            if record is None or token.issuer is not _CAPABILITY_ISSUER or not secrets.compare_digest(token.nonce, record[3]):
                return None
            key = record[:3]
            if key in self._tombstones:
                return None
            self._tombstones.add(key)
            return key

    def _issue_audit_capability(self, journal: str, receipt: str, evidence: str, sequence: int) -> object:
        nonce = secrets.token_bytes(32)
        token = _PostAcceptAuditCapability(journal, receipt, evidence, sequence, nonce)
        with self._audit_lock:
            key = (journal, receipt, evidence, sequence)
            if key in self._audit_tombstones:
                raise ValueError("audit authority consumed")
            self._audit_issued[token] = (*key, nonce)
        return token

    def _consume_audit_capability(self, token: object) -> tuple[str, str, str, int] | None:
        if type(token) is not _PostAcceptAuditCapability:
            return None
        with self._audit_lock:
            record = self._audit_issued.pop(token, None)
            if record is None or token.issuer is not _AUDIT_CAPABILITY_ISSUER or not secrets.compare_digest(token.nonce, record[4]):
                return None
            key = record[:4]
            if key in self._audit_tombstones:
                return None
            self._audit_tombstones.add(key)
            return key

    def _append_event(self, connection: sqlite3.Connection, journal: str, receipt: str, binding_digest: str, sequence: int, previous: str, event_type: str, payload: dict[str, object]) -> str:
        if sequence < 0 or sequence >= _MAX_EVENTS or type(payload) is not dict:
            raise ValueError("invalid event")
        unsigned = {"schema_id":"manga_director.future_external_result_event", "schema_version":1, "result_journal_identity":journal, "submission_receipt_identity":receipt, "binding_digest":binding_digest, "sequence":sequence, "event_type":event_type, "previous_event_digest":previous, "payload":payload, "payload_digest":_digest(payload)}
        event = {**unsigned, "event_digest":_digest(unsigned)}
        if len(_canonical(event).encode()) > 8192:
            raise ValueError("event too large")
        connection.execute("INSERT INTO external_result_events VALUES (?, ?, ?, ?, ?)", (journal, sequence, event_type, _canonical(event), event["event_digest"]))
        return str(event["event_digest"])

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database, timeout=5.0, isolation_level=None)
        connection.row_factory = sqlite3.Row
        if str(connection.execute("PRAGMA journal_mode = DELETE").fetchone()[0]).lower() != "delete":
            connection.close()
            raise ValueError("D12-I02 journal mode is unavailable")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    def start(self, journal_identity: str) -> tuple[ResultJournalReport, object | None]:
        """Persist the normal start before issuing its private one-shot capability."""
        try:
            source = _read_accepted_source(self._repository, journal_identity)
            binding = _result_binding(source)
            connection = self._connect()
            try:
                connection.execute("BEGIN IMMEDIATE")
                self._validate_connection(connection)
                existing = connection.execute("SELECT binding_json,binding_digest FROM external_result_bindings WHERE result_journal_identity=?", (binding["result_journal_identity"],)).fetchone()
                if existing is not None:
                    if existing["binding_json"] != _canonical(binding) or existing["binding_digest"] != binding["binding_digest"]:
                        raise ValueError("result binding conflict")
                    state = self._replay(connection, source, binding)
                    connection.commit()
                    if state["phase"] == "RESULT_CAPTURE_STARTED":
                        return ResultJournalReport("RECOVERY_REQUIRED"), None
                    return self._report_from_state(connection, source, binding, state), None
                connection.execute(
                    "INSERT INTO external_result_bindings VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        binding["result_journal_identity"], binding["submission_journal_identity"], binding["submission_receipt_identity"],
                        _canonical(binding["source_projection"]), binding["source_projection_digest"],
                        _canonical(binding["submission_receipt_projection"]), _canonical(binding), binding["binding_digest"],
                    ),
                )
                digest = self._append_event(connection, str(binding["result_journal_identity"]), str(binding["submission_receipt_identity"]), str(binding["binding_digest"]), 0, "0" * 64, "RESULT_CAPTURE_STARTED", {})
                connection.execute("INSERT INTO external_result_state VALUES (?, ?, ?, ?, ?)", (binding["result_journal_identity"], "RESULT_CAPTURE_STARTED", "CAPTURE_IN_FLIGHT", 0, digest))
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                connection.close()
            # This is deliberately after commit: a registration failure leaves
            # durable recovery, never a replacement normal authority.
            token = self._issue_observation_capability(str(binding["result_journal_identity"]), str(binding["submission_receipt_identity"]), 0)
            return ResultJournalReport("RESULT_CAPTURE_STARTED"), token
        except Exception:
            return ResultJournalReport("CORRUPT"), None

    def capture(self, token: object, observation: object) -> ResultJournalReport:
        """Consume exactly one normal capability and durably terminalize it."""
        key = self._consume_observation_capability(token)
        if key is None:
            return ResultJournalReport("RESULT_NOT_AVAILABLE")
        journal, receipt_identity, expected_sequence = key
        try:
            locator = self._connect()
            try:
                self._validate_connection(locator)
                row = locator.execute("SELECT submission_journal_identity FROM external_result_bindings WHERE result_journal_identity=?", (journal,)).fetchone()
                if row is None:
                    raise ValueError("result binding is unavailable")
                submission_journal_identity = str(row["submission_journal_identity"])
            finally:
                locator.close()
            source = _read_accepted_source(self._repository, submission_journal_identity)
            binding = _result_binding(source)
            if binding["result_journal_identity"] != journal or binding["submission_receipt_identity"] != receipt_identity:
                raise ValueError("capability binding mismatch")
            connection = self._connect()
            try:
                connection.execute("BEGIN IMMEDIATE")
                self._validate_connection(connection)
                state = self._replay(connection, source, binding)
                if state["phase"] != "RESULT_CAPTURE_STARTED" or state["availability_gate"] != "CAPTURE_IN_FLIGHT" or int(state["sequence"]) != expected_sequence:
                    raise ValueError("normal capture is unavailable")
                if type(observation) is AcceptedObservationInputV1:
                    report = self._capture_accepted(connection, source, binding, state, observation)
                elif type(observation) is RejectedObservationInputV1:
                    report = self._capture_terminal(connection, binding, state, "RESULT_REJECTED", {"rejection_code": observation.rejection_code})
                elif type(observation) is AmbiguousObservationInputV1:
                    report = self._capture_terminal(connection, binding, state, "RESULT_AMBIGUOUS", {"reason_code": observation.reason_code})
                elif type(observation) is MalformedObservationInputV1:
                    report = self._capture_terminal(connection, binding, state, "RESULT_MALFORMED", {"failure_code": observation.failure_code})
                else:
                    raise ValueError("observation input is invalid")
                connection.commit()
                return report
            except Exception:
                connection.rollback()
                raise
            finally:
                connection.close()
        except Exception:
            # The tombstone intentionally remains, even when this transaction
            # fails before durable mutation.
            return ResultJournalReport("CORRUPT")

    def issue_post_accept_audit(self, submission_journal_identity: str) -> tuple[ResultJournalReport, object | None]:
        """Durably start one audit pair before issuing its separate capability."""
        try:
            source = _read_accepted_source(self._repository, submission_journal_identity)
            binding = _result_binding(source)
            connection = self._connect()
            try:
                connection.execute("BEGIN IMMEDIATE")
                self._validate_connection(connection)
                state = self._replay(connection, source, binding)
                if state["phase"] != "RESULT_CAPTURED" or state["availability_gate"] != "AUDIT_OPEN":
                    raise ValueError("audit is unavailable")
                count = connection.execute("SELECT COUNT(*) FROM external_result_events WHERE result_journal_identity=?", (binding["result_journal_identity"],)).fetchone()[0]
                if int(count) > 30:
                    connection.rollback()
                    return ResultJournalReport("AUDIT_EVENT_CAPACITY_EXHAUSTED"), None
                accepted = connection.execute("SELECT evidence_identity FROM external_result_accepted_results WHERE result_journal_identity=?", (binding["result_journal_identity"],)).fetchone()
                if accepted is None:
                    raise ValueError("accepted evidence missing")
                evidence_identity = str(accepted["evidence_identity"])
                completion = int(state["sequence"]) + 2
                nonce = secrets.token_bytes(32)
                issuance = _digest({"schema_id": "manga_director.future_external_audit_issuance", "schema_version": 1, "result_journal_identity": binding["result_journal_identity"], "submission_receipt_identity": binding["submission_receipt_identity"], "accepted_evidence_identity": evidence_identity, "expected_completion_sequence": completion, "nonce_hex": nonce.hex()})
                digest = self._append_event(connection, str(binding["result_journal_identity"]), str(binding["submission_receipt_identity"]), str(binding["binding_digest"]), int(state["sequence"]) + 1, str(state["last_event_digest"]), "POST_ACCEPT_AUDIT_STARTED", {"accepted_evidence_identity": evidence_identity, "expected_completion_sequence": completion, "issuance_audit_digest": issuance})
                updated = connection.execute("UPDATE external_result_state SET phase='POST_ACCEPT_AUDIT_STARTED',availability_gate='IN_FLIGHT',sequence=?,last_event_digest=? WHERE result_journal_identity=? AND sequence=?", (int(state["sequence"]) + 1, digest, binding["result_journal_identity"], state["sequence"]))
                if updated.rowcount != 1:
                    raise ValueError("audit start CAS failed")
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                connection.close()
            # Keep the committed issuance nonce exclusively process-local.
            token = _PostAcceptAuditCapability(str(binding["result_journal_identity"]), str(binding["submission_receipt_identity"]), evidence_identity, completion, nonce)
            with self._audit_lock:
                key = (str(binding["result_journal_identity"]), str(binding["submission_receipt_identity"]), evidence_identity, completion)
                if key in self._audit_tombstones:
                    raise ValueError("audit authority consumed")
                self._audit_issued[token] = (*key, nonce)
            return ResultJournalReport("POST_ACCEPT_AUDIT_STARTED"), token
        except Exception:
            return ResultJournalReport("CORRUPT"), None

    def audit(self, token: object, candidate: object) -> ResultJournalReport:
        key = self._consume_audit_capability(token)
        if key is None:
            return ResultJournalReport("RESULT_NOT_AVAILABLE")
        journal, receipt_identity, evidence_identity, completion = key
        try:
            locator = self._connect()
            try:
                self._validate_connection(locator)
                row = locator.execute("SELECT submission_journal_identity FROM external_result_bindings WHERE result_journal_identity=?", (journal,)).fetchone()
                if row is None:
                    raise ValueError("result binding is unavailable")
            finally:
                locator.close()
            source = _read_accepted_source(self._repository, str(row["submission_journal_identity"]))
            binding = _result_binding(source)
            if binding["result_journal_identity"] != journal or binding["submission_receipt_identity"] != receipt_identity:
                raise ValueError("audit binding mismatch")
            connection = self._connect()
            try:
                connection.execute("BEGIN IMMEDIATE")
                self._validate_connection(connection)
                state = self._replay(connection, source, binding)
                if state["phase"] != "POST_ACCEPT_AUDIT_STARTED" or state["availability_gate"] != "IN_FLIGHT" or int(state["sequence"]) + 1 != completion:
                    raise ValueError("audit completion is unavailable")
                accepted = self._accepted_evidence(connection, binding)
                if accepted.evidence_identity != evidence_identity:
                    raise ValueError("accepted evidence mismatch")
                report = self._complete_audit(connection, binding, state, accepted, candidate)
                connection.commit()
                return report
            except Exception:
                connection.rollback()
                raise
            finally:
                connection.close()
        except Exception:
            return ResultJournalReport("CORRUPT")

    def reopen(self, journal_identity: str) -> ResultJournalReport:
        try:
            source = _read_accepted_source(self._repository, journal_identity)
            binding = _result_binding(source)
            connection = self._connect()
            try:
                self._validate_connection(connection)
                state = self._replay(connection, source, binding)
                return self._report_from_state(connection, source, binding, state)
            finally:
                connection.close()
        except Exception:
            return ResultJournalReport("CORRUPT")

    def _capture_terminal(self, connection: sqlite3.Connection, binding: dict[str, object], state: sqlite3.Row, phase: str, payload: dict[str, object]) -> ResultJournalReport:
        sequence = int(state["sequence"]) + 1
        digest = self._append_event(connection, str(binding["result_journal_identity"]), str(binding["submission_receipt_identity"]), str(binding["binding_digest"]), sequence, str(state["last_event_digest"]), phase, payload)
        updated = connection.execute(
            "UPDATE external_result_state SET phase=?,availability_gate='CLOSED',sequence=?,last_event_digest=? WHERE result_journal_identity=? AND sequence=?",
            (phase, sequence, digest, binding["result_journal_identity"], state["sequence"]),
        )
        if updated.rowcount != 1:
            raise ValueError("state CAS failed")
        return ResultJournalReport(phase)

    def _capture_accepted(self, connection: sqlite3.Connection, source: dict[str, object], binding: dict[str, object], state: sqlite3.Row, observation: AcceptedObservationInputV1) -> ResultJournalReport:
        outputs = [item.model_dump(mode="json") for item in observation.outputs]
        sequence = int(state["sequence"]) + 1
        observation_identity = _observation_identity(str(binding["submission_receipt_identity"]), str(binding["source_projection_digest"]), "ACCEPTED", sequence)
        canonical, canonical_identity = _canonical_result(binding, outputs)
        unsigned = {
            "schema_id": _SCHEMA_ID,
            "schema_version": 1,
            "source_projection": binding["source_projection"],
            "source_projection_digest": binding["source_projection_digest"],
            "submission_receipt_projection": binding["submission_receipt_projection"],
            "submission_receipt_identity": binding["submission_receipt_identity"],
            "result_observation_identity": observation_identity,
            "canonical_result_projection": canonical,
            "canonical_result_identity": canonical_identity,
        }
        evidence_identity = _digest(unsigned)
        evidence = ExternalProviderResultEvidenceV1.model_validate({**unsigned, "evidence_identity": evidence_identity, "evidence_digest": evidence_identity})
        first = self._append_event(connection, str(binding["result_journal_identity"]), str(binding["submission_receipt_identity"]), str(binding["binding_digest"]), sequence, str(state["last_event_digest"]), "OBSERVATION_RECORDED", {"result_observation_identity": observation_identity, "evidence_digest": evidence.evidence_digest})
        connection.execute(
            "INSERT INTO external_result_accepted_results VALUES (?, ?, ?, ?, ?, ?)",
            (binding["result_journal_identity"], binding["submission_receipt_identity"], observation_identity, evidence.evidence_identity, evidence.model_dump_json(), evidence.evidence_digest),
        )
        second_sequence = sequence + 1
        second = self._append_event(connection, str(binding["result_journal_identity"]), str(binding["submission_receipt_identity"]), str(binding["binding_digest"]), second_sequence, first, "RESULT_CAPTURED", {"result_observation_identity": observation_identity, "evidence_identity": evidence.evidence_identity, "evidence_digest": evidence.evidence_digest})
        updated = connection.execute(
            "UPDATE external_result_state SET phase='RESULT_CAPTURED',availability_gate='AUDIT_OPEN',sequence=?,last_event_digest=? WHERE result_journal_identity=? AND sequence=?",
            (second_sequence, second, binding["result_journal_identity"], state["sequence"]),
        )
        if updated.rowcount != 1:
            raise ValueError("accepted state CAS failed")
        return ResultJournalReport("RESULT_CAPTURED", evidence)

    @staticmethod
    def _accepted_evidence(connection: sqlite3.Connection, binding: dict[str, object]) -> ExternalProviderResultEvidenceV1:
        row = connection.execute("SELECT evidence_json FROM external_result_accepted_results WHERE result_journal_identity=?", (binding["result_journal_identity"],)).fetchone()
        if row is None:
            raise ValueError("accepted evidence missing")
        return ExternalProviderResultEvidenceV1.model_validate_json(row["evidence_json"])

    def _complete_audit(self, connection: sqlite3.Connection, binding: dict[str, object], state: sqlite3.Row, accepted: ExternalProviderResultEvidenceV1, candidate: object) -> ResultJournalReport:
        try:
            parsed = PostAcceptCandidateProjectionV1.model_validate(candidate)
            source = cast(dict[str, object], binding["source_projection"])
            if parsed.provider_reference != source["provider_reference"] or parsed.provider_job_identity != source["provider_job_identity"]:
                return self._close_malformed_audit(connection, binding, state, accepted, "INVALID_BINDING")
            if parsed.provenance_assurance != "UNVERIFIED":
                return self._close_malformed_audit(connection, binding, state, accepted, "INVALID_PROVENANCE")
            projection = parsed.model_dump(mode="json")
            candidate_result, candidate_identity = _canonical_result(binding, list(projection["outputs"]))
            accepted_identity = accepted.canonical_result_identity
            if candidate_identity == accepted_identity:
                payload: dict[str, object] = {"accepted_evidence_identity": accepted.evidence_identity, "candidate_canonical_result_identity": candidate_identity, "comparison_result": "EQUIVALENT"}
                return self._complete_audit_event(connection, binding, state, "POST_ACCEPT_EQUIVALENT_RECORDED", payload, "RESULT_CAPTURED", "AUDIT_OPEN")
            differences = self._difference_codes(cast(list[dict[str, object]], accepted.canonical_result_projection["outputs"]), cast(list[dict[str, object]], projection["outputs"]))
            if not differences:
                raise ValueError("candidate contradiction lacks differences")
            payload = {"accepted_evidence_identity": accepted.evidence_identity, "accepted_canonical_result_identity": accepted_identity, "candidate_canonical_result_identity": candidate_identity, "candidate_projection": projection, "candidate_projection_digest": _digest(projection), "difference_codes": differences}
            return self._complete_audit_event(connection, binding, state, "CONFLICT_RECORDED", payload, "POST_ACCEPT_CONFLICT_RECORDED", "CLOSED")
        except ValueError:
            return self._close_malformed_audit(connection, binding, state, accepted, self._malformed_candidate_code(candidate))

    @staticmethod
    def _malformed_candidate_code(candidate: object) -> str:
        if type(candidate) is PostAcceptCandidateProjectionV1:
            return "INVALID_CANDIDATE_STRUCTURE"
        if type(candidate) is not dict or set(candidate) != {"provider_reference", "provider_job_identity", "provenance_assurance", "outputs"}:
            return "INVALID_CANDIDATE_STRUCTURE"
        if candidate.get("provenance_assurance") != "UNVERIFIED":
            return "INVALID_PROVENANCE"
        outputs = candidate["outputs"]
        if type(outputs) not in {list, tuple} or not 1 <= len(outputs) <= 4:
            return "INVALID_OUTPUT_SET"
        for output in outputs:
            failure = LocalFileExternalProviderResultJournal._output_failure(output)
            if failure is not None:
                return failure
        return "INVALID_CANDIDATE_STRUCTURE"

    @staticmethod
    def _output_failure(output: object) -> str | None:
        if type(output) is not dict or set(output) != {"logical_output_id", "sha256", "media_type", "byte_length", "metadata", "metadata_digest"}:
            return "INVALID_CANDIDATE_STRUCTURE"
        try:
            _logical(cast(str, output["logical_output_id"]), 96)
        except ValueError:
            return "INVALID_LOGICAL_OUTPUT_ID"
        if not LocalFileExternalProviderResultJournal._is_digest(output["sha256"]):
            return "INVALID_SHA256"
        if output["media_type"] not in {"image/png", "image/jpeg", "image/webp"}:
            return "INVALID_MEDIA_TYPE"
        if type(output["byte_length"]) is not int or not 1 <= output["byte_length"] <= 2147483647:
            return "INVALID_BYTE_LENGTH"
        try:
            metadata = _metadata(output["metadata"])
        except ValueError:
            return "INVALID_METADATA"
        return None if output["metadata_digest"] == _digest(metadata) else "INVALID_METADATA_DIGEST"

    def _close_malformed_audit(self, connection: sqlite3.Connection, binding: dict[str, object], state: sqlite3.Row, accepted: ExternalProviderResultEvidenceV1, failure_code: str) -> ResultJournalReport:
        return self._complete_audit_event(connection, binding, state, "POST_ACCEPT_MALFORMED_RECORDED", {"accepted_evidence_identity": accepted.evidence_identity, "failure_code": failure_code}, "POST_ACCEPT_MALFORMED_RECORDED", "CLOSED")

    def _complete_audit_event(self, connection: sqlite3.Connection, binding: dict[str, object], state: sqlite3.Row, event_type: str, payload: dict[str, object], phase: str, gate: str) -> ResultJournalReport:
        sequence = int(state["sequence"]) + 1
        digest = self._append_event(connection, str(binding["result_journal_identity"]), str(binding["submission_receipt_identity"]), str(binding["binding_digest"]), sequence, str(state["last_event_digest"]), event_type, payload)
        updated = connection.execute("UPDATE external_result_state SET phase=?,availability_gate=?,sequence=?,last_event_digest=? WHERE result_journal_identity=? AND sequence=?", (phase, gate, sequence, digest, binding["result_journal_identity"], state["sequence"]))
        if updated.rowcount != 1:
            raise ValueError("audit state CAS failed")
        return ResultJournalReport("RESULT_CAPTURED" if event_type == "POST_ACCEPT_EQUIVALENT_RECORDED" else "RESULT_AMBIGUOUS")

    @staticmethod
    def _difference_codes(accepted: list[dict[str, object]], candidate: list[dict[str, object]]) -> list[str]:
        old = {cast(str, item["logical_output_id"]): item for item in accepted}
        new = {cast(str, item["logical_output_id"]): item for item in candidate}
        differences: set[str] = set()
        if set(old) != set(new):
            differences.add("LOGICAL_OUTPUT_SET_CHANGED")
        for logical in set(old) & set(new):
            before, after = old[logical], new[logical]
            if before["sha256"] != after["sha256"]:
                differences.add("OUTPUT_SHA256_CHANGED")
            if before["media_type"] != after["media_type"]:
                differences.add("MEDIA_TYPE_CHANGED")
            if before["byte_length"] != after["byte_length"]:
                differences.add("BYTE_LENGTH_CHANGED")
            if before["metadata"] != after["metadata"] or before["metadata_digest"] != after["metadata_digest"]:
                differences.add("METADATA_CHANGED")
        return sorted(differences)

    def _validate_connection(self, connection: sqlite3.Connection) -> None:
        expected = {
            "external_result_schema_meta": "table",
            "external_result_bindings": "table",
            "external_result_state": "table",
            "external_result_events": "table",
            "external_result_accepted_results": "table",
            "ux_external_result_binding_submission_journal": "index",
            "ux_external_result_binding_submission_receipt": "index",
            "ux_external_result_accepted_receipt": "index",
            "ux_external_result_accepted_observation": "index",
        }
        actual = {row[0]: row[1] for row in connection.execute("SELECT name,type FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'")}
        meta = [tuple(row) for row in connection.execute("SELECT schema_id,schema_version FROM external_result_schema_meta").fetchall()]
        if int(connection.execute("PRAGMA user_version").fetchone()[0]) != 1 or actual != expected or meta != [(_SCHEMA_ID, 1)]:
            raise ValueError("D12-I02 schema is invalid")
        signatures = {
            "external_result_schema_meta": (("schema_id", "TEXT", True, None, 1), ("schema_version", "INTEGER", True, None, 0)),
            "external_result_bindings": (("result_journal_identity", "TEXT", True, None, 1), ("submission_journal_identity", "TEXT", True, None, 0), ("submission_receipt_identity", "TEXT", True, None, 0), ("source_projection_json", "TEXT", True, None, 0), ("source_projection_digest", "TEXT", True, None, 0), ("receipt_projection_json", "TEXT", True, None, 0), ("binding_json", "TEXT", True, None, 0), ("binding_digest", "TEXT", True, None, 0)),
            "external_result_state": (("result_journal_identity", "TEXT", True, None, 1), ("phase", "TEXT", True, None, 0), ("availability_gate", "TEXT", True, None, 0), ("sequence", "INTEGER", True, None, 0), ("last_event_digest", "TEXT", True, None, 0)),
            "external_result_events": (("result_journal_identity", "TEXT", True, None, 1), ("sequence", "INTEGER", True, None, 2), ("event_type", "TEXT", True, None, 0), ("event_json", "TEXT", True, None, 0), ("event_digest", "TEXT", True, None, 0)),
            "external_result_accepted_results": (("result_journal_identity", "TEXT", True, None, 1), ("submission_receipt_identity", "TEXT", True, None, 0), ("result_observation_identity", "TEXT", True, None, 0), ("evidence_identity", "TEXT", True, None, 0), ("evidence_json", "TEXT", True, None, 0), ("evidence_digest", "TEXT", True, None, 0)),
        }
        if any(_table_signature(connection, table) != signature for table, signature in signatures.items()):
            raise ValueError("D12-I02 table schema is invalid")
        expected_indexes = {
            "external_result_schema_meta": {"sqlite_autoindex_external_result_schema_meta_1": (True, "pk", False, ("schema_id",))},
            "external_result_bindings": {"sqlite_autoindex_external_result_bindings_1": (True, "pk", False, ("result_journal_identity",)), "ux_external_result_binding_submission_journal": (True, "c", False, ("submission_journal_identity",)), "ux_external_result_binding_submission_receipt": (True, "c", False, ("submission_receipt_identity",))},
            "external_result_state": {"sqlite_autoindex_external_result_state_1": (True, "pk", False, ("result_journal_identity",))},
            "external_result_events": {"sqlite_autoindex_external_result_events_1": (True, "pk", False, ("result_journal_identity", "sequence"))},
            "external_result_accepted_results": {"sqlite_autoindex_external_result_accepted_results_1": (True, "pk", False, ("result_journal_identity",)), "ux_external_result_accepted_receipt": (True, "c", False, ("submission_receipt_identity",)), "ux_external_result_accepted_observation": (True, "c", False, ("result_observation_identity",))},
        }
        if any(_index_signature(connection, table) != signature for table, signature in expected_indexes.items()):
            raise ValueError("D12-I02 index schema is invalid")

    def _replay(self, connection: sqlite3.Connection, source: dict[str, object], binding: dict[str, object]) -> sqlite3.Row:
        journal = str(binding["result_journal_identity"])
        row = connection.execute("SELECT * FROM external_result_bindings WHERE result_journal_identity=?", (journal,)).fetchone()
        if row is None or row["binding_json"] != _canonical(binding) or row["binding_digest"] != binding["binding_digest"] or row["source_projection_json"] != _canonical(source) or row["source_projection_digest"] != binding["source_projection_digest"] or row["receipt_projection_json"] != _canonical(binding["submission_receipt_projection"]):
            raise ValueError("binding replay mismatch")
        state = connection.execute("SELECT * FROM external_result_state WHERE result_journal_identity=?", (journal,)).fetchone()
        events = connection.execute("SELECT * FROM external_result_events WHERE result_journal_identity=? ORDER BY sequence", (journal,)).fetchall()
        if state is None or not events or len(events) > _MAX_EVENTS or len(events) != int(state["sequence"]) + 1:
            raise ValueError("event sequence is invalid")
        phase = ""
        previous = "0" * 64
        accepted_events: list[dict[str, object]] = []
        replayed_events: list[dict[str, object]] = []
        legal = {
            "": {"RESULT_CAPTURE_STARTED"},
            "RESULT_CAPTURE_STARTED": {"OBSERVATION_RECORDED", "RESULT_REJECTED", "RESULT_AMBIGUOUS", "RESULT_MALFORMED"},
            "OBSERVATION_RECORDED": {"RESULT_CAPTURED"},
            "RESULT_CAPTURED": {"POST_ACCEPT_AUDIT_STARTED"},
            "POST_ACCEPT_AUDIT_STARTED": {"POST_ACCEPT_EQUIVALENT_RECORDED", "CONFLICT_RECORDED", "POST_ACCEPT_MALFORMED_RECORDED"},
            "POST_ACCEPT_CONFLICT_RECORDED": set(),
            "POST_ACCEPT_MALFORMED_RECORDED": set(),
            "RESULT_REJECTED": set(),
            "RESULT_AMBIGUOUS": set(),
            "RESULT_MALFORMED": set(),
        }
        resulting_phase = {"POST_ACCEPT_EQUIVALENT_RECORDED": "RESULT_CAPTURED", "CONFLICT_RECORDED": "POST_ACCEPT_CONFLICT_RECORDED"}
        for sequence, item in enumerate(events):
            event = self._event_from_row(item, journal, binding, sequence, previous)
            event_type = self._validated_event_type(event, phase, legal)
            if event_type == "RESULT_CAPTURED":
                accepted_events.append(event)
            replayed_events.append(event)
            phase, previous = resulting_phase.get(event_type, event_type), str(event["event_digest"])
        gate = {"RESULT_CAPTURE_STARTED": "CAPTURE_IN_FLIGHT", "RESULT_CAPTURED": "AUDIT_OPEN", "POST_ACCEPT_AUDIT_STARTED": "IN_FLIGHT", "POST_ACCEPT_CONFLICT_RECORDED": "CLOSED", "POST_ACCEPT_MALFORMED_RECORDED": "CLOSED", "RESULT_REJECTED": "CLOSED", "RESULT_AMBIGUOUS": "CLOSED", "RESULT_MALFORMED": "CLOSED"}.get(phase)
        if phase != state["phase"] or gate != state["availability_gate"] or previous != state["last_event_digest"]:
            raise ValueError("state replay mismatch")
        accepted = connection.execute("SELECT * FROM external_result_accepted_results WHERE result_journal_identity=?", (journal,)).fetchone()
        if phase in {"RESULT_CAPTURED", "POST_ACCEPT_AUDIT_STARTED", "POST_ACCEPT_CONFLICT_RECORDED", "POST_ACCEPT_MALFORMED_RECORDED"}:
            if accepted is None or len(accepted_events) != 1:
                raise ValueError("accepted result is missing")
            evidence = ExternalProviderResultEvidenceV1.model_validate_json(accepted["evidence_json"])
            captured = accepted_events[0]["payload"]
            if evidence.source_projection != binding["source_projection"] or evidence.source_projection_digest != binding["source_projection_digest"] or evidence.submission_receipt_projection != binding["submission_receipt_projection"] or evidence.submission_receipt_identity != binding["submission_receipt_identity"] or accepted["submission_receipt_identity"] != binding["submission_receipt_identity"] or accepted["result_observation_identity"] != evidence.result_observation_identity or accepted["evidence_identity"] != evidence.evidence_identity or accepted["evidence_digest"] != evidence.evidence_digest or captured != {"result_observation_identity": evidence.result_observation_identity, "evidence_identity": evidence.evidence_identity, "evidence_digest": evidence.evidence_digest}:
                raise ValueError("accepted three-way binding mismatch")
            self._validate_audit_history(replayed_events, evidence, binding)
        elif accepted is not None or accepted_events:
            raise ValueError("accepted row is structurally invalid")
        return cast(sqlite3.Row, state)

    def _validate_audit_history(self, events: list[dict[str, object]], evidence: ExternalProviderResultEvidenceV1, binding: dict[str, object]) -> None:
        starts = [index for index, event in enumerate(events) if event["event_type"] == "POST_ACCEPT_AUDIT_STARTED"]
        for index in starts:
            started = cast(dict[str, object], events[index]["payload"])
            if started["accepted_evidence_identity"] != evidence.evidence_identity or started["expected_completion_sequence"] != index + 1 or not self._is_digest(started["issuance_audit_digest"]):
                raise ValueError("audit start payload is invalid")
            if index == len(events) - 1:
                continue
            completion = events[index + 1]
            payload = cast(dict[str, object], completion["payload"])
            if completion["event_type"] not in {"POST_ACCEPT_EQUIVALENT_RECORDED", "CONFLICT_RECORDED", "POST_ACCEPT_MALFORMED_RECORDED"} or completion["sequence"] != started["expected_completion_sequence"] or payload["accepted_evidence_identity"] != evidence.evidence_identity:
                raise ValueError("audit pair is invalid")
            if completion["event_type"] == "POST_ACCEPT_EQUIVALENT_RECORDED":
                if payload["candidate_canonical_result_identity"] != evidence.canonical_result_identity or payload["comparison_result"] != "EQUIVALENT":
                    raise ValueError("equivalent audit is invalid")
            elif completion["event_type"] == "CONFLICT_RECORDED":
                self._validate_conflict_payload(payload, evidence, binding)
            elif payload["failure_code"] not in {"INVALID_CANDIDATE_STRUCTURE", "INVALID_OUTPUT_SET", "INVALID_LOGICAL_OUTPUT_ID", "INVALID_SHA256", "INVALID_MEDIA_TYPE", "INVALID_BYTE_LENGTH", "INVALID_METADATA", "INVALID_METADATA_DIGEST", "INVALID_PROVENANCE", "INVALID_BINDING", "INVALID_OBSERVATION_IDENTITY"}:
                raise ValueError("malformed audit is invalid")

    @staticmethod
    def _is_digest(value: object) -> bool:
        try:
            _sha256(cast(str, value))
        except ValueError:
            return False
        return True

    def _validate_conflict_payload(self, payload: dict[str, object], evidence: ExternalProviderResultEvidenceV1, binding: dict[str, object]) -> None:
        if payload["accepted_canonical_result_identity"] != evidence.canonical_result_identity:
            raise ValueError("accepted result identity is invalid")
        projection = PostAcceptCandidateProjectionV1.model_validate(payload["candidate_projection"])
        canonical = projection.model_dump(mode="json")
        source = cast(dict[str, object], binding["source_projection"])
        if canonical["provider_reference"] != source["provider_reference"] or canonical["provider_job_identity"] != source["provider_job_identity"] or canonical["provenance_assurance"] != "UNVERIFIED" or payload["candidate_projection_digest"] != _digest(canonical):
            raise ValueError("candidate binding is invalid")
        _, identity = _canonical_result(binding, cast(list[dict[str, object]], canonical["outputs"]))
        codes = self._difference_codes(cast(list[dict[str, object]], evidence.canonical_result_projection["outputs"]), cast(list[dict[str, object]], canonical["outputs"]))
        if payload["candidate_canonical_result_identity"] != identity or identity == evidence.canonical_result_identity or payload["difference_codes"] != codes or not codes:
            raise ValueError("conflict audit is invalid")

    @staticmethod
    def _event_from_row(item: sqlite3.Row, journal: str, binding: dict[str, object], sequence: int, previous: str) -> dict[str, object]:
        try:
            event = json.loads(item["event_json"])
        except (TypeError, json.JSONDecodeError) as error:
            raise ValueError("event JSON is invalid") from error
        required = {"schema_id", "schema_version", "result_journal_identity", "submission_receipt_identity", "binding_digest", "sequence", "event_type", "previous_event_digest", "payload", "payload_digest", "event_digest"}
        if type(event) is not dict or set(event) != required:
            raise ValueError("event envelope is invalid")
        unsigned = {key: value for key, value in event.items() if key != "event_digest"}
        identity_fields = (
            event["schema_id"] == _EVENT_SCHEMA_ID,
            event["schema_version"] == 1,
            event["result_journal_identity"] == journal,
            event["submission_receipt_identity"] == binding["submission_receipt_identity"],
            event["binding_digest"] == binding["binding_digest"],
            event["sequence"] == sequence == item["sequence"],
            event["event_type"] == item["event_type"],
            event["previous_event_digest"] == previous,
        )
        integrity_fields = (
            type(event["payload"]) is dict,
            event["payload_digest"] == _digest(event["payload"]),
            event["event_digest"] == _digest(unsigned) == item["event_digest"],
            len(_canonical(event).encode("utf-8")) <= _MAX_EVENT_BYTES,
        )
        if not all(identity_fields) or not all(integrity_fields):
            raise ValueError("event integrity is invalid")
        return cast(dict[str, object], event)

    @staticmethod
    def _validated_event_type(event: dict[str, object], phase: str, legal: dict[str, set[str]]) -> str:
        event_type = event["event_type"]
        if type(event_type) is not str or event_type not in legal[phase]:
            raise ValueError("event transition is invalid")
        payload = cast(dict[str, object], event["payload"])
        expected = {
            "RESULT_CAPTURE_STARTED": set(),
            "OBSERVATION_RECORDED": {"result_observation_identity", "evidence_digest"},
            "RESULT_CAPTURED": {"result_observation_identity", "evidence_identity", "evidence_digest"},
            "RESULT_REJECTED": {"rejection_code"},
            "RESULT_AMBIGUOUS": {"reason_code"},
            "RESULT_MALFORMED": {"failure_code"},
            "POST_ACCEPT_AUDIT_STARTED": {"accepted_evidence_identity", "expected_completion_sequence", "issuance_audit_digest"},
            "POST_ACCEPT_EQUIVALENT_RECORDED": {"accepted_evidence_identity", "candidate_canonical_result_identity", "comparison_result"},
            "CONFLICT_RECORDED": {"accepted_evidence_identity", "accepted_canonical_result_identity", "candidate_canonical_result_identity", "candidate_projection", "candidate_projection_digest", "difference_codes"},
            "POST_ACCEPT_MALFORMED_RECORDED": {"accepted_evidence_identity", "failure_code"},
        }
        if set(payload) != expected[event_type]:
            raise ValueError("event payload is invalid")
        required_codes = {
            "RESULT_REJECTED": ("rejection_code", {"SYNTHETIC_REJECTED"}),
            "RESULT_AMBIGUOUS": ("reason_code", {"SYNTHETIC_OBSERVATION_AMBIGUOUS"}),
            "RESULT_MALFORMED": ("failure_code", {"SYNTHETIC_MALFORMED", "INVALID_OUTPUT", "INVALID_METADATA"}),
        }
        if event_type in required_codes:
            name, permitted = required_codes[event_type]
            if payload.get(name) not in permitted:
                raise ValueError("terminal outcome code is invalid")
        return event_type

    def _report_from_state(self, connection: sqlite3.Connection, source: dict[str, object], binding: dict[str, object], state: sqlite3.Row) -> ResultJournalReport:
        phase = str(state["phase"])
        if phase in {"RESULT_CAPTURE_STARTED", "POST_ACCEPT_AUDIT_STARTED"}:
            return ResultJournalReport("RECOVERY_REQUIRED")
        if phase == "RESULT_CAPTURED":
            row = connection.execute("SELECT evidence_json FROM external_result_accepted_results WHERE result_journal_identity=?", (binding["result_journal_identity"],)).fetchone()
            if row is None:
                raise ValueError("accepted evidence missing")
            return ResultJournalReport("RESULT_CAPTURED", ExternalProviderResultEvidenceV1.model_validate_json(row["evidence_json"]))
        if phase in {"POST_ACCEPT_CONFLICT_RECORDED", "POST_ACCEPT_MALFORMED_RECORDED"}:
            return ResultJournalReport("RESULT_AMBIGUOUS")
        if phase in {"RESULT_REJECTED", "RESULT_AMBIGUOUS", "RESULT_MALFORMED"}:
            return ResultJournalReport(phase)
        raise ValueError("unknown journal phase")

    def _initialize(self) -> None:
        owner = self._database.parent
        if self._database.exists():
            self._validate_existing()
            return
        if owner.exists() and any(owner.iterdir()):
            raise ValueError("D12-I02 owner is not empty")
        owner.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._database)
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.executescript("CREATE TABLE external_result_schema_meta (schema_id TEXT NOT NULL PRIMARY KEY, schema_version INTEGER NOT NULL); CREATE TABLE external_result_bindings (result_journal_identity TEXT NOT NULL PRIMARY KEY, submission_journal_identity TEXT NOT NULL, submission_receipt_identity TEXT NOT NULL, source_projection_json TEXT NOT NULL, source_projection_digest TEXT NOT NULL, receipt_projection_json TEXT NOT NULL, binding_json TEXT NOT NULL, binding_digest TEXT NOT NULL); CREATE UNIQUE INDEX ux_external_result_binding_submission_journal ON external_result_bindings(submission_journal_identity); CREATE UNIQUE INDEX ux_external_result_binding_submission_receipt ON external_result_bindings(submission_receipt_identity); CREATE TABLE external_result_state (result_journal_identity TEXT NOT NULL PRIMARY KEY, phase TEXT NOT NULL, availability_gate TEXT NOT NULL, sequence INTEGER NOT NULL, last_event_digest TEXT NOT NULL); CREATE TABLE external_result_events (result_journal_identity TEXT NOT NULL, sequence INTEGER NOT NULL, event_type TEXT NOT NULL, event_json TEXT NOT NULL, event_digest TEXT NOT NULL, PRIMARY KEY (result_journal_identity, sequence)); CREATE TABLE external_result_accepted_results (result_journal_identity TEXT NOT NULL PRIMARY KEY, submission_receipt_identity TEXT NOT NULL, result_observation_identity TEXT NOT NULL, evidence_identity TEXT NOT NULL, evidence_json TEXT NOT NULL, evidence_digest TEXT NOT NULL); CREATE UNIQUE INDEX ux_external_result_accepted_receipt ON external_result_accepted_results(submission_receipt_identity); CREATE UNIQUE INDEX ux_external_result_accepted_observation ON external_result_accepted_results(result_observation_identity);")
            connection.execute("INSERT INTO external_result_schema_meta VALUES (?, 1)", ("manga_director.future_external_provider_result_evidence",))
            connection.execute("PRAGMA user_version = 1")
            connection.commit()
        finally:
            connection.close()

    def _validate_existing(self) -> None:
        connection = sqlite3.connect(self._database)
        try:
            self._validate_connection(connection)
        finally:
            connection.close()
