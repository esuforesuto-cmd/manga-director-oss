"""Measure repeatability of indexed SQLite query paths."""

from __future__ import annotations

from benchmarks.database_query import run as database_query
from benchmarks.repeatability import RepeatabilityResult, measure


def run(runs: int = 5) -> RepeatabilityResult:
    return measure(database_query, runs=runs)


if __name__ == "__main__":
    print(run().model_dump_json())
