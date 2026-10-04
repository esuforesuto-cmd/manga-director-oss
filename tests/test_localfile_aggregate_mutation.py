from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from manga_director.domain.events import EventType, WorkflowEvent
from manga_director.domain.project import Chapter, Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.events import MemoryEventBus
from manga_director.repositories.local_file_durability import (
    ConditionalCommitResult,
    RevisionedProjectSnapshot,
    StaleRevisionError,
)
from manga_director.workflow.batch_contracts import (
    BatchRecord,
    BatchStatus,
    ExecutionPolicyName,
    QueueItem,
    QueueItemStatus,
)
from manga_director.workflow.localfile_aggregate_mutation import (
    BatchCompleteMutation,
    BatchCreateStartMutation,
    BatchPageResultMutation,
    BatchPauseMutation,
    BatchResumeMutation,
    BatchRetryMutation,
    ChapterLifecycleMutation,
    LocalFileAggregateMutationCoordinator,
    ProjectLifecycleMutation,
    ProjectStatusMutation,
)


@dataclass
class _FakeStore:
    project: Project
    stale: bool = False
    wrong_reread: bool = False
    commits: int = 0
    loads: int = 0
    raw_saves: int = 0

    def load_revisioned(self, project_id: str) -> RevisionedProjectSnapshot:
        assert project_id == self.project.id
        self.loads += 1
        return RevisionedProjectSnapshot(project=self.project, revision=self.loads, fingerprint="a" * 64)

    def conditional_commit(
        self, snapshot: RevisionedProjectSnapshot, project: Project
    ) -> ConditionalCommitResult:
        del snapshot
        self.commits += 1
        if self.stale:
            raise StaleRevisionError("stale")
        self.project = project
        return ConditionalCommitResult(revision=self.commits)

    def reread(self, project_id: str) -> Project:
        assert project_id == self.project.id
        if self.wrong_reread:
            return self.project.model_copy(update={"workflow": {}}, deep=True)
        return self.project


class _FailingBus(MemoryEventBus):
    def publish(self, events: list[WorkflowEvent]) -> None:
        del events
        raise RuntimeError("private event failure")


class _NthFailingBus(MemoryEventBus):
    def __init__(self, fail_on: int) -> None:
        super().__init__()
        self._fail_on = fail_on
        self.calls = 0

    def publish(self, events: list[WorkflowEvent]) -> None:
        self.calls += 1
        if self.calls == self._fail_on:
            raise RuntimeError("private event failure")
        super().publish(events)


class _FixedEvents:
    def create(self, event_type: EventType, data: dict[str, str]) -> WorkflowEvent:
        return WorkflowEvent(
            event_id=f"event-{event_type.value}",
            event_type=event_type,
            occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
            data=data,
        )


def _project(*, page_state: PageState = PageState.DRAFT) -> Project:
    return Project(
        id="demo",
        title="Demo",
        chapters=[Chapter(id="chapter-1", title="One", page_numbers=[1])],
        pages=[Page(page_number=1, state=page_state)],
        workflow={"batches": {}, "unrelated": {"preserve": True}},
    )


def _two_page_project() -> Project:
    return Project(
        id="demo",
        title="Demo",
        chapters=[Chapter(id="chapter-1", title="One", page_numbers=[1, 2])],
        pages=[Page(page_number=1), Page(page_number=2)],
        workflow={"batches": {}},
    )


def _record(*, item_status: QueueItemStatus = QueueItemStatus.PENDING) -> BatchRecord:
    return BatchRecord(
        id="batch-1",
        project_id="demo",
        policy=ExecutionPolicyName.SEQUENTIAL,
        queue=[QueueItem(page_number=1, chapter_id="chapter-1", status=item_status)],
    )


def _coordinator(store: _FakeStore, events: MemoryEventBus | None = None) -> LocalFileAggregateMutationCoordinator:
    return LocalFileAggregateMutationCoordinator(store, events or MemoryEventBus(), event_factory=_FixedEvents())


def _start(store: _FakeStore) -> None:
    receipt = _coordinator(store).mutate(BatchCreateStartMutation("demo", _record()))
    assert receipt.status == "mutation_applied_event_published"


