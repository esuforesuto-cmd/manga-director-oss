"""Measure static development-workspace diagnostics without executing tools."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter

from manga_director.production import DevelopmentDiagnostics


def run(iterations: int = 100) -> float:
    diagnostics = DevelopmentDiagnostics(Path(__file__).resolve().parents[1])
    started = perf_counter()
    for _ in range(iterations):
        assert diagnostics.report().workspace.valid
    return perf_counter() - started


if __name__ == "__main__":
    print(f"development_workspace: {run():.6f}s")
