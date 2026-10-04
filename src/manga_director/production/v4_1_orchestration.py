"""v4.1 orchestration DTOs without agent execution or workflow authority.

The application service in this module prepares bounded, one-page collaboration
plans from registered agent declarations. It never dispatches tasks, invokes
agents or models, resolves conflicts, persists state, or transitions a workflow.
The existing StateMachine and quality-review/approval gates remain canonical.
"""

from __future__ import annotations

from pydantic import Field

from manga_director.domain.state_machine import PageState
from manga_director.production.director import DirectorModel
from manga_director.production.v4_1_agent_foundation import AgentRegistryRepository
from manga_director.workflow.contracts import WorkflowContext


class TaskDependencyDTO(DirectorModel):
    predecessor_task_id: str
    successor_task_id: str
    dependency_satisfied: bool = False
    workflow_transition_requested: bool = False


class TaskQueueDTO(DirectorModel):
    queue_id: str
    task_ids: tuple[str, ...] = ()
    queued_for_dispatch: bool = False
    queue_persisted: bool = False


class ExecutionPlanDTO(DirectorModel):
    plan_id: str
    project_id: str
    page_reference: str
    task_ids: tuple[str, ...] = ()
    dependencies: tuple[TaskDependencyDTO, ...] = ()
    execution_enabled: bool = False
    manual_execution_required: bool = True


class OrchestrationDTO(DirectorModel):
    orchestration_id: str
    project_id: str
    page_reference: str
    participant_agent_ids: tuple[str, ...] = ()
    current_state: PageState
    orchestration_persisted: bool = False
    autonomous_decision_enabled: bool = False


class ExecutionSummary(DirectorModel):
    planned_task_count: int = Field(ge=0)
    dispatched_task_count: int = 0
    completed_task_count: int = 0
    workflow_changed: bool = False
    automatic_action_taken: bool = False


class OrchestrationReport(DirectorModel):
    orchestration: OrchestrationDTO
    plan: ExecutionPlanDTO
    queue: TaskQueueDTO
    summary: ExecutionSummary
    planning_only: bool = True


class PriorityModelDTO(DirectorModel):
    model_id: str = "human-review-first"
    criteria: tuple[str, ...] = ("human_review", "workflow_legality", "single_page_scope")
    automatic_prioritization_enabled: bool = False


class PlanningRequestDTO(DirectorModel):
    request_id: str
    project_id: str
    page_reference: str
    workflow_state: PageState
    requested_agent_ids: tuple[str, ...] = ()
    request_persisted: bool = False


class TaskBreakdownDTO(DirectorModel):
    task_id: str
    title: str
    assigned_agent_id: str | None = None
    requires_human_review: bool = True
    executable: bool = False


class PlanningResultDTO(DirectorModel):
    request_id: str
    tasks: tuple[TaskBreakdownDTO, ...] = ()
    result_persisted: bool = False
    workflow_changed: bool = False


class PlanningSummary(DirectorModel):
    task_count: int = Field(ge=0)
    assigned_task_count: int = Field(ge=0)
    execution_enabled: bool = False
    self_learning_enabled: bool = False
    automatic_action_taken: bool = False


class PlanningReport(DirectorModel):
    request: PlanningRequestDTO
    priority: PriorityModelDTO
    result: PlanningResultDTO
    summary: PlanningSummary
    planning_only: bool = True


class AssignmentWorkflow(DirectorModel):
    workflow_id: str
    task_id: str
    agent_id: str
    assignment_accepted: bool = False
    assignment_persisted: bool = False


class ReviewWorkflow(DirectorModel):
    workflow_id: str
    task_id: str
    review_required: bool = True
    quality_review_completed: bool = False
    review_persisted: bool = False


class ApprovalWorkflow(DirectorModel):
    workflow_id: str
    task_id: str
    quality_review_completed: bool = False
    approval_granted: bool = False
    state_machine_bypassed: bool = False


class HandoffDTO(DirectorModel):
    handoff_id: str
    from_agent_id: str
    to_agent_id: str
    task_id: str
    handoff_performed: bool = False
    handoff_persisted: bool = False


class CollaborationWorkflowReport(DirectorModel):
    assignment: AssignmentWorkflow
    review: ReviewWorkflow
    approval: ApprovalWorkflow
    handoff: HandoffDTO
    planning_only: bool = True
    automatic_action_taken: bool = False


class ConflictDTO(DirectorModel):
    conflict_id: str
    task_id: str
    conflicting_agent_ids: tuple[str, ...] = ()
    detected: bool = False
    conflict_persisted: bool = False


class ResolutionStrategyDTO(DirectorModel):
    strategy_id: str = "human-review-required"
    description: str = "Escalate conflict evidence to a human reviewer."
    automatic_resolution_enabled: bool = False


class MergeResultDTO(DirectorModel):
    conflict_id: str
    merge_applied: bool = False
    content_changed: bool = False
    result_persisted: bool = False


