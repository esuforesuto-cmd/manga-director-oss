"""Local image-backend lifecycle smoke benchmark."""

from __future__ import annotations

from time import perf_counter

from manga_director.adapters import ImageBackendRuntime


def run() -> float:
    start = perf_counter()
    runtime = ImageBackendRuntime()
    runtime.initialize()
    runtime.health_snapshot()
    runtime.shutdown()
    return perf_counter() - start


if __name__ == "__main__":
    print(f"backend_lifecycle: {run():.6f}s")
