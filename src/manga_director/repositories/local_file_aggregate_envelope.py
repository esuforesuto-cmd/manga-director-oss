"""Private R27 aggregate-envelope codec; it has no workflow or CAS authority."""

from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import cast

_MAGIC = bytes.fromhex("894D445232370D0A")
_FRAME_VERSION = 1
_HEADER_LENGTH = 9
_ENVELOPE_SCHEMA = "manga_director.localfile.aggregate-envelope"
_ENVELOPE_VERSION = 2
_PAYLOAD_ENCODING = "base64-utf8-v1"
_WITNESS_SCHEMA = "manga_director.r27.same-cas-witness"
_WITNESS_VERSION = 1
_WITNESS_PROTOCOL_VERSION = 1

_TOP_LEVEL_KEYS = frozenset(
    {
        "authoritative_envelope_fingerprint",
        "envelope_schema",
        "envelope_version",
        "payload_encoding",
        "project_payload",
        "same_cas_witness",
    }
)
_WITNESS_KEYS = frozenset(
    {
        "aggregate_publication_identity",
        "application_binding_identity",
        "canonical_project_payload_digest",
        "expected_aggregate_fingerprint",
        "expected_revision",
        "pending_lineage_digest",
        "pending_lineage_identity",
        "protocol_version",
        "resulting_revision",
        "same_cas_witness_id",
        "schema",
        "version",
    }
)
_WITNESS_INPUT_KEYS = _WITNESS_KEYS - {
    "aggregate_publication_identity",
    "canonical_project_payload_digest",
    "same_cas_witness_id",
}
_SHA256_WITNESS_KEYS = frozenset(
    {
        "aggregate_publication_identity",
        "application_binding_identity",
        "canonical_project_payload_digest",
        "expected_aggregate_fingerprint",
        "pending_lineage_digest",
        "pending_lineage_identity",
        "same_cas_witness_id",
    }
)


class _AggregateEnvelopeCorruptError(ValueError):
    """Raised when aggregate bytes are not one exact valid representation."""


@dataclass(frozen=True)
class _R27AggregateEnvelope:
    project_payload: bytes
    authoritative_envelope_fingerprint: str
    witness: Mapping[str, object]


def _build_r27_aggregate(project_payload: bytes, witness_inputs: Mapping[str, object]) -> bytes:
    """Return canonical framed bytes from private, non-authoritative inputs."""

    if not isinstance(project_payload, bytes) or not project_payload:
        raise _corrupt()
    try:
        project_payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise _corrupt() from error
    if set(witness_inputs) != _WITNESS_INPUT_KEYS:
        raise _corrupt()

    witness: dict[str, object] = dict(witness_inputs)
    witness["canonical_project_payload_digest"] = _sha256(project_payload)
    _validate_witness_fields(witness, require_identities=False)

    publication_body = _unsigned_publication_body(project_payload, witness)
    witness["aggregate_publication_identity"] = _sha256(_canonical_json_bytes(publication_body))
    witness["same_cas_witness_id"] = _sha256(_canonical_json_bytes(_witness_identity_body(witness)))
    _validate_witness_fields(witness, require_identities=True)

    envelope_without_f1: dict[str, object] = {
        "envelope_schema": _ENVELOPE_SCHEMA,
        "envelope_version": _ENVELOPE_VERSION,
        "payload_encoding": _PAYLOAD_ENCODING,
        "project_payload": base64.b64encode(project_payload).decode("ascii"),
        "same_cas_witness": witness,
    }
    envelope = {
        "authoritative_envelope_fingerprint": _sha256(_canonical_json_bytes(envelope_without_f1)),
        **envelope_without_f1,
    }
    return _MAGIC + bytes((_FRAME_VERSION,)) + _canonical_json_bytes(envelope)


def _project_payload_from_aggregate(aggregate_bytes: bytes) -> bytes:
    """Return exact legacy bytes or validated R27 payload bytes for the held serializer."""

    envelope = _decode_r27_aggregate(aggregate_bytes)
    if envelope is not None:
        return envelope.project_payload
    try:
        aggregate_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise _corrupt() from error
    return aggregate_bytes


def _decode_r27_aggregate(aggregate_bytes: bytes) -> _R27AggregateEnvelope | None:
    """Classify exact bytes without parsing or normalizing an unframed aggregate."""

    if not isinstance(aggregate_bytes, bytes):
        raise _corrupt()
    if aggregate_bytes.startswith(_MAGIC):
        if len(aggregate_bytes) <= _HEADER_LENGTH - 1 or aggregate_bytes[8] != _FRAME_VERSION:
            raise _corrupt()
        body = aggregate_bytes[_HEADER_LENGTH:]
        if not body:
            raise _corrupt()
        return _decode_envelope_body(body)
    if _MAGIC.startswith(aggregate_bytes) or aggregate_bytes.startswith(b"\x89"):
        raise _corrupt()
    return None


def _physical_fingerprint(aggregate_bytes: bytes) -> str:
    """Return F0 over the complete persisted aggregate-file byte sequence."""

    if not isinstance(aggregate_bytes, bytes):
        raise _corrupt()
    return _sha256(aggregate_bytes)


