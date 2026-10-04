from __future__ import annotations

from unittest.mock import Mock

import pytest
from pydantic import ValidationError as PydanticValidationError

from manga_director.domain.events import EventType
from manga_director.domain.project import Chapter, Page, Project
from manga_director.domain.state_machine import PageState, StateMachine
from manga_director.events import MemoryEventBus
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import (
    ChapterContext,
    ChapterWorkflowEngine,
    ChapterWorkflowResult,
    PageNumberWorkflowScheduler,
    ProjectContext,
    ProjectWorkflowEngine,
    ProjectWorkflowResult,
    WorkflowContext,
    WorkflowCoordinator,
)
from manga_director.workflow.hierarchy_contracts import ProjectReadinessSummary


def _approved_page(page_number: int) -> Page:
    return Page(
        page_number=page_number,
        state=PageState.APPROVED,
        page_design={"purpose": "hook"},
        review={"approved": True},
        storyboard={"panels": []},
        prompt={"prompt": "manga page"},
        image={"image_path": "page.png"},
        quality={"passed": True},
        approval={"approved_by": "editor"},
    )


_REQUIRED_EVIDENCE = {
    PageState.DRAFT: (),
    PageState.DESIGNED: ("page_design",),
    PageState.REVIEWED: ("page_design", "review"),
    PageState.STORYBOARDED: ("page_design", "review", "storyboard"),
    PageState.PROMPT_BUILT: ("page_design", "review", "storyboard", "prompt"),
    PageState.GENERATED: ("page_design", "review", "storyboard", "prompt", "image"),
    PageState.QUALITY_CHECKED: (
        "page_design",
        "review",
        "storyboard",
        "prompt",
        "image",
        "quality",
    ),
    PageState.APPROVED: (
        "page_design",
        "review",
        "storyboard",
        "prompt",
        "image",
        "quality",
        "approval",
    ),
}


def _page_with_required_evidence(page_number: int, state: PageState) -> Page:
    return Page(
        page_number=page_number,
        state=state,
        **{field: {"persisted": field} for field in _REQUIRED_EVIDENCE[state]},
    )


class _ReadOnlyRepository:
    def __init__(self, project: Project) -> None:
        self.project = project
        self.load_calls = 0

    def load(self, project_id: str) -> Project:
        assert project_id == self.project.id
        self.load_calls += 1
        return self.project.model_copy(deep=True)

    def save(self, project: Project) -> None:
        raise AssertionError("status must not save")

    def delete(self, project_id: str) -> None:
        raise AssertionError("status must not delete")


def test_scheduler_selects_the_lowest_non_approved_page() -> None:
    chapter = Chapter(id="chapter-1", title="Chapter 1", page_numbers=[3, 1, 2])
    context = ChapterContext(
        chapter=chapter,
        pages=[_approved_page(1), Page(page_number=3), Page(page_number=2)],
    )

    page = PageNumberWorkflowScheduler().next_page(context)

    assert page is not None
    assert page.page_number == 2


def test_project_engine_creates_persists_and_starts_a_project() -> None:
    repository = InMemoryRepository()
    events = MemoryEventBus()
    engine = ProjectWorkflowEngine(repository, events)

    created = engine.create("demo", "Demo")
    started = engine.start("demo")

    assert created.chapters[0].id == "chapter-1"
    assert started.context.current_chapter == "chapter-1"
    assert started.context.current_page == 1
    assert [event.event_type for event in events.published] == [EventType.PROJECT_STARTED]
    assert engine.status("demo").history[0]["event"] == EventType.PROJECT_STARTED.value

    persisted = repository.load("demo")
    repository.save(persisted.replace_page(_approved_page(1)))
    chapter_engine = ChapterWorkflowEngine(repository, events, PageNumberWorkflowScheduler())
    chapter_engine.run(
        "demo",
        "chapter-1",
        lambda project_id, page_number: WorkflowContext(
            page={"project_id": project_id, "page_id": str(page_number)}
        ),
    )
    completed = engine.refresh("demo")

    assert completed.context.current_chapter is None
    assert events.published[-2].event_type == EventType.CHAPTER_COMPLETED
    assert events.published[-1].event_type == EventType.PROJECT_COMPLETED


