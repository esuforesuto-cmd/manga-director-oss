from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from manga_director.domain.project import Project
from manga_director.repositories import local_file_aggregate_envelope as envelope
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.repositories.local_file_durability import LocalFileDurabilityError
from manga_director.repositories.serializer import ProjectSerializer


def _project() -> Project:
    return Project(
        id="r27-vector",
        title="R27 vector",
        created_at="2024-01-02T03:04:05Z",
        updated_at="2024-01-02T03:04:05Z",
    )


def _witness_inputs() -> dict[str, object]:
    return {
        "application_binding_identity": "3" * 64,
        "expected_aggregate_fingerprint": "4" * 64,
        "expected_revision": 7,
        "pending_lineage_digest": "2" * 64,
        "pending_lineage_identity": "1" * 64,
        "protocol_version": 1,
        "resulting_revision": 8,
        "schema": "manga_director.r27.same-cas-witness",
        "version": 1,
    }


def _aggregate() -> bytes:
    return envelope._build_r27_aggregate(ProjectSerializer().dumps(_project()).encode("utf-8"), _witness_inputs())


def _write_revision_record(
    repository: LocalFileRepository,
    *,
    project_id: str,
    aggregate: bytes,
    revision: int,
    record_project_id: str | None = None,
) -> Path:
    path = repository._revision_store._committed_path(project_id)
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "fingerprint": envelope._physical_fingerprint(aggregate),
                "project_id": record_project_id or project_id,
                "revision": revision,
                "schema_version": 1,
            }
        ),
        encoding="utf-8",
    )
    return path


def test_normative_vector_has_exact_frame_f0_and_f1() -> None:
    aggregate = _aggregate()
    decoded = envelope._decode_r27_aggregate(aggregate)

    assert decoded is not None
    assert aggregate[:9] == bytes.fromhex("894D445232370D0A01")
    assert len(aggregate) == 1369
    assert envelope._physical_fingerprint(aggregate) == (
        "f6c2cb05ef2ef0434818b3a893bf86082f34931931fbd0656dc04829dde6af80"
    )
    assert decoded.authoritative_envelope_fingerprint == (
        "72b0527384c184f7d3e417caefd9004051af385290cdbadd2f8a25cf40c92a8a"
    )


def test_framed_aggregate_loads_through_private_localfile_read_path(tmp_path: Path) -> None:
    repository = LocalFileRepository(tmp_path)
    path = tmp_path / "projects" / "r27-vector.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(_aggregate())

    assert repository.load("r27-vector") == _project()
    assert repository.list() == [_project()]


def test_revisioned_r27_reopen_requires_existing_record_without_mutation(tmp_path: Path) -> None:
    repository = LocalFileRepository(tmp_path)
    aggregate = _aggregate()
    path = tmp_path / "projects" / "r27-vector.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(aggregate)

    with pytest.raises(LocalFileDurabilityError, match="r27_revision_record_required"):
        repository._load_revisioned("r27-vector")

    assert path.read_bytes() == aggregate
    assert not (tmp_path / "projects" / "_durability").exists()


def test_revisioned_r27_reopen_validates_model_a_without_mutation(tmp_path: Path) -> None:
    repository = LocalFileRepository(tmp_path)
    aggregate = _aggregate()
    path = tmp_path / "projects" / "r27-vector.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(aggregate)
    record_path = _write_revision_record(
        repository,
        project_id="r27-vector",
        aggregate=aggregate,
        revision=8,
    )
    record_before = record_path.read_bytes()

    snapshot = repository._load_revisioned("r27-vector")

    assert snapshot.project == _project()
    assert snapshot.revision == 8
    assert snapshot.fingerprint == envelope._physical_fingerprint(aggregate)
    assert path.read_bytes() == aggregate
    assert record_path.read_bytes() == record_before


@pytest.mark.parametrize(
    ("record_aggregate", "revision", "record_project_id", "error"),
    [
        (_aggregate(), 7, "r27-vector", "r27_aggregate_corrupt"),
        (_aggregate(), 8, "other-project", "revision_record_binding_invalid"),
        (
            envelope._build_r27_aggregate(
                ProjectSerializer().dumps(_project()).encode("utf-8"),
                {**_witness_inputs(), "application_binding_identity": "5" * 64},
            ),
            8,
            "r27-vector",
            "authoritative_fingerprint_mismatch",
        ),
    ],
)
def test_revisioned_r27_reopen_rejects_cross_binding_without_mutation(
    tmp_path: Path,
    record_aggregate: bytes,
    revision: int,
    record_project_id: str,
    error: str,
) -> None:
    repository = LocalFileRepository(tmp_path)
    aggregate = _aggregate()
    path = tmp_path / "projects" / "r27-vector.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(aggregate)
    record_path = _write_revision_record(
        repository,
        project_id="r27-vector",
        aggregate=record_aggregate,
        revision=revision,
        record_project_id=record_project_id,
    )
    record_before = record_path.read_bytes()

    with pytest.raises(
        (LocalFileDurabilityError, envelope._AggregateEnvelopeCorruptError), match=error
    ):
        repository._load_revisioned("r27-vector")

    assert path.read_bytes() == aggregate
    assert record_path.read_bytes() == record_before


