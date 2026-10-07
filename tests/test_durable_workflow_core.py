from __future__ import annotations

import inspect
import os
import threading
import time
from collections.abc import Sequence
from multiprocessing import Event, get_context
from pathlib import Path
from typing import cast

import pytest

from manga_director.domain.events import WorkflowEvent
from manga_director.domain.exceptions import InvalidPageTransition
from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState, StateMachine
from manga_director.events.bus import EventBus, MemoryEventBus
from manga_director.repositories.local_file_durability import (
    ConditionalCommitResult,
    RevisionedProjectSnapshot,
    StaleRevisionError,
)
from manga_director.repositories.project_loader import ProjectLoader
from manga_director.workflow.contracts import AgentResult, WorkflowContext
from manga_director.workflow.durable_execution import (
    DurablePageStorePort,
    DurableWorkflowExecutionCoordinator,
    DurableWorkflowExecutionResult,
)
from manga_director.workflow.engine import WorkflowEngine
from manga_director.workflow.page_execution_fence import (
    PageExecutionFenceError,
    PageExecutionFencePort,
    WindowsPageExecutionFence,
    _mutex_identity,
)


class RecordingDesignAgent:
    def __init__(self, *, entered: threading.Event | None = None, release: threading.Event | None = None) -> None:
        self.calls = 0
        self._entered = entered
        self._release = release

    def execute(self, context: WorkflowContext) -> AgentResult:
        self.calls += 1
        if self._entered is not None:
            self._entered.set()
        if self._release is not None:
            assert self._release.wait(timeout=2)
        return AgentResult(success=True, state=PageState.DESIGNED, payload={"source": "fake"})


class InvalidEventAgent(RecordingDesignAgent):
    def execute(self, context: WorkflowContext) -> AgentResult:
        result = super().execute(context)
        extra = WorkflowEvent(event_type="page.designed", data={"unexpected": True})
        return result.model_copy(update={"events": [extra]})


class FailingAgent:
    def __init__(self) -> None:
        self.calls = 0

    def execute(self, context: WorkflowContext) -> AgentResult:
        self.calls += 1
        raise RuntimeError("private fake agent failure")


class InspectingEventBus(MemoryEventBus):
    def __init__(self, store: FakeDurablePageStore, *, fail: bool = False) -> None:
        super().__init__()
        self._store = store
        self._fail = fail
        self.calls = 0
        self.revision_seen_at_publish: int | None = None

    def publish(self, events: Sequence[WorkflowEvent]) -> None:
        self.calls += 1
        self.revision_seen_at_publish = self._store.revision
        if self._fail:
            raise RuntimeError("private fake publication failure")
        super().publish(events)


class SharedFence(PageExecutionFencePort):
    def __init__(self, lock: threading.Lock, *, timeout: float = 0.15) -> None:
        self._lock = lock
        self._timeout = timeout
        self._owned = False
        self.release_calls = 0

    def acquire(self) -> None:
        if self._owned:
            return
        if not self._lock.acquire(timeout=self._timeout):
            raise PageExecutionFenceError("page_execution_fence_contended")
        self._owned = True

    def release(self) -> None:
        self.release_calls += 1
        if self._owned:
            self._owned = False
            self._lock.release()


class FenceFactory:
    def __init__(self) -> None:
        self._locks: dict[tuple[str, str], threading.Lock] = {}
        self.created: list[SharedFence] = []

    def __call__(self, project_id: str, page_id: str) -> SharedFence:
        fence = SharedFence(self._locks.setdefault((project_id, page_id), threading.Lock()))
        self.created.append(fence)
        return fence


