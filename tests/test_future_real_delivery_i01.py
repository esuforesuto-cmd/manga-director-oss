"""Focused adversarial contracts for private RFC-01 I01 primitives."""

from __future__ import annotations

import copy
import pickle
import sqlite3
import zlib
from dataclasses import replace
from pathlib import Path

import pytest

from manga_director.production.future_real_delivery_i01 import (
    DirectPngHandoffFactsV1,
    SealedDirectPngHandoffV1,
    StrictLocalAssetRegistryIntegrityReaderV1,
    StrictPngStructuralValidatorV1,
    TrustedDirectPngHandoffIssuer,
)
from manga_director.production.next_generation_local_durable_asset_owner import (
    LocalDurableAssetOwner,
)

_RESULT = "a" * 64
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_HANDOFF_IDENTIFIER_FIELDS = (
    "attempt_id",
    "project_id",
    "page_id",
    "target_page_reference",
    "provider_reference",
    "dispatch_identity",
    "idempotency_identity",
    "submission_receipt_identity",
    "logical_output_id",
    "canonical_result_identity",
)
_UNSAFE_HANDOFF_IDENTIFIER_VALUES = (
    "../caller-selected.png",
    r"..\caller-selected.png",
    "/tmp/output.png",
    r"C:\temp\output.png",
    r"\\server\share\output.png",
    "file:output.png",
    "file:///tmp/output.png",
    "https://example.invalid/output.png",
    "foo/bar",
    r"foo\bar",
    "output\x1fcontrol",
    "",
    " leading",
    "trailing ",
    "api_key:caller-selected",
)


def _chunk(chunk_type: bytes, data: bytes = b"") -> bytes:
    return (
        len(data).to_bytes(4, "big")
        + chunk_type
        + data
        + (zlib.crc32(chunk_type + data) & 0xFFFFFFFF).to_bytes(4, "big")
    )


def _png(*chunks: bytes) -> bytes:
    return _PNG_SIGNATURE + b"".join(chunks)


def _header(
    *, width: int = 1, height: int = 1, bit_depth: int = 8, color_type: int = 2,
    compression: int = 0, filter_method: int = 0, interlace: int = 0,
) -> bytes:
    return _chunk(
        b"IHDR",
        width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + bytes((bit_depth, color_type, compression, filter_method, interlace)),
    )


def _valid_png(*, color_type: int = 2, bit_depth: int = 8, extra: tuple[bytes, ...] = ()) -> bytes:
    palette = (_chunk(b"PLTE", b"\x00\x00\x00"),) if color_type == 3 else ()
    return _png(_header(color_type=color_type, bit_depth=bit_depth), *palette, *extra, _chunk(b"IDAT", b"x"), _chunk(b"IEND"))


def _owner(tmp_path: Path) -> LocalDurableAssetOwner:
    return LocalDurableAssetOwner(tmp_path / "owner")


def _registry_path(root: Path) -> Path:
    return root / "registry" / "asset-owner.sqlite3"


def _reader(owner: LocalDurableAssetOwner) -> StrictLocalAssetRegistryIntegrityReaderV1:
    return StrictLocalAssetRegistryIntegrityReaderV1(owner)


def _issue(issuer: TrustedDirectPngHandoffIssuer, image_bytes: bytes = _valid_png()) -> SealedDirectPngHandoffV1:
    return _issue_with(issuer, image_bytes=image_bytes)


def _issue_with(
    issuer: TrustedDirectPngHandoffIssuer,
    *,
    image_bytes: bytes = _valid_png(),
    replacements: dict[str, str] | None = None,
) -> SealedDirectPngHandoffV1:
    values = {
        "attempt_id": "attempt:i01:001",
        "project_id": "project:i01",
        "page_id": "page:001",
        "target_page_reference": "page-ref:001",
        "provider_reference": "provider:fake",
        "dispatch_identity": "dispatch:001",
        "idempotency_identity": "idempotency:001",
        "submission_receipt_identity": "receipt:001",
        "logical_output_id": "output:001",
        "canonical_result_identity": _RESULT,
    }
    if replacements is not None:
        values.update(replacements)
    return issuer.issue(
        attempt_id=values["attempt_id"],
        project_id=values["project_id"],
        page_id=values["page_id"],
        target_page_reference=values["target_page_reference"],
        provider_reference=values["provider_reference"],
        dispatch_identity=values["dispatch_identity"],
        idempotency_identity=values["idempotency_identity"],
        submission_receipt_identity=values["submission_receipt_identity"],
        logical_output_id=values["logical_output_id"],
        canonical_result_identity=values["canonical_result_identity"],
        image_bytes=image_bytes,
    )


