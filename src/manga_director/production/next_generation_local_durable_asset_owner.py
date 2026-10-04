"""Internal local durable asset owner with private files and SQLite registry.

This provider-neutral owner receives only private runtime material.  It never
selects a provider, invokes one, creates generation evidence, or exposes its
filesystem and registry implementation through durable reports.
"""

from __future__ import annotations

import ctypes
import hashlib
import os
import secrets
import sqlite3
import stat
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, BinaryIO, Protocol

from manga_director.production.next_generation_asset_registration import (
    AssetRegistrationRuntimeResult,
)
from manga_director.production.next_generation_generation_evidence import (
    GenerationOutputEvidenceDTO,
)

_MAX_REGISTERED_BYTES = 25 * 1024 * 1024
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_MEDIA_TYPE = "image/png"
_SCHEMA_VERSION = 1
_REGISTRY_FILENAME = "asset-owner.sqlite3"
_FILE_ATTRIBUTE_DIRECTORY = 0x00000010
_FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
_FILE_TYPE_DISK = 0x0001
_FILE_NAME_NORMALIZED = 0x00000000
_FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
_FILE_FLAG_BACKUP_SEMANTICS = 0x02000000


class _AssetVerificationIntegrityFailure(ValueError):
    """Private structural signal for an integrity-invalid owner asset."""


@dataclass(frozen=True, slots=True)
class OwnerRegistrationMaterial:
    """Provider-neutral private byte material for one registration attempt."""

    attempt_id: str
    provider_reference: str
    image_bytes: bytes = field(repr=False, compare=False)
    media_type: str = _MEDIA_TYPE


class ProviderNeutralAssetOwner(Protocol):
    """Internal provider-neutral durable registration capability."""

    def register(self, material: OwnerRegistrationMaterial) -> AssetRegistrationRuntimeResult: ...


@dataclass(frozen=True, slots=True)
class _OpenedAssetIdentity:
    """Windows metadata derived from the one leased asset HANDLE."""

    final_path: Path
    volume_serial: int
    file_index: int
    size: int
    attributes: int


@dataclass(frozen=True, slots=True)
class _OwnerRootIdentity:
    """Stable HANDLE identity for the trusted assets directory itself."""

    final_path: Path
    volume_serial: int
    file_index: int


@dataclass(frozen=True, slots=True)
class _OwnerRegistrationFactsV1:
    """Private facts released only by an exact one-shot registration result."""

    asset_id: str
    attempt_id: str
    provider_reference: str
    media_type: str
    digest: str


@dataclass(slots=True)
class _OwnerRegistrationCommitmentRecordV1:
    result: AssetRegistrationRuntimeResult
    facts: _OwnerRegistrationFactsV1
    storage_name: str
    root_identity: object
    owner_instance_nonce: bytes
    registration_nonce: bytes


class _OwnerRegistryCorruptV1(ValueError):
    """Private classification for a committed-registration integrity mismatch."""


class _AssetVerificationLease:
    """Private Windows read lease retained until a fenced application completes."""

    def __init__(self, stream: BinaryIO, identity: _OpenedAssetIdentity) -> None:
        self._stream = stream
        self._identity = identity

    def release(self) -> None:
        self._stream.close()


