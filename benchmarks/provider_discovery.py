"""Measure passive LLM provider discovery and metadata lookup."""

from __future__ import annotations

from time import perf_counter

from manga_director.adapters import LLMProviderRuntime


def run(iterations: int = 500) -> float:
    runtime = LLMProviderRuntime()
    started = perf_counter()
    for _ in range(iterations):
        runtime.discover()
        runtime.capability_report()
    return perf_counter() - started


if __name__ == "__main__":
    print(f"provider_discovery: {run():.6f}s")
