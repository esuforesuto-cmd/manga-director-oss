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
from typing import Any, BinaryIO, Literal, Protocol

from manga_director.production.next_generation_asset_registration import (
    AssetRegistrationRuntimeResult,
)
from manga_director.production.next_generation_generation_evidence import (
    EvidenceValueDTO,
    GenerationOutputEvidenceDTO,
)

_MAX_REGISTERED_BYTES = 25 * 1024 * 1024
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_MEDIA_TYPE = "image/png"
_SCHEMA_VERSION = 1
_REGISTRY_FILENAME = "asset-owner.sqlite3"
_SQLITE_HEADER = b"SQLite format 3\x00"
_SQLITE_ROLLBACK_JOURNAL_VERSIONS = b"\x01\x01"
_REGISTRY_DDL = (
    "CREATE TABLE asset_registry ("
    "asset_id TEXT PRIMARY KEY, "
    "attempt_id TEXT NOT NULL UNIQUE, "
    "provider_reference TEXT NOT NULL, "
    "media_type TEXT NOT NULL, "
    "digest TEXT NOT NULL, "
    "storage_name TEXT NOT NULL UNIQUE"
    ")"
)
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


@dataclass(frozen=True, slots=True)
class DurableAssetInventoryObservation:
    outcome: Literal["found", "missing", "corrupt", "ambiguous"]
    attempt_ids: tuple[str, ...] = ()
    bindings: tuple[DurableAssetBindingObservation, ...] = field(
        default=(), repr=False
    )


@dataclass(frozen=True, slots=True)
class DurableAssetBindingObservation:
    attempt_id: str
    provider_reference: str
    output_asset_id: str
    media_type: str
    content_sha256: str


@dataclass(frozen=True, slots=True)
class DurableAssetOutputObservation:
    """Verified read-only facts for one exact registered output."""

    outcome: Literal["found", "missing", "corrupt", "ambiguous"]
    content_sha256: str | None = None
    media_type: str | None = None


@dataclass(frozen=True, slots=True)
class DurableAssetPresenceObservation:
    """Owner-local integrity result that never exposes registry identities."""

    outcome: Literal["empty", "found", "orphaned", "corrupt"]


class ProviderNeutralAssetOwner(Protocol):
    """Internal provider-neutral durable registration capability."""

    def register(self, material: OwnerRegistrationMaterial) -> AssetRegistrationRuntimeResult: ...


@dataclass(frozen=True, slots=True)
class _OpenedAssetIdentity:
    """Stable metadata derived from the one leased asset descriptor."""

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


@dataclass(slots=True)
class _AssetPresentationBytesLease:
    """Validated bytes retaining the exact-file lease until delivery completes."""

    image_bytes: bytes = field(repr=False)
    _lease: _AssetVerificationLease

    def release(self) -> None:
        self._lease.release()


