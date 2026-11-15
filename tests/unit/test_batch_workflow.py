from __future__ import annotations

from unittest.mock import Mock

import pytest

from manga_director.domain.events import EventType
from manga_director.domain.exceptions import WorkflowError
from manga_director.domain.project import Chapter, Page, Project
from manga_director.domain.state_machine import PageState, StateMachine
from manga_director.events import MemoryEventBus
from manga_director.repositories import InMemoryRepository, ProjectLoader
from manga_director.workflow import (
    AutoExecution,
    BatchWorkflowEngine,
    ExecutionPlanner,
    InMemoryExecutionQueue,
    ParallelExecution,
    QueueItem,
    QueueItemStatus,
    SequentialExecution,
    WorkflowContext,
    WorkflowEngine,
    WorkflowResult,
    WorkflowWorker,
)


class ContextStore:
    def __init__(self) -> None:
        self.contexts = {
            page_number: WorkflowContext(page={"page_id": str(page_number)})
            for page_number in [1, 2, 3]
        }

    def load(self, project_id: str, page_id: str) -> WorkflowContext:
        del project_id
        return self.contexts[int(page_id)]

    def save(self, project_id: str, page_id: str, context: WorkflowContext) -> None:
        del project_id
        self.contexts[int(page_id)] = context


class RecordingWorker:
    def __init__(self, fail_page: int | None = None) -> None:
        self.calls: list[int] = []
        self.fail_page = fail_page

    def run(self, page_context: WorkflowContext) -> WorkflowResult:
        page_number = int(page_context.page["page_id"])
        self.calls.append(page_number)
        if self.fail_page == page_number:
            raise RuntimeError(f"page {page_number} failed")
        context = page_context.model_copy(update={"state": PageState.QUALITY_CHECKED}, deep=True)
        return WorkflowResult(
            current_state=PageState.QUALITY_CHECKED,
            completed_step=PageState.QUALITY_CHECKED,
            context=context,
        )


def _project() -> Project:
    return Project(
        id="demo",
        title="Demo",
        chapters=[
            Chapter(id="chapter-1", title="One", page_numbers=[2, 1]),
            Chapter(id="chapter-2", title="Two", page_numbers=[3]),
        ],
        pages=[Page(page_number=1), Page(page_number=2), Page(page_number=3)],
    )


def _engine(repository: InMemoryRepository, worker: RecordingWorker) -> BatchWorkflowEngine:
    return BatchWorkflowEngine(repository, ContextStore(), worker, MemoryEventBus())


def test_execution_planner_orders_pages_and_records_dependencies() -> None:
    plan = ExecutionPlanner().plan(_project(), SequentialExecution(), batch_id="batch-1")

    assert [item.page_number for item in plan.queue] == [1, 2, 3]
    assert [item.dependencies for item in plan.queue] == [[], [1], [2]]


def test_execution_queue_is_fifo_and_clearable() -> None:
    queue = InMemoryExecutionQueue()
    first = QueueItem(page_number=1, chapter_id="chapter-1")
    second = QueueItem(page_number=2, chapter_id="chapter-1")
    queue.enqueue(first)
    queue.enqueue(second)

    assert queue.peek() == first
    assert queue.dequeue() == first
    assert queue.size() == 1
    queue.clear()
    assert queue.dequeue() is None


@pytest.mark.parametrize("policy", [ParallelExecution(), AutoExecution()])
def test_only_sequential_policy_is_executable(policy: ParallelExecution | AutoExecution) -> None:
    repository = InMemoryRepository()
    repository.save(_project())

    with pytest.raises(WorkflowError, match="not implemented"):
        _engine(repository, RecordingWorker()).run("demo", policy)


def test_batch_runs_pages_sequentially_and_persists_progress() -> None:
    repository = InMemoryRepository()
    repository.save(_project())
    worker = RecordingWorker()
    events = MemoryEventBus()
    engine = BatchWorkflowEngine(repository, ContextStore(), worker, events)

    result = engine.run("demo", batch_id="batch-1")

    assert result.success is True
    assert result.completed == [1, 2, 3]
    assert result.statistics.total == 3
    assert result.progress.completed == 3
    assert result.checkpoint.completed_pages == [1, 2, 3]
    assert worker.calls == [1, 2, 3]
    persisted = repository.load("demo").workflow["batches"]["batch-1"]
    assert persisted["policy"] == "sequential"
    assert [event.event_type for event in events.published] == [
        EventType.BATCH_STARTED,
        EventType.BATCH_COMPLETED,
    ]


def test_resume_skips_completed_pages_and_retry_requeues_failed_pages_only() -> None:
    repository = InMemoryRepository()
    repository.save(_project())
    worker = RecordingWorker(fail_page=2)
    engine = _engine(repository, worker)

    failed = engine.run("demo", batch_id="batch-1")
    resumed = engine.resume("demo", "batch-1")
    worker.fail_page = None
    retried = engine.retry("demo", "batch-1")

    assert failed.failed == [2]
    assert resumed.completed == [1]
    assert worker.calls[:2] == [1, 2]
    assert worker.calls[2:] == [2, 3]
    assert worker.calls.count(1) == 1
    assert retried.completed == [1, 2, 3]
    assert retried.retry_summary.requeued_pages == [2]
    assert retried.skipped == []
    persisted = repository.load("demo").workflow["batches"]["batch-1"]
    assert persisted["queue"][1]["status"] == QueueItemStatus.COMPLETED.value


def test_batch_rejects_saved_storyboard_authority_before_page_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = InMemoryRepository()
    project = _project()
    page = project.page(1).model_copy(
        update={
            "metadata": {
                "workflow_history": [{"nested": [{"_explicit_storyboard_input_authority": None}]}]
            }
        }
    )
    repository.save(project.replace_page(page))
    loader = ProjectLoader(repository)
    save_page = Mock(wraps=loader.save)
    monkeypatch.setattr(loader, "save", save_page)
    agent = Mock()
    agent.execute.side_effect = AssertionError("Page agent ran before metadata validation")
    events = MemoryEventBus()
    engine = WorkflowEngine(
        state_machine=StateMachine(), event_bus=events, agents={PageState.DESIGNED: agent}
    )
    batch = BatchWorkflowEngine(repository, loader, WorkflowWorker(engine), events)

    result = batch.run("demo", batch_id="batch-1")
    resumed = batch.resume("demo", "batch-1")
    retried = batch.retry("demo", "batch-1")

    agent.execute.assert_not_called()
    save_page.assert_not_called()
    assert repository.load("demo").page(1) == page
    assert result.failed == [1]
    assert result.completed == []
    assert resumed.failed == [1]
    assert retried.failed == [1]
    event_types = [event.event_type for event in events.published]
    assert EventType.BATCH_STARTED in event_types
    assert EventType.BATCH_FAILED in event_types
    persisted = repository.load("demo").workflow["batches"]["batch-1"]
    assert persisted["queue"][0]["error"] == "Reserved storyboard confirmation metadata is not accepted."
