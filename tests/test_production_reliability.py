"""Read-only reliability and production-readiness contracts."""

from __future__ import annotations

from manga_director.adapters import ImageBackendRuntime, LLMProviderRuntime
from manga_director.cli.config import AppConfig
from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState, StateMachine
from manga_director.events import MemoryEventBus
from manga_director.observability import MetricsRegistry, RuntimeDiagnostics
from manga_director.production import (
    BackendManagement,
    LongRunningDiagnostics,
    OperationalDiagnostics,
    ProductionReadiness,
    ProviderManagement,
    ReliabilityDiagnostics,
    ReliabilityOperations,
    RuntimeConfiguration,
)
from manga_director.repositories import InMemoryRepository, ProjectLoader
from manga_director.workflow import AgentResult, WorkflowContext, WorkflowEngine


class _DesignAgent:
    def execute(self, context: WorkflowContext) -> AgentResult:
        return AgentResult(success=True, state=PageState.DESIGNED, payload={"purpose": "test"})


def _components() -> tuple[InMemoryRepository, ProjectLoader, WorkflowEngine, ReliabilityOperations]:
    repository = InMemoryRepository()
    repository.save(Project(id="reliable", title="Reliable", pages=[Page(page_number=1)]))
    loader = ProjectLoader(repository)
    engine = WorkflowEngine(
        state_machine=StateMachine(),
        event_bus=MemoryEventBus(),
        agents={PageState.DESIGNED: _DesignAgent()},
    )
    return repository, loader, engine, ReliabilityOperations(
        engine=engine,
        loader=loader,
        repository=repository,
    )


def test_resume_validation_consistency_and_simulation_do_not_execute_or_persist() -> None:
    repository, _, _, reliability = _components()

    validation = reliability.validate_resume("reliable", 1)
    simulation = reliability.simulate_recovery("reliable", 1)

    assert validation.resumable is True
    assert validation.consistency.executable_step == "design"
    assert simulation.safe_to_resume is True
    assert simulation.next_step == "design"
    assert repository.load("reliable").page(1).state == PageState.DRAFT


def test_workflow_consistency_detects_state_without_matching_history() -> None:
    repository, _, _, reliability = _components()
    inconsistent = Project(
        id="inconsistent",
        title="Inconsistent",
        pages=[Page(page_number=1, state=PageState.DESIGNED, page_design={"purpose": "test"})],
    )
    repository.save(inconsistent)

    report = reliability.consistency("inconsistent", 1)

    assert report.valid is False
    assert "history" in report.errors[0]


def test_repository_integrity_recovery_report_includes_self_check_and_resume_evidence() -> None:
    _, _, _, reliability = _components()

    report = reliability.recovery_report("reliable", 1)

    assert report.repository.healthy is True
    assert report.resume.resumable is True
    assert report.simulation.persisted_unchanged is True
    assert "# Recovery Report" in report.to_markdown()


def test_long_running_diagnostics_is_bounded_and_passive() -> None:
    metrics = MetricsRegistry()
    metrics.increment("workflow.executions")
    metrics.increment("batch.executions")
    diagnostics = LongRunningDiagnostics(metrics, limit=2)

    diagnostics.capture(active_tasks=1)
    report = diagnostics.capture(active_tasks=0, graceful_recovery={"safe": True})

    assert len(report.tasks) == 2
    assert report.tasks[-1].active_tasks == 0
    assert report.batch.executions == 1
    assert report.graceful_recovery["safe"] is True
    assert "# Runtime Stability" in report.to_markdown()


def test_reliability_diagnostics_and_production_readiness_are_transport_safe() -> None:
    repository, _, _, reliability = _components()
    configuration = RuntimeConfiguration(AppConfig())
    providers = ProviderManagement(LLMProviderRuntime())
    backends = BackendManagement(ImageBackendRuntime())
    operations = OperationalDiagnostics(
        configuration=configuration,
        providers=providers,
        backends=backends,
        dependencies={"repository": True},
    )
    diagnostics = ReliabilityDiagnostics(
        runtime=RuntimeDiagnostics(MetricsRegistry()),
        configuration=configuration,
        providers=providers,
        backends=backends,
        dependencies={"repository": True},
        plugins={"healthy": True},
        extensions={"healthy": True},
    ).report(repository={"healthy": True}, workflow={"scope": "one_page"})
    readiness = ProductionReadiness(operations=operations, reliability=reliability).report("reliable", 1)

    assert diagnostics.architecture["core_modified"] is False
    assert diagnostics.workflow["scope"] == "one_page"
    assert readiness.ready is True
    assert all(check.passed for check in readiness.checks)
    assert "# Reliability Diagnostics" in diagnostics.to_markdown()
    assert "# Production Readiness" in readiness.to_markdown()
    assert repository.load("reliable").id == "reliable"
