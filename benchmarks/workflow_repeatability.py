"""Measure repeatability of page-scoped Workflow transitions."""

from __future__ import annotations

from benchmarks.repeatability import RepeatabilityResult, measure
from benchmarks.workflow_scale import run as workflow_scale


def run(runs: int = 5) -> RepeatabilityResult:
    return measure(lambda: workflow_scale(page_count=40), runs=runs)


if __name__ == "__main__":
    print(run().model_dump_json())
