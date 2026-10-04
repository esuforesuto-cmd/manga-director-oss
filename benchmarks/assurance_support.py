"""Shared mock-only assurance composition for local benchmark modules."""

from __future__ import annotations

from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.cli.config import AppConfig
from manga_director.production import (
    AssuranceService,
    EnterpriseReadiness,
    PlanningService,
    ProviderGovernance,
    ProviderOptimizer,
    ProviderOrchestrator,
    RepositoryMaintenance,
    WorkflowDependencyAnalyzer,
    WorkflowPlanner,
    WorkflowReliabilityAnalyzer,
)
from manga_director.repositories import InMemoryRepository


def service() -> AssuranceService:
    """Build a local, non-executing assurance facade for benchmark measurement."""

    planning = PlanningService(
        planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime())
    )
    workflow = WorkflowReliabilityAnalyzer(planning, WorkflowDependencyAnalyzer(planning))
    providers = ProviderGovernance(
        runtime=LLMProviderRuntime(),
        optimizer=ProviderOptimizer(LLMProviderRuntime(), ProviderOrchestrator(LLMProviderRuntime())),
        configuration=AppConfig(),
    )
    repository = RepositoryMaintenance(InMemoryRepository())
    return AssuranceService(
        workflow=workflow,
        providers=providers,
        enterprise=EnterpriseReadiness(
            configuration=AppConfig(),
            workflow=workflow,
            providers=providers,
            repository=repository,
        ),
        planning=planning,
        repository=repository,
    )
