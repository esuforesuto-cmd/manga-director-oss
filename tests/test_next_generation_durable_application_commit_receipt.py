"""Focused fake-only tests for private durable application commit correlation."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest

from manga_director.domain.state_machine import PageState, StateMachine
from manga_director.events import MemoryEventBus
from manga_director.production.next_generation_durable_application_commit_receipt import (
    DurableApplicationCommitReceiptService,
    DurableApplicationCommitReceiptStoreWriteResult,
    LocalDurableApplicationCommitReceiptStore,
)
from manga_director.production.next_generation_durable_evidence_workflow_binding import (
    DurableEvidenceWorkflowBindingReport,
    WorkflowApplicationAuthorizationDTO,
)
from manga_director.production.next_generation_workflow_application_ledger import (
    LocalWorkflowApplicationLedgerStore,
    WorkflowApplicationLedgerBindingDTO,
    WorkflowApplicationLedgerService,
    WorkflowApplicationLedgerStoreWriteResult,
    _authoritative_commit_proof,
)
from manga_director.workflow.contracts import WorkflowContext
from manga_director.workflow.localfile_external_generated_application import (
    LocalFileExternalGeneratedApplicationCoordinator,
    LocalFileLogicalOutputAssetQualityGate,
)

_ATTEMPT = "attempt:receipt:001"
_AUTHORIZATION = "authorization:receipt:001"
_PROJECT = "project:receipt:001"
_PAGE = "1"
_TARGET = "page:receipt:001"
_PROVIDER = "provider:receipt:001"
_OUTPUT = "asset:receipt:001"


def _binding(**updates: object) -> WorkflowApplicationLedgerBindingDTO:
    values: dict[str, object] = {
        "attempt_id": _ATTEMPT,
        "authorization_id": _AUTHORIZATION,
        "project_id": _PROJECT,
        "page_id": _PAGE,
        "target_page_reference": _TARGET,
        "provider_reference": _PROVIDER,
        "output_asset_id": _OUTPUT,
        "source_state": "PromptBuilt",
        "target_state": "Generated",
    }
    values.update(updates)
    return WorkflowApplicationLedgerBindingDTO.model_validate(values)


def _report() -> DurableEvidenceWorkflowBindingReport:
    return DurableEvidenceWorkflowBindingReport(
        attempt_id=_ATTEMPT,
        provider_reference=_PROVIDER,
        output_asset_id=_OUTPUT,
        project_id=_PROJECT,
        page_id=_PAGE,
        target_page_reference=_TARGET,
        status="eligible",
        eligible=True,
    )


def _authorization() -> WorkflowApplicationAuthorizationDTO:
    return WorkflowApplicationAuthorizationDTO(
        authorization_id=_AUTHORIZATION,
        authorizer_id="human:receipt:001",
        authorized_at=datetime(2026, 8, 23, tzinfo=UTC),
        attempt_id=_ATTEMPT,
        provider_reference=_PROVIDER,
        project_id=_PROJECT,
        page_id=_PAGE,
        target_page_reference=_TARGET,
        source_state="PromptBuilt",
        target_state="Generated",
    )


def test_receipt_requires_the_opaque_proof_and_preserves_private_integrity(
    tmp_path: Path,
) -> None:
    service = DurableApplicationCommitReceiptService()
    store = LocalDurableApplicationCommitReceiptStore(tmp_path / "receipt")
    binding = _binding()

    forged = service.commit(
        binding,
        object(),
        post_commit_revision=2,
        post_commit_fingerprint="a" * 64,
        receipt_store=store,
    )
    committed = service.commit(
        binding,
        _authoritative_commit_proof(binding),
        post_commit_revision=2,
        post_commit_fingerprint="a" * 64,
        receipt_store=store,
    )
    replay = service.commit(
        binding,
        _authoritative_commit_proof(binding),
        post_commit_revision=2,
        post_commit_fingerprint="a" * 64,
        receipt_store=store,
    )
    conflicting = service.commit(
        _binding(output_asset_id="asset:receipt:other"),
        _authoritative_commit_proof(_binding(output_asset_id="asset:receipt:other")),
        post_commit_revision=2,
        post_commit_fingerprint="a" * 64,
        receipt_store=store,
    )
    competing = _binding(
        attempt_id="attempt:receipt:other",
        authorization_id="authorization:receipt:other",
    )
    competing_commit = service.commit(
        competing,
        _authoritative_commit_proof(competing),
        post_commit_revision=2,
        post_commit_fingerprint="a" * 64,
        receipt_store=store,
    )

    assert forged.committed is False
    assert forged.findings[0].code == "RECEIPT_AUTHORITATIVE_COMMIT_PROOF_INVALID"
    assert committed.committed is True and committed.idempotent_confirmation is False
    assert replay.committed is True and replay.idempotent_confirmation is True
    assert conflicting.committed is False
    assert competing_commit.committed is False
    serialized = committed.model_dump_json() + forged.model_dump_json()
    assert "a" * 64 not in serialized
    assert "receipt_digest" not in serialized
    with sqlite3.connect(tmp_path / "receipt" / "durable-application-commit-receipts.sqlite3") as connection:
        assert connection.execute(
            "SELECT post_commit_revision, post_commit_fingerprint "
            "FROM durable_application_commit_receipts"
        ).fetchone() == (2, "a" * 64)


def test_receipt_store_schema_and_corruption_fail_closed(tmp_path: Path) -> None:
    store = LocalDurableApplicationCommitReceiptStore(tmp_path / "receipt")
    database = tmp_path / "receipt" / "durable-application-commit-receipts.sqlite3"

    assert database.is_file()
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (1,)
    with pytest.raises(ValueError, match="durable application commit receipt unavailable"):
        LocalDurableApplicationCommitReceiptStore(Path("relative-owner-root"))

    service = DurableApplicationCommitReceiptService()
    binding = _binding()
    assert service.commit(
        binding,
        _authoritative_commit_proof(binding),
        post_commit_revision=2,
        post_commit_fingerprint="b" * 64,
        receipt_store=store,
    ).committed
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE durable_application_commit_receipts SET receipt_digest = 'tampered'"
        )
    corrupt = service.commit(
        binding,
        _authoritative_commit_proof(binding),
        post_commit_revision=2,
        post_commit_fingerprint="b" * 64,
        receipt_store=store,
    )
    assert corrupt.committed is False


@dataclass(frozen=True)
class _Snapshot:
    revision: int
    fingerprint: str


@dataclass(frozen=True)
class _Commit:
    revision: int


class _Fence:
    def __init__(self) -> None:
        self.acquired = 0
        self.released = 0

    def acquire(self) -> None:
        self.acquired += 1

    def release(self) -> None:
        self.released += 1


class _PageStore:
    def __init__(self, order: list[str], *, cas_fails: bool = False, verify: bool = True) -> None:
        self.context = WorkflowContext(
            page={"project_id": _PROJECT, "page_id": _PAGE},
            state=PageState.PROMPT_BUILT,
            artifacts={"PromptBuilt": {"prompt_markdown": "private prompt"}},
        )
        self.order = order
        self.cas_fails = cas_fails
        self.verify = verify
        self.revision = 1
        self.fingerprint = "1" * 64
        self.commits = 0

    def load_revisioned(self, project_id: str) -> _Snapshot:
        assert project_id == _PROJECT
        return _Snapshot(self.revision, self.fingerprint)

    def context_from_snapshot(self, snapshot: _Snapshot, page_id: str) -> WorkflowContext:
        del snapshot
        assert page_id == _PAGE
        return self.context

    def project_from_context(
        self, snapshot: _Snapshot, page_id: str, context: WorkflowContext
    ) -> WorkflowContext:
        del snapshot
        assert page_id == _PAGE
        return context

    def conditional_commit(self, snapshot: _Snapshot, project: WorkflowContext) -> _Commit:
        del snapshot
        self.order.append("CAS")
        self.commits += 1
        if self.cas_fails:
            raise RuntimeError("private CAS failure")
        self.context = project
        self.revision += 1
        self.fingerprint = f"{self.revision:064x}"
        return _Commit(self.revision)

    def verify_committed(
        self, project_id: str, page_id: str, expected_project: WorkflowContext
    ) -> bool:
        self.order.append("VERIFY")
        return self.verify and (project_id, page_id) == (_PROJECT, _PAGE) and expected_project == self.context


class _RecordingReceiptStore:
    def __init__(self, delegate: LocalDurableApplicationCommitReceiptStore, order: list[str]) -> None:
        self._delegate = delegate
        self._order = order
        self.calls = 0

    def commit(self, receipt: object) -> DurableApplicationCommitReceiptStoreWriteResult:
        self._order.append("RECEIPT")
        self.calls += 1
        return self._delegate.commit(receipt)  # type: ignore[arg-type]


class _FailingReceiptStore:
    def __init__(self) -> None:
        self.calls = 0

    def commit(self, receipt: object) -> DurableApplicationCommitReceiptStoreWriteResult:
        del receipt
        self.calls += 1
        raise RuntimeError("private receipt failure")


class _RecordingLedgerStore:
    def __init__(self, delegate: LocalWorkflowApplicationLedgerStore, order: list[str]) -> None:
        self._delegate = delegate
        self._order = order

    def prepare(
        self, binding: WorkflowApplicationLedgerBindingDTO
    ) -> WorkflowApplicationLedgerStoreWriteResult:
        return self._delegate.prepare(binding)

    def finalize(
        self, binding: WorkflowApplicationLedgerBindingDTO, mutation_capability: object
    ) -> WorkflowApplicationLedgerStoreWriteResult:
        self._order.append("FINALIZE")
        return self._delegate.finalize(binding, mutation_capability)  # type: ignore[arg-type]

    def lookup_applied(self, project_id: str, page_id: str, output_asset_id: str):
        return self._delegate.lookup_applied(project_id, page_id, output_asset_id)


class _RecordingEventBus(MemoryEventBus):
    def __init__(self, order: list[str]) -> None:
        super().__init__()
        self._order = order

    def publish(self, events: list[object]) -> None:
        self._order.append("EVENT")
        super().publish(cast(list, events))


def _coordinator(
    tmp_path: Path,
    page_store: _PageStore,
    receipt_store: object,
    event_bus: MemoryEventBus,
    order: list[str],
) -> tuple[LocalFileExternalGeneratedApplicationCoordinator, WorkflowApplicationLedgerService, LocalWorkflowApplicationLedgerStore]:
    service = WorkflowApplicationLedgerService()
    ledger = LocalWorkflowApplicationLedgerStore(tmp_path / "ledger")
    coordinator = LocalFileExternalGeneratedApplicationCoordinator(
        StateMachine(),
        event_bus,
        service,
        _RecordingLedgerStore(ledger, order),  # type: ignore[arg-type]
        DurableApplicationCommitReceiptService(),
        receipt_store,  # type: ignore[arg-type]
        page_store,  # type: ignore[arg-type]
        fence_factory=lambda project_id, page_id: _Fence(),
    )
    return coordinator, service, ledger


def test_verified_cas_receipt_finalize_event_order(tmp_path: Path) -> None:
    order: list[str] = []
    page_store = _PageStore(order)
    receipt_store = _RecordingReceiptStore(
        LocalDurableApplicationCommitReceiptStore(tmp_path / "receipt"), order
    )
    coordinator, service, ledger = _coordinator(
        tmp_path, page_store, receipt_store, _RecordingEventBus(order), order
    )

    result = coordinator.apply(_report(), _authorization())

    assert result.status == "application_applied_event_published"
    assert order == ["CAS", "VERIFY", "RECEIPT", "FINALIZE", "EVENT"]
    assert service.lookup_applied(_PROJECT, _PAGE, _OUTPUT, ledger).applied is True


def test_cas_or_verification_failure_cannot_create_a_receipt(tmp_path: Path) -> None:
    for name, page_store in (
        ("cas", _PageStore([], cas_fails=True)),
        ("verify", _PageStore([], verify=False)),
    ):
        order: list[str] = page_store.order
        receipt_store = _RecordingReceiptStore(
            LocalDurableApplicationCommitReceiptStore(tmp_path / name / "receipt"), order
        )
        coordinator, _, _ = _coordinator(
            tmp_path / name, page_store, receipt_store, _RecordingEventBus(order), order
        )

        result = coordinator.apply(_report(), _authorization())

        assert result.status == "application_not_applied"
        assert receipt_store.calls == 0


def test_receipt_failure_keeps_generated_prepared_and_quality_blocked(tmp_path: Path) -> None:
    order: list[str] = []
    page_store = _PageStore(order)
    receipt_store = _FailingReceiptStore()
    event_bus = _RecordingEventBus(order)
    coordinator, service, ledger = _coordinator(
        tmp_path, page_store, receipt_store, event_bus, order
    )

    result = coordinator.apply(_report(), _authorization())
    quality = LocalFileLogicalOutputAssetQualityGate(service, ledger).require_applied(page_store.context)

    assert result.status == "application_applied_receipt_failed"
    assert page_store.context.state == PageState.GENERATED
    assert receipt_store.calls == 1
    assert "FINALIZE" not in order and "EVENT" not in order
    assert service.prepare(_report(), _authorization(), ledger).prepared is True
    assert quality == "LOGICAL_OUTPUT_ASSET_QUALITY_PROOF_UNAVAILABLE"