@pytest.mark.parametrize(
    "aggregate",
    [
        bytes.fromhex("894D445232370D0A"),
        bytes.fromhex("894D445232370D0A02"),
        bytes.fromhex("894D445232370D0A01") + b"{",
    ],
)
def test_revisioned_corrupt_r27_never_initializes_legacy_record(tmp_path: Path, aggregate: bytes) -> None:
    repository = LocalFileRepository(tmp_path)
    path = tmp_path / "projects" / "r27-vector.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(aggregate)

    with pytest.raises(envelope._AggregateEnvelopeCorruptError, match="r27_aggregate_corrupt"):
        repository._load_revisioned("r27-vector")

    assert path.read_bytes() == aggregate
    assert not (tmp_path / "projects" / "_durability").exists()


def test_legacy_bytes_are_read_without_rewrite(tmp_path: Path) -> None:
    repository = LocalFileRepository(tmp_path)
    repository.save(_project())
    path = tmp_path / "projects" / "r27-vector.json"
    before = path.read_bytes()

    assert repository.load("r27-vector") == _project()
    assert repository.list() == [_project()]
    assert path.read_bytes() == before
    assert not before.startswith(bytes.fromhex("894D445232370D0A"))


def test_unframed_r27_like_legacy_json_remains_legacy_and_byte_preserved(tmp_path: Path) -> None:
    repository = LocalFileRepository(tmp_path)
    raw_project = json.loads(ProjectSerializer().dumps(_project()))
    raw_project.update(
        {
            "authoritative_envelope_fingerprint": "0" * 64,
            "envelope_schema": "manga_director.localfile.aggregate-envelope",
            "envelope_version": 2,
            "payload_encoding": "base64-utf8-v1",
            "project_payload": "ignored-by-legacy-reader",
            "same_cas_witness": {},
        }
    )
    legacy_bytes = json.dumps(raw_project, ensure_ascii=False, indent=2).encode("utf-8")
    path = tmp_path / "projects" / "r27-vector.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(legacy_bytes)

    assert envelope._project_payload_from_aggregate(legacy_bytes) == legacy_bytes
    assert repository.load("r27-vector") == _project()
    assert path.read_bytes() == legacy_bytes


@pytest.mark.parametrize(
    "aggregate",
    [
        b"",
        b"\x89",
        bytes.fromhex("894D445232370D0A"),
        bytes.fromhex("894D445232370D0A02"),
        bytes.fromhex("894D445232370D0A01") + b"{",
        bytes.fromhex("894D445232370D0A01") + b"{}",
        bytes.fromhex("894D445232370D0A01") + b"{}\n",
        bytes.fromhex("894D445232370D0A01") + b"[]",
        bytes.fromhex("894D445232370D0A01") + b"\xef\xbb\xbf{}",
        bytes.fromhex("894D445232370D0A01") + b'{"a":1,"a":1}',
        b"\x89MDRX\r\n\x01{}",
        b"\xff",
    ],
)
def test_malformed_framed_or_binary_aggregate_fails_closed(aggregate: bytes) -> None:
    with pytest.raises(envelope._AggregateEnvelopeCorruptError, match="r27_aggregate_corrupt"):
        envelope._project_payload_from_aggregate(aggregate)


def test_altered_json_f1_trailing_and_noncanonical_json_fail_closed() -> None:
    aggregate = _aggregate()
    body = aggregate[9:]
    parsed = json.loads(body)
    noncanonical = bytes.fromhex("894D445232370D0A01") + json.dumps(parsed, indent=2).encode("utf-8")
    parsed["authoritative_envelope_fingerprint"] = "0" * 64
    wrong_f1 = bytes.fromhex("894D445232370D0A01") + json.dumps(
        parsed, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    for malformed in (wrong_f1, aggregate + b" ", aggregate[:-1], noncanonical):
        with pytest.raises(envelope._AggregateEnvelopeCorruptError, match="r27_aggregate_corrupt"):
            envelope._decode_r27_aggregate(malformed)


def test_model_a_revision_binding_is_exact_and_read_only() -> None:
    aggregate = _aggregate()
    before = aggregate
    envelope._validate_revision_binding(
        aggregate,
        record_project_id="r27-vector",
        record_revision=8,
        record_fingerprint=envelope._physical_fingerprint(aggregate),
        project_id_reader=lambda payload: ProjectSerializer().loads(payload.decode("utf-8")).id,
    )

    assert aggregate == before
    for field, value in (
        ("record_project_id", "other-project"),
        ("record_revision", 7),
        ("record_fingerprint", "0" * 64),
    ):
        arguments: dict[str, object] = {
            "record_project_id": "r27-vector",
            "record_revision": 8,
            "record_fingerprint": envelope._physical_fingerprint(aggregate),
            "project_id_reader": lambda payload: ProjectSerializer().loads(payload.decode("utf-8")).id,
        }
        arguments[field] = value
        with pytest.raises(envelope._AggregateEnvelopeCorruptError, match="r27_aggregate_corrupt"):
            envelope._validate_revision_binding(aggregate, **arguments)  # type: ignore[arg-type]


def test_project_payload_is_exact_base64_utf8_transport() -> None:
    aggregate = _aggregate()
    body = json.loads(aggregate[9:])

    assert base64.b64decode(body["project_payload"], validate=True) == ProjectSerializer().dumps(_project()).encode(
        "utf-8"
    )
