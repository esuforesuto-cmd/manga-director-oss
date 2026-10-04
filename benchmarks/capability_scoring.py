"""Measure metadata-only Provider capability scoring."""

from __future__ import annotations

from time import perf_counter

from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.production import ProviderOrchestrator


def run(iterations: int = 500) -> float:
    orchestrator = ProviderOrchestrator(LLMProviderRuntime())
    started = perf_counter()
    for _ in range(iterations):
        orchestrator.select(("text", "deterministic"))
    return perf_counter() - started


if __name__ == "__main__":
    print(f"capability_scoring: {run():.6f}s")
