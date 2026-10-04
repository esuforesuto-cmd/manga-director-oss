"""Phase 42 operational DTO, recovery, and repeatability contracts."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from benchmarks import backend_repeatability, configuration_repeatability, provider_repeatability
from manga_director.adapters import ImageBackendRuntime, LLMProviderRuntime
from manga_director.api import ObservabilityApplication
from manga_director.cli.app import app
from manga_director.cli.config import AppConfig, configuration_governance
from manga_director.domain.project import Page, Project
from manga_director.observability import MetricsRegistry, RuntimeDiagnostics, RuntimeHealth
from manga_director.production import PlanningService, ProviderOrchestrator, WorkflowPlanner
from manga_director.repositories import (
    InMemoryRepository,
    ProjectIntegrityChecker,
    RepositorySelfCheck,
)
from manga_director.workflow import WorkflowContext


def _health(repository: InMemoryRepository) -> RuntimeHealth:
    return RuntimeHealth(
        config=AppConfig(),
        providers=LLMProviderRuntime(),
        backends=ImageBackendRuntime(),
        repository_check=RepositorySelfCheck(repository),
        configuration_summary=lambda: configuration_governance(AppConfig()).model_dump(),
    )


def test_runtime_health_reports_every_boundary_as_safe_dto() -> None:
    repository = InMemoryRepository()
    repository.save(Project(id="health", title="Health", pages=[Page(page_number=1)]))

    report = _health(repository).report("health")

    assert report.healthy is True
    assert report.provider.healthy == report.provider.registered
    assert report.backend.healthy == report.backend.registered
    assert report.repository["healthy"] is True
    assert report.configuration["healthy"] is True
    assert "# Runtime Health" in report.to_markdown()


def test_repository_self_check_detects_snapshot_integrity_failure() -> None:
    repository = InMemoryRepository()
    project = Project(id="repository", title="Repository", pages=[Page(page_number=1)])
    repository.save(project)
    check = RepositorySelfCheck(repository)

    assert check.check(project.id).healthy is True
    malformed = project.model_copy(update={"workflow": {"batches": []}}, deep=True)
    assert ProjectIntegrityChecker().check(malformed).valid is False


def test_observability_application_returns_transport_safe_dtos() -> None:
    repository = InMemoryRepository()
    repository.save(Project(id="api", title="API", pages=[Page(page_number=1)]))
    application = ObservabilityApplication(
        health=lambda: _health(repository).report("api"),
        diagnostics=lambda: RuntimeDiagnostics(MetricsRegistry()).report(workflow={"healthy": True}),
        repository_check=lambda: RepositorySelfCheck(repository).check("api"),
    )

    assert application.health_summary()["workflow"]["scope"] == "one_page"
    assert application.provider_health()["kind"] == "provider"
    assert application.backend_health()["kind"] == "backend"
    assert application.diagnostics_report()["workflow"]["healthy"] is True
    assert application.repository_integrity()["healthy"] is True


def test_observability_application_exposes_optional_planning_previews() -> None:
    repository = InMemoryRepository()
    planning = PlanningService(
        planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime())
    )
    application = ObservabilityApplication(
        health=lambda: _health(repository).report(),
        diagnostics=lambda: RuntimeDiagnostics(MetricsRegistry()).report(),
        repository_check=lambda: RepositorySelfCheck(repository).check(),
        planning=lambda: planning.summary(WorkflowContext()),
        provider_selection=lambda: planning.provider_preview(("text",)),
        analytics=lambda: {"analysis_only": True},
        enterprise=lambda: {"healthy": True},
        executive=lambda: {"automatic_action_taken": False},
        assurance=lambda: {"analysis_only": True},
        provider_governance=lambda: {"governance_only": True},
        dashboard=lambda: {"automatic_release": False},
    )

    assert application.planning_preview()["execution_performed"] is False
    assert application.provider_preview()["selection_performed"] is False
    assert application.workflow_analytics()["analysis_only"] is True
    assert application.enterprise_diagnostics()["healthy"] is True
    assert application.executive_analytics()["automatic_action_taken"] is False
    assert application.workflow_assurance()["analysis_only"] is True
    assert application.provider_governance()["governance_only"] is True
    assert application.executive_dashboard()["automatic_release"] is False


def test_phase_42_cli_health_and_integrity_commands(tmp_path: Path) -> None:
    runner = CliRunner()
    config = tmp_path / "config.yaml"

    health = runner.invoke(app, ["health", "summary", "--config", str(config)])
    providers = runner.invoke(app, ["provider", "check", "--config", str(config)])
    backends = runner.invoke(app, ["backend", "check", "--config", str(config)])
    repository = runner.invoke(app, ["repository", "check", "--config", str(config)])

    assert health.exit_code == providers.exit_code == backends.exit_code == repository.exit_code == 0
    assert '"workflow"' in health.stdout
    assert '"kind": "provider"' in providers.stdout
    assert '"kind": "backend"' in backends.stdout
    assert '"projects_checked": 0' in repository.stdout


def test_provider_backend_and_configuration_repeatability_smoke() -> None:
    results = [
        provider_repeatability.run(runs=3),
        backend_repeatability.run(runs=3),
        configuration_repeatability.run(runs=3),
    ]

    assert all(result.runs == 3 and result.relative_spread <= 2.0 for result in results)
