"""Deterministic, page-number ordered planning for BatchWorkflowEngine."""

from __future__ import annotations

from uuid import uuid4

from manga_director.domain.project import Project
from manga_director.domain.state_machine import PageState
from manga_director.workflow.batch_contracts import (
    BatchRecord,
    ExecutionPolicy,
    QueueItem,
)


class ExecutionPlanner:
    """Collect eligible project pages and express their sequential dependencies."""

    def plan(
        self,
        project: Project,
        policy: ExecutionPolicy,
        *,
        batch_id: str | None = None,
        chapter_ids: list[str] | None = None,
    ) -> BatchRecord:
        selected_chapters = [
            chapter
            for chapter in project.chapters
            if chapter_ids is None or chapter.id in chapter_ids
        ]
        page_chapters = {
            page_number: chapter.id
            for chapter in selected_chapters
            for page_number in chapter.page_numbers
        }
        eligible_pages = sorted(
            page_number
            for page_number in page_chapters
            if project.page(page_number).state
            not in {PageState.QUALITY_CHECKED, PageState.APPROVED}
        )
        queue: list[QueueItem] = []
        predecessor: int | None = None
        for page_number in eligible_pages:
            queue.append(
                QueueItem(
                    page_number=page_number,
                    chapter_id=page_chapters[page_number],
                    dependencies=[] if predecessor is None else [predecessor],
                )
            )
            predecessor = page_number
        return BatchRecord(
            id=batch_id or f"batch-{uuid4().hex[:12]}",
            project_id=project.id,
            chapter_ids=[chapter.id for chapter in selected_chapters],
            policy=policy.name,
            queue=queue,
        )
