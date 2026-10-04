"""Measure read-only workflow validation DTO construction."""

from __future__ import annotations

from time import perf_counter

from benchmarks.assurance_support import service
from manga_director.workflow import WorkflowContext


def run(iterations: int = 500) -> float:
    assurance = service()
    context = WorkflowContext()
    started = perf_counter()
    for _ in range(iterations):
        validation = assurance.workflow_reliability(context).validation
        if validation.next_command != "design":
            raise RuntimeError("Draft workflow validation must remain deterministic.")
    return perf_counter() - started


if __name__ == "__main__":
    print(f"workflow_validation: {run():.6f}s")
