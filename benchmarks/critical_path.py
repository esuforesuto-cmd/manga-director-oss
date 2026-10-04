"""Measure critical-path extraction without workflow execution."""

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
    context = WorkflowContext()
    started = perf_counter()
    for _ in range(iterations):
        path = analyzer.analyze(context).critical_path
        if path.execution_enabled:
            raise RuntimeError("Critical-path analysis must remain non-executing.")
    return perf_counter() - started


if __name__ == "__main__":
    print(f"critical_path: {run():.6f}s")
