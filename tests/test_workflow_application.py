from contextvars import Context, copy_context
from unittest.mock import Mock, call

import pytest

from manga_director.adapters import ImageGeneratorFactory, LLMFactory
from manga_director.agents.registry import primary_agents, support_agents
from manga_director.application import WorkflowApplicationService, build_workflow_application
from manga_director.domain.events import EventType
from manga_director.domain.exceptions import StateTransitionError, ValidationError
from manga_director.domain.project import Page
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
from manga_director.workflow.contracts import WorkflowContext


class _ExtendingProjectLoader(ProjectLoader):
    def load(self, project_id: str, page_id: str) -> WorkflowContext:
        context = super().load(project_id, page_id)
        return context.model_copy(
            update={"metadata": context.metadata | {"loader_extension": "preserved"}}
        )


def _application(
    events: MemoryEventBus | None = None, *, loader: ProjectLoader | None = None
) -> WorkflowApplicationService:
    loader = loader if loader is not None else ProjectLoader(InMemoryRepository())
    repository = loader.repository
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


def test_execution_loader_uses_load_override_with_one_repository_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = InMemoryRepository()
    loader = ProjectLoader(repository)
    loader.create("demo", "Demo", 1)
    original_load = repository.load
    repository_load = Mock(wraps=original_load)
    monkeypatch.setattr(repository, "load", repository_load)

    extended_loader = _ExtendingProjectLoader(repository)

    context = extended_loader.load_for_execution("demo", "1")

    assert context.metadata["loader_extension"] == "preserved"
    repository_load.assert_called_once_with("demo")