def test_batch_closed_mutations_cover_start_result_complete_and_explicit_retry() -> None:
    store = _FakeStore(_project())
    _start(store)
    coordinator = _coordinator(store)

    complete = coordinator.mutate(BatchPageResultMutation("demo", "batch-1", 1, "completed"))
    finished = coordinator.mutate(BatchCompleteMutation("demo", "batch-1"))

    assert complete.status == "mutation_applied"
    assert finished.status == "mutation_applied_event_published"
    assert store.project.workflow["batches"]["batch-1"]["status"] == BatchStatus.COMPLETED.value

    retry_store = _FakeStore(_project())
    _start(retry_store)
    failed = _coordinator(retry_store).mutate(BatchPageResultMutation("demo", "batch-1", 1, "failed"))
    retry = _coordinator(retry_store).mutate(BatchRetryMutation("demo", "batch-1"))

    assert failed.status == "mutation_applied_event_published"
    assert retry.status == "mutation_applied"
    assert retry_store.project.workflow["batches"]["batch-1"]["queue"][0]["status"] == "pending"


def test_batch_resume_and_pause_publish_only_after_verified_cas() -> None:
    store = _FakeStore(_project())
    _start(store)
    events = MemoryEventBus()
    coordinator = _coordinator(store, events)

    resumed = coordinator.mutate(BatchResumeMutation("demo", "batch-1"))
    paused = coordinator.mutate(BatchPauseMutation("demo", "batch-1"))

    assert resumed.status == "mutation_applied_event_published"
    assert paused.status == "mutation_applied_event_published"
    assert [event.event_type for event in events.published] == [
        EventType.BATCH_RESUMED,
        EventType.BATCH_PAUSED,
    ]
    assert store.project.workflow["batches"]["batch-1"]["status"] == BatchStatus.PAUSED.value


def test_batch_resume_and_pause_fail_closed_after_stale_cas_without_events() -> None:
    seed = _FakeStore(_project())
    _start(seed)
    store = _FakeStore(seed.project, stale=True)
    events = MemoryEventBus()

    receipt = _coordinator(store, events).mutate(BatchResumeMutation("demo", "batch-1"))

    assert receipt.status == "stale_conflict"
    assert store.commits == 1
    assert events.published == []


def test_completed_batch_resume_is_a_true_noop_without_cas_or_event() -> None:
    store = _FakeStore(_project())
    _start(store)
    _coordinator(store).mutate(BatchPageResultMutation("demo", "batch-1", 1, "completed"))
    _coordinator(store).mutate(BatchCompleteMutation("demo", "batch-1"))
    commits_before = store.commits
    events = MemoryEventBus()

    receipt = _coordinator(store, events).mutate(BatchResumeMutation("demo", "batch-1"))

    assert receipt.status == "mutation_applied"
    assert receipt.code == "AGGREGATE_MUTATION_NOOP"
    assert store.commits == commits_before
    assert events.published == []


def test_resume_failed_only_preserves_failed_items_and_publishes_resumed_after_one_cas() -> None:
    store = _FakeStore(_project())
    _start(store)
    _coordinator(store).mutate(BatchPageResultMutation("demo", "batch-1", 1, "failed"))
    commits_before = store.commits
    events = MemoryEventBus()

    receipt = _coordinator(store, events).mutate(BatchResumeMutation("demo", "batch-1"))

    record = store.project.workflow["batches"]["batch-1"]
    assert receipt.status == "mutation_applied_event_published"
    assert receipt.resulting_status == BatchStatus.FAILED.value
    assert store.commits == commits_before + 1
    assert record["status"] == BatchStatus.FAILED.value
    assert record["queue"][0]["status"] == QueueItemStatus.FAILED.value
    assert record["queue"][0]["error"] == "BATCH_PAGE_EXECUTION_FAILED"
    assert [event.event_type for event in events.published] == [EventType.BATCH_RESUMED]


def test_resume_empty_noncompleted_commits_completed_then_publishes_bounded_event_sequence() -> None:
    store = _FakeStore(_project())
    empty = _record().model_copy(update={"id": "empty", "queue": []}, deep=True)
    _coordinator(store).mutate(BatchCreateStartMutation("demo", empty))
    commits_before = store.commits
    events = MemoryEventBus()

    receipt = _coordinator(store, events).mutate(BatchResumeMutation("demo", "empty"))

    assert receipt.status == "mutation_applied_event_published"
    assert receipt.resulting_status == BatchStatus.COMPLETED.value
    assert store.commits == commits_before + 1
    assert store.project.workflow["batches"]["empty"]["status"] == BatchStatus.COMPLETED.value
    assert [event.event_type for event in events.published] == [
        EventType.BATCH_RESUMED,
        EventType.BATCH_COMPLETED,
    ]