class LocalDurableAssetOwner(ProviderNeutralAssetOwner):
    """Own private local byte persistence and logical asset registration."""

    def __init__(self, owner_root: Path) -> None:
        self._root = _prepare_owner_root(owner_root)
        self._registry_directory = _prepare_child_directory(self._root, "registry")
        self._staging_directory = _prepare_child_directory(self._root, "staging")
        self._assets_directory = _prepare_child_directory(self._root, "assets")
        self._assets_root_identity = (
            _capture_windows_owner_root_identity(self._assets_directory)
            if os.name == "nt"
            else None
        )
        self._registry_path = _prepare_registry_path(self._registry_directory)
        self._initialize_registry()
        self._real_delivery_lock = threading.RLock()
        self._real_delivery_owner_instance_nonce = secrets.token_bytes(32)
        self._live_registration_commitments_by_result_id: dict[int, _OwnerRegistrationCommitmentRecordV1] = {}
        self._issued_registration_identities: set[tuple[object, ...]] = set()
        self._consumed_registration_identities: set[tuple[object, ...]] = set()
        self._unissuable_registration_identities: set[tuple[object, ...]] = set()

    def register(self, material: OwnerRegistrationMaterial) -> AssetRegistrationRuntimeResult:
        """Durably register valid material or return a redacted failed result."""

        if not _is_valid_material(material):
            return _failed_result(material)
        digest = hashlib.sha256(material.image_bytes).hexdigest()
        connection: sqlite3.Connection | None = None
        staging_path: Path | None = None
        final_path: Path | None = None
        durable_committed = False
        try:
            connection = self._connect()
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT asset_id, provider_reference, media_type, digest, storage_name "
                "FROM asset_registry WHERE attempt_id = ?",
                (material.attempt_id,),
            ).fetchone()
            if existing is not None:
                connection.rollback()
                # A replay remains compatible with the owner result contract,
                # but it never receives a new I02 commitment.
                return self._existing_result(material, digest, existing)

            asset_uuid = uuid.uuid4()
            asset_id = f"asset:generated:{asset_uuid}"
            storage_name = f"{asset_uuid.hex}.png"
            staging_path = self._staging_path(asset_uuid)
            final_path = self._final_path(storage_name)
            self._write_staging(staging_path, material.image_bytes)
            self._place_final(staging_path, final_path)
            self._commit_registration(
                connection,
                asset_id=asset_id,
                material=material,
                digest=digest,
                storage_name=storage_name,
            )
            durable_committed = True
            result = _registered_result(material, asset_id)
            try:
                self._issue_real_delivery_registration_commitment_v1(
                    result=result,
                    asset_id=asset_id,
                    material=material,
                    digest=digest,
                    storage_name=storage_name,
                )
            except Exception:
                return _failed_result(material)
            return result
        except Exception:
            if connection is not None:
                _rollback_quietly(connection)
            if not durable_committed and final_path is not None and final_path.exists():
                _delete_quietly(self, final_path)
            if not durable_committed and staging_path is not None and staging_path.exists():
                _delete_quietly(self, staging_path)
            return _failed_result(material)
        finally:
            if connection is not None:
                connection.close()

    def _issue_real_delivery_registration_commitment_v1(
        self,
        *,
        result: AssetRegistrationRuntimeResult,
        asset_id: str,
        material: OwnerRegistrationMaterial,
        digest: str,
        storage_name: str,
    ) -> None:
        """Create the sole volatile I02 registration authority after commit."""

        if result.outcome != "registered" or result.output is None:
            raise ValueError("asset registration authority is unavailable")
        facts = _OwnerRegistrationFactsV1(
            asset_id=asset_id,
            attempt_id=material.attempt_id,
            provider_reference=material.provider_reference,
            media_type=material.media_type,
            digest=digest,
        )
        registration_nonce = secrets.token_bytes(32)
        identity = self._real_delivery_registration_identity(
            facts, storage_name, self._assets_root_identity, registration_nonce
        )
        with self._real_delivery_lock:
            if (
                identity in self._issued_registration_identities
                or identity in self._consumed_registration_identities
                or identity in self._unissuable_registration_identities
            ):
                raise ValueError("asset registration authority is unavailable")
            try:
                self._live_registration_commitments_by_result_id[id(result)] = _OwnerRegistrationCommitmentRecordV1(
                    result=result,
                    facts=facts,
                    storage_name=storage_name,
                    root_identity=self._assets_root_identity,
                    owner_instance_nonce=self._real_delivery_owner_instance_nonce,
                    registration_nonce=registration_nonce,
                )
                self._issued_registration_identities.add(identity)
            except Exception:
                self._unissuable_registration_identities.add(identity)
                raise

    def _consume_real_delivery_registration_v1(self, result: object) -> _OwnerRegistrationFactsV1:
        """Authenticate and tombstone one exact successful owner result."""

        with self._real_delivery_lock:
            record = self._live_registration_commitments_by_result_id.get(id(result))
            if (
                type(result) is not AssetRegistrationRuntimeResult
                or record is None
                or record.result is not result
                or record.owner_instance_nonce is not self._real_delivery_owner_instance_nonce
                or result.outcome != "registered"
                or result.output is None
            ):
                raise ValueError("asset registration authority is unavailable")
            self._assert_real_delivery_registration_record_v1(record)
            identity = self._real_delivery_registration_identity(
                record.facts, record.storage_name, record.root_identity, record.registration_nonce
            )
            if identity not in self._issued_registration_identities or identity in self._consumed_registration_identities:
                raise ValueError("asset registration authority is unavailable")
            del self._live_registration_commitments_by_result_id[id(result)]
            self._issued_registration_identities.remove(identity)
            self._consumed_registration_identities.add(identity)
            return record.facts

    def _assert_real_delivery_registration_record_v1(
        self, record: _OwnerRegistrationCommitmentRecordV1
    ) -> None:
        connection: sqlite3.Connection | None = None
        try:
            connection = self._connect()
            if not _registry_schema_is_valid(connection):
                raise _OwnerRegistryCorruptV1("asset owner registry is corrupt")
            rows = connection.execute(
                "SELECT asset_id, attempt_id, provider_reference, media_type, digest, storage_name "
                "FROM asset_registry WHERE asset_id = ?",
                (record.facts.asset_id,),
            ).fetchall()
            expected = (
                record.facts.asset_id,
                record.facts.attempt_id,
                record.facts.provider_reference,
                record.facts.media_type,
                record.facts.digest,
                record.storage_name,
            )
            if len(rows) != 1 or tuple(str(value) for value in rows[0]) != expected:
                raise _OwnerRegistryCorruptV1("asset owner registry is corrupt")
            if not _private_file_matches(self._final_path(record.storage_name), record.facts.digest):
                raise _OwnerRegistryCorruptV1("asset owner registry is corrupt")
        except _OwnerRegistryCorruptV1:
            raise
        except (OSError, sqlite3.Error, TypeError, ValueError) as error:
            raise _OwnerRegistryCorruptV1("asset owner registry is corrupt") from error
        finally:
            if connection is not None:
                connection.close()

    def _real_delivery_registration_identity(
        self,
        facts: _OwnerRegistrationFactsV1,
        storage_name: str,
        root_identity: object,
        registration_nonce: bytes,
    ) -> tuple[object, ...]:
        return (
            self._real_delivery_owner_instance_nonce,
            registration_nonce,
            facts.asset_id,
            facts.attempt_id,
            facts.provider_reference,
            facts.media_type,
            facts.digest,
            storage_name,
            root_identity,
        )

    def _verify_for_generated_application(
        self,
        *,
        attempt_id: str,
        provider_reference: str,
        output_asset_id: str,
        expected_sha256: str,
        expected_media_type: str,
    ) -> _AssetVerificationLease:
        """Lease one exact owner asset without accepting a caller-selected path.

        This is private D10 composition support.  The exclusive Windows share
        mode prevents another Windows writer from replacing the verified file
        until the canonical page CAS has completed.
        """

        if (
            not _is_logical_reference(attempt_id)
            or not _is_logical_reference(provider_reference)
            or not _is_logical_reference(output_asset_id)
            or not _is_sha256(expected_sha256)
            or expected_media_type != _MEDIA_TYPE
        ):
            raise ValueError("asset verification input is unavailable")
        connection: sqlite3.Connection | None = None
        try:
            connection = self._connect()
            rows = connection.execute(
                "SELECT attempt_id, provider_reference, media_type, digest, storage_name "
                "FROM asset_registry WHERE asset_id = ?",
                (output_asset_id,),
            ).fetchall()
            if len(rows) != 1:
                raise ValueError("asset verification record is unavailable")
            row = rows[0]
            if (
                row[0] != attempt_id
                or row[1] != provider_reference
                or row[2] != expected_media_type
                or row[3] != expected_sha256
            ):
                raise _AssetVerificationIntegrityFailure("asset verification binding is invalid")
            path = self._final_path(str(row[4]))
            return _open_verified_windows_lease(
                path,
                self._assets_directory,
                self._assets_root_identity,
                expected_sha256,
            )
        finally:
            if connection is not None:
                connection.close()

    def _initialize_registry(self) -> None:
        existed = self._registry_path.exists()
        connection: sqlite3.Connection | None = None
        try:
            connection = self._connect()
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if not existed:
                if version != 0 or _has_user_tables(connection):
                    raise ValueError("asset owner registry is unavailable")
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    "CREATE TABLE asset_registry ("
                    "asset_id TEXT PRIMARY KEY, "
                    "attempt_id TEXT NOT NULL UNIQUE, "
                    "provider_reference TEXT NOT NULL, "
                    "media_type TEXT NOT NULL, "
                    "digest TEXT NOT NULL, "
                    "storage_name TEXT NOT NULL UNIQUE"
                    ")"
                )
                connection.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")
                connection.commit()
                return
            if version != _SCHEMA_VERSION or not _registry_schema_is_valid(connection):
                raise ValueError("asset owner registry is unavailable")
        except (sqlite3.Error, ValueError, TypeError) as error:
            if connection is not None:
                _rollback_quietly(connection)
            raise ValueError("asset owner registry is unavailable") from error
        finally:
            if connection is not None:
                connection.close()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._registry_path, timeout=5.0, isolation_level=None)
        journal_mode = str(connection.execute("PRAGMA journal_mode = DELETE").fetchone()[0]).lower()
        if journal_mode != "delete":
            connection.close()
            raise ValueError("asset owner registry is unavailable")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    def _existing_result(
        self,
        material: OwnerRegistrationMaterial,
        digest: str,
        row: tuple[str, str, str, str, str],
    ) -> AssetRegistrationRuntimeResult:
        asset_id, provider_reference, media_type, stored_digest, storage_name = row
        if (
            provider_reference != material.provider_reference
            or media_type != material.media_type
            or stored_digest != digest
        ):
            return _conflict_result(material)
        try:
            final_path = self._final_path(storage_name)
            if not _private_file_matches(final_path, digest):
                return _failed_result(material)
        except Exception:
            return _failed_result(material)
        return _registered_result(material, asset_id)

    def _write_staging(self, path: Path, image_bytes: bytes) -> None:
        _assert_private_path(path, self._staging_directory)
        with path.open("xb") as stream:
            stream.write(image_bytes)
            stream.flush()
            os.fsync(stream.fileno())

    def _place_final(self, staging_path: Path, final_path: Path) -> None:
        _assert_private_path(staging_path, self._staging_directory)
        _assert_private_path(final_path, self._assets_directory)
        if final_path.exists() or _is_link_or_reparse_point(final_path):
            raise ValueError("asset owner storage is unavailable")
        os.replace(staging_path, final_path)
        _sync_directory_if_supported(self._assets_directory)

    def _commit_registration(
        self,
        connection: sqlite3.Connection,
        *,
        asset_id: str,
        material: OwnerRegistrationMaterial,
        digest: str,
        storage_name: str,
    ) -> None:
        connection.execute(
            "INSERT INTO asset_registry "
            "(asset_id, attempt_id, provider_reference, media_type, digest, storage_name) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                asset_id,
                material.attempt_id,
                material.provider_reference,
                material.media_type,
                digest,
                storage_name,
            ),
        )
        connection.commit()

    def _staging_path(self, asset_uuid: uuid.UUID) -> Path:
        return _private_child(self._staging_directory, f"{asset_uuid.hex}.stage")

    def _final_path(self, storage_name: str) -> Path:
        if not _is_storage_name(storage_name):
            raise ValueError("asset owner storage is unavailable")
        return _private_child(self._assets_directory, storage_name)

    @staticmethod
    def _delete_private_file(path: Path) -> None:
        try:
            if path.exists() and not _is_link_or_reparse_point(path):
                path.unlink()
        except OSError:
            pass


