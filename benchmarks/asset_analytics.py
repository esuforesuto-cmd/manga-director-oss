"""Measure redacted Asset Analytics projection without Repository writes."""

from time import perf_counter

from manga_director.domain.project import Project
from manga_director.production import V32FoundationService, V32InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext


def run(iterations: int = 500) -> float:
    repository = InMemoryRepository()
    repository.save(Project(id="benchmark", title="Benchmark", metadata={"reference": {}}))
    service = V32InsightsService(V32FoundationService(repository), repository)
    context = WorkflowContext(page={"id": "benchmark-1"})
    started = perf_counter()
    for _ in range(iterations):
        service.asset_analytics_dashboard("benchmark", context).to_json()
    return perf_counter() - started
