from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from manga_director.domain.events import WorkflowEvent
from manga_director.domain.exceptions import ProjectNotFoundError
from manga_director.domain.state_machine import PageState


class Page(BaseModel):
    """Persisted, page-at-a-time production state owned by a Project aggregate."""

    model_config = ConfigDict(frozen=True)

    page_number: int = Field(ge=1)
    state: PageState = PageState.DRAFT
    page_design: dict[str, Any] | None = None
    review: dict[str, Any] | None = None
    storyboard: dict[str, Any] | None = None
    dialogue: dict[str, Any] | None = None
    prompt: dict[str, Any] | None = None
    image: dict[str, Any] | None = None
    quality: dict[str, Any] | None = None
    continuity: dict[str, Any] | None = None
    approval: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    history: list[dict[str, Any]] = Field(default_factory=list)
    events: list[WorkflowEvent] = Field(default_factory=list)


class Chapter(BaseModel):
    """An ordered, persisted chapter boundary over a Project's page aggregate."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    page_numbers: list[int] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    history: list[dict[str, Any]] = Field(default_factory=list)


class Project(BaseModel):
    """The aggregate persisted by ProjectRepository implementations."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    chapters: list[Chapter] = Field(default_factory=list)
    pages: list[Page] = Field(default_factory=list)
    characters: list[dict[str, Any]] = Field(default_factory=list)
    workflow: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def page(self, page_number: int) -> Page:
        for page in self.pages:
            if page.page_number == page_number:
                return page
        raise ProjectNotFoundError(f"Page {page_number} does not exist in project '{self.id}'.")

    def replace_page(self, replacement: Page) -> Project:
        pages = [
            replacement if page.page_number == replacement.page_number else page
            for page in self.pages
        ]
        return self.model_copy(update={"pages": pages, "updated_at": datetime.now(UTC)}, deep=True)

    def add_page(self, page: Page) -> Project:
        if any(existing.page_number == page.page_number for existing in self.pages):
            raise ValueError(f"Page {page.page_number} already exists in project '{self.id}'.")
        return self.model_copy(
            update={"pages": [*self.pages, page], "updated_at": datetime.now(UTC)},
            deep=True,
        )

    def chapter(self, chapter_id: str) -> Chapter:
        for chapter in self.chapters:
            if chapter.id == chapter_id:
                return chapter
        raise ProjectNotFoundError(f"Chapter '{chapter_id}' does not exist in project '{self.id}'.")

    def replace_chapter(self, replacement: Chapter) -> Project:
        chapters = [
            replacement if chapter.id == replacement.id else chapter for chapter in self.chapters
        ]
        return self.model_copy(
            update={"chapters": chapters, "updated_at": datetime.now(UTC)},
            deep=True,
        )
