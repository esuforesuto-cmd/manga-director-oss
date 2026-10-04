"""Shared provider-free fixture for v2.7 Director reliability benchmarks."""

from __future__ import annotations

from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.domain.project import Page, Project
from manga_director.production import (
    DirectorFoundationService,
    DirectorReliabilityService,
    KnowledgeIntelligenceService,
    KnowledgeService,
    PlanningService,
    ProviderOrchestrator,
    WorkflowPlanner,
)
from manga_director.repositories import InMemoryRepository


def service() -> DirectorReliabilityService:
    repository = InMemoryRepository()
    repository.save(Project(id="benchmark", title="Benchmark", pages=[Page(page_number=1)]))
    foundation = DirectorFoundationService(
        PlanningService(
            planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime())
        ),
        KnowledgeService(repository),
    )
    return DirectorReliabilityService(foundation, KnowledgeIntelligenceService(foundation))
