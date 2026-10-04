"""Measure v3 Director Platform DTO construction without workflow execution."""

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
from manga_director.workflow import WorkflowContext


def run(iterations: int = 500) -> float:
    planning = PlanningService(
        planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime())
    )
    service = DirectorPlanningService(
        DirectorFoundationService(planning, KnowledgeService(InMemoryRepository())), planning
    )
    started = perf_counter()
    for _ in range(iterations):
        service.director_platform(WorkflowContext(page={"id": "benchmark-page"}))
    return perf_counter() - started
