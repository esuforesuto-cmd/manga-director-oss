"""Measure checklist-only enterprise AI readiness composition."""

from __future__ import annotations

from time import perf_counter

from benchmarks.director_reliability_support import service
from manga_director.workflow import WorkflowContext


def run(iterations: int = 500) -> float:
    reliability = service()
    context = WorkflowContext(page={"id": "benchmark-page"})
    started = perf_counter()
    for _ in range(iterations):
        if reliability.enterprise_ai_readiness(context).deployment_performed:
            raise RuntimeError("Readiness benchmark must never deploy.")
    return perf_counter() - started


if __name__ == "__main__":
    print(f"enterprise_ai_readiness: {run():.6f}s")
