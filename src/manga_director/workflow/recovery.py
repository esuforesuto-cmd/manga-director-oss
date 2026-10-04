"""Failure-safe page workflow recovery through existing Engine and Repository ports."""

from __future__ import annotations

from typing import TYPE_CHECKING

from manga_director.workflow.contracts import WorkflowResult, WorkflowStatus
from manga_director.workflow.engine import WorkflowEngine

if TYPE_CHECKING:
    from manga_director.repositories.project_loader import ProjectLoader


class WorkflowRecovery:
    """Resume exactly one persisted page step, saving only after a successful result."""

    def __init__(self, engine: WorkflowEngine, loader: ProjectLoader) -> None:
        self._engine = engine
        self._loader = loader

    def status(self, project_id: str, page_number: int) -> WorkflowStatus:
        return self._engine.status(self._loader.load(project_id, str(page_number)))

    def resume_step(self, project_id: str, page_number: int) -> WorkflowResult:
        """Execute the next legal step; failures leave the persisted page untouched."""

        context = self._loader.load(project_id, str(page_number))
        result = self._engine.execute(context)
        self._loader.save(project_id, str(page_number), result.context)
        return result