def _prepare_owner_root(owner_root: Path) -> Path:
    if not isinstance(owner_root, Path) or not owner_root.is_absolute() or ".." in owner_root.parts:
        raise ValueError("asset owner root is unavailable")
    if owner_root.exists() and _is_link_or_reparse_point(owner_root):
        raise ValueError("asset owner root is unavailable")
    try:
        owner_root.mkdir(parents=True, exist_ok=True)
        root = owner_root.resolve(strict=True)
    except OSError as error:
        raise ValueError("asset owner root is unavailable") from error
    if _is_link_or_reparse_point(root) or not root.is_dir():
        raise ValueError("asset owner root is unavailable")
    return root


def _prepare_child_directory(root: Path, name: str) -> Path:
    path = _private_child(root, name)
    try:
        path.mkdir(exist_ok=True)
    except OSError as error:
        raise ValueError("asset owner root is unavailable") from error
    if _is_link_or_reparse_point(path) or not path.is_dir():
        raise ValueError("asset owner root is unavailable")
    return path


def _prepare_registry_path(registry_directory: Path) -> Path:
    path = _private_child(registry_directory, _REGISTRY_FILENAME)
    if path.exists() and (_is_link_or_reparse_point(path) or not path.is_file()):
        raise ValueError("asset owner registry is unavailable")
    return path


