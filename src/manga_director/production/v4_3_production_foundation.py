"""v4.3 Creative Production Platform foundation DTOs without side effects.

This Application-layer module creates immutable, exactly-one-Page-scoped
production, asset, workspace, and deliverable projections. It does not mutate
Projects or repositories, transition workflows, assign tasks, create assets,
export artifacts, publish or distribute deliverables, or call external systems.
The domain StateMachine remains the sole workflow-transition authority.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.domain.state_machine import PageState
from manga_director.production.director import DirectorModel
from manga_director.workflow.contracts import WorkflowContext


class ProductionProjectDTO(DirectorModel):
    """Read-only production identity for exactly one existing Page."""

    project_id: str
    page_reference: str
    current_state: PageState
    page_count: Literal[1] = 1
    lifecycle_state: Literal["observed"] = "observed"
    project_persisted: bool = False


class ProductionStageDTO(DirectorModel):
    project_id: str
    page_reference: str
    workflow_state: PageState
    stage_name: str
    stage_started: bool = False
    stage_completed: bool = False
    transition_requested: bool = False


class ProductionMilestoneDTO(DirectorModel):
    milestone_id: str
    project_id: str
    page_reference: str
    status: Literal["defined"] = "defined"
    completed: bool = False
    milestone_persisted: bool = False


class ProductionDeliverableDTO(DirectorModel):
    deliverable_id: str
    project_id: str
    page_reference: str
    readiness: Literal["evidence_only"] = "evidence_only"
    artifact_created: bool = False
    human_release_review_required: bool = True


class PipelineSummary(DirectorModel):
    project_count: int = Field(default=1, ge=0)
    page_count: Literal[1] = 1
    observed_stage_count: int = Field(default=1, ge=0)
    completed_stage_count: int = 0
    workflow_changed: bool = False
    automatic_action_taken: bool = False


class ProductionPipelineFoundationReport(DirectorModel):
    project: ProductionProjectDTO
    stage: ProductionStageDTO
    milestone: ProductionMilestoneDTO
    deliverable: ProductionDeliverableDTO
    summary: PipelineSummary
    planning_only: bool = True


class V43AssetDTO(DirectorModel):
    asset_id: str
    project_id: str
    page_reference: str
    category: Literal["workflow_evidence"] = "workflow_evidence"
    asset_created: bool = False
    asset_persisted: bool = False


class V43AssetVersionDTO(DirectorModel):
    asset_id: str
    version_id: str
    revision: int = Field(default=0, ge=0)
    version_created: bool = False
    version_replaced: bool = False


class V43AssetMetadataDTO(DirectorModel):
    asset_id: str
    metadata_keys: tuple[str, ...] = ()
    provenance_supplied: bool = False
    metadata_changed: bool = False


class V43DependencyDTO(DirectorModel):
    asset_id: str
    dependency_references: tuple[str, ...] = ()
    dependency_resolved: bool = False
    dependency_persisted: bool = False


class AssetCatalogSummary(DirectorModel):
    asset_count: int = Field(default=1, ge=0)
    version_count: int = Field(default=1, ge=0)
    dependency_count: int = Field(default=0, ge=0)
    catalog_persisted: bool = False
    distribution_enabled: bool = False


class AssetManagementFoundationReport(DirectorModel):
    asset: V43AssetDTO
    version: V43AssetVersionDTO
    metadata: V43AssetMetadataDTO
    dependency: V43DependencyDTO
    summary: AssetCatalogSummary
    planning_only: bool = True


class V43WorkspaceDTO(DirectorModel):
    workspace_id: str
    project_id: str
    page_reference: str
    workspace_created: bool = False
    workspace_persisted: bool = False


class V43TeamMemberDTO(DirectorModel):
    member_id: str
    workspace_id: str
    role: Literal["human_owner"] = "human_owner"
    membership_changed: bool = False
    permission_granted: bool = False


class V43TaskDTO(DirectorModel):
    task_id: str
    workspace_id: str
    page_reference: str
    status: Literal["planned"] = "planned"
    assigned: bool = False
    dispatched: bool = False
    completed: bool = False


class V43BoardDTO(DirectorModel):
    board_id: str
    workspace_id: str
    task_ids: tuple[str, ...] = ()
    board_persisted: bool = False
    board_changed: bool = False


class WorkspaceSummary(DirectorModel):
    workspace_count: int = Field(default=1, ge=0)
    member_count: int = Field(default=1, ge=0)
    task_count: int = Field(default=1, ge=0)
    assigned_task_count: int = 0
    automatic_action_taken: bool = False


class ProjectWorkspaceFoundationReport(DirectorModel):
    workspace: V43WorkspaceDTO
    team_member: V43TeamMemberDTO
    task: V43TaskDTO
    board: V43BoardDTO
    summary: WorkspaceSummary
    planning_only: bool = True


class DeliverablePackageDTO(DirectorModel):
    package_id: str
    project_id: str
    page_reference: str
    package_created: bool = False
    package_persisted: bool = False


class ExportProfileDTO(DirectorModel):
    profile_id: str
    package_id: str
    target_format: Literal["not_selected"] = "not_selected"
    export_enabled: bool = False
    export_performed: bool = False


class ArtifactDTO(DirectorModel):
    artifact_id: str
    package_id: str
    page_reference: str
    artifact_created: bool = False
    artifact_uploaded: bool = False


class ReleaseCandidateDTO(DirectorModel):
    candidate_id: str
    package_id: str
    readiness: Literal["review_required"] = "review_required"
    approved: bool = False
    published: bool = False
    distribution_started: bool = False


class DeliverySummary(DirectorModel):
    package_count: int = Field(default=1, ge=0)
    artifact_count: int = 0
    release_candidate_count: int = Field(default=1, ge=0)
    exports_performed: int = 0
    publications_performed: int = 0
    automatic_action_taken: bool = False


class DeliverableFoundationReport(DirectorModel):
    package: DeliverablePackageDTO
    export_profile: ExportProfileDTO
    artifact: ArtifactDTO
    release_candidate: ReleaseCandidateDTO
    summary: DeliverySummary
    planning_only: bool = True


class V43ProductionFoundationService:
    """Build non-executing Creative Production Platform DTO projections."""

    def production_pipeline(
        self, project_id: str, context: WorkflowContext
    ) -> ProductionPipelineFoundationReport:
        page_reference = _page_reference(context)
        project = ProductionProjectDTO(
            project_id=project_id,
            page_reference=page_reference,
            current_state=context.state,
        )
        return ProductionPipelineFoundationReport(
            project=project,
            stage=ProductionStageDTO(
                project_id=project_id,
                page_reference=page_reference,
                workflow_state=context.state,
                stage_name=context.state.value,
            ),
            milestone=ProductionMilestoneDTO(
                milestone_id=f"milestone:{project_id}:{page_reference}",
                project_id=project_id,
                page_reference=page_reference,
            ),
            deliverable=ProductionDeliverableDTO(
                deliverable_id=f"deliverable:{project_id}:{page_reference}",
                project_id=project_id,
                page_reference=page_reference,
            ),
            summary=PipelineSummary(),
        )

    def asset_management(
        self, project_id: str, context: WorkflowContext
    ) -> AssetManagementFoundationReport:
        page_reference = _page_reference(context)
        asset_id = f"asset:{project_id}:{page_reference}"
        dependency_references = tuple(sorted(str(name) for name in context.artifacts))
        metadata_keys = tuple(sorted(str(name) for name in context.metadata))
        return AssetManagementFoundationReport(
            asset=V43AssetDTO(
                asset_id=asset_id,
                project_id=project_id,
                page_reference=page_reference,
            ),
            version=V43AssetVersionDTO(asset_id=asset_id, version_id=f"version:{asset_id}"),
            metadata=V43AssetMetadataDTO(
                asset_id=asset_id,
                metadata_keys=metadata_keys,
                provenance_supplied=bool(context.artifacts),
            ),
            dependency=V43DependencyDTO(
                asset_id=asset_id,
                dependency_references=dependency_references,
            ),
            summary=AssetCatalogSummary(dependency_count=len(dependency_references)),
        )

    def project_workspace(
        self, project_id: str, context: WorkflowContext
    ) -> ProjectWorkspaceFoundationReport:
        page_reference = _page_reference(context)
        workspace_id = f"workspace:{project_id}"
        task_id = f"task:{project_id}:{page_reference}"
        return ProjectWorkspaceFoundationReport(
            workspace=V43WorkspaceDTO(
                workspace_id=workspace_id,
                project_id=project_id,
                page_reference=page_reference,
            ),
            team_member=V43TeamMemberDTO(member_id="human-owner", workspace_id=workspace_id),
            task=V43TaskDTO(
                task_id=task_id,
                workspace_id=workspace_id,
                page_reference=page_reference,
            ),
            board=V43BoardDTO(
                board_id=f"board:{project_id}",
                workspace_id=workspace_id,
                task_ids=(task_id,),
            ),
            summary=WorkspaceSummary(),
        )

    def deliverables(self, project_id: str, context: WorkflowContext) -> DeliverableFoundationReport:
        page_reference = _page_reference(context)
        package_id = f"deliverable-package:{project_id}:{page_reference}"
        return DeliverableFoundationReport(
            package=DeliverablePackageDTO(
                package_id=package_id,
                project_id=project_id,
                page_reference=page_reference,
            ),
            export_profile=ExportProfileDTO(
                profile_id=f"export-profile:{project_id}:{page_reference}",
                package_id=package_id,
            ),
            artifact=ArtifactDTO(
                artifact_id=f"artifact:{project_id}:{page_reference}",
                package_id=package_id,
                page_reference=page_reference,
            ),
            release_candidate=ReleaseCandidateDTO(
                candidate_id=f"release-candidate:{project_id}:{page_reference}",
                package_id=package_id,
            ),
            summary=DeliverySummary(),
        )


def _page_reference(context: WorkflowContext) -> str:
    page_id = context.page.get("id")
    return str(page_id) if page_id is not None else "page"
