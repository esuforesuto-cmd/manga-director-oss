"""Project-level workflow state, persistence, and lifecycle events."""

from __future__ import annotations

from typing import Any

from manga_director.domain.events import EventType, WorkflowEvent
from manga_director.domain.exceptions import ProjectAlreadyExistsError, ValidationError
from manga_director.domain.project import Chapter, Page, Project
from manga_director.domain.state_machine import PageState, StateMachine
from manga_director.events.bus import EventBus
from manga_director.repositories.protocols import ProjectRepository
from manga_director.workflow.hierarchy_contracts import (
    PageReadinessInspection,
    ProjectContext,
    ProjectReadinessSummary,
    ProjectWorkflowResult,
)

_REQUIRED_EVIDENCE: dict[PageState, tuple[str, ...]] = {
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


class ProjectWorkflowEngine:
    """Own project lifecycle metadata while depending only on the repository port."""

    def __init__(self, repository: ProjectRepository, event_bus: EventBus) -> None:
        self._repository = repository
        self._event_bus = event_bus
        self._state_machine = StateMachine()

    def create(self, project_id: str, title: str, page_number: int = 1) -> ProjectContext:
        """Create a minimal project with its first page assigned to a default chapter."""
        if self._repository.exists(project_id):
            raise ProjectAlreadyExistsError(f"Project '{project_id}' already exists.")
        chapter = Chapter(id="chapter-1", title="Chapter 1", page_numbers=[page_number])
        project = Project(
            id=project_id,
            title=title,
            chapters=[chapter],
            pages=[Page(page_number=page_number)],
        )
        self._repository.save(project)
        return self._context(project)

    def start(self, project_id: str) -> ProjectWorkflowResult:
        """Record ProjectStarted exactly once and expose the next incomplete chapter."""
        project = self._normalise(self._repository.load(project_id))
        events: list[WorkflowEvent] = []
        if not self._has_history_event(project, EventType.PROJECT_STARTED):
            event = WorkflowEvent(
                event_type=EventType.PROJECT_STARTED, data={"project_id": project.id}
            )
            project = self._record(project, event)
            events.append(event)
        project = self._set_position(project)
        self._repository.save(project)
        self._event_bus.publish(events)
        return ProjectWorkflowResult(
            context=self._context(project), events=events, messages=["project workflow started"]
        )

    def add_chapter(
        self, project_id: str, chapter_id: str, title: str, page_numbers: list[int]
    ) -> ProjectContext:
        """Attach an ordered Chapter boundary without changing any Page state."""
        project = self._repository.load(project_id)
        if any(chapter.id == chapter_id for chapter in project.chapters):
            raise ValidationError(
                f"Chapter '{chapter_id}' already exists in project '{project_id}'."
            )
        if not page_numbers:
            raise ValidationError("A chapter requires at least one page number.")
        for page_number in page_numbers:
            project.page(page_number)
        assigned = {number for chapter in project.chapters for number in chapter.page_numbers}
        overlap = sorted(assigned.intersection(page_numbers))
        if overlap:
            rendered = ", ".join(map(str, overlap))
            raise ValidationError(f"Pages already belong to another chapter: {rendered}.")
        project = project.model_copy(
            update={
                "chapters": [
                    *project.chapters,
                    Chapter(id=chapter_id, title=title, page_numbers=sorted(page_numbers)),
                ]
            },
            deep=True,
        )
        project = self._set_position(project)
        self._repository.save(project)
        return self._context(project)

    def status(self, project_id: str) -> ProjectContext:
        """Inspect a normalised in-memory Project without persistence or execution."""
        project = self._set_position(self._normalise(self._repository.load(project_id)))
        return self._context(project, self._readiness(project))

    def refresh(self, project_id: str) -> ProjectWorkflowResult:
        """Persist progress and emit ProjectCompleted once every chapter is approved."""
        project = self._set_position(self._normalise(self._repository.load(project_id)))
        events: list[WorkflowEvent] = []
        if self._is_completed(project) and not self._has_history_event(
            project, EventType.PROJECT_COMPLETED
        ):
            event = WorkflowEvent(
                event_type=EventType.PROJECT_COMPLETED, data={"project_id": project.id}
            )
            project = self._record(project, event)
            events.append(event)
        self._repository.save(project)
        self._event_bus.publish(events)
        return ProjectWorkflowResult(
            context=self._context(project), events=events, messages=["project progress refreshed"]
        )

    def _normalise(self, project: Project) -> Project:
        if project.chapters or not project.pages:
            return project
        page_numbers = sorted(page.page_number for page in project.pages)
        return project.model_copy(
            update={
                "chapters": [Chapter(id="chapter-1", title="Chapter 1", page_numbers=page_numbers)]
            },
            deep=True,
        )

    def _set_position(self, project: Project) -> Project:
        chapter = next(
            (item for item in project.chapters if not self._chapter_completed(project, item)), None
        )
        if chapter is None:
            chapter = next(
                (item for item in project.chapters if not self._has_chapter_completion_event(item)),
                None,
            )
        page_number = None
        if chapter is not None and not self._chapter_completed(project, chapter):
            page_number = next(
                (
                    number
                    for number in sorted(chapter.page_numbers)
                    if project.page(number).state != PageState.APPROVED
                ),
                None,
            )
        workflow = dict(project.workflow)
        workflow["current_chapter"] = chapter.id if chapter else None
        workflow["current_page"] = page_number
        return project.model_copy(update={"workflow": workflow}, deep=True)

    def _record(self, project: Project, event: WorkflowEvent) -> Project:
        workflow = dict(project.workflow)
        history = [*workflow.get("history", []), self._history_entry(event)]
        workflow["history"] = history
        return project.model_copy(update={"workflow": workflow}, deep=True)

    @staticmethod
    def _history_entry(event: WorkflowEvent) -> dict[str, Any]:
        return {"event": str(event.event_type), "data": event.data}

    @staticmethod
    def _has_history_event(project: Project, event_type: EventType) -> bool:
        history = project.workflow.get("history", [])
        return any(item.get("event") == event_type.value for item in history)

    @staticmethod
    def _chapter_completed(project: Project, chapter: Chapter) -> bool:
        return bool(chapter.page_numbers) and all(
            project.page(page_number).state == PageState.APPROVED
            for page_number in chapter.page_numbers
        )

    @staticmethod
    def _has_chapter_completion_event(chapter: Chapter) -> bool:
        return any(
            item.get("event") == EventType.CHAPTER_COMPLETED.value for item in chapter.history
        )

    def _is_completed(self, project: Project) -> bool:
        return bool(project.chapters) and all(
            self._chapter_completed(project, chapter) for chapter in project.chapters
        )

    def _readiness(self, project: Project) -> list[PageReadinessInspection]:
        return [self._inspect_page(page) for page in sorted(project.pages, key=lambda page: page.page_number)]

    def _inspect_page(self, page: Page) -> PageReadinessInspection:
        unmet = tuple(
            field for field in _REQUIRED_EVIDENCE[page.state] if getattr(page, field) is None
        )
        if unmet:
            operation = "NO_OP_BLOCKED"
        elif page.state == PageState.APPROVED:
            operation = "NO_OP_TERMINAL"
        else:
            operation = self._state_machine.next_command(page.state)
        return PageReadinessInspection(
            page_number=page.page_number,
            current_state=page.state,
            unmet_prerequisites=unmet,
            next_operation=operation,
        )

    @staticmethod
    def _context(
        project: Project, page_readiness: list[PageReadinessInspection] | None = None
    ) -> ProjectContext:
        workflow = project.workflow
        return ProjectContext(
            project=project,
            chapters=project.chapters,
            metadata=dict(project.metadata),
            history=list(workflow.get("history", [])),
            current_chapter=workflow.get("current_chapter"),
            current_page=workflow.get("current_page"),
            page_readiness=page_readiness or [],
            readiness_summary=(
                ProjectWorkflowEngine._summarise_readiness(page_readiness)
                if page_readiness is not None
                else None
            ),
        )

    @staticmethod
    def _summarise_readiness(
        page_readiness: list[PageReadinessInspection],
    ) -> ProjectReadinessSummary:
        completed = actionable = blocked = 0
        next_page = None
        next_actionable_page: PageReadinessInspection | None = None
        first_blocked_page: PageReadinessInspection | None = None
        for inspection in page_readiness:
            if inspection.next_operation == "NO_OP_TERMINAL":
                completed += 1
            elif inspection.next_operation == "NO_OP_BLOCKED":
                blocked += 1
                if first_blocked_page is None:
                    first_blocked_page = inspection
            else:
                actionable += 1
                if next_page is None:
                    next_page = inspection.page_number
                    next_actionable_page = inspection
        summary = ProjectReadinessSummary(
            completed_page_count=completed,
            actionable_page_count=actionable,
            blocked_page_count=blocked,
            next_actionable_page_number=next_page,
            first_blocked_page=first_blocked_page if actionable == 0 else None,
            next_actionable_page=next_actionable_page,
            readiness_outcome=(
                "EMPTY"
                if not page_readiness
                else "ACTIONABLE"
                if actionable
                else "BLOCKED"
                if blocked
                else "COMPLETE"
            ),
        )
        return summary.model_copy(
            update={
                "readiness_focus_page": (
                    summary.next_actionable_page
                    if summary.readiness_outcome == "ACTIONABLE"
                    else summary.first_blocked_page
                    if summary.readiness_outcome == "BLOCKED"
                    else None
                ),
            }
        )
