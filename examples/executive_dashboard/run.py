"""Create dashboard DTO data without a Web UI or automatic release."""

from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.cli.config import AppConfig
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

configuration = AppConfig()
runtime = LLMProviderRuntime()
planning = PlanningService(planner=WorkflowPlanner(), providers=ProviderOrchestrator(runtime))
workflow = WorkflowReliabilityAnalyzer(planning, WorkflowDependencyAnalyzer(planning))
providers = ProviderGovernance(
    runtime=runtime,
    optimizer=ProviderOptimizer(runtime, ProviderOrchestrator(runtime)),
    configuration=configuration,
)
repository = RepositoryMaintenance(InMemoryRepository())
service = AssuranceService(
    workflow=workflow,
    providers=providers,
    enterprise=EnterpriseReadiness(
        configuration=configuration,
        workflow=workflow,
        providers=providers,
        repository=repository,
    ),
    planning=planning,
    repository=repository,
)
print(service.dashboard(WorkflowContext(page={"id": "example-page"})).to_markdown())
