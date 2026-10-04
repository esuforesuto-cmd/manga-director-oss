"""Measure local documentation-link and release-asset validation only."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter

from manga_director.cli.config import AppConfig
from manga_director.production import QualityAutomation
from manga_director.repositories import InMemoryRepository


def run(iterations: int = 10) -> float:
    quality = QualityAutomation(
        repository=InMemoryRepository(), configuration=AppConfig(), root=Path(__file__).resolve().parents[1]
    )
    started = perf_counter()
    for _ in range(iterations):
        assert quality.documentation_validation().valid
    return perf_counter() - started


if __name__ == "__main__":
    print(f"documentation_validation: {run():.6f}s")
