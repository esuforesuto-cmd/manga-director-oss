"""Measure local adapter-construction health checks without network probes."""

from __future__ import annotations

from time import perf_counter

from manga_director.adapters import LLMProviderRuntime


def run(iterations: int = 100) -> float:
    runtime = LLMProviderRuntime()
    started = perf_counter()
    for _ in range(iterations):
        runtime.health()
    return perf_counter() - started


if __name__ == "__main__":
    print(f"provider_health: {run():.6f}s")
