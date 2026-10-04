"""Measure Release Readiness evidence without publication or authorization."""

from time import perf_counter

from manga_director.production import V32AssuranceService, V32FoundationService, V32InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext


def run(iterations: int = 500) -> float:
    repository = InMemoryRepository()
    foundation = V32FoundationService(repository)
    service = V32AssuranceService(
        foundation, V32InsightsService(foundation, repository), repository
    )
    context = WorkflowContext(page={"id": "benchmark-1"})
    started = perf_counter()
    for _ in range(iterations):
        service.release_readiness_dashboard(context).to_json()
    return perf_counter() - started
