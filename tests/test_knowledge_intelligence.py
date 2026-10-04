from __future__ import annotations

from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.domain.project import Page, Project
from manga_director.production import (
    DirectorFoundationService,
    KnowledgeIntelligenceService,
    KnowledgeService,
    PlanningService,
    ProviderOrchestrator,
    WorkflowPlanner,
)
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext


def _service() -> tuple[KnowledgeIntelligenceService, InMemoryRepository]:
    repository = InMemoryRepository()
    repository.save(Project(id="alpha", title="Alpha", pages=[Page(page_number=1)], metadata={"world": "city"}))
    foundation = DirectorFoundationService(
        PlanningService(planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime())),
        KnowledgeService(repository),
    )
    return KnowledgeIntelligenceService(foundation), repository


def test_knowledge_graph_similarity_and_enterprise_report_are_repository_read_only() -> None:
    service, repository = _service()
    report = service.knowledge_intelligence()

    assert report.coverage.coverage == "available"
    assert report.relationships.analysis_only is True
    assert service.similarity("alpha")[0].project_id == "alpha"
    assert service.enterprise_knowledge().audit_only is True
    assert repository.load("alpha").title == "Alpha"


def test_director_analysis_optimization_and_dashboard_never_execute() -> None:
    service, _ = _service()
    context = WorkflowContext(page={"id": "page-1"})

    analysis = service.director_analysis(context)
    optimization = service.workflow_optimization(context)
    dashboard = service.dashboard(context)

    assert analysis.alternatives[0].command == "design"
    assert analysis.risk.execution_performed is False
    assert optimization.workflow_modified is False
    assert dashboard.automatic_action_taken is False
    assert context.state.value == "Draft"
