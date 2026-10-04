"""Application service used by MCP Tool handlers; it delegates every workflow decision."""

from __future__ import annotations

from typing import Any

from manga_director.domain.exceptions import StateTransitionError
from manga_director.domain.state_machine import PageState
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.repositories.project_loader import ProjectLoader
from manga_director.repositories.protocols import ProjectRepository
from manga_director.workflow.coordinator import WorkflowCoordinator
from manga_director.workflow.durable_execution import (
    LogicalOutputAssetQualityGatePort,
    _route_localfile_primary,
)
from manga_director.workflow.engine import WorkflowEngine


class MangaApplicationService:
    """MCP-facing use cases with no Agent, provider, or StateMachine invocation."""

    def __init__(
        self,
        workflow_engine: WorkflowEngine,
        workflow_coordinator: WorkflowCoordinator,
        project_loader: ProjectLoader,
        repository: ProjectRepository,
        *,
        localfile_quality_gate: LogicalOutputAssetQualityGatePort | None = None,
    ) -> None:
        self._engine = workflow_engine
        self._coordinator = workflow_coordinator
        self._loader = project_loader
        self._repository = repository
        self._localfile_quality_gate = localfile_quality_gate

    def create_project(
        self, project_id: str, title: str, page_number: int, metadata: dict[str, Any]
    ) -> Any:
        context = self._coordinator.create_project(project_id, title, page_number)
        if metadata:
            project = self._repository.load(project_id)
            self._repository.save(
                project.model_copy(update={"metadata": {**project.metadata, **metadata}}, deep=True)
            )
            return self._coordinator.project_status(project_id)
        return context

    def list_projects(self) -> Any:
        return self._repository.list()

    def get_project(self, project_id: str) -> Any:
        return self._repository.load(project_id)

    def delete_project(self, project_id: str) -> None:
        self._repository.delete(project_id)

    def get_project_status(self, project_id: str) -> Any:
        return self._coordinator.project_status(project_id)

    def run_project(self, project_id: str) -> Any:
        return self._coordinator.run_project(project_id)

    def resume_project(self, project_id: str) -> Any:
        return self._coordinator.resume_project(project_id)

    def run_chapter(self, project_id: str, chapter_id: str) -> Any:
        return self._coordinator.run_chapter(project_id, chapter_id)

    def get_chapter_status(self, project_id: str, chapter_id: str) -> Any:
        return self._coordinator.chapter_status(project_id, chapter_id)

    def get_page_status(self, project_id: str, page_number: int) -> Any:
        return self._engine.status(self._loader.load(project_id, str(page_number)))

    def execute_page(
        self, command: str, project_id: str, page_number: int, metadata: dict[str, Any]
    ) -> Any:
        if isinstance(self._repository, LocalFileRepository):
            if self._localfile_quality_gate is None:
                return _route_localfile_primary(
                    self._engine,
                    self._repository,
                    project_id,
                    str(page_number),
                    command,
                    metadata,
                )
            return _route_localfile_primary(
                self._engine,
                self._repository,
                project_id,
                str(page_number),
                command,
                metadata,
                logical_output_asset_quality_gate=self._localfile_quality_gate,
            )
        context = self._loader.load(project_id, str(page_number))
        context = context.model_copy(
            update={"metadata": {**context.metadata, **metadata}}, deep=True
        )
        result = self._engine.execute_command(context, command)
        self._loader.save(project_id, str(page_number), result.context)
        return result

    def execute_support(
        self, name: str, project_id: str, page_number: int, metadata: dict[str, Any]
    ) -> Any:
        context = self._loader.load(project_id, str(page_number))
        context = context.model_copy(
            update={"metadata": {**context.metadata, **metadata}}, deep=True
        )
        result = self._engine.execute_support(context, name)
        self._loader.save(project_id, str(page_number), result.context)
        return result

    def approve_page(
        self, project_id: str, page_number: int, approved_by: str, metadata: dict[str, Any]
    ) -> Any:
        context = self._loader.load(project_id, str(page_number))
        if context.state != PageState.QUALITY_CHECKED:
            raise StateTransitionError("approve_page requires a QualityChecked page.")
        return self.execute_page(
            "approve",
            project_id,
            page_number,
            {**metadata, "approved_by": approved_by},
        )
