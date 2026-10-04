"""Measure public decision-trace and execution-readiness validation."""

from __future__ import annotations

from time import perf_counter

from benchmarks.director_reliability_support import service
from manga_director.workflow import WorkflowContext


def run(iterations: int = 500) -> float:
    reliability = service()
    context = WorkflowContext(page={"id": "benchmark-page"})
    started = perf_counter()
    for _ in range(iterations):
        if not reliability.director_reliability(context).decision_trace.valid:
            raise RuntimeError("Decision trace validation must remain deterministic.")
    return perf_counter() - started


if __name__ == "__main__":
    print(f"planning_validation: {run():.6f}s")
