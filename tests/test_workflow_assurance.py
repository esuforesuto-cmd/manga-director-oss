from __future__ import annotations

from manga_director import __version__
from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.cli.config import AppConfig
from manga_director.domain.state_machine import PageState
from manga_director.production import (
    AssuranceService,
    EnterpriseReadiness,
    PlanningService,
    ProviderGovernance,
    ProviderOptimizer,
    ProviderOrchestrator,
    RepositoryMaintenance,
    WorkflowDependencyAnalyzer,
    WorkflowPlanner,
    WorkflowReliabilityAnalyzer,
)
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext


def _service() -> AssuranceService:
    planning = PlanningService(
        planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime())
    )
    workflow = WorkflowReliabilityAnalyzer(planning, WorkflowDependencyAnalyzer(planning))
    providers = ProviderGovernance(
        runtime=LLMProviderRuntime(),
        optimizer=ProviderOptimizer(LLMProviderRuntime(), ProviderOrchestrator(LLMProviderRuntime())),
        configuration=AppConfig(),
    )
    repository = RepositoryMaintenance(InMemoryRepository())
    return AssuranceService(
        workflow=workflow,
        providers=providers,
        enterprise=EnterpriseReadiness(
            configuration=AppConfig(),
            workflow=workflow,
            providers=providers,
            repository=repository,
        ),
        planning=planning,
        repository=repository,
    )


def test_workflow_integrity_and_validation_are_read_only_for_one_page() -> None:
    context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)

    report = _service().workflow_reliability(context)

    assert report.integrity.valid is True
    assert report.validation.next_command == "design"
    assert report.readiness.execution_performed is False
    assert report.analysis_only is True
    assert context.state is PageState.DRAFT


def test_workflow_reliability_detects_missing_storyboard_evidence() -> None:
    context = WorkflowContext(state=PageState.PROMPT_BUILT)

    report = _service().workflow_reliability(context)

    assert report.integrity.valid is False
    assert report.risk.level == "high"
    assert report.readiness.ready is False


def test_provider_governance_keeps_protocol_and_factory_boundaries_unchanged() -> None:
    report = _service().provider_governance()

    assert report.policy.valid is True
    assert report.capabilities.valid is True
    assert report.lifecycle.network_probes is False
    assert report.governance_only is True
    assert report.optimization.optimization_performed is False


def test_enterprise_readiness_is_a_checklist_without_deployment() -> None:
    report = _service().enterprise_readiness(WorkflowContext())

    assert report.deployment.name == "deployment"
    assert report.deployment.guidance.startswith("This report is a checklist")
    assert "# Enterprise Readiness Report" in report.to_markdown()


def test_workflow_health_diagnostics_expose_only_safe_dtos() -> None:
    report = _service().workflow_diagnostics(WorkflowContext())

    assert report.health.state == "Draft"
    assert report.execution["execution_performed"] is False
    assert report.architecture["workflow_engine_modified"] is False
    assert "# Workflow Diagnostics Report" in report.to_markdown()


def test_executive_dashboard_cannot_start_a_release_or_workflow() -> None:
    dashboard = _service().dashboard(WorkflowContext())

    assert dashboard.workflow.state == "Draft"
    assert dashboard.release.version == __version__
    assert dashboard.release.automatic_release is False
    assert dashboard.enterprise.total_areas == 6
