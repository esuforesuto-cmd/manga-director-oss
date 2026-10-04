"""Contracts for non-executing v4.7 Creative Decision Platform analysis."""

from __future__ import annotations

from pathlib import Path

from manga_director.domain.state_machine import PageState
from manga_director.production import V47DecisionIntelligenceService
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "pilot-1", "storyboard": {"panels": []}},
        state=PageState.PROMPT_BUILT,
        artifacts={"storyboard": {"panels": []}},
        metadata={"provenance": "human"},
    )


def test_decision_intelligence_is_advisory_without_autonomous_selection() -> None:
    report = V47DecisionIntelligenceService().decision_intelligence("pilot", _context())

    assert report.planning_only is True
    assert report.analysis.page_count == 1
    assert report.analysis.evidence_coverage_assessed is False
    assert report.analysis.alternatives_compared is False
    assert report.analysis.risk_assessed is False
    assert report.analysis.uncertainty_explained is False
    assert report.analysis.decision_recommended is False
    assert report.analysis.autonomous_decision_made is False
    assert report.summary.decision_selected is False
    assert report.summary.automatic_action_taken is False


def test_recommendation_analytics_cannot_rank_accept_or_dispatch() -> None:
    report = V47DecisionIntelligenceService().recommendation_analytics("pilot", _context())

    assert report.planning_only is True
    assert report.analytics.page_count == 1
    assert report.analytics.rationale_coverage_assessed is False
    assert report.analytics.prerequisite_coverage_assessed is False
    assert report.analytics.impact_compared is False
    assert report.analytics.confidence_assessed is False
    assert report.analytics.option_ranked is False
    assert report.analytics.recommendation_accepted is False
    assert report.summary.action_dispatched is False
    assert report.summary.automatic_action_taken is False


def test_review_analytics_cannot_complete_review_or_bypass_quality() -> None:
    report = V47DecisionIntelligenceService().review_analytics("pilot", _context())

    assert report.planning_only is True
    assert report.analytics.page_count == 1
    assert report.analytics.finding_trend_assessed is False
    assert report.analytics.coverage_assessed is False
    assert report.analytics.consistency_assessed is False
    assert report.analytics.escalation_assessed is False
    assert report.analytics.review_completed is False
    assert report.analytics.quality_gate_bypassed is False
    assert report.summary.finding_mutated is False
    assert report.summary.automatic_action_taken is False


def test_approval_insights_preserve_manual_approval_and_state_machine_boundaries() -> None:
    report = V47DecisionIntelligenceService().approval_insights("pilot", _context())

    assert report.planning_only is True
    assert report.insights.page_count == 1
    assert report.insights.prerequisite_readiness_assessed is False
    assert report.insights.escalation_assessed is False
    assert report.insights.override_rationale_assessed is False
    assert report.insights.human_approval_required is True
    assert report.insights.approval_submitted is False
    assert report.insights.approval_granted is False
    assert report.insights.workflow_transitioned is False
    assert report.summary.access_granted is False
    assert report.summary.policy_enforced is False
    assert report.summary.automatic_action_taken is False


def test_executive_decision_dashboard_is_transport_neutral_and_non_operational() -> None:
    report = V47DecisionIntelligenceService().executive_decision_dashboard("pilot", _context())

    assert report.planning_only is True
    assert report.dashboard.page_count == 1
    assert report.dashboard.presentation_dependency is False
    assert report.dashboard.dashboard_persisted is False
    assert report.dashboard.dashboard_published is False
    assert report.dashboard.decision.analysis.autonomous_decision_made is False
    assert report.dashboard.recommendation.analytics.recommendation_accepted is False
    assert report.dashboard.review.analytics.review_completed is False
    assert report.dashboard.approval.insights.approval_granted is False
    assert report.summary.organizational_action_taken is False
    assert report.summary.telemetry_collected is False
    assert report.summary.monitoring_started is False
    assert report.summary.automatic_action_taken is False


def test_v4_7_intelligence_keeps_delivery_repository_and_runtime_boundaries_out_of_module() -> None:
    source = (ROOT / "src/manga_director/production/v4_7_decision_intelligence.py").read_text(
        encoding="utf-8"
    )

    assert "manga_director.api" not in source
    assert "manga_director.cli" not in source
    assert "manga_director.mcp" not in source
    assert "manga_director.repositories" not in source
    assert "save(" not in source
    assert ".execute(" not in source
    assert "workflow_engine" not in source


def test_v4_7_intelligence_docs_report_quality_gates_and_debt_are_available() -> None:
    assets = (
        "docs/DECISION_INTELLIGENCE.md",
        "docs/RECOMMENDATION_ANALYTICS.md",
        "docs/REVIEW_ANALYTICS.md",
        "docs/APPROVAL_INSIGHTS.md",
        "docs/EXECUTIVE_DECISION_DASHBOARD.md",
        "docs/V4_7_ITERATION_2_DECISION_INTELLIGENCE_REPORT.md",
    )
    gates = (ROOT / "docs/V4_QUALITY_GATES.md").read_text(encoding="utf-8")
    debt = (ROOT / "docs/TECH_DEBT.md").read_text(encoding="utf-8")

    assert all((ROOT / asset).is_file() for asset in assets)
    for gate in (
        "Decision Intelligence Validation",
        "Recommendation Analytics Validation",
        "Review Analytics Validation",
        "Approval Insights Validation",
        "Executive Decision Dashboard Validation",
    ):
        assert gate in gates
    for category in (
        "Decision Intelligence",
        "Recommendation Analytics",
        "Review Analytics",
        "Approval Insights",
        "Executive Decision Dashboard",
    ):
        assert category in debt