class LocalDurableAssetOwner(ProviderNeutralAssetOwner):
    """Own private local byte persistence and logical asset registration."""

    def __init__(self, owner_root: Path, *, _issue_i02_commitment: bool = True) -> None:
        if not isinstance(_issue_i02_commitment, bool):
            raise ValueError("asset owner commitment mode is unavailable")
        self._root = _prepare_owner_root(owner_root)
        self._registry_directory = _prepare_child_directory(self._root, "registry")
        self._staging_directory = _prepare_child_directory(self._root, "staging")
        self._assets_directory = _prepare_child_directory(self._root, "assets")
        self._assets_root_identity = _capture_owner_root_identity(
            self._assets_directory
        )
        self._registry_path = _prepare_registry_path(self._registry_directory)
        self._initialize_registry()
        self._real_delivery_lock = threading.RLock()
        self._real_delivery_owner_instance_nonce = secrets.token_bytes(32)
        self._live_registration_commitments_by_result_id: dict[int, _OwnerRegistrationCommitmentRecordV1] = {}
        self._issued_registration_identities: set[tuple[object, ...]] = set()
        self._consumed_registration_identities: set[tuple[object, ...]] = set()
        self._unissuable_registration_identities: set[tuple[object, ...]] = set()
        self._issue_i02_commitment = _issue_i02_commitment

    @classmethod
    def _open_existing_for_presentation(cls, owner_root: Path) -> LocalDurableAssetOwner:
        """Open only an existing owner layout without creating or repairing it."""

        root = _existing_owner_root(owner_root)
        registry_directory = _existing_child_directory(root, "registry")
        assets_directory = _existing_child_directory(root, "assets")
        registry_path = _existing_regular_file(
            registry_directory / _REGISTRY_FILENAME, registry_directory
        )
        owner = object.__new__(cls)
        owner._root = root
        owner._registry_directory = registry_directory
        owner._assets_directory = assets_directory
        owner._registry_path = registry_path
        owner._assets_root_identity = _capture_owner_root_identity(assets_directory)
        return owner

    @classmethod
    def observe_attempts(  # noqa: C901 - one closed integrity inventory.
        cls, owner_root: Path, attempt_ids: tuple[str, ...]
    ) -> DurableAssetInventoryObservation:
        """Verify exact existing registrations without creating owner state."""

        if len(attempt_ids) != len(set(attempt_ids)):
            return DurableAssetInventoryObservation("ambiguous")
        missing = _owner_observation_missing(owner_root)
        if missing is True:
            return DurableAssetInventoryObservation("missing")
        if missing is None:
            return DurableAssetInventoryObservation("corrupt")
        try:
            owner = cls._open_existing_for_presentation(owner_root)
        except (OSError, ValueError):
            return DurableAssetInventoryObservation("corrupt")
        connection: sqlite3.Connection | None = None
        leases: list[_AssetPresentationBytesLease] = []
        try:
            connection = _open_readonly_registry(owner._registry_path)
            if not _registry_schema_is_valid(connection):
                return DurableAssetInventoryObservation("corrupt")
            found: list[str] = []
            bindings: list[DurableAssetBindingObservation] = []
            for attempt_id in attempt_ids:
                rows = connection.execute(
                    "SELECT asset_id, provider_reference, media_type, digest, storage_name "
                    "FROM asset_registry WHERE attempt_id = ?",
                    (attempt_id,),
                ).fetchall()
                if not rows:
                    continue
                if len(rows) != 1:
                    return DurableAssetInventoryObservation("ambiguous")
                asset_id, provider, media_type, digest, storage_name = rows[0]
                if not _is_storage_name(storage_name):
                    return DurableAssetInventoryObservation("corrupt")
                lease = owner._read_verified_presentation_bytes(
                    attempt_id=attempt_id,
                    provider_reference=provider,
                    output_asset_id=asset_id,
                    expected_sha256=digest,
                    expected_media_type=media_type,
                )
                leases.append(lease)
                found.append(attempt_id)
                bindings.append(
                    DurableAssetBindingObservation(
                        attempt_id, provider, asset_id, media_type, digest
                    )
                )
        except Exception:
            return DurableAssetInventoryObservation("corrupt")
        finally:
            for lease in leases:
                lease.release()
            if connection is not None:
                connection.close()
        if not found:
            return DurableAssetInventoryObservation("missing")
        if len(found) != len(attempt_ids):
            ordered = tuple(sorted(bindings, key=lambda item: item.attempt_id))
            return DurableAssetInventoryObservation(
                "ambiguous", tuple(item.attempt_id for item in ordered), ordered
            )
        ordered = tuple(sorted(bindings, key=lambda item: item.attempt_id))
        return DurableAssetInventoryObservation(
            "found", tuple(item.attempt_id for item in ordered), ordered
        )

    @classmethod
    def observe_output(
        cls,
        owner_root: Path,
        *,
        attempt_id: str,
        provider_reference: str,
        output_asset_id: str,
    ) -> DurableAssetOutputObservation:
        """Verify one exact output binding without exposing registry rows or paths."""

        missing = _owner_observation_missing(owner_root)
        if missing is True:
            return DurableAssetOutputObservation("missing")
        if missing is None:
            return DurableAssetOutputObservation("corrupt")
        try:
            owner = cls._open_existing_for_presentation(owner_root)
        except (OSError, ValueError):
            return DurableAssetOutputObservation("corrupt")
        connection: sqlite3.Connection | None = None
        lease: _AssetPresentationBytesLease | None = None
        try:
            connection = _open_readonly_registry(owner._registry_path)
            if not _registry_schema_is_valid(connection):
                return DurableAssetOutputObservation("corrupt")
            rows = connection.execute(
                "SELECT asset_id, provider_reference, media_type, digest "
                "FROM asset_registry WHERE attempt_id = ?",
                (attempt_id,),
            ).fetchall()
            if not rows:
                return DurableAssetOutputObservation("missing")
            if len(rows) != 1:
                return DurableAssetOutputObservation("ambiguous")
            asset_id, provider, media_type, digest = rows[0]
            if asset_id != output_asset_id or provider != provider_reference:
                return DurableAssetOutputObservation("corrupt")
            lease = owner._read_verified_presentation_bytes(
                attempt_id=attempt_id,
                provider_reference=provider_reference,
                output_asset_id=output_asset_id,
                expected_sha256=digest,
                expected_media_type=media_type,
            )
            return DurableAssetOutputObservation("found", digest, media_type)
        except Exception:
            return DurableAssetOutputObservation("corrupt")
        finally:
            if lease is not None:
                lease.release()
            if connection is not None:
                connection.close()

    @classmethod
    def observe_presence(
        cls, owner_root: Path, authority_attempt_ids: tuple[str, ...]
    ) -> DurableAssetPresenceObservation:
        """Verify every registry row and byte lease against attempt authority."""

        if len(authority_attempt_ids) != len(set(authority_attempt_ids)):
            return DurableAssetPresenceObservation("corrupt")
        missing = _owner_observation_missing(owner_root)
        if missing is True:
            return DurableAssetPresenceObservation("empty")
        if missing is None:
            return DurableAssetPresenceObservation("corrupt")
        try:
            owner = cls._open_existing_for_presentation(owner_root)
        except (OSError, ValueError):
            return DurableAssetPresenceObservation("corrupt")
        connection: sqlite3.Connection | None = None
        leases: list[_AssetPresentationBytesLease] = []
        try:
            connection = _open_readonly_registry(owner._registry_path)
            if not _registry_schema_is_valid(connection):
                return DurableAssetPresenceObservation("corrupt")
            rows = connection.execute(
                "SELECT attempt_id, asset_id, provider_reference, media_type, digest, "
                "storage_name FROM asset_registry"
            ).fetchall()
            observed_ids = _observe_registry_attempt_ids(owner, rows, leases)
            if observed_ids is None:
                return DurableAssetPresenceObservation("corrupt")
        except Exception:
            return DurableAssetPresenceObservation("corrupt")
        finally:
            for lease in leases:
                lease.release()
            if connection is not None:
                connection.close()
        if not observed_ids:
            return DurableAssetPresenceObservation("empty")
        if not observed_ids.issubset(set(authority_attempt_ids)):
            return DurableAssetPresenceObservation("orphaned")
        return DurableAssetPresenceObservation("found")

    def _read_verified_presentation_bytes(
        self,
        *,
        attempt_id: str,
        provider_reference: str,
        output_asset_id: str,
        expected_sha256: str,
        expected_media_type: str,
    ) -> _AssetPresentationBytesLease:
        """Return bytes from the exact read-only registry-selected asset lease."""

        if (
            not _is_logical_reference(attempt_id)
            or not _is_logical_reference(provider_reference)
            or not _is_logical_reference(output_asset_id)
            or not _is_sha256(expected_sha256)
            or expected_media_type != _MEDIA_TYPE
        ):
            raise ValueError("asset presentation input is unavailable")
        connection: sqlite3.Connection | None = None
        lease: _AssetVerificationLease | None = None
        try:
            connection = _open_readonly_registry(self._registry_path)
            rows = connection.execute(
                "SELECT attempt_id, provider_reference, media_type, digest, storage_name "
                "FROM asset_registry WHERE asset_id = ?",
                (output_asset_id,),
            ).fetchall()
            if len(rows) != 1:
                raise ValueError("asset presentation record is unavailable")
            row = rows[0]
            if (
                not isinstance(row, tuple)
                or len(row) != 5
                or row[0] != attempt_id
                or row[1] != provider_reference
                or row[2] != expected_media_type
                or row[3] != expected_sha256
                or not _is_storage_name(row[4])
            ):
                raise _AssetVerificationIntegrityFailure(
                    "asset presentation binding is invalid"
                )
            lease = _open_verified_asset_lease(
                self._final_path(row[4]),
                self._assets_directory,
                self._assets_root_identity,
                expected_sha256,
            )
            image_bytes = lease._stream.read(_MAX_REGISTERED_BYTES + 1)
            if (
                type(image_bytes) is not bytes
                or len(image_bytes) != lease._identity.size
                or not 1 <= len(image_bytes) <= _MAX_REGISTERED_BYTES
                or hashlib.sha256(image_bytes).hexdigest() != expected_sha256
            ):
                raise _AssetVerificationIntegrityFailure("asset presentation read is invalid")
            presentation = _AssetPresentationBytesLease(image_bytes, lease)
            lease = None
            return presentation
        except (OSError, sqlite3.Error, TypeError) as error:
            raise ValueError("asset presentation is unavailable") from error
        finally:
            if lease is not None:
                lease.release()
            if connection is not None:
                connection.close()

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
            asset_id = f"asset-generated-{asset_uuid}"
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
            result = _registered_result(material, asset_id, digest)
            if self._issue_i02_commitment:
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
            return _open_verified_asset_lease(
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
                connection.execute(_REGISTRY_DDL)
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
        return _registered_result(material, asset_id, digest)

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


def _owner_observation_missing(owner_root: Path) -> bool | None:
    """Return True only for an absent authority, None for unsafe existing paths."""

    try:
        root_kind = _readonly_path_kind(owner_root)
        if root_kind == "missing":
            return True
        parent = owner_root.parent
        if (
            not owner_root.is_absolute()
            or root_kind != "directory"
            or _readonly_path_kind(parent) != "directory"
        ):
            return None
        registry = owner_root / "registry"
        database = registry / _REGISTRY_FILENAME
        if (
            _readonly_path_kind(registry) != "directory"
            or registry.resolve(strict=True).parent != owner_root.resolve(strict=True)
            or _readonly_path_kind(database) != "file"
            or database.resolve(strict=True).parent != registry.resolve(strict=True)
        ):
            return None
        return False
    except OSError:
        return None


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
    reparse_point = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    if stat.S_ISLNK(status.st_mode) or bool(
        reparse_point and attributes & reparse_point
    ):
        return "unsafe"
    if stat.S_ISREG(status.st_mode):
        return "file"
    if stat.S_ISDIR(status.st_mode):
        return "directory"
    return "unsafe"


def _existing_owner_root(owner_root: Path) -> Path:
    if not isinstance(owner_root, Path) or not owner_root.is_absolute() or ".." in owner_root.parts:
        raise ValueError("asset presentation owner is unavailable")
    try:
        if _is_link_or_reparse_point(owner_root) or not owner_root.is_dir():
            raise ValueError("asset presentation owner is unavailable")
        root = owner_root.resolve(strict=True)
    except OSError as error:
        raise ValueError("asset presentation owner is unavailable") from error
    if _is_link_or_reparse_point(root) or not root.is_dir():
        raise ValueError("asset presentation owner is unavailable")
    return root


def _existing_child_directory(root: Path, name: str) -> Path:
    path = _private_child(root, name)
    if _is_link_or_reparse_point(path) or not path.is_dir():
        raise ValueError("asset presentation owner is unavailable")
    return path


def _existing_regular_file(path: Path, parent: Path) -> Path:
    _assert_private_path(path, parent)
    if _is_link_or_reparse_point(path) or not path.is_file():
        raise ValueError("asset presentation registry is unavailable")
    return path


def _open_readonly_registry(registry_path: Path) -> sqlite3.Connection:
    _existing_regular_file(registry_path, registry_path.parent)
    _require_rollback_journal_database(registry_path)
    connection = sqlite3.connect(
        f"{registry_path.resolve(strict=True).as_uri()}?mode=ro",
        uri=True,
        timeout=0.0,
        isolation_level=None,
    )
    try:
        connection.execute("PRAGMA query_only = ON")
        if connection.execute("PRAGMA query_only").fetchall() != [(1,)]:
            raise ValueError("asset presentation registry is unavailable")
        connection.execute("BEGIN")
        version = connection.execute("PRAGMA user_version").fetchall()
        journal_mode = connection.execute("PRAGMA journal_mode").fetchall()
        objects = connection.execute(
            "SELECT type, name FROM sqlite_master "
            "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
        ).fetchall()
        ddl = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'asset_registry'"
        ).fetchall()
        if (
            version != [(_SCHEMA_VERSION,)]
            or journal_mode != [("delete",)]
            or objects != [("table", "asset_registry")]
            or len(ddl) != 1
            or not isinstance(ddl[0][0], str)
            or _without_ascii_whitespace(ddl[0][0])
            != _without_ascii_whitespace(_REGISTRY_DDL)
            or not _registry_schema_is_valid(connection)
        ):
            raise ValueError("asset presentation registry is unavailable")
        return connection
    except Exception:
        connection.close()
        raise


