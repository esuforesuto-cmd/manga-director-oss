"""Local provider lifecycle smoke benchmark."""

from __future__ import annotations

from time import perf_counter

from manga_director.adapters import LLMProviderRuntime


def run() -> float:
    start = perf_counter()
    runtime = LLMProviderRuntime()
    runtime.initialize()
    runtime.health_snapshot()
    runtime.shutdown()
    return perf_counter() - start


if __name__ == "__main__":
    print(f"provider_lifecycle: {run():.6f}s")
