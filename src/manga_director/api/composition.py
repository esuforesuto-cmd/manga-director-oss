"""Dependency-injection composition for the local workflow HTTP adapter."""

from __future__ import annotations

from typing import Any

from manga_director.api.workflow import create_workflow_app
from manga_director.application import build_workflow_application
from manga_director.application.generated_asset_presentation import (
    attach_generated_asset_presentation,
    build_generated_asset_presentation,
)
from manga_director.application.human_visual_review_readiness import (
    attach_human_visual_review_readiness,
    build_human_visual_review_readiness,
)
from manga_director.repositories.local_file import LocalFileRepository
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
    if isinstance(repository, LocalFileRepository):
        attach_generated_asset_presentation(
            application,
            build_generated_asset_presentation(repository),
        )
        attach_human_visual_review_readiness(
            application,
            build_human_visual_review_readiness(repository),
        )
    return create_workflow_app(application)
