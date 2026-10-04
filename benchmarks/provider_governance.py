"""Measure local Provider governance without a model or remote health request."""

from __future__ import annotations

from time import perf_counter

from benchmarks.assurance_support import service


def run(iterations: int = 200) -> float:
    assurance = service()
    started = perf_counter()
    for _ in range(iterations):
        assurance.provider_governance()
    return perf_counter() - started


if __name__ == "__main__":
    print(f"provider_governance: {run():.6f}s")
