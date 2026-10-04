"""Measure workflow-health diagnostics without an Agent or Provider request."""

from __future__ import annotations

from time import perf_counter

from benchmarks.assurance_support import service
from manga_director.workflow import WorkflowContext


def run(iterations: int = 500) -> float:
    assurance = service()
    context = WorkflowContext()
    started = perf_counter()
    for _ in range(iterations):
        health = assurance.workflow_diagnostics(context).health
        if health.state != "Draft":
            raise RuntimeError("Workflow health benchmark must remain one-page and deterministic.")
    return perf_counter() - started


if __name__ == "__main__":
    print(f"workflow_health: {run():.6f}s")
