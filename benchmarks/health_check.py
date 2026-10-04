"""Local production health DTO timing."""

from __future__ import annotations

from time import perf_counter

from benchmarks.startup_time import build_runtime


def run() -> float:
    """Measure health composition after a local startup."""

    runtime = build_runtime()
    runtime.start()
    started = perf_counter()
    assert runtime.health_report().live is True
    return perf_counter() - started
