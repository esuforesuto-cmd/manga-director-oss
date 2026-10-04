"""Contract tests for v5.2 advisory Automation Intelligence."""

from __future__ import annotations

from manga_director.platform import (
    AutomationEngineFoundation,
    AutomationEventDTO,
    AutomationIntelligenceService,
    AutomationRegistryFoundation,
    AutomationRequestDTO,
    AutomationRuleDTO,
    EventBusFoundation,
    UnifiedSDKFoundation,
    WorkflowTemplateDTO,
)


def _engine(page_reference: str = "page-001") -> AutomationEngineFoundation:
    template = WorkflowTemplateDTO(
        template_id="storyboard-review",
        title="Storyboard review",
        owner="creative-operations",
        page_reference=page_reference,
        required_evidence=("storyboard", "quality-review"),
    )
    rule = AutomationRuleDTO(
        rule_id="review-ready",
        title="Review readiness",
        owner="creative-operations",
        required_evidence=("storyboard", "quality-review"),
    )
    event = AutomationEventDTO(
        event_id="review-completed",
        event_type="quality-review.completed",
        producer="quality-review",
        page_reference=page_reference,
        provenance="caller-supplied",
        correlation_id="review-001",
    )
    return AutomationEngineFoundation(
        registry=AutomationRegistryFoundation((template,), (rule,)),
        event_bus=EventBusFoundation((event,)),
    )


def _request(approval_boundary: str | None = "editor-review") -> AutomationRequestDTO:
    return AutomationRequestDTO(
        template_id="storyboard-review",
        rule_id="review-ready",
        event_id="review-completed",
        evidence_types=("storyboard", "quality-review"),
        approval_boundary=approval_boundary,
    )


def test_automation_intelligence_is_human_gated_and_non_executing() -> None:
    dashboard = AutomationIntelligenceService(_engine()).preview(_request())

    assert dashboard.automation.health == "ready_for_human_review"
    assert dashboard.automation.human_review_required is True
    assert dashboard.automation.autonomous_decision_made is False
    assert dashboard.automation.execution_performed is False
    assert dashboard.planning_only is True


def test_rule_analytics_reports_evidence_coverage_without_rule_learning() -> None:
    dashboard = AutomationIntelligenceService(_engine()).preview(_request())

    assert dashboard.rule_analytics.rule_id == "review-ready"
    assert dashboard.rule_analytics.required_evidence_count == 2
    assert dashboard.rule_analytics.supplied_evidence_count == 2
    assert dashboard.rule_analytics.missing_evidence == ()
    assert dashboard.rule_analytics.safety_boundary_preserved is True


def test_event_processing_intelligence_never_starts_delivery() -> None:
    dashboard = AutomationIntelligenceService(_engine()).preview(_request())

    assert dashboard.event_processing.event_known is True
    assert dashboard.event_processing.provenance == "caller-supplied"
    assert dashboard.event_processing.correlation_present is True
    assert dashboard.event_processing.dispatch_started is False
    assert dashboard.event_processing.processing_performed is False


def test_workflow_optimization_is_an_advisory_and_preserves_state_machine() -> None:
    dashboard = AutomationIntelligenceService(_engine()).preview(_request())

    report = dashboard.workflow_optimization
    assert report.template_id == "storyboard-review"
    assert report.page_count == 1
    assert report.evidence_coverage_complete is True
    assert report.state_machine_authoritative is True
    assert report.optimization_applied is False
    assert report.workflow_mutated is False


def test_dashboard_surfaces_missing_human_approval_without_approving() -> None:
    dashboard = UnifiedSDKFoundation(automation=_engine()).automation_dashboard(
        _request(approval_boundary=None)
    )

    assert dashboard.automation.health == "attention_required"
    assert dashboard.rule_analytics.eligible_for_human_review is True
    assert "declare a human approval boundary" in dashboard.workflow_optimization.recommendations
    assert dashboard.human_review_required is True
