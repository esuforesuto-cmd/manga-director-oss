"""Measure local provider health-summary repeatability without network calls."""

from __future__ import annotations

from benchmarks.provider_lifecycle import run as provider_lifecycle
from benchmarks.repeatability import RepeatabilityResult, measure


def run(runs: int = 5) -> RepeatabilityResult:
    """Measure enough lightweight samples to avoid OS-timeslice noise."""

    return measure(provider_lifecycle, runs=runs, inner_runs=1_000)


if __name__ == "__main__":
    print(run().model_dump_json())
