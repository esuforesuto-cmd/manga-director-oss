"""Measure non-executing one-page orchestration DTO construction."""

from benchmarks.director_planner import run as _run


def run(iterations: int = 500) -> float:
    return _run(iterations)
