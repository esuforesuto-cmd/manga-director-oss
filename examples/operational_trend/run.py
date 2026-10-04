"""Render bounded supplied operational trends; no collection service is started."""

from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.production import (
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

planning = PlanningService(
    planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime())
)
workflow = WorkflowDependencyAnalyzer(planning)
providers = ProviderOptimizer(LLMProviderRuntime(), ProviderOrchestrator(LLMProviderRuntime()))
report = OperationalAnalytics().summary(
    workflow.analyze(WorkflowContext()),
    providers.compare(),
    RepositoryMaintenance(InMemoryRepository()),
    history={"workflow": (20.0, 40.0), "performance": (3.0, 2.0)},
)
print(report.to_markdown())
