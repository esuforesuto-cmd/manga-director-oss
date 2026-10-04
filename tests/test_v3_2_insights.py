"""Contracts for v3.2 Iteration 2 analysis-only insight DTOs."""

from __future__ import annotations

from typing import cast

from typer.testing import CliRunner

from manga_director.api import ObservabilityApplication
from manga_director.api.observability import create_observability_app
from manga_director.cli.app import app
from manga_director.domain.project import Chapter, Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.mcp.application import MangaApplicationService
from manga_director.mcp.registry import default_tool_registry
from manga_director.production import V32FoundationService, V32InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext


def _service() -> tuple[V32InsightsService, InMemoryRepository]:
    repository = InMemoryRepository()
    repository.save(
        Project(
            id="pilot",
            title="Pilot",
            chapters=[Chapter(id="one", title="One", page_numbers=[1])],
            pages=[Page(page_number=1, storyboard={"panels": []})],
            metadata={"reference": {"secret": "not exposed"}},
        )
    )
    foundation = V32FoundationService(repository)
    return V32InsightsService(foundation, repository), repository


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "pilot-1"},
        state=PageState.PROMPT_BUILT,
        artifacts={"storyboard": {"panels": []}, "prompt": {"text": "not exposed"}},
        metadata={"workflow_history": [{"step": "prompt", "to": "PromptBuilt"}]},
    )


def test_creative_workspace_is_review_only_and_does_not_start_tasks() -> None:
    service, repository = _service()
    context = _context()

    report = service.creative_workspace("pilot", context)

    assert report.session.review_only is True
    assert report.session.workflow_execution_enabled is False
    assert report.activity.repository_mutated is False
    assert all(task.automatically_started is False for task in report.tasks)
    assert report.progress.workflow_advanced is False
    assert context.state is PageState.PROMPT_BUILT
    assert repository.load("pilot").title == "Pilot"


def test_asset_analytics_stays_redacted_and_read_only() -> None:
    service, repository = _service()

    report, summary = service.asset_analytics("pilot", _context())
    rendered = report.to_json()

    assert report.values_redacted is True
    assert report.repository_mutated is False
    assert report.quality.quality_scored is False
    assert summary.automatic_action_taken is False
    assert "not exposed" not in rendered
    assert repository.load("pilot").metadata["reference"]["secret"] == "not exposed"


def test_workflow_intelligence_observes_state_machine_without_transition() -> None:
    service, _ = _service()
    context = _context()

    report = service.workflow_intelligence(context)

    assert report.recommendation.next_command == "generate"
    assert report.recommendation.workflow_changed is False
    assert report.timeline.execution_replayed is False
    assert report.summary.automatic_transition is False
    assert context.state is PageState.PROMPT_BUILT


def test_production_insights_do_not_forecast_or_automate_operations() -> None:
    service, _ = _service()

    report = service.production_insights(_context())

    assert report.quality.quality_scored is False
    assert report.review.review_executed is False
    assert report.productivity.workflow_started is False
    assert report.forecast.forecast == "not_computed"
    assert report.forecast.automation_started is False
    assert report.executive.release_authorized is False


def test_pipeline_analysis_reports_a_bottleneck_without_applying_a_profile() -> None:
    service, _ = _service()
    context = _context().model_copy(update={"state": PageState.QUALITY_CHECKED})

    report = service.workflow_intelligence_dashboard(context).report.bottleneck

    assert report.bottleneck == "human_approval"
    assert report.requires_human_review is True
    assert report.remediation_applied is False
    assert context.state is PageState.QUALITY_CHECKED


def test_v3_2_insight_dashboards_are_dto_only_for_fastapi_mcp_and_cli() -> None:
    service, _ = _service()
    context = _context()
    application = ObservabilityApplication(
        health=lambda: None,  # type: ignore[arg-type]
        diagnostics=lambda: None,  # type: ignore[arg-type]
        repository_check=lambda: None,  # type: ignore[arg-type]
        creative_workspace_v32=lambda: service.creative_workspace_dashboard("pilot", context),
        asset_analytics_v32=lambda: service.asset_analytics_dashboard("pilot", context),
        workflow_intelligence_v32=lambda: service.workflow_intelligence_dashboard(context),
        production_insights_v32=lambda: service.production_insights_dashboard(context),
        pipeline_analysis_v32=lambda: (
            service.workflow_intelligence_dashboard(context).report.bottleneck
        ),
    )
    registry = default_tool_registry(
        cast(MangaApplicationService, None),
        creative_workspace_v32_provider=lambda: service.creative_workspace_dashboard(
            "pilot", context
        ),
        asset_analytics_v32_provider=lambda: service.asset_analytics_dashboard("pilot", context),
        workflow_intelligence_v32_provider=lambda: service.workflow_intelligence_dashboard(context),
        production_insights_v32_provider=lambda: service.production_insights_dashboard(context),
        pipeline_analysis_v32_provider=lambda: (
            service.workflow_intelligence_dashboard(context).report.bottleneck
        ),
    )

    assert application.creative_workspace_v32_preview()["automatic_action_taken"] is False
    assert application.asset_analytics_v32_preview()["report"]["repository_mutated"] is False
    assert application.workflow_intelligence_v32_preview()["automatic_action_taken"] is False
    assert application.production_insights_v32_preview()["automatic_action_taken"] is False
    routes = {route.path for route in create_observability_app(application).routes}
    assert {
        "/v3.2/creative-workspace",
        "/v3.2/asset-analytics",
        "/v3.2/workflow-intelligence",
        "/v3.2/production-insights",
        "/v3.2/pipeline-analysis",
    } <= routes
    assert registry.invoke("creative_workspace_v32", {}).data["automatic_action_taken"] is False
    assert registry.invoke("asset_analytics_v32", {}).data["report"]["repository_mutated"] is False
    assert registry.invoke("workflow_intelligence_v32", {}).data["automatic_action_taken"] is False
    assert registry.invoke("production_insights_v32", {}).data["automatic_action_taken"] is False
    command_help = CliRunner().invoke(app, ["director", "--help"])
    assert command_help.exit_code == 0
    assert "creative-workspace" in command_help.output
    assert "asset-analytics" in command_help.output
    assert "workflow-intelligence-v32" in command_help.output
    assert "production-insights" in command_help.output
    assert "pipeline-analysis" in command_help.output
