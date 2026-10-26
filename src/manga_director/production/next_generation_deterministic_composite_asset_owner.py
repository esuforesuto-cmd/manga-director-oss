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


@dataclass(frozen=True, slots=True)
class DeterministicCompositeInventoryObservation:
    outcome: Literal["found", "missing", "corrupt", "ambiguous"]
    composition_attempt_ids: tuple[str, ...] = ()
    assets: tuple[PageCompositeAsset, ...] = field(default=(), repr=False)
    missing_composition_attempt_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DeterministicCompositePageObservation:
    outcome: Literal["found", "missing", "corrupt", "ambiguous"]
    composition_attempt_ids: tuple[str, ...] = ()
    assets: tuple[PageCompositeAsset, ...] = field(default=(), repr=False)


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

    def observe_attempts(  # noqa: C901 - one closed integrity inventory.
        self, composition_attempt_ids: tuple[str, ...]
    ) -> DeterministicCompositeInventoryObservation:
        if len(composition_attempt_ids) != len(set(composition_attempt_ids)):
            return DeterministicCompositeInventoryObservation("ambiguous")
        path_status = _readonly_composite_owner_status(
            self._root, self._asset_directory, self._database_path
        )
        if path_status == "missing":
            return DeterministicCompositeInventoryObservation(
                "missing",
                missing_composition_attempt_ids=tuple(
                    sorted(composition_attempt_ids)
                ),
            )
        if path_status == "corrupt":
            return DeterministicCompositeInventoryObservation("corrupt")
        try:
            uri = f"{self._database_path.as_uri()}?mode=ro"
            with sqlite3.connect(uri, uri=True) as connection:
                connection.execute("PRAGMA query_only = ON")
                if int(connection.execute("PRAGMA user_version").fetchone()[0]) != _SCHEMA_VERSION:
                    return DeterministicCompositeInventoryObservation("corrupt")
                if not _composite_schema_is_exact(connection):
                    return DeterministicCompositeInventoryObservation("corrupt")
                all_rows = connection.execute(
                    "SELECT asset_id, storage_name, producer_kind, payload_json, "
                    "payload_digest, content_sha256, composition_attempt_id "
                    "FROM composite_assets"
                ).fetchall()
                verified_assets: dict[str, PageCompositeAsset] = {}
                for row in all_rows:
                    verified = _verified_row(row[:6], row[6])
                    if verified is None:
                        return DeterministicCompositeInventoryObservation("corrupt")
                    asset, storage_name = verified
                    if asset.composition_attempt_id in verified_assets:
                        return DeterministicCompositeInventoryObservation("ambiguous")
                    path = self._safe_asset_path(storage_name)
                    if _file_digest(path) != asset.content_sha256:
                        return DeterministicCompositeInventoryObservation("corrupt")
                    verified_assets[asset.composition_attempt_id] = asset
                found: list[str] = []
                assets: list[PageCompositeAsset] = []
                for attempt_id in composition_attempt_ids:
                    found_asset = verified_assets.get(attempt_id)
                    if found_asset is None:
                        continue
                    found.append(attempt_id)
                    assets.append(found_asset)
        except Exception:
            return DeterministicCompositeInventoryObservation("corrupt")
        missing = tuple(sorted(set(composition_attempt_ids) - set(found)))
        if not found:
            return DeterministicCompositeInventoryObservation(
                "missing", missing_composition_attempt_ids=missing
            )
        return DeterministicCompositeInventoryObservation(
            "found",
            tuple(sorted(found)),
            tuple(sorted(assets, key=lambda item: item.composition_attempt_id)),
            missing,
        )

    @classmethod
    def observe_attempts_at(
        cls, owner_root: Path, composition_attempt_ids: tuple[str, ...]
    ) -> DeterministicCompositeInventoryObservation:
        owner = object.__new__(cls)
        owner._root = owner_root
        owner._asset_directory = owner_root / _ASSET_DIRECTORY
        owner._database_path = owner_root / _DATABASE_FILENAME
        return owner.observe_attempts(composition_attempt_ids)

    def observe_page(
        self, project_id: str, page_id: str
    ) -> DeterministicCompositePageObservation:
        """Verify and return composites whose source manifest owns this Page."""

        path_status = _readonly_composite_owner_status(
            self._root, self._asset_directory, self._database_path
        )
        if path_status == "missing":
            return DeterministicCompositePageObservation("missing")
        if path_status == "corrupt":
            return DeterministicCompositePageObservation("corrupt")
        try:
            uri = f"{self._database_path.as_uri()}?mode=ro"
            with sqlite3.connect(uri, uri=True) as connection:
                connection.execute("PRAGMA query_only = ON")
                if (
                    int(connection.execute("PRAGMA user_version").fetchone()[0])
                    != _SCHEMA_VERSION
                    or not _composite_schema_is_exact(connection)
                ):
                    return DeterministicCompositePageObservation("corrupt")
                rows = connection.execute(
                    "SELECT asset_id, storage_name, producer_kind, payload_json, "
                    "payload_digest, content_sha256, composition_attempt_id "
                    "FROM composite_assets"
                ).fetchall()
            matching: list[PageCompositeAsset] = []
            observed_ids: set[str] = set()
            for row in rows:
                verified = _verified_row(row[:6], row[6])
                if verified is None or row[6] in observed_ids:
                    return DeterministicCompositePageObservation("corrupt")
                asset, storage_name = verified
                if _file_digest(self._safe_asset_path(storage_name)) != asset.content_sha256:
                    return DeterministicCompositePageObservation("corrupt")
                observed_ids.add(asset.composition_attempt_id)
                source = asset.ordered_sources[0]
                if source.project_id == project_id and source.page_id == page_id:
                    matching.append(asset)
        except Exception:
            return DeterministicCompositePageObservation("corrupt")
        if not matching:
            return DeterministicCompositePageObservation("missing")
        ordered = tuple(sorted(matching, key=lambda item: item.composition_attempt_id))
        attempt_ids = tuple(item.composition_attempt_id for item in ordered)
        if len(attempt_ids) != len(set(attempt_ids)):
            return DeterministicCompositePageObservation(
                "ambiguous", attempt_ids, ordered
            )
        return DeterministicCompositePageObservation("found", attempt_ids, ordered)

    @classmethod
    def observe_page_at(
        cls, owner_root: Path, project_id: str, page_id: str
    ) -> DeterministicCompositePageObservation:
        owner = object.__new__(cls)
        owner._root = owner_root
        owner._asset_directory = owner_root / _ASSET_DIRECTORY
        owner._database_path = owner_root / _DATABASE_FILENAME
        return owner.observe_page(project_id, page_id)

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