def test_chapter_engine_runs_one_page_and_completes_after_approval() -> None:
    repository = InMemoryRepository()
    project = Project(
        id="demo",
        title="Demo",
        chapters=[Chapter(id="chapter-1", title="Chapter 1", page_numbers=[1])],
        pages=[Page(page_number=1)],
    )
    repository.save(project)
    events = MemoryEventBus()
    engine = ChapterWorkflowEngine(repository, events, PageNumberWorkflowScheduler())

    def approve_page(project_id: str, page_number: int) -> WorkflowContext:
        persisted = repository.load(project_id)
        repository.save(persisted.replace_page(_approved_page(page_number)))
        return WorkflowContext(
            page={"project_id": project_id, "page_id": str(page_number)},
            state=PageState.APPROVED,
        )

    result = engine.run("demo", "chapter-1", approve_page)

    assert result.completed is True
    assert result.page_context is not None
    assert result.page_context.state == PageState.APPROVED
    assert [event.event_type for event in events.published] == [
        EventType.CHAPTER_STARTED,
        EventType.CHAPTER_COMPLETED,
    ]


def test_chapter_engine_resume_keeps_a_quality_checked_page_current() -> None:
    repository = InMemoryRepository()
    repository.save(
        Project(
            id="demo",
            title="Demo",
            chapters=[Chapter(id="chapter-1", title="Chapter 1", page_numbers=[1])],
            pages=[
                Page(
                    page_number=1,
                    state=PageState.QUALITY_CHECKED,
                    page_design={"purpose": "hook"},
                    review={"approved": True},
                    storyboard={"panels": []},
                    prompt={"prompt": "manga page"},
                    image={"image_path": "page.png"},
                    quality={"passed": True},
                )
            ],
        )
    )
    engine = ChapterWorkflowEngine(repository, MemoryEventBus(), PageNumberWorkflowScheduler())
    calls: list[int] = []

    def run_page(project_id: str, page_number: int) -> WorkflowContext:
        calls.append(page_number)
        return WorkflowContext(
            page={"project_id": project_id, "page_id": str(page_number)},
            state=PageState.QUALITY_CHECKED,
        )

    result = engine.run("demo", "chapter-1", run_page)

    assert calls == [1]
    assert result.completed is False
    assert result.context.current_page == 1


def test_coordinator_delegates_project_to_chapter_without_workflow_logic() -> None:
    project = Project(
        id="demo",
        title="Demo",
        chapters=[Chapter(id="chapter-1", title="Chapter 1", page_numbers=[1])],
        pages=[Page(page_number=1)],
    )
    project_context = ProjectContext(
        project=project,
        chapters=project.chapters,
        current_chapter="chapter-1",
        current_page=1,
    )
    project_engine = Mock()
    project_engine.start.return_value = ProjectWorkflowResult(context=project_context)
    project_engine.refresh.return_value = ProjectWorkflowResult(context=project_context)
    chapter_engine = Mock()
    chapter_engine.run.return_value = ChapterWorkflowResult(
        context=ChapterContext(chapter=project.chapters[0], pages=project.pages, current_page=1),
        completed=False,
    )
    coordinator = WorkflowCoordinator(project_engine, chapter_engine, Mock(), Mock())

    result = coordinator.run_project("demo")

    assert result.context == project_context
    project_engine.start.assert_called_once_with("demo")
    assert chapter_engine.run.call_args.args[:2] == ("demo", "chapter-1")
    project_engine.refresh.assert_called_once_with("demo")


@pytest.mark.parametrize("state", list(PageState))
def test_project_status_reports_exact_state_and_one_read_only_outcome(state: PageState) -> None:
    project = Project(id="demo", title="Demo", pages=[_page_with_required_evidence(1, state)])
    repository = _ReadOnlyRepository(project)
    event_bus = Mock()
    event_bus.publish.side_effect = AssertionError("status must not publish events")

    status = ProjectWorkflowEngine(repository, event_bus).status("demo")

    inspection = status.page_readiness[0]
    assert inspection.current_state == state
    assert inspection.unmet_prerequisites == ()
    assert inspection.non_execution is True
    assert inspection.next_operation == (
        "NO_OP_TERMINAL" if state == PageState.APPROVED else StateMachine().next_command(state)
    )
    assert status.readiness_summary is not None
    assert status.readiness_summary.model_dump() == {
        "completed_page_count": int(state == PageState.APPROVED),
        "actionable_page_count": int(state != PageState.APPROVED),
        "blocked_page_count": 0,
        "next_actionable_page_number": None if state == PageState.APPROVED else 1,
        "first_blocked_page": None,
        "next_actionable_page": None if state == PageState.APPROVED else inspection.model_dump(),
        "readiness_outcome": "COMPLETE" if state == PageState.APPROVED else "ACTIONABLE",
        "readiness_focus_page": None if state == PageState.APPROVED else inspection.model_dump(),
    }
    assert repository.load_calls == 1
    assert repository.project == project


