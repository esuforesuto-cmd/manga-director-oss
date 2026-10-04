"""Private LocalFile composition for durable hierarchy and batch execution.

This module is deliberately selected only by the LocalFile CLI composition
root.  It reuses the fenced page core and aggregate mutations; it does not
change the legacy workflow classes or repository protocol.
"""

from __future__ import annotations

from contextvars import ContextVar, Token
from time import perf_counter

from manga_director.domain.events import EventType, WorkflowEvent
from manga_director.domain.exceptions import WorkflowError
from manga_director.domain.project import Project
from manga_director.domain.state_machine import PageState
from manga_director.events.bus import EventBus
from manga_director.observability.metrics import MetricsRegistry
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.repositories.project_loader import ProjectLoader
from manga_director.workflow.batch_contracts import (
    BatchRecord,
    BatchStatus,
    ExecutionPolicy,
    ExecutionPolicyName,
    ExecutionResult,
    QueueItemStatus,
    SequentialExecution,
)
from manga_director.workflow.batch_engine import BatchWorkflowEngine
from manga_director.workflow.contracts import WorkflowContext, WorkflowResult, WorkflowStatus
from manga_director.workflow.coordinator import WorkflowCoordinator
from manga_director.workflow.durable_execution import (
    LogicalOutputAssetQualityGatePort,
    _DurableRunRoutingError,
    _route_localfile_run,
)
from manga_director.workflow.engine import WorkflowEngine
from manga_director.workflow.execution_planner import ExecutionPlanner
from manga_director.workflow.hierarchy_contracts import (
    ChapterContext,
    ChapterWorkflowResult,
    ProjectContext,
    ProjectWorkflowResult,
)
from manga_director.workflow.localfile_aggregate_mutation import (
    AggregateMutationRequest,
    BatchCompleteMutation,
    BatchCreateStartMutation,
    BatchPageOutcome,
    BatchPageResultMutation,
    BatchPauseMutation,
    BatchResumeMutation,
    BatchRetryMutation,
    ChapterLifecycleMutation,
    LocalFileAggregateMutationCoordinator,
    LocalFileAggregateMutationReceipt,
    LocalFileAggregateMutationStore,
    ProjectLifecycleMutation,
)
from manga_director.workflow.project_engine import ProjectWorkflowEngine
from manga_director.workflow.scheduler import PageNumberWorkflowScheduler


class _DurableRoutingFailure(WorkflowError):
    """Bounded failure raised after a durable route cannot continue safely."""


class _CapturingLifecycleEventFactory:
    """Private event capture for unchanged hierarchy result event semantics."""

    def __init__(self) -> None:
        self._captured_events: ContextVar[list[WorkflowEvent] | None] = ContextVar(
            "localfile_durable_lifecycle_events", default=None
        )

    def begin_capture(self) -> Token[list[WorkflowEvent] | None]:
        """Open one operation-local lifecycle event capture scope."""

        return self._captured_events.set([])

    def complete_capture(self, token: Token[list[WorkflowEvent] | None]) -> list[WorkflowEvent]:
        """Return only this scope's events and close its capture scope."""

        events = self._captured_events.get()
        self._captured_events.reset(token)
        if events is None:
            raise _DurableRoutingFailure("DURABLE_LIFECYCLE_EVENT_CAPTURE_INVALID")
        return events

    def discard_capture(self, token: Token[list[WorkflowEvent] | None]) -> None:
        """Close a failed operation's private capture scope without returning it."""

        self._captured_events.reset(token)

    def create(self, event_type: EventType, data: dict[str, str]) -> WorkflowEvent:
        event = WorkflowEvent(event_type=event_type, data=data)
        captured = self._captured_events.get()
        if captured is None:
            raise _DurableRoutingFailure("DURABLE_LIFECYCLE_EVENT_CAPTURE_INVALID")
        captured.append(event)
        return event


