"""Private RFC-01 I01 validation primitives.

This module deliberately has no public export and no workflow, provider,
filesystem-write, or application authority.  It only validates a pre-existing
asset-owner registry, seals bounded in-memory PNG bytes for one local handoff,
and checks PNG container structure without decoding it.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
import stat
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from manga_director.production.next_generation_local_durable_asset_owner import (
    LocalDurableAssetOwner,
)

_MAX_PNG_BYTES: Final = 25 * 1024 * 1024
_PNG_SIGNATURE: Final = b"\x89PNG\r\n\x1a\n"
_REGISTRY_FILENAME: Final = "asset-owner.sqlite3"
_UNAVAILABLE: Final = "RFC-01 I01 material is unavailable"
_VALID_COLOR_DEPTHS: Final = {
    0: frozenset((1, 2, 4, 8, 16)),
    2: frozenset((8, 16)),
    3: frozenset((1, 2, 4, 8)),
    4: frozenset((8, 16)),
    6: frozenset((8, 16)),
}
_EXPECTED_COLUMNS: Final = (
    (0, "asset_id", "TEXT", 0, None, 1),
    (1, "attempt_id", "TEXT", 1, None, 0),
    (2, "provider_reference", "TEXT", 1, None, 0),
    (3, "media_type", "TEXT", 1, None, 0),
    (4, "digest", "TEXT", 1, None, 0),
    (5, "storage_name", "TEXT", 1, None, 0),
)
_EXPECTED_AUTO_INDEXES: Final = {
    "sqlite_autoindex_asset_registry_1": (1, "pk", 0, "asset_id"),
    "sqlite_autoindex_asset_registry_2": (1, "u", 0, "attempt_id"),
    "sqlite_autoindex_asset_registry_3": (1, "u", 0, "storage_name"),
}
_SECRET_IDENTIFIER_PARTS: Final = (
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "endpoint",
    "password",
    "secret",
    "token",
    "bearer",
)


def _unavailable() -> ValueError:
    return ValueError(_UNAVAILABLE)


class StrictLocalAssetRegistryIntegrityReaderV1:
    """Read and validate exactly one existing owner registry without mutation."""

    __slots__ = ("_registry_path",)

    def __init__(self, owner: LocalDurableAssetOwner) -> None:
        if type(owner) is not LocalDurableAssetOwner:
            raise _unavailable()
        owner_root = owner._root
        if not isinstance(owner_root, Path) or not owner_root.is_absolute():
            raise _unavailable()
        self._registry_path = owner_root / "registry" / _REGISTRY_FILENAME

    def validate(self) -> None:
        """Fail closed unless the frozen asset-owner v1 registry is exact."""

        path = self._registry_path
        connection: sqlite3.Connection | None = None
        try:
            if not _is_existing_regular_file(path) or path.stat().st_size < 1:
                raise _unavailable()
            connection = sqlite3.connect(
                f"{path.resolve(strict=True).as_uri()}?mode=ro",
                uri=True,
                timeout=0.0,
                isolation_level=None,
            )
            connection.execute("PRAGMA query_only = ON")
            connection.execute("BEGIN")
            if int(connection.execute("PRAGMA user_version").fetchone()[0]) != 1:
                raise _unavailable()
            _validate_registry_schema(connection)
        except (OSError, sqlite3.Error, TypeError, ValueError) as error:
            if isinstance(error, ValueError) and str(error) == _UNAVAILABLE:
                raise
            raise _unavailable() from error
        finally:
            if connection is not None:
                connection.close()


def _is_existing_regular_file(path: Path) -> bool:
    try:
        status = path.lstat()
    except OSError:
        return False
    attributes = getattr(status, "st_file_attributes", 0)
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return path.is_file() and not path.is_symlink() and not bool(attributes & reparse)


def _validate_registry_schema(connection: sqlite3.Connection) -> None:
    objects = connection.execute(
        "SELECT type, name, tbl_name FROM sqlite_master "
        "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
    ).fetchall()
    if objects != [("table", "asset_registry", "asset_registry")]:
        raise _unavailable()
    table_info = [tuple(row) for row in connection.execute("PRAGMA table_info(asset_registry)")]
    if table_info != list(_EXPECTED_COLUMNS):
        raise _unavailable()
    index_rows = connection.execute("PRAGMA index_list(asset_registry)").fetchall()
    actual_indexes: dict[str, tuple[int, str, int, str]] = {}
    for row in index_rows:
        if len(row) != 5:
            raise _unavailable()
        _, name, unique, origin, partial = row
        if not isinstance(name, str) or name in actual_indexes:
            raise _unavailable()
        key_columns = [
            (int(index_row[0]), int(index_row[1]), index_row[2])
            for index_row in connection.execute(f"PRAGMA index_xinfo({name!r})")
            if len(index_row) == 6 and int(index_row[5]) == 1
        ]
        if len(key_columns) != 1 or key_columns[0][0] != 0 or not isinstance(key_columns[0][2], str):
            raise _unavailable()
        actual_indexes[name] = (
            int(unique),
            str(origin),
            int(partial),
            str(key_columns[0][2]),
        )
    if actual_indexes != _EXPECTED_AUTO_INDEXES:
        raise _unavailable()


@dataclass(frozen=True, slots=True)
class DirectPngHandoffFactsV1:
    """Immutable facts bound to a single private direct-byte handoff."""

    attempt_id: str
    project_id: str
    page_id: str
    target_page_reference: str
    provider_reference: str
    dispatch_identity: str
    idempotency_identity: str
    submission_receipt_identity: str
    logical_output_id: str
    canonical_result_identity: str
    expected_sha256: str
    expected_byte_length: int
    media_type: str = "image/png"


class SealedDirectPngHandoffV1:
    """Non-serializable, issuer-registered, one-shot private handoff."""

    __slots__ = ("_facts", "_image_bytes", "_nonce", "_sealed", "__weakref__")
    _facts: DirectPngHandoffFactsV1
    _image_bytes: bytes | None
    _nonce: bytes
    _sealed: bool

    def __init__(self) -> None:
        raise TypeError(_UNAVAILABLE)

    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError(_UNAVAILABLE)

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_sealed", False):
            raise TypeError(_UNAVAILABLE)
        object.__setattr__(self, name, value)

    def __reduce__(self) -> str | tuple[object, ...]:
        raise TypeError(_UNAVAILABLE)

    def __copy__(self) -> object:
        raise TypeError(_UNAVAILABLE)

    def __deepcopy__(self, memo: object) -> object:
        raise TypeError(_UNAVAILABLE)

    @property
    def facts(self) -> DirectPngHandoffFactsV1:
        return self._facts


@dataclass(slots=True)
class _RegisteredHandoff:
    handoff: SealedDirectPngHandoffV1
    nonce: bytes
    image_bytes: bytes | None


class TrustedDirectPngHandoffIssuer:
    """Private issuer retaining the process-local authority registry."""

    __slots__ = ("_issued", "_tombstones", "_binding_tombstones")

    def __init__(self) -> None:
        self._issued: dict[int, _RegisteredHandoff] = {}
        self._tombstones: set[int] = set()
        self._binding_tombstones: set[DirectPngHandoffFactsV1] = set()

    def issue(
        self,
        *,
        attempt_id: str,
        project_id: str,
        page_id: str,
        target_page_reference: str,
        provider_reference: str,
        dispatch_identity: str,
        idempotency_identity: str,
        submission_receipt_identity: str,
        logical_output_id: str,
        canonical_result_identity: str,
        image_bytes: bytes,
        media_type: str = "image/png",
    ) -> SealedDirectPngHandoffV1:
        if type(image_bytes) is not bytes or not 1 <= len(image_bytes) <= _MAX_PNG_BYTES:
            raise _unavailable()
        values = (
            attempt_id,
            project_id,
            page_id,
            target_page_reference,
            provider_reference,
            dispatch_identity,
            idempotency_identity,
            submission_receipt_identity,
            logical_output_id,
        )
        if media_type != "image/png" or not all(_is_logical_reference(value) for value in values):
            raise _unavailable()
        if not _is_sha256(canonical_result_identity):
            raise _unavailable()
        facts = DirectPngHandoffFactsV1(
            attempt_id=attempt_id,
            project_id=project_id,
            page_id=page_id,
            target_page_reference=target_page_reference,
            provider_reference=provider_reference,
            dispatch_identity=dispatch_identity,
            idempotency_identity=idempotency_identity,
            submission_receipt_identity=submission_receipt_identity,
            logical_output_id=logical_output_id,
            canonical_result_identity=canonical_result_identity,
            expected_sha256=hashlib.sha256(image_bytes).hexdigest(),
            expected_byte_length=len(image_bytes),
        )
        if facts in self._binding_tombstones:
            raise _unavailable()
        handoff = object.__new__(SealedDirectPngHandoffV1)
        nonce = secrets.token_bytes(32)
        object.__setattr__(handoff, "_facts", facts)
        object.__setattr__(handoff, "_image_bytes", image_bytes)
        object.__setattr__(handoff, "_nonce", nonce)
        object.__setattr__(handoff, "_sealed", True)
        self._issued[id(handoff)] = _RegisteredHandoff(handoff, nonce, image_bytes)
        self._binding_tombstones.add(facts)
        return handoff

    def consume(
        self,
        handoff: SealedDirectPngHandoffV1,
        *,
        expected: DirectPngHandoffFactsV1,
    ) -> bytes:
        """Tombstone a registered handoff before releasing its direct bytes."""

        if type(handoff) is not SealedDirectPngHandoffV1 or type(expected) is not DirectPngHandoffFactsV1:
            raise _unavailable()
        registered = self._issued.get(id(handoff))
        if (
            registered is None
            or registered.handoff is not handoff
            or id(handoff) in self._tombstones
            or not hmac.compare_digest(registered.nonce, handoff._nonce)
        ):
            raise _unavailable()
        self._tombstones.add(id(handoff))
        del self._issued[id(handoff)]
        image_bytes = registered.image_bytes
        registered.image_bytes = None
        object.__setattr__(handoff, "_image_bytes", None)
        if image_bytes is None or handoff.facts != expected:
            raise _unavailable()
        if (
            len(image_bytes) != expected.expected_byte_length
            or hashlib.sha256(image_bytes).hexdigest() != expected.expected_sha256
        ):
            raise _unavailable()
        return image_bytes


def _is_logical_reference(value: object) -> bool:
    if type(value) is not str or not value or value != value.strip():
        return False
    lowered = value.lower()
    return not (
        any(character.isspace() or ord(character) < 32 for character in value)
        or "/" in value
        or "\\" in value
        or ".." in value
        or lowered.startswith("file:")
        or "://" in value
        or (len(value) > 1 and value[0].isalpha() and value[1] == ":")
        or any(part in lowered for part in _SECRET_IDENTIFIER_PARTS)
    )


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


@dataclass(frozen=True, slots=True)
class PngStructuralInfoV1:
    """Narrow structural facts, not a decoded-image or visual-safety claim."""

    width: int
    height: int
    color_type: int
    bit_depth: int
    interlace_method: int


class StrictPngStructuralValidatorV1:
    """Validate bounded, CRC-checked PNG container structure only."""

    __slots__ = ()

    def validate(self, image_bytes: bytes) -> PngStructuralInfoV1:
        if type(image_bytes) is not bytes or not 1 <= len(image_bytes) <= _MAX_PNG_BYTES:
            raise _unavailable()
        if not image_bytes.startswith(_PNG_SIGNATURE):
            raise _unavailable()
        cursor = len(_PNG_SIGNATURE)
        state = _PngParseState()
        while cursor < len(image_bytes):
            chunk_type, chunk_data, cursor = _read_chunk(image_bytes, cursor)
            _accept_chunk(state, chunk_type, chunk_data, cursor, len(image_bytes))
        header = _finish_png(state)
        return PngStructuralInfoV1(
            width=header[0],
            height=header[1],
            color_type=header[2],
            bit_depth=header[3],
            interlace_method=header[4],
        )


@dataclass(slots=True)
class _PngParseState:
    header: tuple[int, int, int, int, int] | None = None
    saw_plte: bool = False
    saw_idat: bool = False
    idat_closed: bool = False
    saw_iend: bool = False


def _read_chunk(image_bytes: bytes, cursor: int) -> tuple[bytes, bytes, int]:
    if len(image_bytes) - cursor < 12:
        raise _unavailable()
    chunk_length = int.from_bytes(image_bytes[cursor : cursor + 4], "big", signed=False)
    chunk_type = image_bytes[cursor + 4 : cursor + 8]
    data_start = cursor + 8
    if chunk_length > len(image_bytes) - data_start - 4:
        raise _unavailable()
    data_end = data_start + chunk_length
    chunk_data = image_bytes[data_start:data_end]
    given_crc = int.from_bytes(image_bytes[data_end : data_end + 4], "big", signed=False)
    if not _is_valid_chunk_type(chunk_type) or zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF != given_crc:
        raise _unavailable()
    return chunk_type, chunk_data, data_end + 4


def _accept_chunk(
    state: _PngParseState,
    chunk_type: bytes,
    chunk_data: bytes,
    cursor: int,
    total_length: int,
) -> None:
    if state.header is None and chunk_type != b"IHDR":
        raise _unavailable()
    if state.saw_idat and chunk_type != b"IDAT":
        state.idat_closed = True
    handlers = {
        b"IHDR": _accept_header_chunk,
        b"PLTE": _accept_palette_chunk,
        b"IDAT": _accept_data_chunk,
        b"IEND": _accept_end_chunk,
    }
    handler = handlers.get(chunk_type)
    if handler is not None:
        handler(state, chunk_data, cursor, total_length)
    elif 65 <= chunk_type[0] <= 90:
        raise _unavailable()


def _accept_header_chunk(
    state: _PngParseState, chunk_data: bytes, _cursor: int, _total_length: int
) -> None:
    if state.header is not None:
        raise _unavailable()
    state.header = _parse_header(chunk_data)


def _accept_palette_chunk(
    state: _PngParseState, chunk_data: bytes, _cursor: int, _total_length: int
) -> None:
    if state.header is None or state.saw_plte or state.saw_idat:
        raise _unavailable()
    _validate_palette(chunk_data, state.header[2], state.header[3])
    state.saw_plte = True


def _accept_data_chunk(
    state: _PngParseState, _chunk_data: bytes, _cursor: int, _total_length: int
) -> None:
    if state.header is None or state.idat_closed:
        raise _unavailable()
    state.saw_idat = True


def _accept_end_chunk(
    state: _PngParseState, chunk_data: bytes, cursor: int, total_length: int
) -> None:
    if state.header is None or state.saw_iend or not state.saw_idat or chunk_data:
        raise _unavailable()
    state.saw_iend = True
    if cursor != total_length:
        raise _unavailable()


def _finish_png(state: _PngParseState) -> tuple[int, int, int, int, int]:
    if state.header is None or not state.saw_idat or not state.saw_iend:
        raise _unavailable()
    color_type = state.header[2]
    if color_type == 3 and not state.saw_plte:
        raise _unavailable()
    if color_type in (0, 4) and state.saw_plte:
        raise _unavailable()
    return state.header


def _is_valid_chunk_type(chunk_type: bytes) -> bool:
    return len(chunk_type) == 4 and all(
        65 <= value <= 90 or 97 <= value <= 122 for value in chunk_type
    ) and 65 <= chunk_type[2] <= 90


def _parse_header(data: bytes) -> tuple[int, int, int, int, int]:
    if len(data) != 13:
        raise _unavailable()
    width = int.from_bytes(data[0:4], "big", signed=False)
    height = int.from_bytes(data[4:8], "big", signed=False)
    bit_depth = data[8]
    color_type = data[9]
    compression, filter_method, interlace_method = data[10:13]
    if (
        not 0 < width <= 8192
        or not 0 < height <= 8192
        or width * height > 33_554_432
        or bit_depth not in _VALID_COLOR_DEPTHS.get(color_type, frozenset())
        or compression != 0
        or filter_method != 0
        or interlace_method not in (0, 1)
    ):
        raise _unavailable()
    return width, height, color_type, bit_depth, interlace_method


def _validate_palette(data: bytes, color_type: int, bit_depth: int) -> None:
    if color_type in (0, 4) or len(data) < 3 or len(data) > 768 or len(data) % 3:
        raise _unavailable()
    if color_type == 3 and len(data) // 3 > 2**bit_depth:
        raise _unavailable()
