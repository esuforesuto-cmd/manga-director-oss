"""Measure read-only one-page workflow planning DTO construction."""

from __future__ import annotations

from time import perf_counter

from manga_director.domain.state_machine import PageState
from manga_director.production import WorkflowPlanner
from manga_director.workflow import WorkflowContext


def run(iterations: int = 500) -> float:
    planner = WorkflowPlanner()
    context = WorkflowContext(state=PageState.PROMPT_BUILT)
    started = perf_counter()
    for _ in range(iterations):
        planner.plan(context)
    return perf_counter() - started


if __name__ == "__main__":
    print(f"workflow_planner: {run():.6f}s")
