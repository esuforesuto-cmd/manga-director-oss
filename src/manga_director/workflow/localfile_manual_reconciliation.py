"""Private Ledger-only reconciliation for one exact durable external application.

The coordinator never repairs a Project, creates a Receipt, publishes an
event, or executes generation.  It can only complete a prepared Ledger row
when the current authoritative Project still exactly matches its Receipt.
"""

# ruff: noqa: C901

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, Protocol, cast

from pydantic import ConfigDict

from manga_director.domain.state_machine import PageState
from manga_director.production.director import DirectorModel
from manga_director.production.next_generation_durable_application_commit_receipt import (
    DurableApplicationCommitReceiptService,
    LocalDurableApplicationCommitReceiptStore,
)
from manga_director.production.next_generation_durable_evidence_workflow_binding import (
    DurableEvidenceWorkflowBindingReport,
    WorkflowApplicationAuthorizationDTO,
)
from manga_director.production.next_generation_workflow_application_ledger import (
    _DATABASE_FILENAME,
    _TABLE_NAME,
    LocalWorkflowApplicationLedgerStore,
    WorkflowApplicationLedgerBindingDTO,
    WorkflowApplicationLedgerService,
    _binding_from_eligibility,
    _canonical_payload,
    _digest,
)
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.workflow.durable_execution import LocalFileDurablePageStore
from manga_director.workflow.page_execution_fence import (
    PageExecutionFenceError,
    PageExecutionFencePort,
    WindowsPageExecutionFence,
)

ManualReconciliationStatus = Literal["reconciled", "confirmed", "blocked"]


