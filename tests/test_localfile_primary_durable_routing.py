from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from manga_director.cli import app as cli_app
from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState, StateMachine
from manga_director.events import MemoryEventBus
from manga_director.mcp.application import MangaApplicationService
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.repositories.project_loader import ProjectLoader
from manga_director.workflow.contracts import AgentResult, WorkflowContext
from manga_director.workflow.durable_execution import (
    DurableWorkflowExecutionCoordinator,
    LocalFileDurablePageStore,
    _DurableRoutingError,
    _DurableRunRoutingError,
    _route_localfile_primary,
    _route_localfile_run,
)
from manga_director.workflow.engine import WorkflowEngine


class RecordingAgent:
    def __init__(self, state: PageState) -> None:
        self.state = state
        self.calls = 0
        self.inputs: list[WorkflowContext] = []

    def execute(self, context: WorkflowContext) -> AgentResult:
        self.calls += 1
        self.inputs.append(context)
        return AgentResult(success=True, state=self.state, payload={"state": self.state.value})


class FailingEventBus(MemoryEventBus):
    def publish(self, events: list[object]) -> None:
        raise RuntimeError("private event publication failure")


class FailingAgent(RecordingAgent):
    def execute(self, context: WorkflowContext) -> AgentResult:
        self.calls += 1
        self.inputs.append(context)
        raise RuntimeError("private agent failure")


class NthFailingEventBus(MemoryEventBus):
    def __init__(self, fail_on_call: int) -> None:
        super().__init__()
        self.calls = 0
        self._fail_on_call = fail_on_call

    def publish(self, events: list[object]) -> None:
        self.calls += 1
        if self.calls == self._fail_on_call:
            raise RuntimeError("private event publication failure")
        super().publish(events)


class CountingFence:
    def __init__(self) -> None:
        self.acquire_calls = 0
        self.release_calls = 0

    def acquire(self) -> None:
        self.acquire_calls += 1

    def release(self) -> None:
        self.release_calls += 1


def _repository(tmp_path: Path) -> LocalFileRepository:
    repository = LocalFileRepository(tmp_path)
    repository.save(Project(id="routing-demo", title="Routing", pages=[Page(page_number=1)]))
    return repository


def _engine(bus: MemoryEventBus, agents: dict[PageState, RecordingAgent]) -> WorkflowEngine:
    return WorkflowEngine(state_machine=StateMachine(), event_bus=bus, agents=agents)


def _agents() -> dict[PageState, RecordingAgent]:
    return {state: RecordingAgent(state) for state in list(PageState)[1:]}


