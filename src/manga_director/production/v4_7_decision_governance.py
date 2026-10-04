"""v4.7 Creative Decision Platform governance DTOs without side effects.

The Application-layer reports make caller-supplied decision, recommendation,
review, and approval evidence auditable.  They cannot persist or enforce a
policy, complete a review, select a recommendation, grant an approval, change
workflow state, invoke an agent, execute work, or call an external service.
The domain StateMachine remains the transition authority.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.production.director import DirectorModel
from manga_director.production.v4_7_decision_intelligence import (
    ApprovalInsightsReport,
    DecisionIntelligenceReport,
    ExecutiveDecisionDashboardReport,
    RecommendationAnalyticsReport,
    ReviewAnalyticsReport,
    V47DecisionIntelligenceService,
)
from manga_director.workflow.contracts import WorkflowContext


class V47DecisionPolicyDTO(DirectorModel):
    policy_id: str
    decision_id: str
    page_count: Literal[1] = 1
    state_machine_authoritative: bool = True
    persisted_storyboard_required: bool = True
    completed_quality_review_required: bool = True
    human_decision_required: bool = True
    policy_enforced: bool = False
    policy_persisted: bool = False


class V47DecisionComplianceDTO(DirectorModel):
    policy_id: str
    decision_id: str
    page_count: Literal[1] = 1
    storyboard_verified: bool = False
    quality_review_verified: bool = False
    human_decision_verified: bool = False
    compliance_confirmed: bool = False
    autonomous_decision_made: bool = False


class V47DecisionGovernanceSummary(DirectorModel):
    policy_count: int = Field(default=1, ge=0)
    compliance_count: int = Field(default=1, ge=0)
    enforcement_action_count: int = 0
    automatic_action_taken: bool = False


class DecisionGovernanceReport(DirectorModel):
    decision: DecisionIntelligenceReport
    policy: V47DecisionPolicyDTO
    compliance: V47DecisionComplianceDTO
    summary: V47DecisionGovernanceSummary
    planning_only: bool = True


class V47RecommendationPolicyDTO(DirectorModel):
    policy_id: str
    recommendation_id: str
    page_count: Literal[1] = 1
    rationale_required: bool = True
    prerequisites_required: bool = True
    human_review_required: bool = True
    policy_enforced: bool = False
    recommendation_selected: bool = False


class V47RecommendationComplianceDTO(DirectorModel):
    policy_id: str
    recommendation_id: str
    page_count: Literal[1] = 1
    rationale_verified: bool = False
    prerequisites_verified: bool = False
    human_review_verified: bool = False
    compliance_confirmed: bool = False
    recommendation_accepted: bool = False


class V47RecommendationGovernanceSummary(DirectorModel):
    policy_count: int = Field(default=1, ge=0)
    compliance_count: int = Field(default=1, ge=0)
    enforcement_action_count: int = 0
    automatic_action_taken: bool = False


class RecommendationGovernanceReport(DirectorModel):
    recommendation: RecommendationAnalyticsReport
    policy: V47RecommendationPolicyDTO
    compliance: V47RecommendationComplianceDTO
    summary: V47RecommendationGovernanceSummary
    planning_only: bool = True


class V47ReviewAuditDTO(DirectorModel):
    audit_id: str
    review_id: str
    decision_id: str
    page_count: Literal[1] = 1
    finding_trace_required: bool = True
    coverage_trace_required: bool = True
    consistency_trace_required: bool = True
    audit_persisted: bool = False
    review_completed: bool = False
    quality_gate_bypassed: bool = False


class V47ReviewAuditSummary(DirectorModel):
    finding_count: int = Field(default=0, ge=0)
    audit_action_taken: bool = False
    automatic_action_taken: bool = False


class ReviewAuditReport(DirectorModel):
    review: ReviewAnalyticsReport
    audit: V47ReviewAuditDTO
    summary: V47ReviewAuditSummary
    planning_only: bool = True


class V47ApprovalComplianceDTO(DirectorModel):
    compliance_id: str
    approval_request_id: str
    decision_id: str
    page_count: Literal[1] = 1
    state_machine_authoritative: bool = True
    persisted_storyboard_required: bool = True
    completed_quality_review_required: bool = True
    human_approval_required: bool = True
    compliance_confirmed: bool = False
    approval_submitted: bool = False
    approval_granted: bool = False
    workflow_transitioned: bool = False


class V47ApprovalComplianceSummary(DirectorModel):
    prerequisite_count: int = Field(default=3, ge=0)
    access_granted: bool = False
    policy_enforced: bool = False
    automatic_action_taken: bool = False


class ApprovalComplianceReport(DirectorModel):
    approval: ApprovalInsightsReport
    compliance: V47ApprovalComplianceDTO
    summary: V47ApprovalComplianceSummary
    planning_only: bool = True


class V47DecisionReliabilityDTO(DirectorModel):
    reliability_id: str
    project_id: str
    page_reference: str
    page_count: Literal[1] = 1
    health_status: Literal["not_checked"] = "not_checked"
    health_check_executed: bool = False
    failure_detected: bool = False
    monitoring_active: bool = False
    alert_sent: bool = False
    retry_attempted: bool = False
    recovery_attempted: bool = False


class V47DecisionReliabilitySummary(DirectorModel):
    observed_component_count: int = Field(default=5, ge=0)
    incident_count: int = 0
    recovery_count: int = 0
    automatic_action_taken: bool = False


class DecisionReliabilityReport(DirectorModel):
    dashboard: ExecutiveDecisionDashboardReport
    reliability: V47DecisionReliabilityDTO
    summary: V47DecisionReliabilitySummary
    planning_only: bool = True


class V47DecisionGovernanceDashboardDTO(DirectorModel):
    dashboard_id: str
    project_id: str
    page_reference: str
    page_count: Literal[1] = 1
    decision: DecisionGovernanceReport
    recommendation: RecommendationGovernanceReport
    review: ReviewAuditReport
    approval: ApprovalComplianceReport
    reliability: DecisionReliabilityReport
    presentation_dependency: bool = False
    dashboard_persisted: bool = False
    dashboard_published: bool = False


class V47DecisionGovernanceDashboardSummary(DirectorModel):
    governance_health_assessed: bool = False
    organizational_action_taken: bool = False
    telemetry_collected: bool = False
    monitoring_started: bool = False
    automatic_action_taken: bool = False


class ExecutiveDecisionGovernanceDashboardReport(DirectorModel):
    dashboard: V47DecisionGovernanceDashboardDTO
    summary: V47DecisionGovernanceDashboardSummary
    planning_only: bool = True


class V47DecisionGovernanceService:
    """Build non-enforcing, non-operational v4.7 governance evidence reports."""

    def __init__(self, intelligence: V47DecisionIntelligenceService | None = None) -> None:
        self._intelligence = intelligence or V47DecisionIntelligenceService()

    def decision_governance(
        self, project_id: str, context: WorkflowContext
    ) -> DecisionGovernanceReport:
        decision = self._intelligence.decision_intelligence(project_id, context)
        policy_id = f"decision-policy:{decision.analysis.decision_id}"
        return DecisionGovernanceReport(
            decision=decision,
            policy=V47DecisionPolicyDTO(policy_id=policy_id, decision_id=decision.analysis.decision_id),
            compliance=V47DecisionComplianceDTO(
                policy_id=policy_id, decision_id=decision.analysis.decision_id
            ),
            summary=V47DecisionGovernanceSummary(),
        )

    def recommendation_governance(
        self, project_id: str, context: WorkflowContext
    ) -> RecommendationGovernanceReport:
        recommendation = self._intelligence.recommendation_analytics(project_id, context)
        recommendation_id = recommendation.analytics.recommendation_id
        policy_id = f"recommendation-policy:{recommendation_id}"
        return RecommendationGovernanceReport(
            recommendation=recommendation,
            policy=V47RecommendationPolicyDTO(
                policy_id=policy_id, recommendation_id=recommendation_id
            ),
            compliance=V47RecommendationComplianceDTO(
                policy_id=policy_id, recommendation_id=recommendation_id
            ),
            summary=V47RecommendationGovernanceSummary(),
        )

    def review_audit(self, project_id: str, context: WorkflowContext) -> ReviewAuditReport:
        review = self._intelligence.review_analytics(project_id, context)
        audit = V47ReviewAuditDTO(
            audit_id=f"review-audit:{review.analytics.review_id}",
            review_id=review.analytics.review_id,
            decision_id=review.analytics.decision_id,
        )
        return ReviewAuditReport(review=review, audit=audit, summary=V47ReviewAuditSummary())

    def approval_compliance(self, project_id: str, context: WorkflowContext) -> ApprovalComplianceReport:
        approval = self._intelligence.approval_insights(project_id, context)
        insights = approval.insights
        return ApprovalComplianceReport(
            approval=approval,
            compliance=V47ApprovalComplianceDTO(
                compliance_id=f"approval-compliance:{insights.approval_request_id}",
                approval_request_id=insights.approval_request_id,
                decision_id=insights.decision_id,
            ),
            summary=V47ApprovalComplianceSummary(),
        )

    def decision_reliability(
        self, project_id: str, context: WorkflowContext
    ) -> DecisionReliabilityReport:
        dashboard = self._intelligence.executive_decision_dashboard(project_id, context)
        return DecisionReliabilityReport(
            dashboard=dashboard,
            reliability=V47DecisionReliabilityDTO(
                reliability_id=f"decision-reliability:{project_id}:{dashboard.dashboard.page_reference}",
                project_id=project_id,
                page_reference=dashboard.dashboard.page_reference,
            ),
            summary=V47DecisionReliabilitySummary(),
        )

    def executive_decision_governance_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> ExecutiveDecisionGovernanceDashboardReport:
        intelligence = self._intelligence.executive_decision_dashboard(project_id, context)
        page_reference = intelligence.dashboard.page_reference
        return ExecutiveDecisionGovernanceDashboardReport(
            dashboard=V47DecisionGovernanceDashboardDTO(
                dashboard_id=f"executive-decision-governance-dashboard:{project_id}:{page_reference}",
                project_id=project_id,
                page_reference=page_reference,
                decision=self.decision_governance(project_id, context),
                recommendation=self.recommendation_governance(project_id, context),
                review=self.review_audit(project_id, context),
                approval=self.approval_compliance(project_id, context),
                reliability=self.decision_reliability(project_id, context),
            ),
            summary=V47DecisionGovernanceDashboardSummary(),
        )
