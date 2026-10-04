"""Private RFC-01 I02a predecessor protocol.

This module deliberately owns only volatile peer/capability/bootstrap state.
It imports neither I02, I03 nor I04 and has no provider, filesystem, workflow,
or public-export authority.
"""

from __future__ import annotations

import hmac
import secrets
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Final, TypeVar

_UNAVAILABLE: Final = "RFC-01 I02a protocol authority is unavailable"


def _unavailable() -> ValueError:
    return ValueError(_UNAVAILABLE)


class _BootstrapState(StrEnum):
    UNISSUED = "UNISSUED"
    LIVE = "LIVE"
    CONSUMED = "CONSUMED"
    REGISTERED = "REGISTERED"
    BOOTSTRAP_FAILED = "BOOTSTRAP_FAILED"


class _JournalCompletionCallbackResultV1(StrEnum):
    COMMITTED = "COMMITTED"
    ALREADY_COMMITTED_EXACT = "ALREADY_COMMITTED_EXACT"
    TERMINAL_NO_COMMIT = "TERMINAL_NO_COMMIT"
    NOT_COMMITTED = "NOT_COMMITTED"
    CORRUPT = "CORRUPT"
    UNKNOWN_OUTCOME = "UNKNOWN_OUTCOME"


class _CompletionLifecycleV1(StrEnum):
    """The protocol-owned R16 completion lifecycle."""

    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    FINALIZED = "FINALIZED"


class _SealedAuthority:
    """Common non-copyable/non-serializable volatile authority base."""

    __slots__ = ("_sealed", "__weakref__")
    _sealed: bool

    def __init__(self) -> None:
        raise TypeError(_UNAVAILABLE)

    def __init_subclass__(cls, **kwargs: object) -> None:
        if cls.__name__ not in {
            "_ProductionJournalBootstrapChannelV1",
            "_ProtocolTestPairAuthorityV1",
            "_JournalPeerBindingV1",
            "_RegisteredAssetReplayAttestationV1",
            "_RegisteredOwnerVerificationRequestV1",
            "_RegisteredOwnerVerificationCompletionCapabilityV1",
        }:
            raise TypeError(_UNAVAILABLE)
        super().__init_subclass__(**kwargs)

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


class _RealDeliveryJournalPeerV1:
    """Nominal predecessor-owned journal base; derivation alone is inert."""

    __slots__ = ()

    def __init_subclass__(cls, **kwargs: object) -> None:
        if cls.__bases__ != (_RealDeliveryJournalPeerV1,):
            raise TypeError(_UNAVAILABLE)
        super().__init_subclass__(**kwargs)


@dataclass(frozen=True, slots=True)
class _RegisteredAssetReplayFactsV1:
    delivery_identity: str
    attempt_id: str
    binding_digest: str
    provider_reference: str
    canonical_result_identity: str
    logical_output_id: str
    asset_id: str
    asset_registration_digest: str
    sha256: str
    expected_byte_length: int
    media_type: str
    provenance_assurance: str
    phase: str
    sequence: int
    last_event_digest: str


@dataclass(frozen=True, slots=True)
class _VerifiedOwnerAssetFactsV1:
    assets_root_identity: tuple[str, int, int]
    final_file_identity: tuple[str, int, int, int]
    verified_sha256: str
    verified_byte_length: int
    verified_media_type: str
    owner_attempt_id: str = ""
    owner_provider_reference: str = ""
    owner_digest: str = ""
    owner_storage_name: str = ""
    _release_leases: Callable[[], None] | None = field(default=None, repr=False, compare=False)


@dataclass(slots=True)
class _Record:
    object: object
    nonce: bytes


class _ProductionJournalClassAlreadyRegisteredV1(Exception):
    """Private non-authority observation used only by later I04 wiring."""


class _ProductionJournalBootstrapChannelV1(_SealedAuthority):
    __slots__ = ("_state", "_nonce", "_sealed")
    _state: _ProtocolStateV1
    _nonce: bytes

    def _register_production_journal_class_once_v1(
        self, journal_class: type[_RealDeliveryJournalPeerV1]
    ) -> None:
        self._state.register_production_class(self, journal_class)


