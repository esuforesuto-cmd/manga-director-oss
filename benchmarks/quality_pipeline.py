"""Measure a provider-free quality pipeline over a one-page workflow context."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter

from manga_director.cli.config import AppConfig
from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.production import QualityAutomation
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext


def run(iterations: int = 10) -> float:
    root = Path(__file__).resolve().parents[1]
    repository = InMemoryRepository()
    repository.save(Project(id="benchmark", title="Benchmark", pages=[Page(page_number=1)]))
    quality = QualityAutomation(repository=repository, configuration=AppConfig(), root=root)
    context = WorkflowContext(
        page={"id": "one"},
        state=PageState.GENERATED,
        artifacts={PageState.STORYBOARDED.value: {"panels": []}},
    )
    started = perf_counter()
    for _ in range(iterations):
        assert quality.pipeline(context, "benchmark").dashboard.healthy
    return perf_counter() - started


if __name__ == "__main__":
    print(f"quality_pipeline: {run():.6f}s")
