"""Measure safe AI workflow diagnostics DTO construction."""

from __future__ import annotations

from time import perf_counter

from benchmarks.director_reliability_support import service
from manga_director.workflow import WorkflowContext


def run(iterations: int = 500) -> float:
    reliability = service()
    context = WorkflowContext(page={"id": "benchmark-page"})
    started = perf_counter()
    for _ in range(iterations):
        if not reliability.diagnostics(context).diagnostics_only:
            raise RuntimeError("AI workflow diagnostics must remain read-only.")
    return perf_counter() - started


if __name__ == "__main__":
    print(f"ai_workflow_diagnostics: {run():.6f}s")
