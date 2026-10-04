"""Measure JSON/Markdown planning-report rendering without workflow execution."""

from __future__ import annotations

from time import perf_counter

from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.production import PlanningService, ProviderOrchestrator, WorkflowPlanner
from manga_director.workflow import WorkflowContext


def run(iterations: int = 100) -> float:
    service = PlanningService(
        planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime())
    )
    context = WorkflowContext()
    started = perf_counter()
    for _ in range(iterations):
        service.summary(context).to_markdown()
    return perf_counter() - started


if __name__ == "__main__":
    print(f"planning_report: {run():.6f}s")
