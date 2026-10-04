"""Optional tracemalloc-backed runtime memory snapshot timing."""

from __future__ import annotations

import tracemalloc
from time import perf_counter

from manga_director.observability import MetricsRegistry
from manga_director.production import LongRunningDiagnostics


def run() -> float:
    tracemalloc.start()
    try:
        diagnostics = LongRunningDiagnostics(MetricsRegistry())
        started = perf_counter()
        assert diagnostics.capture().memory.tracing_enabled is True
        return perf_counter() - started
    finally:
        tracemalloc.stop()
