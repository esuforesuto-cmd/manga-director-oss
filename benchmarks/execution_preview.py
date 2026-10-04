"""Measure a non-executing one-page execution preview."""

from __future__ import annotations

from time import perf_counter

from manga_director.production import WorkflowPlanner
from manga_director.workflow import WorkflowContext


def run(iterations: int = 500) -> float:
    planner = WorkflowPlanner()
    context = WorkflowContext()
    started = perf_counter()
    for _ in range(iterations):
        planner.execution_preview(context)
    return perf_counter() - started


if __name__ == "__main__":
    print(f"execution_preview: {run():.6f}s")
