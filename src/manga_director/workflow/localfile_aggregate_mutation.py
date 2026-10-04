"""Private, revision-aware LocalFile aggregate lifecycle mutations.

This module deliberately does not route page execution.  It is the durable
aggregate companion for later delivery composition: each mutation works from a
fresh authoritative snapshot, has one conditional commit, and publishes an
existing lifecycle event only after targeted verification.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from manga_director.domain.events import EventType, WorkflowEvent
from manga_director.domain.project import Chapter, Project
from manga_director.domain.state_machine import PageState
from manga_director.events.bus import EventBus
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.repositories.local_file_durability import (
    ConditionalCommitResult,
    RevisionedProjectSnapshot,
    StaleRevisionError,
)
from manga_director.workflow.batch_contracts import (
    BatchRecord,
    BatchStatus,
    ExecutionStatistics,
    ProgressSnapshot,
    QueueItem,
    QueueItemStatus,
    ResumeCheckpoint,
    RetrySummary,
)

AggregateMutationStatus = Literal[
    "mutation_not_applied",
    "mutation_applied",
    "mutation_applied_event_published",
    "mutation_applied_event_failed",
    "stale_conflict",
    "malformed_authoritative_state",
    "invalid_mutation_precondition",
    "post_commit_verification_failed",
]
BatchPageOutcome = Literal["completed", "failed", "deferred"]
ProjectMutationOperation = Literal["start", "refresh"]
ChapterMutationOperation = Literal["start", "record_page", "refresh"]


@dataclass(frozen=True, slots=True)
class BatchCreateStartMutation:
    """Closed request for the existing batch create/start lifecycle action."""

    project_id: str
    record: BatchRecord


@dataclass(frozen=True, slots=True)
class BatchPageResultMutation:
    """Closed request for one persisted batch queue-item result."""

    project_id: str
    batch_id: str
    page_number: int
    outcome: BatchPageOutcome
    elapsed_time: float = 0.0


@dataclass(frozen=True, slots=True)
class BatchCompleteMutation:
    """Closed request for the existing batch completion action."""

    project_id: str
    batch_id: str
    elapsed_time: float = 0.0


@dataclass(frozen=True, slots=True)
class BatchRetryMutation:
    """Closed request for the existing explicit failed-page requeue action."""

    project_id: str
    batch_id: str


@dataclass(frozen=True, slots=True)
class BatchResumeMutation:
    """Closed request for the existing Batch resume lifecycle action."""

    project_id: str
    batch_id: str


@dataclass(frozen=True, slots=True)
class BatchPauseMutation:
    """Closed request for the existing Batch pause lifecycle action."""

    project_id: str
    batch_id: str


@dataclass(frozen=True, slots=True)
class ProjectLifecycleMutation:
    """Closed request for existing project start or refresh semantics."""

    project_id: str
    operation: ProjectMutationOperation


@dataclass(frozen=True, slots=True)
class ProjectStatusMutation:
    """Closed request for position-only project status persistence."""

    project_id: str


@dataclass(frozen=True, slots=True)
class ChapterLifecycleMutation:
    """Closed request for existing chapter lifecycle semantics."""

    project_id: str
    chapter_id: str
    operation: ChapterMutationOperation
    page_number: int | None = None


AggregateMutationRequest = (
    BatchCreateStartMutation
    | BatchPageResultMutation
    | BatchCompleteMutation
    | BatchRetryMutation
    | BatchResumeMutation
    | BatchPauseMutation
    | ProjectLifecycleMutation
    | ProjectStatusMutation
    | ChapterLifecycleMutation
)


@dataclass(frozen=True, slots=True)
class LocalFileAggregateMutationReceipt:
    """Private, redacted mutation result for later durable routing composition."""

    project_id: str
    target_kind: Literal["batch", "project", "chapter"]
    target_id: str
    status: AggregateMutationStatus
    code: str
    verified: bool
    event_published: bool
    resulting_status: str | None = None
    resulting_page: int | None = None


class LocalFileAggregateMutationStorePort(Protocol):
    """Private LocalFile aggregate operations; no public repository contract changes."""

    def load_revisioned(self, project_id: str) -> RevisionedProjectSnapshot: ...

    def conditional_commit(
        self, snapshot: RevisionedProjectSnapshot, project: Project
    ) -> ConditionalCommitResult: ...

    def reread(self, project_id: str) -> Project: ...


class LocalFileAggregateMutationStore(LocalFileAggregateMutationStorePort):
    """Private adapter over the established LocalFile revision/CAS primitives."""

    def __init__(self, repository: LocalFileRepository) -> None:
        self._repository = repository

    def load_revisioned(self, project_id: str) -> RevisionedProjectSnapshot:
        return self._repository._load_revisioned(project_id)

    def conditional_commit(
        self, snapshot: RevisionedProjectSnapshot, project: Project
    ) -> ConditionalCommitResult:
        return self._repository._conditional_commit(snapshot, project)

    def reread(self, project_id: str) -> Project:
        return self._repository._load_revisioned(project_id).project


class _LifecycleEventFactory(Protocol):
    def create(
        self, event_type: EventType, data: dict[str, str]
    ) -> WorkflowEvent: ...


class _ExistingLifecycleEventFactory:
    """Keep existing event ownership while allowing deterministic fake-only tests."""

    def create(self, event_type: EventType, data: dict[str, str]) -> WorkflowEvent:
        return WorkflowEvent(event_type=event_type, data=data)


class LocalFileAggregateMutationCoordinator:
    """Apply one closed LocalFile aggregate mutation without page execution."""

    def __init__(
        self,
        store: LocalFileAggregateMutationStorePort,
        event_bus: EventBus,
        *,
        event_factory: _LifecycleEventFactory | None = None,
    ) -> None:
        self._store = store
        self._event_bus = event_bus
        self._event_factory = event_factory or _ExistingLifecycleEventFactory()

    def mutate(self, request: AggregateMutationRequest) -> LocalFileAggregateMutationReceipt:
        """Attempt exactly one validated aggregate CAS; never retry or fall back."""

        target_kind, target_id = _target(request)
        if not _request_is_well_formed(request):
            return _receipt(
                request.project_id,
                target_kind,
                target_id,
                "invalid_mutation_precondition",
                "AGGREGATE_MUTATION_INPUT_INVALID",
            )
        snapshot = self._load_snapshot(request, target_kind, target_id)
        if isinstance(snapshot, LocalFileAggregateMutationReceipt):
            return snapshot
        no_op = self._completed_resume_noop(request, snapshot.project, target_kind, target_id)
        if no_op is not None:
            return no_op
        try:
            proposal, events, result = self._pure_mutation(snapshot.project, request)
        except _InvalidPrecondition:
            return _receipt(
                request.project_id,
                target_kind,
                target_id,
                "invalid_mutation_precondition",
                "AGGREGATE_MUTATION_PRECONDITION_INVALID",
            )
        except Exception:
            return _receipt(
                request.project_id,
                target_kind,
                target_id,
                "malformed_authoritative_state",
                "AUTHORITATIVE_MUTATION_UNAVAILABLE",
            )
        try:
            self._store.conditional_commit(snapshot, proposal)
        except StaleRevisionError:
            return _receipt(
                request.project_id,
                target_kind,
                target_id,
                "stale_conflict",
                "AUTHORITATIVE_CAS_STALE_CONFLICT",
            )
        except Exception:
            return _receipt(
                request.project_id,
                target_kind,
                target_id,
                "mutation_not_applied",
                "AUTHORITATIVE_CAS_FAILED",
            )
        try:
            verified = self._store.reread(request.project_id)
            if not _is_verified(request, proposal, verified):
                raise _VerificationFailure
        except Exception:
            return _receipt(
                request.project_id,
                target_kind,
                target_id,
                "post_commit_verification_failed",
                "AUTHORITATIVE_POST_COMMIT_VERIFICATION_FAILED",
            )
        return self._publish_events(request, target_kind, target_id, events, result)

    def _load_snapshot(
        self,
        request: AggregateMutationRequest,
        target_kind: Literal["batch", "project", "chapter"],
        target_id: str,
    ) -> RevisionedProjectSnapshot | LocalFileAggregateMutationReceipt:
        try:
            snapshot = self._store.load_revisioned(request.project_id)
        except Exception:
            return _receipt(
                request.project_id,
                target_kind,
                target_id,
                "malformed_authoritative_state",
                "AUTHORITATIVE_SNAPSHOT_UNAVAILABLE",
            )
        if snapshot.project.id != request.project_id:
            return _receipt(
                request.project_id,
                target_kind,
                target_id,
                "malformed_authoritative_state",
                "AUTHORITATIVE_PROJECT_BINDING_INVALID",
            )
        return snapshot

    @staticmethod
    def _completed_resume_noop(
        request: AggregateMutationRequest,
        project: Project,
        target_kind: Literal["batch", "project", "chapter"],
        target_id: str,
    ) -> LocalFileAggregateMutationReceipt | None:
        if not isinstance(request, BatchResumeMutation):
            return None
        try:
            existing = _require_batch(project, request.batch_id)
        except _InvalidPrecondition:
            return _receipt(
                request.project_id,
                target_kind,
                target_id,
                "invalid_mutation_precondition",
                "AGGREGATE_MUTATION_PRECONDITION_INVALID",
            )
        if existing.status != BatchStatus.COMPLETED:
            return None
        return _receipt(
            request.project_id,
            target_kind,
            target_id,
            "mutation_applied",
            "AGGREGATE_MUTATION_NOOP",
            verified=True,
            result=(existing.status.value, None),
        )

    def _publish_events(
        self,
        request: AggregateMutationRequest,
        target_kind: Literal["batch", "project", "chapter"],
        target_id: str,
        events: tuple[WorkflowEvent, ...],
        result: tuple[str | None, int | None],
    ) -> LocalFileAggregateMutationReceipt:
        if not events:
            return _receipt(
                request.project_id,
                target_kind,
                target_id,
                "mutation_applied",
                "AGGREGATE_MUTATION_APPLIED",
                verified=True,
                result=result,
            )
        event_published = False
        for event in events:
            try:
                self._event_bus.publish([event])
            except Exception:
                return _receipt(
                    request.project_id,
                    target_kind,
                    target_id,
                    "mutation_applied_event_failed",
                    "POST_COMMIT_EVENT_PUBLICATION_FAILED",
                    verified=True,
                    event_published=event_published,
                    result=result,
                )
            event_published = True
        return _receipt(
            request.project_id,
            target_kind,
            target_id,
            "mutation_applied_event_published",
            "AGGREGATE_MUTATION_APPLIED",
            verified=True,
            event_published=event_published,
            result=result,
        )

    def _pure_mutation(
        self, project: Project, request: AggregateMutationRequest
    ) -> tuple[Project, tuple[WorkflowEvent, ...], tuple[str | None, int | None]]:
        if isinstance(request, BatchCreateStartMutation):
            return self._create_start_batch(project, request)
        if isinstance(request, BatchPageResultMutation):
            return self._record_batch_page_result(project, request)
        if isinstance(request, BatchCompleteMutation):
            return self._complete_batch(project, request)
        if isinstance(request, BatchRetryMutation):
            return self._retry_batch(project, request)
        if isinstance(request, BatchResumeMutation):
            return self._resume_batch(project, request)
        if isinstance(request, BatchPauseMutation):
            return self._pause_batch(project, request)
        if isinstance(request, ProjectLifecycleMutation):
            return self._mutate_project_lifecycle(project, request)
        if isinstance(request, ProjectStatusMutation):
            return self._persist_project_status(project)
        if isinstance(request, ChapterLifecycleMutation):
            return self._mutate_chapter_lifecycle(project, request)
        raise _InvalidPrecondition

    def _create_start_batch(
        self, project: Project, request: BatchCreateStartMutation
    ) -> tuple[Project, tuple[WorkflowEvent, ...], tuple[str, None]]:
        batches = _batches(project)
        if request.record.project_id != project.id or request.record.id in batches:
            raise _InvalidPrecondition
        event = self._event_factory.create(
            EventType.BATCH_STARTED,
            {"batch_id": request.record.id, "project_id": project.id},
        )
        record = _with_batch_progress(
            request.record.model_copy(
                update={"status": BatchStatus.RUNNING, "events": [*request.record.events, event]},
                deep=True,
            )
        )
        return _replace_batch(project, record), (event,), (record.status.value, None)

    def _record_batch_page_result(
        self, project: Project, request: BatchPageResultMutation
    ) -> tuple[Project, tuple[WorkflowEvent, ...], tuple[str, int]]:
        record = _require_batch(project, request.batch_id)
        if record.status != BatchStatus.RUNNING:
            raise _InvalidPrecondition
        item = _require_pending_item(record, request.page_number)
        status = QueueItemStatus.COMPLETED if request.outcome == "completed" else QueueItemStatus.FAILED
        error = None if status == QueueItemStatus.COMPLETED else _batch_failure_code(request.outcome)
        replacement = item.model_copy(
            update={"status": status, "attempts": item.attempts + 1, "error": error},
            deep=True,
        )
        updated = _replace_queue_item(record, replacement)
        updated = updated.model_copy(
            update={
                "logs": [
                    *updated.logs,
                    f"page {request.page_number} {request.outcome}",
                ],
                "status": BatchStatus.FAILED
                if request.outcome in {"failed", "deferred"}
                else updated.status,
            },
            deep=False,
        )
        event: WorkflowEvent | None = (
            self._event_factory.create(
                EventType.BATCH_FAILED,
                {"batch_id": updated.id, "project_id": project.id},
            )
            if request.outcome in {"failed", "deferred"}
            else None
        )
        if event is not None:
            updated = updated.model_copy(update={"events": [*updated.events, event]}, deep=False)
        updated = _with_batch_progress(updated, elapsed_time=request.elapsed_time)
        return (
            _replace_batch(project, updated),
            (event,) if event is not None else (),
            (updated.status.value, request.page_number),
        )

    def _complete_batch(
        self, project: Project, request: BatchCompleteMutation
    ) -> tuple[Project, tuple[WorkflowEvent, ...], tuple[str, None]]:
        record = _require_batch(project, request.batch_id)
        if record.status != BatchStatus.RUNNING or any(
            item.status != QueueItemStatus.COMPLETED for item in record.queue
        ):
            raise _InvalidPrecondition
        event = self._event_factory.create(
            EventType.BATCH_COMPLETED,
            {"batch_id": record.id, "project_id": project.id},
        )
        updated = record.model_copy(
            update={"status": BatchStatus.COMPLETED, "events": [*record.events, event]},
            deep=False,
        )
        updated = _with_batch_progress(updated, elapsed_time=request.elapsed_time)
        return _replace_batch(project, updated), (event,), (updated.status.value, None)

    def _retry_batch(
        self, project: Project, request: BatchRetryMutation
    ) -> tuple[Project, tuple[WorkflowEvent, ...], tuple[str, None]]:
        record = _require_batch(project, request.batch_id)
        failed = [item.page_number for item in record.queue if item.status == QueueItemStatus.FAILED]
        if not failed:
            raise _InvalidPrecondition
        queue = [
            item.model_copy(update={"status": QueueItemStatus.PENDING, "error": None}, deep=True)
            if item.status == QueueItemStatus.FAILED
            else item
            for item in record.queue
        ]
        updated = record.model_copy(
            update={
                "queue": queue,
                "status": BatchStatus.RUNNING,
                "logs": [*record.logs, "retrying failed pages"],
                "retry_summary": RetrySummary(
                    retry_count=record.retry_summary.retry_count + 1,
                    requeued_pages=failed,
                ),
            },
            deep=False,
        )
        return _replace_batch(project, _with_batch_progress(updated)), (), (updated.status.value, None)

    def _resume_batch(
        self, project: Project, request: BatchResumeMutation
    ) -> tuple[Project, tuple[WorkflowEvent, ...], tuple[str, None]]:
        record = _require_batch(project, request.batch_id)
        if record.policy.value != "sequential" or record.status == BatchStatus.COMPLETED:
            raise _InvalidPrecondition
        resumed = self._event_factory.create(
            EventType.BATCH_RESUMED,
            {"batch_id": record.id, "project_id": project.id},
        )
        pending = any(item.status == QueueItemStatus.PENDING for item in record.queue)
        failed = any(item.status == QueueItemStatus.FAILED for item in record.queue)
        status = BatchStatus.RUNNING if pending else BatchStatus.FAILED if failed else BatchStatus.COMPLETED
        events: tuple[WorkflowEvent, ...] = (resumed,)
        updated = _with_batch_progress(
            record.model_copy(
                update={"status": status, "events": [*record.events, resumed]},
                deep=False,
            )
        )
        if status == BatchStatus.COMPLETED:
            completed = self._event_factory.create(
                EventType.BATCH_COMPLETED,
                {"batch_id": record.id, "project_id": project.id},
            )
            updated = updated.model_copy(update={"events": [*updated.events, completed]}, deep=False)
            events = (resumed, completed)
        return _replace_batch(project, updated), events, (updated.status.value, None)

    def _pause_batch(
        self, project: Project, request: BatchPauseMutation
    ) -> tuple[Project, tuple[WorkflowEvent, ...], tuple[str, None]]:
        record = _require_batch(project, request.batch_id)
        if record.status == BatchStatus.COMPLETED:
            raise _InvalidPrecondition
        event = self._event_factory.create(
            EventType.BATCH_PAUSED,
            {"batch_id": record.id, "project_id": project.id},
        )
        updated = _with_batch_progress(
            record.model_copy(
                update={"status": BatchStatus.PAUSED, "events": [*record.events, event]},
                deep=False,
            )
        )
        return _replace_batch(project, updated), (event,), (updated.status.value, None)

    def _mutate_project_lifecycle(
        self, project: Project, request: ProjectLifecycleMutation
    ) -> tuple[Project, tuple[WorkflowEvent, ...], tuple[str | None, int | None]]:
        project = _normalise_project(project)
        event: WorkflowEvent | None = None
        if request.operation == "start":
            if not _has_project_history_event(project, EventType.PROJECT_STARTED):
                event = self._event_factory.create(EventType.PROJECT_STARTED, {"project_id": project.id})
                project = _record_project_event(project, event)
            project = _set_project_position(project)
            return project, (event,) if event is not None else (), (project.workflow.get("current_chapter"), project.workflow.get("current_page"))
        if request.operation == "refresh":
            project = _set_project_position(project)
            event = None
            if _project_completed(project) and not _has_project_history_event(
                project, EventType.PROJECT_COMPLETED
            ):
                event = self._event_factory.create(EventType.PROJECT_COMPLETED, {"project_id": project.id})
                project = _record_project_event(project, event)
            return project, (event,) if event is not None else (), (project.workflow.get("current_chapter"), project.workflow.get("current_page"))
        raise _InvalidPrecondition

    @staticmethod
    def _persist_project_status(
        project: Project,
    ) -> tuple[Project, tuple[WorkflowEvent, ...], tuple[str | None, int | None]]:
        project = _normalise_project(project)
        project = _set_project_position(project)
        return project, (), (project.workflow.get("current_chapter"), project.workflow.get("current_page"))

    def _mutate_chapter_lifecycle(
        self, project: Project, request: ChapterLifecycleMutation
    ) -> tuple[Project, tuple[WorkflowEvent, ...], tuple[str | None, int | None]]:
        chapter = project.chapter(request.chapter_id)
        event: WorkflowEvent | None = None
        if request.operation == "start":
            if _has_chapter_event(chapter, EventType.CHAPTER_STARTED):
                return project, (), (chapter.id, chapter.metadata.get("current_page"))
            event = self._event_factory.create(
                EventType.CHAPTER_STARTED,
                {"project_id": project.id, "chapter_id": chapter.id},
            )
            return _record_chapter_event(project, chapter, event), (event,), (chapter.id, None)
        if request.operation == "record_page":
            if request.page_number is None or request.page_number not in chapter.page_numbers:
                raise _InvalidPrecondition
            page = project.page(request.page_number)
            updated = chapter.model_copy(
                update={
                    "metadata": {**chapter.metadata, "current_page": request.page_number},
                    "history": [
                        *chapter.history,
                        {
                            "action": "page_run",
                            "page_number": request.page_number,
                            "state": page.state.value,
                        },
                    ],
                },
                deep=True,
            )
            return project.replace_chapter(updated), (), (chapter.id, request.page_number)
        if request.operation == "refresh":
            completed = _chapter_completed(project, chapter)
            updated = chapter
            if completed and chapter.metadata.get("current_page") is not None:
                updated = updated.model_copy(
                    update={"metadata": {**updated.metadata, "current_page": None}}, deep=True
                )
            event = None
            if completed and not _has_chapter_event(updated, EventType.CHAPTER_COMPLETED):
                event = self._event_factory.create(
                    EventType.CHAPTER_COMPLETED,
                    {"project_id": project.id, "chapter_id": chapter.id},
                )
                updated = updated.model_copy(
                    update={
                        "history": [
                            *updated.history,
                            {"event": str(event.event_type), "data": event.data},
                        ]
                    },
                    deep=True,
                )
            return project.replace_chapter(updated), (event,) if event is not None else (), (chapter.id, updated.metadata.get("current_page"))
        raise _InvalidPrecondition


class _InvalidPrecondition(ValueError):
    pass


class _VerificationFailure(ValueError):
    pass


def _request_is_well_formed(request: AggregateMutationRequest) -> bool:
    if not _valid_identity(request.project_id):
        return False
    if isinstance(request, BatchCreateStartMutation):
        return _valid_identity(request.record.id) and request.record.project_id == request.project_id
    if isinstance(
        request,
        (
            BatchPageResultMutation,
            BatchCompleteMutation,
            BatchRetryMutation,
            BatchResumeMutation,
            BatchPauseMutation,
        ),
    ):
        return _valid_identity(request.batch_id) and (
            not hasattr(request, "elapsed_time")
            or isinstance(request.elapsed_time, float)
            and request.elapsed_time >= 0
        ) and (
            not isinstance(request, BatchPageResultMutation)
            or request.outcome in {"completed", "failed", "deferred"}
            and isinstance(request.page_number, int)
            and not isinstance(request.page_number, bool)
            and request.page_number >= 1
        )
    if isinstance(request, ProjectLifecycleMutation):
        return request.operation in {"start", "refresh"}
    if isinstance(request, ProjectStatusMutation):
        return True
    if isinstance(request, ChapterLifecycleMutation):
        return _valid_identity(request.chapter_id) and request.operation in {
            "start",
            "record_page",
            "refresh",
        } and (
            request.operation != "record_page"
            or isinstance(request.page_number, int)
            and not isinstance(request.page_number, bool)
            and request.page_number >= 1
        )
    return False


def _target(request: AggregateMutationRequest) -> tuple[Literal["batch", "project", "chapter"], str]:
    if isinstance(request, BatchCreateStartMutation):
        return "batch", request.record.id
    if isinstance(
        request,
        (
            BatchPageResultMutation,
            BatchCompleteMutation,
            BatchRetryMutation,
            BatchResumeMutation,
            BatchPauseMutation,
        ),
    ):
        return "batch", request.batch_id
    if isinstance(request, (ProjectLifecycleMutation, ProjectStatusMutation)):
        return "project", request.project_id
    return "chapter", request.chapter_id


def _receipt(
    project_id: str,
    target_kind: Literal["batch", "project", "chapter"],
    target_id: str,
    status: AggregateMutationStatus,
    code: str,
    *,
    verified: bool = False,
    event_published: bool = False,
    result: tuple[str | None, int | None] = (None, None),
) -> LocalFileAggregateMutationReceipt:
    return LocalFileAggregateMutationReceipt(
        project_id=project_id,
        target_kind=target_kind,
        target_id=target_id,
        status=status,
        code=code,
        verified=verified,
        event_published=event_published,
        resulting_status=result[0],
        resulting_page=result[1],
    )


def _batches(project: Project) -> dict[str, BatchRecord]:
    raw = project.workflow.get("batches", {})
    if not isinstance(raw, dict):
        raise _InvalidPrecondition
    return {batch_id: BatchRecord.model_validate(value) for batch_id, value in raw.items()}


def _require_batch(project: Project, batch_id: str) -> BatchRecord:
    try:
        return _batches(project)[batch_id]
    except KeyError as exc:
        raise _InvalidPrecondition from exc


def _replace_batch(project: Project, record: BatchRecord) -> Project:
    batches = _batches(project)
    batches[record.id] = record
    workflow = dict(project.workflow)
    workflow["batches"] = {batch_id: batch.model_dump(mode="json") for batch_id, batch in batches.items()}
    return project.model_copy(update={"workflow": workflow}, deep=True)


def _require_pending_item(record: BatchRecord, page_number: int) -> QueueItem:
    for item in record.queue:
        if item.page_number == page_number and item.status == QueueItemStatus.PENDING:
            return item
    raise _InvalidPrecondition


def _replace_queue_item(record: BatchRecord, replacement: QueueItem) -> BatchRecord:
    return record.model_copy(
        update={
            "queue": [
                replacement if item.page_number == replacement.page_number else item
                for item in record.queue
            ]
        },
        deep=True,
    )


def _with_batch_progress(record: BatchRecord, *, elapsed_time: float | None = None) -> BatchRecord:
    completed = [item.page_number for item in record.queue if item.status == QueueItemStatus.COMPLETED]
    pending = next((item.page_number for item in record.queue if item.status == QueueItemStatus.PENDING), None)
    return record.model_copy(
        update={
            "statistics": ExecutionStatistics(
                total=len(record.queue),
                completed=len(completed),
                failed=sum(item.status == QueueItemStatus.FAILED for item in record.queue),
                skipped=sum(item.status == QueueItemStatus.SKIPPED for item in record.queue),
                attempts=sum(item.attempts for item in record.queue),
                elapsed_time=record.statistics.elapsed_time if elapsed_time is None else elapsed_time,
            ),
            "progress": ProgressSnapshot(
                total=len(record.queue),
                completed=len(completed),
                next_page=pending,
            ),
            "checkpoint": ResumeCheckpoint(completed_pages=completed, next_page=pending),
        },
        deep=False,
    )


def _batch_failure_code(outcome: BatchPageOutcome) -> str:
    return (
        "LOGICAL_OUTPUT_ASSET_QUALITY_GATING_DEFERRED"
        if outcome == "deferred"
        else "BATCH_PAGE_EXECUTION_FAILED"
    )


def _normalise_project(project: Project) -> Project:
    if project.chapters or not project.pages:
        return project
    page_numbers = sorted(page.page_number for page in project.pages)
    return project.model_copy(
        update={"chapters": [Chapter(id="chapter-1", title="Chapter 1", page_numbers=page_numbers)]},
        deep=True,
    )


def _set_project_position(project: Project) -> Project:
    chapter = next((item for item in project.chapters if not _chapter_completed(project, item)), None)
    if chapter is None:
        chapter = next(
            (item for item in project.chapters if not _has_chapter_event(item, EventType.CHAPTER_COMPLETED)),
            None,
        )
    page_number = None
    if chapter is not None and not _chapter_completed(project, chapter):
        page_number = next(
            (number for number in sorted(chapter.page_numbers) if project.page(number).state != PageState.APPROVED),
            None,
        )
    workflow = dict(project.workflow)
    workflow["current_chapter"] = chapter.id if chapter else None
    workflow["current_page"] = page_number
    return project.model_copy(update={"workflow": workflow}, deep=True)


def _record_project_event(project: Project, event: WorkflowEvent) -> Project:
    workflow = dict(project.workflow)
    workflow["history"] = [
        *workflow.get("history", []),
        {"event": str(event.event_type), "data": event.data},
    ]
    return project.model_copy(update={"workflow": workflow}, deep=True)


def _has_project_history_event(project: Project, event_type: EventType) -> bool:
    history = project.workflow.get("history", [])
    return isinstance(history, list) and any(
        isinstance(item, dict) and item.get("event") == event_type.value for item in history
    )


def _record_chapter_event(project: Project, chapter: Chapter, event: WorkflowEvent) -> Project:
    updated = chapter.model_copy(
        update={
            "history": [
                *chapter.history,
                {"event": str(event.event_type), "data": event.data},
            ]
        },
        deep=True,
    )
    return project.replace_chapter(updated)


def _has_chapter_event(chapter: Chapter, event_type: EventType) -> bool:
    return any(
        isinstance(item, dict) and item.get("event") == event_type.value for item in chapter.history
    )


def _chapter_completed(project: Project, chapter: Chapter) -> bool:
    return bool(chapter.page_numbers) and all(
        project.page(page_number).state == PageState.APPROVED for page_number in chapter.page_numbers
    )


def _project_completed(project: Project) -> bool:
    return bool(project.chapters) and all(
        _chapter_completed(project, chapter) for chapter in project.chapters
    )


def _is_verified(request: AggregateMutationRequest, proposal: Project, actual: Project) -> bool:
    if actual.id != proposal.id:
        return False
    if isinstance(request, BatchCreateStartMutation):
        return bool(
            _require_batch(actual, request.record.id) == _require_batch(proposal, request.record.id)
        )
    if isinstance(request, (BatchPageResultMutation, BatchCompleteMutation, BatchRetryMutation)):
        return bool(
            _require_batch(actual, request.batch_id) == _require_batch(proposal, request.batch_id)
        )
    if isinstance(request, (BatchResumeMutation, BatchPauseMutation)):
        return bool(
            _require_batch(actual, request.batch_id) == _require_batch(proposal, request.batch_id)
        )
    if isinstance(request, ProjectLifecycleMutation):
        return bool(actual.workflow == proposal.workflow)
    if isinstance(request, ProjectStatusMutation):
        return bool(actual.chapters == proposal.chapters and actual.workflow == proposal.workflow)
    if isinstance(request, ChapterLifecycleMutation):
        return bool(actual.chapter(request.chapter_id) == proposal.chapter(request.chapter_id))
    return False


def _valid_identity(value: str) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip()
