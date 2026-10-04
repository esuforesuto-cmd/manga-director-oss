"""Private R18 trusted LocalFile composition construction.

This module only authenticates construction of the R18 authority.  It neither
replays delivery data nor owns workflow, provider, or application authority.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

from manga_director.production.future_real_delivery_i02_real_asset_delivery_journal import (
    PrivateRealAssetDeliveryJournal,
)
from manga_director.production.next_generation_local_durable_asset_owner import (
    LocalDurableAssetOwner,
)
from manga_director.repositories.local_file import LocalFileRepository

if TYPE_CHECKING:
    from manga_director.production.future_real_delivery_binding_authority import (
        RealDeliveryBindingAuthorityV1,
    )


_NORMAL_ROOT_LOCKS: dict[Path, threading.RLock] = {}
_NORMAL_ROOT_LOCKS_GUARD = threading.Lock()
_GRANT_MARKER = object()


def _rejected() -> ValueError:
    return ValueError("AUTHORITY_REJECTED")


class _R18ConstructionCapabilityV1:
    """Opaque process-local token; copying or serialization is never authority."""

    __slots__ = ("_factory", "_nonce")

    def __init__(self, factory: object, nonce: object) -> None:
        self._factory = factory
        self._nonce = nonce

    def __reduce__(self) -> NoReturn:
        raise TypeError("R18 construction capabilities are not serializable")

    def __copy__(self) -> NoReturn:
        raise TypeError("R18 construction capabilities are not copyable")

    def __deepcopy__(self, memo: object) -> NoReturn:
        del memo
        raise TypeError("R18 construction capabilities are not copyable")


class _R18ConstructionGrantV1:
    """Opaque correlation object; factory registry membership is its only authority."""

    __slots__ = ()

    def __init__(self, *args: object) -> None:
        del args
        raise _rejected()

    def __reduce__(self) -> NoReturn:
        raise TypeError("R18 construction grants are not serializable")

    def __copy__(self) -> NoReturn:
        raise TypeError("R18 construction grants are not copyable")

    def __deepcopy__(self, memo: object) -> NoReturn:
        del memo
        raise TypeError("R18 construction grants are not copyable")


class _R18LockHeldInvocationV1:
    """Opaque, one-use correlation object for one live canonical root lock."""

    __slots__ = ()

    def __init__(self, *args: object) -> None:
        del args
        raise _rejected()

    def __reduce__(self) -> NoReturn:
        raise TypeError("R18 lock-held invocations are not serializable")

    def __copy__(self) -> NoReturn:
        raise TypeError("R18 lock-held invocations are not copyable")

    def __deepcopy__(self, memo: object) -> NoReturn:
        del memo
        raise TypeError("R18 lock-held invocations are not copyable")


@dataclass(frozen=True, slots=True)
class _R18CompositionV1:
    """Private exact tuple returned only by the factory that constructed it."""

    repository: LocalFileRepository
    owner: LocalDurableAssetOwner
    journal: PrivateRealAssetDeliveryJournal
    capability: _R18ConstructionCapabilityV1


class PrivateR18CompositionFactoryV1:
    """Construct one repository/owner/journal tuple and issue its one-shot token."""

    __slots__ = ("_issued", "_issued_grants", "_active_lock_invocations", "_lock", "_nonce")

    def __init__(self) -> None:
        self._issued: dict[object, tuple[LocalFileRepository, LocalDurableAssetOwner, PrivateRealAssetDeliveryJournal]] = {}
        self._issued_grants: dict[
            _R18ConstructionGrantV1,
            tuple[LocalFileRepository, LocalDurableAssetOwner, PrivateRealAssetDeliveryJournal, Path, bool],
        ] = {}
        self._active_lock_invocations: dict[
            _R18LockHeldInvocationV1,
            tuple[_R18ConstructionGrantV1, Path, threading.RLock],
        ] = {}
        self._lock = threading.RLock()
        self._nonce = object()

    def create(self, repository_root: Path) -> _R18CompositionV1:
        """Create the complete private tuple; callers never register a tuple."""

        if not isinstance(repository_root, Path) or not repository_root.is_absolute():
            raise _rejected()
        repository = LocalFileRepository(repository_root)
        return self._issue_composition_for_repository_v1(repository)

    def _create_for_existing_repository_v1(self, repository: object) -> _R18CompositionV1:
        """Issue one R18 tuple for the exact repository held by private composition.

        This is the R31 Model A inlet.  It deliberately accepts neither a root
        nor any value that could be used to reconstruct an equivalent driver.
        The later composition registry, not this factory, decides whether this
        exact instance is the canonical Coordinator repository.
        """

        if type(repository) is not LocalFileRepository:
            raise _rejected()
        return self._issue_composition_for_repository_v1(repository)

    def _issue_composition_for_repository_v1(
        self, repository: LocalFileRepository
    ) -> _R18CompositionV1:
        """Derive the fixed R18 children from one exact LocalFile driver."""

        normal_root = repository._next_generation_normal_execution_owner_root()
        owner = LocalDurableAssetOwner(normal_root / "assets")
        journal = PrivateRealAssetDeliveryJournal(owner)
        token_nonce = object()
        capability = _R18ConstructionCapabilityV1(self._nonce, token_nonce)
        with self._lock:
            self._issued[token_nonce] = (repository, owner, journal)
        return _R18CompositionV1(repository, owner, journal, capability)

    def _consume_exact_v1(self, composition: _R18CompositionV1) -> _R18ConstructionGrantV1:
        """Atomically tombstone a valid token before fallible authority creation."""

        if type(composition) is not _R18CompositionV1:
            raise _rejected()
        capability = composition.capability
        if type(capability) is not _R18ConstructionCapabilityV1 or capability._factory is not self._nonce:
            raise _rejected()
        with self._lock:
            expected = self._issued.get(capability._nonce)
            if expected is None:
                raise _rejected()
            if not (
                expected[0] is composition.repository
                and expected[1] is composition.owner
                and expected[2] is composition.journal
            ):
                raise _rejected()
            del self._issued[capability._nonce]
            normal_root = expected[0]._next_generation_normal_execution_owner_root()
            grant = object.__new__(_R18ConstructionGrantV1)
            self._issued_grants[grant] = (*expected, normal_root, False)
            return grant

    def _normal_root_for_issued_grant_v1(self, grant: object) -> Path:
        """Read the factory-owned lock key without granting construction authority."""

        if type(grant) is not _R18ConstructionGrantV1:
            raise _rejected()
        with self._lock:
            issued = self._issued_grants.get(grant)
            if issued is None:
                raise _rejected()
            return issued[3]

    def _active_lock_invocation_v1(
        self,
        grant: object,
        normal_root: object,
        root_lock: object,
    ) -> _R18LockHeldInvocationV1:
        """Issue one private handoff object only while its exact root lock is held."""

        if (
            type(grant) is not _R18ConstructionGrantV1
            or not isinstance(normal_root, Path)
            or not _root_lock_is_held_v1(root_lock)
        ):
            raise _rejected()
        with self._lock:
            issued = self._issued_grants.get(grant)
            if (
                issued is None
                or issued[3] is not normal_root
                or root_lock is not _normal_root_lock_v1(normal_root)
            ):
                raise _rejected()
            invocation = object.__new__(_R18LockHeldInvocationV1)
            self._active_lock_invocations[invocation] = (grant, normal_root, root_lock)
            return invocation

    def _require_active_lock_invocation_v1(
        self, grant: object, invocation: object
    ) -> tuple[LocalFileRepository, LocalDurableAssetOwner, PrivateRealAssetDeliveryJournal, Path, bool]:
        """Fail closed unless a live invocation still holds the exact canonical lock."""

        if (
            type(grant) is not _R18ConstructionGrantV1
            or type(invocation) is not _R18LockHeldInvocationV1
        ):
            raise _rejected()
        exact_grant = grant
        exact_invocation = invocation
        with self._lock:
            handoff = self._active_lock_invocations.get(exact_invocation)
            issued = self._issued_grants.get(exact_grant)
            if handoff is None or issued is None:
                raise _rejected()
            handoff_grant, normal_root, root_lock = handoff
            if (
                handoff_grant is not exact_grant
                or issued[3] is not normal_root
                or root_lock is not _normal_root_lock_v1(normal_root)
                or not _root_lock_is_held_v1(root_lock)
            ):
                raise _rejected()
            return issued

    def _arm_issued_grant_under_root_lock_v1(
        self, grant: object, invocation: object | None = None
    ) -> None:
        """Permit exactly one final construction only from the canonical locked path."""

        self._require_active_lock_invocation_v1(grant, invocation)
        if type(grant) is not _R18ConstructionGrantV1:
            raise _rejected()
        exact_grant = grant
        with self._lock:
            issued = self._issued_grants.get(exact_grant)
            if issued is None or issued[4]:
                raise _rejected()
            self._issued_grants[exact_grant] = (*issued[:4], True)

    def _consume_issued_grant_v1(
        self, grant: object, invocation: object | None = None
    ) -> tuple[LocalFileRepository, LocalDurableAssetOwner, PrivateRealAssetDeliveryJournal]:
        """Consume only the exact live factory-owned grant after canonical locking."""

        self._require_active_lock_invocation_v1(grant, invocation)
        if type(grant) is not _R18ConstructionGrantV1:
            raise _rejected()
        exact_grant = grant
        with self._lock:
            issued = self._issued_grants.pop(exact_grant, None)
            if issued is None or not issued[4]:
                raise _rejected()
            return issued[:3]

    def _invalidate_lock_invocation_v1(self, invocation: object) -> None:
        """Invalidate the private handoff on every return or exception path."""

        if type(invocation) is not _R18LockHeldInvocationV1:
            raise _rejected()
        with self._lock:
            if self._active_lock_invocations.pop(invocation, None) is None:
                raise _rejected()

    def construct_authority(self, composition: _R18CompositionV1) -> RealDeliveryBindingAuthorityV1:
        """Consume a valid token before entering fallible R18 construction."""

        grant = self._consume_exact_v1(composition)
        from manga_director.production.future_real_delivery_binding_authority import (
            _construct_from_factory_issued_grant_v1,
        )

        normal_root = self._normal_root_for_issued_grant_v1(grant)
        root_lock = _normal_root_lock_v1(normal_root)
        with root_lock:
            invocation = self._active_lock_invocation_v1(grant, normal_root, root_lock)
            try:
                self._arm_issued_grant_under_root_lock_v1(grant, invocation)
                return _construct_from_factory_issued_grant_v1(self, grant, invocation)
            finally:
                self._invalidate_lock_invocation_v1(invocation)


def _normal_root_lock_v1(normal_root: Path) -> threading.RLock:
    """Return the private process-local construction lock for one canonical root."""

    with _NORMAL_ROOT_LOCKS_GUARD:
        return _NORMAL_ROOT_LOCKS.setdefault(normal_root, threading.RLock())


def _root_lock_is_held_v1(root_lock: object) -> bool:
    """Use the CPython RLock ownership probe; unknown implementations fail closed."""

    probe = getattr(root_lock, "_is_owned", None)
    return callable(probe) and probe() is True
