"""Contracts for the additive v3.4 intelligence projections."""

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
from manga_director.production import V34FoundationService, V34InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _service() -> tuple[V34InsightsService, InMemoryRepository]:
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
    foundation = V34FoundationService(repository)
    return V34InsightsService(foundation, repository), repository


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "pilot-1", "storyboard": {"panels": []}},
        state=PageState.QUALITY_CHECKED,
        artifacts={"storyboard": {"panels": []}, "prompt": {"text": "not exposed"}},
        metadata={"workflow_history": [{"step": "quality", "to": "QualityChecked"}]},
    )


def test_knowledge_intelligence_is_read_only_and_advisory() -> None:
    service, repository = _service()

    report = service.knowledge_intelligence("pilot", _context())

    assert report.analysis_only is True
    assert report.dependencies.dependency_resolved is False
    assert report.quality.quality_score_computed is False
    assert report.recommendations.recommendation_applied is False
    assert report.summary.repository_mutated is False
    assert repository.load("pilot").metadata["world"] == "not exposed"


def test_production_optimization_does_not_modify_workflow_or_allocate() -> None:
    service, _ = _service()

    report = service.production_optimization("pilot", _context())

    assert report.analysis_only is True
    assert report.capacity.capacity_plan_applied is False
    assert report.allocation.resource_allocated is False
    assert report.allocation.allocation_rebalanced is False
    assert report.bottleneck.bottleneck == "human_approval"
    assert report.bottleneck.remediation_applied is False
    assert report.summary.workflow_modified is False


def test_organization_analytics_cannot_score_people_or_take_action() -> None:
    service, _ = _service()

    report = service.organization_analytics("pilot", _context())

    assert report.analysis_only is True
    assert report.trend.trend_computed is False
    assert report.productivity.productivity_score_computed is False
    assert report.productivity.personnel_action_taken is False
    assert report.collaboration.notification_sent is False
    assert report.role_utilization.role_changed is False
    assert report.forecast.delivery_committed is False


def test_release_analytics_cannot_publish_deploy_or_change_api() -> None:
    service, _ = _service()

    report = service.release_analytics("pilot", _context())

    assert report.analysis_only is True
    assert report.trend.trend_computed is False
    assert report.deployment.analytics_collected_remotely is False
    assert report.deployment.deployment_started is False
    assert report.regression.remediation_applied is False
    assert report.compatibility.public_api_changed is False
    assert report.forecast.release_authorized is False
    assert report.summary.tag_created is False
    assert report.summary.publication_started is False


def test_v3_4_insights_are_available_via_fastapi_mcp_and_cli_dto_boundaries() -> None:
    service, _ = _service()
    context = _context()
    application = ObservabilityApplication(
        health=lambda: None,  # type: ignore[arg-type]
        diagnostics=lambda: None,  # type: ignore[arg-type]
        repository_check=lambda: None,  # type: ignore[arg-type]
        knowledge_intelligence_v34=lambda: service.knowledge_intelligence_dashboard(
            "pilot", context
        ),
        production_optimization_v34=lambda: service.production_optimization_dashboard(
            "pilot", context
        ),
        organization_analytics_v34=lambda: service.organization_analytics_dashboard(
            "pilot", context
        ),
        release_analytics_v34=lambda: service.release_analytics_dashboard("pilot", context),
    )
    registry = default_tool_registry(
        cast(MangaApplicationService, None),
        knowledge_intelligence_v34_provider=lambda: service.knowledge_intelligence_dashboard(
            "pilot", context
        ),
        production_optimization_v34_provider=lambda: service.production_optimization_dashboard(
            "pilot", context
        ),
        organization_analytics_v34_provider=lambda: service.organization_analytics_dashboard(
            "pilot", context
        ),
        release_analytics_v34_provider=lambda: service.release_analytics_dashboard(
            "pilot", context
        ),
    )

    assert application.knowledge_intelligence_v34_preview()["automatic_action_taken"] is False
    assert application.production_optimization_v34_preview()["report"]["analysis_only"] is True
    assert application.organization_analytics_v34_preview()["automatic_action_taken"] is False
    assert application.release_analytics_v34_preview()["automatic_action_taken"] is False
    routes = {route.path for route in create_observability_app(application).routes}
    assert {
        "/v3.4/knowledge-intelligence",
        "/v3.4/production-optimization",
        "/v3.4/organization-analytics",
        "/v3.4/release-analytics",
    } <= routes
    assert {
        "knowledge_intelligence_v34",
        "production_optimization_v34",
        "organization_analytics_v34",
        "release_analytics_v34",
    } <= {tool["name"] for tool in registry.list()}
    assert (
        CliRunner().invoke(app, ["director", "knowledge-intelligence-v34", "--help"]).exit_code == 0
    )


def test_v3_4_insight_docs_examples_and_benchmarks_are_available() -> None:
    assets = (
        "docs/KNOWLEDGE_INTELLIGENCE.md",
        "docs/PRODUCTION_OPTIMIZATION.md",
        "docs/ORGANIZATION_ANALYTICS.md",
        "docs/RELEASE_ANALYTICS.md",
        "docs/V3_4_ITERATION_2_KNOWLEDGE_INTELLIGENCE_REPORT.md",
        "examples/knowledge_intelligence/run.py",
        "examples/production_optimization/run.py",
        "examples/organization_analytics/run.py",
        "examples/release_analytics/run.py",
        "examples/capacity_optimization/run.py",
        "benchmarks/knowledge_intelligence.py",
        "benchmarks/production_optimization.py",
        "benchmarks/organization_analytics.py",
        "benchmarks/release_analytics.py",
        "benchmarks/capacity_optimization.py",
    )

    assert all((ROOT / asset).is_file() for asset in assets)
