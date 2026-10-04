"""Contracts for non-executing v4.7 Creative Decision Platform foundations."""

from __future__ import annotations

from pathlib import Path

from manga_director.domain.state_machine import PageState
from manga_director.production import V47DecisionFoundationService
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "pilot-1", "storyboard": {"panels": []}},
        state=PageState.PROMPT_BUILT,
        artifacts={"storyboard": {"panels": []}},
        metadata={"provenance": "human"},
    )


def test_decision_engine_is_one_page_scoped_and_cannot_select_or_persist() -> None:
    report = V47DecisionFoundationService().decision_engine("pilot", _context())

    assert report.planning_only is True
    assert report.context.page_count == 1
    assert report.context.state_machine_authoritative is True
    assert report.context.evidence_collected is False
    assert report.context.decision_persisted is False
    assert report.evidence.provenance_required is True
    assert report.evidence.redaction_required is True
    assert report.evidence.evidence_loaded is False
    assert report.summary.human_owner_required is True
    assert report.summary.decision_selected is False
    assert report.summary.automatic_action_taken is False


def test_recommendation_is_advisory_without_selection_or_dispatch() -> None:
    report = V47DecisionFoundationService().recommendation("pilot", _context())

    assert report.planning_only is True
    assert report.recommendation.page_count == 1
    assert report.recommendation.rationale_required is True
    assert report.recommendation.prerequisites_required is True
    assert report.recommendation.human_review_required is True
    assert report.recommendation.option_selected is False
    assert report.recommendation.recommendation_accepted is False
    assert report.summary.action_dispatched is False
    assert report.summary.automatic_action_taken is False


def test_review_intelligence_cannot_complete_review_or_bypass_quality() -> None:
    report = V47DecisionFoundationService().review_intelligence("pilot", _context())

    assert report.planning_only is True
    assert report.review.page_count == 1
    assert report.review.review_completed is False
    assert report.review.finding_mutated is False
    assert report.summary.approval_recommended is False
    assert report.summary.quality_gate_bypassed is False
    assert report.summary.automatic_action_taken is False


def test_approval_workflow_preserves_state_machine_and_human_review_gates() -> None:
    report = V47DecisionFoundationService().approval_workflow("pilot", _context())

    assert report.planning_only is True
    assert report.approval.page_count == 1
    assert report.approval.state_machine_authoritative is True
    assert report.approval.persisted_storyboard_required is True
    assert report.approval.completed_quality_review_required is True
    assert report.approval.human_approval_required is True
    assert report.approval.approval_submitted is False
    assert report.approval.approval_granted is False
    assert report.approval.workflow_transitioned is False
    assert report.summary.override_granted is False
    assert report.summary.automatic_action_taken is False


def test_executive_dashboard_is_transport_neutral_and_non_operational() -> None:
    report = V47DecisionFoundationService().executive_dashboard("pilot", _context())

    assert report.planning_only is True
    assert report.dashboard.page_count == 1
    assert report.dashboard.presentation_dependency is False
    assert report.dashboard.dashboard_persisted is False
    assert report.dashboard.dashboard_published is False
    assert report.dashboard.approval.approval.approval_granted is False
    assert report.summary.decision_health_assessed is False
    assert report.summary.organizational_action_taken is False
    assert report.summary.telemetry_collected is False
    assert report.summary.monitoring_started is False


def test_v4_7_foundation_keeps_delivery_repository_and_runtime_boundaries_out_of_module() -> None:
    source = (ROOT / "src/manga_director/production/v4_7_decision_foundation.py").read_text(
        encoding="utf-8"
    )

    assert "manga_director.api" not in source
    assert "manga_director.cli" not in source
    assert "manga_director.mcp" not in source
    assert "manga_director.repositories" not in source
    assert "save(" not in source
    assert ".execute(" not in source
    assert "workflow_engine" not in source


def test_v4_7_foundation_docs_report_quality_gates_and_debt_are_available() -> None:
    assets = (
        "docs/DECISION_ENGINE_FOUNDATION.md",
        "docs/RECOMMENDATION_FOUNDATION.md",
        "docs/REVIEW_INTELLIGENCE_FOUNDATION.md",
        "docs/APPROVAL_WORKFLOW_FOUNDATION.md",
        "docs/EXECUTIVE_DASHBOARD_FOUNDATION.md",
        "docs/V4_7_ITERATION_1_DECISION_FOUNDATION_REPORT.md",
    )
    gates = (ROOT / "docs/V4_QUALITY_GATES.md").read_text(encoding="utf-8")
    debt = (ROOT / "docs/TECH_DEBT.md").read_text(encoding="utf-8")

    assert all((ROOT / asset).is_file() for asset in assets)
    for gate in (
        "Decision Engine Foundation Validation",
        "Recommendation Foundation Validation",
        "Review Intelligence Foundation Validation",
        "Approval Workflow Foundation Validation",
        "Executive Dashboard Foundation Validation",
    ):
        assert gate in gates
    for category in (
        "Decision Engine Foundation",
        "Recommendation Foundation",
        "Review Intelligence Foundation",
        "Approval Workflow Foundation",
        "Executive Dashboard Foundation",
    ):
        assert category in debt