class DecisionRecordDTO(DirectorModel):
    decision_id: str
    conflict_id: str
    decision_recorded: bool = False
    human_decision_required: bool = True
    record_persisted: bool = False


class ResolutionSummary(DirectorModel):
    conflict_count: int = Field(ge=0)
    resolved_conflict_count: int = 0
    automatic_action_taken: bool = False


class ConflictResolutionReport(DirectorModel):
    conflict: ConflictDTO
    strategy: ResolutionStrategyDTO
    merge: MergeResultDTO
    decision: DecisionRecordDTO
    summary: ResolutionSummary
    planning_only: bool = True


class V41OrchestrationService:
    """Build one-page advisory orchestration and conflict DTO projections."""

    def __init__(self, registry: AgentRegistryRepository) -> None:
        self._registry = registry

    def orchestration(self, project_id: str, context: WorkflowContext) -> OrchestrationReport:
        page_reference = _page_reference(context)
        task_ids = (f"plan:{page_reference}", f"review:{page_reference}")
        dependency = TaskDependencyDTO(
            predecessor_task_id=task_ids[0], successor_task_id=task_ids[1]
        )
        agent_ids = tuple(agent.agent_id for agent in self._registry.list())
        return OrchestrationReport(
            orchestration=OrchestrationDTO(
                orchestration_id=f"orchestration:{project_id}:{page_reference}",
                project_id=project_id,
                page_reference=page_reference,
                participant_agent_ids=agent_ids,
                current_state=context.state,
            ),
            plan=ExecutionPlanDTO(
                plan_id=f"execution-plan:{project_id}:{page_reference}",
                project_id=project_id,
                page_reference=page_reference,
                task_ids=task_ids,
                dependencies=(dependency,),
            ),
            queue=TaskQueueDTO(
                queue_id=f"task-queue:{project_id}:{page_reference}", task_ids=task_ids
            ),
            summary=ExecutionSummary(planned_task_count=len(task_ids)),
        )

    def planning(self, project_id: str, context: WorkflowContext) -> PlanningReport:
        page_reference = _page_reference(context)
        agent_ids = tuple(agent.agent_id for agent in self._registry.list())
        request = PlanningRequestDTO(
            request_id=f"planning-request:{project_id}:{page_reference}",
            project_id=project_id,
            page_reference=page_reference,
            workflow_state=context.state,
            requested_agent_ids=agent_ids,
        )
        tasks = tuple(
            TaskBreakdownDTO(
                task_id=f"planned-task:{agent_id}:{page_reference}",
                title=f"Human-reviewed preparation for {agent_id}",
                assigned_agent_id=agent_id,
            )
            for agent_id in agent_ids
        )
        return PlanningReport(
            request=request,
            priority=PriorityModelDTO(),
            result=PlanningResultDTO(request_id=request.request_id, tasks=tasks),
            summary=PlanningSummary(task_count=len(tasks), assigned_task_count=len(tasks)),
        )

    def collaboration_workflow(
        self,
        from_agent_id: str,
        to_agent_id: str,
        project_id: str,
        context: WorkflowContext,
    ) -> CollaborationWorkflowReport:
        self._require_agent(from_agent_id)
        self._require_agent(to_agent_id)
        page_reference = _page_reference(context)
        task_id = f"workflow-task:{page_reference}"
        workflow_id = f"collaboration-workflow:{project_id}:{page_reference}"
        return CollaborationWorkflowReport(
            assignment=AssignmentWorkflow(
                workflow_id=workflow_id, task_id=task_id, agent_id=to_agent_id
            ),
            review=ReviewWorkflow(workflow_id=workflow_id, task_id=task_id),
            approval=ApprovalWorkflow(workflow_id=workflow_id, task_id=task_id),
            handoff=HandoffDTO(
                handoff_id=f"handoff:{from_agent_id}:{to_agent_id}:{page_reference}",
                from_agent_id=from_agent_id,
                to_agent_id=to_agent_id,
                task_id=task_id,
            ),
        )

    def conflict_resolution(
        self, project_id: str, context: WorkflowContext
    ) -> ConflictResolutionReport:
        page_reference = _page_reference(context)
        conflict = ConflictDTO(
            conflict_id=f"conflict:{project_id}:{page_reference}",
            task_id=f"workflow-task:{page_reference}",
        )
        return ConflictResolutionReport(
            conflict=conflict,
            strategy=ResolutionStrategyDTO(),
            merge=MergeResultDTO(conflict_id=conflict.conflict_id),
            decision=DecisionRecordDTO(
                decision_id=f"decision:{conflict.conflict_id}", conflict_id=conflict.conflict_id
            ),
            summary=ResolutionSummary(conflict_count=0),
        )

    def _require_agent(self, agent_id: str) -> None:
        if self._registry.get(agent_id) is None:
            raise ValueError(f"unknown agent: {agent_id}")


def _page_reference(context: WorkflowContext) -> str:
    page_id = context.page.get("id")
    return str(page_id) if page_id is not None else "page"
