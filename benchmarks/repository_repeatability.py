"""Measure repeatability of indexed local repository reads."""

from __future__ import annotations

from benchmarks.repeatability import RepeatabilityResult, measure
from benchmarks.repository_index import run as repository_index


def run(runs: int = 5) -> RepeatabilityResult:
    return measure(repository_index, runs=runs)


if __name__ == "__main__":
    print(run().model_dump_json())
