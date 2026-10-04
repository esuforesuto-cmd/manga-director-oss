"""v4.2 autonomous-operations DTOs with human authority retained.

This Application-layer module reports supervision, governance, observability,
and reliability evidence for a proposed one-Page autonomous-creative system.
It never starts monitoring, grants approval or override, enforces policy,
dispatches work, retries, recovers, persists, or changes the existing
StateMachine-owned workflow.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.production.director import DirectorModel
from manga_director.workflow.contracts import WorkflowContext


class SupervisionSessionDTO(DirectorModel):
    supervision_session_id: str
    execution_session_id: str
    page_reference: str
    human_supervisor_id: str
    session_started: bool = False
    session_persisted: bool = False


class ApprovalCheckpointDTO(DirectorModel):
    checkpoint_id: str
    supervision_session_id: str
    page_reference: str
    state_machine_revalidation_required: bool = True
    storyboard_evidence_required: bool = True
    quality_review_required: bool = True
    approval_requested: bool = False
    approval_granted: bool = False


class InterventionDTO(DirectorModel):
    intervention_id: str
    supervision_session_id: str
    page_reference: str
    recommended_action: Literal["human_review"] = "human_review"
    intervention_applied: bool = False
    workflow_changed: bool = False


class OverrideRequestDTO(DirectorModel):
    request_id: str
    supervision_session_id: str
    page_reference: str
    human_authorization_required: bool = True
    request_submitted: bool = False
    override_granted: bool = False
    state_machine_bypassed: bool = False


class HumanSupervisionReport(DirectorModel):
    session: SupervisionSessionDTO
    approval_checkpoint: ApprovalCheckpointDTO
    intervention: InterventionDTO
    override_request: OverrideRequestDTO
    automatic_action_taken: bool = False
    planning_only: bool = True


class ExecutionPolicyDTO(DirectorModel):
    policy_id: str = "human-governed-execution-policy"
    page_reference: str
    allowed_actions: tuple[str, ...] = ("human_review", "state_machine_validation")
    policy_persisted: bool = False
    enforcement_enabled: bool = False


class RiskAssessmentDTO(DirectorModel):
    assessment_id: str
    page_reference: str
    risk_level: Literal["low", "medium", "high", "critical"] = "low"
    requires_human_review: bool = True
    risk_accepted: bool = False
    assessment_persisted: bool = False


class SafetyBoundaryDTO(DirectorModel):
    boundary_id: str
    page_reference: str
    exactly_one_page_required: bool = True
    state_machine_authoritative: bool = True
    persisted_storyboard_required: bool = True
    completed_quality_review_required: bool = True
    boundary_enforced: bool = False


class ComplianceReportDTO(DirectorModel):
    report_id: str
    policy_id: str
    page_reference: str
    assessment_completed: bool = False
    compliance_confirmed: bool = False
    report_persisted: bool = False


class GovernanceSummary(DirectorModel):
    policy_count: int = Field(ge=0)
    assessed_boundary_count: int = 0
    enforcement_enabled: bool = False
    automatic_action_taken: bool = False


class ExecutionGovernanceReport(DirectorModel):
    policy: ExecutionPolicyDTO
    risk: RiskAssessmentDTO
    safety_boundary: SafetyBoundaryDTO
    compliance: ComplianceReportDTO
    summary: GovernanceSummary
    planning_only: bool = True


class ExecutionMetricsDTO(DirectorModel):
    page_reference: str
    prepared_session_count: int = Field(ge=0)
    executing_session_count: int = 0
    completed_session_count: int = 0
    metric_collection_active: bool = False
    metrics_persisted: bool = False


class PipelineTraceDTO(DirectorModel):
    trace_id: str
    page_reference: str
    stage_ids: tuple[str, ...] = ()
    span_count: int = Field(default=0, ge=0)
    trace_recorded: bool = False
    remote_export_enabled: bool = False


class RuntimeEventDTO(DirectorModel):
    event_id: str
    page_reference: str
    event_type: Literal["prepared"] = "prepared"
    event_persisted: bool = False
    event_published: bool = False


class MonitoringDashboardDTO(DirectorModel):
    dashboard_id: str
    page_reference: str
    monitoring_active: bool = False
    alerting_enabled: bool = False
    dashboard_persisted: bool = False


class ExecutionAnalyticsSummary(DirectorModel):
    observed_event_count: int = Field(ge=0)
    recorded_trace_count: int = 0
    exported_metric_count: int = 0
    automatic_action_taken: bool = False


class ExecutionObservabilityReport(DirectorModel):
    metrics: ExecutionMetricsDTO
    trace: PipelineTraceDTO
    event: RuntimeEventDTO
    dashboard: MonitoringDashboardDTO
    summary: ExecutionAnalyticsSummary
    planning_only: bool = True


class FailureClassificationDTO(DirectorModel):
    classification_id: str
    page_reference: str
    category: Literal["unclassified", "evidence_missing"] = "unclassified"
    failure_detected: bool = False
    classification_persisted: bool = False
    automatic_remediation_enabled: bool = False


class RecoveryWorkflowDTO(DirectorModel):
    workflow_id: str
    classification_id: str
    page_reference: str
    recommended_action: Literal["human_review"] = "human_review"
    recovery_started: bool = False
    recovery_completed: bool = False
    workflow_persisted: bool = False


class RetryPolicyDTO(DirectorModel):
    policy_id: str = "no-automatic-retry"
    page_reference: str
    max_automatic_attempts: Literal[0] = 0
    retry_performed: bool = False
    policy_enforced: bool = False


class HealthReportDTO(DirectorModel):
    report_id: str
    page_reference: str
    status: Literal["not_checked"] = "not_checked"
    health_check_performed: bool = False
    report_persisted: bool = False
    remediation_applied: bool = False


class ReliabilityDashboard(DirectorModel):
    dashboard_id: str
    page_reference: str
    monitoring_active: bool = False
    retry_execution_enabled: bool = False
    recovery_execution_enabled: bool = False
    dashboard_persisted: bool = False


class ExecutionReliabilityReport(DirectorModel):
    failure: FailureClassificationDTO
    recovery_workflow: RecoveryWorkflowDTO
    retry_policy: RetryPolicyDTO
    health: HealthReportDTO
    dashboard: ReliabilityDashboard
    automatic_action_taken: bool = False
    planning_only: bool = True


class AutonomousOperationsReport(DirectorModel):
    supervision: HumanSupervisionReport
    governance: ExecutionGovernanceReport
    observability: ExecutionObservabilityReport
    reliability: ExecutionReliabilityReport
    planning_only: bool = True


class V42AutonomousOperationsService:
    """Produce local, human-governed v4.2 operations reports only."""

    def human_supervision(
        self, project_id: str, context: WorkflowContext, human_supervisor_id: str = "human"
    ) -> HumanSupervisionReport:
        page_reference = _page_reference(context)
        execution_session_id = f"execution-session:{project_id}:{page_reference}"
        supervision_session_id = f"supervision-session:{project_id}:{page_reference}"
        return HumanSupervisionReport(
            session=SupervisionSessionDTO(
                supervision_session_id=supervision_session_id,
                execution_session_id=execution_session_id,
                page_reference=page_reference,
                human_supervisor_id=human_supervisor_id,
            ),
            approval_checkpoint=ApprovalCheckpointDTO(
                checkpoint_id=f"approval-checkpoint:{project_id}:{page_reference}",
                supervision_session_id=supervision_session_id,
                page_reference=page_reference,
            ),
            intervention=InterventionDTO(
                intervention_id=f"intervention:{project_id}:{page_reference}",
                supervision_session_id=supervision_session_id,
                page_reference=page_reference,
            ),
            override_request=OverrideRequestDTO(
                request_id=f"override-request:{project_id}:{page_reference}",
                supervision_session_id=supervision_session_id,
                page_reference=page_reference,
            ),
        )

    def execution_governance(
        self, project_id: str, context: WorkflowContext
    ) -> ExecutionGovernanceReport:
        page_reference = _page_reference(context)
        missing_storyboard = "storyboard" not in context.artifacts and "storyboard" not in context.page
        policy = ExecutionPolicyDTO(page_reference=page_reference)
        risk_level: Literal["low", "medium", "high", "critical"] = (
            "high" if missing_storyboard else "low"
        )
        return ExecutionGovernanceReport(
            policy=policy,
            risk=RiskAssessmentDTO(
                assessment_id=f"risk-assessment:{project_id}:{page_reference}",
                page_reference=page_reference,
                risk_level=risk_level,
            ),
            safety_boundary=SafetyBoundaryDTO(
                boundary_id=f"safety-boundary:{project_id}:{page_reference}",
                page_reference=page_reference,
            ),
            compliance=ComplianceReportDTO(
                report_id=f"compliance:{project_id}:{page_reference}",
                policy_id=policy.policy_id,
                page_reference=page_reference,
            ),
            summary=GovernanceSummary(policy_count=1, assessed_boundary_count=1),
        )

    def observability(self, project_id: str, context: WorkflowContext) -> ExecutionObservabilityReport:
        page_reference = _page_reference(context)
        return ExecutionObservabilityReport(
            metrics=ExecutionMetricsDTO(page_reference=page_reference, prepared_session_count=1),
            trace=PipelineTraceDTO(
                trace_id=f"pipeline-trace:{project_id}:{page_reference}", page_reference=page_reference
            ),
            event=RuntimeEventDTO(
                event_id=f"runtime-event:{project_id}:{page_reference}", page_reference=page_reference
            ),
            dashboard=MonitoringDashboardDTO(
                dashboard_id=f"monitoring-dashboard:{project_id}:{page_reference}",
                page_reference=page_reference,
            ),
            summary=ExecutionAnalyticsSummary(observed_event_count=1),
        )

    def reliability(self, project_id: str, context: WorkflowContext) -> ExecutionReliabilityReport:
        page_reference = _page_reference(context)
        missing_storyboard = "storyboard" not in context.artifacts and "storyboard" not in context.page
        classification_id = f"failure-classification:{project_id}:{page_reference}"
        return ExecutionReliabilityReport(
            failure=FailureClassificationDTO(
                classification_id=classification_id,
                page_reference=page_reference,
                category="evidence_missing" if missing_storyboard else "unclassified",
                failure_detected=missing_storyboard,
            ),
            recovery_workflow=RecoveryWorkflowDTO(
                workflow_id=f"recovery-workflow:{project_id}:{page_reference}",
                classification_id=classification_id,
                page_reference=page_reference,
            ),
            retry_policy=RetryPolicyDTO(page_reference=page_reference),
            health=HealthReportDTO(
                report_id=f"health-report:{project_id}:{page_reference}", page_reference=page_reference
            ),
            dashboard=ReliabilityDashboard(
                dashboard_id=f"reliability-dashboard:{project_id}:{page_reference}",
                page_reference=page_reference,
            ),
        )

    def operations(
        self, project_id: str, context: WorkflowContext, human_supervisor_id: str = "human"
    ) -> AutonomousOperationsReport:
        return AutonomousOperationsReport(
            supervision=self.human_supervision(project_id, context, human_supervisor_id),
            governance=self.execution_governance(project_id, context),
            observability=self.observability(project_id, context),
            reliability=self.reliability(project_id, context),
        )


def _page_reference(context: WorkflowContext) -> str:
    page_id = context.page.get("id")
    return str(page_id) if page_id is not None else "page"
