"""Measure v3.4 Release Governance DTO projection without release authority."""

from time import perf_counter

from manga_director.domain.project import Page, Project
from manga_director.production import V34FoundationService, V34GovernanceService, V34InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext


def run(iterations: int = 500) -> float:
    repository = InMemoryRepository()
    repository.save(Project(id="benchmark", title="Benchmark", pages=[Page(page_number=1)]))
    foundation = V34FoundationService(repository)
    service = V34GovernanceService(
        foundation, V34InsightsService(foundation, repository), repository
    )
    context = WorkflowContext(page={"id": "benchmark-1"})
    started = perf_counter()
    for _ in range(iterations):
        service.release_governance_dashboard("benchmark", context).to_json()
    return perf_counter() - started