class LocalFileDurableWorkflowWorker:
    """Private worker that treats caller context solely as page identity."""

    def __init__(
        self,
        repository: LocalFileRepository,
        engine: WorkflowEngine,
        logical_output_asset_quality_gate: LogicalOutputAssetQualityGatePort | None = None,
    ) -> None:
        self._repository = repository
        self._engine = engine
        self._logical_output_asset_quality_gate = logical_output_asset_quality_gate

    def run(self, page_context: WorkflowContext) -> WorkflowResult:
        project_id = page_context.page.get("project_id")
        page_id = page_context.page.get("page_id")
        if not isinstance(project_id, str) or not isinstance(page_id, str) or not page_id.isdecimal():
            raise _DurableRoutingFailure("DURABLE_WORKER_IDENTITY_INVALID")
        if self._logical_output_asset_quality_gate is None:
            result = _route_localfile_run(
                self._engine,
                self._repository,
                project_id,
                page_id,
            )
        else:
            result = _route_localfile_run(
                self._engine,
                self._repository,
                project_id,
                page_id,
                logical_output_asset_quality_gate=self._logical_output_asset_quality_gate,
            )
        if isinstance(result, WorkflowResult):
            return result
        return _status_result(self._engine, self._repository, project_id, page_id)


class LocalFileDurableWorkflowCoordinator(WorkflowCoordinator):
    """Private LocalFile hierarchy route composed only from frozen durable primitives."""

    def __init__(
        self,
        repository: LocalFileRepository,
        engine: WorkflowEngine,
        mutations: LocalFileAggregateMutationCoordinator,
        event_factory: _CapturingLifecycleEventFactory,
        event_bus: EventBus,
        logical_output_asset_quality_gate: LogicalOutputAssetQualityGatePort | None = None,
    ) -> None:
        self._repository = repository
        self._engine = engine
        self._mutations = mutations
        self._event_factory = event_factory
        self._scheduler = PageNumberWorkflowScheduler()
        self._legacy_project_engine = ProjectWorkflowEngine(repository, event_bus)
        self._logical_output_asset_quality_gate = logical_output_asset_quality_gate

    def create_project(self, project_id: str, title: str, page_number: int = 1) -> ProjectContext:
        """Preserve the explicitly non-durable create compatibility path."""

        return self._legacy_project_engine.create(project_id, title, page_number)

    def run_project(self, project_id: str) -> ProjectWorkflowResult:
        events = self._mutate(ProjectLifecycleMutation(project_id, "start"))
        project = self._repository.load(project_id)
        chapter_id = project.workflow.get("current_chapter")
        chapter_result: ChapterWorkflowResult | None = None
        if isinstance(chapter_id, str):
            chapter_result, chapter_events = self._run_chapter(project_id, chapter_id)
            events.extend(chapter_events)
        events.extend(self._mutate(ProjectLifecycleMutation(project_id, "refresh")))
        return ProjectWorkflowResult(
            context=_project_context(self._repository.load(project_id)),
            chapter_result=chapter_result,
            events=events,
            messages=["project workflow started"],
        )

    def resume_project(self, project_id: str) -> ProjectWorkflowResult:
        return self.run_project(project_id)

    def run_chapter(self, project_id: str, chapter_id: str) -> ProjectWorkflowResult:
        events = self._mutate(ProjectLifecycleMutation(project_id, "start"))
        chapter_result, chapter_events = self._run_chapter(project_id, chapter_id)
        events.extend(chapter_events)
        events.extend(self._mutate(ProjectLifecycleMutation(project_id, "refresh")))
        return ProjectWorkflowResult(
            context=_project_context(self._repository.load(project_id)),
            chapter_result=chapter_result,
            events=events,
            messages=["project workflow started"],
        )

    def project_status(self, project_id: str) -> ProjectContext:
        """Return the shared persisted-page inspection without durable mutation."""
        return self._legacy_project_engine.status(project_id)

    def chapter_status(self, project_id: str, chapter_id: str) -> ChapterContext:
        return _chapter_context(self._repository.load(project_id), chapter_id)

    def _run_chapter(
        self, project_id: str, chapter_id: str
    ) -> tuple[ChapterWorkflowResult, list[WorkflowEvent]]:
        events = self._mutate(ChapterLifecycleMutation(project_id, chapter_id, "start"))
        project = self._repository.load(project_id)
        context = _chapter_context(project, chapter_id)
        page = self._scheduler.next_page(context)
        page_context: WorkflowContext | None = None
        if page is not None:
            if self._logical_output_asset_quality_gate is None:
                result = _route_localfile_run(
                    self._engine, self._repository, project_id, str(page.page_number)
                )
            else:
                result = _route_localfile_run(
                    self._engine,
                    self._repository,
                    project_id,
                    str(page.page_number),
                    logical_output_asset_quality_gate=self._logical_output_asset_quality_gate,
                )
            page_context = _result_context(self._engine, self._repository, project_id, page.page_number, result)
            self._mutate(
                ChapterLifecycleMutation(project_id, chapter_id, "record_page", page.page_number)
            )
        events.extend(self._mutate(ChapterLifecycleMutation(project_id, chapter_id, "refresh")))
        final_project = self._repository.load(project_id)
        final_context = _chapter_context(final_project, chapter_id)
        completed = all(item.state == PageState.APPROVED for item in final_context.pages)
        return (
            ChapterWorkflowResult(
                context=final_context,
                page_context=page_context,
                completed=completed,
                events=events,
                messages=["chapter workflow completed" if completed else "one page workflow executed"],
            ),
            events,
        )

    def _mutate(self, request: AggregateMutationRequest) -> list[WorkflowEvent]:
        token = self._event_factory.begin_capture()
        try:
            receipt = self._mutations.mutate(request)
            _require_applied(receipt)
        except BaseException:
            self._event_factory.discard_capture(token)
            raise
        return self._event_factory.complete_capture(token)