class FakeDurablePageStore(DurablePageStorePort):
    def __init__(self, project: Project) -> None:
        self.project = project
        self.revision = 1
        self.load_calls = 0
        self.context_calls = 0
        self.commit_calls = 0
        self.verify_calls = 0
        self.fail_commit = False
        self.fail_verify = False
        self._lock = threading.Lock()

    def load_revisioned(self, project_id: str) -> RevisionedProjectSnapshot:
        assert project_id == self.project.id
        with self._lock:
            self.load_calls += 1
            return RevisionedProjectSnapshot(
                project=self.project,
                revision=self.revision,
                fingerprint=f"private-{self.revision}",
            )

    def context_from_snapshot(
        self, snapshot: RevisionedProjectSnapshot, page_id: str
    ) -> WorkflowContext:
        self.context_calls += 1
        return ProjectLoader._context_from_page(snapshot.project, snapshot.project.page(int(page_id)))

    def project_from_context(
        self,
        snapshot: RevisionedProjectSnapshot,
        page_id: str,
        context: WorkflowContext,
    ) -> Project:
        page = ProjectLoader._page_from_context(snapshot.project.page(int(page_id)), context)
        return snapshot.project.replace_page(page)

    def conditional_commit(
        self, snapshot: RevisionedProjectSnapshot, project: Project
    ) -> ConditionalCommitResult:
        with self._lock:
            self.commit_calls += 1
            if self.fail_commit or snapshot.revision != self.revision:
                raise StaleRevisionError("private fake stale revision")
            self.project = project
            self.revision += 1
            return ConditionalCommitResult(revision=self.revision)

    def verify_committed(
        self, project_id: str, page_id: str, expected_project: Project
    ) -> bool:
        self.verify_calls += 1
        return not self.fail_verify and self.project.page(int(page_id)) == expected_project.page(int(page_id))


def _project(*page_numbers: int) -> Project:
    return Project(id="project:durable-core", title="Durable core", pages=[Page(page_number=n) for n in page_numbers])


def _engine(bus: EventBus, agent: object) -> WorkflowEngine:
    return WorkflowEngine(
        state_machine=StateMachine(),
        event_bus=bus,
        agents={PageState.DESIGNED: cast(RecordingDesignAgent, agent)},
    )


def _coordinator(
    store: FakeDurablePageStore,
    bus: InspectingEventBus,
    agent: object,
    fences: FenceFactory | None = None,
) -> DurableWorkflowExecutionCoordinator:
    return DurableWorkflowExecutionCoordinator(_engine(bus, agent), store, fence_factory=fences or FenceFactory())


def _hold_mutex(project_id: str, page_id: str, ready: Event) -> None:
    fence = WindowsPageExecutionFence(project_id, page_id)
    fence.acquire()
    ready.set()
    time.sleep(30)


@pytest.mark.skipif(os.name != "nt", reason="Windows named mutex contract")
def test_windows_fence_is_hashed_bounded_idempotent_and_released_after_holder_termination() -> None:
    project_id = "project:mutex"
    page_id = "page-token"
    identity = _mutex_identity(project_id, page_id)
    assert identity.startswith("Local\\MangaDirectorPageExecution-")
    assert project_id not in identity and page_id not in identity
    first = WindowsPageExecutionFence(project_id, page_id)
    first.acquire()
    second = WindowsPageExecutionFence(project_id, page_id, timeout_ms=20)
    with pytest.raises(PageExecutionFenceError):
        second.acquire()
    failures: list[BaseException] = []
    started = time.monotonic()

    def attempt_second_acquire() -> None:
        try:
            second.acquire()
        except BaseException as exc:  # test harness only
            failures.append(exc)

    contender = threading.Thread(target=attempt_second_acquire)
    contender.start()
    contender.join(timeout=1)
    assert time.monotonic() - started < 0.5
    assert len(failures) == 1 and isinstance(failures[0], PageExecutionFenceError)
    first.release()
    first.release()
    second.acquire()
    second.release()

    context = get_context("spawn")
    ready = context.Event()
    holder = context.Process(target=_hold_mutex, args=(project_id, "2", ready))
    holder.start()
    assert ready.wait(timeout=5)
    holder.terminate()
    holder.join(timeout=5)
    assert not holder.is_alive()
    recovered = WindowsPageExecutionFence(project_id, "2")
    recovered.acquire()
    recovered.release()


@pytest.mark.skipif(os.name == "nt", reason="Linux page fence fail-closed contract")
def test_linux_page_fence_rejects_before_repository_or_workflow_mutation() -> None:
    fence = WindowsPageExecutionFence("project:durable-core", "1")
    with pytest.raises(PageExecutionFenceError, match="page_execution_fence_unavailable"):
        fence.acquire()

    store = FakeDurablePageStore(_project(1))
    agent = RecordingDesignAgent()
    bus = InspectingEventBus(store)
    coordinator = DurableWorkflowExecutionCoordinator(_engine(bus, agent), store)

    result = coordinator.execute(store.project.id, "1", "design")

    assert result.code == "PAGE_EXECUTION_FENCE_UNAVAILABLE"
    assert agent.calls == 0
    assert store.load_calls == store.context_calls == store.commit_calls == store.verify_calls == 0
    assert bus.calls == len(bus.published) == 0


