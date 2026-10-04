"""Contracts for the additive v3.2 Studio and Asset foundations."""

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
from manga_director.production import V32FoundationService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext


def _service() -> tuple[V32FoundationService, InMemoryRepository]:
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
    return V32FoundationService(repository), repository


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "pilot-1"},
        state=PageState.PROMPT_BUILT,
        artifacts={"storyboard": {"panels": []}, "prompt": {"text": "not exposed"}},
        metadata={"workflow_history": [{"step": "prompt", "to": "PromptBuilt"}]},
    )


def test_creative_studio_is_advisory_and_does_not_change_one_page_workflow() -> None:
    service, repository = _service()
    context = _context()

    report = service.creative_studio("pilot", context)

    assert report.workspace.persisted is False
    assert report.session.agent_execution_enabled is False
    assert report.dashboard.workflow_execution_started is False
    assert report.activity.approval_granted is False
    assert report.summary.automatic_action_taken is False
    assert context.state is PageState.PROMPT_BUILT
    assert repository.load("pilot").title == "Pilot"


def test_asset_intelligence_is_redacted_and_repository_read_only() -> None:
    service, repository = _service()

    report = service.asset_intelligence("pilot", _context())
    rendered = report.to_json()

    assert report.index.repository_read_only is True
    assert report.summary.values_redacted is True
    assert report.persistence_mutated is False
    assert "not exposed" not in rendered
    assert repository.load("pilot").metadata["world"] == "not exposed"


def test_workflow_profiles_observe_the_state_machine_without_transition() -> None:
    service, _ = _service()
    context = _context()

    report, summary = service.workflow_profiles(context)

    assert report.profile.execution.suggested_command == "generate"
    assert report.profile.execution.execution_enabled is False
    assert report.profile.pipeline.pipeline_changed is False
    assert summary.automatic_transition is False
    assert context.state is PageState.PROMPT_BUILT


def test_production_analytics_does_not_execute_review_quality_or_approval() -> None:
    service, _ = _service()

    report = service.production_analytics(_context())

    assert report.workflow.workflow_executed is False
    assert report.review.review_executed is False
    assert report.review.approval_granted is False
    assert report.quality.quality_score_computed is False
    assert report.summary.runtime_automation_started is False


def test_v3_2_dashboards_are_available_via_fastapi_and_mcp_dto_boundaries() -> None:
    service, _ = _service()
    context = _context()
    application = ObservabilityApplication(
        health=lambda: None,  # type: ignore[arg-type]
        diagnostics=lambda: None,  # type: ignore[arg-type]
        repository_check=lambda: None,  # type: ignore[arg-type]
        creative_studio_v32=lambda: service.creative_studio_dashboard("pilot", context),
        asset_intelligence_v32=lambda: service.asset_intelligence_dashboard("pilot", context),
        workflow_profiles_v32=lambda: service.workflow_profile_dashboard(context),
        production_analytics_v32=lambda: service.production_analytics_dashboard(context),
        workspace_dashboard_v32=lambda: service.creative_studio_dashboard("pilot", context),
    )
    registry = default_tool_registry(
        cast(MangaApplicationService, None),
        creative_studio_v32_provider=lambda: service.creative_studio_dashboard("pilot", context),
        asset_intelligence_v32_provider=lambda: service.asset_intelligence_dashboard(
            "pilot", context
        ),
        workflow_profiles_v32_provider=lambda: service.workflow_profile_dashboard(context),
        production_analytics_v32_provider=lambda: service.production_analytics_dashboard(context),
        workspace_dashboard_v32_provider=lambda: service.creative_studio_dashboard(
            "pilot", context
        ),
    )

    assert application.creative_studio_v32_preview()["automatic_action_taken"] is False
    assert application.asset_intelligence_v32_preview()["report"]["persistence_mutated"] is False
    assert application.workflow_profiles_v32_preview()["summary"]["automatic_transition"] is False
    assert application.production_analytics_v32_preview()["automatic_action_taken"] is False
    routes = {route.path for route in create_observability_app(application).routes}
    assert {
        "/v3.2/creative-studio",
        "/v3.2/asset-intelligence",
        "/v3.2/workflow-profiles",
        "/v3.2/production-analytics",
        "/v3.2/workspace-dashboard",
    } <= routes
    assert registry.invoke("creative_studio_v32", {}).data["automatic_action_taken"] is False
    assert (
        registry.invoke("asset_intelligence_v32", {}).data["report"]["persistence_mutated"] is False
    )
    assert (
        registry.invoke("workflow_profiles_v32", {}).data["summary"]["automatic_transition"]
        is False
    )
    assert registry.invoke("production_analytics_v32", {}).data["automatic_action_taken"] is False


def test_v3_2_cli_commands_are_additive_preview_entry_points() -> None:
    result = CliRunner().invoke(app, ["director", "--help"])

    assert result.exit_code == 0
    assert "creative-studio" in result.output
    assert "asset-intelligence" in result.output
    assert "workflow-profiles" in result.output
    assert "production-analytics" in result.output
    assert "workspace-dashboard" in result.output
