"""Contracts for non-enforcing v4.7 Creative Decision Platform governance."""

from __future__ import annotations

from pathlib import Path

from manga_director.domain.state_machine import PageState
from manga_director.production import V47DecisionGovernanceService
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "pilot-1", "storyboard": {"panels": []}},
        state=PageState.PROMPT_BUILT,
        artifacts={"storyboard": {"panels": []}},
        metadata={"provenance": "human"},
    )


def test_decision_governance_preserves_state_machine_and_human_decision_boundaries() -> None:
    report = V47DecisionGovernanceService().decision_governance("pilot", _context())

    assert report.planning_only is True
    assert report.policy.page_count == 1
    assert report.policy.state_machine_authoritative is True
    assert report.policy.persisted_storyboard_required is True
    assert report.policy.completed_quality_review_required is True
    assert report.policy.human_decision_required is True
    assert report.policy.policy_enforced is False
    assert report.policy.policy_persisted is False
    assert report.compliance.compliance_confirmed is False
    assert report.compliance.autonomous_decision_made is False
    assert report.summary.automatic_action_taken is False


def test_recommendation_governance_cannot_select_accept_or_enforce() -> None:
    report = V47DecisionGovernanceService().recommendation_governance("pilot", _context())

    assert report.planning_only is True
    assert report.policy.page_count == 1
    assert report.policy.rationale_required is True
    assert report.policy.prerequisites_required is True
    assert report.policy.human_review_required is True
    assert report.policy.policy_enforced is False
    assert report.policy.recommendation_selected is False
    assert report.compliance.compliance_confirmed is False
    assert report.compliance.recommendation_accepted is False
    assert report.summary.automatic_action_taken is False


def test_review_audit_cannot_complete_review_persist_or_bypass_quality() -> None:
    report = V47DecisionGovernanceService().review_audit("pilot", _context())

    assert report.planning_only is True
    assert report.audit.page_count == 1
    assert report.audit.finding_trace_required is True
    assert report.audit.coverage_trace_required is True
    assert report.audit.consistency_trace_required is True
    assert report.audit.audit_persisted is False
    assert report.audit.review_completed is False
    assert report.audit.quality_gate_bypassed is False
    assert report.summary.audit_action_taken is False
    assert report.summary.automatic_action_taken is False


def test_approval_compliance_preserves_manual_approval_prerequisites() -> None:
    report = V47DecisionGovernanceService().approval_compliance("pilot", _context())

    assert report.planning_only is True
    assert report.compliance.page_count == 1
    assert report.compliance.state_machine_authoritative is True
    assert report.compliance.persisted_storyboard_required is True
    assert report.compliance.completed_quality_review_required is True
    assert report.compliance.human_approval_required is True
    assert report.compliance.compliance_confirmed is False
    assert report.compliance.approval_submitted is False
    assert report.compliance.approval_granted is False
    assert report.compliance.workflow_transitioned is False
    assert report.summary.access_granted is False
    assert report.summary.policy_enforced is False
    assert report.summary.automatic_action_taken is False


def test_decision_reliability_is_diagnostic_only_without_monitoring_or_recovery() -> None:
    report = V47DecisionGovernanceService().decision_reliability("pilot", _context())

    assert report.planning_only is True
    assert report.reliability.page_count == 1
    assert report.reliability.health_status == "not_checked"
    assert report.reliability.health_check_executed is False
    assert report.reliability.failure_detected is False
    assert report.reliability.monitoring_active is False
    assert report.reliability.alert_sent is False
    assert report.reliability.retry_attempted is False
    assert report.reliability.recovery_attempted is False
    assert report.summary.automatic_action_taken is False


def test_executive_governance_dashboard_is_transport_neutral_and_non_operational() -> None:
    report = V47DecisionGovernanceService().executive_decision_governance_dashboard(
        "pilot", _context()
    )

    assert report.planning_only is True
    assert report.dashboard.page_count == 1
    assert report.dashboard.presentation_dependency is False
    assert report.dashboard.dashboard_persisted is False
    assert report.dashboard.dashboard_published is False
    assert report.dashboard.decision.compliance.autonomous_decision_made is False
    assert report.dashboard.recommendation.compliance.recommendation_accepted is False
    assert report.dashboard.review.audit.review_completed is False
    assert report.dashboard.approval.compliance.approval_granted is False
    assert report.dashboard.reliability.reliability.recovery_attempted is False
    assert report.summary.organizational_action_taken is False
    assert report.summary.telemetry_collected is False
    assert report.summary.monitoring_started is False
    assert report.summary.automatic_action_taken is False


def test_v4_7_governance_keeps_delivery_repository_and_runtime_boundaries_out_of_module() -> None:
    source = (ROOT / "src/manga_director/production/v4_7_decision_governance.py").read_text(
        encoding="utf-8"
    )

    assert "manga_director.api" not in source
    assert "manga_director.cli" not in source
    assert "manga_director.mcp" not in source
    assert "manga_director.repositories" not in source
    assert "save(" not in source
    assert ".execute(" not in source
    assert "workflow_engine" not in source


def test_v4_7_governance_docs_report_quality_gates_and_debt_are_available() -> None:
    assets = (
        "docs/DECISION_GOVERNANCE.md",
        "docs/RECOMMENDATION_GOVERNANCE.md",
        "docs/REVIEW_AUDIT.md",
        "docs/APPROVAL_COMPLIANCE.md",
        "docs/DECISION_RELIABILITY.md",
        "docs/V4_7_ITERATION_3_DECISION_GOVERNANCE_REPORT.md",
    )
    gates = (ROOT / "docs/V4_QUALITY_GATES.md").read_text(encoding="utf-8")
    debt = (ROOT / "docs/TECH_DEBT.md").read_text(encoding="utf-8")

    assert all((ROOT / asset).is_file() for asset in assets)
    for gate in (
        "Decision Governance Validation",
        "Recommendation Governance Validation",
        "Review Audit Validation",
        "Approval Compliance Validation",
        "Decision Reliability Validation",
    ):
        assert gate in gates
    for category in (
        "Decision Governance",
        "Recommendation Governance",
        "Review Audit",
        "Approval Compliance",
        "Decision Reliability",
    ):
        assert category in debt