def _require_rollback_journal_database(path: Path) -> None:
    """Reject WAL before sqlite3 can create read-side WAL support files."""

    try:
        with path.open("rb") as stream:
            header = stream.read(20)
    except OSError as error:
        raise ValueError("asset presentation database is unavailable") from error
    if (
        header[: len(_SQLITE_HEADER)] != _SQLITE_HEADER
        or header[18:20] != _SQLITE_ROLLBACK_JOURNAL_VERSIONS
    ):
        raise ValueError("asset presentation database is unavailable")


def _prepare_child_directory(root: Path, name: str) -> Path:
    try:
        path = _private_child(root, name)
        path.mkdir(exist_ok=True)
    except (OSError, ValueError) as error:
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
    expected_columns = (
        ("asset_id", "TEXT", 0, None, 1),
        ("attempt_id", "TEXT", 1, None, 0),
        ("provider_reference", "TEXT", 1, None, 0),
        ("media_type", "TEXT", 1, None, 0),
        ("digest", "TEXT", 1, None, 0),
        ("storage_name", "TEXT", 1, None, 0),
    )
    rows = connection.execute("PRAGMA table_info(asset_registry)").fetchall()
    columns = tuple((row[1], row[2], row[3], row[4], row[5]) for row in rows)
    if columns != expected_columns:
        return False
    objects = connection.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_master "
        "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
    ).fetchall()
    if (
        len(objects) != 1
        or objects[0][:3] != ("table", "asset_registry", "asset_registry")
        or not isinstance(objects[0][3], str)
        or _without_ascii_whitespace(objects[0][3])
        != _without_ascii_whitespace(_REGISTRY_DDL)
    ):
        return False
    indexes = connection.execute("PRAGMA index_list(asset_registry)").fetchall()
    unique_columns: set[tuple[str, str]] = set()
    for index in indexes:
        if len(index) != 5 or index[2] != 1 or not isinstance(index[1], str):
            return False
        index_columns = connection.execute(f"PRAGMA index_info({index[1]})").fetchall()
        if len(index_columns) != 1 or index_columns[0][0] != 0:
            return False
        unique_columns.add((str(index_columns[0][2]), str(index[3])))
    return unique_columns == {
        ("asset_id", "pk"),
        ("attempt_id", "u"),
        ("storage_name", "u"),
    }