class LocalFileDurableBatchWorkflowEngine(BatchWorkflowEngine):
    """Private LocalFile batch route with fresh aggregate snapshots at every handoff."""

    def __init__(
        self,
        repository: LocalFileRepository,
        worker: LocalFileDurableWorkflowWorker,
        event_bus: EventBus,
        mutations: LocalFileAggregateMutationCoordinator,
        *,
        planner: ExecutionPlanner | None = None,
        metrics: MetricsRegistry | None = None,
    ) -> None:
        self._repository = repository
        self._worker = worker
        self._event_bus = event_bus
        self._mutations = mutations
        self._planner = planner or ExecutionPlanner()
        self.metrics = metrics or MetricsRegistry()

    def run(
        self,
        project_id: str,
        policy: ExecutionPolicy | None = None,
        *,
        batch_id: str | None = None,
        chapter_ids: list[str] | None = None,
    ) -> ExecutionResult:
        execution_policy = policy or SequentialExecution()
        self._require_executable_policy(execution_policy)
        self._mutate(ProjectLifecycleMutation(project_id, "start"))
        project = self._repository.load(project_id)
        record = self._planner.plan(
            project, execution_policy, batch_id=batch_id, chapter_ids=chapter_ids
        )
        self._mutate(BatchCreateStartMutation(project_id, record))
        return self._refresh_project(project_id, self._execute_durable(project_id, record.id))

    def resume(self, project_id: str, batch_id: str) -> ExecutionResult:
        self._mutate(BatchResumeMutation(project_id, batch_id))
        record = self._record(project_id, batch_id)
        if record.status != BatchStatus.RUNNING:
            return self._result(record, 0.0)
        return self._refresh_project(project_id, self._execute_durable(project_id, batch_id))

    def retry(self, project_id: str, batch_id: str) -> ExecutionResult:
        self._mutate(BatchRetryMutation(project_id, batch_id))
        return self._refresh_project(project_id, self._execute_durable(project_id, batch_id))

    def pause(self, project_id: str, batch_id: str) -> ExecutionResult:
        self._mutate(BatchPauseMutation(project_id, batch_id))
        return self._result(self._record(project_id, batch_id), 0.0)

    def status(self, project_id: str, batch_id: str) -> ExecutionResult:
        return self._result(self._record(project_id, batch_id), 0.0)

    def _execute_durable(self, project_id: str, batch_id: str) -> ExecutionResult:
        started_at = perf_counter()
        self.metrics.increment("batch.executions")
        while True:
            record = self._record(project_id, batch_id)
            pending = next(
                (item for item in record.queue if item.status == QueueItemStatus.PENDING), None
            )
            if pending is None:
                if record.status == BatchStatus.RUNNING:
                    self._mutate(
                        BatchCompleteMutation(project_id, batch_id, perf_counter() - started_at)
                    )
                    record = self._record(project_id, batch_id)
                return self._finish(record, perf_counter() - started_at)
            completed = {
                item.page_number
                for item in record.queue
                if item.status == QueueItemStatus.COMPLETED
            }
            if not set(pending.dependencies).issubset(completed):
                self._mutate(
                    BatchPageResultMutation(
                        project_id,
                        batch_id,
                        pending.page_number,
                        "failed",
                        perf_counter() - started_at,
                    )
                )
                return self._finish(self._record(project_id, batch_id), perf_counter() - started_at)
            project = self._repository.load(project_id)
            context = ProjectLoader._context_from_page(project, project.page(pending.page_number))
            try:
                self._worker.run(context)
                outcome: BatchPageOutcome = "completed"
            except _DurableRunRoutingError as exc:
                outcome = (
                    "deferred"
                    if "LOGICAL_OUTPUT_ASSET_QUALITY_GATING_DEFERRED" in str(exc)
                    else "failed"
                )
            except Exception:
                outcome = "failed"
            self._mutate(
                BatchPageResultMutation(
                    project_id,
                    batch_id,
                    pending.page_number,
                    outcome,
                    perf_counter() - started_at,
                )
            )
            if outcome != "completed":
                return self._finish(self._record(project_id, batch_id), perf_counter() - started_at)

    def _refresh_project(self, project_id: str, result: ExecutionResult) -> ExecutionResult:
        self._mutate(ProjectLifecycleMutation(project_id, "refresh"))
        return result

    def _record(self, project_id: str, batch_id: str) -> BatchRecord:
        raw = self._repository.load(project_id).workflow.get("batches", {}).get(batch_id)
        if raw is None:
            raise _DurableRoutingFailure("DURABLE_BATCH_RECORD_UNAVAILABLE")
        return BatchRecord.model_validate(raw)

    def _mutate(self, request: AggregateMutationRequest) -> None:
        receipt = self._mutations.mutate(request)
        _require_applied(receipt)

    @staticmethod
    def _require_executable_policy(policy: ExecutionPolicy) -> None:
        if policy.name != ExecutionPolicyName.SEQUENTIAL:
            raise WorkflowError(f"Execution policy '{policy.name.value}' is not implemented.")


