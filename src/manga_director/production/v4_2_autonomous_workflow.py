"""v4.2 semi-autonomous workflow DTOs without execution authority.

The services in this module prepare human-review evidence for goal management,
adaptive planning, pipeline automation, and recovery. They do not select goals,
apply revisions, resolve dependencies, execute pipeline stages, retry, recover,
persist, dispatch, or transition workflows. All actions remain bounded to one
Page and the existing StateMachine remains authoritative.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.domain.state_machine import PageState
from manga_director.production.director import DirectorModel
from manga_director.production.v4_2_autonomous_foundation import GoalDTO
from manga_director.workflow.contracts import WorkflowContext


class GoalManagerDTO(DirectorModel):
    manager_id: str
    goal: GoalDTO
    goal_registered: bool = False
    automatic_goal_selection_enabled: bool = False


class GoalHierarchyDTO(DirectorModel):
    root_goal_id: str
    child_goal_ids: tuple[str, ...] = ()
    hierarchy_persisted: bool = False
    multi_page_scope_allowed: bool = False


class MilestoneDTO(DirectorModel):
    milestone_id: str
    goal_id: str
    page_reference: str
    status: Literal["defined"] = "defined"
    completed: bool = False
    milestone_persisted: bool = False


class ProgressEvaluationDTO(DirectorModel):
    goal_id: str
    page_reference: str
    progress_percent: int = Field(default=0, ge=0, le=100)
    evaluation_persisted: bool = False
    automatic_action_recommended: bool = False


class GoalSummary(DirectorModel):
    goal_count: int = Field(ge=0)
    active_goal_count: int = 0
    completed_goal_count: int = 0
    autonomous_decision_enabled: bool = False


class GoalManagementReport(DirectorModel):
    manager: GoalManagerDTO
    hierarchy: GoalHierarchyDTO
    milestone: MilestoneDTO
    progress: ProgressEvaluationDTO
    summary: GoalSummary
    planning_only: bool = True


class PlanningSessionDTO(DirectorModel):
    session_id: str
    goal_id: str
    page_reference: str
    current_state: PageState
    session_started: bool = False
    session_persisted: bool = False


class ExecutionPlanRevisionDTO(DirectorModel):
    revision_id: str
    session_id: str
    page_reference: str
    rationale: str
    revision_applied: bool = False
    workflow_changed: bool = False


class TaskPrioritizationDTO(DirectorModel):
    session_id: str
    task_ids: tuple[str, ...] = ()
    priority_basis: tuple[str, ...] = ("human_review", "workflow_legality", "one_page_scope")
    automatic_prioritization_enabled: bool = False


class DependencyResolverDTO(DirectorModel):
    session_id: str
    dependency_ids: tuple[str, ...] = ()
    resolution_required: bool = True
    resolution_applied: bool = False
    state_machine_bypassed: bool = False


class AdaptivePlanningReport(DirectorModel):
    session: PlanningSessionDTO
    revision: ExecutionPlanRevisionDTO
    prioritization: TaskPrioritizationDTO
    dependency_resolver: DependencyResolverDTO
    automatic_action_taken: bool = False
    planning_only: bool = True


class PipelineDefinitionDTO(DirectorModel):
    pipeline_id: str
    project_id: str
    page_reference: str
    stage_ids: tuple[str, ...] = ()
    pipeline_persisted: bool = False
    execution_enabled: bool = False


class PipelineStageDTO(DirectorModel):
    stage_id: str
    pipeline_id: str
    name: str
    page_reference: str
    state_machine_revalidation_required: bool = True
    stage_started: bool = False
    stage_completed: bool = False


class StageResultDTO(DirectorModel):
    stage_id: str
    result_status: Literal["not_run"] = "not_run"
    artifact_created: bool = False
    result_persisted: bool = False
    workflow_changed: bool = False


class AutomationRuleDTO(DirectorModel):
    rule_id: str
    pipeline_id: str
    trigger: str
    requires_human_approval: bool = True
    rule_enforced: bool = False
    automatic_dispatch_enabled: bool = False


class PipelineSummary(DirectorModel):
    stage_count: int = Field(ge=0)
    started_stage_count: int = 0
    completed_stage_count: int = 0
    automatic_action_taken: bool = False


class PipelineAutomationReport(DirectorModel):
    definition: PipelineDefinitionDTO
    stage: PipelineStageDTO
    stage_result: StageResultDTO
    rule: AutomationRuleDTO
    summary: PipelineSummary
    planning_only: bool = True


class FailureDetectionDTO(DirectorModel):
    detection_id: str
    page_reference: str
    failure_detected: bool = False
    reason: str | None = None
    monitoring_active: bool = False
    failure_persisted: bool = False


class RecoveryPlanDTO(DirectorModel):
    plan_id: str
    detection_id: str
    page_reference: str
    recommended_action: Literal["human_review"] = "human_review"
    recovery_execution_enabled: bool = False
    plan_persisted: bool = False


class RetryStrategyDTO(DirectorModel):
    strategy_id: str
    plan_id: str
    max_automatic_attempts: Literal[0] = 0
    retry_performed: bool = False
    policy_enforced: bool = False


class RecoveryResultDTO(DirectorModel):
    plan_id: str
    recovered: bool = False
    state_restored: bool = False
    workflow_changed: bool = False
    result_persisted: bool = False


class RecoverySummary(DirectorModel):
    detected_failure_count: int = Field(ge=0)
    recovery_count: int = 0
    retry_count: int = 0
    automatic_action_taken: bool = False


class ExecutionRecoveryReport(DirectorModel):
    failure: FailureDetectionDTO
    plan: RecoveryPlanDTO
    retry: RetryStrategyDTO
    result: RecoveryResultDTO
    summary: RecoverySummary
    planning_only: bool = True


class V42AutonomousWorkflowService:
    """Prepare v4.2 workflow-management reports with all actions disabled."""

    def goal_management(
        self, project_id: str, context: WorkflowContext, objective: str
    ) -> GoalManagementReport:
        goal = _goal(project_id, context, objective)
        return GoalManagementReport(
            manager=GoalManagerDTO(manager_id=f"goal-manager:{project_id}", goal=goal),
            hierarchy=GoalHierarchyDTO(root_goal_id=goal.goal_id),
            milestone=MilestoneDTO(
                milestone_id=f"milestone:{goal.goal_id}",
                goal_id=goal.goal_id,
                page_reference=goal.page_reference,
            ),
            progress=ProgressEvaluationDTO(goal_id=goal.goal_id, page_reference=goal.page_reference),
            summary=GoalSummary(goal_count=1),
        )

    def adaptive_planning(
        self, project_id: str, context: WorkflowContext, objective: str
    ) -> AdaptivePlanningReport:
        goal = _goal(project_id, context, objective)
        page_reference = goal.page_reference
        session_id = f"planning-session:{project_id}:{page_reference}"
        task_id = f"planning-task:{project_id}:{page_reference}"
        return AdaptivePlanningReport(
            session=PlanningSessionDTO(
                session_id=session_id,
                goal_id=goal.goal_id,
                page_reference=page_reference,
                current_state=context.state,
            ),
            revision=ExecutionPlanRevisionDTO(
                revision_id=f"plan-revision:{project_id}:{page_reference}",
                session_id=session_id,
                page_reference=page_reference,
                rationale="Human review is required before any plan change.",
            ),
            prioritization=TaskPrioritizationDTO(session_id=session_id, task_ids=(task_id,)),
            dependency_resolver=DependencyResolverDTO(
                session_id=session_id, dependency_ids=("state_machine_validation",)
            ),
        )

    def pipeline_automation(
        self, project_id: str, context: WorkflowContext
    ) -> PipelineAutomationReport:
        page_reference = _page_reference(context)
        pipeline_id = f"pipeline:{project_id}:{page_reference}"
        stage_id = f"pipeline-stage:{project_id}:{page_reference}:validate"
        return PipelineAutomationReport(
            definition=PipelineDefinitionDTO(
                pipeline_id=pipeline_id,
                project_id=project_id,
                page_reference=page_reference,
                stage_ids=(stage_id,),
            ),
            stage=PipelineStageDTO(
                stage_id=stage_id,
                pipeline_id=pipeline_id,
                name="human_reviewed_state_validation",
                page_reference=page_reference,
            ),
            stage_result=StageResultDTO(stage_id=stage_id),
            rule=AutomationRuleDTO(
                rule_id=f"automation-rule:{project_id}:{page_reference}",
                pipeline_id=pipeline_id,
                trigger="human_approved_review",
            ),
            summary=PipelineSummary(stage_count=1),
        )

    def execution_recovery(self, project_id: str, context: WorkflowContext) -> ExecutionRecoveryReport:
        page_reference = _page_reference(context)
        missing_storyboard = "storyboard" not in context.artifacts and "storyboard" not in context.page
        detection_id = f"failure-detection:{project_id}:{page_reference}"
        plan_id = f"recovery-plan:{project_id}:{page_reference}"
        return ExecutionRecoveryReport(
            failure=FailureDetectionDTO(
                detection_id=detection_id,
                page_reference=page_reference,
                failure_detected=missing_storyboard,
                reason="missing_storyboard_evidence" if missing_storyboard else None,
            ),
            plan=RecoveryPlanDTO(plan_id=plan_id, detection_id=detection_id, page_reference=page_reference),
            retry=RetryStrategyDTO(strategy_id=f"retry-strategy:{plan_id}", plan_id=plan_id),
            result=RecoveryResultDTO(plan_id=plan_id),
            summary=RecoverySummary(detected_failure_count=int(missing_storyboard)),
        )


def _goal(project_id: str, context: WorkflowContext, objective: str) -> GoalDTO:
    return GoalDTO(
        goal_id=f"goal:{project_id}:{_page_reference(context)}",
        project_id=project_id,
        page_reference=_page_reference(context),
        objective=objective,
        current_state=context.state,
    )


def _page_reference(context: WorkflowContext) -> str:
    page_id = context.page.get("id")
    return str(page_id) if page_id is not None else "page"
