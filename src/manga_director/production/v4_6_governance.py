"""v4.6 intelligence governance, observability, and reliability DTOs.

The reports are immutable Application-layer diagnostics over v4.6 intelligence.
They cannot enforce policy, persist context, read/write/share memory, update a
model, invoke agents, mutate/execute a workflow, monitor a runtime, recover, or
call an external service.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.production.director import DirectorModel
from manga_director.production.v4_6_intelligence import (
    AdaptiveWorkflowIntelligenceReport,
    ContextIntelligenceReport,
    IntelligenceDashboardReport,
    ReasoningEngineReport,
    V46IntelligenceService,
)
from manga_director.workflow.contracts import WorkflowContext


class V46IntelligencePolicyDTO(DirectorModel):
    policy_id: str
    project_id: str
    page_reference: str
    state_machine_authoritative: bool = True
    human_review_required: bool = True
    policy_enforced: bool = False
    policy_persisted: bool = False


class V46IntelligenceComplianceDTO(DirectorModel):
    policy_id: str
    page_count: Literal[1] = 1
    storyboard_evidence_required: bool = True
    completed_quality_review_required: bool = True
    compliance_confirmed: bool = False
    autonomous_decision_made: bool = False


class V46IntelligenceGovernanceSummary(DirectorModel):
    policy_count: int = Field(default=1, ge=0)
    compliance_count: int = Field(default=1, ge=0)
    enforcement_action_count: int = 0
    automatic_action_taken: bool = False


class IntelligenceGovernanceReport(DirectorModel):
    dashboard: IntelligenceDashboardReport
    policy: V46IntelligencePolicyDTO
    compliance: V46IntelligenceComplianceDTO
    summary: V46IntelligenceGovernanceSummary
    planning_only: bool = True


class V46ContextGovernanceDTO(DirectorModel):
    policy_id: str
    context_id: str
    provenance_required: bool = True
    redaction_required: bool = True
    consent_required: bool = True
    policy_enforced: bool = False
    context_persisted: bool = False


class V46ContextComplianceDTO(DirectorModel):
    context_id: str
    page_count: Literal[1] = 1
    provenance_confirmed: bool = False
    redaction_confirmed: bool = False
    consent_confirmed: bool = False
    access_granted: bool = False
    context_shared: bool = False


class ContextGovernanceReport(DirectorModel):
    context: ContextIntelligenceReport
    policy: V46ContextGovernanceDTO
    compliance: V46ContextComplianceDTO
    planning_only: bool = True


class V46ReasoningAuditDTO(DirectorModel):
    audit_id: str
    reasoning_id: str
    page_count: Literal[1] = 1
    evidence_trace_required: bool = True
    uncertainty_explanation_required: bool = True
    audit_persisted: bool = False
    model_updated: bool = False
    autonomous_decision_made: bool = False


class V46ReasoningAuditSummary(DirectorModel):
    finding_count: int = 0
    audit_action_taken: bool = False
    automatic_action_taken: bool = False


class ReasoningAuditReport(DirectorModel):
    reasoning: ReasoningEngineReport
    audit: V46ReasoningAuditDTO
    summary: V46ReasoningAuditSummary
    planning_only: bool = True


class V46WorkflowObservabilityDTO(DirectorModel):
    observation_id: str
    proposal_id: str
    page_count: Literal[1] = 1
    current_state: str
    state_machine_authoritative: bool = True
    timeline_entry_count: int = Field(default=0, ge=0)
    metrics_collected: bool = False
    monitoring_active: bool = False
    workflow_executed: bool = False


class V46WorkflowObservabilitySummary(DirectorModel):
    trace_available: bool = False
    alert_sent: bool = False
    operational_action_taken: bool = False


class WorkflowObservabilityReport(DirectorModel):
    workflow: AdaptiveWorkflowIntelligenceReport
    observation: V46WorkflowObservabilityDTO
    summary: V46WorkflowObservabilitySummary
    planning_only: bool = True


class V46IntelligenceReliabilityDTO(DirectorModel):
    reliability_id: str
    project_id: str
    page_reference: str
    health_status: Literal["not_checked"] = "not_checked"
    health_check_executed: bool = False
    failure_detected: bool = False
    monitoring_active: bool = False
    alert_sent: bool = False
    retry_attempted: bool = False
    recovery_attempted: bool = False


class V46IntelligenceReliabilitySummary(DirectorModel):
    observed_component_count: int = Field(default=5, ge=0)
    incident_count: int = 0
    recovery_count: int = 0
    automatic_action_taken: bool = False


class IntelligenceReliabilityReport(DirectorModel):
    dashboard: IntelligenceDashboardReport
    reliability: V46IntelligenceReliabilityDTO
    summary: V46IntelligenceReliabilitySummary
    planning_only: bool = True


class IntelligenceOperationsValidationReport(DirectorModel):
    governance: IntelligenceGovernanceReport
    context: ContextGovernanceReport
    reasoning: ReasoningAuditReport
    workflow: WorkflowObservabilityReport
    reliability: IntelligenceReliabilityReport
    end_to_end_validated: bool = True
    workflow_executed: bool = False
    planning_only: bool = True


class V46IntelligenceGovernanceService:
    """Build non-enforcing v4.6 intelligence operations evidence reports."""

    def __init__(self, intelligence: V46IntelligenceService | None = None) -> None:
        self._intelligence = intelligence or V46IntelligenceService()

    def intelligence_governance(
        self, project_id: str, context: WorkflowContext
    ) -> IntelligenceGovernanceReport:
        dashboard = self._intelligence.intelligence_dashboard(project_id, context)
        page_reference = dashboard.dashboard.page_reference
        policy_id = f"intelligence-policy:{project_id}:{page_reference}"
        return IntelligenceGovernanceReport(
            dashboard=dashboard,
            policy=V46IntelligencePolicyDTO(
                policy_id=policy_id,
                project_id=project_id,
                page_reference=page_reference,
            ),
            compliance=V46IntelligenceComplianceDTO(policy_id=policy_id),
            summary=V46IntelligenceGovernanceSummary(),
        )

    def context_governance(self, project_id: str, context: WorkflowContext) -> ContextGovernanceReport:
        context_report = self._intelligence.context_intelligence(project_id, context)
        context_id = context_report.foundation.context.context_id
        policy_id = f"context-policy:{project_id}:{context_id}"
        return ContextGovernanceReport(
            context=context_report,
            policy=V46ContextGovernanceDTO(policy_id=policy_id, context_id=context_id),
            compliance=V46ContextComplianceDTO(context_id=context_id),
        )

    def reasoning_audit(self, project_id: str, context: WorkflowContext) -> ReasoningAuditReport:
        reasoning = self._intelligence.reasoning_engine(project_id, context)
        reasoning_id = reasoning.analysis.reasoning_id
        return ReasoningAuditReport(
            reasoning=reasoning,
            audit=V46ReasoningAuditDTO(
                audit_id=f"reasoning-audit:{project_id}:{reasoning_id}", reasoning_id=reasoning_id
            ),
            summary=V46ReasoningAuditSummary(),
        )

    def workflow_observability(
        self, project_id: str, context: WorkflowContext
    ) -> WorkflowObservabilityReport:
        workflow = self._intelligence.adaptive_workflow_intelligence(project_id, context)
        proposal = workflow.insight
        return WorkflowObservabilityReport(
            workflow=workflow,
            observation=V46WorkflowObservabilityDTO(
                observation_id=f"workflow-observability:{project_id}:{proposal.proposal_id}",
                proposal_id=proposal.proposal_id,
                current_state=proposal.current_state,
                workflow_executed=proposal.workflow_executed,
            ),
            summary=V46WorkflowObservabilitySummary(),
        )

    def intelligence_reliability(
        self, project_id: str, context: WorkflowContext
    ) -> IntelligenceReliabilityReport:
        dashboard = self._intelligence.intelligence_dashboard(project_id, context)
        return IntelligenceReliabilityReport(
            dashboard=dashboard,
            reliability=V46IntelligenceReliabilityDTO(
                reliability_id=f"intelligence-reliability:{project_id}",
                project_id=project_id,
                page_reference=dashboard.dashboard.page_reference,
            ),
            summary=V46IntelligenceReliabilitySummary(),
        )

    def operations_validation(
        self, project_id: str, context: WorkflowContext
    ) -> IntelligenceOperationsValidationReport:
        return IntelligenceOperationsValidationReport(
            governance=self.intelligence_governance(project_id, context),
            context=self.context_governance(project_id, context),
            reasoning=self.reasoning_audit(project_id, context),
            workflow=self.workflow_observability(project_id, context),
            reliability=self.intelligence_reliability(project_id, context),
        )
