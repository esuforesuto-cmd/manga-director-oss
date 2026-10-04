"""Chapter-level ordering, progress, review, and lifecycle events."""

from __future__ import annotations

from collections.abc import Callable

from manga_director.domain.events import EventType, WorkflowEvent
from manga_director.domain.project import Chapter, Project
from manga_director.domain.state_machine import PageState
from manga_director.events.bus import EventBus
from manga_director.repositories.protocols import ProjectRepository
from manga_director.workflow.contracts import WorkflowContext
from manga_director.workflow.hierarchy_contracts import ChapterContext, ChapterWorkflowResult
from manga_director.workflow.scheduler import WorkflowScheduler

PageWorkflowRunner = Callable[[str, int], WorkflowContext]


class ChapterWorkflowEngine:
    """Schedule at most one page; child workflow execution is injected by a coordinator."""

    def __init__(
        self, repository: ProjectRepository, event_bus: EventBus, scheduler: WorkflowScheduler
    ) -> None:
        self._repository = repository
        self._event_bus = event_bus
        self._scheduler = scheduler

    def status(self, project_id: str, chapter_id: str) -> ChapterContext:
        return self._context(self._repository.load(project_id), chapter_id)

    def review(self, project_id: str, chapter_id: str) -> ChapterContext:
        """Record a chapter review summary without advancing any page state."""
        project = self._repository.load(project_id)
        context = self._context(project, chapter_id)
        chapter = context.chapter
        review = {
            "page_count": len(context.pages),
            "approved_pages": sum(page.state == PageState.APPROVED for page in context.pages),
            "complete": self._completed(context),
        }
        updated = chapter.model_copy(
            update={
                "metadata": {**chapter.metadata, "review": review},
                "history": [*chapter.history, {"action": "review", "summary": review}],
            },
            deep=True,
        )
        self._repository.save(project.replace_chapter(updated))
        return self._context(self._repository.load(project_id), chapter_id)

    def run(
        self, project_id: str, chapter_id: str, page_runner: PageWorkflowRunner
    ) -> ChapterWorkflowResult:
        """Run exactly one scheduled page workflow and persist chapter progress."""
        project = self._repository.load(project_id)
        context = self._context(project, chapter_id)
        events: list[WorkflowEvent] = []
        if not self._has_event(context.chapter, EventType.CHAPTER_STARTED):
            started = WorkflowEvent(
                event_type=EventType.CHAPTER_STARTED,
                data={"project_id": project_id, "chapter_id": chapter_id},
            )
            project = self._record(project, context.chapter, started)
            self._repository.save(project)
            self._event_bus.publish([started])
            events.append(started)
            context = self._context(project, chapter_id)

        page = self._scheduler.next_page(context)
        if page is None:
            return self._complete(project, chapter_id, events)

        page_context = page_runner(project_id, page.page_number)
        project = self._repository.load(project_id)
        context = self._context(project, chapter_id)
        chapter = context.chapter.model_copy(
            update={
                "metadata": {**context.chapter.metadata, "current_page": page.page_number},
                "history": [
                    *context.chapter.history,
                    {
                        "action": "page_run",
                        "page_number": page.page_number,
                        "state": page_context.state.value,
                    },
                ],
            },
            deep=True,
        )
        project = project.replace_chapter(chapter)
        self._repository.save(project)
        return self._complete(project, chapter_id, events, page_context)

    def _complete(
        self,
        project: Project,
        chapter_id: str,
        events: list[WorkflowEvent],
        page_context: WorkflowContext | None = None,
    ) -> ChapterWorkflowResult:
        context = self._context(project, chapter_id)
        completed = self._completed(context)
        if completed and context.current_page is not None:
            cleared = context.chapter.model_copy(
                update={"metadata": {**context.chapter.metadata, "current_page": None}},
                deep=True,
            )
            project = project.replace_chapter(cleared)
            self._repository.save(project)
            context = self._context(project, chapter_id)
        if completed and not self._has_event(context.chapter, EventType.CHAPTER_COMPLETED):
            event = WorkflowEvent(
                event_type=EventType.CHAPTER_COMPLETED,
                data={"project_id": project.id, "chapter_id": chapter_id},
            )
            project = self._record(project, context.chapter, event)
            self._repository.save(project)
            self._event_bus.publish([event])
            events.append(event)
            context = self._context(project, chapter_id)
        return ChapterWorkflowResult(
            context=context,
            page_context=page_context,
            completed=completed,
            events=events,
            messages=["chapter workflow completed" if completed else "one page workflow executed"],
        )

    @staticmethod
    def _has_event(chapter: Chapter, event_type: EventType) -> bool:
        return any(item.get("event") == event_type.value for item in chapter.history)

    @staticmethod
    def _record(project: Project, chapter: Chapter, event: WorkflowEvent) -> Project:
        updated = chapter.model_copy(
            update={
                "history": [
                    *chapter.history,
                    {"event": str(event.event_type), "data": event.data},
                ]
            },
            deep=True,
        )
        return project.replace_chapter(updated)

    @staticmethod
    def _completed(context: ChapterContext) -> bool:
        return bool(context.pages) and all(
            page.state == PageState.APPROVED for page in context.pages
        )

    @staticmethod
    def _context(project: Project, chapter_id: str) -> ChapterContext:
        chapter = project.chapter(chapter_id)
        pages = sorted(
            (project.page(number) for number in chapter.page_numbers),
            key=lambda item: item.page_number,
        )
        return ChapterContext(
            chapter=chapter,
            pages=pages,
            metadata=dict(chapter.metadata),
            history=list(chapter.history),
            current_page=chapter.metadata.get("current_page"),
        )
