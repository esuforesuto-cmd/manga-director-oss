"""Measure configuration-governance repeatability with safe local defaults."""

from __future__ import annotations

from benchmarks.configuration_validation import run as configuration_validation
from benchmarks.repeatability import RepeatabilityResult, measure


def run(runs: int = 5) -> RepeatabilityResult:
    return measure(configuration_validation, runs=runs)


if __name__ == "__main__":
    print(run().model_dump_json())
