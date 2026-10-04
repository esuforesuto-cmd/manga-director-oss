"""Private RFC-01 I02a registered-owner verifier.

The verifier is intentionally read-only.  It validates a protocol-authenticated
request against the existing LocalFile owner registry and one leased Windows
file, then asks the already-paired protocol to issue a volatile completion
capability.  It imports neither I02, I03, I04 nor any workflow authority.
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, Final

from manga_director.production import future_real_delivery_i02a_protocol as protocol
from manga_director.production import next_generation_local_durable_asset_owner as owner_module
from manga_director.production.future_real_delivery_i01 import (
    StrictLocalAssetRegistryIntegrityReaderV1,
    StrictPngStructuralValidatorV1,
)
from manga_director.production.next_generation_local_durable_asset_owner import (
    LocalDurableAssetOwner,
)

_MAX_PNG_BYTES: Final = 25 * 1024 * 1024
_MEDIA_TYPE: Final = "image/png"
_REGISTRY_FILENAME: Final = "asset-owner.sqlite3"
_UNAVAILABLE: Final = "RFC-01 I02a registered owner verification is unavailable"
_GENERIC_READ: Final = 0x80000000
_FILE_SHARE_READ: Final = 0x00000001
_FILE_SHARE_WRITE: Final = 0x00000002
_OPEN_EXISTING: Final = 3
_FILE_ATTRIBUTE_NORMAL: Final = 0x00000080
_FILE_FLAG_OPEN_REPARSE_POINT: Final = 0x00200000
_FILE_FLAG_BACKUP_SEMANTICS: Final = 0x02000000


def _unavailable() -> ValueError:
    return ValueError(_UNAVAILABLE)


@dataclass(frozen=True, slots=True)
class _OwnerRegistryRecordV1:
    asset_id: str
    attempt_id: str
    provider_reference: str
    media_type: str
    digest: str
    storage_name: str


class _RootLeaseV1:
    __slots__ = ("_kernel32", "_handle", "identity", "_released")

    def __init__(self, kernel32: Any, handle: int, identity: owner_module._OpenedAssetIdentity) -> None:
        self._kernel32 = kernel32
        self._handle = handle
        self.identity = identity
        self._released = False

    def release(self) -> None:
        if not self._released:
            self._released = True
            if not self._kernel32.CloseHandle(ctypes.c_void_p(self._handle)):
                raise _unavailable()


class _FinalFileLeaseV1:
    __slots__ = ("_stream", "identity", "_released")

    def __init__(self, stream: BinaryIO, identity: owner_module._OpenedAssetIdentity) -> None:
        self._stream = stream
        self.identity = identity
        self._released = False

    def read_all(self) -> bytes:
        self._stream.seek(0)
        return self._stream.read()

    def release(self) -> None:
        if not self._released:
            self._released = True
            self._stream.close()


class _VerifierLeaseRecordV1:
    __slots__ = ("_root", "_file", "_released")

    def __init__(self, root: _RootLeaseV1, final_file: _FinalFileLeaseV1) -> None:
        self._root = root
        self._file = final_file
        self._released = False

    def release(self) -> None:
        if self._released:
            return
        self._released = True
        error: Exception | None = None
        try:
            self._file.release()
        except Exception as caught:
            error = caught
        try:
            self._root.release()
        except Exception as caught:
            error = error or caught
        if error is not None:
            raise _unavailable() from error


class PrivateRegisteredOwnerAssetVerifierV1:
    """Read-only I02a verifier for one paired registered-owner request."""

    __slots__ = ("_owner", "_verifier_peer", "_registry_reader", "_png_validator")

    def __init__(
        self,
        owner: LocalDurableAssetOwner,
        verifier_peer: protocol._RegisteredOwnerVerificationVerifierPeerV1,
    ) -> None:
        if (
            type(owner) is not LocalDurableAssetOwner
            or type(verifier_peer) is not protocol._RegisteredOwnerVerificationVerifierPeerV1
        ):
            raise _unavailable()
        self._owner = owner
        self._verifier_peer = verifier_peer
        self._registry_reader = StrictLocalAssetRegistryIntegrityReaderV1(owner)
        self._png_validator = StrictPngStructuralValidatorV1()

    def verify(
        self,
        request: protocol._RegisteredOwnerVerificationRequestV1,
    ) -> protocol._RegisteredOwnerVerificationCompletionCapabilityV1:
        """Validate one live request and issue its sole completion capability."""

        facts = self._verifier_peer._validate_registered_owner_verification_request_v1(request)
        _validate_request_facts(facts)
        lease_record: _VerifierLeaseRecordV1 | None = None
        try:
            record = self._read_exact_owner_record(facts)
            if _asset_registration_digest(record) != facts.asset_registration_digest:
                raise _unavailable()
            root_lease = _open_root_lease(self._owner)
            try:
                final_path = _derive_final_asset_path(self._owner, record.storage_name)
                final_lease = _open_final_file_lease(final_path, root_lease, self._owner)
            except Exception:
                root_lease.release()
                raise
            lease_record = _VerifierLeaseRecordV1(root_lease, final_lease)
            image_bytes = final_lease.read_all()
            actual_sha256 = hashlib.sha256(image_bytes).hexdigest()
            if (
                len(image_bytes) != facts.expected_byte_length
                or actual_sha256 != facts.sha256
                or actual_sha256 != record.digest
                or facts.media_type != _MEDIA_TYPE
                or record.media_type != _MEDIA_TYPE
            ):
                raise _unavailable()
            self._png_validator.validate(image_bytes)
            verified = protocol._VerifiedOwnerAssetFactsV1(
                assets_root_identity=_root_identity_tuple(root_lease.identity),
                final_file_identity=_file_identity_tuple(final_lease.identity),
                verified_sha256=actual_sha256,
                verified_byte_length=len(image_bytes),
                verified_media_type=_MEDIA_TYPE,
                owner_attempt_id=record.attempt_id,
                owner_provider_reference=record.provider_reference,
                owner_digest=record.digest,
                owner_storage_name=record.storage_name,
                _release_leases=lease_record.release,
            )
            capability = self._verifier_peer._consume_request_and_issue_completion_v1(
                request, verified
            )
            lease_record = None
            return capability
        except Exception as error:
            if lease_record is not None:
                try:
                    lease_record.release()
                except Exception:
                    pass
            if isinstance(error, ValueError) and str(error) == _UNAVAILABLE:
                raise
            raise _unavailable() from error

    def _read_exact_owner_record(
        self, facts: protocol._RegisteredAssetReplayFactsV1
    ) -> _OwnerRegistryRecordV1:
        self._registry_reader.validate()
        owner_root = self._owner._root
        path = owner_root / "registry" / _REGISTRY_FILENAME
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(
                f"{path.resolve(strict=True).as_uri()}?mode=ro",
                uri=True,
                timeout=0.0,
                isolation_level=None,
            )
            connection.execute("PRAGMA query_only = ON")
            connection.execute("BEGIN")
            rows = connection.execute(
                "SELECT asset_id, attempt_id, provider_reference, media_type, digest, storage_name "
                "FROM asset_registry WHERE asset_id = ?",
                (facts.asset_id,),
            ).fetchall()
            if len(rows) != 1:
                raise _unavailable()
            row = rows[0]
            if len(row) != 6 or not all(type(value) is str for value in row):
                raise _unavailable()
            record = _OwnerRegistryRecordV1(*row)
            if (
                record.asset_id != facts.asset_id
                or record.attempt_id != facts.attempt_id
                or record.provider_reference != facts.provider_reference
                or record.media_type != facts.media_type
                or record.digest != facts.sha256
                or not owner_module._is_storage_name(record.storage_name)
            ):
                raise _unavailable()
            return record
        except (OSError, sqlite3.Error, TypeError, ValueError) as error:
            if isinstance(error, ValueError) and str(error) == _UNAVAILABLE:
                raise
            raise _unavailable() from error
        finally:
            if connection is not None:
                connection.close()


def _validate_request_facts(facts: protocol._RegisteredAssetReplayFactsV1) -> None:
    if (
        type(facts) is not protocol._RegisteredAssetReplayFactsV1
        or facts.phase != "ASSET_REGISTERED"
        or facts.media_type != _MEDIA_TYPE
        or not 1 <= facts.expected_byte_length <= _MAX_PNG_BYTES
        or facts.sequence < 0
        or not all(
            _is_sha256(value)
            for value in (
                facts.binding_digest,
                facts.canonical_result_identity,
                facts.asset_registration_digest,
                facts.sha256,
                facts.last_event_digest,
            )
        )
        or not all(
            _is_logical_reference(value)
            for value in (
                facts.delivery_identity,
                facts.attempt_id,
                facts.provider_reference,
                facts.logical_output_id,
                facts.asset_id,
                facts.provenance_assurance,
            )
        )
    ):
        raise _unavailable()


def _asset_registration_digest(record: _OwnerRegistryRecordV1) -> str:
    """Return the exact frozen R03 canonical asset-registration digest."""

    projection = {
        "asset_id": record.asset_id,
        "asset_sha256": record.digest,
        "attempt_id": record.attempt_id,
        "media_type": record.media_type,
        "provider_reference": record.provider_reference,
        "schema": "manga_director.real_asset_registration",
        "version": 1,
    }
    encoded = json.dumps(projection, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _derive_final_asset_path(owner: LocalDurableAssetOwner, storage_name: str) -> Path:
    assets_directory = owner._assets_directory
    if not isinstance(assets_directory, Path) or not owner_module._is_storage_name(storage_name):
        raise _unavailable()
    path = assets_directory / storage_name
    try:
        owner_module._assert_private_path(path, assets_directory)
    except (OSError, ValueError) as error:
        raise _unavailable() from error
    return path


def _open_root_lease(owner: LocalDurableAssetOwner) -> _RootLeaseV1:
    if os.name != "nt":
        raise _unavailable()
    assets_directory = owner._assets_directory
    captured = owner._assets_root_identity
    if (
        not isinstance(assets_directory, Path)
        or type(captured) is not owner_module._OwnerRootIdentity
        or owner_module._is_link_or_reparse_point(assets_directory)
    ):
        raise _unavailable()
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    handle = _open_handle(
        kernel32,
        assets_directory,
        _FILE_SHARE_READ | _FILE_SHARE_WRITE,
        _FILE_FLAG_BACKUP_SEMANTICS | _FILE_FLAG_OPEN_REPARSE_POINT,
    )
    try:
        identity = owner_module._windows_handle_identity(kernel32, handle)
        if (
            not identity.attributes & owner_module._FILE_ATTRIBUTE_DIRECTORY
            or identity.attributes & owner_module._FILE_ATTRIBUTE_REPARSE_POINT
            or identity.volume_serial == 0
            or identity.file_index == 0
            or not owner_module._windows_paths_equal(identity.final_path, captured.final_path)
            or identity.volume_serial != captured.volume_serial
            or identity.file_index != captured.file_index
        ):
            raise _unavailable()
        return _RootLeaseV1(kernel32, handle, identity)
    except Exception:
        kernel32.CloseHandle(ctypes.c_void_p(handle))
        raise


def _open_final_file_lease(
    path: Path,
    root_lease: _RootLeaseV1,
    owner: LocalDurableAssetOwner,
) -> _FinalFileLeaseV1:
    if os.name != "nt" or owner_module._is_link_or_reparse_point(path):
        raise _unavailable()
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    handle = _open_handle(
        kernel32,
        path,
        _FILE_SHARE_READ,
        _FILE_ATTRIBUTE_NORMAL | _FILE_FLAG_OPEN_REPARSE_POINT,
    )
    try:
        import msvcrt

        descriptor = msvcrt.open_osfhandle(int(handle), os.O_RDONLY)
        stream = os.fdopen(descriptor, "rb", closefd=True)
    except Exception as error:
        kernel32.CloseHandle(ctypes.c_void_p(handle))
        raise _unavailable() from error
    try:
        identity = owner_module._windows_handle_identity(kernel32, handle)
        captured = owner._assets_root_identity
        if (
            type(captured) is not owner_module._OwnerRootIdentity
            or identity.attributes
            & (owner_module._FILE_ATTRIBUTE_DIRECTORY | owner_module._FILE_ATTRIBUTE_REPARSE_POINT)
            or identity.volume_serial == 0
            or identity.file_index == 0
            or not 1 <= identity.size <= _MAX_PNG_BYTES
            or not owner_module._windows_paths_equal(identity.final_path, path.resolve(strict=True))
            or not _is_strict_descendant(identity.final_path, root_lease.identity.final_path)
            or not owner_module._windows_paths_equal(root_lease.identity.final_path, captured.final_path)
            or root_lease.identity.volume_serial != captured.volume_serial
            or root_lease.identity.file_index != captured.file_index
        ):
            raise _unavailable()
        return _FinalFileLeaseV1(stream, identity)
    except Exception:
        stream.close()
        raise


def _open_handle(kernel32: Any, path: Path, share_mode: int, flags: int) -> int:
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
    handle = create_file(str(path), _GENERIC_READ, share_mode, None, _OPEN_EXISTING, flags, None)
    invalid = ctypes.c_void_p(-1).value
    if not handle or handle == invalid:
        raise _unavailable()
    return int(handle)


def _is_strict_descendant(path: Path, root: Path) -> bool:
    try:
        return path.resolve(strict=False).relative_to(root.resolve(strict=False)) != Path(".")
    except (OSError, ValueError):
        return False


def _root_identity_tuple(identity: owner_module._OpenedAssetIdentity) -> tuple[str, int, int]:
    return (str(identity.final_path), identity.volume_serial, identity.file_index)


def _file_identity_tuple(identity: owner_module._OpenedAssetIdentity) -> tuple[str, int, int, int]:
    return (str(identity.final_path), identity.volume_serial, identity.file_index, identity.size)


def _is_sha256(value: object) -> bool:
    return type(value) is str and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _is_logical_reference(value: object) -> bool:
    if type(value) is not str or not value or value != value.strip():
        return False
    lowered = value.lower()
    return not (
        any(char.isspace() or ord(char) < 32 for char in value)
        or "/" in value
        or "\\" in value
        or ".." in value
        or lowered.startswith("file:")
        or "://" in value
        or (len(value) > 1 and value[0].isalpha() and value[1] == ":")
    )
