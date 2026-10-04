"""Replaceable scheduling port; v1 hierarchy uses page-number order only."""

from __future__ import annotations

from typing import Protocol

from manga_director.domain.project import Page
from manga_director.domain.state_machine import PageState
from manga_director.workflow.hierarchy_contracts import ChapterContext


class WorkflowScheduler(Protocol):
    """Select the next eligible page without executing workflow logic."""

    def next_page(self, context: ChapterContext) -> Page | None: ...


class PageNumberWorkflowScheduler:
    """Select the first non-approved Chapter page by ascending page number."""

    def next_page(self, context: ChapterContext) -> Page | None:
        return next(
            (
                page
                for page in sorted(context.pages, key=lambda item: item.page_number)
                if page.state != PageState.APPROVED
            ),
            None,
        )
