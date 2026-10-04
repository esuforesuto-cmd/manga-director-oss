"""Measure redacted Asset DTO projection without asset storage activity."""

from time import perf_counter

from manga_director.domain.project import Project
from manga_director.production import V32FoundationService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext


def run(iterations: int = 500) -> float:
    repository = InMemoryRepository()
    repository.save(Project(id="benchmark", title="Benchmark", metadata={"reference": {}}))
    service = V32FoundationService(repository)
    context = WorkflowContext(page={"id": "benchmark-1"}, artifacts={"storyboard": {}})
    started = perf_counter()
    for _ in range(iterations):
        service.asset_intelligence_dashboard("benchmark", context).to_json()
    return perf_counter() - started
