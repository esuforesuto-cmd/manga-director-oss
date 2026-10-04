"""Measure in-process observability report composition without workflow execution."""

from __future__ import annotations

from time import perf_counter

from manga_director.domain.project import Page, Project
from manga_director.observability import MetricsRegistry
from manga_director.production import ProductionInsights, RepositoryMaintenance
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext


def run(iterations: int = 200) -> float:
    repository = InMemoryRepository()
    repository.save(Project(id="benchmark", title="Benchmark", pages=[Page(page_number=1)]))
    metrics = MetricsRegistry()
    metrics.increment("repository.operations")
    metrics.observe("repository.duration_seconds", 0.001)
    insights = ProductionInsights(metrics=metrics, maintenance=RepositoryMaintenance(repository))
    started = perf_counter()
    for _ in range(iterations):
        assert insights.observability_report(WorkflowContext(page={"id": "one"})).performance_snapshot
    return perf_counter() - started


if __name__ == "__main__":
    print(f"observability_metrics: {run():.6f}s")