def test_resume_empty_noncompleted_first_event_failure_does_not_attempt_second_event() -> None:
    store = _FakeStore(_project())
    empty = _record().model_copy(update={"id": "empty", "queue": []}, deep=True)
    _coordinator(store).mutate(BatchCreateStartMutation("demo", empty))
    events = _NthFailingBus(1)

    receipt = _coordinator(store, events).mutate(BatchResumeMutation("demo", "empty"))

    assert receipt.status == "mutation_applied_event_failed"
    assert receipt.event_published is False
    assert events.calls == 1
    assert events.published == []
    assert store.project.workflow["batches"]["empty"]["status"] == BatchStatus.COMPLETED.value


def test_resume_empty_noncompleted_second_event_failure_preserves_first_event() -> None:
    store = _FakeStore(_project())
    empty = _record().model_copy(update={"id": "empty", "queue": []}, deep=True)
    _coordinator(store).mutate(BatchCreateStartMutation("demo", empty))
    events = _NthFailingBus(2)

    receipt = _coordinator(store, events).mutate(BatchResumeMutation("demo", "empty"))

    assert receipt.status == "mutation_applied_event_failed"
    assert receipt.event_published is True
    assert events.calls == 2
    assert [event.event_type for event in events.published] == [EventType.BATCH_RESUMED]
    assert store.project.workflow["batches"]["empty"]["status"] == BatchStatus.COMPLETED.value


def test_project_status_persists_position_only_without_refresh_or_event() -> None:
    store = _FakeStore(_project(page_state=PageState.APPROVED))
    events = MemoryEventBus()

    receipt = _coordinator(store, events).mutate(ProjectStatusMutation("demo"))

    assert receipt.status == "mutation_applied"
    assert receipt.event_published is False
    assert events.published == []
    assert store.project.workflow.get("history", []) == []
    assert store.project.workflow["current_chapter"] == "chapter-1"
    assert store.project.workflow["current_page"] is None


def test_project_status_normalises_only_existing_default_chapter_and_preserves_data() -> None:
    project = Project(
        id="demo",
        title="Demo",
        pages=[Page(page_number=1)],
        workflow={"batches": {}, "unrelated": {"preserve": True}},
    )
    store = _FakeStore(project)

    receipt = _coordinator(store).mutate(ProjectStatusMutation("demo"))

    assert receipt.status == "mutation_applied"
    assert store.project.chapters[0].id == "chapter-1"
    assert store.project.workflow["unrelated"] == {"preserve": True}


def test_deferred_logical_output_is_bounded_failed_batch_outcome() -> None:
    store = _FakeStore(_project(page_state=PageState.GENERATED))
    _start(store)

    receipt = _coordinator(store).mutate(BatchPageResultMutation("demo", "batch-1", 1, "deferred"))
    record = store.project.workflow["batches"]["batch-1"]

    assert receipt.status == "mutation_applied_event_published"
    assert record["status"] == BatchStatus.FAILED.value
    assert record["queue"][0]["error"] == "LOGICAL_OUTPUT_ASSET_QUALITY_GATING_DEFERRED"
    assert store.project.page(1).state == PageState.GENERATED


def test_project_and_chapter_lifecycle_mutations_preserve_unrelated_aggregate_state() -> None:
    store = _FakeStore(_project())
    coordinator = _coordinator(store)

    started = coordinator.mutate(ProjectLifecycleMutation("demo", "start"))
    chapter_started = coordinator.mutate(ChapterLifecycleMutation("demo", "chapter-1", "start"))
    page_recorded = coordinator.mutate(
        ChapterLifecycleMutation("demo", "chapter-1", "record_page", page_number=1)
    )
    refreshed = coordinator.mutate(ProjectLifecycleMutation("demo", "refresh"))

    assert [item.status for item in (started, chapter_started, page_recorded, refreshed)] == [
        "mutation_applied_event_published",
        "mutation_applied_event_published",
        "mutation_applied",
        "mutation_applied",
    ]
    assert store.project.workflow["unrelated"] == {"preserve": True}
    assert store.project.chapter("chapter-1").metadata["current_page"] == 1


