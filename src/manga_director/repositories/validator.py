from __future__ import annotations

import re

from manga_director.domain.exceptions import ValidationError
from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState


class ProjectValidator:
    """Validates persisted aggregate invariants before a repository save."""

    _required_fields: dict[PageState, str] = {
        PageState.DESIGNED: "page_design",
        PageState.REVIEWED: "review",
        PageState.STORYBOARDED: "storyboard",
        PageState.PROMPT_BUILT: "prompt",
        PageState.GENERATED: "image",
        PageState.QUALITY_CHECKED: "quality",
        PageState.APPROVED: "approval",
    }
    _states = list(PageState)

    def validate(self, project: Project) -> None:
        if not project.id.strip():
            raise ValidationError("Project ID is required.")
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", project.id) is None:
            raise ValidationError(
                "Project ID may contain only letters, numbers, hyphens, and underscores."
            )
        if not project.title.strip():
            raise ValidationError("Project title is required.")
        numbers = [page.page_number for page in project.pages]
        if len(numbers) != len(set(numbers)):
            raise ValidationError("Page numbers must be unique.")
        for page in project.pages:
            self._validate_page(page)
        chapter_ids = [chapter.id for chapter in project.chapters]
        if len(chapter_ids) != len(set(chapter_ids)):
            raise ValidationError("Chapter IDs must be unique.")
        known_pages = set(numbers)
        for chapter in project.chapters:
            if not chapter.page_numbers:
                raise ValidationError(f"Chapter '{chapter.id}' requires at least one page.")
            unknown_pages = sorted(set(chapter.page_numbers) - known_pages)
            if unknown_pages:
                rendered_pages = ", ".join(map(str, unknown_pages))
                raise ValidationError(
                    f"Chapter '{chapter.id}' references unknown pages: {rendered_pages}."
                )

    def _validate_page(self, page: Page) -> None:
        state_index = self._states.index(page.state)
        for state, field in self._required_fields.items():
            if self._states.index(state) <= state_index and getattr(page, field) is None:
                raise ValidationError(
                    f"Page {page.page_number} at {page.state.value} requires '{field}'."
                )
