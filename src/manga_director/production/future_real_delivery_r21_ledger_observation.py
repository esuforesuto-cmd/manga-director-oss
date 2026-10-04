"""Private R21 LocalFile composition check for read-only Ledger observation.

R21 creates no capability and owns no lifecycle transition.  This module only
ensures that a private caller is observing the fixed Ledger owner attached to
the same LocalFile composition before delegating to the Ledger owner's
read-only seam.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from manga_director.production.next_generation_workflow_application_ledger import (
    LocalWorkflowApplicationLedgerStore,
    _WorkflowApplicationLedgerObservationV1,
)
from manga_director.repositories.local_file import LocalFileRepository


class _R21LedgerObservationBoundaryV1:
    """One private composition-held observer; its Ledger owner cannot be replaced."""

    __slots__ = ("_ledger_store", "_construction_outcome")

    _ledger_store: LocalWorkflowApplicationLedgerStore | None
    _construction_outcome: Literal["AUTHORITY_REJECTED"] | None

    def __init__(self, *args: object) -> None:
        del args
        raise ValueError("AUTHORITY_REJECTED")

    def _observe_exact_readonly_v1(self, binding: object) -> _WorkflowApplicationLedgerObservationV1:
        if self._construction_outcome is not None:
            return _WorkflowApplicationLedgerObservationV1(self._construction_outcome)
        if self._ledger_store is None:
            return _WorkflowApplicationLedgerObservationV1("AUTHORITY_REJECTED")
        return self._ledger_store._observe_exact_readonly_v1(binding)


class _R21LocalFileLedgerCompositionV1:
    """Private construction-held LocalFile/Ledger pair for one R21 observer."""

    __slots__ = ("_repository", "_ledger_store")

    _repository: LocalFileRepository
    _ledger_store: LocalWorkflowApplicationLedgerStore

    def __init__(self, *args: object) -> None:
        del args
        raise ValueError("AUTHORITY_REJECTED")


def _construct_localfile_ledger_observation_composition_v1(
    repository_root: object,
) -> _R21LocalFileLedgerCompositionV1:
    """Construct the only pair a private R21 composition can authenticate.

    The Ledger path is derived exclusively from the fresh LocalFile repository;
    callers never supply a Ledger instance for positive composition authority.
    """

    if not isinstance(repository_root, Path):
        raise ValueError("AUTHORITY_REJECTED")
    repository = LocalFileRepository(repository_root)
    ledger_store = LocalWorkflowApplicationLedgerStore(
        repository._workflow_application_ledger_owner_root()
    )
    composition = object.__new__(_R21LocalFileLedgerCompositionV1)
    object.__setattr__(composition, "_repository", repository)
    object.__setattr__(composition, "_ledger_store", ledger_store)
    return composition


def _bind_exact_localfile_ledger_observer_v1(
    composition: object,
    repository: object,
    ledger_store: object,
) -> _R21LedgerObservationBoundaryV1:
    """Bind the sole Ledger instance held by one fixed LocalFile composition.

    This is deliberately not an R20 provenance check: a valid equal Ledger
    DTO remains a query value only.  Once bound, callers cannot supply a
    replacement Ledger owner to the observation operation.
    """

    boundary = object.__new__(_R21LedgerObservationBoundaryV1)
    if type(composition) is not _R21LocalFileLedgerCompositionV1:
        object.__setattr__(boundary, "_ledger_store", None)
        object.__setattr__(boundary, "_construction_outcome", "AUTHORITY_REJECTED")
        return boundary
    if (
        repository is not composition._repository
        or ledger_store is not composition._ledger_store
    ):
        object.__setattr__(boundary, "_ledger_store", None)
        object.__setattr__(boundary, "_construction_outcome", "AUTHORITY_REJECTED")
        return boundary
    object.__setattr__(boundary, "_ledger_store", ledger_store)
    object.__setattr__(boundary, "_construction_outcome", None)
    return boundary
