"""Non-executing recovery simulation timing."""

from __future__ import annotations

from time import perf_counter

from benchmarks.workflow_resume import build_reliability


def run() -> float:
    reliability = build_reliability()
    started = perf_counter()
    assert reliability.simulate_recovery("resume", 1).safe_to_resume is True
    return perf_counter() - started
