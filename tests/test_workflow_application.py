from unittest.mock import Mock

import pytest

from manga_director.adapters import ImageGeneratorFactory, LLMFactory
from manga_director.agents.registry import primary_agents, support_agents
from manga_director.application import WorkflowApplicationService, build_workflow_application
from manga_director.domain.events import EventType
from manga_director.domain.exceptions import StateTransitionError, ValidationError
from manga_director.domain.state_machine import PageState, StateMachine
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


def _application(events: MemoryEventBus | None = None) -> WorkflowApplicationService:
    repository = InMemoryRepository()
    loader = ProjectLoader(repository)
    events = events if events is not None else MemoryEventBus()
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


@pytest.mark.parametrize("run_chapter", [False, True], ids=["project", "chapter"])
def test_application_service_delegates_workflow_and_explicit_approval(run_chapter: bool) -> None:
    application = _application()

    application.create_project("demo", "Demo", 1, {"genre": "drama"})
    if run_chapter:
        application.run_chapter("demo", "chapter-1")
    else:
        application.run_project("demo")
    before_approval = application.get_page_status("demo", 1)
    application.approve_page("demo", 1, "editor", {})
    after_approval = application.get_page_status("demo", 1)

    assert before_approval.current_state.value == "QualityChecked"
    assert after_approval.current_state.value == "Approved"
    assert application.get_project("demo").metadata == {"genre": "drama"}


@pytest.mark.parametrize(
    ("method", "args"),
    [
        ("run_project", ("demo",)),
        ("resume_project", ("demo",)),
        ("run_chapter", ("demo", "chapter-1")),
    ],
)
@pytest.mark.parametrize(
    "metadata",
    [
        {"_explicit_storyboard_input_authority": "private-marker"},
        {"nested": {"_explicit_storyboard_input_authority": "private-marker"}},
        {"nested": [{"_explicit_storyboard_input_authority": "private-marker"}]},
        {"workflow_history": [{"_explicit_storyboard_input_authority": "private-marker"}]},
        {"_explicit_storyboard_input_authority": None},
    ],
    ids=["top-level", "nested", "list", "workflow-history", "null"],
)
def test_hierarchy_rejects_saved_storyboard_authority_before_running_page(
    method: str, args: tuple[str, ...], metadata: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    events = MemoryEventBus()
    application = _application(events)
    application.create_project("demo", "Demo", 1, {})
    project = application._repository.load("demo")
    page = project.page(1).model_copy(update={"metadata": metadata})
    application._repository.save(project.replace_page(page))

    agent = Mock()
    agent.execute.side_effect = AssertionError("Page agent ran before metadata validation")
    monkeypatch.setitem(application._engine._agents, PageState.DESIGNED, agent)
    save_page = Mock(wraps=application._loader.save)
    monkeypatch.setattr(application._loader, "save", save_page)

    with pytest.raises(ValidationError, match=r"^Reserved storyboard confirmation metadata is not accepted\.$"):
        getattr(application, method)(*args)

    agent.execute.assert_not_called()
    save_page.assert_not_called()
    assert application._repository.load("demo").page(1) == page
    assert [event.event_type for event in events.published] == [
        EventType.PROJECT_STARTED,
        EventType.CHAPTER_STARTED,
    ]


def test_page_status_remains_readable_with_reserved_saved_metadata() -> None:
    application = _application()
    application.create_project("demo", "Demo", 1, {})
    project = application._repository.load("demo")
    page = project.page(1).model_copy(
        update={"metadata": {"workflow_history": [{"_explicit_storyboard_input_authority": None}]}}
    )
    application._repository.save(project.replace_page(page))

    status = application.get_page_status("demo", 1)

    assert status.current_state == PageState.DRAFT
    assert status.workflow_history == []


@pytest.mark.parametrize("operation", ["execute_page", "execute_support"])
def test_page_commands_reject_saved_reserved_workflow_history_before_execution_or_save(
    operation: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    application = _application()
    application.create_project("demo", "Demo", 1, {})
    project = application._repository.load("demo")
    page = project.page(1).model_copy(
        update={
            "metadata": {
                "workflow_history": [{"_explicit_storyboard_input_authority": "private-marker"}]
            }
        }
    )
    application._repository.save(project.replace_page(page))
    agent = Mock()
    if operation == "execute_page":
        monkeypatch.setitem(application._engine._agents, PageState.DESIGNED, agent)
    else:
        monkeypatch.setitem(application._engine._support_agents, "dialogue", agent)
    save_page = Mock(wraps=application._loader.save)
    monkeypatch.setattr(application._loader, "save", save_page)

    with pytest.raises(ValidationError, match="Reserved storyboard confirmation metadata") as error:
        if operation == "execute_page":
            application.execute_page("design", "demo", 1, {})
        else:
            application.execute_support("dialogue", "demo", 1, {})

    assert "private-marker" not in str(error.value)
    agent.execute.assert_not_called()
    save_page.assert_not_called()
    assert application._repository.load("demo").page(1) == page


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


def test_non_localfile_application_cannot_confirm_storyboard_input() -> None:
    application = _application()
    with pytest.raises(StateTransitionError, match="LocalFile"):
        application._confirm_storyboard_input("demo", 1, {})


def test_support_rejects_reserved_storyboard_authority_in_persisted_metadata() -> None:
    application = _application()
    application.create_project("demo", "Demo", 1, {})
    project = application._repository.load("demo")
    page = project.page(1).model_copy(
        update={
            "metadata": {"workflow_history": [{"_explicit_storyboard_input_authority": {"forged": True}}]}
        },
        deep=True,
    )
    application._repository.save(project.replace_page(page))

    with pytest.raises(ValidationError, match="Reserved storyboard confirmation metadata"):
        application.execute_support("dialogue", "demo", 1, {})
