from __future__ import annotations

from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.domain.project import Chapter, Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.production import (
    DirectorFoundationService,
    KnowledgeService,
    PlanningService,
    ProviderOrchestrator,
    WorkflowPlanner,
)
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext


def _service(repository: InMemoryRepository) -> DirectorFoundationService:
    planning = PlanningService(
        planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime())
    )
    return DirectorFoundationService(planning, KnowledgeService(repository))


def test_director_planner_uses_one_legal_step_and_keeps_context_unchanged() -> None:
    repository = InMemoryRepository()
    context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)

    report = _service(repository).director_plan(context)

    assert report.strategy.command == "design"
    assert report.readiness.execution_performed is False
    assert report.trace.side_effects == "none"
    assert context.state is PageState.DRAFT


def test_knowledge_search_and_summary_use_only_the_repository_port() -> None:
    repository = InMemoryRepository()
    repository.save(
        Project(
            id="pilot",
            title="Pilot Chapter",
            chapters=[Chapter(id="one", title="One", page_numbers=[1])],
            pages=[Page(page_number=1)],
            metadata={"world": "city", "secret": "not exposed"},
        )
    )
    service = _service(repository)

    search = service.knowledge_search("pilot")
    report = service.knowledge_report()

    assert search.matches[0].project_id == "pilot"
    assert report.summary.project_count == 1
    assert report.health.healthy is True
    assert repository.load("pilot").metadata["secret"] == "not exposed"


def test_knowledge_repository_projection_is_redacted_and_read_only() -> None:
    repository = InMemoryRepository()
    repository.save(
        Project(
            id="pilot",
            title="Pilot Chapter",
            pages=[Page(page_number=1)],
            metadata={"world": "city", "secret": "not exposed"},
        )
    )

    snapshot = KnowledgeService(repository).snapshot()

    assert snapshot.mutated_repository is False
    assert snapshot.entries[0].metadata_keys == ("secret", "world")
    assert repository.load("pilot").metadata == {"world": "city", "secret": "not exposed"}


def test_knowledge_search_normalizes_queries_and_returns_a_stable_read_only_view() -> None:
    repository = InMemoryRepository()
    repository.save(Project(id="pilot", title="Pilot", metadata={"world": "city"}))
    repository.save(Project(id="alpha", title="Alpha", metadata={"world": "harbor"}))
    service = KnowledgeService(repository)

    world_matches = service.search(" WORLD ")
    all_matches = service.search("   ")

    assert tuple(entry.project_id for entry in world_matches.matches) == ("alpha", "pilot")
    assert tuple(entry.project_id for entry in all_matches.matches) == ("alpha", "pilot")
    assert repository.load("pilot").metadata == {"world": "city"}
    assert repository.load("alpha").metadata == {"world": "harbor"}


def test_workflow_orchestration_and_executive_summary_are_visualization_only() -> None:
    repository = InMemoryRepository()
    context = WorkflowContext(page={"id": "page-2"}, state=PageState.PROMPT_BUILT)
    service = _service(repository)

    orchestration = service.orchestration(context)
    summary = service.executive_summary(context)

    assert orchestration.preview.next_command == "generate"
    assert orchestration.preview.execution_performed is False
    assert summary.execution_performed is False
    assert '"execution_performed": false' in summary.to_json()
    assert context.state is PageState.PROMPT_BUILT
