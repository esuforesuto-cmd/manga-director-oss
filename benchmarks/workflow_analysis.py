"""Measure read-only one-page workflow analysis DTO composition."""

from __future__ import annotations

from time import perf_counter

from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.production import (
    PlanningService,
    ProviderOrchestrator,
    WorkflowDependencyAnalyzer,
    WorkflowPlanner,
)
from manga_director.workflow import WorkflowContext


def run(iterations: int = 500) -> float:
    analyzer = WorkflowDependencyAnalyzer(
        PlanningService(planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime()))
    )
    started = perf_counter()
    for _ in range(iterations):
        analyzer.analyze(WorkflowContext())
    return perf_counter() - started


if __name__ == "__main__":
    print(f"workflow_analysis: {run():.6f}s")
