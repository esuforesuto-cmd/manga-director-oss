from __future__ import annotations

from pathlib import Path
from typing import Any

from manga_director.domain.exceptions import ProjectAlreadyExistsError
from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.repositories.database_factory import DatabaseFactory
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.repositories.protocols import ProjectRepository
from manga_director.repositories.serializer import ProjectSerializer, SerializationFormat
from manga_director.workflow.contracts import WorkflowContext


class ProjectLoader:
    """Maps persisted Project pages to WorkflowContext without workflow decisions."""

    def __init__(self, repository: ProjectRepository) -> None:
        self._repository = repository

    @property
    def repository(self) -> ProjectRepository:
        """Expose the persistence port for composition roots, never a concrete driver."""
        return self._repository

    @classmethod
    def from_settings(
        cls,
        driver: str,
        root: Path,
        format: SerializationFormat,
        base_directory: Path,
        database_provider: str | None = None,
        database_url: str | None = None,
    ) -> ProjectLoader:
        if database_provider is not None:
            if database_url is None:
                raise ValueError("database_url is required when database_provider is configured")
            repository = DatabaseFactory.create(database_provider, database_url)
            repository.create_schema()
            return cls(repository)
        if driver != "local_file":
            raise ValueError(f"Unsupported repository driver: {driver}")
        resolved_root = root if root.is_absolute() else base_directory / root
        return cls(LocalFileRepository(resolved_root, format=format))

    def create(self, project_id: str, title: str, page_number: int = 1) -> Project:
        if self._repository.exists(project_id):
            raise ProjectAlreadyExistsError(f"Project '{project_id}' already exists.")
        project = Project(id=project_id, title=title, pages=[Page(page_number=page_number)])
        self._repository.save(project)
        return project

    def open(self, project_id: str) -> Project:
        return self._repository.load(project_id)

    def list(self) -> list[Project]:
        return self._repository.list()

    def delete(self, project_id: str) -> None:
        self._repository.delete(project_id)

    def export(self, project_id: str, destination: Path) -> None:
        project = self._repository.load(project_id)
        serializer = ProjectSerializer.for_path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(serializer.dumps(project), encoding="utf-8")

    def import_(self, source: Path) -> Project:
        serializer = ProjectSerializer.for_path(source)
        project = serializer.loads(source.read_text(encoding="utf-8"))
        if self._repository.exists(project.id):
            raise ProjectAlreadyExistsError(f"Project '{project.id}' already exists.")
        self._repository.save(project)
        return project

    def initialize(self, project_id: str, page_id: str) -> WorkflowContext:
        project = self.create(project_id, project_id, int(page_id))
        return self._context_from_page(project, project.page(int(page_id)))

    def load(self, project_id: str, page_id: str) -> WorkflowContext:
        project = self._repository.load(project_id)
        return self._context_from_page(project, project.page(int(page_id)))

    def save(self, project_id: str, page_id: str, context: WorkflowContext) -> None:
        project = self._repository.load(project_id)
        page = self._page_from_context(project.page(int(page_id)), context)
        self._repository.save(project.replace_page(page))

    @staticmethod
    def _context_from_page(project: Project, page: Page) -> WorkflowContext:
        artifacts: dict[str, Any] = {}
        mapping = {
            PageState.DESIGNED: page.page_design,
            PageState.REVIEWED: page.review,
            PageState.STORYBOARDED: page.storyboard,
            PageState.PROMPT_BUILT: page.prompt,
            PageState.GENERATED: page.image,
            PageState.QUALITY_CHECKED: page.quality,
            PageState.APPROVED: page.approval,
        }
        for state, value in mapping.items():
            if value is not None:
                artifacts[state.value] = value
        if page.dialogue is not None:
            artifacts["support:dialogue"] = page.dialogue
        if page.continuity is not None:
            artifacts["support:continuity"] = page.continuity
        return WorkflowContext(
            page={"project_id": project.id, "page_id": str(page.page_number)},
            state=page.state,
            events=page.events,
            artifacts=artifacts,
            metadata=page.metadata | {"workflow_history": page.history},
        )

    @staticmethod
    def _page_from_context(page: Page, context: WorkflowContext) -> Page:
        artifacts = context.artifacts
        metadata = dict(context.metadata)
        history = list(metadata.pop("workflow_history", []))
        metadata.pop("current_step", None)
        return page.model_copy(
            update={
                "state": context.state,
                "page_design": artifacts.get(PageState.DESIGNED.value),
                "review": artifacts.get(PageState.REVIEWED.value),
                "storyboard": artifacts.get(PageState.STORYBOARDED.value),
                "dialogue": artifacts.get("support:dialogue"),
                "prompt": artifacts.get(PageState.PROMPT_BUILT.value),
                "image": artifacts.get(PageState.GENERATED.value),
                "quality": artifacts.get(PageState.QUALITY_CHECKED.value),
                "continuity": artifacts.get("support:continuity"),
                "approval": artifacts.get(PageState.APPROVED.value),
                "metadata": metadata,
                "history": history,
                "events": context.events,
            },
            deep=True,
        )