def test_registry_reader_accepts_exact_existing_schema_without_mutation(tmp_path: Path) -> None:
    owner = _owner(tmp_path)
    path = _registry_path(tmp_path / "owner")
    before = path.read_bytes()

    _reader(owner).validate()

    assert path.read_bytes() == before


def test_registry_reader_has_no_caller_path_and_rejects_owner_subclasses(tmp_path: Path) -> None:
    owner = _owner(tmp_path)
    assert not hasattr(_reader(owner), "path")
    with pytest.raises(ValueError):
        StrictLocalAssetRegistryIntegrityReaderV1(object())  # type: ignore[arg-type]


def test_registry_reader_does_not_mutate_an_invalid_existing_store(tmp_path: Path) -> None:
    owner = _owner(tmp_path)
    path = _registry_path(tmp_path / "owner")
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE extra (value TEXT)")
    before = path.read_bytes()

    with pytest.raises(ValueError, match="unavailable"):
        _reader(owner).validate()

    assert path.read_bytes() == before


@pytest.mark.parametrize("mode", ("missing", "zero", "version", "type", "null", "default", "pk", "unique", "autoindex", "table", "index", "view", "trigger", "corrupt"))
def test_registry_reader_rejects_all_frozen_schema_failures(tmp_path: Path, mode: str) -> None:
    root = tmp_path / "owner"
    owner = _owner(tmp_path)
    path = _registry_path(root)
    if mode == "missing":
        path.unlink()
    elif mode == "zero":
        path.write_bytes(b"")
    elif mode == "corrupt":
        path.write_bytes(b"not sqlite")
    else:
        _alter_registry(path, mode)
    with pytest.raises(ValueError, match="unavailable"):
        _reader(owner).validate()


def _alter_registry(path: Path, mode: str) -> None:
    direct_sql = {
        "version": "PRAGMA user_version = 2",
        "table": "CREATE TABLE extra (value TEXT)",
        "index": "CREATE INDEX extra_index ON asset_registry(digest)",
        "view": "CREATE VIEW extra_view AS SELECT asset_id FROM asset_registry",
        "trigger": "CREATE TRIGGER extra_trigger AFTER INSERT ON asset_registry BEGIN SELECT 1; END",
    }
    replacement_columns = {
        "type": "asset_id BLOB PRIMARY KEY, attempt_id TEXT NOT NULL UNIQUE, provider_reference TEXT NOT NULL, media_type TEXT NOT NULL, digest TEXT NOT NULL, storage_name TEXT NOT NULL UNIQUE",
        "null": "asset_id TEXT PRIMARY KEY, attempt_id TEXT UNIQUE, provider_reference TEXT NOT NULL, media_type TEXT NOT NULL, digest TEXT NOT NULL, storage_name TEXT NOT NULL UNIQUE",
        "default": "asset_id TEXT PRIMARY KEY, attempt_id TEXT NOT NULL UNIQUE DEFAULT 'x', provider_reference TEXT NOT NULL, media_type TEXT NOT NULL, digest TEXT NOT NULL, storage_name TEXT NOT NULL UNIQUE",
        "pk": "asset_id TEXT NOT NULL UNIQUE, attempt_id TEXT PRIMARY KEY, provider_reference TEXT NOT NULL, media_type TEXT NOT NULL, digest TEXT NOT NULL, storage_name TEXT NOT NULL UNIQUE",
        "unique": "asset_id TEXT PRIMARY KEY, attempt_id TEXT NOT NULL, provider_reference TEXT NOT NULL, media_type TEXT NOT NULL, digest TEXT NOT NULL, storage_name TEXT NOT NULL UNIQUE",
        "autoindex": "asset_id TEXT PRIMARY KEY, attempt_id TEXT NOT NULL UNIQUE, provider_reference TEXT NOT NULL, media_type TEXT NOT NULL, digest TEXT NOT NULL, storage_name TEXT NOT NULL, UNIQUE(storage_name, digest)",
    }
    with sqlite3.connect(path) as connection:
        if mode in direct_sql:
            connection.execute(direct_sql[mode])
            return
        connection.execute("DROP TABLE asset_registry")
        connection.execute(f"CREATE TABLE asset_registry ({replacement_columns[mode]})")