class _ManualReconciliationModel(DirectorModel):
    """Private immutable, closed reconciliation values."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class ManualReconciliationInputDTO(_ManualReconciliationModel):
    """Exact existing normal evidence required for one private reconciliation."""

    binding_report: DurableEvidenceWorkflowBindingReport
    authorization: WorkflowApplicationAuthorizationDTO


class ManualReconciliationFindingDTO(_ManualReconciliationModel):
    """One deterministic redacted reconciliation finding."""

    code: str
    status: Literal["blocked"]
    message: str


class ManualReconciliationReport(_ManualReconciliationModel):
    """Private bounded outcome without Project or Receipt storage internals."""

    attempt_id: str = ""
    authorization_id: str = ""
    project_id: str = ""
    page_id: str = ""
    output_asset_id: str = ""
    status: ManualReconciliationStatus
    reconciled: bool
    confirmed: bool
    findings: tuple[ManualReconciliationFindingDTO, ...] = ()


class _ManualReconciliationCoordinatorPort(Protocol):
    """The sole caller-facing operation for one trusted LocalFile composition."""

    def reconcile(self, input: ManualReconciliationInputDTO) -> ManualReconciliationReport: ...


@dataclass(frozen=True, slots=True)
class LocalFileManualReconciliationComposition:
    """Private LocalFile dependencies for reconciliation only."""

    coordinator: _ManualReconciliationCoordinatorPort


@dataclass(frozen=True, slots=True)
class _LocalFileManualReconciliationCoordinator:
    """The sole reconciliation owner; every mutation follows fresh validation."""

    _repository: LocalFileRepository

    def reconcile(self, input: ManualReconciliationInputDTO) -> ManualReconciliationReport:
        """Reconcile only after all immutable, current, and durable facts agree."""

        binding = _binding_from_eligibility(input.binding_report, input.authorization)
        if binding is None:
            return _blocked(None, "MANUAL_RECONCILIATION_BINDING_INVALID")
        fence: PageExecutionFencePort | None = None
        connection: sqlite3.Connection | None = None
        try:
            fence = WindowsPageExecutionFence(binding.project_id, binding.page_id)
            fence.acquire()

            owner_root = self._repository._workflow_application_ledger_owner_root()
            ledger_service = WorkflowApplicationLedgerService()
            ledger_store = LocalWorkflowApplicationLedgerStore(owner_root)
            receipt_service = DurableApplicationCommitReceiptService()
            receipt_store = LocalDurableApplicationCommitReceiptStore(owner_root)
            page_store = LocalFileDurablePageStore(self._repository)

            snapshot = page_store.load_revisioned(binding.project_id)
            context = page_store.context_from_snapshot(snapshot, binding.page_id)
            if not _generated_logical_output_matches(context, binding):
                return _blocked(binding, "MANUAL_RECONCILIATION_PROJECT_STATE_MISMATCH")
            revision = getattr(snapshot, "revision", None)
            fingerprint = getattr(snapshot, "fingerprint", None)
            if not _private_correlation(revision, fingerprint):
                return _blocked(binding, "MANUAL_RECONCILIATION_PROJECT_CORRELATION_INVALID")
            receipt = receipt_service.lookup_exact(
                binding,
                post_commit_revision=cast(int, revision),
                post_commit_fingerprint=cast(str, fingerprint),
                receipt_store=receipt_store,
            )
            if receipt.outcome != "found":
                return _blocked(binding, _receipt_code(receipt.outcome))
            lifecycle = ledger_service.lookup_exact(binding, ledger_store)
            if lifecycle.outcome == "applied":
                return _confirmed(binding)
            if lifecycle.outcome != "prepared":
                return _blocked(binding, _ledger_lookup_code(lifecycle.outcome))

            # This is deliberately inline: no callable receives a prepared binding
            # and can mutate its lifecycle without repeating this method's checks.
            connection = sqlite3.connect(
                owner_root / _DATABASE_FILENAME, timeout=5.0, isolation_level=None
            )
            mode = str(connection.execute("PRAGMA journal_mode = DELETE").fetchone()[0]).lower()
            if mode != "delete":
                return _blocked(binding, "MANUAL_RECONCILIATION_LEDGER_FINALIZE_FAILED")
            connection.execute("PRAGMA synchronous = FULL")
            connection.execute("BEGIN IMMEDIATE")
            payload = _canonical_payload(binding, "applied")
            cursor = connection.execute(
                f"UPDATE {_TABLE_NAME} SET lifecycle = ?, binding_json = ?, binding_digest = ? "
                "WHERE attempt_id = ? AND authorization_id = ? AND project_id = ? AND page_id = ? "
                "AND target_page_reference = ? AND provider_reference = ? AND output_asset_id = ? "
                "AND source_state = ? AND target_state = ? AND lifecycle = 'prepared'",
                (
                    "applied",
                    payload,
                    _digest(payload),
                    binding.attempt_id,
                    binding.authorization_id,
                    binding.project_id,
                    binding.page_id,
                    binding.target_page_reference,
                    binding.provider_reference,
                    binding.output_asset_id,
                    binding.source_state,
                    binding.target_state,
                ),
            )
            if cursor.rowcount != 1:
                connection.rollback()
                return _blocked(binding, "MANUAL_RECONCILIATION_LEDGER_FINALIZE_FAILED")
            connection.commit()
            confirmed = ledger_service.lookup_exact(binding, ledger_store)
            if confirmed.outcome != "applied":
                return _blocked(binding, "MANUAL_RECONCILIATION_APPLIED_CONFIRMATION_FAILED")
            return _reconciled(binding)
        except PageExecutionFenceError:
            return _blocked(binding, "MANUAL_RECONCILIATION_PAGE_FENCE_UNAVAILABLE")
        except Exception:
            return _blocked(binding, "MANUAL_RECONCILIATION_FAILED")
        finally:
            if connection is not None:
                try:
                    connection.rollback()
                except sqlite3.Error:
                    pass
                connection.close()
            if fence is not None:
                fence.release()


def build_localfile_manual_reconciliation_composition(
    repository: LocalFileRepository,
) -> LocalFileManualReconciliationComposition:
    """Compose the one trusted LocalFile reconciliation owner."""

    return LocalFileManualReconciliationComposition(
        coordinator=_LocalFileManualReconciliationCoordinator(repository)
    )


def _generated_logical_output_matches(
    context: object, binding: WorkflowApplicationLedgerBindingDTO
) -> bool:
    state = getattr(context, "state", None)
    artifacts = getattr(context, "artifacts", None)
    if state != PageState.GENERATED or not isinstance(artifacts, Mapping):
        return False
    return artifacts.get(PageState.GENERATED.value) == {
        "artifact_kind": "logical_output_asset",
        "output_asset_id": binding.output_asset_id,
    }


def _private_correlation(revision: object, fingerprint: object) -> bool:
    return (
        isinstance(revision, int)
        and not isinstance(revision, bool)
        and revision >= 1
        and isinstance(fingerprint, str)
        and len(fingerprint) == 64
        and all(character in "0123456789abcdef" for character in fingerprint)
    )


def _receipt_code(outcome: str) -> str:
    return {
        "missing": "MANUAL_RECONCILIATION_RECEIPT_MISSING",
        "conflict": "MANUAL_RECONCILIATION_RECEIPT_CONFLICT",
        "corrupt": "MANUAL_RECONCILIATION_RECEIPT_CORRUPT",
    }.get(outcome, "MANUAL_RECONCILIATION_RECEIPT_INVALID")


def _ledger_lookup_code(outcome: str) -> str:
    return {
        "missing": "MANUAL_RECONCILIATION_LEDGER_MISSING",
        "conflict": "MANUAL_RECONCILIATION_LEDGER_CONFLICT",
        "corrupt": "MANUAL_RECONCILIATION_LEDGER_CORRUPT",
    }.get(outcome, "MANUAL_RECONCILIATION_LEDGER_INVALID")


def _reconciled(binding: WorkflowApplicationLedgerBindingDTO) -> ManualReconciliationReport:
    return _report(binding, "reconciled", reconciled=True, confirmed=False)


def _confirmed(binding: WorkflowApplicationLedgerBindingDTO) -> ManualReconciliationReport:
    return _report(binding, "confirmed", reconciled=False, confirmed=True)


def _blocked(
    binding: WorkflowApplicationLedgerBindingDTO | None, code: str
) -> ManualReconciliationReport:
    return _report(
        binding,
        "blocked",
        reconciled=False,
        confirmed=False,
        findings=(
            ManualReconciliationFindingDTO(
                code=code,
                status="blocked",
                message="manual reconciliation is unavailable",
            ),
        ),
    )


def _report(
    binding: WorkflowApplicationLedgerBindingDTO | None,
    status: ManualReconciliationStatus,
    *,
    reconciled: bool,
    confirmed: bool,
    findings: tuple[ManualReconciliationFindingDTO, ...] = (),
) -> ManualReconciliationReport:
    if binding is None:
        return ManualReconciliationReport(
            status=status,
            reconciled=reconciled,
            confirmed=confirmed,
            findings=findings,
        )
    return ManualReconciliationReport(
        attempt_id=binding.attempt_id,
        authorization_id=binding.authorization_id,
        project_id=binding.project_id,
        page_id=binding.page_id,
        output_asset_id=binding.output_asset_id,
        status=status,
        reconciled=reconciled,
        confirmed=confirmed,
        findings=findings,
    )