def _without_ascii_whitespace(value: str) -> str:
    return "".join(character for character in value if character not in " \t\r\n\f\v")


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


def _observe_registry_attempt_ids(
    owner: LocalDurableAssetOwner,
    rows: list[tuple[Any, ...]],
    leases: list[_AssetPresentationBytesLease],
) -> set[str] | None:
    observed_ids: set[str] = set()
    for row in rows:
        if len(row) != 6 or not all(isinstance(value, str) for value in row):
            return None
        attempt_id, asset_id, provider, media_type, digest, storage_name = row
        if attempt_id in observed_ids or not _is_storage_name(storage_name):
            return None
        lease = owner._read_verified_presentation_bytes(
            attempt_id=attempt_id,
            provider_reference=provider,
            output_asset_id=asset_id,
            expected_sha256=digest,
            expected_media_type=media_type,
        )
        leases.append(lease)
        observed_ids.add(attempt_id)
    return observed_ids


def _private_file_matches(path: Path, expected_digest: str) -> bool:
    _assert_private_path(path, path.parent)
    if _is_link_or_reparse_point(path) or not path.is_file() or path.stat().st_size > _MAX_REGISTERED_BYTES:
        return False
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(64 * 1024):
            digest.update(chunk)
    return digest.hexdigest() == expected_digest