@pytest.mark.parametrize(
    ("project_id", "page_id", "timeout_ms"),
    (("", "1", 1_000), ("project", "", 1_000), ("project", "1", 0)),
)
def test_page_fence_constructor_validation_precedes_platform_rejection(
    project_id: str, page_id: str, timeout_ms: int
) -> None:
    with pytest.raises(ValueError):
        WindowsPageExecutionFence(project_id, page_id, timeout_ms=timeout_ms)


def test_durable_execution_commits_before_one_canonical_event_and_uses_authoritative_page() -> None:
    store = FakeDurablePageStore(_project(1))
    agent = RecordingDesignAgent()
    bus = InspectingEventBus(store)
    fences = FenceFactory()
    result = _coordinator(store, bus, agent, fences).execute(store.project.id, "1", "design")

    assert result.status == "transition_applied_event_published"
    assert result.event_published is True
    assert agent.calls == 1
    assert store.load_calls == store.context_calls == store.commit_calls == store.verify_calls == 1
    assert store.project.page(1).state == PageState.DESIGNED
    assert bus.calls == len(bus.published) == 1
    assert bus.revision_seen_at_publish == 2
    assert len(bus.published) == 1
    assert fences.created[0].release_calls == 1


def test_state_machine_and_agent_selection_are_reused_without_public_engine_change() -> None:
    store = FakeDurablePageStore(_project(1))
    agent = RecordingDesignAgent()
    bus = InspectingEventBus(store)
    coordinator = _coordinator(store, bus, agent)
    rejected = coordinator.execute(store.project.id, "1", "approve")
    assert rejected.code == "DURABLE_EXECUTION_FAILED"
    assert agent.calls == store.commit_calls == bus.calls == 0

    plain_bus = MemoryEventBus()
    plain_engine = _engine(plain_bus, agent)
    plain_execute_result = plain_engine.execute(WorkflowContext(page={"page_id": "1"}))
    assert plain_execute_result.current_state == PageState.DESIGNED
    result = plain_engine.execute_command(WorkflowContext(page={"page_id": "1"}), "design")
    assert result.current_state == PageState.DESIGNED
    assert len(plain_bus.published) == 2
    assert list(inspect.signature(WorkflowEngine.execute).parameters) == ["self", "context"]
    assert list(inspect.signature(WorkflowEngine.execute_command).parameters) == ["self", "context", "command"]
    assert list(inspect.signature(WorkflowEngine.run).parameters) == ["self", "context"]


def test_cas_failure_publishes_nothing_reruns_nothing_and_releases_fence() -> None:
    store = FakeDurablePageStore(_project(1))
    store.fail_commit = True
    agent = RecordingDesignAgent()
    bus = InspectingEventBus(store)
    fences = FenceFactory()
    result = _coordinator(store, bus, agent, fences).execute(store.project.id, "1", "design")

    assert result.status == "transition_not_applied"
    assert result.code == "AUTHORITATIVE_CAS_FAILED"
    assert agent.calls == store.commit_calls == 1
    assert bus.calls == len(bus.published) == 0
    assert store.project.page(1).state == PageState.DRAFT
    assert fences.created[0].release_calls == 1


def test_event_failure_keeps_committed_state_without_second_publication_and_releases_fence() -> None:
    store = FakeDurablePageStore(_project(1))
    agent = RecordingDesignAgent()
    bus = InspectingEventBus(store, fail=True)
    fences = FenceFactory()
    result = _coordinator(store, bus, agent, fences).execute(store.project.id, "1", "design")

    assert result.status == "transition_applied_event_failed"
    assert result.code == "POST_COMMIT_EVENT_PUBLICATION_FAILED"
    assert store.project.page(1).state == PageState.DESIGNED
    assert agent.calls == store.commit_calls == bus.calls == 1
    assert fences.created[0].release_calls == 1


