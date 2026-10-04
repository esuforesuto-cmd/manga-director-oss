"""Measure safe enterprise diagnostics DTO composition."""

from __future__ import annotations

from time import perf_counter

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


def run(iterations: int = 100) -> float:
    planning = PlanningService(
        planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime())
    )
    workflow = WorkflowDependencyAnalyzer(planning)
    providers = ProviderOptimizer(LLMProviderRuntime(), ProviderOrchestrator(LLMProviderRuntime()))
    diagnostics = EnterpriseDiagnostics(
        configuration=AppConfig(),
        workflow=workflow,
        providers=providers,
        backends=ImageBackendRuntime(),
        repository=RepositoryMaintenance(InMemoryRepository()),
    )
    started = perf_counter()
    for _ in range(iterations):
        diagnostics.report(WorkflowContext())
    return perf_counter() - started


if __name__ == "__main__":
    print(f"enterprise_diagnostics: {run():.6f}s")
