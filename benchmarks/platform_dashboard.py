"""Measure v3.5 Executive Analytics dashboard projection without external action."""

from time import perf_counter

from manga_director.domain.project import Page, Project
from manga_director.production import V35FoundationService, V35InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext


def run(iterations: int = 500) -> float:
    repository = InMemoryRepository()
    repository.save(Project(id="benchmark", title="Benchmark", pages=[Page(page_number=1)]))
    foundation = V35FoundationService(repository)
    service = V35InsightsService(foundation, repository)
    context = WorkflowContext(page={"id": "benchmark-1"})
    started = perf_counter()
    for _ in range(iterations):
        service.executive_analytics_dashboard("benchmark", context).to_json()
    return perf_counter() - started
