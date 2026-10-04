"""Generate a readiness checklist without deploying or resuming a workflow."""

from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.cli.config import AppConfig
from manga_director.production import (
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
report = EnterpriseReadiness(
    configuration=configuration,
    workflow=workflow,
    providers=providers,
    repository=RepositoryMaintenance(InMemoryRepository()),
).report(WorkflowContext(page={"id": "example-page"}))
print(report.to_markdown())
