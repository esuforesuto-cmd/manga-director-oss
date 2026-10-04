"""Measure repository-derived v3 Knowledge Foundation DTO construction."""

from time import perf_counter

from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.production import (
    DirectorFoundationService,
    DirectorPlanningService,
    KnowledgeService,
    PlanningService,
    ProviderOrchestrator,
    WorkflowPlanner,
)
from manga_director.repositories import InMemoryRepository


def run(iterations: int = 500) -> float:
    repository = InMemoryRepository()
    planning = PlanningService(
        planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime())
    )
    service = DirectorPlanningService(DirectorFoundationService(planning, KnowledgeService(repository)), planning)
    started = perf_counter()
    for _ in range(iterations):
        service.knowledge_foundation()
    return perf_counter() - started
