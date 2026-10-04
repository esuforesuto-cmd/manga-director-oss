"""v4.6 Creative Intelligence OS foundation DTOs without side effects.

The module provides immutable Application-layer projections for caller-supplied
creative context, cross-agent memory references, reasoning, intelligence-hub,
and adaptive-workflow evidence. It cannot collect or persist context, read or
write shared memory, invoke agents, decide autonomously, mutate or execute a
workflow, schedule work, or call an external service. The domain StateMachine
remains the transition authority.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.production.director import DirectorModel
from manga_director.workflow.contracts import WorkflowContext


class V46UnifiedCreativeContextDTO(DirectorModel):
    context_id: str
    project_id: str
    page_reference: str
    page_count: Literal[1] = 1
    workflow_state: str
    context_collected: bool = False
    context_persisted: bool = False


class V46ContextProvenanceDTO(DirectorModel):
    context_id: str
    source_supplied: bool = True
    provenance_recorded: bool = False
    redaction_required: bool = True
    freshness_assessed: bool = False


class V46ContextSummary(DirectorModel):
    reference_count: int = Field(default=1, ge=0)
    implicit_collection_performed: bool = False
    automatic_action_taken: bool = False


class UnifiedCreativeContextReport(DirectorModel):
    context: V46UnifiedCreativeContextDTO
    provenance: V46ContextProvenanceDTO
    summary: V46ContextSummary
    planning_only: bool = True


class V46CrossAgentMemoryDTO(DirectorModel):
    memory_id: str
    context_id: str
    source_agent_reference: str = "not_accessed"
    page_count: Literal[1] = 1
    memory_read: bool = False
    memory_written: bool = False
    memory_synchronized: bool = False


class V46MemoryConsentDTO(DirectorModel):
    memory_id: str
    provenance_required: bool = True
    consent_required: bool = True
    redaction_required: bool = True
    access_granted: bool = False


class V46CrossAgentMemorySummary(DirectorModel):
    reference_count: int = Field(default=1, ge=0)
    conflict_count: int = 0
    automatic_retrieval_performed: bool = False
    automatic_action_taken: bool = False


class CrossAgentMemoryReport(DirectorModel):
    context: UnifiedCreativeContextReport
    memory: V46CrossAgentMemoryDTO
    consent: V46MemoryConsentDTO
    summary: V46CrossAgentMemorySummary
    planning_only: bool = True


class V46CreativeReasoningDTO(DirectorModel):
    reasoning_id: str
    context_id: str
    page_count: Literal[1] = 1
    alternative_count: int = Field(default=0, ge=0)
    evidence_trace_available: bool = False
    autonomous_inference_performed: bool = False
    content_generated: bool = False


class V46ReasoningRecommendationDTO(DirectorModel):
    reasoning_id: str
    message: str = "Require human review of supplied evidence and alternatives."
    confidence_assessed: bool = False
    human_review_required: bool = True
    recommendation_accepted: bool = False


class V46CreativeReasoningSummary(DirectorModel):
    reasoning_count: int = Field(default=1, ge=0)
    agent_delegated: bool = False
    automatic_action_taken: bool = False


class CreativeReasoningFoundationReport(DirectorModel):
    context: UnifiedCreativeContextReport
    memory: CrossAgentMemoryReport
    reasoning: V46CreativeReasoningDTO
    recommendation: V46ReasoningRecommendationDTO
    summary: V46CreativeReasoningSummary
    planning_only: bool = True


class V46AdaptiveWorkflowDTO(DirectorModel):
    proposal_id: str
    project_id: str
    page_reference: str
    page_count: Literal[1] = 1
    current_state: str
    state_machine_authoritative: bool = True
    workflow_mutated: bool = False
    workflow_executed: bool = False


class V46AdaptiveWorkflowSafetyDTO(DirectorModel):
    proposal_id: str
    storyboard_required: bool = True
    quality_review_required: bool = True
    human_approval_required: bool = True
    rollback_plan_required: bool = True
    stage_skipped: bool = False


class V46AdaptiveWorkflowSummary(DirectorModel):
    proposal_count: int = Field(default=1, ge=0)
    schedule_created: bool = False
    recovery_attempted: bool = False
    automatic_action_taken: bool = False


class AdaptiveWorkflowFoundationReport(DirectorModel):
    context: UnifiedCreativeContextReport
    proposal: V46AdaptiveWorkflowDTO
    safety: V46AdaptiveWorkflowSafetyDTO
    summary: V46AdaptiveWorkflowSummary
    planning_only: bool = True


class V46IntelligenceHubDTO(DirectorModel):
    hub_id: str
    project_id: str
    page_reference: str
    page_count: Literal[1] = 1
    report_count: int = Field(default=4, ge=0)
    presentation_dependency: bool = False
    hub_persisted: bool = False
    telemetry_collected: bool = False


class V46IntelligenceHubSummary(DirectorModel):
    context_composed: bool = True
    human_review_required: bool = True
    published: bool = False
    operational_action_taken: bool = False


class IntelligenceHubFoundationReport(DirectorModel):
    context: UnifiedCreativeContextReport
    memory: CrossAgentMemoryReport
    reasoning: CreativeReasoningFoundationReport
    adaptive_workflow: AdaptiveWorkflowFoundationReport
    hub: V46IntelligenceHubDTO
    summary: V46IntelligenceHubSummary
    planning_only: bool = True


class V46IntelligenceFoundationService:
    """Build non-executing v4.6 Creative Intelligence OS foundation reports."""

    def unified_creative_context(
        self, project_id: str, context: WorkflowContext
    ) -> UnifiedCreativeContextReport:
        page_reference = _page_reference(context)
        context_id = f"creative-context:{project_id}:{page_reference}"
        return UnifiedCreativeContextReport(
            context=V46UnifiedCreativeContextDTO(
                context_id=context_id,
                project_id=project_id,
                page_reference=page_reference,
                workflow_state=context.state.value,
            ),
            provenance=V46ContextProvenanceDTO(context_id=context_id),
            summary=V46ContextSummary(),
        )

    def cross_agent_memory(self, project_id: str, context: WorkflowContext) -> CrossAgentMemoryReport:
        context_report = self.unified_creative_context(project_id, context)
        memory_id = f"cross-agent-memory:{project_id}:{_page_reference(context)}"
        return CrossAgentMemoryReport(
            context=context_report,
            memory=V46CrossAgentMemoryDTO(memory_id=memory_id, context_id=context_report.context.context_id),
            consent=V46MemoryConsentDTO(memory_id=memory_id),
            summary=V46CrossAgentMemorySummary(),
        )

    def creative_reasoning(
        self, project_id: str, context: WorkflowContext
    ) -> CreativeReasoningFoundationReport:
        context_report = self.unified_creative_context(project_id, context)
        memory_report = self.cross_agent_memory(project_id, context)
        reasoning_id = f"creative-reasoning:{project_id}:{_page_reference(context)}"
        return CreativeReasoningFoundationReport(
            context=context_report,
            memory=memory_report,
            reasoning=V46CreativeReasoningDTO(
                reasoning_id=reasoning_id, context_id=context_report.context.context_id
            ),
            recommendation=V46ReasoningRecommendationDTO(reasoning_id=reasoning_id),
            summary=V46CreativeReasoningSummary(),
        )

    def adaptive_workflow(
        self, project_id: str, context: WorkflowContext
    ) -> AdaptiveWorkflowFoundationReport:
        context_report = self.unified_creative_context(project_id, context)
        proposal_id = f"adaptive-workflow:{project_id}:{_page_reference(context)}"
        return AdaptiveWorkflowFoundationReport(
            context=context_report,
            proposal=V46AdaptiveWorkflowDTO(
                proposal_id=proposal_id,
                project_id=project_id,
                page_reference=_page_reference(context),
                current_state=context.state.value,
            ),
            safety=V46AdaptiveWorkflowSafetyDTO(proposal_id=proposal_id),
            summary=V46AdaptiveWorkflowSummary(),
        )

    def intelligence_hub(
        self, project_id: str, context: WorkflowContext
    ) -> IntelligenceHubFoundationReport:
        context_report = self.unified_creative_context(project_id, context)
        memory_report = self.cross_agent_memory(project_id, context)
        reasoning_report = self.creative_reasoning(project_id, context)
        workflow_report = self.adaptive_workflow(project_id, context)
        return IntelligenceHubFoundationReport(
            context=context_report,
            memory=memory_report,
            reasoning=reasoning_report,
            adaptive_workflow=workflow_report,
            hub=V46IntelligenceHubDTO(
                hub_id=f"intelligence-hub:{project_id}:{_page_reference(context)}",
                project_id=project_id,
                page_reference=_page_reference(context),
            ),
            summary=V46IntelligenceHubSummary(),
        )


def _page_reference(context: WorkflowContext) -> str:
    page_id = context.page.get("id")
    return str(page_id) if page_id is not None else "page"
