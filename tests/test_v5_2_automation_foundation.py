"""Contract tests for the v5.2 human-gated automation foundation."""

from __future__ import annotations

import pytest

from manga_director.platform import (
    AutomationEngineFoundation,
    AutomationEventDTO,
    AutomationRegistryFoundation,
    AutomationRequestDTO,
    AutomationRuleDTO,
    EventBusFoundation,
    RuleEngineFoundation,
    UnifiedSDKFoundation,
    WorkflowTemplateDTO,
    WorkflowTemplateFoundation,
)


def _template() -> WorkflowTemplateDTO:
    return WorkflowTemplateDTO(
        template_id="storyboard-review",
        title="Storyboard review",
        owner="creative-operations",
        page_reference="page-001",
        required_evidence=("storyboard", "quality-review"),
    )


def _rule() -> AutomationRuleDTO:
    return AutomationRuleDTO(
        rule_id="review-ready",
        title="Review readiness",
        owner="creative-operations",
        required_evidence=("storyboard", "quality-review"),
    )


def _event() -> AutomationEventDTO:
    return AutomationEventDTO(
        event_id="review-completed",
        event_type="quality-review.completed",
        producer="quality-review",
        page_reference="page-001",
        provenance="caller-supplied",
    )


def _engine() -> AutomationEngineFoundation:
    registry = AutomationRegistryFoundation((_template(),), (_rule(),))
    event_bus = EventBusFoundation((_event(),))
    return AutomationEngineFoundation(registry=registry, event_bus=event_bus)


def test_workflow_template_is_single_page_human_review_validation_only() -> None:
    report = WorkflowTemplateFoundation().validate(
        _template(), ("storyboard", "quality-review")
    )

    assert report.valid is True
    assert report.template.page_count == 1
    assert report.state_machine_authoritative is True
    assert report.planning_only is True
    assert report.template.workflow_started is False
    assert report.template.workflow_mutated is False


def test_rule_engine_is_deterministic_and_never_executes_or_approves() -> None:
    report = RuleEngineFoundation().evaluate(_rule(), ("storyboard", "quality-review"))
    missing = RuleEngineFoundation().evaluate(_rule(), ("storyboard",))

    assert report.eligible is True
    assert report.autonomous_decision_made is False
    assert report.execution_performed is False
    assert missing.eligible is False
    assert missing.missing_evidence == ("quality-review",)


def test_event_bus_only_records_local_metadata_and_rejects_duplicates() -> None:
    bus = EventBusFoundation((_event(),))
    report = bus.report()

    assert report.event_count == 1
    assert report.dispatch_started is False
    assert report.queue_created is False
    assert report.retry_scheduled is False
    with pytest.raises(ValueError, match="duplicate automation event"):
        bus.register(_event())


def test_automation_registry_is_explicit_local_and_rejects_duplicate_rules() -> None:
    registry = AutomationRegistryFoundation((_template(),), (_rule(),))
    report = registry.report()

    assert report.template_count == 1
    assert report.rule_count == 1
    assert report.external_discovery_performed is False
    assert report.runtime_changed is False
    with pytest.raises(ValueError, match="duplicate automation rule"):
        registry.register_rule(_rule())


def test_engine_builds_human_gated_plan_without_workflow_execution() -> None:
    request = AutomationRequestDTO(
        template_id="storyboard-review",
        rule_id="review-ready",
        event_id="review-completed",
        evidence_types=("storyboard", "quality-review"),
        approval_boundary="editor-review",
    )
    report = _engine().preview(request)

    assert report.findings == ()
    assert report.plan is not None
    assert report.plan.eligible_for_human_review is True
    assert report.plan.execution_requested is False
    assert report.plan.execution_performed is False
    assert report.plan.workflow_mutated is False
    assert report.human_review_required is True
    assert report.state_machine_authoritative is True


def test_engine_requires_a_human_approval_boundary_and_sdk_is_additive() -> None:
    request = AutomationRequestDTO(
        template_id="storyboard-review",
        rule_id="review-ready",
        event_id="review-completed",
        evidence_types=("storyboard", "quality-review"),
    )
    report = UnifiedSDKFoundation(automation=_engine()).automation_preview(request)

    assert "human approval boundary is required" in report.findings
    assert report.plan is not None
    assert report.plan.eligible_for_human_review is False
    assert report.planning_only is True
