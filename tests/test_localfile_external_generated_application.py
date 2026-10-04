"""Focused fake-only tests for external Generated application and Ledger gating."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from manga_director.domain.state_machine import PageState, StateMachine
from manga_director.events import MemoryEventBus
from manga_director.production.next_generation_durable_application_commit_receipt import (
    DurableApplicationCommitReceiptService,
    LocalDurableApplicationCommitReceiptStore,
)
from manga_director.production.next_generation_durable_evidence_workflow_binding import (
    DurableEvidenceWorkflowBindingReport,
    WorkflowApplicationAuthorizationDTO,
)
from manga_director.production.next_generation_workflow_application_ledger import (
    LocalWorkflowApplicationLedgerStore,
    WorkflowApplicationLedgerAppliedLookupResult,
    WorkflowApplicationLedgerBindingDTO,
    WorkflowApplicationLedgerService,
    WorkflowApplicationLedgerStorePort,
    WorkflowApplicationLedgerStoreWriteResult,
    _authoritative_commit_proof,
)
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.workflow.contracts import AgentResult, WorkflowContext
from manga_director.workflow.durable_execution import DurableWorkflowExecutionCoordinator
from manga_director.workflow.engine import WorkflowEngine
from manga_director.workflow.localfile_external_generated_application import (
    LocalFileExternalGeneratedApplicationCoordinator,
    LocalFileLogicalOutputAssetQualityGate,
    build_localfile_external_generation_composition,
)

_ATTEMPT = "attempt:external:001"
_AUTHORIZATION = "authorization:external:001"
_PROJECT = "project:external:001"
_PAGE = "1"
_TARGET = "page:external:001"
_PROVIDER = "provider:external:001"
_OUTPUT = "asset:external:001"


class _Fence:
    def __init__(self) -> None:
        self.acquired = 0
        self.released = 0

    def acquire(self) -> None:
        self.acquired += 1

    def release(self) -> None:
        self.released += 1


@dataclass(frozen=True)
class _Snapshot:
    revision: int
    fingerprint: str


@dataclass(frozen=True)
class _Commit:
    revision: int


class _PageStore:
    def __init__(self, context: WorkflowContext, *, commit_fails: bool = False) -> None:
        self.context = context
        self.commit_fails = commit_fails
        self.commits = 0
        self.verifications = 0
        self.revision = 1
        self.fingerprint = "a" * 64

    def load_revisioned(self, project_id: str) -> _Snapshot:
        assert project_id == _PROJECT
        return _Snapshot(self.revision, self.fingerprint)

    def context_from_snapshot(self, snapshot: object, page_id: str) -> WorkflowContext:
        del snapshot
        assert page_id == _PAGE
        return self.context

    def project_from_context(
        self, snapshot: object, page_id: str, context: WorkflowContext
    ) -> object:
        del snapshot
        assert page_id == _PAGE
        return context

    def conditional_commit(self, snapshot: object, project: object) -> _Commit:
        del snapshot
        self.commits += 1
        if self.commit_fails:
            raise RuntimeError("synthetic CAS failure")
        self.context = cast(WorkflowContext, project)
        self.revision += 1
        self.fingerprint = f"{self.revision:064x}"
        return _Commit(self.revision)

    def verify_committed(self, project_id: str, page_id: str, expected_project: object) -> bool:
        assert (project_id, page_id) == (_PROJECT, _PAGE)
        self.verifications += 1
        return expected_project == self.context


class _RaisingEventBus(MemoryEventBus):
    def publish(self, events: list[object]) -> None:
        del events
        raise RuntimeError("private event failure")


class _ProofCheckingEventBus(MemoryEventBus):
    def __init__(
        self,
        ledger_service: WorkflowApplicationLedgerService,
        ledger_store: WorkflowApplicationLedgerStorePort,
    ) -> None:
        super().__init__()
        self._ledger_service = ledger_service
        self._ledger_store = ledger_store
        self.published_after_finalize = False

    def publish(self, events: list[object]) -> None:
        self.published_after_finalize = (
            self._ledger_service.lookup_applied(_PROJECT, _PAGE, _OUTPUT, self._ledger_store).applied
            is True
        )
        super().publish(events)  # type: ignore[arg-type]


class _FinalizeFailingLedgerStore:
    def __init__(self, delegate: WorkflowApplicationLedgerStorePort) -> None:
        self._delegate = delegate

    def prepare(
        self, binding: WorkflowApplicationLedgerBindingDTO
    ) -> WorkflowApplicationLedgerStoreWriteResult:
        return self._delegate.prepare(binding)

    def finalize(
        self, binding: WorkflowApplicationLedgerBindingDTO, mutation_capability: object
    ) -> WorkflowApplicationLedgerStoreWriteResult:
        del binding, mutation_capability
        raise RuntimeError("private ledger finalize failure")

    def lookup_applied(
        self, project_id: str, page_id: str, output_asset_id: str
    ) -> WorkflowApplicationLedgerAppliedLookupResult:
        return self._delegate.lookup_applied(project_id, page_id, output_asset_id)


class _QualityAgent:
    def __init__(self) -> None:
        self.calls = 0

    def execute(self, context: WorkflowContext) -> AgentResult:
        del context
        self.calls += 1
        return AgentResult(success=True, state=PageState.QUALITY_CHECKED, payload={})


def _context(state: PageState = PageState.PROMPT_BUILT) -> WorkflowContext:
    return WorkflowContext(
        page={"project_id": _PROJECT, "page_id": _PAGE},
        state=state,
        artifacts={"PromptBuilt": {"prompt_markdown": "private prompt"}},
    )


def _authorization(**updates: object) -> WorkflowApplicationAuthorizationDTO:
    values: dict[str, object] = {
        "authorization_id": _AUTHORIZATION,
        "authorizer_id": "human:external:001",
        "authorized_at": datetime(2026, 8, 23, tzinfo=UTC),
        "attempt_id": _ATTEMPT,
        "provider_reference": _PROVIDER,
        "project_id": _PROJECT,
        "page_id": _PAGE,
        "target_page_reference": _TARGET,
        "source_state": "PromptBuilt",
        "target_state": "Generated",
    }
    values.update(updates)
    return WorkflowApplicationAuthorizationDTO.model_validate(values)


def _binding_report(**updates: object) -> DurableEvidenceWorkflowBindingReport:
    values: dict[str, object] = {
        "attempt_id": _ATTEMPT,
        "provider_reference": _PROVIDER,
        "output_asset_id": _OUTPUT,
        "project_id": _PROJECT,
        "page_id": _PAGE,
        "target_page_reference": _TARGET,
        "status": "eligible",
        "eligible": True,
    }
    values.update(updates)
    return DurableEvidenceWorkflowBindingReport.model_validate(values)


def _coordinator(
    tmp_path: Path,
    page_store: _PageStore,
    event_bus: MemoryEventBus | None = None,
) -> tuple[LocalFileExternalGeneratedApplicationCoordinator, WorkflowApplicationLedgerService, LocalWorkflowApplicationLedgerStore]:
    ledger_service = WorkflowApplicationLedgerService()
    ledger_store = LocalWorkflowApplicationLedgerStore(tmp_path / "ledger")
    receipt_service = DurableApplicationCommitReceiptService()
    receipt_store = LocalDurableApplicationCommitReceiptStore(tmp_path / "receipt")
    fence = _Fence()
    return (
        LocalFileExternalGeneratedApplicationCoordinator(
            StateMachine(),
            event_bus or MemoryEventBus(),
            ledger_service,
            ledger_store,
            receipt_service,
            receipt_store,
            page_store,  # type: ignore[arg-type]
            fence_factory=lambda project_id, page_id: fence,
        ),
        ledger_service,
        ledger_store,
    )


def test_trusted_composition_uses_a_stable_absolute_owner_root(tmp_path: Path) -> None:
    repository = LocalFileRepository(tmp_path)
    first = repository._workflow_application_ledger_owner_root()
    second = repository._workflow_application_ledger_owner_root()

    assert first == second
    assert first.is_absolute()
    assert first.name == "_workflow_application_ledger"


def test_external_application_commits_once_then_finalizes_before_event(tmp_path: Path) -> None:
    page_store = _PageStore(_context())
    bus = MemoryEventBus()
    coordinator, service, store = _coordinator(tmp_path, page_store, bus)

    result = coordinator.apply(_binding_report(), _authorization())

    assert result.status == "application_applied_event_published"
    assert page_store.commits == 1 and page_store.verifications == 1
    assert page_store.context.state == PageState.GENERATED
    assert page_store.context.artifacts["Generated"] == {
        "artifact_kind": "logical_output_asset",
        "output_asset_id": _OUTPUT,
    }
    assert len(bus.published) == 1
    assert service.lookup_applied(_PROJECT, _PAGE, _OUTPUT, store).applied is True


def test_event_publication_occurs_only_after_ledger_finalize(tmp_path: Path) -> None:
    page_store = _PageStore(_context())
    ledger_service = WorkflowApplicationLedgerService()
    ledger_store = LocalWorkflowApplicationLedgerStore(tmp_path / "ledger")
    receipt_service = DurableApplicationCommitReceiptService()
    receipt_store = LocalDurableApplicationCommitReceiptStore(tmp_path / "receipt")
    bus = _ProofCheckingEventBus(ledger_service, ledger_store)
    coordinator = LocalFileExternalGeneratedApplicationCoordinator(
        StateMachine(),
        bus,
        ledger_service,
        ledger_store,
        receipt_service,
        receipt_store,
        page_store,  # type: ignore[arg-type]
        fence_factory=lambda project_id, page_id: _Fence(),
    )

    assert coordinator.apply(_binding_report(), _authorization()).event_published is True
    assert bus.published_after_finalize is True


def test_applied_replay_does_not_commit_or_republish(tmp_path: Path) -> None:
    page_store = _PageStore(_context())
    bus = MemoryEventBus()
    coordinator, _, _ = _coordinator(tmp_path, page_store, bus)

    assert coordinator.apply(_binding_report(), _authorization()).event_published is True
    replay = coordinator.apply(_binding_report(), _authorization())

    assert replay.status == "application_replay_confirmed"
    assert page_store.commits == 1
    assert len(bus.published) == 1


def test_prepared_replay_continues_with_one_authoritative_cas(tmp_path: Path) -> None:
    page_store = _PageStore(_context())
    coordinator, service, ledger_store = _coordinator(tmp_path, page_store)
    assert service.prepare(_binding_report(), _authorization(), ledger_store).prepared is True

    result = coordinator.apply(_binding_report(), _authorization())

    assert result.status == "application_applied_event_published"
    assert page_store.commits == 1


def test_prepared_generated_and_applied_promptbuilt_fail_closed(tmp_path: Path) -> None:
    generated = _context(PageState.GENERATED).model_copy(
        update={
            "artifacts": {
                "Generated": {"artifact_kind": "logical_output_asset", "output_asset_id": _OUTPUT}
            }
        }
    )
    generated_store = _PageStore(generated)
    coordinator, service, ledger_store = _coordinator(tmp_path / "prepared", generated_store)
    assert service.prepare(_binding_report(), _authorization(), ledger_store).prepared is True
    assert coordinator.apply(_binding_report(), _authorization()).code.endswith("PREPARED_GENERATED_AMBIGUOUS")

    prompt_store = _PageStore(_context())
    applied, service, ledger_store = _coordinator(tmp_path / "applied", prompt_store)
    prepared = service.prepare(_binding_report(), _authorization(), ledger_store)
    assert service.finalize(prepared.binding, _authoritative_commit_proof(prepared.binding), ledger_store).applied
    assert applied.apply(_binding_report(), _authorization()).code.endswith("APPLIED_PROMPT_BUILT_CONFLICT")


def test_cas_and_event_failures_preserve_frozen_boundaries(tmp_path: Path) -> None:
    failed_cas, service, store = _coordinator(tmp_path / "cas", _PageStore(_context(), commit_fails=True))
    cas = failed_cas.apply(_binding_report(), _authorization())
    assert cas.code.endswith("AUTHORITATIVE_CAS_FAILED")
    assert service.lookup_applied(_PROJECT, _PAGE, _OUTPUT, store).status == "blocked"

    page_store = _PageStore(_context())
    event_failed, service, store = _coordinator(
        tmp_path / "event", page_store, _RaisingEventBus()
    )
    event = event_failed.apply(_binding_report(), _authorization())
    assert event.status == "application_applied_event_failed"
    assert page_store.context.state == PageState.GENERATED
    assert service.lookup_applied(_PROJECT, _PAGE, _OUTPUT, store).applied is True


def test_finalize_failure_keeps_generated_prepared_and_suppresses_event(tmp_path: Path) -> None:
    page_store = _PageStore(_context())
    ledger_service = WorkflowApplicationLedgerService()
    durable_store = LocalWorkflowApplicationLedgerStore(tmp_path / "ledger")
    receipt_service = DurableApplicationCommitReceiptService()
    receipt_store = LocalDurableApplicationCommitReceiptStore(tmp_path / "receipt")
    coordinator = LocalFileExternalGeneratedApplicationCoordinator(
        StateMachine(),
        MemoryEventBus(),
        ledger_service,
        _FinalizeFailingLedgerStore(durable_store),  # type: ignore[arg-type]
        receipt_service,
        receipt_store,
        page_store,  # type: ignore[arg-type]
        fence_factory=lambda project_id, page_id: _Fence(),
    )

    result = coordinator.apply(_binding_report(), _authorization())

    assert result.status == "application_applied_ledger_finalize_failed"
    assert page_store.context.state == PageState.GENERATED
    assert page_store.commits == 1
    assert ledger_service.lookup_applied(_PROJECT, _PAGE, _OUTPUT, durable_store).status == "blocked"


def test_quality_gate_allows_only_an_exact_applied_logical_output_proof(tmp_path: Path) -> None:
    service = WorkflowApplicationLedgerService()
    ledger_store = LocalWorkflowApplicationLedgerStore(tmp_path / "ledger")
    prepared = service.prepare(_binding_report(), _authorization(), ledger_store)
    assert prepared.binding is not None
    assert service.finalize(
        prepared.binding, _authoritative_commit_proof(prepared.binding), ledger_store
    ).applied
    context = _context(PageState.GENERATED).model_copy(
        update={
            "artifacts": {
                "Generated": {"artifact_kind": "logical_output_asset", "output_asset_id": _OUTPUT}
            }
        }
    )
    quality_agent = _QualityAgent()
    engine = WorkflowEngine(
        state_machine=StateMachine(),
        event_bus=MemoryEventBus(),
        agents={PageState.QUALITY_CHECKED: quality_agent},
    )
    page_store = _PageStore(context)
    coordinator = DurableWorkflowExecutionCoordinator(
        engine,
        page_store,  # type: ignore[arg-type]
        fence_factory=lambda project_id, page_id: _Fence(),
        logical_output_asset_quality_gate=LocalFileLogicalOutputAssetQualityGate(
            service, ledger_store
        ),
    )

    result = coordinator.execute(_PROJECT, _PAGE, "quality")

    assert result.status == "transition_applied_event_published"
    assert quality_agent.calls == 1


def test_quality_gate_blocks_missing_or_prepared_proof_before_agent(tmp_path: Path) -> None:
    service = WorkflowApplicationLedgerService()
    ledger_store = LocalWorkflowApplicationLedgerStore(tmp_path / "ledger")
    context = _context(PageState.GENERATED).model_copy(
        update={
            "artifacts": {
                "Generated": {"artifact_kind": "logical_output_asset", "output_asset_id": _OUTPUT}
            }
        }
    )
    quality_agent = _QualityAgent()
    engine = WorkflowEngine(
        state_machine=StateMachine(),
        event_bus=MemoryEventBus(),
        agents={PageState.QUALITY_CHECKED: quality_agent},
    )
    coordinator = DurableWorkflowExecutionCoordinator(
        engine,
        _PageStore(context),  # type: ignore[arg-type]
        fence_factory=lambda project_id, page_id: _Fence(),
        logical_output_asset_quality_gate=LocalFileLogicalOutputAssetQualityGate(
            service, ledger_store
        ),
    )

    result = coordinator.execute(_PROJECT, _PAGE, "quality")

    assert result.code == "LOGICAL_OUTPUT_ASSET_QUALITY_PROOF_UNAVAILABLE"
    assert quality_agent.calls == 0


def test_legacy_image_path_quality_remains_ungated(tmp_path: Path) -> None:
    context = _context(PageState.GENERATED).model_copy(
        update={"artifacts": {"Generated": {"image_path": "legacy.png"}}}
    )
    quality_agent = _QualityAgent()
    engine = WorkflowEngine(
        state_machine=StateMachine(),
        event_bus=MemoryEventBus(),
        agents={PageState.QUALITY_CHECKED: quality_agent},
    )
    coordinator = DurableWorkflowExecutionCoordinator(
        engine,
        _PageStore(context),  # type: ignore[arg-type]
        fence_factory=lambda project_id, page_id: _Fence(),
        logical_output_asset_quality_gate=LocalFileLogicalOutputAssetQualityGate(
            WorkflowApplicationLedgerService(),
            LocalWorkflowApplicationLedgerStore(tmp_path / "ledger"),
        ),
    )

    result = coordinator.execute(_PROJECT, _PAGE, "quality")

    assert result.status == "transition_applied_event_published"
    assert quality_agent.calls == 1


def test_private_composition_exposes_one_gate_and_coordinator(tmp_path: Path) -> None:
    repository = LocalFileRepository(tmp_path)
    composition = build_localfile_external_generation_composition(
        repository, StateMachine(), MemoryEventBus()
    )

    assert composition.ledger_store is not None
    assert composition.quality_gate is not None
    assert composition.external_application is not None
    assert composition.external_application._r25_localfile_composition is not None