def _open_verified_asset_lease(
    path: Path,
    owner_root: Path,
    expected_owner_root: _OwnerRootIdentity | None,
    expected_digest: str,
) -> _AssetVerificationLease:
    if os.name == "nt":
        return _open_verified_windows_lease(
            path, owner_root, expected_owner_root, expected_digest
        )
    return _open_verified_posix_lease(
        path, owner_root, expected_owner_root, expected_digest
    )


def _open_verified_posix_lease(
    path: Path,
    owner_root: Path,
    expected_owner_root: _OwnerRootIdentity | None,
    expected_digest: str,
) -> _AssetVerificationLease:
    """Lease and hash one ordinary file relative to its pinned POSIX owner root."""

    _assert_private_path(path, owner_root)
    no_follow = getattr(os, "O_NOFOLLOW", None)
    directory = getattr(os, "O_DIRECTORY", None)
    if (
        os.name == "nt"
        or expected_owner_root is None
        or not isinstance(no_follow, int)
        or not isinstance(directory, int)
    ):
        raise ValueError("asset verification lease is unavailable")
    root_descriptor = os.open(
        owner_root,
        os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | no_follow | directory,
    )
    asset_descriptor: int | None = None
    stream: BinaryIO | None = None
    try:
        if not _posix_owner_root_descriptor_matches(
            root_descriptor, owner_root, expected_owner_root
        ):
            raise _AssetVerificationIntegrityFailure(
                "asset verification owner identity is invalid"
            )
        asset_descriptor = os.open(
            path.name,
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NONBLOCK", 0)
            | no_follow,
            dir_fd=root_descriptor,
        )
        descriptor_status = os.fstat(asset_descriptor)
        path_status = os.stat(
            path.name, dir_fd=root_descriptor, follow_symlinks=False
        )
        if not _posix_asset_identity_matches(descriptor_status, path_status):
            raise _AssetVerificationIntegrityFailure(
                "asset verification identity is invalid"
            )
        identity = _OpenedAssetIdentity(
            final_path=path,
            volume_serial=descriptor_status.st_dev,
            file_index=descriptor_status.st_ino,
            size=descriptor_status.st_size,
            attributes=descriptor_status.st_mode,
        )
        stream = os.fdopen(asset_descriptor, "rb", closefd=True)
        asset_descriptor = None
        digest = hashlib.sha256()
        while chunk := stream.read(64 * 1024):
            digest.update(chunk)
        final_status = os.fstat(stream.fileno())
        final_path_status = os.stat(
            path.name, dir_fd=root_descriptor, follow_symlinks=False
        )
        if (
            not _posix_asset_identity_matches(final_status, final_path_status)
            or not _same_posix_file_identity(descriptor_status, final_status)
            or digest.hexdigest() != expected_digest
            or not _posix_owner_root_descriptor_matches(
                root_descriptor, owner_root, expected_owner_root
            )
        ):
            raise _AssetVerificationIntegrityFailure(
                "asset verification digest or binding is invalid"
            )
        stream.seek(0)
        lease = _AssetVerificationLease(stream, identity)
        stream = None
        return lease
    finally:
        if stream is not None:
            stream.close()
        if asset_descriptor is not None:
            os.close(asset_descriptor)
        os.close(root_descriptor)


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


