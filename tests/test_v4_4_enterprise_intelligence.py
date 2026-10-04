"""Contracts for non-executing v4.4 enterprise intelligence reports."""

from __future__ import annotations

from pathlib import Path

from manga_director.domain.state_machine import PageState
from manga_director.production import V44EnterpriseIntelligenceService
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "pilot-1", "storyboard": {"panels": []}},
        state=PageState.PROMPT_BUILT,
        artifacts={"storyboard": {"panels": []}},
        metadata={"provenance": "human"},
    )


def test_collaboration_analytics_is_advisory_and_cannot_assign_or_approve() -> None:
    report = V44EnterpriseIntelligenceService().collaboration_intelligence("pilot", _context())

    assert report.planning_only is True
    assert report.metrics.assignment_count == 0
    assert report.metrics.metric_persisted is False
    assert report.insight.status == "review_required"
    assert report.insight.storyboard_evidence_required is True
    assert report.insight.completed_quality_review_required is True
    assert report.insight.automatic_action_taken is False
    assert report.team.review.approval_granted is False


def test_portfolio_analytics_cannot_persist_allocate_schedule_or_remediate() -> None:
    report = V44EnterpriseIntelligenceService().portfolio_analytics("pilot", _context())

    assert report.planning_only is True
    assert report.metrics.observed_project_count == 1
    assert report.metrics.observed_page_count == 1
    assert report.metrics.metric_persisted is False
    assert report.risk.risk_level == "not_assessed"
    assert report.risk.schedule_alert_sent is False
    assert report.risk.allocation_changed is False
    assert report.risk.remediation_applied is False


def test_extension_intelligence_cannot_load_execute_or_grant_permission() -> None:
    report = V44EnterpriseIntelligenceService().extension_intelligence("pilot", _context())

    assert report.planning_only is True
    assert report.insight.compatibility_status == "not_assessed"
    assert report.insight.extension_loaded is False
    assert report.insight.extension_executed is False
    assert report.recommendation.permission_granted is False
    assert report.recommendation.automatic_action_taken is False


def test_marketplace_insights_are_one_page_and_cannot_operate_commerce_or_runtime() -> None:
    report = V44EnterpriseIntelligenceService().marketplace_insights("pilot", _context())

    assert report.planning_only is True
    assert report.insight.page_count == 1
    assert report.insight.compatibility_status == "not_assessed"
    assert report.insight.catalog_persisted is False
    assert report.readiness.human_review_required is True
    assert report.readiness.download_enabled is False
    assert report.readiness.installation_enabled is False
    assert report.readiness.execution_enabled is False
    assert report.readiness.publication_enabled is False
    assert report.readiness.payment_enabled is False
    assert report.readiness.billing_enabled is False


def test_enterprise_dashboard_composes_read_only_reports_without_publication_or_actions() -> None:
    report = V44EnterpriseIntelligenceService().enterprise_dashboard("pilot", _context())

    assert report.planning_only is True
    assert report.dashboard.page_reference == "pilot-1"
    assert report.dashboard.collaboration.team.review.approval_granted is False
    assert report.dashboard.portfolio.risk.remediation_applied is False
    assert report.dashboard.extension.insight.extension_executed is False
    assert report.dashboard.marketplace.readiness.execution_enabled is False
    assert report.dashboard.dashboard_persisted is False
    assert report.dashboard.dashboard_published is False
    assert report.dashboard.automatic_action_taken is False


def test_v4_4_intelligence_keeps_delivery_repository_and_runtime_boundaries_out_of_module() -> None:
    source = (ROOT / "src/manga_director/production/v4_4_enterprise_intelligence.py").read_text(
        encoding="utf-8"
    )

    assert "manga_director.api" not in source
    assert "manga_director.cli" not in source
    assert "manga_director.mcp" not in source
    assert "manga_director.repositories" not in source
    assert "save(" not in source
    assert ".execute(" not in source
    assert "workflow_engine" not in source


def test_v4_4_intelligence_docs_report_quality_gates_and_debt_are_available() -> None:
    assets = (
        "docs/COLLABORATION_INTELLIGENCE.md",
        "docs/PORTFOLIO_ANALYTICS.md",
        "docs/EXTENSION_INTELLIGENCE.md",
        "docs/MARKETPLACE_INSIGHTS.md",
        "docs/ENTERPRISE_DASHBOARD.md",
        "docs/V4_4_ITERATION_2_ENTERPRISE_INTELLIGENCE_REPORT.md",
    )
    gates = (ROOT / "docs/V4_QUALITY_GATES.md").read_text(encoding="utf-8")
    debt = (ROOT / "docs/TECH_DEBT.md").read_text(encoding="utf-8")

    assert all((ROOT / asset).is_file() for asset in assets)
    for gate in (
        "Collaboration Analytics Validation",
        "Portfolio Analytics Validation",
        "Extension Intelligence Validation",
        "Marketplace Insights Validation",
        "Enterprise Dashboard Validation",
    ):
        assert gate in gates
    for category in (
        "Collaboration Intelligence",
        "Portfolio Analytics",
        "Extension Intelligence",
        "Marketplace Insights",
        "Enterprise Dashboard",
    ):
        assert category in debt
