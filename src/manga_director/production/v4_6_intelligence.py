"""v4.6 Creative Intelligence OS analysis DTOs without side effects.

These Application-layer reports analyze supplied v4.6 foundation evidence. They
cannot collect or persist context, read/write/synchronize memory, update a
model, invoke or delegate agents, make autonomous decisions, mutate or execute
workflows, schedule work, or call an external service.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.production.director import DirectorModel
from manga_director.production.v4_6_intelligence_foundation import (
    AdaptiveWorkflowFoundationReport,
    CreativeReasoningFoundationReport,
    CrossAgentMemoryReport,
    IntelligenceHubFoundationReport,
    UnifiedCreativeContextReport,
    V46IntelligenceFoundationService,
)
from manga_director.workflow.contracts import WorkflowContext


class V46ContextInsightDTO(DirectorModel):
    context_id: str
    page_count: Literal[1] = 1
    reference_count: int = Field(default=1, ge=0)
    provenance_status: Literal["not_assessed"] = "not_assessed"
    freshness_status: Literal["not_assessed"] = "not_assessed"
    context_collected: bool = False


class V46ContextRecommendationDTO(DirectorModel):
    context_id: str
    message: str = "Review supplied provenance, redaction, freshness, and scope."
    context_persisted: bool = False
    automatic_action_taken: bool = False


class ContextIntelligenceReport(DirectorModel):
    foundation: UnifiedCreativeContextReport
    insight: V46ContextInsightDTO
    recommendation: V46ContextRecommendationDTO
    planning_only: bool = True


class V46ReasoningAnalysisDTO(DirectorModel):
    reasoning_id: str
    page_count: Literal[1] = 1
    alternative_count: int = Field(default=0, ge=0)
    evidence_trace_available: bool = False
    analysis_status: Literal["not_assessed"] = "not_assessed"
    model_updated: bool = False
    autonomous_decision_made: bool = False


class V46ReasoningExplanationDTO(DirectorModel):
    reasoning_id: str
    assumptions_explained: bool = False
    uncertainty_explained: bool = False
    human_review_required: bool = True
    recommendation_accepted: bool = False


class ReasoningEngineReport(DirectorModel):
    foundation: CreativeReasoningFoundationReport
    analysis: V46ReasoningAnalysisDTO
    explanation: V46ReasoningExplanationDTO
    planning_only: bool = True


class V46AdaptiveWorkflowInsightDTO(DirectorModel):
    proposal_id: str
    page_count: Literal[1] = 1
    current_state: str
    state_machine_authoritative: bool = True
    dependency_analysis_completed: bool = False
    workflow_mutated: bool = False
    workflow_executed: bool = False


class V46AdaptiveWorkflowRecommendationDTO(DirectorModel):
    proposal_id: str
    message: str = "Require human review of safety, impact, and rollback evidence."
    stage_change_approved: bool = False
    schedule_created: bool = False
    automatic_action_taken: bool = False


class AdaptiveWorkflowIntelligenceReport(DirectorModel):
    foundation: AdaptiveWorkflowFoundationReport
    insight: V46AdaptiveWorkflowInsightDTO
    recommendation: V46AdaptiveWorkflowRecommendationDTO
    planning_only: bool = True


class V46KnowledgeSharingDTO(DirectorModel):
    sharing_id: str
    memory_id: str
    page_count: Literal[1] = 1
    provenance_required: bool = True
    consent_required: bool = True
    redaction_required: bool = True
    knowledge_shared: bool = False
    agent_messaged: bool = False
    memory_synchronized: bool = False


class V46KnowledgeSharingRecommendationDTO(DirectorModel):
    sharing_id: str
    message: str = "Require explicit human consent and provenance review before sharing."
    access_granted: bool = False
    automatic_action_taken: bool = False


class CrossAgentKnowledgeSharingReport(DirectorModel):
    foundation: CrossAgentMemoryReport
    sharing: V46KnowledgeSharingDTO
    recommendation: V46KnowledgeSharingRecommendationDTO
    planning_only: bool = True


class V46IntelligenceDashboardDTO(DirectorModel):
    dashboard_id: str
    project_id: str
    page_reference: str
    page_count: Literal[1] = 1
    context: ContextIntelligenceReport
    reasoning: ReasoningEngineReport
    workflow: AdaptiveWorkflowIntelligenceReport
    knowledge_sharing: CrossAgentKnowledgeSharingReport
    presentation_dependency: bool = False
    dashboard_persisted: bool = False
    dashboard_published: bool = False


class IntelligenceDashboardReport(DirectorModel):
    foundation: IntelligenceHubFoundationReport
    dashboard: V46IntelligenceDashboardDTO
    planning_only: bool = True


class V46IntelligenceService:
    """Build non-executing v4.6 intelligence and dashboard projections."""

    def __init__(self, foundation: V46IntelligenceFoundationService | None = None) -> None:
        self._foundation = foundation or V46IntelligenceFoundationService()

    def context_intelligence(
        self, project_id: str, context: WorkflowContext
    ) -> ContextIntelligenceReport:
        foundation = self._foundation.unified_creative_context(project_id, context)
        return ContextIntelligenceReport(
            foundation=foundation,
            insight=V46ContextInsightDTO(
                context_id=foundation.context.context_id,
                reference_count=foundation.summary.reference_count,
                context_collected=foundation.context.context_collected,
            ),
            recommendation=V46ContextRecommendationDTO(context_id=foundation.context.context_id),
        )

    def reasoning_engine(self, project_id: str, context: WorkflowContext) -> ReasoningEngineReport:
        foundation = self._foundation.creative_reasoning(project_id, context)
        return ReasoningEngineReport(
            foundation=foundation,
            analysis=V46ReasoningAnalysisDTO(
                reasoning_id=foundation.reasoning.reasoning_id,
                alternative_count=foundation.reasoning.alternative_count,
                evidence_trace_available=foundation.reasoning.evidence_trace_available,
            ),
            explanation=V46ReasoningExplanationDTO(reasoning_id=foundation.reasoning.reasoning_id),
        )

    def adaptive_workflow_intelligence(
        self, project_id: str, context: WorkflowContext
    ) -> AdaptiveWorkflowIntelligenceReport:
        foundation = self._foundation.adaptive_workflow(project_id, context)
        return AdaptiveWorkflowIntelligenceReport(
            foundation=foundation,
            insight=V46AdaptiveWorkflowInsightDTO(
                proposal_id=foundation.proposal.proposal_id,
                current_state=foundation.proposal.current_state,
                workflow_mutated=foundation.proposal.workflow_mutated,
                workflow_executed=foundation.proposal.workflow_executed,
            ),
            recommendation=V46AdaptiveWorkflowRecommendationDTO(
                proposal_id=foundation.proposal.proposal_id
            ),
        )

    def knowledge_sharing(
        self, project_id: str, context: WorkflowContext
    ) -> CrossAgentKnowledgeSharingReport:
        foundation = self._foundation.cross_agent_memory(project_id, context)
        sharing_id = f"knowledge-sharing:{project_id}:{foundation.memory.memory_id}"
        return CrossAgentKnowledgeSharingReport(
            foundation=foundation,
            sharing=V46KnowledgeSharingDTO(
                sharing_id=sharing_id,
                memory_id=foundation.memory.memory_id,
                memory_synchronized=foundation.memory.memory_synchronized,
            ),
            recommendation=V46KnowledgeSharingRecommendationDTO(sharing_id=sharing_id),
        )

    def intelligence_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> IntelligenceDashboardReport:
        foundation = self._foundation.intelligence_hub(project_id, context)
        context_report = self.context_intelligence(project_id, context)
        reasoning_report = self.reasoning_engine(project_id, context)
        workflow_report = self.adaptive_workflow_intelligence(project_id, context)
        sharing_report = self.knowledge_sharing(project_id, context)
        return IntelligenceDashboardReport(
            foundation=foundation,
            dashboard=V46IntelligenceDashboardDTO(
                dashboard_id=f"intelligence-dashboard:{project_id}:{foundation.hub.page_reference}",
                project_id=project_id,
                page_reference=foundation.hub.page_reference,
                context=context_report,
                reasoning=reasoning_report,
                workflow=workflow_report,
                knowledge_sharing=sharing_report,
            ),
        )
