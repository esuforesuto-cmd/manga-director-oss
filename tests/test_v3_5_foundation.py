"""Contracts for the additive v3.5 intelligence foundations."""

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
from manga_director.production import V35FoundationService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _service() -> tuple[V35FoundationService, InMemoryRepository]:
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
    return V35FoundationService(repository), repository


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "pilot-1", "storyboard": {"panels": []}},
        state=PageState.PROMPT_BUILT,
        artifacts={"storyboard": {"panels": []}, "prompt": {"text": "not exposed"}},
        metadata={"workflow_history": [{"step": "prompt", "to": "PromptBuilt"}]},
    )


def test_knowledge_graph_is_repository_read_only_and_never_persists_edges() -> None:
    service, repository = _service()

    report = service.knowledge_graph("pilot", _context())

    assert report.analysis_only is True
    assert report.graph.repository_read_only is True
    assert all(node.persisted is False for node in report.graph.nodes)
    assert all(edge.persisted is False for edge in report.graph.edges)
    assert all(trace.persisted is False for trace in report.traces)
    assert repository.load("pilot").metadata["world"] == "not exposed"


def test_creative_intelligence_is_diagnostic_and_cannot_change_or_approve() -> None:
    service, _ = _service()

    report = service.creative_intelligence("pilot", _context())

    assert report.analysis_only is True
    assert report.story.story_changed is False
    assert report.character.character_changed is False
    assert report.page_quality.quality_review_completed is False
    assert report.page_quality.approval_granted is False
    assert report.summary.recommendation_applied is False


def test_production_intelligence_cannot_schedule_allocate_or_deploy() -> None:
    service, _ = _service()

    report = service.production_intelligence("pilot", _context())

    assert report.analysis_only is True
    assert report.pipeline.pipeline_changed is False
    assert report.capacity.capacity_allocated is False
    assert report.delivery.forecast_committed is False
    assert report.delivery.schedule_changed is False
    assert report.health.remediation_started is False
    assert report.executive.deployment_started is False


def test_platform_analytics_is_local_and_cannot_collect_or_act() -> None:
    service, _ = _service()

    report = service.platform_analytics("pilot", _context())

    assert report.analysis_only is True
    assert report.health.monitoring_started is False
    assert report.dashboard.presentation_bound is False
    assert report.trend.trend_persisted is False
    assert report.history.remote_collection_performed is False
    assert all(kpi.target_enforced is False for kpi in report.kpis)


def test_v3_5_dashboards_are_available_via_fastapi_mcp_and_cli_dto_boundaries() -> None:
    service, _ = _service()
    context = _context()
    application = ObservabilityApplication(
        health=lambda: None,  # type: ignore[arg-type]
        diagnostics=lambda: None,  # type: ignore[arg-type]
        repository_check=lambda: None,  # type: ignore[arg-type]
        knowledge_graph_v35=lambda: service.knowledge_graph_dashboard("pilot", context),
        creative_intelligence_v35=lambda: service.creative_intelligence_dashboard("pilot", context),
        production_intelligence_v35=lambda: service.production_intelligence_dashboard(
            "pilot", context
        ),
        platform_analytics_v35=lambda: service.platform_analytics_dashboard("pilot", context),
    )
    registry = default_tool_registry(
        cast(MangaApplicationService, None),
        knowledge_graph_v35_provider=lambda: service.knowledge_graph_dashboard("pilot", context),
        creative_intelligence_v35_provider=lambda: service.creative_intelligence_dashboard(
            "pilot", context
        ),
        production_intelligence_v35_provider=lambda: service.production_intelligence_dashboard(
            "pilot", context
        ),
        platform_analytics_v35_provider=lambda: service.platform_analytics_dashboard("pilot", context),
    )

    assert application.knowledge_graph_v35_preview()["automatic_action_taken"] is False
    assert application.creative_intelligence_v35_preview()["report"]["analysis_only"] is True
    assert application.production_intelligence_v35_preview()["automatic_action_taken"] is False
    assert application.platform_analytics_v35_preview()["automatic_action_taken"] is False
    routes = {route.path for route in create_observability_app(application).routes}
    assert {
        "/v3.5/knowledge-graph",
        "/v3.5/creative-intelligence",
        "/v3.5/production-intelligence",
        "/v3.5/platform-analytics",
    } <= routes
    assert {
        "knowledge_graph_v35",
        "creative_intelligence_v35",
        "production_intelligence_v35",
        "platform_analytics_v35",
    } <= {tool["name"] for tool in registry.list()}
    assert CliRunner().invoke(app, ["director", "knowledge-graph-v35", "--help"]).exit_code == 0


def test_v3_5_foundation_docs_examples_and_benchmarks_are_available() -> None:
    assets = (
        "docs/KNOWLEDGE_GRAPH_FOUNDATION.md",
        "docs/CREATIVE_INTELLIGENCE_FOUNDATION.md",
        "docs/PRODUCTION_INTELLIGENCE_FOUNDATION.md",
        "docs/PLATFORM_ANALYTICS_FOUNDATION.md",
        "docs/V3_5_ITERATION_1_FOUNDATION_REPORT.md",
        "examples/v3_5/knowledge_graph/run.py",
        "examples/v3_5/creative_intelligence/run.py",
        "examples/v3_5/production_intelligence/run.py",
        "examples/v3_5/platform_analytics/run.py",
        "examples/v3_5/platform_health/run.py",
        "benchmarks/knowledge_graph_v35.py",
        "benchmarks/creative_intelligence.py",
        "benchmarks/production_intelligence_v35.py",
        "benchmarks/platform_analytics.py",
        "benchmarks/platform_health.py",
    )

    assert all((ROOT / asset).is_file() for asset in assets)
