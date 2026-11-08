"""Transport-neutral workflow use cases shared by delivery adapters."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from manga_director.domain.exceptions import StateTransitionError, ValidationError
from manga_director.domain.state_machine import PageState
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.repositories.project_loader import ProjectLoader
from manga_director.repositories.protocols import ProjectRepository
from manga_director.workflow.coordinator import WorkflowCoordinator
from manga_director.workflow.durable_execution import (
    EvidenceLinkedApprovalGatePort,
    LogicalOutputAssetQualityGatePort,
    _route_localfile_primary,
    _route_localfile_storyboard_confirmation,
)
from manga_director.workflow.engine import WorkflowEngine


class WorkflowApplicationService:
    """Coordinate workflow use cases without owning transition decisions."""

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
        """Preserve the existing MCP use case; HTTP intentionally does not expose it."""

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
        if _contains_reserved_storyboard_authority(metadata) and not isinstance(
            self._repository, LocalFileRepository
        ):
            raise ValidationError("Reserved storyboard confirmation metadata is not accepted.")
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
        if _contains_reserved_storyboard_authority(context.metadata):
            raise ValidationError("Reserved storyboard confirmation metadata is not accepted.")
        context = context.model_copy(
            update={"metadata": {**context.metadata, **metadata}}, deep=True
        )
        result = self._engine.execute_command(context, command)
        self._loader.save(project_id, str(page_number), result.context)
        return result

    def _confirm_storyboard_input(
        self, project_id: str, page_number: int, request: dict[str, Any]
    ) -> Any:
        """Dedicated private confirmation entry point; unavailable to other repositories."""

        if type(self._repository) is not LocalFileRepository:
            raise StateTransitionError("Storyboard confirmation requires LocalFile.")
        return _route_localfile_storyboard_confirmation(
            self._engine,
            self._repository,
            project_id,
            str(page_number),
            request,
        )

    def execute_support(
        self, name: str, project_id: str, page_number: int, metadata: dict[str, Any]
    ) -> Any:
        if _contains_reserved_storyboard_authority(metadata):
            raise ValidationError("Reserved storyboard confirmation metadata is not accepted.")
        context = self._loader.load(project_id, str(page_number))
        if _contains_reserved_storyboard_authority(context.metadata):
            raise ValidationError("Reserved storyboard confirmation metadata is not accepted.")
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

    def _approve_page_with_evidence(
        self,
        project_id: str,
        page_number: int,
        approved_by: str,
        review_id: str,
        gate: EvidenceLinkedApprovalGatePort,
    ) -> Any:
        """Run the private LocalFile-only linked operation through the durable path."""

        if not isinstance(self._repository, LocalFileRepository):
            raise StateTransitionError(
                "evidence-linked approval requires a LocalFile repository."
            )
        return _route_localfile_primary(
            self._engine,
            self._repository,
            project_id,
            str(page_number),
            "approve",
            {
                "approved_by": approved_by,
                "review_evidence_id": review_id,
            },
            evidence_linked_approval_gate=gate,
        )


def _contains_reserved_storyboard_authority(value: Any) -> bool:
    """Reject the private capability key anywhere in caller or persisted metadata."""

    pending = [value]
    visited: set[int] = set()
    while pending:
        current = pending.pop()
        if isinstance(current, Mapping):
            if "_explicit_storyboard_input_authority" in current:
                return True
            identity = id(current)
            if identity not in visited:
                visited.add(identity)
                pending.extend(current.values())
        elif isinstance(current, (list, tuple)):
            identity = id(current)
            if identity not in visited:
                visited.add(identity)
                pending.extend(current)
    return False
