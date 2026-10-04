"""Measure planning-only operations summary composition with an in-memory repository."""

from __future__ import annotations

from time import perf_counter

from manga_director.domain.project import Page, Project
from manga_director.observability import MetricsRegistry
from manga_director.production import ProductionInsights, RepositoryMaintenance
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext


def run(iterations: int = 100) -> float:
    repository = InMemoryRepository()
    repository.save(Project(id="benchmark", title="Benchmark", pages=[Page(page_number=1)]))
    insights = ProductionInsights(metrics=MetricsRegistry(), maintenance=RepositoryMaintenance(repository))
    context = WorkflowContext(page={"id": "one"})
    started = perf_counter()
    for _ in range(iterations):
        assert not insights.operations_report(context, project_id="benchmark").scheduler_plan.automatic_execution
    return perf_counter() - started


if __name__ == "__main__":
    print(f"operations_summary: {run():.6f}s")
