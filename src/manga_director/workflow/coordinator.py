"""Thin Project -> Chapter -> Page workflow coordinator."""

from __future__ import annotations

from typing import Protocol

from manga_director.workflow.chapter_engine import ChapterWorkflowEngine
from manga_director.workflow.contracts import WorkflowContext
from manga_director.workflow.engine import WorkflowEngine
from manga_director.workflow.hierarchy_contracts import (
    ChapterContext,
    ProjectContext,
    ProjectWorkflowResult,
)
from manga_director.workflow.project_engine import ProjectWorkflowEngine


class PageContextStore(Protocol):
    """Persistence boundary needed to map an aggregate page to a page workflow context."""

    def load(self, project_id: str, page_id: str) -> WorkflowContext: ...

    def save(self, project_id: str, page_id: str, context: WorkflowContext) -> None: ...


class WorkflowCoordinator:
    """Delegate hierarchy calls only; state and scheduling live in the workflow engines."""

    def __init__(
        self,
        project_engine: ProjectWorkflowEngine,
        chapter_engine: ChapterWorkflowEngine,
        page_engine: WorkflowEngine,
        page_store: PageContextStore,
    ) -> None:
        self._project_engine = project_engine
        self._chapter_engine = chapter_engine
        self._page_engine = page_engine
        self._page_store = page_store

    def create_project(self, project_id: str, title: str, page_number: int = 1) -> ProjectContext:
        return self._project_engine.create(project_id, title, page_number)

    def run_project(self, project_id: str) -> ProjectWorkflowResult:
        started = self._project_engine.start(project_id)
        if started.context.current_chapter is None:
            return self._project_engine.refresh(project_id)
        chapter = self._chapter_engine.run(
            project_id, started.context.current_chapter, self._run_page
        )
        refreshed = self._project_engine.refresh(project_id)
        return refreshed.model_copy(
            update={
                "chapter_result": chapter,
                "events": [*started.events, *chapter.events, *refreshed.events],
            },
            deep=True,
        )

    def resume_project(self, project_id: str) -> ProjectWorkflowResult:
        return self.run_project(project_id)

    def run_chapter(self, project_id: str, chapter_id: str) -> ProjectWorkflowResult:
        started = self._project_engine.start(project_id)
        chapter = self._chapter_engine.run(project_id, chapter_id, self._run_page)
        refreshed = self._project_engine.refresh(project_id)
        return refreshed.model_copy(
            update={
                "chapter_result": chapter,
                "events": [*started.events, *chapter.events, *refreshed.events],
            },
            deep=True,
        )

    def project_status(self, project_id: str) -> ProjectContext:
        """Return the Project engine's read-only persisted-page inspection."""
        return self._project_engine.status(project_id)

    def chapter_status(self, project_id: str, chapter_id: str) -> ChapterContext:
        return self._chapter_engine.status(project_id, chapter_id)

    def _run_page(self, project_id: str, page_number: int) -> WorkflowContext:
        context = self._page_store.load(project_id, str(page_number))
        results = self._page_engine.run(context)
        final_context = results[-1].context if results else context
        self._page_store.save(project_id, str(page_number), final_context)
        return final_context
