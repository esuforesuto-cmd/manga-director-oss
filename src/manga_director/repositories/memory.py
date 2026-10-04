from builtins import list as builtin_list

from manga_director.domain.exceptions import ProjectNotFoundError
from manga_director.domain.project import Page, Project
from manga_director.observability.repository import RepositoryMetrics
from manga_director.repositories.protocols import ProjectRepository
from manga_director.repositories.queries import ProjectMetadata, page_history_slice
from manga_director.repositories.validator import ProjectValidator


class InMemoryRepository(ProjectRepository):
    """Dictionary-backed repository for isolated unit tests."""

    def __init__(
        self,
        validator: ProjectValidator | None = None,
        *,
        metrics: RepositoryMetrics | None = None,
    ) -> None:
        self._validator = validator or ProjectValidator()
        self._projects: dict[str, Project] = {}
        self.metrics = metrics or RepositoryMetrics()

    def load(self, project_id: str) -> Project:
        return self.metrics.measure("load", lambda: self._load(project_id))

    def _load(self, project_id: str) -> Project:
        try:
            return self._projects[project_id].model_copy(deep=True)
        except KeyError as exc:
            raise ProjectNotFoundError(f"Project '{project_id}' does not exist.") from exc

    def save(self, project: Project) -> None:
        self.metrics.measure("save", lambda: self._save(project))

    def _save(self, project: Project) -> None:
        self._validator.validate(project)
        if self._projects.get(project.id) == project:
            return
        self._projects[project.id] = project.model_copy(deep=True)

    def exists(self, project_id: str) -> bool:
        return self.metrics.measure("exists", lambda: project_id in self._projects)

    def delete(self, project_id: str) -> None:
        self.metrics.measure("delete", lambda: self._delete(project_id))

    def _delete(self, project_id: str) -> None:
        if project_id not in self._projects:
            raise ProjectNotFoundError(f"Project '{project_id}' does not exist.")
        del self._projects[project_id]

    def list(self) -> list[Project]:
        return self.metrics.measure(
            "list",
            lambda: [self._projects[key].model_copy(deep=True) for key in sorted(self._projects)],
        )

    def list_metadata(
        self, *, offset: int = 0, limit: int | None = None
    ) -> builtin_list[ProjectMetadata]:
        return self.metrics.measure("list_metadata", lambda: self._list_metadata(offset, limit))

    def _list_metadata(self, offset: int, limit: int | None) -> builtin_list[ProjectMetadata]:
        _validate_window(offset, limit)
        ids = sorted(self._projects)[offset : None if limit is None else offset + limit]
        return [
            ProjectMetadata(
                id=project.id,
                title=project.title,
                page_count=len(project.pages),
                chapter_count=len(project.chapters),
                updated_at=project.updated_at,
            )
            for project in (self._projects[project_id] for project_id in ids)
        ]

    def load_page(self, project_id: str, page_number: int) -> Page:
        return self.metrics.measure("load_page", lambda: self._load(project_id).page(page_number))

    def load_history(
        self,
        project_id: str,
        page_number: int,
        *,
        offset: int = 0,
        limit: int | None = None,
    ) -> builtin_list[dict[str, object]]:
        return self.metrics.measure(
            "load_history",
            lambda: page_history_slice(
                self._load(project_id).page(page_number).history, offset=offset, limit=limit
            ),
        )


def _validate_window(offset: int, limit: int | None) -> None:
    if offset < 0 or (limit is not None and limit < 0):
        raise ValueError("offset and limit must be non-negative")