def _readonly_composite_owner_status(
    root: Path, asset_directory: Path, database: Path
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
            or _readonly_path_kind(asset_directory) != "directory"
            or asset_directory.resolve(strict=True).parent != root.resolve(strict=True)
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


def _composite_schema_is_exact(connection: sqlite3.Connection) -> bool:
    objects = connection.execute(
        "SELECT type, name, tbl_name FROM sqlite_master "
        "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
    ).fetchall()
    if objects != [("table", "composite_assets", "composite_assets")]:
        return False
    columns = tuple(
        (str(row[1]), str(row[2]).upper(), int(row[3]), row[4], int(row[5]))
        for row in connection.execute("PRAGMA table_info(composite_assets)")
    )
    if columns != (
        ("composition_attempt_id", "TEXT", 0, None, 1),
        ("asset_id", "TEXT", 1, None, 0),
        ("storage_name", "TEXT", 1, None, 0),
        ("producer_kind", "TEXT", 1, None, 0),
        ("payload_json", "TEXT", 1, None, 0),
        ("payload_digest", "TEXT", 1, None, 0),
        ("content_sha256", "TEXT", 1, None, 0),
    ):
        return False
    indexes = connection.execute("PRAGMA index_list(composite_assets)").fetchall()
    observed: set[tuple[int, str, int, tuple[str, ...]]] = set()
    for index in indexes:
        if len(index) != 5 or not isinstance(index[1], str):
            return False
        index_columns = tuple(
            str(row[2])
            for row in connection.execute(
                f"PRAGMA index_info({index[1]})"
            ).fetchall()
        )
        observed.add((int(index[2]), str(index[3]), int(index[4]), index_columns))
    return observed == {
        (1, "pk", 0, ("composition_attempt_id",)),
        (1, "u", 0, ("asset_id",)),
        (1, "u", 0, ("storage_name",)),
    }


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