def _private_child(parent: Path, name: str) -> Path:
    child = parent / name
    _assert_private_path(child, parent)
    return child


def _assert_private_path(path: Path, parent: Path) -> None:
    if not path.is_absolute() or path.parent != parent or path.name != path.name.strip() or not path.name:
        raise ValueError("asset owner storage is unavailable")
    if _is_link_or_reparse_point(path):
        raise ValueError("asset owner storage is unavailable")
    try:
        path.resolve(strict=False).relative_to(parent.resolve(strict=True))
    except (OSError, ValueError) as error:
        raise ValueError("asset owner storage is unavailable") from error


def _is_link_or_reparse_point(path: Path) -> bool:
    try:
        status = path.lstat()
    except FileNotFoundError:
        return False
    attributes = getattr(status, "st_file_attributes", 0)
    reparse_point = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return path.is_symlink() or bool(reparse_point and attributes & reparse_point)


def _has_user_tables(connection: sqlite3.Connection) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' LIMIT 1"
    ).fetchone() is not None


def _registry_schema_is_valid(connection: sqlite3.Connection) -> bool:
    expected = {
        "asset_id",
        "attempt_id",
        "provider_reference",
        "media_type",
        "digest",
        "storage_name",
    }
    columns = {
        str(row[1])
        for row in connection.execute("PRAGMA table_info(asset_registry)").fetchall()
        if len(row) > 1
    }
    return columns == expected


