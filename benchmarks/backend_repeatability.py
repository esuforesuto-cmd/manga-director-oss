"""Measure local image-backend lifecycle repeatability without generation."""

from __future__ import annotations

from benchmarks.backend_lifecycle import run as backend_lifecycle
from benchmarks.repeatability import RepeatabilityResult, measure


def run(runs: int = 5) -> RepeatabilityResult:
    return measure(backend_lifecycle, runs=runs)


if __name__ == "__main__":
    print(run().model_dump_json())
