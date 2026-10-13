"""Dependency-injection composition for the local workflow HTTP adapter."""

from __future__ import annotations

from typing import Any

from manga_director.api.workflow import create_workflow_app
from manga_director.application import build_workflow_application
from manga_director.repositories.project_loader import ProjectLoader
from manga_director.repositories.protocols import ProjectRepository
from manga_director.workflow.coordinator import WorkflowCoordinator
from manga_director.workflow.engine import WorkflowEngine


def build_workflow_app(
    *,
    workflow_engine: WorkflowEngine,
    workflow_coordinator: WorkflowCoordinator,
    project_loader: ProjectLoader,
    repository: ProjectRepository,
) -> Any:
    """Compose the shared Application Service and optional FastAPI delivery."""

    application = build_workflow_application(
        workflow_engine=workflow_engine,
        workflow_coordinator=workflow_coordinator,
        project_loader=project_loader,
        repository=repository,
    )
    return create_workflow_app(application)