def test_valid_registry_reader_closes_connection_for_exclusive_lock(tmp_path: Path) -> None:
    owner = _owner(tmp_path)
    _reader(owner).validate()
    with sqlite3.connect(_registry_path(tmp_path / "owner"), timeout=0.0) as connection:
        connection.execute("BEGIN EXCLUSIVE")


def test_registry_reader_rejects_a_busy_registry(tmp_path: Path) -> None:
    owner = _owner(tmp_path)
    path = _registry_path(tmp_path / "owner")
    with sqlite3.connect(path, timeout=0.0) as connection:
        connection.execute("BEGIN EXCLUSIVE")
        with pytest.raises(ValueError, match="unavailable"):
            _reader(owner).validate()


def test_handoff_is_issuer_bound_one_shot_and_hash_bound() -> None:
    issuer = TrustedDirectPngHandoffIssuer()
    handoff = _issue(issuer)
    facts = handoff.facts

    image_bytes = issuer.consume(handoff, expected=facts)

    assert image_bytes == _valid_png()
    assert facts.expected_byte_length == len(image_bytes)
    assert facts.expected_sha256
    with pytest.raises(ValueError):
        issuer.consume(handoff, expected=facts)
    with pytest.raises(ValueError):
        _issue(issuer)


def test_handoff_rejects_construction_copy_serialization_wrong_issuer_and_wrong_binding() -> None:
    issuer = TrustedDirectPngHandoffIssuer()
    handoff = _issue(issuer)
    facts = handoff.facts
    with pytest.raises(TypeError):
        SealedDirectPngHandoffV1()
    with pytest.raises(TypeError):
        type("Forged", (SealedDirectPngHandoffV1,), {})
    with pytest.raises(TypeError):
        copy.copy(handoff)
    with pytest.raises(TypeError):
        pickle.dumps(handoff)
    copied = object.__new__(SealedDirectPngHandoffV1)
    object.__setattr__(copied, "_facts", facts)
    object.__setattr__(copied, "_image_bytes", _valid_png())
    object.__setattr__(copied, "_nonce", handoff._nonce)
    object.__setattr__(copied, "_sealed", True)
    with pytest.raises(ValueError):
        issuer.consume(copied, expected=facts)
    with pytest.raises(ValueError):
        TrustedDirectPngHandoffIssuer().consume(handoff, expected=facts)
    bad_facts = replace(facts, attempt_id="attempt:wrong")
    with pytest.raises(ValueError):
        issuer.consume(handoff, expected=bad_facts)
    with pytest.raises(ValueError):
        issuer.consume(handoff, expected=facts)


@pytest.mark.parametrize("field", _HANDOFF_IDENTIFIER_FIELDS)
@pytest.mark.parametrize("bad", _UNSAFE_HANDOFF_IDENTIFIER_VALUES)
def test_handoff_rejects_unsafe_identifier_in_every_binding_field_without_mutation(
    field: str, bad: str
) -> None:
    issuer = TrustedDirectPngHandoffIssuer()
    with pytest.raises(ValueError):
        _issue_with(issuer, replacements={field: bad})
    assert issuer._issued == {}
    assert issuer._tombstones == set()
    assert issuer._binding_tombstones == set()


@pytest.mark.parametrize("field", _HANDOFF_IDENTIFIER_FIELDS[:-1])
@pytest.mark.parametrize("value", ("attempt-001", "result_abc123", "panel.main", "output-1"))
def test_handoff_accepts_ordinary_logical_identifier_punctuation(field: str, value: str) -> None:
    handoff = _issue_with(TrustedDirectPngHandoffIssuer(), replacements={field: value})

    assert getattr(handoff.facts, field) == value


