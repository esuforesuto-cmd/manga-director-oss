"""Optional, backward-compatible read optimizations for Project repositories."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from manga_director.domain.project import Page


class ProjectMetadata(BaseModel):
    """Small Project listing record that does not require aggregate consumers."""

    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    page_count: int = Field(ge=0)
    chapter_count: int = Field(ge=0)
    updated_at: datetime


class ProjectQueryRepository(Protocol):
    """Optional read-side capability; ProjectRepository itself remains unchanged."""

    def list_metadata(
        self, *, offset: int = 0, limit: int | None = None
    ) -> list[ProjectMetadata]: ...

    def load_page(self, project_id: str, page_number: int) -> Page: ...

    def load_history(
        self,
        project_id: str,
        page_number: int,
        *,
        offset: int = 0,
        limit: int | None = None,
    ) -> list[dict[str, Any]]: ...


def page_history_slice(
    history: list[dict[str, Any]], *, offset: int = 0, limit: int | None = None
) -> list[dict[str, Any]]:
    """Validate simple pagination and return an isolated history window."""

    if offset < 0:
        raise ValueError("offset must be non-negative")
    if limit is not None and limit < 0:
        raise ValueError("limit must be non-negative")
    end = None if limit is None else offset + limit
    return [dict(entry) for entry in history[offset:end]]
