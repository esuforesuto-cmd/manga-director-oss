"""v4.1 human-review, governance, observability, and reliability DTOs.

This application-layer module reports local, one-page multi-agent evidence. It
never grants approval, enforces permissions, sends telemetry, retries work,
starts recovery, invokes agents, or changes StateMachine-owned workflow state.
"""

from __future__ import annotations

from pydantic import Field

from manga_director.domain.state_machine import PageState
from manga_director.production.director import DirectorModel
from manga_director.production.v4_1_agent_foundation import (
    AgentDTO,
    AgentRegistryRepository,
)
from manga_director.workflow.contracts import WorkflowContext


class ApprovalRequestDTO(DirectorModel):
    request_id: str
    project_id: str
    page_reference: str
    current_state: PageState
    quality_review_completed: bool = False
    request_dispatched: bool = False
    human_decision_required: bool = True


class ApprovalResultDTO(DirectorModel):
    request_id: str
    approved: bool = False
    state_machine_transitioned: bool = False
    result_persisted: bool = False


class ReviewSessionDTO(DirectorModel):
    session_id: str
    page_reference: str
    session_started: bool = False
    review_completed: bool = False
    session_persisted: bool = False


class FeedbackDTO(DirectorModel):
    feedback_id: str
    session_id: str
    submitted: bool = False
    feedback_persisted: bool = False
    automatic_action_taken: bool = False


class DecisionHistoryDTO(DirectorModel):
    page_reference: str
    decision_count: int = Field(ge=0)
    history_persisted: bool = False
    retention_enabled: bool = False


class HumanReviewReport(DirectorModel):
    request: ApprovalRequestDTO
    result: ApprovalResultDTO
    session: ReviewSessionDTO
    feedback: FeedbackDTO
    history: DecisionHistoryDTO
    planning_only: bool = True


class AgentPolicyDTO(DirectorModel):
    policy_id: str = "human-governed-agent-policy"
    agent_id: str
    allowed_capability_ids: tuple[str, ...] = ()
    policy_persisted: bool = False
    enforcement_enabled: bool = False


class PermissionDTO(DirectorModel):
    permission_id: str
    agent_id: str
    permission_granted: bool = False
    permission_persisted: bool = False


class CapabilityRestrictionDTO(DirectorModel):
    restriction_id: str
    agent_id: str
    restricted_capability_ids: tuple[str, ...] = ()
    restriction_enforced: bool = False


class ComplianceSummary(DirectorModel):
    assessed_agent_count: int = Field(ge=0)
    compliant_agent_count: int = 0
    enforcement_enabled: bool = False
    automatic_action_taken: bool = False


class GovernanceReport(DirectorModel):
    policy: AgentPolicyDTO
    permission: PermissionDTO
    restriction: CapabilityRestrictionDTO
    compliance: ComplianceSummary
    planning_only: bool = True


class AgentMetricsDTO(DirectorModel):
    registered_agent_count: int = Field(ge=0)
    executing_agent_count: int = 0
    metric_collection_persisted: bool = False
    remote_export_enabled: bool = False


class ExecutionTraceDTO(DirectorModel):
    trace_id: str
    page_reference: str
    span_count: int = 0
    trace_persisted: bool = False
    agent_execution_observed: bool = False


class EventTimelineDTO(DirectorModel):
    page_reference: str
    observed_event_count: int = Field(ge=0)
    timeline_persisted: bool = False
    event_dispatch_enabled: bool = False


class CollaborationMetrics(DirectorModel):
    planned_participant_count: int = Field(ge=0)
    completed_handoff_count: int = 0
    completed_review_count: int = 0
    metrics_persisted: bool = False


class RuntimeDashboardDTO(DirectorModel):
    dashboard_id: str
    agent_metrics: AgentMetricsDTO
    collaboration_metrics: CollaborationMetrics
    dashboard_persisted: bool = False
    monitoring_enabled: bool = False


class ObservabilityReport(DirectorModel):
    agent_metrics: AgentMetricsDTO
    trace: ExecutionTraceDTO
    timeline: EventTimelineDTO
    collaboration_metrics: CollaborationMetrics
    dashboard: RuntimeDashboardDTO
    planning_only: bool = True


class RetryPolicyDTO(DirectorModel):
    policy_id: str = "manual-retry-only"
    max_automatic_attempts: int = 0
    retry_performed: bool = False
    policy_persisted: bool = False


class TimeoutPolicyDTO(DirectorModel):
    policy_id: str = "no-runtime-timeout-control"
    timeout_enforced: bool = False
    cancellation_performed: bool = False
    policy_persisted: bool = False


class RecoveryDTO(DirectorModel):
    recovery_id: str
    page_reference: str
    recovery_started: bool = False
    recovery_completed: bool = False
    recovery_persisted: bool = False