class _ProtocolTestPairAuthorityV1(_SealedAuthority):
    __slots__ = ("_state", "_nonce", "_sealed")
    _state: _ProtocolStateV1
    _nonce: bytes


class _JournalPeerBindingV1(_SealedAuthority):
    __slots__ = ("_state", "_nonce", "_pair_nonce", "_sealed")
    _state: _ProtocolStateV1
    _nonce: bytes
    _pair_nonce: bytes


class _RegisteredAssetReplayAttestationV1(_SealedAuthority):
    __slots__ = ("_state", "_nonce", "_pair_nonce", "_facts", "_sealed")
    _state: _ProtocolStateV1
    _nonce: bytes
    _pair_nonce: bytes
    _facts: _RegisteredAssetReplayFactsV1


class _RegisteredOwnerVerificationRequestV1(_SealedAuthority):
    __slots__ = ("_state", "_nonce", "_pair_nonce", "_facts", "_sealed")
    _state: _ProtocolStateV1
    _nonce: bytes
    _pair_nonce: bytes
    _facts: _RegisteredAssetReplayFactsV1

    @property
    def facts(self) -> _RegisteredAssetReplayFactsV1:
        return self._facts


class _RegisteredOwnerVerificationCompletionCapabilityV1(_SealedAuthority):
    __slots__ = ("_state", "_nonce", "_pair_nonce", "_request", "_verified", "_sealed")
    _state: _ProtocolStateV1
    _nonce: bytes
    _pair_nonce: bytes
    _request: _RegisteredOwnerVerificationRequestV1
    _verified: _VerifiedOwnerAssetFactsV1


class _ActiveCompletionDispatchV1:
    """Ephemeral callback input minted only for one ACTIVE completion.

    This is deliberately not an authority capability: authenticity is decided
    only by the protocol state map while the outer protocol operation is active.
    """

    __slots__ = ("_state", "_capability", "_nonce", "_sealed")
    _state: _ProtocolStateV1
    _capability: _RegisteredOwnerVerificationCompletionCapabilityV1
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


@dataclass(slots=True)
class _CompletionLifecycleRecordV1:
    capability: _RegisteredOwnerVerificationCompletionCapabilityV1
    nonce: bytes
    verifier: _RegisteredOwnerVerificationVerifierPeerV1
    journal_peer: _RegisteredOwnerVerificationJournalPeerV1
    pair_nonce: bytes
    request: _RegisteredOwnerVerificationRequestV1
    delivery_identity: str
    dispatch_nonce: bytes
    state: _CompletionLifecycleV1


class _RegisteredOwnerVerificationJournalPeerV1:
    __slots__ = ("_state", "_journal", "_pair_nonce", "_bound", "_closed")

    def __init__(self, state: _ProtocolStateV1, journal: _RealDeliveryJournalPeerV1, pair_nonce: bytes) -> None:
        self._state = state
        self._journal = journal
        self._pair_nonce = pair_nonce
        self._bound = False
        self._closed = False

    def _issue_registered_owner_verification_request_v1(self) -> _RegisteredOwnerVerificationRequestV1:
        return self._state._issue_request(self)

    def _assert_active_completion_dispatch_v1(
        self, dispatch: _ActiveCompletionDispatchV1
    ) -> tuple[_RegisteredAssetReplayFactsV1, _VerifiedOwnerAssetFactsV1]:
        """Read only the exact facts for a currently active callback."""

        return self._state._assert_active_completion_dispatch(self, dispatch)


class _RegisteredOwnerVerificationVerifierPeerV1:
    __slots__ = ("_state", "_journal_peer", "_pair_nonce", "_closed")

    def __init__(self, state: _ProtocolStateV1, journal_peer: _RegisteredOwnerVerificationJournalPeerV1, pair_nonce: bytes) -> None:
        self._state = state
        self._journal_peer = journal_peer
        self._pair_nonce = pair_nonce
        self._closed = False

    def _consume_request_and_issue_completion_v1(
        self,
        request: _RegisteredOwnerVerificationRequestV1,
        verified: _VerifiedOwnerAssetFactsV1,
    ) -> _RegisteredOwnerVerificationCompletionCapabilityV1:
        return self._state._issue_completion(self, request, verified)

    def _validate_registered_owner_verification_request_v1(
        self, request: _RegisteredOwnerVerificationRequestV1
    ) -> _RegisteredAssetReplayFactsV1:
        """Authenticate an unconsumed, exact-pair request without consuming it."""

        return self._state._validate_request(self, request)

    def _consume_completion_and_call_journal_v1(
        self,
        capability: _RegisteredOwnerVerificationCompletionCapabilityV1,
    ) -> _JournalCompletionCallbackResultV1:
        return self._state._consume_completion(self, capability)


