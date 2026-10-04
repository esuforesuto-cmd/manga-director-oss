"""Measure v3.2 Studio DTO projection without workflow dispatch."""

from time import perf_counter

from manga_director.domain.project import Page, Project
from manga_director.production import V32FoundationService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext


def run(iterations: int = 500) -> float:
    repository = InMemoryRepository()
    repository.save(Project(id="benchmark", title="Benchmark", pages=[Page(page_number=1)]))
    service = V32FoundationService(repository)
    context = WorkflowContext(page={"id": "benchmark-1"})
    started = perf_counter()
    for _ in range(iterations):
        service.creative_studio_dashboard("benchmark", context).to_json()
    return perf_counter() - started