def test_chapter_and_project_completion_use_existing_lifecycle_events() -> None:
    store = _FakeStore(_project(page_state=PageState.APPROVED))
    coordinator = _coordinator(store)

    chapter = coordinator.mutate(ChapterLifecycleMutation("demo", "chapter-1", "refresh"))
    project = coordinator.mutate(ProjectLifecycleMutation("demo", "refresh"))

    assert chapter.status == "mutation_applied_event_published"
    assert project.status == "mutation_applied_event_published"
    assert store.project.chapter("chapter-1").history[-1]["event"] == EventType.CHAPTER_COMPLETED.value
    assert store.project.workflow["history"][-1]["event"] == EventType.PROJECT_COMPLETED.value


def test_every_mutation_loads_a_new_snapshot_and_uses_exactly_one_cas() -> None:
    store = _FakeStore(_project())
    coordinator = _coordinator(store)

    coordinator.mutate(ProjectLifecycleMutation("demo", "start"))
    coordinator.mutate(ProjectLifecycleMutation("demo", "refresh"))

    assert store.loads == 2
    assert store.commits == 2
    assert store.raw_saves == 0


def test_stale_conflict_has_no_event_retry_or_raw_save_and_preserves_prior_page() -> None:
    store = _FakeStore(_project(page_state=PageState.DESIGNED), stale=True)
    _start_store = _FakeStore(_project(page_state=PageState.DESIGNED))
    _start(_start_store)
    store.project = _start_store.project
    events = MemoryEventBus()

    receipt = _coordinator(store, events).mutate(BatchPageResultMutation("demo", "batch-1", 1, "completed"))

    assert receipt.status == "stale_conflict"
    assert store.commits == 1
    assert events.published == []
    assert store.raw_saves == 0
    assert store.project.page(1).state == PageState.DESIGNED


def test_overlapping_batches_remain_nonexclusive_while_each_record_is_independent() -> None:
    store = _FakeStore(_project())
    first = _record()
    second = first.model_copy(update={"id": "batch-2"}, deep=True)
    _coordinator(store).mutate(BatchCreateStartMutation("demo", first))
    _coordinator(store).mutate(BatchCreateStartMutation("demo", second))

    first_result = _coordinator(store).mutate(BatchPageResultMutation("demo", "batch-1", 1, "completed"))
    second_result = _coordinator(store).mutate(BatchPageResultMutation("demo", "batch-2", 1, "completed"))

    assert first_result.status == "mutation_applied"
    assert second_result.status == "mutation_applied"
    assert store.project.workflow["batches"]["batch-1"]["queue"][0]["status"] == "completed"
    assert store.project.workflow["batches"]["batch-2"]["queue"][0]["status"] == "completed"


def test_different_page_conflict_is_one_cas_attempt_without_automatic_replay() -> None:
    store = _FakeStore(_two_page_project())
    record = BatchRecord(
        id="batch-1",
        project_id="demo",
        policy=ExecutionPolicyName.SEQUENTIAL,
        queue=[QueueItem(page_number=2, chapter_id="chapter-1")],
    )
    _coordinator(store).mutate(BatchCreateStartMutation("demo", record))
    store.stale = True

    receipt = _coordinator(store).mutate(BatchPageResultMutation("demo", "batch-1", 2, "completed"))

    assert receipt.status == "stale_conflict"
    assert store.commits == 2
    assert store.loads == 2


def test_post_commit_verification_failure_publishes_no_event() -> None:
    store = _FakeStore(_project(), wrong_reread=True)
    events = MemoryEventBus()

    receipt = _coordinator(store, events).mutate(ProjectLifecycleMutation("demo", "start"))

    assert receipt.status == "post_commit_verification_failed"
    assert events.published == []
    assert store.commits == 1


def test_event_failure_preserves_the_verified_commit_without_republish() -> None:
    store = _FakeStore(_project())

    receipt = _coordinator(store, _FailingBus()).mutate(ProjectLifecycleMutation("demo", "start"))

    assert receipt.status == "mutation_applied_event_failed"
    assert store.project.workflow["history"][0]["event"] == EventType.PROJECT_STARTED.value
    assert store.commits == 1


@pytest.mark.parametrize(
    "mutation_request",
    [
        BatchPageResultMutation(" demo", "batch-1", 1, "completed"),
        ChapterLifecycleMutation("demo", "chapter-1", "record_page"),
    ],
)
def test_malformed_closed_requests_fail_before_snapshot_or_cas(mutation_request: object) -> None:
    store = _FakeStore(_project())

    receipt = _coordinator(store).mutate(mutation_request)  # type: ignore[arg-type]

    assert receipt.status == "invalid_mutation_precondition"
    assert store.loads == 0
    assert store.commits == 0
