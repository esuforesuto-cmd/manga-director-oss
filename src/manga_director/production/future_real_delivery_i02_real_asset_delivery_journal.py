"""Private RFC-01 I02 real-asset delivery persistence and replay.

The journal is deliberately not a provider, asset-owner, filesystem, workflow,
or Generated-application authority.  It owns only its exact LocalFile SQLite
store, deterministic event replay, and the paired I02a completion callback.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import stat
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Final, cast

from manga_director.production import future_real_delivery_i02a_protocol as protocol
from manga_director.production.next_generation_local_durable_asset_owner import (
    LocalDurableAssetOwner,
    _OwnerRegistrationFactsV1,
    _OwnerRegistryCorruptV1,
)

_SCHEMA_ID: Final = "manga_director.real_asset_delivery_journal"
_SCHEMA_VERSION: Final = 1
_CANONICAL_RESULT_SCHEMA_ID: Final = "manga_director.real_provider_canonical_result"
_CANONICAL_RESULT_SCHEMA_VERSION: Final = 1
_ASSET_REGISTRATION_SCHEMA: Final = "manga_director.real_asset_registration"
_GENESIS_DIGEST: Final = "0" * 64
_MAX_EVENT_BYTES: Final = 8 * 1024
_MAX_EVENTS: Final = 16
_MEDIA_TYPE: Final = "image/png"
_PROVENANCE: Final = "UNVERIFIED"
_UNAVAILABLE: Final = "RFC-01 I02 real asset delivery journal is unavailable"

_TABLES: Final = (
    "real_asset_delivery_bindings",
    "real_asset_delivery_events",
    "real_asset_delivery_schema_meta",
)
_EXPECTED_COLUMNS: Final = {
    "real_asset_delivery_schema_meta": (
        (0, "schema_id", "TEXT", 0, None, 1),
        (1, "schema_version", "INTEGER", 1, None, 0),
    ),
    "real_asset_delivery_bindings": (
        (0, "delivery_identity", "TEXT", 0, None, 1),
        (1, "attempt_id", "TEXT", 1, None, 0),
        (2, "canonical_result_identity", "TEXT", 1, None, 0),
        (3, "logical_output_id", "TEXT", 1, None, 0),
        (4, "asset_sha256", "TEXT", 1, None, 0),
        (5, "binding_json", "TEXT", 1, None, 0),
        (6, "binding_digest", "TEXT", 1, None, 0),
        (7, "phase", "TEXT", 1, None, 0),
        (8, "sequence", "INTEGER", 1, None, 0),
        (9, "terminal_code", "TEXT", 0, None, 0),
        (10, "last_event_digest", "TEXT", 1, None, 0),
    ),
    "real_asset_delivery_events": (
        (0, "delivery_identity", "TEXT", 1, None, 1),
        (1, "sequence", "INTEGER", 1, None, 2),
        (2, "event_type", "TEXT", 1, None, 0),
        (3, "payload_json", "TEXT", 1, None, 0),
        (4, "payload_digest", "TEXT", 1, None, 0),
        (5, "previous_event_digest", "TEXT", 1, None, 0),
        (6, "event_digest", "TEXT", 1, None, 0),
    ),
}
_EXPECTED_INDEXES: Final = {
    "real_asset_delivery_schema_meta": {
        "sqlite_autoindex_real_asset_delivery_schema_meta_1": (1, "pk", 0, ("schema_id",)),
    },
    "real_asset_delivery_bindings": {
        "sqlite_autoindex_real_asset_delivery_bindings_1": (1, "pk", 0, ("delivery_identity",)),
        "sqlite_autoindex_real_asset_delivery_bindings_2": (1, "u", 0, ("attempt_id",)),
        "sqlite_autoindex_real_asset_delivery_bindings_3": (
            1,
            "u",
            0,
            ("canonical_result_identity", "logical_output_id", "asset_sha256"),
        ),
    },
    "real_asset_delivery_events": {
        "sqlite_autoindex_real_asset_delivery_events_1": (
            1,
            "pk",
            0,
            ("delivery_identity", "sequence"),
        ),
    },
}


def _unavailable() -> ValueError:
    return ValueError(_UNAVAILABLE)


class _DurableJournalCorruptV1(ValueError):
    """Private replay-integrity classification; never a repair capability."""


class _UnknownDeliveryIdentityV1(ValueError):
    """Private caller-target rejection; it is not durable corruption."""


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True, allow_nan=False)


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _canonical_result_identity_v1(
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
    asset_sha256: str,
    expected_byte_length: int,
) -> str:
    """Derive the frozen canonical result identity from authoritative facts."""

    return _digest(
        {
            "asset_sha256": asset_sha256,
            "attempt_id": attempt_id,
            "dispatch_identity": dispatch_identity,
            "expected_byte_length": expected_byte_length,
            "idempotency_identity": idempotency_identity,
            "logical_output_id": logical_output_id,
            "media_type": _MEDIA_TYPE,
            "page_id": page_id,
            "project_id": project_id,
            "provenance_assurance": _PROVENANCE,
            "provider_reference": provider_reference,
            "schema_id": _CANONICAL_RESULT_SCHEMA_ID,
            "schema_version": _CANONICAL_RESULT_SCHEMA_VERSION,
            "submission_receipt_identity": submission_receipt_identity,
            "target_page_reference": target_page_reference,
        }
    )


def _is_sha256(value: object) -> bool:
    return type(value) is str and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _is_reference(value: object) -> bool:
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
    )


class _DeliveryStatusV1(StrEnum):
    DELIVERY_STARTED = "DELIVERY_STARTED"
    BYTES_VALIDATED = "BYTES_VALIDATED"
    ASSET_REGISTERED = "ASSET_REGISTERED"
    DELIVERY_COMPLETED = "DELIVERY_COMPLETED"
    DELIVERY_MALFORMED = "DELIVERY_MALFORMED"
    DELIVERY_CONFLICT = "DELIVERY_CONFLICT"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
    CORRUPT = "CORRUPT"


@dataclass(frozen=True, slots=True)
class _DeliveryBindingInputV1:
    """Private trusted-composition input; it is not a capability or public DTO."""

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
    asset_sha256: str
    expected_byte_length: int
    media_type: str = _MEDIA_TYPE
    provenance_assurance: str = _PROVENANCE

    def __post_init__(self) -> None:
        if (
            self.media_type != _MEDIA_TYPE
            or self.provenance_assurance != _PROVENANCE
            or not 1 <= self.expected_byte_length <= 25 * 1024 * 1024
            or not _is_sha256(self.canonical_result_identity)
            or not _is_sha256(self.asset_sha256)
            or not all(
                _is_reference(value)
                for value in (
                    self.attempt_id,
                    self.project_id,
                    self.page_id,
                    self.target_page_reference,
                    self.provider_reference,
                    self.dispatch_identity,
                    self.idempotency_identity,
                    self.submission_receipt_identity,
                    self.logical_output_id,
                )
            )
        ):
            raise _unavailable()
        if self.canonical_result_identity != _canonical_result_identity_v1(
            attempt_id=self.attempt_id,
            project_id=self.project_id,
            page_id=self.page_id,
            target_page_reference=self.target_page_reference,
            provider_reference=self.provider_reference,
            dispatch_identity=self.dispatch_identity,
            idempotency_identity=self.idempotency_identity,
            submission_receipt_identity=self.submission_receipt_identity,
            logical_output_id=self.logical_output_id,
            asset_sha256=self.asset_sha256,
            expected_byte_length=self.expected_byte_length,
        ):
            raise _unavailable()

    def canonical_result_projection(self) -> dict[str, object]:
        """The R03/R14 canonical provider-result identity projection."""

        return {
            "asset_sha256": self.asset_sha256,
            "attempt_id": self.attempt_id,
            "dispatch_identity": self.dispatch_identity,
            "expected_byte_length": self.expected_byte_length,
            "idempotency_identity": self.idempotency_identity,
            "logical_output_id": self.logical_output_id,
            "media_type": self.media_type,
            "page_id": self.page_id,
            "project_id": self.project_id,
            "provenance_assurance": self.provenance_assurance,
            "provider_reference": self.provider_reference,
            "schema_id": _CANONICAL_RESULT_SCHEMA_ID,
            "schema_version": _CANONICAL_RESULT_SCHEMA_VERSION,
            "submission_receipt_identity": self.submission_receipt_identity,
            "target_page_reference": self.target_page_reference,
        }

    def base_projection(self) -> dict[str, object]:
        return {
            "asset_sha256": self.asset_sha256,
            "attempt_id": self.attempt_id,
            "canonical_result_identity": self.canonical_result_identity,
            "dispatch_identity": self.dispatch_identity,
            "expected_byte_length": self.expected_byte_length,
            "idempotency_identity": self.idempotency_identity,
            "logical_output_id": self.logical_output_id,
            "media_type": self.media_type,
            "page_id": self.page_id,
            "project_id": self.project_id,
            "provenance_assurance": self.provenance_assurance,
            "provider_reference": self.provider_reference,
            "schema_id": _SCHEMA_ID,
            "schema_version": _SCHEMA_VERSION,
            "submission_receipt_identity": self.submission_receipt_identity,
            "target_page_reference": self.target_page_reference,
        }

    @property
    def delivery_identity(self) -> str:
        return _digest(self.base_projection())

    def projection(self) -> dict[str, object]:
        value = self.base_projection()
        value["binding_digest"] = self.delivery_identity
        value["delivery_identity"] = self.delivery_identity
        return value


@dataclass(frozen=True, slots=True)
class _DeliveryReplayV1:
    binding: _DeliveryBindingInputV1
    status: _DeliveryStatusV1
    sequence: int
    last_event_digest: str
    asset_id: str | None
    asset_registration_digest: str | None


@dataclass(frozen=True, slots=True)
class _CorruptDeliveryReplayV1:
    """Read-only external classification when no trustworthy binding remains."""

    status: _DeliveryStatusV1 = _DeliveryStatusV1.CORRUPT


class PrivateRealAssetDeliveryJournal(protocol._RealDeliveryJournalPeerV1):
    """Private I02 SQLite journal; no owner, provider, or application authority."""

    __slots__ = ("_database_path", "_delivery_identity", "_owner", "_peer")

    def __init__(self, owner: LocalDurableAssetOwner) -> None:
        if type(owner) is not LocalDurableAssetOwner:
            raise _unavailable()
        root = owner._root
        if not isinstance(root, Path) or not root.is_absolute():
            raise _unavailable()
        self._database_path = root / "_durability" / "_post_lts_real_asset_delivery" / "real-asset-delivery.sqlite3"
        self._delivery_identity: str | None = None
        self._owner = owner
        self._peer: protocol._RegisteredOwnerVerificationJournalPeerV1 | None = None
        self._initialize_or_validate()

    def _bind_registered_owner_verification_peer_v1(
        self,
        peer: protocol._RegisteredOwnerVerificationJournalPeerV1,
        binding: protocol._JournalPeerBindingV1,
    ) -> None:
        if (
            self._peer is not None
            or type(peer) is not protocol._RegisteredOwnerVerificationJournalPeerV1
            or type(binding) is not protocol._JournalPeerBindingV1
        ):
            raise _unavailable()
        self._peer = peer

    def _begin_delivery_v1(self, binding: _DeliveryBindingInputV1) -> _DeliveryReplayV1:
        if type(binding) is not _DeliveryBindingInputV1:
            raise _unavailable()
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = self._find_by_attempt(connection, binding.attempt_id)
            if existing is not None:
                replay = self._replay_connection(connection, str(existing[0]))
                if replay.binding == binding:
                    connection.commit()
                    self._delivery_identity = replay.binding.delivery_identity
                    return replay
                connection.rollback()
                return _DeliveryReplayV1(binding, _DeliveryStatusV1.DELIVERY_CONFLICT, -1, "", None, None)
            composite = connection.execute(
                "SELECT delivery_identity FROM real_asset_delivery_bindings "
                "WHERE canonical_result_identity = ? AND logical_output_id = ? AND asset_sha256 = ?",
                (binding.canonical_result_identity, binding.logical_output_id, binding.asset_sha256),
            ).fetchone()
            if composite is not None:
                self._replay_connection(connection, str(composite[0]))
                connection.rollback()
                return _DeliveryReplayV1(binding, _DeliveryStatusV1.DELIVERY_CONFLICT, -1, "", None, None)
            delivery_identity = binding.delivery_identity
            payload = {
                "asset_sha256": binding.asset_sha256,
                "canonical_result_identity": binding.canonical_result_identity,
                "expected_byte_length": binding.expected_byte_length,
                "logical_output_id": binding.logical_output_id,
                "media_type": binding.media_type,
                "provenance_assurance": binding.provenance_assurance,
            }
            event_digest = self._insert_event(connection, binding, 0, "DELIVERY_STARTED", _GENESIS_DIGEST, payload)
            connection.execute(
                "INSERT INTO real_asset_delivery_bindings "
                "(delivery_identity, attempt_id, canonical_result_identity, logical_output_id, asset_sha256, "
                "binding_json, binding_digest, phase, sequence, terminal_code, last_event_digest) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    delivery_identity,
                    binding.attempt_id,
                    binding.canonical_result_identity,
                    binding.logical_output_id,
                    binding.asset_sha256,
                    _canonical_json(binding.projection()),
                    delivery_identity,
                    _DeliveryStatusV1.DELIVERY_STARTED.value,
                    0,
                    None,
                    event_digest,
                ),
            )
            connection.commit()
            self._delivery_identity = delivery_identity
            return _DeliveryReplayV1(binding, _DeliveryStatusV1.DELIVERY_STARTED, 0, event_digest, None, None)
        except (sqlite3.Error, TypeError, ValueError) as error:
            _rollback(connection)
            if isinstance(error, ValueError) and str(error) == _UNAVAILABLE:
                raise
            raise _unavailable() from error
        finally:
            connection.close()

    def _record_bytes_validated_v1(
        self,
        actual_byte_length: int,
        asset_sha256: str,
        media_type: str,
    ) -> _DeliveryReplayV1:
        replay = self._require_current(_DeliveryStatusV1.DELIVERY_STARTED)
        if type(actual_byte_length) is not int or actual_byte_length != replay.binding.expected_byte_length:
            return self._append_terminal_v1(replay, _DeliveryStatusV1.DELIVERY_MALFORMED, "LENGTH_MISMATCH")
        if asset_sha256 != replay.binding.asset_sha256:
            return self._append_terminal_v1(replay, _DeliveryStatusV1.DELIVERY_MALFORMED, "HASH_MISMATCH")
        if media_type != _MEDIA_TYPE:
            return self._append_terminal_v1(replay, _DeliveryStatusV1.DELIVERY_MALFORMED, "MEDIA_TYPE_INVALID")
        return self._append_event_v1(
            replay,
            "BYTES_VALIDATED",
            {
                "actual_byte_length": actual_byte_length,
                "asset_sha256": asset_sha256,
                "media_type": media_type,
                "png_structure": "VALID",
            },
            _DeliveryStatusV1.BYTES_VALIDATED,
            None,
        )

    def _record_asset_registered_v1(
        self,
        asset_id: str,
        owner_attempt_id: str,
        owner_provider_reference: str,
        owner_media_type: str,
        owner_digest: str,
    ) -> _DeliveryReplayV1:
        """Reject raw owner-like facts; R14 requires owner-held authority."""

        raise _unavailable()

    def _record_authenticated_asset_registered_v1(self, result: object) -> _DeliveryReplayV1:
        """Consume the exact one-shot owner commitment before any I02 mutation."""

        replay = self._require_current(_DeliveryStatusV1.BYTES_VALIDATED)
        try:
            facts = self._owner._consume_real_delivery_registration_v1(result)
        except _OwnerRegistryCorruptV1:
            return _DeliveryReplayV1(
                replay.binding,
                _DeliveryStatusV1.CORRUPT,
                replay.sequence,
                replay.last_event_digest,
                replay.asset_id,
                replay.asset_registration_digest,
            )
        except ValueError:
            # The owner distinguishes registry-integrity corruption above.  Its
            # remaining rejection is the exact process-local commitment boundary
            # (R14 matrix case 08), whose externally visible outcome is recovery.
            return _DeliveryReplayV1(
                replay.binding,
                _DeliveryStatusV1.RECOVERY_REQUIRED,
                replay.sequence,
                replay.last_event_digest,
                replay.asset_id,
                replay.asset_registration_digest,
            )
        if type(facts) is not _OwnerRegistrationFactsV1:
            raise _unavailable()
        try:
            return self._record_authenticated_asset_registered_from_owner_facts_v1(replay, facts)
        except ValueError as error:
            # This is reached only after the owner has tombstoned the exact
            # commitment.  The journal's sentinel denotes an unsuccessful
            # pre-commit I02 append; it must not revive that authority.
            if str(error) != _UNAVAILABLE:
                raise
            return _DeliveryReplayV1(
                replay.binding,
                _DeliveryStatusV1.RECOVERY_REQUIRED,
                replay.sequence,
                replay.last_event_digest,
                replay.asset_id,
                replay.asset_registration_digest,
            )

    def _record_authenticated_asset_registered_from_owner_facts_v1(
        self, replay: _DeliveryReplayV1, facts: _OwnerRegistrationFactsV1
    ) -> _DeliveryReplayV1:
        replay = self._require_current(_DeliveryStatusV1.BYTES_VALIDATED)
        if (
            not _is_reference(facts.asset_id)
            or facts.attempt_id != replay.binding.attempt_id
            or facts.provider_reference != replay.binding.provider_reference
            or facts.media_type != _MEDIA_TYPE
            or facts.digest != replay.binding.asset_sha256
        ):
            return self._append_terminal_v1(replay, _DeliveryStatusV1.DELIVERY_CONFLICT, "DELIVERY_BINDING_CONFLICT")
        registration_digest = _asset_registration_digest(
            facts.asset_id,
            replay.binding.attempt_id,
            replay.binding.provider_reference,
            _MEDIA_TYPE,
            replay.binding.asset_sha256,
        )
        return self._append_event_v1(
            replay,
            "ASSET_REGISTERED",
            {"asset_id": facts.asset_id, "asset_registration_digest": registration_digest},
            _DeliveryStatusV1.ASSET_REGISTERED,
            None,
        )

    def _replay_registered_asset_for_owner_verification_v1(self) -> protocol._RegisteredAssetReplayFactsV1:
        replay = self._require_current(_DeliveryStatusV1.ASSET_REGISTERED)
        if replay.asset_id is None or replay.asset_registration_digest is None:
            raise _unavailable()
        return protocol._RegisteredAssetReplayFactsV1(
            delivery_identity=replay.binding.delivery_identity,
            attempt_id=replay.binding.attempt_id,
            binding_digest=replay.binding.delivery_identity,
            provider_reference=replay.binding.provider_reference,
            canonical_result_identity=replay.binding.canonical_result_identity,
            logical_output_id=replay.binding.logical_output_id,
            asset_id=replay.asset_id,
            asset_registration_digest=replay.asset_registration_digest,
            sha256=replay.binding.asset_sha256,
            expected_byte_length=replay.binding.expected_byte_length,
            media_type=replay.binding.media_type,
            provenance_assurance=replay.binding.provenance_assurance,
            phase=_DeliveryStatusV1.ASSET_REGISTERED.value,
            sequence=replay.sequence,
            last_event_digest=replay.last_event_digest,
        )

    def _complete_registered_asset_from_verified_capability_v1(
        self,
        dispatch: protocol._ActiveCompletionDispatchV1,
    ) -> protocol._JournalCompletionCallbackResultV1:
        if type(dispatch) is not protocol._ActiveCompletionDispatchV1 or self._peer is None:
            return protocol._JournalCompletionCallbackResultV1.NOT_COMMITTED
        try:
            request_facts, verified = self._peer._assert_active_completion_dispatch_v1(dispatch)
            connection = self._connect()
        except ValueError:
            return protocol._JournalCompletionCallbackResultV1.NOT_COMMITTED
        except (OSError, sqlite3.Error, TypeError):
            return protocol._JournalCompletionCallbackResultV1.UNKNOWN_OUTCOME
        try:
            connection.execute("BEGIN IMMEDIATE")
            replay = self._replay_connection(connection, request_facts.delivery_identity)
            if replay.status is _DeliveryStatusV1.DELIVERY_COMPLETED:
                if self._request_matches_completed_replay(connection, request_facts, replay):
                    connection.commit()
                    return protocol._JournalCompletionCallbackResultV1.ALREADY_COMMITTED_EXACT
                connection.rollback()
                return protocol._JournalCompletionCallbackResultV1.CORRUPT
            if replay.status is not _DeliveryStatusV1.ASSET_REGISTERED:
                connection.rollback()
                return protocol._JournalCompletionCallbackResultV1.TERMINAL_NO_COMMIT
            if not self._request_matches_replay(request_facts, replay) or not self._verified_matches_replay(verified, replay):
                connection.rollback()
                return protocol._JournalCompletionCallbackResultV1.CORRUPT
            completed = self._append_event_in_transaction(
                connection,
                replay,
                "DELIVERY_COMPLETED",
                {"asset_id": replay.asset_id, "asset_registration_digest": replay.asset_registration_digest},
                _DeliveryStatusV1.DELIVERY_COMPLETED,
                _DeliveryStatusV1.DELIVERY_COMPLETED.value,
            )
            connection.commit()
            self._delivery_identity = completed.binding.delivery_identity
            return protocol._JournalCompletionCallbackResultV1.COMMITTED
        except ValueError:
            _rollback(connection)
            return protocol._JournalCompletionCallbackResultV1.CORRUPT
        except (OSError, sqlite3.Error, TypeError):
            _rollback(connection)
            return protocol._JournalCompletionCallbackResultV1.UNKNOWN_OUTCOME
        finally:
            connection.close()

    def _replay_v1(self, delivery_identity: str | None = None) -> _DeliveryReplayV1:
        identity = delivery_identity or self._delivery_identity
        if type(identity) is not str or not _is_sha256(identity):
            raise _unavailable()
        connection: sqlite3.Connection | None = None
        try:
            connection = self._connect()
            connection.execute("BEGIN")
            binding_row = connection.execute(
                "SELECT 1 FROM real_asset_delivery_bindings WHERE delivery_identity = ?", (identity,)
            ).fetchone()
            if binding_row is None:
                event_row = connection.execute(
                    "SELECT 1 FROM real_asset_delivery_events WHERE delivery_identity = ?", (identity,)
                ).fetchone()
                if event_row is not None or identity == self._delivery_identity:
                    raise _DurableJournalCorruptV1(_UNAVAILABLE)
                raise _UnknownDeliveryIdentityV1(_UNAVAILABLE)
            replay = self._replay_connection(connection, identity)
            connection.commit()
            return replay
        except _UnknownDeliveryIdentityV1 as error:
            _rollback(connection)
            raise _unavailable() from error
        except ValueError as error:
            _rollback(connection)
            if isinstance(error, _DurableJournalCorruptV1):
                raise
            raise _DurableJournalCorruptV1(_UNAVAILABLE) from error
        except (sqlite3.Error, TypeError) as error:
            _rollback(connection)
            raise _unavailable() from error
        finally:
            if connection is not None:
                connection.close()

    def _reopen_v1(
        self, delivery_identity: str | None = None
    ) -> _DeliveryReplayV1 | _CorruptDeliveryReplayV1:
        """Return the sole composition-visible recovery classification on reopen."""

        try:
            replay = self._replay_v1(delivery_identity)
        except _DurableJournalCorruptV1:
            return _CorruptDeliveryReplayV1()
        if replay.status is _DeliveryStatusV1.BYTES_VALIDATED:
            return _DeliveryReplayV1(
                replay.binding,
                _DeliveryStatusV1.RECOVERY_REQUIRED,
                replay.sequence,
                replay.last_event_digest,
                replay.asset_id,
                replay.asset_registration_digest,
            )
        return replay

    def _require_current(self, expected: _DeliveryStatusV1) -> _DeliveryReplayV1:
        replay = self._replay_v1()
        if replay.status is not expected:
            raise _unavailable()
        return replay

    def _append_terminal_v1(
        self,
        replay: _DeliveryReplayV1,
        status: _DeliveryStatusV1,
        reason_code: str,
    ) -> _DeliveryReplayV1:
        event_type = "DELIVERY_MALFORMED" if status is _DeliveryStatusV1.DELIVERY_MALFORMED else "DELIVERY_CONFLICT"
        payload: dict[str, object] = {"reason_code": reason_code}
        if status is _DeliveryStatusV1.DELIVERY_CONFLICT:
            payload["conflicting_digest"] = replay.binding.delivery_identity
        return self._append_event_v1(replay, event_type, payload, status, status.value)

    def _append_event_v1(
        self,
        replay: _DeliveryReplayV1,
        event_type: str,
        payload: dict[str, object],
        status: _DeliveryStatusV1,
        terminal_code: str | None,
    ) -> _DeliveryReplayV1:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            current = self._replay_connection(connection, replay.binding.delivery_identity)
            if current != replay:
                raise _unavailable()
            result = self._append_event_in_transaction(connection, current, event_type, payload, status, terminal_code)
            connection.commit()
            return result
        except (sqlite3.Error, TypeError, ValueError) as error:
            _rollback(connection)
            if isinstance(error, ValueError) and str(error) == _UNAVAILABLE:
                raise
            raise _unavailable() from error
        finally:
            connection.close()

    def _append_event_in_transaction(
        self,
        connection: sqlite3.Connection,
        replay: _DeliveryReplayV1,
        event_type: str,
        payload: dict[str, object],
        status: _DeliveryStatusV1,
        terminal_code: str | None,
    ) -> _DeliveryReplayV1:
        sequence = replay.sequence + 1
        if sequence >= _MAX_EVENTS:
            raise _unavailable()
        digest = self._insert_event(connection, replay.binding, sequence, event_type, replay.last_event_digest, payload)
        updated = connection.execute(
            "UPDATE real_asset_delivery_bindings SET phase = ?, sequence = ?, terminal_code = ?, last_event_digest = ? "
            "WHERE delivery_identity = ? AND sequence = ? AND last_event_digest = ?",
            (status.value, sequence, terminal_code, digest, replay.binding.delivery_identity, replay.sequence, replay.last_event_digest),
        )
        if updated.rowcount != 1:
            raise _unavailable()
        asset_id = replay.asset_id
        registration_digest = replay.asset_registration_digest
        if event_type == "ASSET_REGISTERED":
            asset_id = str(payload["asset_id"])
            registration_digest = str(payload["asset_registration_digest"])
        return _DeliveryReplayV1(replay.binding, status, sequence, digest, asset_id, registration_digest)

    def _insert_event(
        self,
        connection: sqlite3.Connection,
        binding: _DeliveryBindingInputV1,
        sequence: int,
        event_type: str,
        previous_digest: str,
        payload: dict[str, object],
    ) -> str:
        payload_json = _canonical_json(payload)
        payload_digest = _digest(payload)
        envelope = {
            "attempt_id": binding.attempt_id,
            "binding_digest": binding.delivery_identity,
            "delivery_identity": binding.delivery_identity,
            "event_type": event_type,
            "payload": payload,
            "payload_digest": payload_digest,
            "previous_event_digest": previous_digest,
            "schema_id": _SCHEMA_ID,
            "schema_version": _SCHEMA_VERSION,
            "sequence": sequence,
        }
        if len(_canonical_json(envelope).encode("utf-8")) > _MAX_EVENT_BYTES:
            raise _unavailable()
        event_digest = _digest(envelope)
        connection.execute(
            "INSERT INTO real_asset_delivery_events "
            "(delivery_identity, sequence, event_type, payload_json, payload_digest, previous_event_digest, event_digest) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (binding.delivery_identity, sequence, event_type, payload_json, payload_digest, previous_digest, event_digest),
        )
        return event_digest

    def _find_by_attempt(self, connection: sqlite3.Connection, attempt_id: str) -> tuple[object, ...] | None:
        row = connection.execute(
            "SELECT delivery_identity FROM real_asset_delivery_bindings WHERE attempt_id = ?", (attempt_id,)
        ).fetchone()
        return cast(tuple[object, ...] | None, row)

    def _replay_connection(self, connection: sqlite3.Connection, delivery_identity: str) -> _DeliveryReplayV1:
        _validate_schema(connection)
        row = connection.execute(
            "SELECT delivery_identity, attempt_id, canonical_result_identity, logical_output_id, asset_sha256, binding_json, "
            "binding_digest, phase, sequence, terminal_code, last_event_digest "
            "FROM real_asset_delivery_bindings WHERE delivery_identity = ?",
            (delivery_identity,),
        ).fetchone()
        if row is None or len(row) != 11 or not all(type(value) in (str, int, type(None)) for value in row):
            raise _unavailable()
        (
            row_identity,
            attempt_id,
            canonical_result_identity,
            logical_output_id,
            asset_sha256,
            binding_json,
            binding_digest,
            phase,
            sequence,
            terminal_code,
            last_event_digest,
        ) = row
        if (
            type(row_identity) is not str
            or type(attempt_id) is not str
            or type(canonical_result_identity) is not str
            or type(logical_output_id) is not str
            or type(asset_sha256) is not str
            or type(binding_json) is not str
            or type(binding_digest) is not str
            or type(phase) is not str
            or type(sequence) is not int
            or type(last_event_digest) is not str
        ):
            raise _unavailable()
        binding = _binding_from_json(binding_json)
        if (
            binding.delivery_identity != row_identity
            or binding.delivery_identity != binding_digest
            or row_identity != delivery_identity
            or binding.attempt_id != attempt_id
            or binding.canonical_result_identity != canonical_result_identity
            or binding.logical_output_id != logical_output_id
            or binding.asset_sha256 != asset_sha256
        ):
            raise _unavailable()
        events = connection.execute(
            "SELECT delivery_identity, sequence, event_type, payload_json, payload_digest, previous_event_digest, event_digest "
            "FROM real_asset_delivery_events WHERE delivery_identity = ? ORDER BY sequence",
            (delivery_identity,),
        ).fetchall()
        replay = _replay_events(binding, events)
        if (
            replay.status.value != phase
            or replay.sequence != sequence
            or replay.last_event_digest != last_event_digest
            or _terminal_code(replay.status) != terminal_code
        ):
            raise _unavailable()
        return replay

    def _request_matches_replay(
        self, facts: protocol._RegisteredAssetReplayFactsV1, replay: _DeliveryReplayV1
    ) -> bool:
        return bool(
            replay.asset_id is not None
            and replay.asset_registration_digest is not None
            and facts.delivery_identity == replay.binding.delivery_identity
            and facts.binding_digest == replay.binding.delivery_identity
            and facts.attempt_id == replay.binding.attempt_id
            and facts.provider_reference == replay.binding.provider_reference
            and facts.canonical_result_identity == replay.binding.canonical_result_identity
            and facts.logical_output_id == replay.binding.logical_output_id
            and facts.asset_id == replay.asset_id
            and facts.asset_registration_digest == replay.asset_registration_digest
            and facts.sha256 == replay.binding.asset_sha256
            and facts.expected_byte_length == replay.binding.expected_byte_length
            and facts.media_type == _MEDIA_TYPE
            and facts.provenance_assurance == _PROVENANCE
            and facts.phase == _DeliveryStatusV1.ASSET_REGISTERED.value
            and facts.sequence == replay.sequence
            and facts.last_event_digest == replay.last_event_digest
        )

    def _request_matches_completed_replay(
        self,
        connection: sqlite3.Connection,
        facts: protocol._RegisteredAssetReplayFactsV1,
        replay: _DeliveryReplayV1,
    ) -> bool:
        if (
            replay.status is not _DeliveryStatusV1.DELIVERY_COMPLETED
            or replay.asset_id is None
            or replay.asset_registration_digest is None
            or facts.delivery_identity != replay.binding.delivery_identity
            or facts.binding_digest != replay.binding.delivery_identity
            or facts.attempt_id != replay.binding.attempt_id
            or facts.provider_reference != replay.binding.provider_reference
            or facts.canonical_result_identity != replay.binding.canonical_result_identity
            or facts.logical_output_id != replay.binding.logical_output_id
            or facts.asset_id != replay.asset_id
            or facts.asset_registration_digest != replay.asset_registration_digest
            or facts.sha256 != replay.binding.asset_sha256
            or facts.expected_byte_length != replay.binding.expected_byte_length
            or facts.media_type != _MEDIA_TYPE
            or facts.provenance_assurance != _PROVENANCE
            or facts.phase != _DeliveryStatusV1.ASSET_REGISTERED.value
            or facts.sequence != replay.sequence - 1
        ):
            return False
        row = connection.execute(
            "SELECT previous_event_digest FROM real_asset_delivery_events "
            "WHERE delivery_identity = ? AND sequence = ?",
            (replay.binding.delivery_identity, replay.sequence),
        ).fetchone()
        return bool(row is not None and len(row) == 1 and row[0] == facts.last_event_digest)

    def _verified_matches_replay(
        self, verified: protocol._VerifiedOwnerAssetFactsV1, replay: _DeliveryReplayV1
    ) -> bool:
        return bool(
            verified.owner_attempt_id == replay.binding.attempt_id
            and verified.owner_provider_reference == replay.binding.provider_reference
            and verified.owner_digest == replay.binding.asset_sha256
            and verified.verified_sha256 == replay.binding.asset_sha256
            and verified.verified_byte_length == replay.binding.expected_byte_length
            and verified.owner_storage_name is not None
            and verified.verified_media_type == _MEDIA_TYPE
        )

    def _initialize_or_validate(self) -> None:
        database = self._database_path
        directory = database.parent
        existed = database.exists()
        if existed and not _regular_file(database):
            raise _unavailable()
        if existed and database.stat().st_size == 0:
            raise _unavailable()
        if not existed:
            _prepare_empty_owner_directory(directory)
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(str(database), timeout=0.0, isolation_level=None)
            if not existed:
                connection.execute("BEGIN IMMEDIATE")
                if int(connection.execute("PRAGMA user_version").fetchone()[0]) != 0 or _user_objects(connection):
                    raise _unavailable()
                _create_schema(connection)
                connection.commit()
            _configure_connection(connection)
            _validate_schema(connection)
        except (OSError, sqlite3.Error, TypeError, ValueError) as error:
            _rollback(connection)
            if isinstance(error, ValueError) and str(error) == _UNAVAILABLE:
                raise
            raise _unavailable() from error
        finally:
            if connection is not None:
                connection.close()

    def _connect(self) -> sqlite3.Connection:
        if not _regular_file(self._database_path) or self._database_path.stat().st_size == 0:
            raise _unavailable()
        try:
            connection = sqlite3.connect(str(self._database_path), timeout=0.0, isolation_level=None)
            _configure_connection(connection)
            _validate_schema(connection)
            return connection
        except (OSError, sqlite3.Error, TypeError, ValueError) as error:
            if "connection" in locals():
                connection.close()
            if isinstance(error, ValueError) and str(error) == _UNAVAILABLE:
                raise
            raise _unavailable() from error


def _asset_registration_digest(
    asset_id: str, attempt_id: str, provider_reference: str, media_type: str, asset_sha256: str
) -> str:
    return _digest(
        {
            "asset_id": asset_id,
            "asset_sha256": asset_sha256,
            "attempt_id": attempt_id,
            "media_type": media_type,
            "provider_reference": provider_reference,
            "schema": _ASSET_REGISTRATION_SCHEMA,
            "version": 1,
        }
    )


def _binding_from_json(binding_json: str) -> _DeliveryBindingInputV1:
    try:
        loaded = json.loads(binding_json)
    except (TypeError, ValueError) as error:
        raise _unavailable() from error
    if type(loaded) is not dict or _canonical_json(loaded) != binding_json:
        raise _unavailable()
    required = {
        "asset_sha256", "attempt_id", "binding_digest", "canonical_result_identity", "delivery_identity",
        "dispatch_identity", "expected_byte_length", "idempotency_identity", "logical_output_id", "media_type",
        "page_id", "project_id", "provenance_assurance", "provider_reference", "schema_id", "schema_version",
        "submission_receipt_identity", "target_page_reference",
    }
    if set(loaded) != required or loaded.get("schema_id") != _SCHEMA_ID or loaded.get("schema_version") != _SCHEMA_VERSION:
        raise _unavailable()
    try:
        binding = _DeliveryBindingInputV1(
            attempt_id=loaded["attempt_id"], project_id=loaded["project_id"], page_id=loaded["page_id"],
            target_page_reference=loaded["target_page_reference"], provider_reference=loaded["provider_reference"],
            dispatch_identity=loaded["dispatch_identity"], idempotency_identity=loaded["idempotency_identity"],
            submission_receipt_identity=loaded["submission_receipt_identity"], logical_output_id=loaded["logical_output_id"],
            canonical_result_identity=loaded["canonical_result_identity"], asset_sha256=loaded["asset_sha256"],
            expected_byte_length=loaded["expected_byte_length"], media_type=loaded["media_type"],
            provenance_assurance=loaded["provenance_assurance"],
        )
    except (KeyError, TypeError, ValueError) as error:
        raise _unavailable() from error
    if loaded["delivery_identity"] != binding.delivery_identity or loaded["binding_digest"] != binding.delivery_identity:
        raise _unavailable()
    return binding


def _replay_events(binding: _DeliveryBindingInputV1, rows: list[tuple[object, ...]]) -> _DeliveryReplayV1:
    if not 1 <= len(rows) <= _MAX_EVENTS:
        raise _unavailable()
    status: _DeliveryStatusV1 | None = None
    asset_id: str | None = None
    registration_digest: str | None = None
    previous = _GENESIS_DIGEST
    for expected_sequence, row in enumerate(rows):
        if len(row) != 7:
            raise _unavailable()
        identity, sequence, event_type, payload_json, payload_digest, previous_digest, event_digest = row
        if (
            identity != binding.delivery_identity
            or sequence != expected_sequence
            or type(event_type) is not str
            or type(payload_json) is not str
            or type(payload_digest) is not str
            or previous_digest != previous
            or type(event_digest) is not str
        ):
            raise _unavailable()
        try:
            payload = json.loads(payload_json)
        except (TypeError, ValueError) as error:
            raise _unavailable() from error
        if type(payload) is not dict or _canonical_json(payload) != payload_json or _digest(payload) != payload_digest:
            raise _unavailable()
        envelope = {
            "attempt_id": binding.attempt_id, "binding_digest": binding.delivery_identity,
            "delivery_identity": binding.delivery_identity, "event_type": event_type, "payload": payload,
            "payload_digest": payload_digest, "previous_event_digest": previous_digest, "schema_id": _SCHEMA_ID,
            "schema_version": _SCHEMA_VERSION, "sequence": expected_sequence,
        }
        if len(_canonical_json(envelope).encode("utf-8")) > _MAX_EVENT_BYTES or _digest(envelope) != event_digest:
            raise _unavailable()
        status, asset_id, registration_digest = _apply_event(
            binding, status, event_type, payload, asset_id, registration_digest
        )
        previous = event_digest
    if status is None:
        raise _unavailable()
    return _DeliveryReplayV1(binding, status, len(rows) - 1, previous, asset_id, registration_digest)


def _apply_event(
    binding: _DeliveryBindingInputV1,
    status: _DeliveryStatusV1 | None,
    event_type: str,
    payload: dict[str, object],
    asset_id: str | None,
    registration_digest: str | None,
) -> tuple[_DeliveryStatusV1, str | None, str | None]:
    expected: dict[str, set[str]] = {
        "DELIVERY_STARTED": {"asset_sha256", "canonical_result_identity", "expected_byte_length", "logical_output_id", "media_type", "provenance_assurance"},
        "BYTES_VALIDATED": {"actual_byte_length", "asset_sha256", "media_type", "png_structure"},
        "ASSET_REGISTERED": {"asset_id", "asset_registration_digest"},
        "DELIVERY_COMPLETED": {"asset_id", "asset_registration_digest"},
        "DELIVERY_MALFORMED": {"reason_code"},
        "DELIVERY_CONFLICT": {"reason_code", "conflicting_digest"},
        "DELIVERY_RECOVERY_REQUIRED": {"reason_code"},
    }
    if event_type not in expected or set(payload) != expected[event_type]:
        raise _unavailable()
    if event_type == "DELIVERY_STARTED" and status is None and payload == {
        "asset_sha256": binding.asset_sha256, "canonical_result_identity": binding.canonical_result_identity,
        "expected_byte_length": binding.expected_byte_length, "logical_output_id": binding.logical_output_id,
        "media_type": _MEDIA_TYPE, "provenance_assurance": _PROVENANCE,
    }:
        return _DeliveryStatusV1.DELIVERY_STARTED, None, None
    if event_type == "BYTES_VALIDATED" and status is _DeliveryStatusV1.DELIVERY_STARTED and payload == {
        "actual_byte_length": binding.expected_byte_length, "asset_sha256": binding.asset_sha256,
        "media_type": _MEDIA_TYPE, "png_structure": "VALID",
    }:
        return _DeliveryStatusV1.BYTES_VALIDATED, None, None
    if event_type == "ASSET_REGISTERED" and status is _DeliveryStatusV1.BYTES_VALIDATED:
        candidate = payload.get("asset_id")
        digest = payload.get("asset_registration_digest")
        if (
            type(candidate) is not str
            or type(digest) is not str
            or not _is_reference(candidate)
            or not _is_sha256(digest)
        ):
            raise _unavailable()
        if digest != _asset_registration_digest(candidate, binding.attempt_id, binding.provider_reference, _MEDIA_TYPE, binding.asset_sha256):
            raise _unavailable()
        return _DeliveryStatusV1.ASSET_REGISTERED, candidate, digest
    if event_type == "DELIVERY_COMPLETED" and status is _DeliveryStatusV1.ASSET_REGISTERED and payload == {
        "asset_id": asset_id, "asset_registration_digest": registration_digest,
    }:
        return _DeliveryStatusV1.DELIVERY_COMPLETED, asset_id, registration_digest
    if event_type == "DELIVERY_MALFORMED" and status is _DeliveryStatusV1.DELIVERY_STARTED and _reason(payload):
        return _DeliveryStatusV1.DELIVERY_MALFORMED, None, None
    if event_type == "DELIVERY_CONFLICT" and status in (_DeliveryStatusV1.BYTES_VALIDATED, _DeliveryStatusV1.ASSET_REGISTERED) and _reason(payload):
        if not _is_sha256(payload.get("conflicting_digest")):
            raise _unavailable()
        return _DeliveryStatusV1.DELIVERY_CONFLICT, asset_id, registration_digest
    if event_type == "DELIVERY_RECOVERY_REQUIRED" and status in (_DeliveryStatusV1.BYTES_VALIDATED, _DeliveryStatusV1.ASSET_REGISTERED) and _reason(payload):
        return _DeliveryStatusV1.RECOVERY_REQUIRED, asset_id, registration_digest
    raise _unavailable()


def _reason(payload: dict[str, object]) -> bool:
    return payload.get("reason_code") in {
        "HANDOFF_INVALID", "LENGTH_MISMATCH", "HASH_MISMATCH", "MEDIA_TYPE_INVALID", "PNG_INVALID",
        "ASSET_OWNER_CONFLICT", "ASSET_REGISTRY_UNAVAILABLE", "INTERRUPTED_DELIVERY", "DELIVERY_BINDING_CONFLICT",
    }


def _terminal_code(status: _DeliveryStatusV1) -> str | None:
    return {
        _DeliveryStatusV1.DELIVERY_COMPLETED: _DeliveryStatusV1.DELIVERY_COMPLETED.value,
        _DeliveryStatusV1.DELIVERY_MALFORMED: _DeliveryStatusV1.DELIVERY_MALFORMED.value,
        _DeliveryStatusV1.DELIVERY_CONFLICT: _DeliveryStatusV1.DELIVERY_CONFLICT.value,
        _DeliveryStatusV1.RECOVERY_REQUIRED: _DeliveryStatusV1.RECOVERY_REQUIRED.value,
    }.get(status)


def _regular_file(path: Path) -> bool:
    try:
        mode = path.lstat().st_mode
    except OSError:
        return False
    return stat.S_ISREG(mode) and not path.is_symlink()


def _prepare_empty_owner_directory(directory: Path) -> None:
    try:
        if directory.exists():
            if directory.is_symlink() or not directory.is_dir() or any(directory.iterdir()):
                raise _unavailable()
        else:
            directory.mkdir(parents=True, exist_ok=False)
    except OSError as error:
        raise _unavailable() from error


def _configure_connection(connection: sqlite3.Connection) -> None:
    mode = str(connection.execute("PRAGMA journal_mode = DELETE").fetchone()[0]).lower()
    if mode != "delete":
        raise _unavailable()
    connection.execute("PRAGMA synchronous = FULL")


def _create_schema(connection: sqlite3.Connection) -> None:
    connection.execute("CREATE TABLE real_asset_delivery_schema_meta (schema_id TEXT PRIMARY KEY, schema_version INTEGER NOT NULL)")
    connection.execute(
        "CREATE TABLE real_asset_delivery_bindings (delivery_identity TEXT PRIMARY KEY, attempt_id TEXT NOT NULL UNIQUE, "
        "canonical_result_identity TEXT NOT NULL, logical_output_id TEXT NOT NULL, asset_sha256 TEXT NOT NULL, "
        "binding_json TEXT NOT NULL, binding_digest TEXT NOT NULL, phase TEXT NOT NULL, sequence INTEGER NOT NULL, "
        "terminal_code TEXT, last_event_digest TEXT NOT NULL, UNIQUE (canonical_result_identity, logical_output_id, asset_sha256))"
    )
    connection.execute(
        "CREATE TABLE real_asset_delivery_events (delivery_identity TEXT NOT NULL, sequence INTEGER NOT NULL, event_type TEXT NOT NULL, "
        "payload_json TEXT NOT NULL, payload_digest TEXT NOT NULL, previous_event_digest TEXT NOT NULL, event_digest TEXT NOT NULL, "
        "PRIMARY KEY (delivery_identity, sequence))"
    )
    connection.execute("PRAGMA user_version = 1")
    connection.execute("INSERT INTO real_asset_delivery_schema_meta (schema_id, schema_version) VALUES (?, ?)", (_SCHEMA_ID, _SCHEMA_VERSION))


def _validate_schema(connection: sqlite3.Connection) -> None:
    if int(connection.execute("PRAGMA user_version").fetchone()[0]) != _SCHEMA_VERSION:
        raise _unavailable()
    objects = connection.execute(
        "SELECT type, name, tbl_name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    expected_objects = [("table", name, name) for name in _TABLES]
    if objects != expected_objects:
        raise _unavailable()
    for table, expected_columns in _EXPECTED_COLUMNS.items():
        if [tuple(row) for row in connection.execute(f"PRAGMA table_info({table})")] != list(expected_columns):
            raise _unavailable()
        actual_indexes: dict[str, tuple[int, str, int, tuple[str, ...]]] = {}
        for row in connection.execute(f"PRAGMA index_list({table})"):
            if len(row) != 5:
                raise _unavailable()
            _, name, unique, origin, partial = row
            if type(name) is not str or name in actual_indexes:
                raise _unavailable()
            key_rows = [
                (int(item[0]), item[2])
                for item in connection.execute(f"PRAGMA index_xinfo({name!r})")
                if len(item) == 6 and int(item[5]) == 1
            ]
            if any(type(column) is not str for _, column in key_rows):
                raise _unavailable()
            actual_indexes[name] = (int(unique), str(origin), int(partial), tuple(column for _, column in sorted(key_rows)))
        if actual_indexes != _EXPECTED_INDEXES[table]:
            raise _unavailable()
    if connection.execute("SELECT schema_id, schema_version FROM real_asset_delivery_schema_meta").fetchall() != [(_SCHEMA_ID, _SCHEMA_VERSION)]:
        raise _unavailable()


def _user_objects(connection: sqlite3.Connection) -> list[tuple[object, ...]]:
    return connection.execute("SELECT type, name, tbl_name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchall()


def _rollback(connection: sqlite3.Connection | None) -> None:
    if connection is not None:
        try:
            connection.rollback()
        except sqlite3.Error:
            pass
