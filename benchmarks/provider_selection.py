"""Measure metadata-only Provider selection without invoking an LLM provider."""

from __future__ import annotations

from time import perf_counter

from manga_director.adapters import LLMProviderRuntime
from manga_director.production import ProviderOrchestrator


def run(iterations: int = 500) -> float:
    orchestrator = ProviderOrchestrator(LLMProviderRuntime())
    started = perf_counter()
    for _ in range(iterations):
        orchestrator.select(("text",))
    return perf_counter() - started


if __name__ == "__main__":
    print(f"provider_selection: {run():.6f}s")
