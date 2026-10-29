"""Dependency-injection composition for the local workflow HTTP adapter."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from manga_director.api.workflow import create_workflow_app
from manga_director.application import build_workflow_application
from manga_director.application.approved_asset_download import (
    attach_approved_asset_download,
    build_approved_asset_download,
)
from manga_director.application.evidence_linked_approval import (
    attach_evidence_linked_approval,
    build_evidence_linked_approval,
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
from manga_director.production.next_generation_page_generation_plan import PanelRectangle
from manga_director.production.next_generation_page_output_proof import (
    PageOutputResolverPort,
)
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.repositories.project_loader import ProjectLoader
from manga_director.repositories.protocols import ProjectRepository
from manga_director.workflow.coordinator import WorkflowCoordinator
from manga_director.workflow.durable_execution import (
    LogicalOutputAssetQualityGatePort,
)
from manga_director.workflow.engine import WorkflowEngine
from manga_director.workflow.localfile_page_output_proof_bridge import (
    build_localfile_page_output_proof_bridge,
)
from manga_director.workflow.localfile_panel_aware_generation_activation import (
    LocalFilePanelAwareActivationResult,
    execute_localfile_panel_aware_generation,
)


def build_workflow_app(
    *,
    workflow_engine: WorkflowEngine,
    workflow_coordinator: WorkflowCoordinator,
    project_loader: ProjectLoader,
    repository: ProjectRepository,
) -> Any:
    """Compose the shared Application Service and optional FastAPI delivery."""

    page_output_proof: PageOutputResolverPort | None = None
    localfile_quality_gate_factory: (
        Callable[[LocalFileRepository], LogicalOutputAssetQualityGatePort] | None
    ) = None
    if isinstance(repository, LocalFileRepository):
        page_output_proof, quality_gate = build_localfile_page_output_proof_bridge(repository)

        def localfile_quality_gate_factory(
            _repository: LocalFileRepository,
        ) -> LogicalOutputAssetQualityGatePort:
            return quality_gate
    application = build_workflow_application(
        workflow_engine=workflow_engine,
        workflow_coordinator=workflow_coordinator,
        project_loader=project_loader,
        repository=repository,
        **({"localfile_quality_gate_factory": localfile_quality_gate_factory}
           if localfile_quality_gate_factory is not None else {}),
    )
    panel_aware_activation = None
    if isinstance(repository, LocalFileRepository):
        human_visual_review_readiness = build_human_visual_review_readiness(
            repository, page_output_resolver=page_output_proof
        )
        attach_approved_asset_download(
            application,
            build_approved_asset_download(repository, page_output_proof),
        )
        attach_generated_asset_presentation(
            application,
            build_generated_asset_presentation(
                repository, page_output_resolver=page_output_proof
            ),
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
        attach_evidence_linked_approval(
            application,
            build_evidence_linked_approval(
                repository,
                application,
                human_visual_review_readiness,
            ),
        )

        if type(repository) is LocalFileRepository:

            def activate_panel_aware_generation(
                project_id: str,
                page_number: int,
                authorized_by: str,
                checkpoint_name: str,
                rectangles: tuple[PanelRectangle, ...],
                layout_profile_id: str,
                layout_profile_version: int,
            ) -> LocalFilePanelAwareActivationResult:
                return execute_localfile_panel_aware_generation(
                    repository,
                    workflow_engine,
                    project_id,
                    page_number,
                    authorized_by,
                    checkpoint_name,
                    rectangles,
                    layout_profile_id=layout_profile_id,
                    layout_profile_version=layout_profile_version,
                )

            panel_aware_activation = activate_panel_aware_generation
    return create_workflow_app(
        application,
        panel_aware_activation=panel_aware_activation,
    )