def _capture_owner_root_identity(owner_root: Path) -> _OwnerRootIdentity:
    if os.name == "nt":
        return _capture_windows_owner_root_identity(owner_root)
    return _capture_posix_owner_root_identity(owner_root)


def _capture_posix_owner_root_identity(owner_root: Path) -> _OwnerRootIdentity:
    """Pin one ordinary POSIX assets directory without following a final link."""

    no_follow = getattr(os, "O_NOFOLLOW", None)
    directory = getattr(os, "O_DIRECTORY", None)
    if (
        os.name == "nt"
        or not isinstance(no_follow, int)
        or not isinstance(directory, int)
    ):
        raise ValueError("asset owner root is unavailable")
    descriptor = os.open(
        owner_root,
        os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | no_follow | directory,
    )
    try:
        descriptor_status = os.fstat(descriptor)
        path_status = owner_root.lstat()
        if (
            not stat.S_ISDIR(descriptor_status.st_mode)
            or stat.S_ISLNK(path_status.st_mode)
            or not stat.S_ISDIR(path_status.st_mode)
            or not _same_posix_file_identity(descriptor_status, path_status)
        ):
            raise ValueError("asset owner root is unavailable")
        return _OwnerRootIdentity(
            final_path=owner_root.resolve(strict=True),
            volume_serial=descriptor_status.st_dev,
            file_index=descriptor_status.st_ino,
        )
    finally:
        os.close(descriptor)


