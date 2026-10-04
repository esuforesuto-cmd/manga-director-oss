"""Operating-quality contracts for v5.2 Automation Governance."""

from __future__ import annotations

from manga_director.platform import (
    AutomationEngineFoundation,
    AutomationEventDTO,
    AutomationPlatformMaturityService,
    AutomationRegistryFoundation,
    AutomationRequestDTO,
    AutomationRuleDTO,
    EventBusFoundation,
    UnifiedSDKFoundation,
    WorkflowTemplateDTO,
)


def _engine() -> AutomationEngineFoundation:
    template = WorkflowTemplateDTO(
        template_id="storyboard-review",
        title="Storyboard review",
        owner="creative-operations",
        page_reference="page-001",
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
        page_reference="page-001",
        provenance="caller-supplied",
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


def test_automation_governance_is_non_enforcing_and_human_gated() -> None:
    report = AutomationPlatformMaturityService(_engine()).report(_request())

    assert report.governance.policy.policy_enforced is False
    assert report.governance.compliance.template_single_page is True
    assert report.governance.compliance.human_approval_boundary_declared is True
    assert report.governance.compliance.rule_safety_boundary_preserved is True
    assert report.governance.automatic_action_taken is False


def test_rule_governance_audits_explicit_rule_without_changing_it() -> None:
    report = AutomationPlatformMaturityService(_engine()).report(_request())

    assert report.rule_governance.compliance.rule_id == "review-ready"
    assert report.rule_governance.compliance.owner_declared is True
    assert report.rule_governance.compliance.evidence_complete is True
    assert report.rule_governance.compliance.safety_boundary_preserved is True
    assert report.rule_governance.compliance.rule_changed is False


def test_observability_is_local_metadata_not_runtime_monitoring() -> None:
    report = AutomationPlatformMaturityService(_engine()).report(_request())

    assert report.observability.observation_count == 4
    assert {item.status for item in report.observability.observations} == {"available"}
    assert report.observability.monitoring_started is False
    assert report.observability.report_persisted is False
    assert all(item.telemetry_collected is False for item in report.observability.observations)


def test_reliability_and_lifecycle_never_attempt_recovery_or_transition() -> None:
    report = AutomationPlatformMaturityService(_engine()).report(_request())

    assert report.reliability.component_count == 4
    assert report.reliability.runtime_reconfigured is False
    assert all(item.recovery_attempted is False for item in report.reliability.components)
    assert report.lifecycle.lifecycle.stage == "advisory"
    assert report.lifecycle.lifecycle.lifecycle_transitioned is False
    assert report.lifecycle.lifecycle.lifecycle_persisted is False


def test_integration_requires_human_approval_and_sdk_is_additive() -> None:
    report = UnifiedSDKFoundation(automation=_engine()).automation_maturity(
        _request(approval_boundary=None)
    )

    assert report.dashboard.automation.health == "attention_required"
    assert report.governance.compliance.human_approval_boundary_declared is False
    assert report.lifecycle.lifecycle.human_approval_boundary_declared is False
    assert report.lts_compatible is True
    assert report.automatic_action_taken is False
    assert report.planning_only is True
