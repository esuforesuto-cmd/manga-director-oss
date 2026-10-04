"""Contracts for v3.5 analysis-only intelligence reporting."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from typer.testing import CliRunner

from manga_director.api import ObservabilityApplication
from manga_director.api.observability import create_observability_app
from manga_director.cli.app import app
from manga_director.domain.project import Chapter, Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.mcp.application import MangaApplicationService
from manga_director.mcp.registry import default_tool_registry
from manga_director.production import V35FoundationService, V35InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _service() -> tuple[V35InsightsService, InMemoryRepository]:
    repository = InMemoryRepository()
    repository.save(
        Project(
            id="pilot",
            title="Pilot",
            chapters=[Chapter(id="one", title="One", page_numbers=[1])],
            pages=[Page(page_number=1, storyboard={"panels": []})],
            metadata={"reference": {"secret": "not exposed"}, "world": "not exposed"},
        )
    )
    foundation = V35FoundationService(repository)
    return V35InsightsService(foundation, repository), repository


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "pilot-1", "storyboard": {"panels": []}},
        state=PageState.PROMPT_BUILT,
        artifacts={"storyboard": {"panels": []}, "prompt": {"text": "not exposed"}},
        metadata={"workflow_history": [{"step": "prompt", "to": "PromptBuilt"}]},
    )


def test_knowledge_analytics_is_read_only_and_cannot_apply_recommendations() -> None:
    service, repository = _service()

    report = service.knowledge_analytics("pilot", _context())

    assert report.analysis_only is True
    assert report.insight.applied is False
    assert report.coverage.coverage_persisted is False
    assert report.relationships.graph_changed is False
    assert report.recommendations.recommendation_applied is False
    assert report.health.health_enforced is False
    assert repository.load("pilot").metadata["world"] == "not exposed"


def test_creative_analytics_cannot_change_story_or_approve_a_page() -> None:
    service, _ = _service()

    report = service.creative_analytics("pilot", _context())

    assert report.analysis_only is True
    assert report.story.story_changed is False
    assert report.character.character_changed is False
    assert report.page_quality.quality_completed is False
    assert report.page_quality.approval_granted is False
    assert report.recommendations.recommendation_applied is False


def test_production_analytics_cannot_optimize_schedule_or_deploy() -> None:
    service, _ = _service()

    report = service.production_analytics("pilot", _context())

    assert report.analysis_only is True
    assert report.efficiency.pipeline_changed is False
    assert report.capacity.forecast_committed is False
    assert report.capacity.capacity_allocated is False
    assert report.delivery_risk.mitigation_applied is False
    assert report.optimization.optimization_applied is False
    assert report.optimization.deployment_started is False
    assert report.executive.schedule_changed is False


def test_platform_analytics_cannot_collect_persist_or_remediate() -> None:
    service, _ = _service()

    report = service.platform_intelligence("pilot", _context())

    assert report.analysis_only is True
    assert report.history.history_persisted is False
    assert report.regression.remediation_applied is False
    assert report.executive.release_authorized is False
    assert report.health.monitoring_started is False
    assert report.health.external_action_taken is False
    assert all(kpi.target_enforced is False for kpi in report.kpis)


def test_v3_5_analytics_dashboards_are_available_via_fastapi_mcp_and_cli() -> None:
    service, _ = _service()
    context = _context()
    application = ObservabilityApplication(
        health=lambda: None,  # type: ignore[arg-type]
        diagnostics=lambda: None,  # type: ignore[arg-type]
        repository_check=lambda: None,  # type: ignore[arg-type]
        knowledge_insights_v35=lambda: service.knowledge_insights_dashboard("pilot", context),
        creative_analytics_v35=lambda: service.creative_analytics_dashboard("pilot", context),
        production_analytics_v35=lambda: service.production_analytics_dashboard("pilot", context),
        executive_analytics_v35=lambda: service.executive_analytics_dashboard("pilot", context),
    )
    registry = default_tool_registry(
        cast(MangaApplicationService, None),
        knowledge_insights_v35_provider=lambda: service.knowledge_insights_dashboard(
            "pilot", context
        ),
        creative_analytics_v35_provider=lambda: service.creative_analytics_dashboard(
            "pilot", context
        ),
        production_analytics_v35_provider=lambda: service.production_analytics_dashboard(
            "pilot", context
        ),
        executive_analytics_v35_provider=lambda: service.executive_analytics_dashboard(
            "pilot", context
        ),
    )

    assert application.knowledge_insights_v35_preview()["automatic_action_taken"] is False
    assert application.creative_analytics_v35_preview()["report"]["analysis_only"] is True
    assert application.production_analytics_v35_preview()["automatic_action_taken"] is False
    assert application.executive_analytics_v35_preview()["automatic_action_taken"] is False
    routes = {route.path for route in create_observability_app(application).routes}
    assert {
        "/v3.5/knowledge-insights",
        "/v3.5/creative-analytics",
        "/v3.5/production-analytics",
        "/v3.5/executive-analytics",
    } <= routes
    assert {
        "knowledge_insights_v35",
        "creative_analytics_v35",
        "production_analytics_v35",
        "executive_analytics_v35",
    } <= {tool["name"] for tool in registry.list()}
    assert CliRunner().invoke(app, ["director", "knowledge-insights-v35", "--help"]).exit_code == 0


def test_v3_5_analytics_docs_examples_and_benchmarks_are_available() -> None:
    assets = (
        "docs/KNOWLEDGE_INTELLIGENCE.md",
        "docs/CREATIVE_ANALYTICS.md",
        "docs/PRODUCTION_OPTIMIZATION.md",
        "docs/PLATFORM_ANALYTICS.md",
        "docs/V3_5_ITERATION_2_INTELLIGENCE_REPORT.md",
        "examples/knowledge_insights/run.py",
        "examples/creative_dashboard/run.py",
        "examples/production_dashboard/run.py",
        "examples/executive_dashboard/v3_5_analytics.py",
        "benchmarks/knowledge_graph_v35.py",
        "benchmarks/creative_intelligence.py",
        "benchmarks/production_intelligence_v35.py",
        "benchmarks/platform_dashboard.py",
    )

    assert all((ROOT / asset).is_file() for asset in assets)
