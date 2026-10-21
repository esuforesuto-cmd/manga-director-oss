import pytest

from manga_director.adapters import ImageGeneratorFactory, LLMFactory
from manga_director.agents.registry import primary_agents, support_agents
from manga_director.application import WorkflowApplicationService, build_workflow_application
from manga_director.domain.exceptions import StateTransitionError
from manga_director.domain.state_machine import StateMachine
from manga_director.events import MemoryEventBus
from manga_director.mcp.application import MangaApplicationService
from manga_director.prompting import PromptPipeline, PromptTemplateLoader
from manga_director.repositories import InMemoryRepository, ProjectLoader
from manga_director.workflow import (
    ChapterWorkflowEngine,
    PageNumberWorkflowScheduler,
    ProjectWorkflowEngine,
    WorkflowCoordinator,
    WorkflowEngine,
)


def _application() -> WorkflowApplicationService:
    repository = InMemoryRepository()
    loader = ProjectLoader(repository)
    events = MemoryEventBus()
    engine = WorkflowEngine(
        state_machine=StateMachine(),
        event_bus=events,
        agents=primary_agents(
            ImageGeneratorFactory.create("mock"),
            None,
            LLMFactory.create("mock"),
            PromptPipeline(template_loader=PromptTemplateLoader()),
        ),
        support_agents=support_agents(LLMFactory.create("mock"), None),
    )
    coordinator = WorkflowCoordinator(
        ProjectWorkflowEngine(repository, events),
        ChapterWorkflowEngine(repository, events, PageNumberWorkflowScheduler()),
        engine,
        loader,
    )
    return build_workflow_application(
        workflow_engine=engine,
        workflow_coordinator=coordinator,
        project_loader=loader,
        repository=repository,
    )


def test_neutral_application_service_preserves_the_mcp_import_contract() -> None:
    assert MangaApplicationService is WorkflowApplicationService


def test_application_service_delegates_workflow_and_explicit_approval() -> None:
    application = _application()

    application.create_project("demo", "Demo", 1, {"genre": "drama"})
    application.run_project("demo")
    before_approval = application.get_page_status("demo", 1)
    application.approve_page("demo", 1, "editor", {})
    after_approval = application.get_page_status("demo", 1)

    assert before_approval.current_state.value == "QualityChecked"
    assert after_approval.current_state.value == "Approved"
    assert application.get_project("demo").metadata == {"genre": "drama"}


def test_non_localfile_application_cannot_enter_private_evidence_linked_path() -> None:
    application = _application()

    with pytest.raises(StateTransitionError, match="LocalFile"):
        application._approve_page_with_evidence(
            "demo",
            1,
            "editor:local",
            "review:exact:001",
            object(),  # type: ignore[arg-type]
        )