def build_localfile_durable_workflow(
    repository: LocalFileRepository,
    engine: WorkflowEngine,
    event_bus: EventBus,
    *,
    logical_output_asset_quality_gate: LogicalOutputAssetQualityGatePort | None = None,
) -> tuple[LocalFileDurableWorkflowCoordinator, LocalFileDurableBatchWorkflowEngine]:
    """Create the private LocalFile-only hierarchy and batch composition."""

    lifecycle_events = _CapturingLifecycleEventFactory()
    coordinator_mutations = LocalFileAggregateMutationCoordinator(
        LocalFileAggregateMutationStore(repository), event_bus, event_factory=lifecycle_events
    )
    batch_mutations = LocalFileAggregateMutationCoordinator(
        LocalFileAggregateMutationStore(repository), event_bus
    )
    worker = LocalFileDurableWorkflowWorker(
        repository, engine, logical_output_asset_quality_gate
    )
    return (
        LocalFileDurableWorkflowCoordinator(
            repository,
            engine,
            coordinator_mutations,
            lifecycle_events,
            event_bus,
            logical_output_asset_quality_gate,
        ),
        LocalFileDurableBatchWorkflowEngine(repository, worker, event_bus, batch_mutations),
    )


def _require_applied(receipt: LocalFileAggregateMutationReceipt) -> None:
    if receipt.status not in {"mutation_applied", "mutation_applied_event_published"}:
        raise _DurableRoutingFailure(f"DURABLE_AGGREGATE_PARTIAL_PROGRESS:{receipt.code}")


def _project_context(project: Project) -> ProjectContext:
    return ProjectContext(
        project=project,
        chapters=project.chapters,
        metadata=dict(project.metadata),
        history=list(project.workflow.get("history", [])),
        current_chapter=project.workflow.get("current_chapter"),
        current_page=project.workflow.get("current_page"),
    )


def _chapter_context(project: Project, chapter_id: str) -> ChapterContext:
    chapter = project.chapter(chapter_id)
    return ChapterContext(
        chapter=chapter,
        pages=sorted(
            (project.page(page_number) for page_number in chapter.page_numbers),
            key=lambda item: item.page_number,
        ),
        metadata=dict(chapter.metadata),
        history=list(chapter.history),
        current_page=chapter.metadata.get("current_page"),
    )


def _result_context(
    engine: WorkflowEngine,
    repository: LocalFileRepository,
    project_id: str,
    page_number: int,
    result: WorkflowResult | WorkflowStatus,
) -> WorkflowContext:
    if isinstance(result, WorkflowResult):
        return result.context
    project = repository.load(project_id)
    return ProjectLoader._context_from_page(project, project.page(page_number))


def _status_result(
    engine: WorkflowEngine,
    repository: LocalFileRepository,
    project_id: str,
    page_id: str,
) -> WorkflowResult:
    project = repository.load(project_id)
    context = ProjectLoader._context_from_page(project, project.page(int(page_id)))
    status = engine.status(context)
    return WorkflowResult(
        current_state=status.current_state,
        completed_step="none",
        logs=["page workflow already at an automatic stopping point"],
        context=context,
    )