def test_handoff_restart_and_downstream_failure_never_restore_authority() -> None:
    issuer = TrustedDirectPngHandoffIssuer()
    handoff = _issue(issuer)
    with pytest.raises(ValueError):
        issuer.consume(handoff, expected=DirectPngHandoffFactsV1(**{name: getattr(handoff.facts, name) for name in handoff.facts.__dataclass_fields__} | {"logical_output_id": "output:wrong"}))
    with pytest.raises(ValueError):
        issuer.consume(handoff, expected=handoff.facts)
    with pytest.raises(ValueError):
        TrustedDirectPngHandoffIssuer().consume(_issue(TrustedDirectPngHandoffIssuer()), expected=handoff.facts)


@pytest.mark.parametrize(
    "image_bytes",
    (
        b"not-a-png",
        _PNG_SIGNATURE + b"\x00\x00",
        _PNG_SIGNATURE + b"\xff\xff\xff\xffIHDR",
        _png(_header())[:-1],
        _png(_header(), _chunk(b"IDAT", b"x"), _chunk(b"IEND"))[:-4] + b"\x00\x00\x00\x00",
        _png(_header(), _chunk(b"AB1D"), _chunk(b"IDAT", b"x"), _chunk(b"IEND")),
        _png(_header(), _chunk(b"ABCD"), _chunk(b"IDAT", b"x"), _chunk(b"IEND")),
        _png(_chunk(b"IDAT", b"x"), _chunk(b"IEND")),
        _png(_header(), _header(), _chunk(b"IDAT", b"x"), _chunk(b"IEND")),
        _png(_chunk(b"IHDR", b"short"), _chunk(b"IDAT", b"x"), _chunk(b"IEND")),
        _png(_header(width=0), _chunk(b"IDAT", b"x"), _chunk(b"IEND")),
        _png(_header(width=8193), _chunk(b"IDAT", b"x"), _chunk(b"IEND")),
        _png(_header(width=8192, height=8192), _chunk(b"IDAT", b"x"), _chunk(b"IEND")),
        _png(_header(color_type=2, bit_depth=4), _chunk(b"IDAT", b"x"), _chunk(b"IEND")),
        _png(_header(compression=1), _chunk(b"IDAT", b"x"), _chunk(b"IEND")),
        _png(_header(filter_method=1), _chunk(b"IDAT", b"x"), _chunk(b"IEND")),
        _png(_header(interlace=2), _chunk(b"IDAT", b"x"), _chunk(b"IEND")),
        _png(_header(), _chunk(b"IDAT", b"x"), _chunk(b"PLTE", b"\x00\x00\x00"), _chunk(b"IEND")),
        _png(_header(color_type=3), _chunk(b"PLTE", b"\x00\x00\x00"), _chunk(b"PLTE", b"\x00\x00\x00"), _chunk(b"IDAT", b"x"), _chunk(b"IEND")),
        _png(_header(color_type=3), _chunk(b"PLTE", b"\x00\x00"), _chunk(b"IDAT", b"x"), _chunk(b"IEND")),
        _png(_header(color_type=3), _chunk(b"IDAT", b"x"), _chunk(b"IEND")),
        _png(_header(), _chunk(b"IEND")),
        _png(_header(), _chunk(b"IDAT", b"x"), _chunk(b"IDAT", b"y"), _chunk(b"tEXt", b"x"), _chunk(b"IDAT", b"z"), _chunk(b"IEND")),
        _png(_header(), _chunk(b"IDAT", b"x")),
        _png(_header(), _chunk(b"IDAT", b"x"), _chunk(b"IEND"), _chunk(b"IEND")),
        _png(_header(), _chunk(b"IDAT", b"x"), _chunk(b"IEND", b"x")),
        _valid_png() + b"trailing",
        pytest.param(b"x" * (25 * 1024 * 1024 + 1), id="oversized"),
    ),
)
def test_png_validator_rejects_frozen_invalid_containers(image_bytes: bytes) -> None:
    with pytest.raises(ValueError):
        StrictPngStructuralValidatorV1().validate(image_bytes)


def test_png_validator_accepts_representative_png_and_checked_ancillary_chunk() -> None:
    info = StrictPngStructuralValidatorV1().validate(_valid_png(extra=(_chunk(b"aBCD", b"ok"),)))
    assert (info.width, info.height, info.color_type, info.bit_depth) == (1, 1, 2, 8)
