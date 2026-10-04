"""Measure v3.5 Platform Health projection without monitoring actions."""

from time import perf_counter

from manga_director.domain.project import Page, Project
from manga_director.production import V35FoundationService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext


def run(iterations: int = 500) -> float:
    repository = InMemoryRepository()
    repository.save(Project(id="benchmark", title="Benchmark", pages=[Page(page_number=1)]))
    service = V35FoundationService(repository)
    context = WorkflowContext(page={"id": "benchmark-1"})
    started = perf_counter()
    for _ in range(iterations):
        service.platform_analytics("benchmark", context).health.model_dump(mode="json")
    return perf_counter() - started