@pytest.mark.parametrize(
    ("state", "missing"),
    [(state, fields[-1] if fields else None) for state, fields in _REQUIRED_EVIDENCE.items()],
)
def test_project_status_fails_closed_for_missing_cumulative_evidence(
    state: PageState, missing: str | None
) -> None:
    values = {field: {"persisted": field} for field in _REQUIRED_EVIDENCE[state]}
    if missing is not None:
        del values[missing]
    repository = _ReadOnlyRepository(
        Project(id="demo", title="Demo", pages=[Page(page_number=1, state=state, **values)])
    )

    status = ProjectWorkflowEngine(repository, Mock()).status("demo")
    inspection = status.page_readiness[0]

    assert inspection.unmet_prerequisites == (() if missing is None else (missing,))
    assert inspection.next_operation == (
        "NO_OP_BLOCKED"
        if missing is not None
        else StateMachine().next_command(PageState.DRAFT)
    )
    assert inspection.non_execution is True
    assert status.readiness_summary is not None
    assert status.readiness_summary.model_dump() == {
        "completed_page_count": 0,
        "actionable_page_count": int(missing is None),
        "blocked_page_count": int(missing is not None),
        "next_actionable_page_number": 1 if missing is None else None,
        "first_blocked_page": inspection.model_dump() if missing is not None else None,
        "next_actionable_page": inspection.model_dump() if missing is None else None,
        "readiness_outcome": "ACTIONABLE" if missing is None else "BLOCKED",
        "readiness_focus_page": inspection.model_dump(),
    }


def test_project_status_is_deterministic_and_leaves_unsorted_pages_unchanged() -> None:
    project = Project(
        id="demo",
        title="Demo",
        pages=[
            _page_with_required_evidence(3, PageState.APPROVED),
            Page(page_number=1),
            _page_with_required_evidence(2, PageState.REVIEWED),
        ],
    )
    repository = _ReadOnlyRepository(project)
    engine = ProjectWorkflowEngine(repository, Mock())

    first = engine.status("demo").model_dump(mode="json")
    second = engine.status("demo").model_dump(mode="json")

    assert [item["page_number"] for item in first["page_readiness"]] == [1, 2, 3]
    assert first == second
    assert repository.project == project


def test_project_status_normalises_its_return_value_without_saving_the_project() -> None:
    project = Project(id="demo", title="Demo", pages=[Page(page_number=1)])
    repository = _ReadOnlyRepository(project)

    status = ProjectWorkflowEngine(repository, Mock()).status("demo")

    assert status.current_chapter == "chapter-1"
    assert status.current_page == 1
    assert status.project.chapters == [
        Chapter(id="chapter-1", title="Chapter 1", page_numbers=[1])
    ]
    assert status.chapters == status.project.chapters
    assert repository.project == project


def test_project_status_propagates_malformed_project_load_errors() -> None:
    class MalformedRepository:
        def load(self, project_id: str) -> Project:
            return Project.model_validate({"id": project_id, "title": "Demo", "pages": [{"page_number": 0}]})

    with pytest.raises(PydanticValidationError):
        ProjectWorkflowEngine(MalformedRepository(), Mock()).status("demo")


def test_project_readiness_summary_covers_all_pages_and_preserves_current_position() -> None:
    project = Project(
        id="demo",
        title="Demo",
        chapters=[
            Chapter(id="chapter-2", title="Later", page_numbers=[20, 10]),
            Chapter(id="chapter-1", title="Earlier", page_numbers=[8, 3]),
        ],
        pages=[
            _approved_page(20),
            Page(page_number=10, state=PageState.DESIGNED),
            _page_with_required_evidence(8, PageState.REVIEWED),
            Page(page_number=3),
            Page(page_number=2),
        ],
    )
    before = project.model_dump(mode="json")
    repository = _ReadOnlyRepository(project)
    event_bus = Mock()
    event_bus.publish.side_effect = AssertionError("status must not publish events")
    engine = ProjectWorkflowEngine(repository, event_bus)

    status = engine.status("demo")
    repeated = engine.status("demo")

    assert status.current_chapter == "chapter-2"
    assert status.current_page == 10
    assert [item.page_number for item in status.page_readiness] == [2, 3, 8, 10, 20]
    assert status.readiness_summary is not None
    assert status.readiness_summary.model_dump() == {
        "completed_page_count": 1,
        "actionable_page_count": 3,
        "blocked_page_count": 1,
        "next_actionable_page_number": 2,
        "first_blocked_page": None,
        "next_actionable_page": status.page_readiness[0].model_dump(),
        "readiness_outcome": "ACTIONABLE",
        "readiness_focus_page": status.page_readiness[0].model_dump(),
    }
    assert status.model_dump(mode="json") == repeated.model_dump(mode="json")
    assert repository.load_calls == 2
    assert repository.project.model_dump(mode="json") == before
    assert "readiness_summary" not in status.project.model_dump()
    with pytest.raises(PydanticValidationError, match="frozen_instance"):
        status.readiness_summary.actionable_page_count = 0


