"""Measure v3.2 analytics DTO composition without runtime automation."""

from time import perf_counter

from manga_director.production import V32FoundationService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext


def run(iterations: int = 500) -> float:
    service = V32FoundationService(InMemoryRepository())
    context = WorkflowContext(page={"id": "benchmark-1"})
    started = perf_counter()
    for _ in range(iterations):
        service.production_analytics_dashboard(context).to_json()
    return perf_counter() - started