def _is_valid_material(material: object) -> bool:
    if not isinstance(material, OwnerRegistrationMaterial):
        return False
    if not _is_logical_reference(material.attempt_id) or not _is_logical_reference(
        material.provider_reference
    ):
        return False
    image_bytes = material.image_bytes
    return bool(
        material.media_type == _MEDIA_TYPE
        and isinstance(image_bytes, bytes)
        and image_bytes
        and len(image_bytes) <= _MAX_REGISTERED_BYTES
        and image_bytes.startswith(_PNG_SIGNATURE)
    )


def _is_logical_reference(value: object) -> bool:
    return bool(
        isinstance(value, str)
        and value
        and value == value.strip()
        and not any(character.isspace() for character in value)
        and not value.startswith(("/", "\\"))
        and "://" not in value
    )


def _is_storage_name(value: object) -> bool:
    path = Path(value) if isinstance(value, str) else None
    return bool(
        path is not None
        and path.name == value
        and path.suffix == ".png"
        and len(path.stem) == 32
        and all(character in "0123456789abcdef" for character in path.stem)
    )


def _private_file_matches(path: Path, expected_digest: str) -> bool:
    _assert_private_path(path, path.parent)
    if _is_link_or_reparse_point(path) or not path.is_file() or path.stat().st_size > _MAX_REGISTERED_BYTES:
        return False
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(64 * 1024):
            digest.update(chunk)
    return digest.hexdigest() == expected_digest


