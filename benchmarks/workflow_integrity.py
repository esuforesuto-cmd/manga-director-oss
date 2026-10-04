"""Measure one-page workflow integrity analysis without workflow execution."""

from __future__ import annotations

from time import perf_counter

from benchmarks.assurance_support import service
from manga_director.workflow import WorkflowContext


def run(iterations: int = 500) -> float:
    assurance = service()
    context = WorkflowContext()
    started = perf_counter()
    for _ in range(iterations):
        integrity = assurance.workflow_reliability(context).integrity
        if not integrity.valid:
            raise RuntimeError("Draft workflow integrity must remain valid.")
    return perf_counter() - started


if __name__ == "__main__":
    print(f"workflow_integrity: {run():.6f}s")