@pytest.mark.parametrize("source", ["metadata", "history"])
def test_execution_loader_rejects_persisted_authority_before_override_or_execution(
    source: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = InMemoryRepository()
    loader = _ExtendingProjectLoader(repository)
    project = loader.create("demo", "Demo", 1)
    history = [{"_explicit_storyboard_input_authority": "private-marker"}]
    update = (
        {"metadata": {"workflow_history": history}} if source == "metadata" else {"history": history}
    )
    stored = project.replace_page(project.page(1).model_copy(update=update))
    repository.save(stored)
    application = _application(loader=loader)
    masking_load = Mock(return_value=WorkflowContext(metadata={"workflow_history": []}))
    agent = Mock()
    save_page = Mock(wraps=loader.save)
    monkeypatch.setattr(loader, "load", masking_load)
    monkeypatch.setattr(loader, "save", save_page)
    monkeypatch.setitem(application._engine._agents, PageState.DESIGNED, agent)

    with pytest.raises(ValidationError, match="Reserved storyboard confirmation metadata") as error:
        application.execute_page("design", "demo", 1, {})

    assert "private-marker" not in str(error.value)
    masking_load.assert_not_called()
    agent.execute.assert_not_called()
    save_page.assert_not_called()
    assert repository.load("demo") == stored


def test_execution_snapshot_only_applies_to_the_requested_project_and_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = InMemoryRepository()
    loader = _ExtendingProjectLoader(repository)
    project = loader.create("demo", "Demo", 1)
    metadata = {"_explicit_storyboard_input_authority": None}
    repository.save(project.model_copy(update={"pages": [project.page(1), Page(page_number=2)]}))
    other = loader.create("other", "Other", 1)
    repository.save(other.replace_page(other.page(1).model_copy(update={"metadata": metadata})))
    original_load = repository.load
    repository_load = Mock(wraps=original_load)
    monkeypatch.setattr(repository, "load", repository_load)

    def load_with_other_reads(project_id: str, page_id: str) -> WorkflowContext:
        second = project.model_copy(
            update={"pages": [project.page(1), Page(page_number=2, metadata={"new": True})]}
        )
        repository.save(second)
        assert ProjectLoader.load(loader, project_id, "2").metadata["new"] is True
        other_context = ProjectLoader.load(loader, "other", "1")
        assert "_explicit_storyboard_input_authority" in other_context.metadata
        return ProjectLoader.load(loader, project_id, page_id)

    monkeypatch.setattr(loader, "load", load_with_other_reads)

    assert loader.load_for_execution("demo", "01").page["page_id"] == "1"
    assert repository_load.call_args_list == [call("demo"), call("demo"), call("other")]


@pytest.mark.parametrize("override_raises", [False, True])
def test_execution_snapshot_is_released_in_current_and_copied_contexts(
    override_raises: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = InMemoryRepository()
    loader = _ExtendingProjectLoader(repository)
    project = loader.create("demo", "Demo", 1)
    captured: list[Context] = []

    def capture_context(project_id: str, page_id: str) -> WorkflowContext:
        captured.append(copy_context())
        if override_raises:
            raise RuntimeError("load override failed")
        return ProjectLoader.load(loader, project_id, page_id)

    with monkeypatch.context() as patch:
        patch.setattr(loader, "load", capture_context)
        if override_raises:
            with pytest.raises(RuntimeError, match="load override failed"):
                loader.load_for_execution("demo", "1")
        else:
            loader.load_for_execution("demo", "1")

    repository.save(project.replace_page(Page(page_number=1, metadata={"new": True})))
    assert loader.load("demo", "1").metadata["new"] is True
    assert captured[0].run(loader.load, "demo", "1").metadata["new"] is True


@pytest.mark.parametrize(
    ("context", "message"),
    [
        (WorkflowContext(page={"project_id": "other"}), "does not match"),
        (WorkflowContext(page={"page_id": "2"}), "does not match"),
        (WorkflowContext(page={"page_id": "1", "page_number": 2}), "does not match"),
        (WorkflowContext(page={"page_id": True}), "does not match"),
        (
            WorkflowContext(metadata={"_explicit_storyboard_input_authority": None}),
            "Reserved storyboard confirmation metadata",
        ),
    ],
    ids=["project", "page-id", "page-number", "invalid-page-id", "returned-authority"],
)
def test_execution_rejects_invalid_override_context_without_running_or_saving(
    context: WorkflowContext, message: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = InMemoryRepository()
    loader = _ExtendingProjectLoader(repository)
    stored = loader.create("demo", "Demo", 1)
    application = _application(loader=loader)
    agent = Mock()
    save_page = Mock(wraps=loader.save)
    monkeypatch.setattr(loader, "load", Mock(return_value=context))
    monkeypatch.setattr(loader, "save", save_page)
    monkeypatch.setitem(application._engine._agents, PageState.DESIGNED, agent)

    with pytest.raises(ValidationError, match=message):
        application.execute_page("design", "demo", 1, {})

    agent.execute.assert_not_called()
    save_page.assert_not_called()
    assert repository.load("demo") == stored


def test_execution_rejects_repository_project_mismatch_before_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = InMemoryRepository()
    loader = _ExtendingProjectLoader(repository)
    stored = loader.create("demo", "Demo", 1)
    application = _application(loader=loader)
    original_load = repository.load
    mismatched_load = Mock(return_value=stored.model_copy(update={"id": "other"}))
    override = Mock(return_value=WorkflowContext())
    agent = Mock()
    save_page = Mock(wraps=loader.save)
    monkeypatch.setattr(repository, "load", mismatched_load)
    monkeypatch.setattr(loader, "load", override)
    monkeypatch.setattr(loader, "save", save_page)
    monkeypatch.setitem(application._engine._agents, PageState.DESIGNED, agent)

    with pytest.raises(ValidationError, match="Loaded Project does not match"):
        application.execute_page("design", "demo", 1, {})

    mismatched_load.assert_called_once_with("demo")
    override.assert_not_called()
    agent.execute.assert_not_called()
    save_page.assert_not_called()
    assert original_load("demo") == stored


@pytest.mark.parametrize("page", [{}, {"project_id": "demo", "page_id": "01", "page_number": 1}])
def test_execution_loader_accepts_legacy_omissions_and_matching_identity(
    page: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    loader = _ExtendingProjectLoader(InMemoryRepository())
    loader.create("demo", "Demo", 1)
    context = WorkflowContext(page=page)
    monkeypatch.setattr(loader, "load", Mock(return_value=context))

    assert loader.load_for_execution("demo", "1") is context


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
