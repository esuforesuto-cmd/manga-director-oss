"""v4.3 production governance, assurance, monitoring, and reliability DTOs.

These immutable Application-layer projections provide human-review evidence for
commercial-grade production operations. They do not enforce policies, grant
approval, send alerts, monitor a process, recover work, mutate a repository,
or publish, distribute, bill, or call an external service.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.domain.state_machine import PageState
from manga_director.production.director import DirectorModel
from manga_director.production.v4_3_production_intelligence import (
    ProductionReportDTO,
    ProjectAnalyticsReport,
    V43ProductionIntelligenceService,
)
from manga_director.workflow.contracts import WorkflowContext


class V43ProductionPolicyDTO(DirectorModel):
    policy_id: str
    project_id: str
    page_reference: str
    state_machine_authoritative: bool = True
    policy_enforced: bool = False
    policy_persisted: bool = False


class V43WorkflowComplianceDTO(DirectorModel):
    policy_id: str
    workflow_state: PageState
    page_count: Literal[1] = 1
    storyboard_evidence_present: bool = False
    quality_review_required: bool = True
    compliance_confirmed: bool = False
    workflow_changed: bool = False


class V43ApprovalMatrixDTO(DirectorModel):
    policy_id: str
    required_roles: tuple[Literal["human_owner", "quality_reviewer"], ...] = (
        "human_owner",
        "quality_reviewer",
    )
    approval_granted: bool = False
    automatic_approval_enabled: bool = False


class V43GovernanceSummary(DirectorModel):
    policy_count: int = Field(default=1, ge=0)
    compliance_count: int = Field(default=1, ge=0)
    approval_count: int = 0
    enforcement_action_taken: bool = False


class V43ProductionGovernanceReport(DirectorModel):
    production: ProductionReportDTO
    policy: V43ProductionPolicyDTO
    compliance: V43WorkflowComplianceDTO
    approval_matrix: V43ApprovalMatrixDTO
    summary: V43GovernanceSummary
    planning_only: bool = True


class V43QASessionDTO(DirectorModel):
    session_id: str
    project_id: str
    page_reference: str
    workflow_state: PageState
    session_started: bool = False
    session_persisted: bool = False


class V43ValidationRuleDTO(DirectorModel):
    rule_id: str
    session_id: str
    state_machine_authoritative: bool = True
    rule_evaluated: bool = False
    remediation_applied: bool = False


class V43ReviewChecklistDTO(DirectorModel):
    session_id: str
    storyboard_required: bool = True
    quality_review_required: bool = True
    checklist_completed: bool = False
    approval_granted: bool = False


class V43QualityScoreDTO(DirectorModel):
    session_id: str
    score: int = Field(default=0, ge=0, le=100)
    score_persisted: bool = False
    quality_gate_passed: bool = False


class V43QASummary(DirectorModel):
    session_count: int = Field(default=1, ge=0)
    evaluated_rule_count: int = 0
    completed_review_count: int = 0
    automatic_action_taken: bool = False


class V43QualityAssuranceReport(DirectorModel):
    production: ProductionReportDTO
    session: V43QASessionDTO
    rule: V43ValidationRuleDTO
    checklist: V43ReviewChecklistDTO
    score: V43QualityScoreDTO
    summary: V43QASummary
    planning_only: bool = True


class V43OperationsMetricsDTO(DirectorModel):
    project_id: str
    page_reference: str
    observed_stage_count: int = Field(default=0, ge=0)
    metric_persisted: bool = False
    telemetry_export_enabled: bool = False


class V43ProductionTimelineDTO(DirectorModel):
    project_id: str
    page_reference: str
    events: tuple[str, ...] = ()
    timeline_persisted: bool = False
    monitoring_active: bool = False


class V43AlertDTO(DirectorModel):
    alert_id: str
    project_id: str
    severity: Literal["info", "warning", "high", "critical"] = "info"
    alert_configured: bool = False
    alert_sent: bool = False
    remediation_triggered: bool = False


class V43MonitoringDashboardDTO(DirectorModel):
    project_id: str
    metric_count: int = Field(default=1, ge=0)
    alert_count: int = 0
    dashboard_persisted: bool = False
    automatic_action_taken: bool = False


class V43OperationsSummary(DirectorModel):
    observed_project_count: int = Field(default=1, ge=0)
    active_monitor_count: int = 0
    sent_alert_count: int = 0
    automatic_action_taken: bool = False


class V43OperationsMonitoringReport(DirectorModel):
    analytics: ProjectAnalyticsReport
    metrics: V43OperationsMetricsDTO
    timeline: V43ProductionTimelineDTO
    alert: V43AlertDTO
    dashboard: V43MonitoringDashboardDTO
    summary: V43OperationsSummary
    planning_only: bool = True


class V43HealthCheckDTO(DirectorModel):
    project_id: str
    page_reference: str
    status: Literal["not_checked"] = "not_checked"
    check_executed: bool = False
    health_persisted: bool = False


class V43IncidentDTO(DirectorModel):
    incident_id: str
    project_id: str
    page_reference: str
    detected: bool = False
    incident_persisted: bool = False
    escalation_sent: bool = False


class V43RecoveryPolicyDTO(DirectorModel):
    policy_id: str
    project_id: str
    automatic_retry_enabled: bool = False
    automatic_recovery_enabled: bool = False
    policy_enforced: bool = False


class V43ReliabilityMetricsDTO(DirectorModel):
    project_id: str
    observed_incident_count: int = 0
    recovery_count: int = 0
    metrics_persisted: bool = False
    remediation_applied: bool = False


class V43ReliabilitySummary(DirectorModel):
    health_check_count: int = Field(default=1, ge=0)
    incident_count: int = 0
    recovery_count: int = 0
    automatic_action_taken: bool = False


class V43PlatformReliabilityReport(DirectorModel):
    analytics: ProjectAnalyticsReport
    health: V43HealthCheckDTO
    incident: V43IncidentDTO
    recovery_policy: V43RecoveryPolicyDTO
    metrics: V43ReliabilityMetricsDTO
    summary: V43ReliabilitySummary
    planning_only: bool = True


class V43ProductionOperationsService:
    """Build non-executing production operations DTO projections."""

    def __init__(self, intelligence: V43ProductionIntelligenceService | None = None) -> None:
        self._intelligence = intelligence or V43ProductionIntelligenceService()

    def production_governance(
        self, project_id: str, context: WorkflowContext
    ) -> V43ProductionGovernanceReport:
        production = self._intelligence.production_automation(project_id, context)
        page_reference = production.plan.page_reference
        policy_id = f"production-policy:{project_id}:{page_reference}"
        return V43ProductionGovernanceReport(
            production=production,
            policy=V43ProductionPolicyDTO(
                policy_id=policy_id,
                project_id=project_id,
                page_reference=page_reference,
            ),
            compliance=V43WorkflowComplianceDTO(
                policy_id=policy_id,
                workflow_state=context.state,
                storyboard_evidence_present=(
                    "storyboard" in context.artifacts or "storyboard" in context.page
                ),
            ),
            approval_matrix=V43ApprovalMatrixDTO(policy_id=policy_id),
            summary=V43GovernanceSummary(),
        )

    def quality_assurance(self, project_id: str, context: WorkflowContext) -> V43QualityAssuranceReport:
        production = self._intelligence.production_automation(project_id, context)
        page_reference = production.plan.page_reference
        session_id = f"qa-session:{project_id}:{page_reference}"
        return V43QualityAssuranceReport(
            production=production,
            session=V43QASessionDTO(
                session_id=session_id,
                project_id=project_id,
                page_reference=page_reference,
                workflow_state=context.state,
            ),
            rule=V43ValidationRuleDTO(
                rule_id=f"qa-rule:{project_id}:{page_reference}",
                session_id=session_id,
            ),
            checklist=V43ReviewChecklistDTO(session_id=session_id),
            score=V43QualityScoreDTO(session_id=session_id),
            summary=V43QASummary(),
        )

    def operations_monitoring(
        self, project_id: str, context: WorkflowContext
    ) -> V43OperationsMonitoringReport:
        analytics = self._intelligence.project_analytics(project_id, context)
        page_reference = analytics.progress.page_reference
        return V43OperationsMonitoringReport(
            analytics=analytics,
            metrics=V43OperationsMetricsDTO(
                project_id=project_id,
                page_reference=page_reference,
                observed_stage_count=0,
            ),
            timeline=V43ProductionTimelineDTO(
                project_id=project_id,
                page_reference=page_reference,
            ),
            alert=V43AlertDTO(alert_id=f"operations-alert:{project_id}:{page_reference}", project_id=project_id),
            dashboard=V43MonitoringDashboardDTO(project_id=project_id),
            summary=V43OperationsSummary(),
        )

    def platform_reliability(
        self, project_id: str, context: WorkflowContext
    ) -> V43PlatformReliabilityReport:
        analytics = self._intelligence.project_analytics(project_id, context)
        page_reference = analytics.progress.page_reference
        return V43PlatformReliabilityReport(
            analytics=analytics,
            health=V43HealthCheckDTO(project_id=project_id, page_reference=page_reference),
            incident=V43IncidentDTO(
                incident_id=f"incident:{project_id}:{page_reference}",
                project_id=project_id,
                page_reference=page_reference,
            ),
            recovery_policy=V43RecoveryPolicyDTO(
                policy_id=f"recovery-policy:{project_id}",
                project_id=project_id,
            ),
            metrics=V43ReliabilityMetricsDTO(project_id=project_id),
            summary=V43ReliabilitySummary(),
        )