def _posix_owner_root_descriptor_matches(
    descriptor: int,
    owner_root: Path,
    expected: _OwnerRootIdentity,
) -> bool:
    try:
        descriptor_status = os.fstat(descriptor)
        path_status = owner_root.lstat()
        resolved = owner_root.resolve(strict=True)
    except OSError:
        return False
    return bool(
        stat.S_ISDIR(descriptor_status.st_mode)
        and not stat.S_ISLNK(path_status.st_mode)
        and stat.S_ISDIR(path_status.st_mode)
        and _same_posix_file_identity(descriptor_status, path_status)
        and descriptor_status.st_dev == expected.volume_serial
        and descriptor_status.st_ino == expected.file_index
        and resolved == expected.final_path
    )


def _posix_asset_identity_matches(
    descriptor_status: os.stat_result, path_status: os.stat_result
) -> bool:
    return bool(
        stat.S_ISREG(descriptor_status.st_mode)
        and not stat.S_ISLNK(path_status.st_mode)
        and stat.S_ISREG(path_status.st_mode)
        and _same_posix_file_identity(descriptor_status, path_status)
        and 0 < descriptor_status.st_size <= _MAX_REGISTERED_BYTES
    )


def _same_posix_file_identity(
    left: os.stat_result, right: os.stat_result
) -> bool:
    return bool(
        left.st_dev == right.st_dev
        and left.st_ino == right.st_ino
        and left.st_mode == right.st_mode
        and left.st_size == right.st_size
        and left.st_mtime_ns == right.st_mtime_ns
        and left.st_ctime_ns == right.st_ctime_ns
    )


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
    material: OwnerRegistrationMaterial, asset_id: str, digest: str
) -> AssetRegistrationRuntimeResult:
    return AssetRegistrationRuntimeResult(
        attempt_id=material.attempt_id,
        provider_reference=material.provider_reference,
        outcome="registered",
        output=GenerationOutputEvidenceDTO(
            output_asset_id=asset_id,
            output_content_hash=EvidenceValueDTO(availability="known", value=digest),
            media_type=material.media_type,
        ),
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
