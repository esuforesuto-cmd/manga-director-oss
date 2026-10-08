"""Linux-only proof that page-authority callers fail closed before mutation."""

from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from generation_admission_v1_fixtures import manifest

from manga_director.domain.state_machine import PageState, StateMachine
from manga_director.events import MemoryEventBus
from manga_director.production import future_localfile_durable_generation_boundary as local_d05
from manga_director.production.next_generation_durable_evidence_workflow_binding import (
    DurableEvidenceWorkflowBindingReport,
    WorkflowApplicationAuthorizationDTO,
)
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.workflow.durable_execution import _DurableRoutingError, _route_localfile_primary
from manga_director.workflow.engine import WorkflowEngine
from manga_director.workflow.localfile_external_generated_application import (
    build_localfile_external_generation_composition,
)
from manga_director.workflow.localfile_manual_reconciliation import (
    ManualReconciliationInputDTO,
    build_localfile_manual_reconciliation_composition,
)

linux_only = pytest.mark.skipif(
    os.name == "nt", reason="Linux page-authority fail-closed contract"
)


def _tree(root: Path) -> tuple[tuple[str, str], ...]:
    """Return durable bytes, including the absence of a durable root."""

    if not root.exists():
        return ()
    entries: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*")):
        relative = str(path.relative_to(root))
        if path.is_dir():
            entries.append((relative, "directory"))
        elif path.is_file():
            entries.append((relative, hashlib.sha256(path.read_bytes()).hexdigest()))
    return tuple(entries)


def _binding() -> tuple[DurableEvidenceWorkflowBindingReport, WorkflowApplicationAuthorizationDTO]:
    report = DurableEvidenceWorkflowBindingReport(
        attempt_id="attempt:linux-fail-closed",
        provider_reference="provider:linux-fail-closed",
        output_asset_id="asset:linux-fail-closed",
        project_id="project-linux-fail-closed",
        page_id="1",
        target_page_reference="page:linux-fail-closed",
        status="eligible",
        eligible=True,
    )
    authorization = WorkflowApplicationAuthorizationDTO(
        authorization_id="authorization:linux-fail-closed",
        authorizer_id="human:linux-fail-closed",
        authorized_at=datetime(2026, 10, 8, tzinfo=UTC),
        attempt_id=report.attempt_id,
        provider_reference=report.provider_reference,
        project_id=report.project_id,
        page_id=report.page_id,
        target_page_reference=report.target_page_reference,
        source_state="PromptBuilt",
        target_state="Generated",
    )
    return report, authorization


class _NoStateMachineMutation(StateMachine):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def validate_transition(self, from_state: PageState, to_state: PageState) -> None:
        self.calls += 1
        raise AssertionError("page fence must reject before StateMachine mutation")


class _NoAgent:
    def __init__(self) -> None:
        self.calls = 0

    def execute(self, context: object) -> object:
        del context
        self.calls += 1
        raise AssertionError("page fence must reject before an agent/provider call")


@linux_only
def test_linux_d05_admission_is_unavailable_before_attempt_or_provider_mutation(tmp_path: Path) -> None:
    repository = LocalFileRepository(tmp_path / "repository")
    admitted = manifest().model_copy(
        update={"project_id": "project-linux-d05", "attempt_id": "attempt-linux-d05", "page_id": "1"}
    )
    boundary = local_d05.LocalFileDurableGenerationBoundary(repository)
    assert boundary.reserve(admitted).code == "RESERVATION_RESERVED"
    before = _tree(repository._root)

    result = boundary.prepare_provider_start(admitted)

    assert result.eligibility == "BLOCKED"
    assert result.code == "FINAL_REVALIDATION_UNAVAILABLE"
    assert result.permit is None
    assert _tree(repository._root) == before
    assert boundary._core._store.lookup(admitted.attempt_id).attempt is not None


@linux_only
def test_linux_external_generated_application_is_unavailable_before_ledger_cas_event_or_r26_mutation(
    tmp_path: Path,
) -> None:
    repository = LocalFileRepository(tmp_path / "repository")
    state_machine = _NoStateMachineMutation()
    event_bus = MemoryEventBus()
    composition = build_localfile_external_generation_composition(repository, state_machine, event_bus)
    report, authorization = _binding()
    before = _tree(repository._root)

    result = composition.external_application.apply(report, authorization)

    assert result.status == "application_not_applied"
    assert result.code == "EXTERNAL_APPLICATION_PAGE_FENCE_UNAVAILABLE"
    assert state_machine.calls == 0
    assert event_bus.published == []
    assert composition.external_application._r26_active_fence_contexts == set()
    assert _tree(repository._root) == before


@linux_only
def test_linux_manual_reconciliation_is_unavailable_before_repository_ledger_receipt_or_r26_mutation(
    tmp_path: Path,
) -> None:
    repository = LocalFileRepository(tmp_path / "repository")
    report, authorization = _binding()
    composition = build_localfile_manual_reconciliation_composition(repository)
    before = _tree(repository._root)

    result = composition.coordinator.reconcile(
        ManualReconciliationInputDTO(binding_report=report, authorization=authorization)
    )

    assert result.status == "blocked"
    assert result.findings[0].code == "MANUAL_RECONCILIATION_PAGE_FENCE_UNAVAILABLE"
    assert result.reconciled is result.confirmed is False
    assert _tree(repository._root) == before


@linux_only
def test_linux_cli_durable_execution_is_unavailable_before_repository_state_event_or_provider_mutation(
    tmp_path: Path,
) -> None:
    repository = LocalFileRepository(tmp_path / "repository")
    event_bus = MemoryEventBus()
    agent = _NoAgent()
    engine = WorkflowEngine(
        state_machine=StateMachine(),
        event_bus=event_bus,
        agents={state: agent for state in list(PageState)[1:]},
    )
    before = _tree(repository._root)

    with pytest.raises(_DurableRoutingError, match="PAGE_EXECUTION_FENCE_UNAVAILABLE"):
        _route_localfile_primary(engine, repository, "project-linux-cli", "1", "design", {})

    assert agent.calls == 0
    assert event_bus.published == []
    assert _tree(repository._root) == before
