"""Workflow-private R26 prerequisite composition.

This module is deliberately unreachable from public, CLI, MCP, legacy, and
fake-only composition.  It establishes only a process-local owner/root and
the durable R26 marker prerequisite; it has no proof, CAS, StateMachine,
provider, Receipt, or Ledger-finalization authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Event, RLock
from typing import Literal

from manga_director.domain.state_machine import StateMachine
from manga_director.events.bus import MemoryEventBus
from manga_director.production.future_real_delivery_r26_reconciliation import (
    _R26_PROOF_FACTORY_ISSUER,
    _construct_r26_reconciliation_proof_factory_v1,
)
from manga_director.production.next_generation_workflow_application_ledger import (
    _R26_PREPARATION_ISSUER,
    LocalWorkflowApplicationLedgerStore,
    WorkflowApplicationLedgerBindingDTO,
    _issue_r26_protocol_v1_observation_capability,
    _issue_r26_protocol_v1_preparation_capability,
    _R26AuthenticatedProtocolObservationV1,
    _R26ProtocolObservationV2,
    _R26ProtocolPreparationResultV1,
    _register_r26_protocol_v1_ready_root,
)
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.workflow.durable_execution import LocalFileDurablePageStore
from manga_director.workflow.localfile_external_generated_application import (
    _build_private_real_delivery_canonical_external_generation_composition_from_owned_repository_v1,
)

_LAUNCH_ISSUER = object()
_BOOTSTRAP_FACTORY = object()
_REGISTRY_LOCK = RLock()
_ROOTS_BY_REPOSITORY: dict[int, _RootRegistryEntry] = {}
_REPOSITORY_BY_DURABLE_ROOT: dict[str, LocalFileRepository] = {}


class _PrivateAuthorityRejectedError(ValueError):
    """An explicit private authority validation rejection."""


def _authority_rejected() -> _PrivateAuthorityRejectedError:
    return _PrivateAuthorityRejectedError("AUTHORITY_REJECTED")


def _construction_failed() -> ValueError:
    return ValueError("R26_ROOT_CONSTRUCTION_FAILED")


def _corrupt() -> ValueError:
    return ValueError("CORRUPT")


@dataclass(frozen=True, slots=True)
class _PrivateRealDeliveryLaunchConfigurationV1:
    """Value-only host construction input; it is never positive authority."""

    repository_root: Path


class _PrivateRealDeliveryLaunchAuthorizationV1:
    """Host-minted, process-local one-use entry authorization."""

    __slots__ = ("_configuration", "_host", "_issuer", "_used")

    _configuration: _PrivateRealDeliveryLaunchConfigurationV1
    _host: _PrivateRealDeliveryWorkflowHostV1
    _issuer: object
    _used: bool

    def __init__(self, *args: object) -> None:
        del args
        raise _authority_rejected()

    def __copy__(self) -> _PrivateRealDeliveryLaunchAuthorizationV1:
        """Return a structural copy that cannot satisfy the host registry."""

        copied = object.__new__(_PrivateRealDeliveryLaunchAuthorizationV1)
        object.__setattr__(copied, "_configuration", self._configuration)
        object.__setattr__(copied, "_host", self._host)
        object.__setattr__(copied, "_issuer", self._issuer)
        object.__setattr__(copied, "_used", self._used)
        return copied

    def __deepcopy__(self, memo: dict[int, object]) -> _PrivateRealDeliveryLaunchAuthorizationV1:
        """Keep deep-copy attempts deterministic without copying host internals."""

        del memo
        return self.__copy__()


class _PrivateRealDeliveryBootstrapAuthorizationV1:
    """Owner-issued, process-local bootstrap authority for exactly one root call."""

    __slots__ = (
        "_event_bus",
        "_factory",
        "_in_flight",
        "_issuer",
        "_owner",
        "_repository",
        "_state_machine",
        "_used",
    )

    _event_bus: MemoryEventBus
    _factory: object
    _in_flight: bool
    _issuer: _PrivateRealDeliveryCompositionOwnerV1
    _owner: _PrivateRealDeliveryCompositionOwnerV1
    _repository: LocalFileRepository
    _state_machine: StateMachine
    _used: bool

    def __init__(self, *args: object) -> None:
        del args
        raise _authority_rejected()


class _PrivateRealDeliveryCompositionEntryV1:
    """Private host-to-owner inlet; it accepts no raw authority tuple."""

    __slots__ = ()

    def __init__(self, *args: object) -> None:
        del args
        raise _authority_rejected()

    def _create_owner_from_host_authorization_v1(
        self, authorization: object, configuration: object
    ) -> _PrivateRealDeliveryCompositionOwnerV1:
        if type(authorization) is not _PrivateRealDeliveryLaunchAuthorizationV1:
            raise _authority_rejected()
        exact = authorization
        host = getattr(exact, "_host", None)
        if (
            getattr(exact, "_issuer", None) is not _LAUNCH_ISSUER
            or type(host) is not _PrivateRealDeliveryWorkflowHostV1
            or getattr(exact, "_used", None) is not False
            or getattr(exact, "_configuration", None) is not host._configuration
            or exact not in host._launch_issued
        ):
            raise _authority_rejected()
        if (
            type(configuration) is not _PrivateRealDeliveryLaunchConfigurationV1
            or configuration is not host._configuration
        ):
            raise _authority_rejected()
        root = configuration.repository_root
        if not isinstance(root, Path) or not root.is_absolute():
            raise _authority_rejected()
        object.__setattr__(exact, "_used", True)
        host._launch_issued.discard(exact)
        repository = LocalFileRepository(root)
        owner = object.__new__(_PrivateRealDeliveryCompositionOwnerV1)
        object.__setattr__(owner, "_host", exact._host)
        object.__setattr__(owner, "_repository", repository)
        object.__setattr__(owner, "_state_machine", StateMachine())
        object.__setattr__(owner, "_event_bus", MemoryEventBus())
        object.__setattr__(owner, "_bootstrap_issued", set())
        object.__setattr__(owner, "_root", None)
        return owner


class _PrivateRealDeliveryWorkflowHostV1:
    """The sole private root-of-trust for one real-delivery composition lifetime."""

    __slots__ = ("_configuration", "_launch_issued", "_lock", "_owner")

    _configuration: _PrivateRealDeliveryLaunchConfigurationV1
    _launch_issued: set[_PrivateRealDeliveryLaunchAuthorizationV1]
    _lock: RLock
    _owner: _PrivateRealDeliveryCompositionOwnerV1 | None

    def __init__(self, *args: object) -> None:
        del args
        raise _authority_rejected()

    def _issue_launch_authorization_v1(self) -> _PrivateRealDeliveryLaunchAuthorizationV1:
        authorization = object.__new__(_PrivateRealDeliveryLaunchAuthorizationV1)
        object.__setattr__(authorization, "_configuration", self._configuration)
        object.__setattr__(authorization, "_host", self)
        object.__setattr__(authorization, "_issuer", _LAUNCH_ISSUER)
        object.__setattr__(authorization, "_used", False)
        self._launch_issued.add(authorization)
        return authorization

    def _start_private_real_delivery_composition_v1(
        self,
    ) -> _PrivateR26ReconciliationCompositionRootV1:
        with self._lock:
            owner = self._owner
            if owner is None:
                authorization = self._issue_launch_authorization_v1()
                entry = object.__new__(_PrivateRealDeliveryCompositionEntryV1)
                owner = entry._create_owner_from_host_authorization_v1(
                    authorization, self._configuration
                )
                object.__setattr__(self, "_owner", owner)
        # The factory owns construction joining.  Holding the host lock here
        # would turn a concurrent waiter into an unauthorized automatic retry
        # after a failed generation.
        return owner._construct_or_reuse_root_v1()


class _PrivateRealDeliveryCompositionOwnerV1:
    """Retains the owner-created exact repository, StateMachine, and EventBus."""

    __slots__ = ("_bootstrap_issued", "_event_bus", "_host", "_repository", "_root", "_state_machine")

    _bootstrap_issued: set[_PrivateRealDeliveryBootstrapAuthorizationV1]
    _event_bus: MemoryEventBus
    _host: _PrivateRealDeliveryWorkflowHostV1
    _repository: LocalFileRepository
    _root: _PrivateR26ReconciliationCompositionRootV1 | None
    _state_machine: StateMachine

    def __init__(self, *args: object) -> None:
        del args
        raise _authority_rejected()

    def _issue_bootstrap_authorization_v1(self) -> _PrivateRealDeliveryBootstrapAuthorizationV1:
        authorization = object.__new__(_PrivateRealDeliveryBootstrapAuthorizationV1)
        object.__setattr__(authorization, "_issuer", self)
        object.__setattr__(authorization, "_owner", self)
        object.__setattr__(authorization, "_repository", self._repository)
        object.__setattr__(authorization, "_state_machine", self._state_machine)
        object.__setattr__(authorization, "_event_bus", self._event_bus)
        object.__setattr__(authorization, "_factory", _BOOTSTRAP_FACTORY)
        object.__setattr__(authorization, "_in_flight", False)
        object.__setattr__(authorization, "_used", False)
        self._bootstrap_issued.add(authorization)
        return authorization

    def _construct_or_reuse_root_v1(self) -> _PrivateR26ReconciliationCompositionRootV1:
        if self._root is not None:
            return self._root
        authorization = self._issue_bootstrap_authorization_v1()
        root = _construct_private_r26_reconciliation_root_v1(authorization)
        object.__setattr__(self, "_root", root)
        return root


@dataclass(slots=True)
class _RootRegistryEntry:
    state: Literal["CONSTRUCTING", "READY"]
    repository: LocalFileRepository
    state_machine: StateMachine
    event_bus: MemoryEventBus
    completion: Event
    root: _PrivateR26ReconciliationCompositionRootV1 | None = None
    failure: str | None = None
    joined_waiters: int = 0
    constructor_pending: bool = True


class _PrivateR26ReconciliationCompositionRootV1:
    """Authenticated ready root retaining one canonical private composition."""

    __slots__ = ("_composition", "_event_bus", "_ledger_store", "_owner", "_r26_proof_factory", "_repository", "_state_machine")

    _composition: object
    _event_bus: MemoryEventBus
    _ledger_store: LocalWorkflowApplicationLedgerStore
    _owner: _PrivateRealDeliveryCompositionOwnerV1
    _r26_proof_factory: object
    _repository: LocalFileRepository
    _state_machine: StateMachine

    def __init__(self, *args: object) -> None:
        del args
        raise _authority_rejected()

    def _prepare_r26_protocol_marker_v1(
        self, binding: object
    ) -> _R26ProtocolPreparationResultV1:
        """The only marker-1 preparation inlet; it contains no R26 proof logic."""

        if type(binding) is not WorkflowApplicationLedgerBindingDTO:
            raise _authority_rejected()
        capability = _issue_r26_protocol_v1_preparation_capability(
            self._ledger_store,
            self._repository,
            root=self,
            _issuer=_R26_PREPARATION_ISSUER,
        )
        return self._ledger_store._prepare_r26_protocol_v1_under_existing_transaction(
            binding, capability, repository=self._repository, root=self
        )

    def _observe_r26_protocol_marker_v2(
        self, binding: object
    ) -> _R26AuthenticatedProtocolObservationV1 | _R26ProtocolObservationV2:
        if type(binding) is not WorkflowApplicationLedgerBindingDTO:
            return _R26ProtocolObservationV2("AUTHORITY_REJECTED")
        capability = _issue_r26_protocol_v1_observation_capability(
            self._ledger_store,
            self._repository,
            root=self,
            _issuer=_R26_PREPARATION_ISSUER,
        )
        return self._ledger_store._observe_r26_protocol_authenticated_readonly_v1(
            binding, capability, repository=self._repository, root=self
        )


def _create_private_real_delivery_workflow_host_v1(
    repository_root: object,
) -> _PrivateRealDeliveryWorkflowHostV1:
    """Create a host from value-only configuration, never from a raw authority tuple."""

    if not isinstance(repository_root, Path) or not repository_root.is_absolute():
        raise _authority_rejected()
    host = object.__new__(_PrivateRealDeliveryWorkflowHostV1)
    object.__setattr__(
        host, "_configuration", _PrivateRealDeliveryLaunchConfigurationV1(repository_root)
    )
    object.__setattr__(host, "_lock", RLock())
    object.__setattr__(host, "_launch_issued", set())
    object.__setattr__(host, "_owner", None)
    return host


def _construct_private_r26_reconciliation_root_v1(  # noqa: C901
    authorization: object,
) -> _PrivateR26ReconciliationCompositionRootV1:
    """Validate a sealed owner authorization and atomically publish one root."""

    owner, repository, state_machine, event_bus, exact_authorization = _claim_bootstrap_authorization(
        authorization
    )
    try:
        try:
            durable_root = str(repository._workflow_application_ledger_owner_root())
        except (OSError, ValueError) as error:
            raise _construction_failed() from error

        constructor_entry = False
        with _REGISTRY_LOCK:
            guarded_repository = _REPOSITORY_BY_DURABLE_ROOT.get(durable_root)
            if guarded_repository is not None and guarded_repository is not repository:
                raise _authority_rejected()
            entry = _ROOTS_BY_REPOSITORY.get(id(repository))
            if entry is not None:
                _validate_registry_entry(entry, repository, state_machine, event_bus)
                if entry.state == "READY":
                    if entry.root is None:
                        raise _corrupt()
                    return entry.root
                if entry.state == "CONSTRUCTING":
                    if entry.failure is not None:
                        raise _terminal_generation_error(entry.failure)
                    entry.joined_waiters += 1
                    waiter = entry
            else:
                waiter = _RootRegistryEntry(
                    "CONSTRUCTING", repository, state_machine, event_bus, Event()
                )
                _ROOTS_BY_REPOSITORY[id(repository)] = waiter
                _REPOSITORY_BY_DURABLE_ROOT[durable_root] = repository
                entry = None
                constructor_entry = True

        if entry is not None:
            try:
                waiter.completion.wait()
                if waiter.failure is not None:
                    raise _terminal_generation_error(waiter.failure)
                if waiter.root is None or waiter.state != "READY":
                    raise _corrupt()
                return waiter.root
            finally:
                _complete_joined_waiter_delivery(repository, durable_root, waiter)

        try:
            composition = _build_private_real_delivery_canonical_external_generation_composition_from_owned_repository_v1(
                repository, state_machine, event_bus
            )
            coordinator = composition.external_application
            ledger_store = composition.ledger_store
            if (
                type(ledger_store) is not LocalWorkflowApplicationLedgerStore
                or not isinstance(coordinator._page_store, LocalFileDurablePageStore)
                or coordinator._page_store._repository is not repository
            ):
                raise _authority_rejected()
            root = object.__new__(_PrivateR26ReconciliationCompositionRootV1)
            object.__setattr__(root, "_owner", owner)
            object.__setattr__(root, "_repository", repository)
            object.__setattr__(root, "_state_machine", state_machine)
            object.__setattr__(root, "_event_bus", event_bus)
            object.__setattr__(root, "_composition", composition)
            object.__setattr__(root, "_ledger_store", ledger_store)
            proof_factory = _construct_r26_reconciliation_proof_factory_v1(
                root,
                repository,
                coordinator,
                coordinator._page_store,
                ledger_store,
                coordinator._r25_localfile_composition,
                _issuer=_R26_PROOF_FACTORY_ISSUER,
            )
            object.__setattr__(root, "_r26_proof_factory", proof_factory)
            object.__setattr__(coordinator, "_r26_proof_factory", proof_factory)
        except _PrivateAuthorityRejectedError:
            _fail_construction_generation(repository, durable_root, waiter, "AUTHORITY_REJECTED")
            raise
        except Exception as error:
            _fail_construction_generation(
                repository, durable_root, waiter, "R26_ROOT_CONSTRUCTION_FAILED"
            )
            raise _construction_failed() from error

        with _REGISTRY_LOCK:
            current = _ROOTS_BY_REPOSITORY.get(id(repository))
            if current is not waiter or current.state != "CONSTRUCTING":
                _fail_construction_generation(repository, durable_root, waiter, "CORRUPT")
                raise _corrupt()
            _register_r26_protocol_v1_ready_root(
                root,
                ledger_store,
                repository,
                _issuer=_R26_PREPARATION_ISSUER,
            )
            waiter.root = root
            waiter.state = "READY"
            waiter.completion.set()
        return root
    finally:
        if "constructor_entry" in locals() and constructor_entry:
            _complete_constructor_delivery(repository, durable_root, waiter)
        _tombstone_bootstrap_authorization(exact_authorization)


def _claim_bootstrap_authorization(
    authorization: object,
) -> tuple[
    _PrivateRealDeliveryCompositionOwnerV1,
    LocalFileRepository,
    StateMachine,
    MemoryEventBus,
    _PrivateRealDeliveryBootstrapAuthorizationV1,
]:
    if type(authorization) is not _PrivateRealDeliveryBootstrapAuthorizationV1:
        raise _authority_rejected()
    exact = authorization
    possible_owner = getattr(exact, "_owner", None)
    if type(possible_owner) is not _PrivateRealDeliveryCompositionOwnerV1:
        raise _authority_rejected()
    owner = possible_owner
    if (
        getattr(exact, "_issuer", None) is not owner
        or getattr(exact, "_factory", None) is not _BOOTSTRAP_FACTORY
        or getattr(exact, "_used", None) is not False
        or getattr(exact, "_in_flight", None) is not False
        or exact not in owner._bootstrap_issued
        or getattr(exact, "_repository", None) is not owner._repository
        or getattr(exact, "_state_machine", None) is not owner._state_machine
        or getattr(exact, "_event_bus", None) is not owner._event_bus
    ):
        raise _authority_rejected()
    object.__setattr__(exact, "_in_flight", True)
    return owner, exact._repository, exact._state_machine, exact._event_bus, exact


def _tombstone_bootstrap_authorization(
    authorization: _PrivateRealDeliveryBootstrapAuthorizationV1,
) -> None:
    object.__setattr__(authorization, "_in_flight", False)
    object.__setattr__(authorization, "_used", True)
    authorization._owner._bootstrap_issued.discard(authorization)


def _validate_registry_entry(
    entry: object,
    repository: LocalFileRepository,
    state_machine: StateMachine,
    event_bus: MemoryEventBus,
) -> None:
    if type(entry) is not _RootRegistryEntry:
        raise _corrupt()
    if entry.state not in {"CONSTRUCTING", "READY"}:
        raise _corrupt()
    if (
        entry.repository is not repository
        or entry.state_machine is not state_machine
        or entry.event_bus is not event_bus
    ):
        raise _authority_rejected()


def _fail_construction_generation(
    repository: LocalFileRepository, durable_root: str, entry: _RootRegistryEntry
    , failure: Literal["AUTHORITY_REJECTED", "R26_ROOT_CONSTRUCTION_FAILED", "CORRUPT"]
) -> None:
    with _REGISTRY_LOCK:
        current = _ROOTS_BY_REPOSITORY.get(id(repository))
        if current is not entry or entry.state != "CONSTRUCTING":
            raise _corrupt()
        entry.failure = failure
        entry.completion.set()
        _retire_terminal_generation_if_delivered(repository, durable_root, entry)


def _complete_constructor_delivery(
    repository: LocalFileRepository, durable_root: str, entry: _RootRegistryEntry
) -> None:
    with _REGISTRY_LOCK:
        entry.constructor_pending = False
        _retire_terminal_generation_if_delivered(repository, durable_root, entry)


def _complete_joined_waiter_delivery(
    repository: LocalFileRepository, durable_root: str, entry: _RootRegistryEntry
) -> None:
    with _REGISTRY_LOCK:
        if entry.joined_waiters <= 0:
            raise _corrupt()
        entry.joined_waiters -= 1
        _retire_terminal_generation_if_delivered(repository, durable_root, entry)


def _retire_terminal_generation_if_delivered(
    repository: LocalFileRepository, durable_root: str, entry: _RootRegistryEntry
) -> None:
    if (
        entry.state != "CONSTRUCTING"
        or entry.failure is None
        or entry.constructor_pending
        or entry.joined_waiters != 0
    ):
        return
    if _ROOTS_BY_REPOSITORY.get(id(repository)) is entry:
        del _ROOTS_BY_REPOSITORY[id(repository)]
    if _REPOSITORY_BY_DURABLE_ROOT.get(durable_root) is repository:
        del _REPOSITORY_BY_DURABLE_ROOT[durable_root]


def _terminal_generation_error(
    failure: str | None,
) -> ValueError:
    if failure == "AUTHORITY_REJECTED":
        return _authority_rejected()
    if failure == "R26_ROOT_CONSTRUCTION_FAILED":
        return _construction_failed()
    if failure == "CORRUPT":
        return _corrupt()
    return _corrupt()
