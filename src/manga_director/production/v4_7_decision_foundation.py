"""v4.7 Creative Decision Platform foundation DTOs without side effects.

The Application-layer reports describe caller-supplied decision, review,
recommendation, approval, and executive evidence for exactly one existing page.
They cannot collect or persist evidence, select a decision, approve content,
enforce policy, invoke an agent, mutate or execute a workflow, or call an
external service. The domain StateMachine remains the transition authority.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.production.director import DirectorModel
from manga_director.workflow.contracts import WorkflowContext


class V47DecisionContextDTO(DirectorModel):
    decision_id: str
    project_id: str
    page_reference: str
    page_count: Literal[1] = 1
    workflow_state: str
    state_machine_authoritative: bool = True
    evidence_collected: bool = False
    decision_persisted: bool = False


class V47DecisionEvidenceDTO(DirectorModel):
    decision_id: str
    evidence_reference_count: int = Field(default=0, ge=0)
    provenance_required: bool = True
    redaction_required: bool = True
    evidence_loaded: bool = False


class V47DecisionSummary(DirectorModel):
    alternative_count: int = Field(default=0, ge=0)
    risk_count: int = Field(default=0, ge=0)
    human_owner_required: bool = True
    decision_selected: bool = False
    automatic_action_taken: bool = False


class DecisionEngineFoundationReport(DirectorModel):
    context: V47DecisionContextDTO
    evidence: V47DecisionEvidenceDTO
    summary: V47DecisionSummary
    planning_only: bool = True


class V47RecommendationDTO(DirectorModel):
    recommendation_id: str
    decision_id: str
    page_count: Literal[1] = 1
    rationale_required: bool = True
    prerequisites_required: bool = True
    human_review_required: bool = True
    option_selected: bool = False
    recommendation_accepted: bool = False


class V47RecommendationSummary(DirectorModel):
    recommendation_count: int = Field(default=1, ge=0)
    confidence_assessed: bool = False
    action_dispatched: bool = False
    automatic_action_taken: bool = False


class RecommendationFoundationReport(DirectorModel):
    decision: DecisionEngineFoundationReport
    recommendation: V47RecommendationDTO
    summary: V47RecommendationSummary
    planning_only: bool = True


class V47ReviewIntelligenceDTO(DirectorModel):
    review_id: str
    decision_id: str
    page_count: Literal[1] = 1
    finding_count: int = Field(default=0, ge=0)
    review_coverage_assessed: bool = False
    consistency_assessed: bool = False
    review_completed: bool = False
    finding_mutated: bool = False


class V47ReviewIntelligenceSummary(DirectorModel):
    escalation_required: bool = False
    approval_recommended: bool = False
    quality_gate_bypassed: bool = False
    automatic_action_taken: bool = False


class ReviewIntelligenceFoundationReport(DirectorModel):
    recommendation: RecommendationFoundationReport
    review: V47ReviewIntelligenceDTO
    summary: V47ReviewIntelligenceSummary
    planning_only: bool = True


class V47ApprovalWorkflowDTO(DirectorModel):
    approval_request_id: str
    decision_id: str
    page_count: Literal[1] = 1
    state_machine_authoritative: bool = True
    persisted_storyboard_required: bool = True
    completed_quality_review_required: bool = True
    human_approval_required: bool = True
    approval_submitted: bool = False
    approval_granted: bool = False
    workflow_transitioned: bool = False


class V47ApprovalWorkflowSummary(DirectorModel):
    missing_prerequisite_count: int = Field(default=0, ge=0)
    escalation_created: bool = False
    override_granted: bool = False
    automatic_action_taken: bool = False


class ApprovalWorkflowFoundationReport(DirectorModel):
    review: ReviewIntelligenceFoundationReport
    approval: V47ApprovalWorkflowDTO
    summary: V47ApprovalWorkflowSummary
    planning_only: bool = True


class V47ExecutiveDashboardDTO(DirectorModel):
    dashboard_id: str
    project_id: str
    page_reference: str
    page_count: Literal[1] = 1
    decision: DecisionEngineFoundationReport
    recommendation: RecommendationFoundationReport
    review: ReviewIntelligenceFoundationReport
    approval: ApprovalWorkflowFoundationReport
    presentation_dependency: bool = False
    dashboard_persisted: bool = False
    dashboard_published: bool = False


class V47ExecutiveDashboardSummary(DirectorModel):
    decision_health_assessed: bool = False
    organizational_action_taken: bool = False
    telemetry_collected: bool = False
    monitoring_started: bool = False


class ExecutiveDashboardFoundationReport(DirectorModel):
    dashboard: V47ExecutiveDashboardDTO
    summary: V47ExecutiveDashboardSummary
    planning_only: bool = True


class V47DecisionFoundationService:
    """Build non-executing v4.7 Creative Decision Platform foundations."""

    def decision_engine(
        self, project_id: str, context: WorkflowContext
    ) -> DecisionEngineFoundationReport:
        page_reference = _page_reference(context)
        decision_id = f"decision:{project_id}:{page_reference}"
        return DecisionEngineFoundationReport(
            context=V47DecisionContextDTO(
                decision_id=decision_id,
                project_id=project_id,
                page_reference=page_reference,
                workflow_state=context.state.value,
            ),
            evidence=V47DecisionEvidenceDTO(decision_id=decision_id),
            summary=V47DecisionSummary(),
        )

    def recommendation(
        self, project_id: str, context: WorkflowContext
    ) -> RecommendationFoundationReport:
        decision = self.decision_engine(project_id, context)
        return RecommendationFoundationReport(
            decision=decision,
            recommendation=V47RecommendationDTO(
                recommendation_id=f"recommendation:{decision.context.decision_id}",
                decision_id=decision.context.decision_id,
            ),
            summary=V47RecommendationSummary(),
        )

    def review_intelligence(
        self, project_id: str, context: WorkflowContext
    ) -> ReviewIntelligenceFoundationReport:
        recommendation = self.recommendation(project_id, context)
        return ReviewIntelligenceFoundationReport(
            recommendation=recommendation,
            review=V47ReviewIntelligenceDTO(
                review_id=f"review-intelligence:{recommendation.decision.context.decision_id}",
                decision_id=recommendation.decision.context.decision_id,
            ),
            summary=V47ReviewIntelligenceSummary(),
        )

    def approval_workflow(
        self, project_id: str, context: WorkflowContext
    ) -> ApprovalWorkflowFoundationReport:
        review = self.review_intelligence(project_id, context)
        return ApprovalWorkflowFoundationReport(
            review=review,
            approval=V47ApprovalWorkflowDTO(
                approval_request_id=f"approval:{review.review.decision_id}",
                decision_id=review.review.decision_id,
            ),
            summary=V47ApprovalWorkflowSummary(),
        )

    def executive_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> ExecutiveDashboardFoundationReport:
        decision = self.decision_engine(project_id, context)
        recommendation = self.recommendation(project_id, context)
        review = self.review_intelligence(project_id, context)
        approval = self.approval_workflow(project_id, context)
        return ExecutiveDashboardFoundationReport(
            dashboard=V47ExecutiveDashboardDTO(
                dashboard_id=f"executive-dashboard:{project_id}:{decision.context.page_reference}",
                project_id=project_id,
                page_reference=decision.context.page_reference,
                decision=decision,
                recommendation=recommendation,
                review=review,
                approval=approval,
            ),
            summary=V47ExecutiveDashboardSummary(),
        )


def _page_reference(context: WorkflowContext) -> str:
    page_id = context.page.get("id")
    return str(page_id) if page_id is not None else "page"
