"""Create a compact optimization summary without automatic action."""

from manga_director.adapters.runtime import ImageBackendRuntime, LLMProviderRuntime
from manga_director.cli.config import AppConfig
from manga_director.production import (
    AnalyticsService,
    EnterpriseDiagnostics,
    OperationalAnalytics,
    PlanningService,
    ProviderOptimizer,
    ProviderOrchestrator,
    RepositoryMaintenance,
    WorkflowDependencyAnalyzer,
    WorkflowPlanner,
)
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

planning = PlanningService(
    planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime())
)
workflow = WorkflowDependencyAnalyzer(planning)
providers = ProviderOptimizer(LLMProviderRuntime(), ProviderOrchestrator(LLMProviderRuntime()))
repository = RepositoryMaintenance(InMemoryRepository())
service = AnalyticsService(
    workflow=workflow,
    providers=providers,
    enterprise=EnterpriseDiagnostics(
        configuration=AppConfig(),
        workflow=workflow,
        providers=providers,
        backends=ImageBackendRuntime(),
        repository=repository,
    ),
    operations=OperationalAnalytics(),
    repository=repository,
)
print(service.executive_report(WorkflowContext()).optimization.to_markdown())
