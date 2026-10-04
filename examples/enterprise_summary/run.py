"""Render a local enterprise audit without delivery or workflow execution."""

from manga_director.adapters.runtime import ImageBackendRuntime, LLMProviderRuntime
from manga_director.cli.config import AppConfig
from manga_director.production import (
    EnterpriseDiagnostics,
    PlanningService,
    ProviderOptimizer,
    ProviderOrchestrator,
    RepositoryMaintenance,
    WorkflowDependencyAnalyzer,
    WorkflowPlanner,
)
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

planning = PlanningService(
    planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime())
)
workflow = WorkflowDependencyAnalyzer(planning)
providers = ProviderOptimizer(LLMProviderRuntime(), ProviderOrchestrator(LLMProviderRuntime()))
report = EnterpriseDiagnostics(
    configuration=AppConfig(),
    workflow=workflow,
    providers=providers,
    backends=ImageBackendRuntime(),
    repository=RepositoryMaintenance(InMemoryRepository()),
).report(WorkflowContext(page={"id": "example-page"}))
print(report.to_markdown())