_AuthorityT = TypeVar("_AuthorityT", bound=_SealedAuthority)


class _ProtocolStateV1:
    """One isolated volatile authority universe; production owns one singleton."""

    __slots__ = (
        "_lock", "_bootstrap", "_bootstrap_state", "_registered_class", "_records",
        "_tombstones", "_bound_journals", "_pairs", "_requests", "_completions",
        "_completion_lifecycle_records", "_active_completion_dispatches", "_test_class", "_test_authority",
    )

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._bootstrap: _ProductionJournalBootstrapChannelV1 | None = None
        self._bootstrap_state = _BootstrapState.UNISSUED
        self._registered_class: type[_RealDeliveryJournalPeerV1] | None = None
        self._records: dict[int, _Record] = {}
        self._tombstones: set[object] = set()
        self._bound_journals: set[int] = set()
        self._pairs: dict[int, tuple[_RegisteredOwnerVerificationJournalPeerV1, _RegisteredOwnerVerificationVerifierPeerV1]] = {}
        self._requests: dict[int, _RegisteredOwnerVerificationRequestV1] = {}
        self._completions: dict[int, _RegisteredOwnerVerificationCompletionCapabilityV1] = {}
        self._completion_lifecycle_records: dict[int, _CompletionLifecycleRecordV1] = {}
        self._active_completion_dispatches: dict[int, _ActiveCompletionDispatchV1] = {}
        self._test_class: type[_RealDeliveryJournalPeerV1] | None = None
        self._test_authority: _ProtocolTestPairAuthorityV1 | None = None

    def take_bootstrap(self) -> _ProductionJournalBootstrapChannelV1:
        with self._lock:
            if self._bootstrap_state is _BootstrapState.REGISTERED:
                raise _ProductionJournalClassAlreadyRegisteredV1()
            if self._bootstrap_state is not _BootstrapState.UNISSUED:
                raise _unavailable()
            channel = self._mint(_ProductionJournalBootstrapChannelV1)
            self._bootstrap = channel
            self._bootstrap_state = _BootstrapState.LIVE
            return channel

    def register_production_class(
        self, channel: _ProductionJournalBootstrapChannelV1, candidate: type[_RealDeliveryJournalPeerV1]
    ) -> None:
        with self._lock:
            if not self._consume(channel, _ProductionJournalBootstrapChannelV1):
                raise _unavailable()
            if self._bootstrap_state is not _BootstrapState.LIVE:
                raise _unavailable()
            self._bootstrap_state = _BootstrapState.CONSUMED
            try:
                if self._registered_class is not None or type(candidate) is not type or candidate.__base__ is not _RealDeliveryJournalPeerV1:
                    raise _unavailable()
                self._registered_class = candidate
                self._bootstrap_state = _BootstrapState.REGISTERED
            except Exception as error:
                self._bootstrap_state = _BootstrapState.BOOTSTRAP_FAILED
                if isinstance(error, ValueError):
                    raise
                raise _unavailable() from error

    def issue_test_authority(self, journal_class: type[_RealDeliveryJournalPeerV1]) -> _ProtocolTestPairAuthorityV1:
        with self._lock:
            if self._test_authority is not None or type(journal_class) is not type or journal_class.__base__ is not _RealDeliveryJournalPeerV1:
                raise _unavailable()
            authority = self._mint(_ProtocolTestPairAuthorityV1)
            self._test_class = journal_class
            self._test_authority = authority
            return authority

    def create_pair(
        self, journal: _RealDeliveryJournalPeerV1, test_authority: _ProtocolTestPairAuthorityV1 | None = None
    ) -> tuple[_RegisteredOwnerVerificationJournalPeerV1, _RegisteredOwnerVerificationVerifierPeerV1]:
        with self._lock:
            if type(journal) is self._registered_class:
                if test_authority is not None:
                    raise _unavailable()
            elif type(journal) is self._test_class:
                if test_authority is None or not self._consume(test_authority, _ProtocolTestPairAuthorityV1):
                    raise _unavailable()
            else:
                raise _unavailable()
            if id(journal) in self._bound_journals:
                raise _unavailable()
            pair_nonce = secrets.token_bytes(32)
            journal_peer = _RegisteredOwnerVerificationJournalPeerV1(self, journal, pair_nonce)
            verifier_peer = _RegisteredOwnerVerificationVerifierPeerV1(self, journal_peer, pair_nonce)
            binding = self._mint(_JournalPeerBindingV1, _pair_nonce=pair_nonce)
            try:
                bind = getattr(journal, "_bind_registered_owner_verification_peer_v1", None)
                if not callable(bind):
                    raise _unavailable()
                bind(journal_peer, binding)
                if not self._consume(binding, _JournalPeerBindingV1):
                    raise _unavailable()
            except Exception as error:
                journal_peer._closed = True
                verifier_peer._closed = True
                if isinstance(error, ValueError):
                    raise
                raise _unavailable() from error
            journal_peer._bound = True
            self._bound_journals.add(id(journal))
            self._pairs[id(journal_peer)] = (journal_peer, verifier_peer)
            return journal_peer, verifier_peer

    def _issue_request(self, peer: _RegisteredOwnerVerificationJournalPeerV1) -> _RegisteredOwnerVerificationRequestV1:
        with self._lock:
            pair = self._pairs.get(id(peer))
            if pair is None or pair[0] is not peer or peer._closed or not peer._bound:
                raise _unavailable()
            replay = getattr(peer._journal, "_replay_registered_asset_for_owner_verification_v1", None)
            if not callable(replay):
                raise _unavailable()
            try:
                facts = replay()
            except Exception as error:
                raise _unavailable() from error
            if type(facts) is not _RegisteredAssetReplayFactsV1 or facts.phase != "ASSET_REGISTERED":
                raise _unavailable()
            if (
                any(
                    item._pair_nonce == peer._pair_nonce
                    and item._facts.delivery_identity == facts.delivery_identity
                    for item in self._requests.values()
                )
                or any(
                    item._pair_nonce == peer._pair_nonce
                    and item._request._facts.delivery_identity == facts.delivery_identity
                    for item in self._completions.values()
                )
            ):
                raise _unavailable()
            attestation = self._mint(
                _RegisteredAssetReplayAttestationV1, _pair_nonce=peer._pair_nonce, _facts=facts
            )
            if not self._consume(attestation, _RegisteredAssetReplayAttestationV1):
                raise _unavailable()
            request = self._mint(
                _RegisteredOwnerVerificationRequestV1, _pair_nonce=peer._pair_nonce, _facts=facts
            )
            self._requests[id(request)] = request
            return request

    def _issue_completion(
        self, verifier: _RegisteredOwnerVerificationVerifierPeerV1, request: _RegisteredOwnerVerificationRequestV1,
        verified: _VerifiedOwnerAssetFactsV1,
    ) -> _RegisteredOwnerVerificationCompletionCapabilityV1:
        with self._lock:
            pair = self._pairs.get(id(verifier._journal_peer))
            if pair is None or pair[1] is not verifier or verifier._closed or type(verified) is not _VerifiedOwnerAssetFactsV1:
                raise _unavailable()
            if not self._consume(request, _RegisteredOwnerVerificationRequestV1) or request._pair_nonce != verifier._pair_nonce:
                raise _unavailable()
            self._requests.pop(id(request), None)
            capability = self._mint(
                _RegisteredOwnerVerificationCompletionCapabilityV1, _pair_nonce=verifier._pair_nonce
            )
            object.__setattr__(capability, "_request", request)
            object.__setattr__(capability, "_verified", verified)
            self._completions[id(capability)] = capability
            record = self._records.get(id(capability))
            if record is None:
                raise _unavailable()
            self._completion_lifecycle_records[id(capability)] = _CompletionLifecycleRecordV1(
                capability=capability,
                nonce=record.nonce,
                verifier=verifier,
                journal_peer=verifier._journal_peer,
                pair_nonce=verifier._pair_nonce,
                request=request,
                delivery_identity=request._facts.delivery_identity,
                dispatch_nonce=secrets.token_bytes(32),
                state=_CompletionLifecycleV1.PENDING,
            )
            return capability

    def _validate_request(
        self,
        verifier: _RegisteredOwnerVerificationVerifierPeerV1,
        request: _RegisteredOwnerVerificationRequestV1,
    ) -> _RegisteredAssetReplayFactsV1:
        """Return only live request facts; all other inputs fail closed."""

        with self._lock:
            pair = self._pairs.get(id(verifier._journal_peer))
            if (
                pair is None
                or pair[1] is not verifier
                or verifier._closed
                or type(request) is not _RegisteredOwnerVerificationRequestV1
                or request._pair_nonce != verifier._pair_nonce
            ):
                raise _unavailable()
            record = self._records.get(id(request))
            if (
                record is None
                or record.object is not request
                or request in self._tombstones
                or type(request._nonce) is not bytes
                or not hmac.compare_digest(record.nonce, request._nonce)
                or self._requests.get(id(request)) is not request
            ):
                raise _unavailable()
            return request._facts

    def _consume_completion(
        self, verifier: _RegisteredOwnerVerificationVerifierPeerV1,
        capability: _RegisteredOwnerVerificationCompletionCapabilityV1,
    ) -> _JournalCompletionCallbackResultV1:
        dispatch: _ActiveCompletionDispatchV1
        with self._lock:
            pair = self._pairs.get(id(verifier._journal_peer))
            record = self._completion_lifecycle_records.get(id(capability))
            if (
                pair is None
                or pair[1] is not verifier
                or type(capability) is not _RegisteredOwnerVerificationCompletionCapabilityV1
                or record is None
                or record.capability is not capability
                or record.verifier is not verifier
                or record.journal_peer is not verifier._journal_peer
                or record.pair_nonce != verifier._pair_nonce
                or record.request is not capability._request
                or record.delivery_identity != capability._request._facts.delivery_identity
                or record.state is not _CompletionLifecycleV1.PENDING
                or type(capability._nonce) is not bytes
                or not hmac.compare_digest(record.nonce, capability._nonce)
            ):
                raise _unavailable()
            callback = getattr(
                verifier._journal_peer._journal,
                "_complete_registered_asset_from_verified_capability_v1",
                None,
            )
            if not callable(callback) or not self._consume(capability, _RegisteredOwnerVerificationCompletionCapabilityV1):
                raise _unavailable()
            self._completions.pop(id(capability), None)
            record.state = _CompletionLifecycleV1.ACTIVE
            dispatch = object.__new__(_ActiveCompletionDispatchV1)
            object.__setattr__(dispatch, "_state", self)
            object.__setattr__(dispatch, "_capability", capability)
            object.__setattr__(dispatch, "_nonce", record.dispatch_nonce)
            object.__setattr__(dispatch, "_sealed", True)
            self._active_completion_dispatches[id(dispatch)] = dispatch
        result = _JournalCompletionCallbackResultV1.NOT_COMMITTED
        try:
            callback_result = callback(dispatch)
            if type(callback_result) is _JournalCompletionCallbackResultV1:
                result = callback_result
        except Exception:
            result = self._callback_exception_result(verifier._journal_peer._journal, capability)
        finally:
            with self._lock:
                active = self._active_completion_dispatches.get(id(dispatch))
                current = self._completion_lifecycle_records.get(id(capability))
                if active is dispatch:
                    del self._active_completion_dispatches[id(dispatch)]
                if current is record and current.state is _CompletionLifecycleV1.ACTIVE:
                    current.state = _CompletionLifecycleV1.FINALIZED
                    del self._completion_lifecycle_records[id(capability)]
            try:
                _release_verified_leases(capability._verified)
            except Exception:
                result = _JournalCompletionCallbackResultV1.UNKNOWN_OUTCOME
        return result

    @staticmethod
    def _callback_exception_result(
        journal: _RealDeliveryJournalPeerV1,
        capability: _RegisteredOwnerVerificationCompletionCapabilityV1,
    ) -> _JournalCompletionCallbackResultV1:
        """Classify acknowledgement loss from existing durable replay only."""

        replay = getattr(journal, "_replay_v1", None)
        if not callable(replay):
            return _JournalCompletionCallbackResultV1.NOT_COMMITTED
        try:
            durable = replay(capability._request._facts.delivery_identity)
        except Exception:
            return _JournalCompletionCallbackResultV1.NOT_COMMITTED
        status = getattr(durable, "status", None)
        if getattr(status, "value", None) == "DELIVERY_COMPLETED":
            return _JournalCompletionCallbackResultV1.UNKNOWN_OUTCOME
        return _JournalCompletionCallbackResultV1.NOT_COMMITTED

    def _assert_active_completion_dispatch(
        self,
        peer: _RegisteredOwnerVerificationJournalPeerV1,
        dispatch: _ActiveCompletionDispatchV1,
    ) -> tuple[_RegisteredAssetReplayFactsV1, _VerifiedOwnerAssetFactsV1]:
        with self._lock:
            if type(dispatch) is not _ActiveCompletionDispatchV1:
                raise _unavailable()
            actual = self._active_completion_dispatches.get(id(dispatch))
            capability = dispatch._capability
            record = self._completion_lifecycle_records.get(id(capability))
            if (
                actual is not dispatch
                or dispatch._state is not self
                or record is None
                or record.capability is not capability
                or record.journal_peer is not peer
                or record.pair_nonce != peer._pair_nonce
                or record.request is not capability._request
                or record.delivery_identity != capability._request._facts.delivery_identity
                or record.state is not _CompletionLifecycleV1.ACTIVE
                or type(dispatch._nonce) is not bytes
                or not hmac.compare_digest(record.dispatch_nonce, dispatch._nonce)
            ):
                raise _unavailable()
            return capability._request._facts, capability._verified
    def _mint(self, authority_type: type[_AuthorityT], **values: object) -> _AuthorityT:
        authority = object.__new__(authority_type)
        nonce = secrets.token_bytes(32)
        object.__setattr__(authority, "_state", self)
        object.__setattr__(authority, "_nonce", nonce)
        for name, value in values.items():
            object.__setattr__(authority, name, value)
        object.__setattr__(authority, "_sealed", True)
        self._records[id(authority)] = _Record(authority, nonce)
        return authority

    def _consume(self, authority: object, expected: type[_SealedAuthority]) -> bool:
        if type(authority) is not expected:
            return False
        record = self._records.get(id(authority))
        if record is None or record.object is not authority or authority in self._tombstones:
            return False
        nonce = getattr(authority, "_nonce", None)
        if type(nonce) is not bytes or not hmac.compare_digest(record.nonce, nonce):
            return False
        self._tombstones.add(authority)
        del self._records[id(authority)]
        return True


def _release_verified_leases(verified: _VerifiedOwnerAssetFactsV1) -> None:
    release = verified._release_leases
    if release is not None:
        release()


_PRODUCTION_STATE = _ProtocolStateV1()


def _take_production_journal_bootstrap_channel_once_v1() -> _ProductionJournalBootstrapChannelV1:
    """Transfer the sole process-lifetime production channel to trusted I04 wiring."""

    return _PRODUCTION_STATE.take_bootstrap()


def _create_registered_owner_verification_pair_v1(
    journal: _RealDeliveryJournalPeerV1,
    test_authority: _ProtocolTestPairAuthorityV1 | None = None,
) -> tuple[_RegisteredOwnerVerificationJournalPeerV1, _RegisteredOwnerVerificationVerifierPeerV1]:
    return _PRODUCTION_STATE.create_pair(journal, test_authority)


def _create_isolated_test_protocol_state_v1() -> _ProtocolStateV1:
    """Private test fixture seam; it never observes or resets production state."""

    return _ProtocolStateV1()