def test_localfile_route_applies_every_primary_command_with_exact_published_event(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    bus = MemoryEventBus()
    agents = _agents()
    engine = _engine(bus, agents)
    commands: list[tuple[str, dict[str, Any], PageState]] = [
        ("design", {"page_design": {"purpose": "Fresh purpose"}}, PageState.DESIGNED),
        ("review", {}, PageState.REVIEWED),
        ("storyboard", {}, PageState.STORYBOARDED),
        ("prompt", {}, PageState.PROMPT_BUILT),
        ("generate", {}, PageState.GENERATED),
        ("quality", {"quality_scores": {"composition": 5}}, PageState.QUALITY_CHECKED),
        ("approve", {"approved_by": "editor"}, PageState.APPROVED),
    ]

    for command, overlay, expected_state in commands:
        result = _route_localfile_primary(engine, repository, "routing-demo", "1", command, overlay)
        assert result.current_state == expected_state
        assert result.events == [bus.published[-1]]
        assert result.events[0] is bus.published[-1]

    assert agents[PageState.DESIGNED].inputs[0].metadata["page_design"]["purpose"] == "Fresh purpose"
    assert agents[PageState.QUALITY_CHECKED].inputs[0].metadata["quality_scores"] == {"composition": 5}
    assert agents[PageState.APPROVED].inputs[0].metadata["approved_by"] == "editor"


def test_overlay_rejects_unknown_or_identity_state_and_artifact_mutation_before_agent(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    bus = MemoryEventBus()
    agents = _agents()
    engine = _engine(bus, agents)
    invalid = (
        {"unknown": True},
        {"project_id": "other"},
        {"state": "Approved"},
        {"artifacts": {}},
    )

    for overlay in invalid:
        with pytest.raises(_DurableRoutingError):
            _route_localfile_primary(engine, repository, "routing-demo", "1", "design", overlay)

    assert agents[PageState.DESIGNED].calls == 0
    assert bus.published == []
    assert repository.load("routing-demo").page(1).state == PageState.DRAFT


def test_overlay_input_is_not_mutated_and_conflicting_authoritative_metadata_blocks(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    agents = _agents()
    engine = _engine(MemoryEventBus(), agents)
    supplied = {"page_design": {"purpose": "Caller-owned"}}

    _route_localfile_primary(engine, repository, "routing-demo", "1", "design", supplied)

    assert supplied == {"page_design": {"purpose": "Caller-owned"}}
    stale = {"page_design": {"purpose": "Different"}}
    with pytest.raises(_DurableRoutingError):
        _route_localfile_primary(engine, repository, "routing-demo", "1", "review", stale)


def test_receipt_exposes_only_the_exact_event_published_after_commit(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    bus = MemoryEventBus()
    coordinator = DurableWorkflowExecutionCoordinator(
        _engine(bus, _agents()), LocalFileDurablePageStore(repository)
    )

    receipt = coordinator._execute_with_receipt(
        "routing-demo", "1", "design", {"page_design": {"purpose": "Receipt"}}
    )

    assert receipt.outcome.status == "transition_applied_event_published"
    assert receipt.workflow_result is not None
    assert receipt.canonical_event is receipt.workflow_result.events[0]
    assert receipt.canonical_event is bus.published[0]


def test_event_failure_keeps_committed_state_without_receipt_success_or_republish(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    agents = _agents()
    coordinator = DurableWorkflowExecutionCoordinator(
        _engine(FailingEventBus(), agents), LocalFileDurablePageStore(repository)
    )

    receipt = coordinator._execute_with_receipt(
        "routing-demo", "1", "design", {"page_design": {"purpose": "Event failure"}}
    )

    assert receipt.outcome.status == "transition_applied_event_failed"
    assert receipt.workflow_result is None
    assert receipt.canonical_event is None
    assert repository.load("routing-demo").page(1).state == PageState.DESIGNED
    assert agents[PageState.DESIGNED].calls == 1


def test_cli_primary_commands_select_localfile_durable_route_without_changing_run_or_support(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository(tmp_path)
    engine = _engine(MemoryEventBus(), _agents())
    runtime = SimpleNamespace(loader=ProjectLoader(repository), engine=engine)
    monkeypatch.setattr(cli_app, "_use_runtime", lambda _path, action, **_kwargs: action(runtime))

    cli_app._execute_primary("design", "routing-demo", "1", tmp_path / "config.yaml", {"page_design": {}})
    cli_app._execute_primary("review", "routing-demo", "1", tmp_path / "config.yaml")

    assert repository.load("routing-demo").page(1).state == PageState.REVIEWED


def test_mcp_primary_and_approval_use_localfile_durable_route(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    loader = ProjectLoader(repository)
    engine = _engine(MemoryEventBus(), _agents())
    service = MangaApplicationService(engine, SimpleNamespace(), loader, repository)

    service.execute_page("design", "routing-demo", 1, {"page_design": {}})
    service.execute_page("review", "routing-demo", 1, {})
    service.execute_page("storyboard", "routing-demo", 1, {})
    service.execute_page("prompt", "routing-demo", 1, {})
    service.execute_page("generate", "routing-demo", 1, {})
    service.execute_page("quality", "routing-demo", 1, {"quality_scores": {}})
    result = service.approve_page("routing-demo", 1, "editor", {})

    assert result.current_state == PageState.APPROVED


def test_localfile_durable_run_uses_fresh_step_fences_and_reaches_quality_checked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository(tmp_path)
    bus = MemoryEventBus()
    agents = _agents()
    engine = _engine(bus, agents)
    fences: list[CountingFence] = []
    original_load = repository._load_revisioned
    original_commit = repository._conditional_commit
    loads = 0
    commits = 0

    def load(project_id: str):
        nonlocal loads
        loads += 1
        return original_load(project_id)

    def commit(snapshot, project):
        nonlocal commits
        commits += 1
        return original_commit(snapshot, project)

    monkeypatch.setattr(repository, "_load_revisioned", load)
    monkeypatch.setattr(repository, "_conditional_commit", commit)

    result = _route_localfile_run(
        engine,
        repository,
        "routing-demo",
        "1",
        fence_factory=lambda _project, _page: fences.append(CountingFence()) or fences[-1],
    )

    assert result.current_state == PageState.QUALITY_CHECKED
    assert loads == 13  # one fresh load and one verification load per committed step, then stop load
    assert commits == len(bus.published) == 6
    assert len(fences) == 7
    assert all(fence.acquire_calls == fence.release_calls == 1 for fence in fences)
    assert agents[PageState.APPROVED].calls == 0
    assert agents[PageState.GENERATED].calls == 1


def test_localfile_durable_run_stops_on_later_agent_failure_without_rolling_back(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    bus = MemoryEventBus()
    agents = _agents()
    agents[PageState.STORYBOARDED] = FailingAgent(PageState.STORYBOARDED)

    with pytest.raises(_DurableRunRoutingError, match="DURABLE_RUN_PARTIAL_PROGRESS"):
        _route_localfile_run(_engine(bus, agents), repository, "routing-demo", "1")

    assert repository.load("routing-demo").page(1).state == PageState.REVIEWED
    assert len(bus.published) == 2
    assert agents[PageState.DESIGNED].calls == agents[PageState.REVIEWED].calls == 1
    assert agents[PageState.STORYBOARDED].calls == 1


def test_localfile_durable_run_stops_after_cas_conflict_without_agent_rerun(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository(tmp_path)
    bus = MemoryEventBus()
    agents = _agents()
    engine = _engine(bus, agents)
    original_commit = repository._conditional_commit
    calls = 0

    def commit(snapshot, project):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("private stale revision")
        return original_commit(snapshot, project)

    monkeypatch.setattr(repository, "_conditional_commit", commit)

    with pytest.raises(_DurableRunRoutingError, match="AUTHORITATIVE_CAS_FAILED"):
        _route_localfile_run(engine, repository, "routing-demo", "1")

    assert calls == 2
    assert repository.load("routing-demo").page(1).state == PageState.DESIGNED
    assert len(bus.published) == 1
    assert agents[PageState.REVIEWED].calls == 1


def test_localfile_durable_run_stops_after_event_failure_with_committed_state(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    bus = NthFailingEventBus(fail_on_call=3)
    agents = _agents()

    with pytest.raises(_DurableRunRoutingError, match="POST_COMMIT_EVENT_PUBLICATION_FAILED"):
        _route_localfile_run(_engine(bus, agents), repository, "routing-demo", "1")

    assert repository.load("routing-demo").page(1).state == PageState.STORYBOARDED
    assert len(bus.published) == 2
    assert bus.calls == 3
    assert agents[PageState.PROMPT_BUILT].calls == 0


def test_localfile_durable_run_noops_from_quality_checked_and_approved(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    agents = _agents()
    engine = _engine(MemoryEventBus(), agents)

    _route_localfile_run(engine, repository, "routing-demo", "1")
    quality_result = _route_localfile_run(engine, repository, "routing-demo", "1")
    _route_localfile_primary(engine, repository, "routing-demo", "1", "approve", {"approved_by": "editor"})
    approved_result = _route_localfile_run(engine, repository, "routing-demo", "1")

    assert quality_result.current_state == PageState.QUALITY_CHECKED
    assert approved_result.current_state == PageState.APPROVED
    assert agents[PageState.APPROVED].calls == 1


def test_logical_output_asset_blocks_run_before_quality_agent(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    agents = _agents()
    engine = _engine(MemoryEventBus(), agents)

    for command in ("design", "review", "storyboard", "prompt", "generate"):
        _route_localfile_primary(engine, repository, "routing-demo", "1", command, {})
    snapshot = repository._load_revisioned("routing-demo")
    page = snapshot.project.page(1).model_copy(
        update={"image": {"artifact_kind": "logical_output_asset", "output_asset_id": "asset:001"}}
    )
    repository._conditional_commit(snapshot, snapshot.project.replace_page(page))

    with pytest.raises(_DurableRunRoutingError, match="LOGICAL_OUTPUT_ASSET_QUALITY_GATING_DEFERRED"):
        _route_localfile_run(engine, repository, "routing-demo", "1")

    assert agents[PageState.QUALITY_CHECKED].calls == 0
    assert repository.load("routing-demo").page(1).state == PageState.GENERATED
