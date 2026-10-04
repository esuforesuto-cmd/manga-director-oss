"""Measure enterprise readiness checklist composition without deployment."""

from __future__ import annotations

from time import perf_counter

from benchmarks.assurance_support import service
from manga_director.workflow import WorkflowContext


def run(iterations: int = 200) -> float:
    assurance = service()
    context = WorkflowContext()
    started = perf_counter()
    for _ in range(iterations):
        assurance.enterprise_readiness(context)
    return perf_counter() - started


if __name__ == "__main__":
    print(f"enterprise_readiness: {run():.6f}s")