def _open_verified_windows_lease(
    path: Path,
    owner_root: Path,
    expected_owner_root: _OwnerRootIdentity | None,
    expected_digest: str,
) -> _AssetVerificationLease:
    """Lease and hash the exact Windows HANDLE, never a later path reopen.

    The caller derives ``path`` from the owner registry.  This function rejects
    a handle whose final normalized path, attributes, or file identity is not
    the expected ordinary file beneath that same owner root.
    """

    _assert_private_path(path, owner_root)
    if (
        os.name != "nt"
        or expected_owner_root is None
        or _is_link_or_reparse_point(path)
        or not _owner_root_identity_matches(owner_root, expected_owner_root)
    ):
        raise ValueError("asset verification lease is unavailable")
    import msvcrt

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    handle = _open_windows_asset_handle(kernel32, path)
    descriptor = msvcrt.open_osfhandle(int(handle), os.O_RDONLY)
    stream = os.fdopen(descriptor, "rb", closefd=True)
    try:
        identity = _windows_handle_identity(kernel32, handle)
        if not _handle_is_expected_owner_asset(
            identity, path, expected_owner_root
        ):
            raise _AssetVerificationIntegrityFailure("asset verification identity is invalid")
        digest = hashlib.sha256()
        while chunk := stream.read(64 * 1024):
            digest.update(chunk)
        if digest.hexdigest() != expected_digest:
            raise _AssetVerificationIntegrityFailure("asset verification digest is invalid")
        stream.seek(0)
        return _AssetVerificationLease(stream, identity)
    except Exception:
        stream.close()
        raise


def _open_windows_asset_handle(kernel32: Any, path: Path) -> int:
    create_file = kernel32.CreateFileW
    create_file.argtypes = (
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
    )
    create_file.restype = ctypes.c_void_p
    handle = create_file(
        str(path),
        0x80000000,  # GENERIC_READ
        0x00000001,  # FILE_SHARE_READ; deny new writer/delete sharing
        None,
        3,  # OPEN_EXISTING
        0x00000080 | _FILE_FLAG_OPEN_REPARSE_POINT,
        None,
    )
    invalid = ctypes.c_void_p(-1).value
    if not handle or handle == invalid:
        raise ValueError("asset verification lease is unavailable")
    return int(handle)


def _capture_windows_owner_root_identity(owner_root: Path) -> _OwnerRootIdentity:
    """Pin the ordinary assets directory identity at owner construction."""

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = (
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
    )
    create_file.restype = ctypes.c_void_p
    handle = create_file(
        str(owner_root),
        0x80000000,  # GENERIC_READ
        0x00000007,  # permit normal owner directory use after this snapshot
        None,
        3,  # OPEN_EXISTING
        _FILE_FLAG_BACKUP_SEMANTICS | _FILE_FLAG_OPEN_REPARSE_POINT,
        None,
    )
    invalid = ctypes.c_void_p(-1).value
    if not handle or handle == invalid:
        raise ValueError("asset owner root is unavailable")
    try:
        identity = _windows_handle_identity(kernel32, int(handle))
        if (
            not identity.attributes & _FILE_ATTRIBUTE_DIRECTORY
            or identity.attributes & _FILE_ATTRIBUTE_REPARSE_POINT
            or identity.volume_serial == 0
            or identity.file_index == 0
        ):
            raise ValueError("asset owner root is unavailable")
        return _OwnerRootIdentity(
            final_path=identity.final_path,
            volume_serial=identity.volume_serial,
            file_index=identity.file_index,
        )
    finally:
        kernel32.CloseHandle(ctypes.c_void_p(handle))


def _windows_handle_identity(kernel32: Any, handle: int) -> _OpenedAssetIdentity:
    class _FileTime(ctypes.Structure):
        _fields_ = [("low", ctypes.c_uint32), ("high", ctypes.c_uint32)]

    class _ByHandleFileInformation(ctypes.Structure):
        _fields_ = [
            ("attributes", ctypes.c_uint32),
            ("creation", _FileTime),
            ("access", _FileTime),
            ("write", _FileTime),
            ("volume_serial", ctypes.c_uint32),
            ("size_high", ctypes.c_uint32),
            ("size_low", ctypes.c_uint32),
            ("links", ctypes.c_uint32),
            ("index_high", ctypes.c_uint32),
            ("index_low", ctypes.c_uint32),
        ]

    get_information = kernel32.GetFileInformationByHandle
    get_information.argtypes = (ctypes.c_void_p, ctypes.POINTER(_ByHandleFileInformation))
    get_information.restype = ctypes.c_bool
    information = _ByHandleFileInformation()
    raw_handle = ctypes.c_void_p(handle)
    if not get_information(raw_handle, ctypes.byref(information)):
        raise ValueError("asset verification handle metadata is unavailable")
    get_file_type = kernel32.GetFileType
    get_file_type.argtypes = (ctypes.c_void_p,)
    get_file_type.restype = ctypes.c_uint32
    if get_file_type(raw_handle) != _FILE_TYPE_DISK:
        raise ValueError("asset verification handle is not a disk file")
    final_path = _windows_final_path(kernel32, raw_handle)
    return _OpenedAssetIdentity(
        final_path=final_path,
        volume_serial=int(information.volume_serial),
        file_index=(int(information.index_high) << 32) | int(information.index_low),
        size=(int(information.size_high) << 32) | int(information.size_low),
        attributes=int(information.attributes),
    )


