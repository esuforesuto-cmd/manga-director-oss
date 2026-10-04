"""Measure bounded operational trend generation without a collector."""

from __future__ import annotations

from time import perf_counter

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


def run(iterations: int = 500) -> float:
    planning = PlanningService(
        planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime())
    )
    workflow = WorkflowDependencyAnalyzer(planning).analyze(WorkflowContext())
    providers = ProviderOptimizer(LLMProviderRuntime(), ProviderOrchestrator(LLMProviderRuntime())).compare()
    repository = RepositoryMaintenance(InMemoryRepository())
    analytics = OperationalAnalytics()
    started = perf_counter()
    for _ in range(iterations):
        analytics.summary(workflow, providers, repository)
    return perf_counter() - started


if __name__ == "__main__":
    print(f"operational_analytics: {run():.6f}s")
