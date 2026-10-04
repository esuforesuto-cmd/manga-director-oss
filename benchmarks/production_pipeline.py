"""Measure v3.3 Production Pipeline DTO projection without workflow dispatch."""

from time import perf_counter

from manga_director.domain.project import Page, Project
from manga_director.production import V33FoundationService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext


def run(iterations: int = 500) -> float:
    repository = InMemoryRepository()
    repository.save(Project(id="benchmark", title="Benchmark", pages=[Page(page_number=1)]))
    service = V33FoundationService(repository)
    context = WorkflowContext(page={"id": "benchmark-1"})
    started = perf_counter()
    for _ in range(iterations):
        service.production_pipeline_dashboard("benchmark", context).to_json()
    return perf_counter() - started