def _windows_final_path(kernel32: Any, handle: Any) -> Path:
    get_final_path = kernel32.GetFinalPathNameByHandleW
    get_final_path.argtypes = (ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32)
    get_final_path.restype = ctypes.c_uint32
    required = int(get_final_path(handle, None, 0, _FILE_NAME_NORMALIZED))
    if required < 1:
        raise ValueError("asset verification final path is unavailable")
    buffer = ctypes.create_unicode_buffer(required + 1)
    written = int(get_final_path(handle, buffer, len(buffer), _FILE_NAME_NORMALIZED))
    if written < 1 or written >= len(buffer):
        raise ValueError("asset verification final path is unavailable")
    raw = buffer.value
    if raw.startswith("\\\\?\\UNC\\"):
        raw = "\\\\" + raw[8:]
    elif raw.startswith("\\\\?\\"):
        raw = raw[4:]
    return Path(raw)


def _handle_is_expected_owner_asset(
    identity: _OpenedAssetIdentity,
    path: Path,
    expected_owner_root: _OwnerRootIdentity,
) -> bool:
    try:
        expected = path.resolve(strict=True)
        final = identity.final_path.resolve(strict=False)
        final.relative_to(expected_owner_root.final_path)
    except (OSError, ValueError):
        return False
    return bool(
        _windows_paths_equal(final, expected)
        and identity.volume_serial != 0
        and identity.file_index != 0
        and 0 < identity.size <= _MAX_REGISTERED_BYTES
        and not identity.attributes & (_FILE_ATTRIBUTE_DIRECTORY | _FILE_ATTRIBUTE_REPARSE_POINT)
    )


def _owner_root_identity_matches(
    owner_root: Path, expected: _OwnerRootIdentity
) -> bool:
    try:
        current = _capture_windows_owner_root_identity(owner_root)
    except (OSError, ValueError):
        return False
    return (
        _windows_paths_equal(current.final_path, expected.final_path)
        and current.volume_serial == expected.volume_serial
        and current.file_index == expected.file_index
    )


def _windows_paths_equal(left: Path, right: Path) -> bool:
    return str(left).replace("/", "\\").casefold() == str(right).replace("/", "\\").casefold()


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def _sync_directory_if_supported(directory: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _rollback_quietly(connection: sqlite3.Connection) -> None:
    try:
        connection.rollback()
    except sqlite3.Error:
        pass


def _delete_quietly(owner: LocalDurableAssetOwner, path: Path) -> None:
    try:
        owner._delete_private_file(path)
    except OSError:
        pass


def _registered_result(
    material: OwnerRegistrationMaterial, asset_id: str
) -> AssetRegistrationRuntimeResult:
    return AssetRegistrationRuntimeResult(
        attempt_id=material.attempt_id,
        provider_reference=material.provider_reference,
        outcome="registered",
        output=GenerationOutputEvidenceDTO(output_asset_id=asset_id, media_type=material.media_type),
        durable_registration_confirmed=True,
    )


def _conflict_result(material: OwnerRegistrationMaterial) -> AssetRegistrationRuntimeResult:
    return AssetRegistrationRuntimeResult(
        attempt_id=material.attempt_id,
        provider_reference=material.provider_reference,
        outcome="idempotency_conflict",
    )


def _failed_result(material: object) -> AssetRegistrationRuntimeResult:
    attempt_id = material.attempt_id if isinstance(material, OwnerRegistrationMaterial) else ""
    provider_reference = material.provider_reference if isinstance(material, OwnerRegistrationMaterial) else ""
    return AssetRegistrationRuntimeResult(
        attempt_id=attempt_id,
        provider_reference=provider_reference,
        outcome="failed",
    )
