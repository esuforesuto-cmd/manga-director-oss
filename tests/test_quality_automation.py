"""Contracts for the v2.5 read-only quality automation facade."""

from __future__ import annotations

from pathlib import Path

from manga_director.cli.config import AppConfig
from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.production import (
    DevelopmentDiagnostics,
    QualityAutomation,
    RepositoryMaintenance,
)
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _repository() -> InMemoryRepository:
    repository = InMemoryRepository()
    repository.save(
        Project(
            id="quality",
            title="Quality",
            pages=[Page(page_number=1, history=[{"step": "design"}])],
        )
    )
    return repository


def _automation(repository: InMemoryRepository) -> QualityAutomation:
    return QualityAutomation(repository=repository, configuration=AppConfig(), root=ROOT)


def test_repository_maintenance_reports_statistics_and_non_destructive_cleanup() -> None:
    repository = _repository()
    maintenance = RepositoryMaintenance(repository)

    report = maintenance.report("quality")

    assert report.healthy is True
    assert report.statistics.projects == 1
    assert report.statistics.pages == 1
    assert report.large_repository.largest_project_id == "quality"
    assert report.cleanup.destructive_action_performed is False
    assert "# Repository Maintenance" in report.to_markdown()


def test_quality_pipeline_validates_repository_workflow_configuration_api_docs_and_release() -> None:
    automation = _automation(_repository())
    context = WorkflowContext(
        page={"id": "one"},
        state=PageState.GENERATED,
        artifacts={PageState.STORYBOARDED.value: {"panels": []}},
    )

    report = automation.pipeline(context, "quality")

    assert report.dashboard.healthy is True
    assert report.dashboard.total == 6
    assert {result.name for result in report.results} == {
        "repository_validation",
        "workflow_validation",
        "configuration_validation",
        "api_compatibility_validation",
        "documentation_validation",
        "release_artifact_validation",
    }
    assert "# Quality Pipeline" in report.to_markdown()


def test_workflow_validation_rejects_generated_context_without_storyboard() -> None:
    result = _automation(_repository()).workflow_validation(
        WorkflowContext(page={"id": "one"}, state=PageState.GENERATED)
    )

    assert result.valid is False
    assert any("storyboard" in error.lower() for error in result.errors)


def test_documentation_and_api_compatibility_validations_are_explicit_dtos() -> None:
    automation = _automation(_repository())

    documentation = automation.documentation_validation()
    api = automation.api_compatibility_validation()

    assert documentation.valid is True
    assert api.valid is True
    assert "local_markdown_links" in documentation.checks
    assert "root_public_api" in api.checks


def test_development_diagnostics_reports_workspace_dependencies_and_build_metadata() -> None:
    report = DevelopmentDiagnostics(ROOT).report()

    assert report.workspace.valid is True
    assert report.environment.source_present is True
    assert report.dependencies.runtime
    assert report.build.version_source == "src/manga_director/_version.py"
    assert "# Development Diagnostics" in report.to_markdown()


def test_release_validation_and_production_summary_remain_read_only() -> None:
    automation = _automation(_repository())
    context = WorkflowContext(page={"id": "one"})

    release = automation.release_artifact_validation()
    summary = automation.production_summary(context, "quality")

    assert release.valid is True
    assert summary.release_readiness is True
    assert summary.maintenance_summary.statistics.projects == 1
    assert "# Production Quality Summary" in summary.to_markdown()
