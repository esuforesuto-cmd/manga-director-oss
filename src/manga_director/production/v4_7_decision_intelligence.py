"""v4.7 Creative Decision Platform analysis DTOs without side effects.

The Application-layer reports analyze caller-supplied v4.7 foundation evidence.
They cannot collect or persist decision evidence, select an option, approve a
request, enforce policy, invoke an agent, mutate or execute a workflow, or call
an external service. The domain StateMachine remains the transition authority.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.production.director import DirectorModel
from manga_director.production.v4_7_decision_foundation import (
    ApprovalWorkflowFoundationReport,
    DecisionEngineFoundationReport,
    ExecutiveDashboardFoundationReport,
    RecommendationFoundationReport,
    ReviewIntelligenceFoundationReport,
    V47DecisionFoundationService,
)
from manga_director.workflow.contracts import WorkflowContext


class V47DecisionIntelligenceDTO(DirectorModel):
    analysis_id: str
    decision_id: str
    page_count: Literal[1] = 1
    evidence_coverage_assessed: bool = False
    alternatives_compared: bool = False
    risk_assessed: bool = False
    uncertainty_explained: bool = False
    decision_recommended: bool = False
    autonomous_decision_made: bool = False


class V47DecisionIntelligenceSummary(DirectorModel):
    insight_count: int = Field(default=1, ge=0)
    human_review_required: bool = True
    decision_selected: bool = False
    automatic_action_taken: bool = False


class DecisionIntelligenceReport(DirectorModel):
    foundation: DecisionEngineFoundationReport
    analysis: V47DecisionIntelligenceDTO
    summary: V47DecisionIntelligenceSummary
    planning_only: bool = True


class V47RecommendationAnalyticsDTO(DirectorModel):
    analytics_id: str
    recommendation_id: str
    decision_id: str
    page_count: Literal[1] = 1
    rationale_coverage_assessed: bool = False
    prerequisite_coverage_assessed: bool = False
    impact_compared: bool = False
    confidence_assessed: bool = False
    option_ranked: bool = False
    recommendation_accepted: bool = False


class V47RecommendationAnalyticsSummary(DirectorModel):
    comparison_count: int = Field(default=0, ge=0)
    human_review_required: bool = True
    action_dispatched: bool = False
    automatic_action_taken: bool = False


class RecommendationAnalyticsReport(DirectorModel):
    foundation: RecommendationFoundationReport
    analytics: V47RecommendationAnalyticsDTO
    summary: V47RecommendationAnalyticsSummary
    planning_only: bool = True


class V47ReviewAnalyticsDTO(DirectorModel):
    analytics_id: str
    review_id: str
    decision_id: str
    page_count: Literal[1] = 1
    finding_trend_assessed: bool = False
    coverage_assessed: bool = False
    consistency_assessed: bool = False
    escalation_assessed: bool = False
    review_completed: bool = False
    quality_gate_bypassed: bool = False


class V47ReviewAnalyticsSummary(DirectorModel):
    insight_count: int = Field(default=1, ge=0)
    human_review_required: bool = True
    finding_mutated: bool = False
    automatic_action_taken: bool = False


class ReviewAnalyticsReport(DirectorModel):
    foundation: ReviewIntelligenceFoundationReport
    analytics: V47ReviewAnalyticsDTO
    summary: V47ReviewAnalyticsSummary
    planning_only: bool = True


class V47ApprovalInsightsDTO(DirectorModel):
    insight_id: str
    approval_request_id: str
    decision_id: str
    page_count: Literal[1] = 1
    prerequisite_readiness_assessed: bool = False
    escalation_assessed: bool = False
    override_rationale_assessed: bool = False
    human_approval_required: bool = True
    approval_submitted: bool = False
    approval_granted: bool = False
    workflow_transitioned: bool = False


class V47ApprovalInsightsSummary(DirectorModel):
    insight_count: int = Field(default=1, ge=0)
    access_granted: bool = False
    policy_enforced: bool = False
    automatic_action_taken: bool = False


class ApprovalInsightsReport(DirectorModel):
    foundation: ApprovalWorkflowFoundationReport
    insights: V47ApprovalInsightsDTO
    summary: V47ApprovalInsightsSummary
    planning_only: bool = True


class V47ExecutiveDecisionDashboardDTO(DirectorModel):
    dashboard_id: str
    project_id: str
    page_reference: str
    page_count: Literal[1] = 1
    decision: DecisionIntelligenceReport
    recommendation: RecommendationAnalyticsReport
    review: ReviewAnalyticsReport
    approval: ApprovalInsightsReport
    presentation_dependency: bool = False
    dashboard_persisted: bool = False
    dashboard_published: bool = False


class V47ExecutiveDecisionDashboardSummary(DirectorModel):
    decision_health_assessed: bool = False
    organizational_action_taken: bool = False
    telemetry_collected: bool = False
    monitoring_started: bool = False
    automatic_action_taken: bool = False


class ExecutiveDecisionDashboardReport(DirectorModel):
    foundation: ExecutiveDashboardFoundationReport
    dashboard: V47ExecutiveDecisionDashboardDTO
    summary: V47ExecutiveDecisionDashboardSummary
    planning_only: bool = True


class V47DecisionIntelligenceService:
    """Build non-executing v4.7 decision-analysis and dashboard reports."""

    def __init__(self, foundation: V47DecisionFoundationService | None = None) -> None:
        self._foundation = foundation or V47DecisionFoundationService()

    def decision_intelligence(
        self, project_id: str, context: WorkflowContext
    ) -> DecisionIntelligenceReport:
        foundation = self._foundation.decision_engine(project_id, context)
        decision_id = foundation.context.decision_id
        return DecisionIntelligenceReport(
            foundation=foundation,
            analysis=V47DecisionIntelligenceDTO(
                analysis_id=f"decision-intelligence:{decision_id}", decision_id=decision_id
            ),
            summary=V47DecisionIntelligenceSummary(),
        )

    def recommendation_analytics(
        self, project_id: str, context: WorkflowContext
    ) -> RecommendationAnalyticsReport:
        foundation = self._foundation.recommendation(project_id, context)
        recommendation = foundation.recommendation
        return RecommendationAnalyticsReport(
            foundation=foundation,
            analytics=V47RecommendationAnalyticsDTO(
                analytics_id=f"recommendation-analytics:{recommendation.recommendation_id}",
                recommendation_id=recommendation.recommendation_id,
                decision_id=recommendation.decision_id,
            ),
            summary=V47RecommendationAnalyticsSummary(),
        )

    def review_analytics(self, project_id: str, context: WorkflowContext) -> ReviewAnalyticsReport:
        foundation = self._foundation.review_intelligence(project_id, context)
        review = foundation.review
        return ReviewAnalyticsReport(
            foundation=foundation,
            analytics=V47ReviewAnalyticsDTO(
                analytics_id=f"review-analytics:{review.review_id}",
                review_id=review.review_id,
                decision_id=review.decision_id,
            ),
            summary=V47ReviewAnalyticsSummary(),
        )

    def approval_insights(self, project_id: str, context: WorkflowContext) -> ApprovalInsightsReport:
        foundation = self._foundation.approval_workflow(project_id, context)
        approval = foundation.approval
        return ApprovalInsightsReport(
            foundation=foundation,
            insights=V47ApprovalInsightsDTO(
                insight_id=f"approval-insights:{approval.approval_request_id}",
                approval_request_id=approval.approval_request_id,
                decision_id=approval.decision_id,
            ),
            summary=V47ApprovalInsightsSummary(),
        )

    def executive_decision_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> ExecutiveDecisionDashboardReport:
        foundation = self._foundation.executive_dashboard(project_id, context)
        decision = self.decision_intelligence(project_id, context)
        recommendation = self.recommendation_analytics(project_id, context)
        review = self.review_analytics(project_id, context)
        approval = self.approval_insights(project_id, context)
        return ExecutiveDecisionDashboardReport(
            foundation=foundation,
            dashboard=V47ExecutiveDecisionDashboardDTO(
                dashboard_id=f"executive-decision-dashboard:{project_id}:{foundation.dashboard.page_reference}",
                project_id=project_id,
                page_reference=foundation.dashboard.page_reference,
                decision=decision,
                recommendation=recommendation,
                review=review,
                approval=approval,
            ),
            summary=V47ExecutiveDecisionDashboardSummary(),
        )
