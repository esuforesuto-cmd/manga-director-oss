"""Contracts for the non-executing v4.3 production intelligence layer."""

from __future__ import annotations

from pathlib import Path

from manga_director.domain.state_machine import PageState
from manga_director.production import V43ProductionIntelligenceService
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "pilot-1", "storyboard": {"panels": []}},
        state=PageState.PROMPT_BUILT,
        artifacts={"storyboard": {"panels": []}},
        metadata={"provenance": "human"},
    )


def test_production_automation_is_a_one_page_plan_without_stage_execution() -> None:
    report = V43ProductionIntelligenceService().production_automation("pilot", _context())

    assert report.planning_only is True
    assert report.plan.page_count == 1
    assert report.plan.plan_applied is False
    assert report.plan.workflow_changed is False
    assert report.stage_automation.automation_enabled is False
    assert report.stage_automation.stage_started is False
    assert report.stage_automation.stage_completed is False
    assert report.stage_automation.action_dispatched is False
    assert report.template.state_machine_authoritative is True
    assert report.template.template_applied is False
    assert report.template.stage_skipping_allowed is False
    assert report.schedule.schedule_registered is False
    assert report.schedule.automatic_start_enabled is False
    assert report.automatic_action_taken is False


def test_asset_intelligence_analyzes_context_without_resolution_or_remediation() -> None:
    report = V43ProductionIntelligenceService().asset_intelligence("pilot", _context())

    assert report.planning_only is True
    assert report.analysis.metadata_key_count == 1
    assert report.analysis.provenance_present is True
    assert report.dependency_analysis.dependency_references == ("storyboard",)
    assert report.dependency_analysis.resolution_applied is False
    assert report.usage.usage_changed is False
    assert report.duplicates.duplicate_resolution_applied is False
    assert report.duplicates.asset_deleted is False
    assert report.summary.automatic_action_taken is False


def test_publishing_workflow_cannot_export_call_external_services_or_distribute() -> None:
    report = V43ProductionIntelligenceService().publishing_workflow("pilot", _context())

    assert report.planning_only is True
    assert report.export_workflow.workflow_started is False
    assert report.export_workflow.export_performed is False
    assert report.export_workflow.artifact_created is False
    assert report.profile.target_name == "not_selected"
    assert report.profile.credentials_present is False
    assert report.profile.external_service_called is False
    assert report.schedule.schedule_registered is False
    assert report.schedule.automatic_release_enabled is False
    assert report.distribution.distribution_started is False
    assert report.distribution.external_delivery_performed is False
    assert report.summary.automatic_action_taken is False


def test_project_analytics_cannot_allocate_resources_or_change_project_work() -> None:
    report = V43ProductionIntelligenceService().project_analytics("pilot", _context())

    assert report.planning_only is True
    assert report.progress.progress_persisted is False
    assert report.progress.progress_changed is False
    assert report.kpi.target_set is False
    assert report.kpi.alert_configured is False
    assert report.velocity.forecast_generated is False
    assert report.velocity.schedule_changed is False
    assert report.resources.resources_allocated is False
    assert report.resources.capacity_changed is False
    assert report.dashboard.automation_enabled is False
    assert report.dashboard.automatic_action_taken is False


def test_v4_3_intelligence_keeps_delivery_and_repository_boundaries_out_of_module() -> None:
    source = (ROOT / "src/manga_director/production/v4_3_production_intelligence.py").read_text(
        encoding="utf-8"
    )

    assert "manga_director.api" not in source
    assert "manga_director.cli" not in source
    assert "manga_director.mcp" not in source
    assert "manga_director.repositories" not in source
    assert "save(" not in source
    assert ".execute(" not in source
    assert "workflow_engine" not in source


def test_v4_3_intelligence_docs_examples_benchmarks_and_report_are_available() -> None:
    assets = (
        "docs/PRODUCTION_AUTOMATION.md",
        "docs/ASSET_INTELLIGENCE.md",
        "docs/PUBLISHING_WORKFLOW.md",
        "docs/PROJECT_ANALYTICS.md",
        "docs/V4_3_ITERATION_2_PRODUCTION_INTELLIGENCE_REPORT.md",
        "examples/production_automation/v4_3_intelligence.py",
        "examples/asset_intelligence/v4_3_intelligence.py",
        "examples/publishing_workflow/v4_3_intelligence.py",
        "examples/project_analytics/v4_3_intelligence.py",
        "benchmarks/production_automation_v4_3.py",
        "benchmarks/asset_analysis_v4_3.py",
        "benchmarks/publishing_v4_3.py",
        "benchmarks/analytics_v4_3.py",
    )

    assert all((ROOT / asset).is_file() for asset in assets)


def test_v4_3_intelligence_quality_gates_and_technical_debt_are_registered() -> None:
    gates = (ROOT / "docs/V4_QUALITY_GATES.md").read_text(encoding="utf-8")
    debt = (ROOT / "docs/TECH_DEBT.md").read_text(encoding="utf-8")

    for gate in (
        "Production Automation Validation",
        "Asset Intelligence Validation",
        "Publishing Workflow Validation",
        "Project Analytics Validation",
    ):
        assert gate in gates
    for category in (
        "Production Automation",
        "Asset Intelligence",
        "Publishing Workflow",
        "Project Analytics",
    ):
        assert category in debt
