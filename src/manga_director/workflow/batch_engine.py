"""Persisted Batch workflow orchestration above Project and Page workflows."""

from __future__ import annotations

from time import perf_counter

from manga_director.domain.events import EventType, WorkflowEvent
from manga_director.domain.exceptions import ValidationError, WorkflowError
from manga_director.domain.project import Project
from manga_director.events.bus import EventBus
from manga_director.observability.metrics import MetricsRegistry
from manga_director.repositories.protocols import ProjectRepository
from manga_director.workflow.batch_contracts import (
    AutoExecution,
    BatchRecord,
    BatchStatus,
    ExecutionPolicy,
    ExecutionPolicyName,
    ExecutionResult,
    ExecutionStatistics,
    InMemoryExecutionQueue,
    ParallelExecution,
    ProgressSnapshot,
    QueueItem,
    QueueItemStatus,
    ResumeCheckpoint,
    RetrySummary,
    SequentialExecution,
    Worker,
)
from manga_director.workflow.coordinator import PageContextStore
from manga_director.workflow.execution_planner import ExecutionPlanner
from manga_director.workflow.project_engine import ProjectWorkflowEngine


class BatchWorkflowEngine:
    """Coordinate persisted, sequential page work without accessing Agents or state rules."""

    def __init__(
        self,
        repository: ProjectRepository,
        page_store: PageContextStore,
        worker: Worker,
        event_bus: EventBus,
        planner: ExecutionPlanner | None = None,
        project_engine: ProjectWorkflowEngine | None = None,
        metrics: MetricsRegistry | None = None,
    ) -> None:
        self._repository = repository
        self._page_store = page_store
        self._worker = worker
        self._event_bus = event_bus
        self._planner = planner or ExecutionPlanner()
        self._project_engine = project_engine
        self.metrics = metrics or MetricsRegistry()

    def run(
        self,
        project_id: str,
        policy: ExecutionPolicy | None = None,
        *,
        batch_id: str | None = None,
        chapter_ids: list[str] | None = None,
    ) -> ExecutionResult:
        """Create and run one persisted batch; only SequentialExecution is available."""
        execution_policy = policy or SequentialExecution()
        self._require_executable_policy(execution_policy)
        self._start_project(project_id)
        project = self._repository.load(project_id)
        record = self._planner.plan(
            project,
            execution_policy,
            batch_id=batch_id,
            chapter_ids=chapter_ids,
        )
        if self._find_record(project, record.id) is not None:
            raise ValidationError(f"Batch '{record.id}' already exists in project '{project_id}'.")
        record = self._with_event(record, EventType.BATCH_STARTED)
        record = self._with_progress(
            record.model_copy(update={"status": BatchStatus.RUNNING}, deep=False)
        )
        self._save_record(project, record)
        self._publish_latest(record)
        return self._refresh_project(project_id, self._execute(record))

    def resume(self, project_id: str, batch_id: str) -> ExecutionResult:
        """Continue only pending items in a previously persisted batch."""
        project = self._repository.load(project_id)
        record = self._require_record(project, batch_id)
        self._require_record_policy(record)
        if record.status == BatchStatus.COMPLETED:
            return self._result(record, 0.0)
        record = self._with_event(record, EventType.BATCH_RESUMED)
        record = self._with_progress(
            record.model_copy(update={"status": BatchStatus.RUNNING}, deep=False)
        )
        self._save_record(project, record)
        self._publish_latest(record)
        return self._refresh_project(project_id, self._execute(record))

    def retry(self, project_id: str, batch_id: str) -> ExecutionResult:
        """Requeue failed items only; completed items are immutable batch history."""
        project = self._repository.load(project_id)
        record = self._require_record(project, batch_id)
        self._require_record_policy(record)
        requeued_pages = [
            item.page_number for item in record.queue if item.status == QueueItemStatus.FAILED
        ]
        queue = [
            item.model_copy(update={"status": QueueItemStatus.PENDING, "error": None}, deep=True)
            if item.status == QueueItemStatus.FAILED
            else item
            for item in record.queue
        ]
        if not any(item.status == QueueItemStatus.PENDING for item in queue):
            return self._result(record, 0.0)
        record = record.model_copy(
            update={
                "queue": queue,
                "status": BatchStatus.RUNNING,
                "logs": [*record.logs, "retrying failed pages"],
                "retry_summary": RetrySummary(
                    retry_count=record.retry_summary.retry_count + 1,
                    requeued_pages=requeued_pages,
                ),
            },
            deep=False,
        )
        record = self._with_progress(record)
        self._save_record(project, record)
        return self._refresh_project(project_id, self._execute(record))

    def pause(self, project_id: str, batch_id: str) -> ExecutionResult:
        """Persist a pause point for an external caller before a later resume."""
        project = self._repository.load(project_id)
        record = self._require_record(project, batch_id)
        if record.status == BatchStatus.COMPLETED:
            return self._result(record, 0.0)
        record = self._with_event(record, EventType.BATCH_PAUSED)
        record = self._with_progress(
            record.model_copy(update={"status": BatchStatus.PAUSED}, deep=False)
        )
        self._save_record(project, record)
        self._publish_latest(record)
        return self._result(record, 0.0)

    def status(self, project_id: str, batch_id: str) -> ExecutionResult:
        project = self._repository.load(project_id)
        return self._result(self._require_record(project, batch_id), 0.0)

    def _execute(self, record: BatchRecord) -> ExecutionResult:
        started_at = perf_counter()
        self.metrics.increment("batch.executions")
        queue = InMemoryExecutionQueue(
            item for item in record.queue if item.status == QueueItemStatus.PENDING
        )
        current = record
        completed_pages = {
            item.page_number for item in record.queue if item.status == QueueItemStatus.COMPLETED
        }
        while queue.size():
            item = queue.dequeue()
            if item is None:
                break
            if not self._dependencies_completed(item, completed_pages):
                current = self._append_log(
                    current, f"page {item.page_number} waiting for predecessor"
                )
                current = self._with_progress(
                    current.model_copy(update={"status": BatchStatus.FAILED}, deep=False),
                    current_page=item.page_number,
                    elapsed_time=perf_counter() - started_at,
                )
                self._persist(current)
                return self._finish(current, perf_counter() - started_at)
            try:
                context = self._page_store.load(current.project_id, str(item.page_number))
                result = self._worker.run(context)
                self._page_store.save(current.project_id, str(item.page_number), result.context)
            except Exception as exc:  # Worker errors become recoverable, persisted failed items.
                failed = item.model_copy(
                    update={
                        "status": QueueItemStatus.FAILED,
                        "attempts": item.attempts + 1,
                        "error": str(exc),
                    },
                    deep=True,
                )
                current = self._replace_item(current, failed)
                current = self._append_log(current, f"page {item.page_number} failed: {exc}")
                current = self._with_event(current, EventType.BATCH_FAILED)
                current = self._with_progress(
                    current.model_copy(update={"status": BatchStatus.FAILED}, deep=False),
                    current_page=item.page_number,
                    elapsed_time=perf_counter() - started_at,
                )
                self._persist(current)
                self._publish_latest(current)
                return self._finish(current, perf_counter() - started_at)
            completed = item.model_copy(
                update={"status": QueueItemStatus.COMPLETED, "attempts": item.attempts + 1},
                deep=True,
            )
            current = self._replace_item(current, completed)
            completed_pages.add(item.page_number)
            current = self._append_log(
                current, f"page {item.page_number} completed at {result.current_state.value}"
            )
            current = self._with_progress(
                current,
                current_page=item.page_number,
                elapsed_time=perf_counter() - started_at,
            )
            self._persist(current)

        status = (
            BatchStatus.FAILED
            if any(item.status == QueueItemStatus.FAILED for item in current.queue)
            else BatchStatus.COMPLETED
        )
        current = self._with_progress(
            current.model_copy(update={"status": status}, deep=False),
            elapsed_time=perf_counter() - started_at,
        )
        if status == BatchStatus.COMPLETED:
            current = self._with_event(current, EventType.BATCH_COMPLETED)
        self._persist(current)
        if status == BatchStatus.COMPLETED:
            self._publish_latest(current)
        return self._finish(current, perf_counter() - started_at)

    def _persist(self, record: BatchRecord) -> None:
        project = self._repository.load(record.project_id)
        self._save_record(project, record)

    def _start_project(self, project_id: str) -> None:
        if self._project_engine is not None:
            self._project_engine.start(project_id)

    def _refresh_project(self, project_id: str, result: ExecutionResult) -> ExecutionResult:
        if self._project_engine is not None:
            self._project_engine.refresh(project_id)
        return result

    def _save_record(self, project: Project, record: BatchRecord) -> None:
        workflow = dict(project.workflow)
        batches = dict(workflow.get("batches", {}))
        batches[record.id] = record.model_dump(mode="json")
        workflow["batches"] = batches
        self._repository.save(project.model_copy(update={"workflow": workflow}, deep=False))

    def _publish_latest(self, record: BatchRecord) -> None:
        if record.events:
            self._event_bus.publish([record.events[-1]])

    @staticmethod
    def _find_record(project: Project, batch_id: str) -> BatchRecord | None:
        raw = project.workflow.get("batches", {}).get(batch_id)
        return BatchRecord.model_validate(raw) if raw is not None else None

    def _require_record(self, project: Project, batch_id: str) -> BatchRecord:
        record = self._find_record(project, batch_id)
        if record is None:
            raise ValidationError(f"Batch '{batch_id}' does not exist in project '{project.id}'.")
        return record

    @staticmethod
    def _require_executable_policy(policy: ExecutionPolicy) -> None:
        if not isinstance(policy, SequentialExecution):
            raise WorkflowError(f"Execution policy '{policy.name.value}' is not implemented.")

    @staticmethod
    def _require_record_policy(record: BatchRecord) -> None:
        if record.policy != ExecutionPolicyName.SEQUENTIAL:
            raise WorkflowError(f"Execution policy '{record.policy.value}' is not implemented.")

    @staticmethod
    def _with_event(record: BatchRecord, event_type: EventType) -> BatchRecord:
        event = WorkflowEvent(
            event_type=event_type,
            data={"batch_id": record.id, "project_id": record.project_id},
        )
        return record.model_copy(update={"events": [*record.events, event]}, deep=False)

    @staticmethod
    def _append_log(record: BatchRecord, message: str) -> BatchRecord:
        return record.model_copy(update={"logs": [*record.logs, message]}, deep=False)

    @staticmethod
    def _replace_item(record: BatchRecord, replacement: QueueItem) -> BatchRecord:
        queue = list(record.queue)
        for index, item in enumerate(queue):
            if item.page_number == replacement.page_number:
                queue[index] = replacement
                break
        return record.model_copy(update={"queue": queue}, deep=False)

    @staticmethod
    def _dependencies_completed(item: QueueItem, completed: set[int]) -> bool:
        return set(item.dependencies).issubset(completed)

    @staticmethod
    def _with_progress(
        record: BatchRecord,
        *,
        current_page: int | None = None,
        elapsed_time: float | None = None,
    ) -> BatchRecord:
        completed = [
            item.page_number for item in record.queue if item.status == QueueItemStatus.COMPLETED
        ]
        pending = next(
            (item.page_number for item in record.queue if item.status == QueueItemStatus.PENDING),
            None,
        )
        statistics = ExecutionStatistics(
            total=len(record.queue),
            completed=len(completed),
            failed=sum(item.status == QueueItemStatus.FAILED for item in record.queue),
            skipped=sum(item.status == QueueItemStatus.SKIPPED for item in record.queue),
            attempts=sum(item.attempts for item in record.queue),
            elapsed_time=elapsed_time
            if elapsed_time is not None
            else record.statistics.elapsed_time,
        )
        return record.model_copy(
            update={
                "statistics": statistics,
                "progress": ProgressSnapshot(
                    total=len(record.queue),
                    completed=len(completed),
                    current_page=current_page,
                    next_page=pending,
                ),
                "checkpoint": ResumeCheckpoint(completed_pages=completed, next_page=pending),
            },
            deep=False,
        )

    def _finish(self, record: BatchRecord, elapsed_time: float) -> ExecutionResult:
        self.metrics.observe("batch.duration_seconds", elapsed_time)
        self.metrics.increment(f"batch.status.{record.status.value}")
        return self._result(record, elapsed_time)

    @staticmethod
    def _result(record: BatchRecord, elapsed_time: float) -> ExecutionResult:
        return ExecutionResult(
            success=record.status == BatchStatus.COMPLETED,
            completed=[
                item.page_number
                for item in record.queue
                if item.status == QueueItemStatus.COMPLETED
            ],
            failed=[
                item.page_number for item in record.queue if item.status == QueueItemStatus.FAILED
            ],
            skipped=[
                item.page_number for item in record.queue if item.status == QueueItemStatus.SKIPPED
            ],
            elapsed_time=elapsed_time,
            logs=record.logs,
            batch_id=record.id,
            status=record.status,
            statistics=record.statistics,
            progress=record.progress,
            checkpoint=record.checkpoint,
            retry_summary=record.retry_summary,
        )


__all__ = ["AutoExecution", "BatchWorkflowEngine", "ParallelExecution", "SequentialExecution"]