def test_post_commit_verification_failure_never_publishes_and_releases_fence() -> None:
    store = FakeDurablePageStore(_project(1))
    store.fail_verify = True
    agent = RecordingDesignAgent()
    bus = InspectingEventBus(store)
    fences = FenceFactory()
    result = _coordinator(store, bus, agent, fences).execute(store.project.id, "1", "design")

    assert result.status == "transition_applied_event_failed"
    assert result.code == "AUTHORITATIVE_POST_COMMIT_VERIFICATION_FAILED"
    assert store.project.page(1).state == PageState.DESIGNED
    assert agent.calls == store.commit_calls == store.verify_calls == 1
    assert bus.calls == len(bus.published) == 0
    assert fences.created[0].release_calls == 1


def test_noncanonical_event_and_agent_failure_stop_before_cas_and_release_fence() -> None:
    for agent in (InvalidEventAgent(), FailingAgent()):
        store = FakeDurablePageStore(_project(1))
        bus = InspectingEventBus(store)
        fences = FenceFactory()
        result = _coordinator(store, bus, agent, fences).execute(store.project.id, "1", "design")
        assert result.status == "transition_not_applied"
        assert store.commit_calls == bus.calls == 0
        assert fences.created[0].release_calls == 1


def test_same_page_fence_stops_second_agent_before_it_can_execute() -> None:
    store = FakeDurablePageStore(_project(1))
    entered = threading.Event()
    release = threading.Event()
    agent = RecordingDesignAgent(entered=entered, release=release)
    bus = InspectingEventBus(store)
    fences = FenceFactory()
    coordinator = _coordinator(store, bus, agent, fences)
    results: list[DurableWorkflowExecutionResult] = []

    first = threading.Thread(target=lambda: results.append(coordinator.execute(store.project.id, "1", "design")))
    first.start()
    assert entered.wait(timeout=1)
    second = coordinator.execute(store.project.id, "1", "design")
    release.set()
    first.join(timeout=2)

    assert second.code == "PAGE_EXECUTION_FENCE_UNAVAILABLE"
    assert agent.calls == 1
    assert len(results) == 1


def test_different_pages_can_execute_then_one_stale_revision_fails_closed_without_rerun() -> None:
    store = FakeDurablePageStore(_project(1, 2))
    entered = threading.Event()
    release = threading.Event()
    agent = RecordingDesignAgent(entered=entered, release=release)
    bus = InspectingEventBus(store)
    coordinator = _coordinator(store, bus, agent, FenceFactory())
    results: list[DurableWorkflowExecutionResult] = []

    first = threading.Thread(target=lambda: results.append(coordinator.execute(store.project.id, "1", "design")))
    second = threading.Thread(target=lambda: results.append(coordinator.execute(store.project.id, "2", "design")))
    first.start()
    second.start()
    deadline = time.monotonic() + 1
    while agent.calls < 2 and time.monotonic() < deadline:
        time.sleep(0.01)
    assert agent.calls == 2
    release.set()
    first.join(timeout=2)
    second.join(timeout=2)

    statuses = {result.status for result in results}
    assert statuses == {"transition_applied_event_published", "transition_not_applied"}
    assert store.commit_calls == 2
    assert bus.calls == 1
    assert agent.calls == 2


def test_private_durable_modules_do_not_activate_public_routing_ledger_recovery_or_knowledge() -> None:
    root = Path(__file__).parents[1]
    durable_source = (root / "src" / "manga_director" / "workflow" / "durable_execution.py").read_text(
        encoding="utf-8"
    )
    exports = (root / "src" / "manga_director" / "workflow" / "__init__.py").read_text(encoding="utf-8")
    production_exports = (root / "src" / "manga_director" / "production" / "__init__.py").read_text(
        encoding="utf-8"
    )
    root_exports = (root / "src" / "manga_director" / "__init__.py").read_text(encoding="utf-8")
    repository_protocol = (root / "src" / "manga_director" / "repositories" / "protocols.py").read_text(
        encoding="utf-8"
    )
    for forbidden in (
        "next_generation_workflow_application_ledger",
        "WorkflowRecovery",
        "manga_director.cli",
        "manga_director.mcp",
        "manga_director.knowledge",
    ):
        assert forbidden not in durable_source
    assert "durable_execution" not in exports
    assert "durable_execution" not in production_exports
    assert "durable_execution" not in root_exports
    assert "conditional_commit" not in repository_protocol


def test_invalid_command_is_still_rejected_by_existing_state_machine() -> None:
    with pytest.raises(InvalidPageTransition):
        StateMachine().validate_command(PageState.DRAFT, "approve")
