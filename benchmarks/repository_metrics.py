"""Measure category extraction for repository metrics without touching persistence."""

from __future__ import annotations

from time import perf_counter

from manga_director.domain.project import Page, Project
from manga_director.observability import MetricsRegistry
from manga_director.production import ProductionInsights, RepositoryMaintenance
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext


def run(iterations: int = 500) -> float:
    repository = InMemoryRepository()
    repository.save(Project(id="benchmark", title="Benchmark", pages=[Page(page_number=1)]))
    metrics = MetricsRegistry()
    metrics.increment("repository.operations.load")
    metrics.observe("repository.duration_seconds.load", 0.001)
    insights = ProductionInsights(metrics=metrics, maintenance=RepositoryMaintenance(repository))
    started = perf_counter()
    for _ in range(iterations):
        assert insights.observability_report(WorkflowContext()).repository_metrics["counters"]
    return perf_counter() - started


if __name__ == "__main__":
    print(f"repository_metrics: {run():.6f}s")