@pytest.mark.parametrize(
    ("pages", "completed", "blocked", "outcome"),
    [
        ([], 0, 0, "EMPTY"),
        ([_approved_page(7), _approved_page(2)], 2, 0, "COMPLETE"),
        ([Page(page_number=7, state=PageState.DESIGNED), Page(page_number=2, state=PageState.APPROVED)], 0, 2, "BLOCKED"),
        ([_approved_page(7), Page(page_number=2, state=PageState.DESIGNED)], 1, 1, "BLOCKED"),
    ],
)
def test_project_readiness_summary_has_no_next_page_without_actionable_work(
    pages: list[Page], completed: int, blocked: int, outcome: str
) -> None:
    repository = _ReadOnlyRepository(Project(id="demo", title="Demo", pages=pages))

    status = ProjectWorkflowEngine(repository, Mock()).status("demo")

    assert status.readiness_summary is not None
    assert status.readiness_summary.model_dump(mode="json") == {
        "completed_page_count": completed,
        "actionable_page_count": 0,
        "blocked_page_count": blocked,
        "next_actionable_page_number": None,
        "next_actionable_page": None,
        "readiness_outcome": outcome,
        "readiness_focus_page": status.page_readiness[0].model_dump(mode="json") if blocked else None,
        "first_blocked_page": (
            next(
                item.model_dump(mode="json")
                for item in status.page_readiness
                if item.next_operation == "NO_OP_BLOCKED"
            )
            if blocked
            else None
        ),
    }
    assert completed + blocked == len(status.page_readiness)
    assert repository.load_calls == 1


def test_project_readiness_summary_returns_the_first_blocked_page_only_when_stalled() -> None:
    blocked = Project(
        id="demo",
        title="Demo",
        pages=[
            Page(page_number=8, state=PageState.DESIGNED),
            Page(page_number=3, state=PageState.REVIEWED),
            _approved_page(1),
        ],
    )

    stalled = ProjectWorkflowEngine(_ReadOnlyRepository(blocked), Mock()).status("demo")

    assert stalled.readiness_summary is not None
    assert stalled.readiness_summary.readiness_outcome == "BLOCKED"
    assert stalled.readiness_summary.first_blocked_page == stalled.page_readiness[1]
    assert stalled.readiness_summary.readiness_focus_page is stalled.readiness_summary.first_blocked_page
    assert stalled.readiness_summary.first_blocked_page.page_number == 3
    assert stalled.readiness_summary.first_blocked_page.unmet_prerequisites == (
        "page_design",
        "review",
    )

    actionable = blocked.model_copy(update={"pages": [*blocked.pages, Page(page_number=2)]})
    available = ProjectWorkflowEngine(_ReadOnlyRepository(actionable), Mock()).status("demo")

    assert available.readiness_summary is not None
    assert available.readiness_summary.readiness_outcome == "ACTIONABLE"
    assert available.readiness_summary.actionable_page_count == 1
    assert available.readiness_summary.first_blocked_page is None
    assert available.readiness_summary.next_actionable_page == available.page_readiness[1]
    assert available.readiness_summary.readiness_focus_page is available.readiness_summary.next_actionable_page
    assert available.readiness_summary.next_actionable_page.page_number == (
        available.readiness_summary.next_actionable_page_number
    )


def test_project_readiness_summary_keeps_existing_construction_valid_without_next_detail() -> None:
    summary = ProjectReadinessSummary(
        completed_page_count=0,
        actionable_page_count=1,
        blocked_page_count=0,
        next_actionable_page_number=1,
    )

    assert summary.next_actionable_page is None
    assert summary.readiness_outcome is None
    assert summary.readiness_focus_page is None
    assert ProjectReadinessSummary.model_validate(
        summary.model_dump(exclude={"next_actionable_page", "readiness_outcome", "readiness_focus_page"})
    ) == summary


def test_project_context_keeps_existing_construction_valid_without_a_summary() -> None:
    project = Project(id="demo", title="Demo", pages=[Page(page_number=1)])

    context = ProjectContext(project=project)

    assert context.readiness_summary is None
    assert ProjectContext.model_validate(context.model_dump(exclude={"readiness_summary"})) == context
