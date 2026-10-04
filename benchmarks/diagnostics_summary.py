"""Enterprise diagnostics composition smoke benchmark."""

from __future__ import annotations

from time import perf_counter

from manga_director.cli.config import AppConfig
from manga_director.observability import EnterpriseDiagnostics


def run(iterations: int = 100) -> float:
    diagnostics = EnterpriseDiagnostics(config=AppConfig())
    start = perf_counter()
    for _ in range(iterations):
        diagnostics.report()
    return perf_counter() - start


if __name__ == "__main__":
    print(f"diagnostics_summary: {run():.6f}s")