def _validate_revision_binding(
    aggregate_bytes: bytes,
    *,
    record_project_id: str,
    record_revision: int,
    record_fingerprint: str,
    project_id_reader: Callable[[bytes], str],
) -> None:
    """Validate Model A binding without writing, promoting, or reconstructing authority."""

    envelope = _decode_r27_aggregate(aggregate_bytes)
    if envelope is None or not _is_sha256(record_fingerprint):
        raise _corrupt()
    if type(record_revision) is not int or record_revision < 1 or not record_project_id:
        raise _corrupt()
    if _physical_fingerprint(aggregate_bytes) != record_fingerprint:
        raise _corrupt()
    try:
        project_id = project_id_reader(envelope.project_payload)
    except Exception as error:
        raise _corrupt() from error
    if not isinstance(project_id, str) or project_id != record_project_id:
        raise _corrupt()
    witness = envelope.witness
    if witness["resulting_revision"] != record_revision:
        raise _corrupt()


def _decode_envelope_body(body: bytes) -> _R27AggregateEnvelope:
    value = _parse_canonical_json_object(body)
    if set(value) != _TOP_LEVEL_KEYS:
        raise _corrupt()
    if value.get("envelope_schema") != _ENVELOPE_SCHEMA:
        raise _corrupt()
    if type(value.get("envelope_version")) is not int or value["envelope_version"] != _ENVELOPE_VERSION:
        raise _corrupt()
    if value.get("payload_encoding") != _PAYLOAD_ENCODING:
        raise _corrupt()
    project_payload = _decode_project_payload(value.get("project_payload"))
    fingerprint = value.get("authoritative_envelope_fingerprint")
    if not _is_sha256(fingerprint):
        raise _corrupt()
    witness = value.get("same_cas_witness")
    if not isinstance(witness, dict):
        raise _corrupt()
    _validate_witness_fields(witness, require_identities=True)

    expected_payload_digest = _sha256(project_payload)
    if witness["canonical_project_payload_digest"] != expected_payload_digest:
        raise _corrupt()
    if witness["aggregate_publication_identity"] != _sha256(
        _canonical_json_bytes(_unsigned_publication_body(project_payload, witness))
    ):
        raise _corrupt()
    if witness["same_cas_witness_id"] != _sha256(_canonical_json_bytes(_witness_identity_body(witness))):
        raise _corrupt()
    fingerprint_body = {key: item for key, item in value.items() if key != "authoritative_envelope_fingerprint"}
    if fingerprint != _sha256(_canonical_json_bytes(fingerprint_body)):
        raise _corrupt()
    return _R27AggregateEnvelope(
        project_payload=project_payload,
        authoritative_envelope_fingerprint=fingerprint,
        witness=witness,
    )


def _unsigned_publication_body(project_payload: bytes, witness: Mapping[str, object]) -> dict[str, object]:
    return {
        "envelope_schema": _ENVELOPE_SCHEMA,
        "envelope_version": _ENVELOPE_VERSION,
        "payload_encoding": _PAYLOAD_ENCODING,
        "project_payload": base64.b64encode(project_payload).decode("ascii"),
        "same_cas_witness": {
            key: value
            for key, value in witness.items()
            if key not in {"aggregate_publication_identity", "same_cas_witness_id"}
        },
    }


def _witness_identity_body(witness: Mapping[str, object]) -> dict[str, object]:
    return {key: value for key, value in witness.items() if key != "same_cas_witness_id"}


def _validate_witness_fields(witness: Mapping[str, object], *, require_identities: bool) -> None:
    required = _WITNESS_KEYS if require_identities else _WITNESS_KEYS - {
        "aggregate_publication_identity",
        "same_cas_witness_id",
    }
    if set(witness) != required:
        raise _corrupt()
    for key in _SHA256_WITNESS_KEYS:
        if key in witness and not _is_sha256(witness[key]):
            raise _corrupt()
    if witness.get("schema") != _WITNESS_SCHEMA or witness.get("version") != _WITNESS_VERSION:
        raise _corrupt()
    if witness.get("protocol_version") != _WITNESS_PROTOCOL_VERSION:
        raise _corrupt()
    expected_revision = witness.get("expected_revision")
    resulting_revision = witness.get("resulting_revision")
    if (
        type(expected_revision) is not int
        or type(resulting_revision) is not int
        or expected_revision < 1
        or resulting_revision != expected_revision + 1
    ):
        raise _corrupt()


def _decode_project_payload(value: object) -> bytes:
    if not isinstance(value, str):
        raise _corrupt()
    try:
        encoded = value.encode("ascii")
        decoded = base64.b64decode(encoded, validate=True)
        decoded.decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError, ValueError) as error:
        raise _corrupt() from error
    if not decoded or base64.b64encode(decoded) != encoded:
        raise _corrupt()
    return decoded


def _parse_canonical_json_object(body: bytes) -> dict[str, object]:
    if body.startswith(b"\xef\xbb\xbf"):
        raise _corrupt()
    try:
        text = body.decode("utf-8")
        value = json.loads(
            text,
            object_pairs_hook=_no_duplicate_keys,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise _corrupt() from error
    if not isinstance(value, dict) or _canonical_json_bytes(value) != body:
        raise _corrupt()
    return cast(dict[str, object], value)


def _canonical_json_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, UnicodeEncodeError, ValueError) as error:
        raise _corrupt() from error


def _no_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _corrupt()
        result[key] = value
    return result


def _reject_float(value: str) -> object:
    del value
    raise _corrupt()


def _reject_constant(value: str) -> object:
    del value
    raise _corrupt()


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _corrupt() -> _AggregateEnvelopeCorruptError:
    return _AggregateEnvelopeCorruptError("r27_aggregate_corrupt")
