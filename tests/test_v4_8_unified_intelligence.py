"""Contracts for the v4.8 Unified Platform Intelligence iteration."""

from __future__ import annotations

from pathlib import Path

from manga_director.domain.state_machine import PageState
from manga_director.production import V48UnifiedPlatformIntelligenceService
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "pilot-1", "storyboard": {"panels": []}},
        state=PageState.PROMPT_BUILT,
        artifacts={"storyboard": {"panels": []}},
        metadata={"provenance": "human"},
    )


def test_platform_analytics_is_one_page_scoped_and_keeps_api_runtime_unchanged() -> None:
    report = V48UnifiedPlatformIntelligenceService().platform_analytics("pilot", _context())

    assert report.planning_only is True
    assert report.analytics.page_count == 1
    assert report.analytics.service_count == 6
    assert report.analytics.module_count == 7
    assert report.analytics.core_dependency_direction_preserved is True
    assert report.analytics.api_surface_changed is False
    assert report.analytics.runtime_reconfigured is False
    assert report.summary.evidence_persisted is False
    assert report.summary.automatic_optimization_applied is False


def test_service_orchestration_is_advisory_and_never_invokes_or_routes_services() -> None:
    report = V48UnifiedPlatformIntelligenceService().service_orchestration("pilot", _context())

    assert report.planning_only is True
    assert report.orchestration.page_count == 1
    assert report.orchestration.service_ids == (
        "agent-platform",
        "decision",
        "enterprise",
        "knowledge",
        "production",
        "workspace",
    )
    assert report.orchestration.order_is_advisory is True
    assert report.orchestration.human_review_required is True
    assert report.orchestration.service_invoked is False
    assert report.orchestration.runtime_route_changed is False
    assert report.orchestration.workflow_mutated is False
    assert report.summary.delegation_created is False
    assert report.summary.automatic_action_taken is False


def test_operational_insights_expose_missing_evidence_without_telemetry_or_action() -> None:
    report = V48UnifiedPlatformIntelligenceService().operational_insights("pilot", _context())

    assert report.planning_only is True
    assert report.summary.insight_count == 6
    assert report.summary.missing_evidence_count == 6
    assert report.summary.monitoring_started is False
    assert report.summary.alert_sent is False
    assert report.summary.optimization_applied is False
    assert all(insight.evidence_missing for insight in report.insights)
    assert all(insight.human_review_required for insight in report.insights)
    assert all(insight.telemetry_collected is False for insight in report.insights)
    assert all(insight.operational_action_taken is False for insight in report.insights)


def test_lifecycle_analytics_is_descriptive_and_never_transitions_or_recovers() -> None:
    report = V48UnifiedPlatformIntelligenceService().lifecycle_analytics("pilot", _context())

    assert report.planning_only is True
    assert report.analytics.page_count == 1
    assert report.analytics.reference_count == 2
    assert report.analytics.source_module_count == 2
    assert report.analytics.lifecycle_persisted is False
    assert report.analytics.state_transitioned is False
    assert report.summary.retention_enforced is False
    assert report.summary.recovery_attempted is False
    assert report.summary.record_mutated is False


def test_unified_dashboard_is_transport_neutral_additive_and_non_operational() -> None:
    report = V48UnifiedPlatformIntelligenceService().unified_dashboard("pilot", _context())

    assert report.planning_only is True
    assert report.dashboard.page_count == 1
    assert report.dashboard.public_api_additive is True
    assert report.dashboard.presentation_dependency is False
    assert report.dashboard.dashboard_persisted is False
    assert report.dashboard.dashboard_published is False
    assert report.dashboard.orchestration.orchestration.service_invoked is False
    assert report.summary.human_review_required is True
    assert report.summary.cross_domain_action_taken is False
    assert report.summary.telemetry_collected is False
    assert report.summary.monitoring_started is False


def test_v4_8_intelligence_keeps_delivery_repository_and_runtime_boundaries_out_of_module() -> None:
    source = (ROOT / "src/manga_director/production/v4_8_unified_intelligence.py").read_text(
        encoding="utf-8"
    )

    assert "manga_director.api" not in source
    assert "manga_director.cli" not in source
    assert "manga_director.mcp" not in source
    assert "manga_director.repositories" not in source
    assert "save(" not in source
    assert ".execute(" not in source
    assert "workflow_engine" not in source


def test_v4_8_intelligence_docs_report_quality_gates_and_debt_are_available() -> None:
    assets = (
        "docs/UNIFIED_PLATFORM_ANALYTICS.md",
        "docs/SERVICE_ORCHESTRATION.md",
        "docs/OPERATIONAL_INSIGHTS.md",
        "docs/LIFECYCLE_ANALYTICS.md",
        "docs/UNIFIED_DASHBOARD.md",
        "docs/V4_8_ITERATION_2_UNIFIED_PLATFORM_INTELLIGENCE_REPORT.md",
    )
    gates = (ROOT / "docs/V4_QUALITY_GATES.md").read_text(encoding="utf-8")
    debt = (ROOT / "docs/TECH_DEBT.md").read_text(encoding="utf-8")

    assert all((ROOT / asset).is_file() for asset in assets)
    for gate in (
        "Unified Platform Analytics Validation",
        "Service Orchestration Validation",
        "Operational Insights Validation",
        "Lifecycle Analytics Validation",
        "Unified Dashboard Validation",
    ):
        assert gate in gates
    for category in (
        "Unified Platform Analytics",
        "Service Orchestration",
        "Operational Insights",
        "Lifecycle Analytics",
        "Unified Dashboard",
    ):
        assert category in debt
