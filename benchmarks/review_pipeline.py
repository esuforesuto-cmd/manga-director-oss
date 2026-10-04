"""Measure v3 Review Pipeline DTO construction without quality approval."""

from time import perf_counter

from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.production import (
    CollaborationPlanningService,
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
    planning = PlanningService(planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime()))
    platform = DirectorPlanningService(DirectorFoundationService(planning, KnowledgeService(InMemoryRepository())), planning)
    service = CollaborationPlanningService(platform)
    started = perf_counter()
    for _ in range(iterations):
        service.review_pipeline(WorkflowContext())
    return perf_counter() - started
