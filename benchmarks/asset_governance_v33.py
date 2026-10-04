"""Measure v3.3 Asset Governance DTO composition without retention or writes."""

from time import perf_counter

from manga_director.domain.project import Page, Project
from manga_director.production import V33FoundationService, V33GovernanceService, V33InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext


def run(iterations: int = 500) -> float:
    repository = InMemoryRepository()
    repository.save(Project(id="benchmark", title="Benchmark", pages=[Page(page_number=1)]))
    foundation = V33FoundationService(repository)
    service = V33GovernanceService(foundation, V33InsightsService(foundation, repository), repository)
    context = WorkflowContext(page={"id": "benchmark-1"})
    started = perf_counter()
    for _ in range(iterations):
        service.asset_governance_dashboard("benchmark", context).to_json()
    return perf_counter() - started
