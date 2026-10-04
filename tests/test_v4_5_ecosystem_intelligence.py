"""Contracts for non-executing v4.5 ecosystem intelligence reports."""

from __future__ import annotations

from pathlib import Path

from manga_director.domain.state_machine import PageState
from manga_director.production import V45EcosystemIntelligenceService
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "pilot-1", "storyboard": {"panels": []}},
        state=PageState.PROMPT_BUILT,
        artifacts={"storyboard": {"panels": []}},
        metadata={"provenance": "human"},
    )


def test_service_intelligence_is_advisory_and_cannot_register_or_invoke() -> None:
    report = V45EcosystemIntelligenceService().service_intelligence("pilot", _context())

    assert report.planning_only is True
    assert report.insight.declared_capability_count == 0
    assert report.insight.compatibility_status == "not_assessed"
    assert report.insight.service_invoked is False
    assert report.recommendation.registration_enabled is False
    assert report.recommendation.automatic_action_taken is False
    assert report.registry.registry.remote_discovery_enabled is False


def test_plugin_analytics_cannot_load_execute_or_grant_permission() -> None:
    report = V45EcosystemIntelligenceService().plugin_analytics("pilot", _context())

    assert report.planning_only is True
    assert report.analytics.isolation_status == "not_reviewed"
    assert report.analytics.plugin_loaded is False
    assert report.analytics.plugin_executed is False
    assert report.recommendation.permission_granted is False
    assert report.recommendation.automatic_action_taken is False


def test_workflow_insights_are_one_page_and_cannot_install_or_execute() -> None:
    report = V45EcosystemIntelligenceService().workflow_insights("pilot", _context())

    assert report.planning_only is True
    assert report.insight.page_count == 1
    assert report.insight.compatibility_status == "not_assessed"
    assert report.insight.state_machine_authoritative is True
    assert report.insight.workflow_executed is False
    assert report.recommendation.installation_enabled is False
    assert report.recommendation.automatic_action_taken is False


def test_knowledge_federation_analytics_cannot_sync_share_or_connect() -> None:
    report = V45EcosystemIntelligenceService().knowledge_federation_analytics("pilot", _context())

    assert report.planning_only is True
    assert report.analytics.page_count == 1
    assert report.analytics.redaction_required is True
    assert report.analytics.consent_required is True
    assert report.analytics.knowledge_synchronized is False
    assert report.analytics.federation_connected is False
    assert report.recommendation.sharing_enabled is False
    assert report.recommendation.transport_enabled is False
    assert report.recommendation.automatic_action_taken is False


def test_ecosystem_dashboard_composes_reports_without_persistence_or_publication() -> None:
    report = V45EcosystemIntelligenceService().ecosystem_dashboard("pilot", _context())

    assert report.planning_only is True
    assert report.dashboard.page_reference == "pilot-1"
    assert report.dashboard.service.insight.service_invoked is False
    assert report.dashboard.plugin.analytics.plugin_executed is False
    assert report.dashboard.workflow.insight.workflow_executed is False
    assert report.dashboard.knowledge_federation.analytics.federation_connected is False
    assert report.dashboard.dashboard_persisted is False
    assert report.dashboard.dashboard_published is False
    assert report.dashboard.automatic_action_taken is False


def test_v4_5_intelligence_keeps_delivery_repository_and_runtime_boundaries_out_of_module() -> None:
    source = (ROOT / "src/manga_director/production/v4_5_ecosystem_intelligence.py").read_text(
        encoding="utf-8"
    )

    assert "manga_director.api" not in source
    assert "manga_director.cli" not in source
    assert "manga_director.mcp" not in source
    assert "manga_director.repositories" not in source
    assert "save(" not in source
    assert ".execute(" not in source
    assert "workflow_engine" not in source


def test_v4_5_intelligence_docs_report_quality_gates_and_debt_are_available() -> None:
    assets = (
        "docs/SERVICE_INTELLIGENCE.md",
        "docs/PLUGIN_ANALYTICS.md",
        "docs/WORKFLOW_INSIGHTS.md",
        "docs/KNOWLEDGE_FEDERATION_ANALYTICS.md",
        "docs/ECOSYSTEM_DASHBOARD.md",
        "docs/V4_5_ITERATION_2_ECOSYSTEM_INTELLIGENCE_REPORT.md",
    )
    gates = (ROOT / "docs/V4_QUALITY_GATES.md").read_text(encoding="utf-8")
    debt = (ROOT / "docs/TECH_DEBT.md").read_text(encoding="utf-8")

    assert all((ROOT / asset).is_file() for asset in assets)
    for gate in (
        "Service Intelligence Validation",
        "Plugin Analytics Validation",
        "Workflow Insights Validation",
        "Knowledge Federation Analytics Validation",
        "Ecosystem Dashboard Validation",
    ):
        assert gate in gates
    for category in (
        "Service Intelligence",
        "Plugin Analytics",
        "Workflow Insights",
        "Knowledge Federation Analytics",
        "Ecosystem Dashboard",
    ):
        assert category in debt
