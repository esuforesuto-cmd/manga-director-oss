"""Measure read-only AI Director planning DTO construction."""

from time import perf_counter

from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.production import (
    DirectorFoundationService,
    KnowledgeService,
    PlanningService,
    ProviderOrchestrator,
    WorkflowPlanner,
)
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext


def run(iterations: int = 500) -> float:
    service = DirectorFoundationService(
        PlanningService(
            planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime())
        ),
        KnowledgeService(InMemoryRepository()),
    )
    started = perf_counter()
    for _ in range(iterations):
        service.director_plan(WorkflowContext())
    return perf_counter() - started
