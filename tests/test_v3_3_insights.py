"""Contracts for the additive v3.3 Iteration 2 insight DTOs."""

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
from manga_director.production import V33FoundationService, V33InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _service() -> tuple[V33InsightsService, InMemoryRepository]:
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
    foundation = V33FoundationService(repository)
    return V33InsightsService(foundation, repository), repository


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "pilot-1", "storyboard": {"panels": []}},
        state=PageState.PROMPT_BUILT,
        artifacts={"storyboard": {"panels": []}, "prompt": {"text": "not exposed"}},
        metadata={"workflow_history": [{"step": "prompt", "to": "PromptBuilt"}]},
    )


def test_production_intelligence_is_advisory_and_cannot_modify_workflow() -> None:
    service, repository = _service()
    context = _context()

    report = service.production_intelligence("pilot", context)

    assert report.analysis_only is True
    assert report.bottleneck.remediation_applied is False
    assert report.optimization.workflow_modified is False
    assert report.optimization.optimization_applied is False
    assert report.summary.automatic_action_taken is False
    assert context.state is PageState.PROMPT_BUILT
    assert repository.load("pilot").title == "Pilot"


def test_quality_analytics_cannot_score_regress_or_approve() -> None:
    service, _ = _service()

    report = service.quality_analytics(_context())

    assert report.analysis_only is True
    assert report.trend.score_computed is False
    assert report.regression.regression_detected is False
    assert report.regression.remediation_applied is False
    assert report.executive.approval_authorized is False


def test_asset_intelligence_is_redacted_and_repository_read_only() -> None:
    service, repository = _service()

    report = service.asset_intelligence("pilot", _context())

    assert report.analysis_only is True
    assert report.summary.values_redacted is True
    assert report.summary.repository_mutated is False
    assert report.consistency.repair_applied is False
    assert report.recommendations.recommendation_applied is False
    assert "not exposed" not in report.model_dump_json()
    assert repository.load("pilot").metadata["world"] == "not exposed"


def test_project_operations_cannot_allocate_schedule_or_commit_delivery() -> None:
    service, _ = _service()

    report = service.project_operations("pilot", _context())

    assert report.analysis_only is True
    assert report.operations.operation_started is False
    assert report.resource_utilization.resource_allocated is False
    assert report.delivery_forecast.delivery_committed is False
    assert report.risks.mitigation_applied is False
    assert report.summary.scheduling_changed is False


def test_v3_3_insights_are_available_via_fastapi_mcp_and_cli_dto_boundaries() -> None:
    service, _ = _service()
    context = _context()
    application = ObservabilityApplication(
        health=lambda: None,  # type: ignore[arg-type]
        diagnostics=lambda: None,  # type: ignore[arg-type]
        repository_check=lambda: None,  # type: ignore[arg-type]
        production_intelligence_v33=lambda: service.production_intelligence_dashboard("pilot", context),
        quality_analytics_v33=lambda: service.quality_analytics_dashboard(context),
        asset_intelligence_v33=lambda: service.asset_intelligence_dashboard("pilot", context),
        project_operations_v33=lambda: service.project_operations_dashboard("pilot", context),
    )
    registry = default_tool_registry(
        cast(MangaApplicationService, None),
        production_intelligence_v33_provider=lambda: service.production_intelligence_dashboard(
            "pilot", context
        ),
        quality_analytics_v33_provider=lambda: service.quality_analytics_dashboard(context),
        asset_intelligence_v33_provider=lambda: service.asset_intelligence_dashboard("pilot", context),
        project_operations_v33_provider=lambda: service.project_operations_dashboard("pilot", context),
    )

    assert application.production_intelligence_v33_preview()["automatic_action_taken"] is False
    assert application.quality_analytics_v33_preview()["report"]["analysis_only"] is True
    assert application.asset_intelligence_v33_preview()["report"]["summary"]["values_redacted"] is True
    assert application.project_operations_v33_preview()["automatic_action_taken"] is False
    routes = {route.path for route in create_observability_app(application).routes}
    assert {
        "/v3.3/production-intelligence",
        "/v3.3/quality-analytics",
        "/v3.3/asset-intelligence",
        "/v3.3/project-operations",
    } <= routes
    assert {
        "production_intelligence_v33",
        "quality_analytics_v33",
        "asset_intelligence_v33",
        "project_operations_v33",
    } <= {tool["name"] for tool in registry.list()}
    assert CliRunner().invoke(app, ["director", "production-intelligence-v33", "--help"]).exit_code == 0


def test_v3_3_insight_docs_examples_and_benchmarks_are_available() -> None:
    assets = (
        "docs/PRODUCTION_INTELLIGENCE.md",
        "docs/QUALITY_ANALYTICS.md",
        "docs/ASSET_INTELLIGENCE_V3_3.md",
        "docs/PROJECT_OPERATIONS.md",
        "docs/V3_3_ITERATION_2_PRODUCTION_INTELLIGENCE_REPORT.md",
        "examples/production_intelligence/run.py",
        "examples/quality_analytics/run.py",
        "examples/asset_intelligence/v3_3_insights.py",
        "examples/project_operations/run.py",
        "examples/pipeline_efficiency/run.py",
        "benchmarks/production_intelligence.py",
        "benchmarks/quality_analytics.py",
        "benchmarks/asset_intelligence_v33.py",
        "benchmarks/project_operations.py",
        "benchmarks/pipeline_efficiency.py",
    )

    assert all((ROOT / asset).is_file() for asset in assets)
