"""Read-side scalability helpers built solely on the repository port."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from manga_director.domain.project import Project
from manga_director.repositories.protocols import ProjectRepository


class RepositoryIndex(BaseModel):
    """A compact, transport-neutral index for a persisted project."""

    model_config = ConfigDict(frozen=True)

    project_id: str
    chapters: dict[str, tuple[int, ...]] = Field(default_factory=dict)
    pages: dict[int, str] = Field(default_factory=dict)
    metadata_keys: tuple[str, ...] = ()
    snapshot_keys: tuple[str, ...] = ()


class HistoryPage(BaseModel):
    """A bounded history window that avoids loading consumer-owned copies."""

    model_config = ConfigDict(frozen=True)

    project_id: str
    page_number: int
    offset: int = Field(ge=0)
    limit: int = Field(gt=0)
    total: int = Field(ge=0)
    entries: tuple[dict[str, Any], ...] = ()


class ProjectScanSummary(BaseModel):
    """Safe aggregate counts for large-project diagnostics."""

    model_config = ConfigDict(frozen=True)

    project_id: str
    chapters: int = Field(ge=0)
    pages: int = Field(ge=0)
    history_entries: int = Field(ge=0)
    metadata_keys: int = Field(ge=0)
    snapshots: int = Field(ge=0)


class RepositoryScalability:
    """Optional indexed reads without expanding :class:`ProjectRepository`.

    The helper owns only compact, invalidatable index data.  Existing callers may
    continue to use ``load`` and ``list`` unchanged.
    """

    def __init__(self, repository: ProjectRepository) -> None:
        self._repository = repository
        self._indexes: dict[str, RepositoryIndex] = {}

    def invalidate(self, project_id: str | None = None) -> None:
        """Discard cached indexes after a repository write or controlled reload."""

        if project_id is None:
            self._indexes.clear()
        else:
            self._indexes.pop(project_id, None)

    def project_index(self, project_id: str, *, refresh: bool = False) -> RepositoryIndex:
        if not refresh and (cached := self._indexes.get(project_id)) is not None:
            return cached
        project = self._repository.load(project_id)
        index = self._build_index(project)
        self._indexes[project_id] = index
        return index

    def chapter_index(self, project_id: str, *, refresh: bool = False) -> dict[str, tuple[int, ...]]:
        return dict(self.project_index(project_id, refresh=refresh).chapters)

    def page_index(self, project_id: str, *, refresh: bool = False) -> dict[int, str]:
        return dict(self.project_index(project_id, refresh=refresh).pages)

    def metadata_cache(self, project_id: str, *, refresh: bool = False) -> tuple[str, ...]:
        return self.project_index(project_id, refresh=refresh).metadata_keys

    def snapshot_index(self, project_id: str, *, refresh: bool = False) -> tuple[str, ...]:
        return self.project_index(project_id, refresh=refresh).snapshot_keys

    def history_page(
        self, project_id: str, page_number: int, *, offset: int = 0, limit: int = 50
    ) -> HistoryPage:
        if offset < 0 or limit <= 0:
            raise ValueError("offset must be non-negative and limit must be positive")
        page = self._repository.load(project_id).page(page_number)
        entries = tuple(dict(entry) for entry in page.history[offset : offset + limit])
        return HistoryPage(
            project_id=project_id,
            page_number=page_number,
            offset=offset,
            limit=limit,
            total=len(page.history),
            entries=entries,
        )

    def scan(self, project_id: str) -> ProjectScanSummary:
        project = self._repository.load(project_id)
        index = self.project_index(project_id, refresh=True)
        return ProjectScanSummary(
            project_id=project.id,
            chapters=len(project.chapters),
            pages=len(project.pages),
            history_entries=sum(len(page.history) for page in project.pages),
            metadata_keys=len(index.metadata_keys),
            snapshots=len(index.snapshot_keys),
        )

    def iter_projects(self, *, batch_size: int = 100) -> Iterator[tuple[Project, ...]]:
        """Yield bounded listing batches for callers that scan many projects."""

        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        projects = self._repository.list()
        for start in range(0, len(projects), batch_size):
            yield tuple(projects[start : start + batch_size])

    @staticmethod
    def _build_index(project: Project) -> RepositoryIndex:
        snapshot_keys = tuple(
            sorted(key for key in project.workflow if "snapshot" in key.lower())
        )
        return RepositoryIndex(
            project_id=project.id,
            chapters={chapter.id: tuple(chapter.page_numbers) for chapter in project.chapters},
            pages={page.page_number: page.state.value for page in project.pages},
            metadata_keys=tuple(sorted(project.metadata)),
            snapshot_keys=snapshot_keys,
        )
