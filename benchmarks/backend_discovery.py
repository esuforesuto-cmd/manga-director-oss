"""Measure passive image-backend discovery and workflow metadata lookup."""

from __future__ import annotations

from time import perf_counter

from manga_director.adapters import ImageBackendRuntime


def run(iterations: int = 500) -> float:
    runtime = ImageBackendRuntime()
    started = perf_counter()
    for _ in range(iterations):
        runtime.discover()
        runtime.capability_report()
        runtime.preset_report()
    return perf_counter() - started


if __name__ == "__main__":
    print(f"backend_discovery: {run():.6f}s")
