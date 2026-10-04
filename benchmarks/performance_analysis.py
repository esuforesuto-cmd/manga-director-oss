"""Measure baseline comparison and trend analysis over local metric snapshots."""

from __future__ import annotations

from time import perf_counter

from manga_director.domain.project import Page, Project
from manga_director.observability import MetricsRegistry
from manga_director.production import PerformanceBaseline, ProductionInsights, RepositoryMaintenance
from manga_director.repositories import InMemoryRepository


def run(iterations: int = 500) -> float:
    repository = InMemoryRepository()
    repository.save(Project(id="benchmark", title="Benchmark", pages=[Page(page_number=1)]))
    metrics = MetricsRegistry()
    metrics.observe("repository.load.duration_seconds", 0.01)
    insights = ProductionInsights(metrics=metrics, maintenance=RepositoryMaintenance(repository))
    baseline = PerformanceBaseline(name="local", averages_seconds={"repository.load.duration_seconds": 0.01})
    started = perf_counter()
    for _ in range(iterations):
        assert not insights.performance_report(baseline=baseline).regression.regressed
    return perf_counter() - started


if __name__ == "__main__":
    print(f"performance_analysis: {run():.6f}s")
