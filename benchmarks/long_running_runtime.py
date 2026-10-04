"""Bounded long-running runtime diagnostics timing."""

from __future__ import annotations

from time import perf_counter

from manga_director.observability import MetricsRegistry
from manga_director.production import LongRunningDiagnostics


def run() -> float:
    metrics = MetricsRegistry()
    metrics.increment("workflow.executions")
    diagnostics = LongRunningDiagnostics(metrics, limit=3)
    started = perf_counter()
    assert diagnostics.capture(active_tasks=0).tasks
    return perf_counter() - started
