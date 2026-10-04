"""Measure v3.3 Project Health projection without Project mutation."""

from time import perf_counter

from manga_director.domain.project import Chapter, Page, Project
from manga_director.production import V33FoundationService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext


def run(iterations: int = 500) -> float:
    repository = InMemoryRepository()
    repository.save(
        Project(
            id="benchmark",
            title="Benchmark",
            chapters=[Chapter(id="one", title="One", page_numbers=[1])],
            pages=[Page(page_number=1)],
        )
    )
    service = V33FoundationService(repository)
    context = WorkflowContext(page={"id": "benchmark-1"})
    started = perf_counter()
    for _ in range(iterations):
        service.project_intelligence_dashboard("benchmark", context).report.health.to_json()
    return perf_counter() - started
