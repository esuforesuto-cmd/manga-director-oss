from __future__ import annotations

from manga_director.adapters.runtime import ImageBackendRuntime, LLMProviderRuntime
from manga_director.cli.config import AppConfig
from manga_director.domain.state_machine import PageState
from manga_director.production import (
    AnalyticsService,
    EnterpriseDiagnostics,
    OperationalAnalytics,
    PlanningService,
    ProviderOptimizer,
    ProviderOrchestrator,
    RepositoryMaintenance,
    WorkflowDependencyAnalyzer,
    WorkflowPlanner,
)
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext


def _service() -> AnalyticsService:
    planning = PlanningService(
        planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime())
    )
    workflow = WorkflowDependencyAnalyzer(planning)
    providers = ProviderOptimizer(LLMProviderRuntime(), ProviderOrchestrator(LLMProviderRuntime()))
    repository = RepositoryMaintenance(InMemoryRepository())
    return AnalyticsService(
        workflow=workflow,
        providers=providers,
        enterprise=EnterpriseDiagnostics(
            configuration=AppConfig(),
            workflow=workflow,
            providers=providers,
            backends=ImageBackendRuntime(),
            repository=repository,
        ),
        operations=OperationalAnalytics(),
        repository=repository,
    )


def test_workflow_analysis_reports_a_linear_critical_path_without_execution() -> None:
    context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)

    report = _service().workflow_analysis(context)

    assert report.dependency_graph.steps[0].command == "design"
    assert report.critical_path.commands[0] == "design"
    assert report.critical_path.execution_enabled is False
    assert report.analysis_only is True
    assert context.state is PageState.DRAFT


def test_workflow_analysis_compares_contexts_without_merging_or_mutating_them() -> None:
    planning = PlanningService(
        planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime())
    )
    analyzer = WorkflowDependencyAnalyzer(planning)
    current = WorkflowContext(state=PageState.REVIEWED)
    reference = WorkflowContext(state=PageState.DRAFT)

    report = analyzer.analyze(current, reference)

    assert report.comparison is not None
    assert report.comparison.progress_delta_steps == 2
    assert current.state is PageState.REVIEWED
    assert reference.state is PageState.DRAFT


def test_provider_comparison_uses_metadata_and_local_health_only() -> None:
    report = _service().provider_comparison(("text", "deterministic"))

    assert report.selection.selected_provider == "mock"
    assert report.optimization_performed is False
    assert all(item.cost_known is False for item in report.comparisons)
    assert any(item.reliability == "local_healthy" for item in report.comparisons)
    assert report.explanation.fallback_execution_enabled is False


def test_enterprise_diagnostics_is_a_presentation_independent_safe_dto() -> None:
    report = _service().enterprise_diagnostics(WorkflowContext())

    assert report.system.one_page_workflow is True
    assert report.system.network_probes is False
    assert report.configuration.name == "configuration"
    assert report.repository.name == "repository"
    assert "# Enterprise Diagnostics Report" in report.to_markdown()


def test_operational_analytics_renders_supplied_trends_without_starting_collection() -> None:
    service = _service()
    workflow = service.workflow_analysis(WorkflowContext())
    providers = service.provider_comparison()
    repository = RepositoryMaintenance(InMemoryRepository())

    report = OperationalAnalytics().summary(
        workflow,
        providers,
        repository,
        history={"workflow": (10.0, 20.0), "performance": (2.0, 1.0)},
    )

    assert report.workflow.direction == "up"
    assert report.performance.direction == "down"
    assert report.analysis_only is True


def test_executive_report_is_non_executing_and_serializable() -> None:
    report = _service().executive_report(WorkflowContext())

    assert report.optimization.automatic_action_taken is False
    assert report.workflow.critical_path.execution_enabled is False
    assert '"selected_provider"' in report.to_json()
    assert "# Executive Analytics Report" in report.to_markdown()
