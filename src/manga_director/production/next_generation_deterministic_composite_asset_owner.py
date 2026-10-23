"""Private LocalFile owner for deterministic Page-composition PNG assets."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from manga_director.production.next_generation_deterministic_page_compositor import (
    CompositeInputError,
    decode_png,
    encode_rgb_png,
)
from manga_director.production.next_generation_page_composition import PageCompositeAsset
from manga_director.production.next_generation_page_generation_plan import logical_reference

CompositeOwnerOutcome = Literal[
    "registered", "confirmed", "conflict", "corrupt", "failed"
]
CompositeReadOutcome = Literal["found", "missing", "corrupt"]

_DATABASE_FILENAME = "deterministic-composite-assets.sqlite3"
_SCHEMA_VERSION = 1
_ASSET_DIRECTORY = "deterministic-composite-assets"
_MAX_BYTES = 25 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class DeterministicCompositeRegistrationResult:
    composition_attempt_id: str
    asset_id: str
    outcome: CompositeOwnerOutcome
    asset: PageCompositeAsset | None = field(default=None, repr=False)


@dataclass(frozen=True, slots=True)
class DeterministicCompositeReadResult:
    asset_id: str
    outcome: CompositeReadOutcome
    asset: PageCompositeAsset | None = field(default=None, repr=False)
    image_bytes: bytes | None = field(default=None, repr=False)


class DeterministicCompositeAssetOwner:
    """Own strict canonical PNGs without any Provider identity or registry row."""

    def __init__(self, owner_root: Path) -> None:
        self._root = _prepare_root(owner_root)
        self._asset_directory = _prepare_directory(self._root, _ASSET_DIRECTORY)
        self._database_path = _prepare_database(self._root)
        self._initialize_schema()

    def register(  # noqa: C901
        self, asset: PageCompositeAsset, image_bytes: bytes
    ) -> DeterministicCompositeRegistrationResult:
        if not isinstance(asset, PageCompositeAsset) or not isinstance(image_bytes, bytes):
            return DeterministicCompositeRegistrationResult("", "", "failed")
        if not image_bytes or len(image_bytes) > _MAX_BYTES:
            return _result(asset, "failed")
        digest = hashlib.sha256(image_bytes).hexdigest()
        if digest != asset.content_sha256:
            return _result(asset, "conflict")
        try:
            decoded = decode_png(image_bytes)
        except CompositeInputError:
            return _result(asset, "failed")
        if (
            decoded.width != asset.width
            or decoded.height != asset.height
            or decoded.channels != 3
            or encode_rgb_png(decoded.width, decoded.height, bytes(decoded.pixels))
            != image_bytes
        ):
            return _result(asset, "conflict")
        storage_name = f"{hashlib.sha256(asset.composition_attempt_id.encode('utf-8')).hexdigest()}.png"
        final_path = self._asset_directory / storage_name
        payload = _canonical_asset_json(asset)
        payload_digest = _digest_text(payload)
        connection: sqlite3.Connection | None = None
        staging_path: Path | None = None
        final_created = False
        try:
            self._assert_live_directories()
            connection = self._connect()
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT asset_id, storage_name, producer_kind, payload_json, payload_digest, "
                "content_sha256 "
                "FROM composite_assets WHERE composition_attempt_id = ?",
                (asset.composition_attempt_id,),
            ).fetchone()
            if row is not None:
                connection.rollback()
                existing = _verified_row(row, asset.composition_attempt_id)
                if existing is None:
                    return _result(asset, "corrupt")
                existing_asset, existing_name = existing
                existing_path = self._safe_asset_path(existing_name)
                if (
                    existing_asset == asset
                    and _file_digest(existing_path) == asset.content_sha256
                    and existing_path.read_bytes() == image_bytes
                ):
                    return _result(asset, "confirmed")
                return _result(asset, "conflict")
            by_asset = connection.execute(
                "SELECT composition_attempt_id FROM composite_assets WHERE asset_id = ?",
                (asset.asset_id,),
            ).fetchone()
            if by_asset is not None:
                connection.rollback()
                return _result(asset, "conflict")
            if final_path.exists():
                if (
                    final_path.is_file()
                    and not final_path.is_symlink()
                    and not _is_reparse(final_path)
                    and _file_digest(final_path) == asset.content_sha256
                    and final_path.read_bytes() == image_bytes
                ):
                    connection.execute(
                        "INSERT INTO composite_assets VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            asset.composition_attempt_id,
                            asset.asset_id,
                            storage_name,
                            "deterministic_page_composition",
                            payload,
                            payload_digest,
                            asset.content_sha256,
                        ),
                    )
                    connection.commit()
                    return _result(asset, "registered")
                connection.rollback()
                return _result(asset, "conflict")
            staging_path = self._asset_directory / f".{uuid.uuid4().hex}.tmp"
            self._write_staging(staging_path, image_bytes)
            self._assert_live_directories()
            os.replace(staging_path, final_path)
            staging_path = None
            final_created = True
            if _file_digest(final_path) != asset.content_sha256:
                raise ValueError("composite exact readback failed")
            connection.execute(
                "INSERT INTO composite_assets VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    asset.composition_attempt_id,
                    asset.asset_id,
                    storage_name,
                    "deterministic_page_composition",
                    payload,
                    payload_digest,
                    asset.content_sha256,
                ),
            )
            connection.commit()
            return _result(asset, "registered")
        except sqlite3.IntegrityError:
            if connection is not None:
                _rollback(connection)
            return _result(asset, "conflict")
        except Exception:
            if connection is not None:
                _rollback(connection)
            if final_created:
                _delete_quietly(final_path)
            return _result(asset, "failed")
        finally:
            if staging_path is not None:
                _delete_quietly(staging_path)
            if connection is not None:
                connection.close()

    def read_verified(self, asset_id: str) -> DeterministicCompositeReadResult:
        try:
            resolved = logical_reference(asset_id, "composite asset")
        except ValueError:
            return DeterministicCompositeReadResult("", "corrupt")
        connection: sqlite3.Connection | None = None
        try:
            self._assert_live_directories()
            connection = self._connect()
            rows = connection.execute(
                "SELECT asset_id, storage_name, producer_kind, payload_json, payload_digest, content_sha256, "
                "composition_attempt_id FROM composite_assets WHERE asset_id = ?",
                (resolved,),
            ).fetchall()
            if not rows:
                return DeterministicCompositeReadResult(resolved, "missing")
            if len(rows) != 1:
                return DeterministicCompositeReadResult(resolved, "corrupt")
            row = rows[0]
            verified = _verified_row(row[:6], row[6])
            if verified is None:
                return DeterministicCompositeReadResult(resolved, "corrupt")
            asset, storage_name = verified
            if asset.asset_id != resolved:
                return DeterministicCompositeReadResult(resolved, "corrupt")
            path = self._safe_asset_path(storage_name)
            data = path.read_bytes()
            if len(data) > _MAX_BYTES or hashlib.sha256(data).hexdigest() != asset.content_sha256:
                return DeterministicCompositeReadResult(resolved, "corrupt")
            decoded = decode_png(data)
            if (decoded.width, decoded.height, decoded.channels) != (
                asset.width,
                asset.height,
                3,
            ):
                return DeterministicCompositeReadResult(resolved, "corrupt")
            return DeterministicCompositeReadResult(resolved, "found", asset, data)
        except Exception:
            return DeterministicCompositeReadResult(resolved, "corrupt")
        finally:
            if connection is not None:
                connection.close()

    def _assert_live_directories(self) -> None:
        if (
            not self._root.is_dir()
            or self._root.is_symlink()
            or _is_reparse(self._root)
            or not self._asset_directory.is_dir()
            or self._asset_directory.is_symlink()
            or _is_reparse(self._asset_directory)
            or self._asset_directory.resolve(strict=True).parent
            != self._root.resolve(strict=True)
        ):
            raise ValueError("composite owner root is unavailable")

    def _safe_asset_path(self, storage_name: str) -> Path:
        if not _safe_storage_name(storage_name):
            raise ValueError("unsafe composite storage name")
        path = self._asset_directory / storage_name
        if path.resolve(strict=False).parent != self._asset_directory:
            raise ValueError("composite asset escaped its owner root")
        if not path.is_file() or path.is_symlink() or _is_reparse(path):
            raise ValueError("composite asset is unavailable")
        return path

    @staticmethod
    def _write_staging(path: Path, data: bytes) -> None:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(descriptor, "wb", closefd=True) as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        except Exception:
            _delete_quietly(path)
            raise

    def _initialize_schema(self) -> None:
        connection: sqlite3.Connection | None = None
        try:
            connection = self._connect()
            connection.execute("BEGIN IMMEDIATE")
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            tables = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            if version == 0 and not tables:
                connection.execute(
                    "CREATE TABLE composite_assets (composition_attempt_id TEXT PRIMARY KEY, "
                    "asset_id TEXT UNIQUE NOT NULL, storage_name TEXT UNIQUE NOT NULL, "
                    "producer_kind TEXT NOT NULL, "
                    "payload_json TEXT NOT NULL, payload_digest TEXT NOT NULL, "
                    "content_sha256 TEXT NOT NULL)"
                )
                connection.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")
                connection.commit()
                return
            columns = {
                str(row[1])
                for row in connection.execute("PRAGMA table_info(composite_assets)")
            }
            if version != _SCHEMA_VERSION or columns != {
                "composition_attempt_id", "asset_id", "storage_name", "payload_json",
                "producer_kind", "payload_digest", "content_sha256",
            }:
                raise ValueError("composite owner is unavailable")
            connection.commit()
        except Exception as error:
            if connection is not None:
                _rollback(connection)
            raise ValueError("composite owner is unavailable") from error
        finally:
            if connection is not None:
                connection.close()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=5.0, isolation_level=None)
        mode = str(connection.execute("PRAGMA journal_mode = DELETE").fetchone()[0]).lower()
        if mode != "delete":
            connection.close()
            raise ValueError("composite owner is unavailable")
        connection.execute("PRAGMA synchronous = FULL")
        return connection


def _result(
    asset: PageCompositeAsset, outcome: CompositeOwnerOutcome
) -> DeterministicCompositeRegistrationResult:
    return DeterministicCompositeRegistrationResult(
        asset.composition_attempt_id, asset.asset_id, outcome, asset if outcome in {"registered", "confirmed"} else None
    )


def _verified_row(
    row: object, composition_attempt_id: str
) -> tuple[PageCompositeAsset, str] | None:
    if not isinstance(row, tuple) or len(row) != 6 or not all(
        isinstance(value, str) for value in row
    ):
        return None
    asset_id, storage_name, producer_kind, payload, payload_digest, content_sha256 = row
    if (
        producer_kind != "deterministic_page_composition"
        or _digest_text(payload) != payload_digest
        or not _safe_storage_name(storage_name)
    ):
        return None
    try:
        asset = PageCompositeAsset.model_validate_json(payload)
    except Exception:
        return None
    if (
        asset.composition_attempt_id != composition_attempt_id
        or asset.asset_id != asset_id
        or asset.content_sha256 != content_sha256
    ):
        return None
    return asset, storage_name


def _canonical_asset_json(asset: PageCompositeAsset) -> str:
    return json.dumps(
        asset.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )


def _digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _file_digest(path: Path) -> str | None:
    try:
        if not path.is_file() or path.is_symlink() or _is_reparse(path):
            return None
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _safe_storage_name(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 68
        and value.endswith(".png")
        and all(character in "0123456789abcdef" for character in value[:-4])
    )


def _prepare_root(root: Path) -> Path:
    if not isinstance(root, Path) or root.is_symlink() or _is_reparse(root):
        raise ValueError("composite owner root is unavailable")
    root.mkdir(parents=True, exist_ok=True)
    resolved = root.resolve(strict=True)
    if not resolved.is_dir() or resolved.is_symlink() or _is_reparse(resolved):
        raise ValueError("composite owner root is unavailable")
    return resolved


def _prepare_directory(root: Path, name: str) -> Path:
    path = root / name
    if path.exists() and (not path.is_dir() or path.is_symlink() or _is_reparse(path)):
        raise ValueError("composite asset directory is unavailable")
    path.mkdir(mode=0o700, exist_ok=True)
    resolved = path.resolve(strict=True)
    if resolved.parent != root or resolved.is_symlink() or _is_reparse(resolved):
        raise ValueError("composite asset directory is unavailable")
    return resolved


def _prepare_database(root: Path) -> Path:
    path = root / _DATABASE_FILENAME
    if path.exists() and (not path.is_file() or path.is_symlink() or _is_reparse(path)):
        raise ValueError("composite owner is unavailable")
    if path.resolve(strict=False).parent != root:
        raise ValueError("composite owner is unavailable")
    return path


def _is_reparse(path: Path) -> bool:
    try:
        attributes = path.lstat()
        return bool(
            getattr(attributes, "st_file_attributes", 0)
            & stat.FILE_ATTRIBUTE_REPARSE_POINT
        )
    except (FileNotFoundError, OSError):
        return False


def _rollback(connection: sqlite3.Connection) -> None:
    try:
        connection.rollback()
    except sqlite3.Error:
        pass


def _delete_quietly(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
