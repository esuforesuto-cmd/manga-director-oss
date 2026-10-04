"""Bounded in-process production metric report timing."""

from __future__ import annotations

from time import perf_counter

from manga_director.production import ProductionMetrics


def run() -> float:
    """Measure category aggregation without an external exporter."""

    metrics = ProductionMetrics()
    for category in ("workflow", "repository", "provider", "backend", "automation", "notification"):
        metrics.registry.increment(f"{category}.executions")
        metrics.registry.observe(f"{category}.duration_seconds", 0.001)
    started = perf_counter()
    assert metrics.report().workflow["counters"]["workflow.executions"] == 1
    return perf_counter() - started
