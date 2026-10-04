"""Contracts for the additive v3.3 production and intelligence foundations."""

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
from manga_director.production import V33FoundationService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _service() -> tuple[V33FoundationService, InMemoryRepository]:
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
    return V33FoundationService(repository), repository


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "pilot-1", "storyboard": {"panels": []}},
        state=PageState.PROMPT_BUILT,
        artifacts={"storyboard": {"panels": []}, "prompt": {"text": "not exposed"}},
        metadata={"workflow_history": [{"step": "prompt", "to": "PromptBuilt"}]},
    )


def test_production_pipeline_observes_the_state_machine_without_transition() -> None:
    service, repository = _service()
    context = _context()

    report = service.production_pipeline("pilot", context)

    assert report.session.workflow_execution_enabled is False
    assert report.transition.transition_applied is False
    assert report.approval.approval_granted is False
    assert report.summary.next_command == "generate"
    assert context.state is PageState.PROMPT_BUILT
    assert repository.load("pilot").title == "Pilot"


def test_quality_intelligence_is_diagnostic_and_cannot_approve() -> None:
    service, _ = _service()

    report = service.quality_intelligence(_context())

    assert report.analysis_only is True
    assert report.dashboard.approval_granted is False
    assert all(rule.enforced_by_report is False for rule in report.rules)
    assert all(finding.remediation_applied is False for finding in report.dashboard.findings)


def test_asset_lifecycle_is_read_only_and_does_not_archive() -> None:
    service, repository = _service()

    report = service.asset_lifecycle("pilot", _context())

    assert report.summary.repository_read_only is True
    assert report.summary.automatic_action_taken is False
    assert all(item.archive_performed is False for item in report.archive)
    assert all(item.dependency_persisted is False for item in report.dependencies)
    assert repository.load("pilot").metadata["world"] == "not exposed"


def test_project_intelligence_is_advisory_and_does_not_schedule() -> None:
    service, _ = _service()

    report = service.project_intelligence("pilot", _context())

    assert report.analysis_only is True
    assert report.health.health_computed is False
    assert report.resources.resource_allocated is False
    assert report.schedule.schedule_modified is False
    assert report.schedule.delivery_commitment_created is False
    assert report.executive.automatic_action_taken is False


def test_v3_3_dashboards_are_available_via_fastapi_mcp_and_cli_dto_boundaries() -> None:
    service, _ = _service()
    context = _context()
    application = ObservabilityApplication(
        health=lambda: None,  # type: ignore[arg-type]
        diagnostics=lambda: None,  # type: ignore[arg-type]
        repository_check=lambda: None,  # type: ignore[arg-type]
        production_pipeline_v33=lambda: service.production_pipeline_dashboard("pilot", context),
        quality_intelligence_v33=lambda: service.quality_intelligence_dashboard(context),
        asset_lifecycle_v33=lambda: service.asset_lifecycle_dashboard("pilot", context),
        project_intelligence_v33=lambda: service.project_intelligence_dashboard("pilot", context),
    )
    registry = default_tool_registry(
        cast(MangaApplicationService, None),
        production_pipeline_v33_provider=lambda: service.production_pipeline_dashboard("pilot", context),
        quality_intelligence_v33_provider=lambda: service.quality_intelligence_dashboard(context),
        asset_lifecycle_v33_provider=lambda: service.asset_lifecycle_dashboard("pilot", context),
        project_intelligence_v33_provider=lambda: service.project_intelligence_dashboard("pilot", context),
    )

    assert application.production_pipeline_v33_preview()["automatic_action_taken"] is False
    assert application.quality_intelligence_v33_preview()["report"]["analysis_only"] is True
    assert application.asset_lifecycle_v33_preview()["automatic_action_taken"] is False
    assert application.project_intelligence_v33_preview()["automatic_action_taken"] is False
    routes = {route.path for route in create_observability_app(application).routes}
    assert {
        "/v3.3/production-pipeline",
        "/v3.3/quality-intelligence",
        "/v3.3/asset-lifecycle",
        "/v3.3/project-intelligence",
    } <= routes
    assert {
        "production_pipeline_v33",
        "quality_intelligence_v33",
        "asset_lifecycle_v33",
        "project_intelligence_v33",
    } <= {tool["name"] for tool in registry.list()}
    assert CliRunner().invoke(app, ["director", "production-pipeline-v33", "--help"]).exit_code == 0


def test_v3_3_foundation_docs_examples_and_benchmarks_are_available() -> None:
    assets = (
        "docs/PRODUCTION_PIPELINE_FOUNDATION.md",
        "docs/QUALITY_INTELLIGENCE_FOUNDATION.md",
        "docs/ASSET_LIFECYCLE_FOUNDATION.md",
        "docs/PROJECT_INTELLIGENCE_FOUNDATION.md",
        "docs/V3_3_ITERATION_1_FOUNDATION_REPORT.md",
        "examples/production_pipeline/run.py",
        "examples/quality_intelligence/run.py",
        "examples/asset_lifecycle/run.py",
        "examples/project_intelligence/run.py",
        "examples/project_health/run.py",
        "benchmarks/production_pipeline.py",
        "benchmarks/quality_intelligence.py",
        "benchmarks/asset_lifecycle.py",
        "benchmarks/project_intelligence.py",
        "benchmarks/project_health.py",
    )

    assert all((ROOT / asset).is_file() for asset in assets)