class FailureReportDTO(DirectorModel):
    report_id: str
    page_reference: str
    failure_detected: bool = False
    remediation_applied: bool = False
    report_persisted: bool = False


class ReliabilitySummary(DirectorModel):
    retry_count: int = 0
    timeout_count: int = 0
    recovery_count: int = 0
    automatic_action_taken: bool = False
    long_term_memory_optimized: bool = False


class ReliabilityReport(DirectorModel):
    retry: RetryPolicyDTO
    timeout: TimeoutPolicyDTO
    recovery: RecoveryDTO
    failure: FailureReportDTO
    summary: ReliabilitySummary
    planning_only: bool = True


class MultiAgentPlatformReport(DirectorModel):
    human_review: HumanReviewReport
    governance: GovernanceReport
    observability: ObservabilityReport
    reliability: ReliabilityReport
    automatic_action_taken: bool = False
    planning_only: bool = True


class V41PlatformAssuranceService:
    """Produce application DTOs for human review and runtime assurance only."""

    def __init__(self, registry: AgentRegistryRepository) -> None:
        self._registry = registry

    def human_review(self, project_id: str, context: WorkflowContext) -> HumanReviewReport:
        page_reference = _page_reference(context)
        request_id = f"approval-request:{project_id}:{page_reference}"
        session_id = f"review-session:{project_id}:{page_reference}"
        return HumanReviewReport(
            request=ApprovalRequestDTO(
                request_id=request_id,
                project_id=project_id,
                page_reference=page_reference,
                current_state=context.state,
            ),
            result=ApprovalResultDTO(request_id=request_id),
            session=ReviewSessionDTO(session_id=session_id, page_reference=page_reference),
            feedback=FeedbackDTO(
                feedback_id=f"feedback:{project_id}:{page_reference}", session_id=session_id
            ),
            history=DecisionHistoryDTO(page_reference=page_reference, decision_count=0),
        )

    def governance(self, agent_id: str) -> GovernanceReport:
        agent = self._agent(agent_id)
        capabilities = tuple(capability.capability_id for capability in agent.profile.capabilities)
        return GovernanceReport(
            policy=AgentPolicyDTO(agent_id=agent.agent_id, allowed_capability_ids=capabilities),
            permission=PermissionDTO(
                permission_id=f"permission:{agent.agent_id}", agent_id=agent.agent_id
            ),
            restriction=CapabilityRestrictionDTO(
                restriction_id=f"restriction:{agent.agent_id}", agent_id=agent.agent_id
            ),
            compliance=ComplianceSummary(assessed_agent_count=1),
        )

    def observability(self, project_id: str, context: WorkflowContext) -> ObservabilityReport:
        page_reference = _page_reference(context)
        agent_metrics = AgentMetricsDTO(registered_agent_count=len(self._registry.list()))
        collaboration = CollaborationMetrics(planned_participant_count=len(self._registry.list()))
        return ObservabilityReport(
            agent_metrics=agent_metrics,
            trace=ExecutionTraceDTO(
                trace_id=f"trace:{project_id}:{page_reference}", page_reference=page_reference
            ),
            timeline=EventTimelineDTO(
                page_reference=page_reference, observed_event_count=len(context.events)
            ),
            collaboration_metrics=collaboration,
            dashboard=RuntimeDashboardDTO(
                dashboard_id=f"runtime-dashboard:{project_id}:{page_reference}",
                agent_metrics=agent_metrics,
                collaboration_metrics=collaboration,
            ),
        )

    def reliability(self, project_id: str, context: WorkflowContext) -> ReliabilityReport:
        page_reference = _page_reference(context)
        return ReliabilityReport(
            retry=RetryPolicyDTO(),
            timeout=TimeoutPolicyDTO(),
            recovery=RecoveryDTO(
                recovery_id=f"recovery:{project_id}:{page_reference}", page_reference=page_reference
            ),
            failure=FailureReportDTO(
                report_id=f"failure:{project_id}:{page_reference}", page_reference=page_reference
            ),
            summary=ReliabilitySummary(),
        )

    def platform_report(
        self, agent_id: str, project_id: str, context: WorkflowContext
    ) -> MultiAgentPlatformReport:
        return MultiAgentPlatformReport(
            human_review=self.human_review(project_id, context),
            governance=self.governance(agent_id),
            observability=self.observability(project_id, context),
            reliability=self.reliability(project_id, context),
        )

    def _agent(self, agent_id: str) -> AgentDTO:
        agent = self._registry.get(agent_id)
        if agent is None:
            raise ValueError(f"unknown agent: {agent_id}")
        return agent


def _page_reference(context: WorkflowContext) -> str:
    page_id = context.page.get("id")
    return str(page_id) if page_id is not None else "page"
