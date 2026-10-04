"""Measure metadata-only Provider comparison with no model request."""

from __future__ import annotations

from time import perf_counter

from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.production import ProviderOptimizer, ProviderOrchestrator


def run(iterations: int = 500) -> float:
    optimizer = ProviderOptimizer(LLMProviderRuntime(), ProviderOrchestrator(LLMProviderRuntime()))
    started = perf_counter()
    for _ in range(iterations):
        optimizer.compare(("text",))
    return perf_counter() - started


if __name__ == "__main__":
    print(f"provider_comparison: {run():.6f}s")
