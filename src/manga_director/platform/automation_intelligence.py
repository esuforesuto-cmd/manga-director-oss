"""v5.2 advisory intelligence for the human-gated Automation Foundation.

The services in this module analyze only local Automation Foundation reports.
They never execute a plan, dispatch an event, alter a workflow, learn from
history, or decide on behalf of a human reviewer.
"""

from __future__ import annotations

from manga_director.platform.automation import (
    AutomationEngineFoundation,
    AutomationEngineReport,
    AutomationRequestDTO,
)
from manga_director.production.director import DirectorModel


class AutomationIntelligenceDTO(DirectorModel):
    """A transparent, non-actionable intelligence summary for one preview."""

    automation_id: str | None = None
    health: str
    finding_count: int
    human_review_required: bool = True
    autonomous_decision_made: bool = False
    execution_performed: bool = False
    recommendation: str
    planning_only: bool = True


class RuleAnalyticsDTO(DirectorModel):
    """Evidence and safety analytics for the one evaluated explicit rule."""

    rule_id: str | None = None
    required_evidence_count: int = 0
    supplied_evidence_count: int = 0
    missing_evidence: tuple[str, ...] = ()
    eligible_for_human_review: bool = False
    safety_boundary_preserved: bool = True
    recommendation: str
    planning_only: bool = True


class EventProcessingIntelligenceDTO(DirectorModel):
    """Event-reference diagnostics; no event processing is performed."""

    event_id: str | None = None
    event_known: bool = False
    provenance: str | None = None
    correlation_present: bool = False
    local_event_count: int = 0
    dispatch_started: bool = False
    processing_performed: bool = False
    recommendation: str
    planning_only: bool = True


class WorkflowOptimizationReport(DirectorModel):
    """A human-readable recommendation without workflow optimization action."""

    template_id: str | None = None
    page_count: int | None = None
    evidence_coverage_complete: bool = False
    page_reference_consistent: bool = False
    state_machine_authoritative: bool = True
    recommendations: tuple[str, ...] = ()
    optimization_applied: bool = False
    workflow_mutated: bool = False
    planning_only: bool = True


class AutomationDashboardDTO(DirectorModel):
    """Presentation-neutral dashboard payload for an automation preview."""

    automation: AutomationIntelligenceDTO
    rule_analytics: RuleAnalyticsDTO
    event_processing: EventProcessingIntelligenceDTO
    workflow_optimization: WorkflowOptimizationReport
    state_machine_authoritative: bool = True
    human_review_required: bool = True
    planning_only: bool = True


class AutomationIntelligenceService:
    """Composes deterministic diagnostics from the additive engine preview."""

    def __init__(self, engine: AutomationEngineFoundation | None = None) -> None:
        self._engine = engine or AutomationEngineFoundation()

    def preview(self, request: AutomationRequestDTO) -> AutomationDashboardDTO:
        """Returns analysis only; caller retains all approval and execution control."""

        report = self._engine.preview(request)
        return AutomationDashboardDTO(
            automation=self._automation_intelligence(report),
            rule_analytics=self._rule_analytics(report, request),
            event_processing=self._event_processing(report, request),
            workflow_optimization=self._workflow_optimization(report),
            state_machine_authoritative=report.state_machine_authoritative,
            human_review_required=report.human_review_required,
        )

    @staticmethod
    def _automation_intelligence(report: AutomationEngineReport) -> AutomationIntelligenceDTO:
        plan = report.plan
        healthy = plan is not None and plan.eligible_for_human_review and not report.findings
        return AutomationIntelligenceDTO(
            automation_id=plan.automation_id if plan else None,
            health="ready_for_human_review" if healthy else "attention_required",
            finding_count=len(report.findings),
            recommendation=(
                "present the advisory plan to the declared human approval boundary"
                if healthy
                else "resolve the reported evidence or approval-boundary findings before review"
            ),
        )

    @staticmethod
    def _rule_analytics(
        report: AutomationEngineReport, request: AutomationRequestDTO
    ) -> RuleAnalyticsDTO:
        rule_report = report.rule
        rule = rule_report.rule if rule_report else None
        missing = rule_report.missing_evidence if rule_report else ()
        safety_preserved = bool(
            rule
            and rule.human_review_required
            and not rule.execution_enabled
            and not rule.self_learning_enabled
            and not rule.automatic_approval_enabled
        )
        return RuleAnalyticsDTO(
            rule_id=rule.rule_id if rule else None,
            required_evidence_count=len(rule.required_evidence) if rule else 0,
            supplied_evidence_count=len(set(request.evidence_types)),
            missing_evidence=missing,
            eligible_for_human_review=bool(rule_report and rule_report.eligible),
            safety_boundary_preserved=safety_preserved,
            recommendation=(
                "retain the explicit rule and human review boundary"
                if rule_report and rule_report.eligible
                else "supply missing evidence or correct the explicit rule safety flags"
            ),
        )

    @staticmethod
    def _event_processing(
        report: AutomationEngineReport, request: AutomationRequestDTO
    ) -> EventProcessingIntelligenceDTO:
        event = next(
            (item for item in report.event_bus.events if item.event_id == request.event_id),
            None,
        )
        return EventProcessingIntelligenceDTO(
            event_id=event.event_id if event else None,
            event_known=event is not None,
            provenance=event.provenance if event else None,
            correlation_present=bool(event and event.correlation_id),
            local_event_count=report.event_bus.event_count,
            dispatch_started=report.event_bus.dispatch_started,
            recommendation=(
                "retain the supplied event as review evidence; no delivery is required"
                if event
                else "supply a known, caller-provenanced event before human review"
            ),
        )

    @staticmethod
    def _workflow_optimization(report: AutomationEngineReport) -> WorkflowOptimizationReport:
        template_report = report.template
        template = template_report.template if template_report else None
        page_reference_consistent = "event and template page references differ" not in report.findings
        recommendations: list[str] = []
        if template_report is None:
            recommendations.append("select a known single-Page workflow template")
        elif template_report.missing_evidence:
            recommendations.append("provide the template's required workflow evidence")
        if not page_reference_consistent:
            recommendations.append("align event and template Page references")
        if report.plan and report.plan.approval_boundary is None:
            recommendations.append("declare a human approval boundary")
        if not recommendations:
            recommendations.append("retain the existing workflow; no optimization is applied")
        return WorkflowOptimizationReport(
            template_id=template.template_id if template else None,
            page_count=template.page_count if template else None,
            evidence_coverage_complete=bool(template_report and template_report.valid),
            page_reference_consistent=page_reference_consistent,
            recommendations=tuple(recommendations),
        )
