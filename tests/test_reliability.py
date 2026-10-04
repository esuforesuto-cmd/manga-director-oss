"""Recovery, integrity, health, and diagnostics contracts for the v2.2 RC path."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from benchmarks import (
    database_repeatability,
    notification_repeatability,
    plugin_repeatability,
    repository_repeatability,
    workflow_repeatability,
)
from manga_director.cli.app import app
from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState, StateMachine
from manga_director.events import MemoryEventBus
from manga_director.mcp import build_mcp_server
from manga_director.mcp.server import McpServer
from manga_director.observability import HealthMonitor, MetricsRegistry, RuntimeDiagnostics
from manga_director.repositories import (
    InMemoryRepository,
    ProjectIntegrityChecker,
    ProjectLoader,
    RepositoryRecovery,
)
from manga_director.workflow import (
    AgentResult,
    ChapterWorkflowEngine,
    PageNumberWorkflowScheduler,
    ProjectWorkflowEngine,
    WorkflowContext,
    WorkflowCoordinator,
    WorkflowEngine,
    WorkflowRecovery,
)


class _FailingAgent:
    def execute(self, context: WorkflowContext) -> AgentResult:
        del context
        raise RuntimeError("simulated agent failure")


def _mcp_server() -> McpServer:
    repository = InMemoryRepository()
    loader = ProjectLoader(repository)
    events = MemoryEventBus()
    engine = WorkflowEngine(
        state_machine=StateMachine(),
        event_bus=events,
        agents={PageState.DESIGNED: _FailingAgent()},
    )
    project_engine = ProjectWorkflowEngine(repository, events)
    coordinator = WorkflowCoordinator(
        project_engine,
        ChapterWorkflowEngine(repository, events, PageNumberWorkflowScheduler()),
        engine,
        loader,
    )
    return build_mcp_server(
        workflow_engine=engine,
        workflow_coordinator=coordinator,
        project_loader=loader,
        repository=repository,
        diagnostics_provider=lambda: RuntimeDiagnostics(MetricsRegistry()).report(
            plugins={"active": []}
        ),
        health_provider=lambda: HealthMonitor({"repository": lambda: True}).dashboard(),
    )


def test_workflow_recovery_does_not_persist_a_failed_step() -> None:
    repository = InMemoryRepository()
    project = Project(id="recovery", title="Recovery", pages=[Page(page_number=1)])
    repository.save(project)
    loader = ProjectLoader(repository)
    engine = WorkflowEngine(
        state_machine=StateMachine(),
        event_bus=MemoryEventBus(),
        agents={PageState.DESIGNED: _FailingAgent()},
    )

    with pytest.raises(RuntimeError, match="simulated"):
        WorkflowRecovery(engine, loader).resume_step(project.id, 1)

    assert repository.load(project.id).page(1).state == PageState.DRAFT


def test_repository_integrity_and_recovery_validate_metadata_history_and_snapshots() -> None:
    repository = InMemoryRepository()
    project = Project(
        id="integrity",
        title="Integrity",
        pages=[Page(page_number=1, history=[{"step": "Draft"}])],
        workflow={"batches": {}},
    )
    repository.save(project)

    assert ProjectIntegrityChecker().check(project).valid is True
    assert RepositoryRecovery(repository).validate_for_resume(project.id).valid is True

    malformed = project.model_copy(update={"workflow": {"batches": []}}, deep=True)
    report = ProjectIntegrityChecker().check(malformed)
    assert report.valid is False
    assert "snapshot" in report.errors[0]


def test_health_dashboard_and_diagnostic_documents_are_transport_safe() -> None:
    dashboard = HealthMonitor({"repository": lambda: True, "plugin": lambda: False}).dashboard()
    report = RuntimeDiagnostics(MetricsRegistry()).report(configuration={"cache_entries": 1})

    assert dashboard.healthy is False
    assert {item.name for item in dashboard.components} == {"plugin", "repository"}
    assert json.loads(report.to_json())["configuration"]["cache_entries"] == 1
    assert "## Configuration" in report.to_markdown()


def test_cli_diagnostics_health_and_export_commands(tmp_path: Path) -> None:
    runner = CliRunner()
    config = tmp_path / "config.yaml"
    destination = tmp_path / "diagnostics.md"

    health = runner.invoke(app, ["health", "check", "--config", str(config)])
    diagnostics = runner.invoke(app, ["diagnostics", "report", "--config", str(config)])
    exported = runner.invoke(
        app,
        ["diagnostics", "export", "--config", str(config), "--output", str(destination)],
    )

    assert health.exit_code == 0
    assert '"components"' in health.stdout
    assert diagnostics.exit_code == 0
    assert '"system"' in diagnostics.stdout
    assert exported.exit_code == 0
    assert destination.read_text(encoding="utf-8").startswith("# manga-director Runtime")


def test_mcp_diagnostic_tools_return_dtos_only() -> None:
    server = _mcp_server()

    health = server.call_tool("health_status")
    report = server.call_tool("diagnostics_report")
    summary = server.call_tool("system_summary")

    assert health.success is True
    assert health.data["components"][0]["name"] == "repository"
    assert report.data["plugins"] == {"active": []}
    assert "python_version" in summary.data["system"]
    assert {
        "health_status",
        "health_summary",
        "diagnostics_report",
        "system_summary",
        "provider_health",
        "backend_health",
        "repository_check",
    } <= {
        item["name"] for item in server.tools()
    }


def test_repeatability_benchmarks_detect_unstable_provider_free_boundaries() -> None:
    results = [
        workflow_repeatability.run(runs=3),
        repository_repeatability.run(runs=3),
        database_repeatability.run(runs=3),
        notification_repeatability.run(runs=3),
        plugin_repeatability.run(runs=3),
    ]

    assert all(result.runs == 3 for result in results)
    # A wide threshold catches pathological local instability without imposing an SLO on CI hosts.
    assert all(result.relative_spread <= 2.0 for result in results)
