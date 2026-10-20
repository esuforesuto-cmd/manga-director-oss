"""Dependency-injection composition for the local workflow HTTP adapter."""

from __future__ import annotations

from typing import Any

from manga_director.api.workflow import create_workflow_app
from manga_director.application import build_workflow_application
from manga_director.application.approved_asset_download import (
    attach_approved_asset_download,
    build_approved_asset_download,
)
from manga_director.application.generated_asset_presentation import (
    attach_generated_asset_presentation,
    build_generated_asset_presentation,
)
from manga_director.application.human_visual_review_evidence import (
    attach_human_visual_review_evidence,
    build_human_visual_review_evidence,
)
from manga_director.application.human_visual_review_evidence_history import (
    attach_human_visual_review_evidence_history,
    build_human_visual_review_evidence_history,
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
        human_visual_review_readiness = build_human_visual_review_readiness(repository)
        attach_approved_asset_download(
            application,
            build_approved_asset_download(repository),
        )
        attach_generated_asset_presentation(
            application,
            build_generated_asset_presentation(repository),
        )
        attach_human_visual_review_readiness(
            application,
            human_visual_review_readiness,
        )
        attach_human_visual_review_evidence(
            application,
            build_human_visual_review_evidence(
                repository,
                human_visual_review_readiness,
            ),
        )
        attach_human_visual_review_evidence_history(
            application,
            build_human_visual_review_evidence_history(repository),
        )
    return create_workflow_app(application)
