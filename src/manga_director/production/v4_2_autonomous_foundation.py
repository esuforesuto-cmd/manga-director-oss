"""v4.2 autonomous-system foundation DTOs without autonomous execution.

This application-layer module prepares immutable, one-page-scoped evidence for
future execution, checkpoint, supervision, and long-running-task capabilities.
It does not start a session, schedule or dispatch a task, persist a checkpoint,
resume work, invoke an agent, mutate a repository, or transition a workflow.
The existing StateMachine remains the sole workflow-transition authority.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.domain.state_machine import PageState
from manga_director.production.director import DirectorModel
from manga_director.workflow.contracts import WorkflowContext


class GoalDTO(DirectorModel):
    """A human-owned, exactly-one-page goal declaration."""

    goal_id: str
    project_id: str
    page_reference: str
    objective: str
    current_state: PageState
    page_count: Literal[1] = 1
    success_criteria: tuple[str, ...] = ()
    human_approved: bool = False
    execution_enabled: bool = False


class ExecutionContextDTO(DirectorModel):
    project_id: str
    page_reference: str
    workflow_state: PageState
    storyboard_evidence_present: bool = False
    quality_review_completed: bool = False
    state_machine_revalidation_required: bool = True
    context_persisted: bool = False


class ExecutionSessionDTO(DirectorModel):
    session_id: str
    goal_id: str
    context: ExecutionContextDTO
    state: Literal["defined"] = "defined"
    human_start_required: bool = True
    session_started: bool = False
    session_persisted: bool = False


class ExecutionStateDTO(DirectorModel):
    session_id: str
    state: Literal["defined"] = "defined"
    execution_started: bool = False
    state_changed: bool = False
    workflow_changed: bool = False


class ExecutionSummary(DirectorModel):
    session_count: int = Field(ge=0)
    started_session_count: int = 0
    completed_session_count: int = 0
    autonomous_decision_enabled: bool = False
    automatic_action_taken: bool = False


class AutonomousExecutionReport(DirectorModel):
    goal: GoalDTO
    session: ExecutionSessionDTO
    state: ExecutionStateDTO
    summary: ExecutionSummary
    planning_only: bool = True


class CheckpointDTO(DirectorModel):
    checkpoint_id: str
    session_id: str
    page_reference: str
    workflow_state: PageState
    sequence: int = Field(ge=0)
    artifact_references: tuple[str, ...] = ()
    integrity_revalidation_required: bool = True
    checkpoint_persisted: bool = False


class SnapshotDTO(DirectorModel):
    snapshot_id: str
    checkpoint_id: str
    page_reference: str
    evidence_hash: str | None = None
    snapshot_persisted: bool = False
    restoration_enabled: bool = False


class ResumeRequestDTO(DirectorModel):
    request_id: str
    checkpoint_id: str
    page_reference: str
    human_authorization_required: bool = True
    request_dispatched: bool = False
    automatic_resume_enabled: bool = False


class ResumeResultDTO(DirectorModel):
    request_id: str
    resume_authorized: bool = False
    resumed: bool = False
    workflow_changed: bool = False
    result_persisted: bool = False


class CheckpointRepository:
    """Immutable local checkpoint projection; not a ProjectRepository replacement."""

    def __init__(self, checkpoints: tuple[CheckpointDTO, ...] = ()) -> None:
        identifiers = tuple(checkpoint.checkpoint_id for checkpoint in checkpoints)
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("checkpoint IDs must be unique")
        self._checkpoints = tuple(checkpoints)

    def list(self) -> tuple[CheckpointDTO, ...]:
        return self._checkpoints

    def get(self, checkpoint_id: str) -> CheckpointDTO | None:
        return next(
            (checkpoint for checkpoint in self._checkpoints if checkpoint.checkpoint_id == checkpoint_id),
            None,
        )


class CheckpointReport(DirectorModel):
    checkpoint: CheckpointDTO
    snapshot: SnapshotDTO
    resume_request: ResumeRequestDTO
    resume_result: ResumeResultDTO
    repository_contract_changed: bool = False
    planning_only: bool = True


class SupervisorSessionDTO(DirectorModel):
    supervisor_session_id: str
    execution_session_id: str
    page_reference: str
    session_started: bool = False
    session_persisted: bool = False


class ProgressMonitorDTO(DirectorModel):
    execution_session_id: str
    observed_checkpoint_count: int = Field(ge=0)
    progress_percent: int = Field(default=0, ge=0, le=100)
    monitoring_active: bool = False
    telemetry_export_enabled: bool = False


class HealthStatusDTO(DirectorModel):
    execution_session_id: str
    status: Literal["not_started"] = "not_started"
    failure_detected: bool = False
    health_persisted: bool = False
    remediation_applied: bool = False


class EscalationDTO(DirectorModel):
    escalation_id: str
    execution_session_id: str
    page_reference: str
    severity: Literal["info", "warning", "high", "critical"] = "info"
    human_decision_required: bool = True
    escalation_sent: bool = False
    emergency_stop_triggered: bool = False


class SupervisorReport(DirectorModel):
    session: SupervisorSessionDTO
    progress: ProgressMonitorDTO
    health: HealthStatusDTO
    escalation: EscalationDTO
    automatic_action_taken: bool = False
    planning_only: bool = True


class TaskQueueDTO(DirectorModel):
    queue_id: str
    task_ids: tuple[str, ...] = ()
    queued_for_dispatch: bool = False
    queue_persisted: bool = False


class ScheduledTaskDTO(DirectorModel):
    task_id: str
    page_reference: str
    scheduled_for: str | None = None
    schedule_registered: bool = False
    execution_enabled: bool = False


class BackgroundTaskDTO(DirectorModel):
    task_id: str
    page_reference: str
    background_started: bool = False
    long_running: bool = False
    cancellation_enabled: bool = False


class TaskProgressDTO(DirectorModel):
    task_id: str
    progress_percent: int = Field(default=0, ge=0, le=100)
    progress_persisted: bool = False
    automatic_continuation_enabled: bool = False


class TaskLifecycleSummary(DirectorModel):
    planned_task_count: int = Field(ge=0)
    scheduled_task_count: int = 0
    running_task_count: int = 0
    completed_task_count: int = 0
    automatic_action_taken: bool = False


class LongRunningTaskReport(DirectorModel):
    queue: TaskQueueDTO
    scheduled_task: ScheduledTaskDTO
    background_task: BackgroundTaskDTO
    progress: TaskProgressDTO
    lifecycle: TaskLifecycleSummary
    planning_only: bool = True


class V42AutonomousFoundationService:
    """Build non-executing v4.2 autonomous-system DTO projections."""

    def __init__(self, checkpoints: CheckpointRepository | None = None) -> None:
        self._checkpoints = checkpoints or CheckpointRepository()

    def execution(
        self, project_id: str, context: WorkflowContext, objective: str
    ) -> AutonomousExecutionReport:
        execution_context = _execution_context(project_id, context)
        goal = GoalDTO(
            goal_id=f"goal:{project_id}:{execution_context.page_reference}",
            project_id=project_id,
            page_reference=execution_context.page_reference,
            objective=objective,
            current_state=context.state,
        )
        session_id = f"execution-session:{project_id}:{execution_context.page_reference}"
        return AutonomousExecutionReport(
            goal=goal,
            session=ExecutionSessionDTO(
                session_id=session_id, goal_id=goal.goal_id, context=execution_context
            ),
            state=ExecutionStateDTO(session_id=session_id),
            summary=ExecutionSummary(session_count=1),
        )

    def checkpoint(self, project_id: str, context: WorkflowContext) -> CheckpointReport:
        execution_context = _execution_context(project_id, context)
        session_id = f"execution-session:{project_id}:{execution_context.page_reference}"
        checkpoint = CheckpointDTO(
            checkpoint_id=f"checkpoint:{project_id}:{execution_context.page_reference}",
            session_id=session_id,
            page_reference=execution_context.page_reference,
            workflow_state=context.state,
            sequence=0,
            artifact_references=tuple(sorted(str(name) for name in context.artifacts)),
        )
        request_id = f"resume-request:{checkpoint.checkpoint_id}"
        return CheckpointReport(
            checkpoint=checkpoint,
            snapshot=SnapshotDTO(
                snapshot_id=f"snapshot:{checkpoint.checkpoint_id}",
                checkpoint_id=checkpoint.checkpoint_id,
                page_reference=checkpoint.page_reference,
            ),
            resume_request=ResumeRequestDTO(
                request_id=request_id,
                checkpoint_id=checkpoint.checkpoint_id,
                page_reference=checkpoint.page_reference,
            ),
            resume_result=ResumeResultDTO(request_id=request_id),
        )

    def supervisor(self, project_id: str, context: WorkflowContext) -> SupervisorReport:
        execution_context = _execution_context(project_id, context)
        session_id = f"execution-session:{project_id}:{execution_context.page_reference}"
        checkpoint_count = sum(
            checkpoint.page_reference == execution_context.page_reference
            for checkpoint in self._checkpoints.list()
        )
        return SupervisorReport(
            session=SupervisorSessionDTO(
                supervisor_session_id=f"supervisor-session:{project_id}:{execution_context.page_reference}",
                execution_session_id=session_id,
                page_reference=execution_context.page_reference,
            ),
            progress=ProgressMonitorDTO(
                execution_session_id=session_id, observed_checkpoint_count=checkpoint_count
            ),
            health=HealthStatusDTO(execution_session_id=session_id),
            escalation=EscalationDTO(
                escalation_id=f"escalation:{project_id}:{execution_context.page_reference}",
                execution_session_id=session_id,
                page_reference=execution_context.page_reference,
            ),
        )

    def long_running_tasks(self, project_id: str, context: WorkflowContext) -> LongRunningTaskReport:
        execution_context = _execution_context(project_id, context)
        task_id = f"long-running-task:{project_id}:{execution_context.page_reference}"
        return LongRunningTaskReport(
            queue=TaskQueueDTO(
                queue_id=f"task-queue:{project_id}:{execution_context.page_reference}",
                task_ids=(task_id,),
            ),
            scheduled_task=ScheduledTaskDTO(
                task_id=task_id, page_reference=execution_context.page_reference
            ),
            background_task=BackgroundTaskDTO(
                task_id=task_id, page_reference=execution_context.page_reference
            ),
            progress=TaskProgressDTO(task_id=task_id),
            lifecycle=TaskLifecycleSummary(planned_task_count=1),
        )


def _execution_context(project_id: str, context: WorkflowContext) -> ExecutionContextDTO:
    page_id = context.page.get("id")
    page_reference = str(page_id) if page_id is not None else "page"
    return ExecutionContextDTO(
        project_id=project_id,
        page_reference=page_reference,
        workflow_state=context.state,
        storyboard_evidence_present=(
            "storyboard" in context.artifacts or "storyboard" in context.page
        ),
    )
