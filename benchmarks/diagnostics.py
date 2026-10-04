"""Measure passive runtime diagnostic report composition."""

from __future__ import annotations

from time import perf_counter

from manga_director.observability import MetricsRegistry, RuntimeDiagnostics


def run(iterations: int = 500) -> float:
    metrics = MetricsRegistry()
    metrics.observe("diagnostics.duration_seconds", 0.001)
    diagnostics = RuntimeDiagnostics(metrics)
    started = perf_counter()
    for _ in range(iterations):
        diagnostics.report(
            plugins={"active": []},
            extensions={"manifest_cache_entries": 1},
            configuration={"cache_entries": 1},
            repositories={"operations": 1},
            events={"published": 1},
        )
    return perf_counter() - started


if __name__ == "__main__":
    print(f"diagnostics: {run():.6f}s")
