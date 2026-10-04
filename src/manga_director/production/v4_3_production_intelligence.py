"""v4.3 Creative Production Platform intelligence DTOs without automation.

The service composes v4.3 foundation evidence into immutable planning,
analysis, publishing-workflow, and project-analytics reports. It never applies
a template, starts a stage, schedules work, mutates assets or projects, exports
or uploads artifacts, publishes/distributes output, or calls external systems.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.domain.state_machine import PageState
from manga_director.production.director import DirectorModel
from manga_director.production.v4_3_production_foundation import (
    AssetManagementFoundationReport,
    DeliverableFoundationReport,
    ProductionPipelineFoundationReport,
    ProjectWorkspaceFoundationReport,
    V43ProductionFoundationService,
)
from manga_director.workflow.contracts import WorkflowContext


class ProductionPlanDTO(DirectorModel):
    plan_id: str
    project_id: str
    page_reference: str
    current_state: PageState
    page_count: Literal[1] = 1
    plan_applied: bool = False
    workflow_changed: bool = False


class StageAutomationDTO(DirectorModel):
    plan_id: str
    stage_name: str
    automation_enabled: bool = False
    stage_started: bool = False
    stage_completed: bool = False
    action_dispatched: bool = False


class WorkflowTemplateDTO(DirectorModel):
    template_id: str
    plan_id: str
    state_machine_authoritative: bool = True
    template_applied: bool = False
    stage_skipping_allowed: bool = False


class ProductionScheduleDTO(DirectorModel):
    schedule_id: str
    plan_id: str
    page_reference: str
    proposed_window: str | None = None
    schedule_registered: bool = False
    automatic_start_enabled: bool = False


class ProductionReportDTO(DirectorModel):
    pipeline: ProductionPipelineFoundationReport
    plan: ProductionPlanDTO
    stage_automation: StageAutomationDTO
    template: WorkflowTemplateDTO
    schedule: ProductionScheduleDTO
    automatic_action_taken: bool = False
    planning_only: bool = True


class V43AssetAnalysisDTO(DirectorModel):
    asset_id: str
    page_reference: str
    metadata_key_count: int = Field(ge=0)
    provenance_present: bool = False
    analysis_persisted: bool = False


class V43DependencyAnalysisDTO(DirectorModel):
    asset_id: str
    dependency_count: int = Field(ge=0)
    dependency_references: tuple[str, ...] = ()
    resolution_applied: bool = False


class AssetUsageReport(DirectorModel):
    asset_id: str
    referenced_by_page_count: Literal[1] = 1
    usage_persisted: bool = False
    usage_changed: bool = False


class DuplicateDetectionDTO(DirectorModel):
    asset_id: str
    duplicate_references: tuple[str, ...] = ()
    duplicate_resolution_applied: bool = False
    asset_deleted: bool = False


class AssetInsightSummary(DirectorModel):
    analyzed_asset_count: int = Field(default=1, ge=0)
    dependency_count: int = Field(default=0, ge=0)
    duplicate_count: int = 0
    recommendation_generated: bool = True
    automatic_action_taken: bool = False


class AssetIntelligenceReport(DirectorModel):
    catalog: AssetManagementFoundationReport
    analysis: V43AssetAnalysisDTO
    dependency_analysis: V43DependencyAnalysisDTO
    usage: AssetUsageReport
    duplicates: DuplicateDetectionDTO
    summary: AssetInsightSummary
    planning_only: bool = True


class ExportWorkflowDTO(DirectorModel):
    workflow_id: str
    package_id: str
    page_reference: str
    workflow_started: bool = False
    export_performed: bool = False
    artifact_created: bool = False


class PublicationProfileDTO(DirectorModel):
    profile_id: str
    workflow_id: str
    target_name: Literal["not_selected"] = "not_selected"
    credentials_present: bool = False
    external_service_called: bool = False


class ReleaseScheduleDTO(DirectorModel):
    schedule_id: str
    workflow_id: str
    proposed_window: str | None = None
    schedule_registered: bool = False
    automatic_release_enabled: bool = False


class DistributionReportDTO(DirectorModel):
    workflow_id: str
    distribution_ready: bool = False
    distribution_started: bool = False
    external_delivery_performed: bool = False


class PublishingSummary(DirectorModel):
    workflow_count: int = Field(default=1, ge=0)
    export_count: int = 0
    release_count: int = 0
    distribution_count: int = 0
    human_approval_required: bool = True
    automatic_action_taken: bool = False


class PublishingWorkflowReport(DirectorModel):
    deliverables: DeliverableFoundationReport
    export_workflow: ExportWorkflowDTO
    profile: PublicationProfileDTO
    schedule: ReleaseScheduleDTO
    distribution: DistributionReportDTO
    summary: PublishingSummary
    planning_only: bool = True


class ProgressAnalyticsDTO(DirectorModel):
    project_id: str
    page_reference: str
    observed_progress_percent: int = Field(default=0, ge=0, le=100)
    progress_persisted: bool = False
    progress_changed: bool = False


class ProjectKPIDTO(DirectorModel):
    project_id: str
    metric_name: Literal["workflow_evidence_count"] = "workflow_evidence_count"
    value: int = Field(default=0, ge=0)
    target_set: bool = False
    alert_configured: bool = False


class VelocityReportDTO(DirectorModel):
    project_id: str
    page_reference: str
    observed_completed_stage_count: int = Field(default=0, ge=0)
    forecast_generated: bool = False
    schedule_changed: bool = False


class ResourceMetricsDTO(DirectorModel):
    project_id: str
    declared_member_count: int = Field(default=1, ge=0)
    assigned_task_count: int = 0
    resources_allocated: bool = False
    capacity_changed: bool = False


class ProjectDashboardSummary(DirectorModel):
    workspace_count: int = Field(default=1, ge=0)
    page_count: Literal[1] = 1
    kpi_count: int = Field(default=1, ge=0)
    automation_enabled: bool = False
    automatic_action_taken: bool = False


class ProjectAnalyticsReport(DirectorModel):
    workspace: ProjectWorkspaceFoundationReport
    progress: ProgressAnalyticsDTO
    kpi: ProjectKPIDTO
    velocity: VelocityReportDTO
    resources: ResourceMetricsDTO
    dashboard: ProjectDashboardSummary
    planning_only: bool = True


class V43ProductionIntelligenceService:
    """Build non-executing v4.3 production intelligence DTO projections."""

    def __init__(self, foundation: V43ProductionFoundationService | None = None) -> None:
        self._foundation = foundation or V43ProductionFoundationService()

    def production_automation(self, project_id: str, context: WorkflowContext) -> ProductionReportDTO:
        pipeline = self._foundation.production_pipeline(project_id, context)
        page_reference = pipeline.project.page_reference
        plan_id = f"production-plan:{project_id}:{page_reference}"
        return ProductionReportDTO(
            pipeline=pipeline,
            plan=ProductionPlanDTO(
                plan_id=plan_id,
                project_id=project_id,
                page_reference=page_reference,
                current_state=context.state,
            ),
            stage_automation=StageAutomationDTO(
                plan_id=plan_id,
                stage_name=pipeline.stage.stage_name,
            ),
            template=WorkflowTemplateDTO(
                template_id=f"workflow-template:{project_id}:{page_reference}",
                plan_id=plan_id,
            ),
            schedule=ProductionScheduleDTO(
                schedule_id=f"production-schedule:{project_id}:{page_reference}",
                plan_id=plan_id,
                page_reference=page_reference,
            ),
        )

    def asset_intelligence(self, project_id: str, context: WorkflowContext) -> AssetIntelligenceReport:
        catalog = self._foundation.asset_management(project_id, context)
        asset_id = catalog.asset.asset_id
        dependencies = catalog.dependency.dependency_references
        return AssetIntelligenceReport(
            catalog=catalog,
            analysis=V43AssetAnalysisDTO(
                asset_id=asset_id,
                page_reference=catalog.asset.page_reference,
                metadata_key_count=len(catalog.metadata.metadata_keys),
                provenance_present=catalog.metadata.provenance_supplied,
            ),
            dependency_analysis=V43DependencyAnalysisDTO(
                asset_id=asset_id,
                dependency_count=len(dependencies),
                dependency_references=dependencies,
            ),
            usage=AssetUsageReport(asset_id=asset_id),
            duplicates=DuplicateDetectionDTO(asset_id=asset_id),
            summary=AssetInsightSummary(dependency_count=len(dependencies)),
        )

    def publishing_workflow(self, project_id: str, context: WorkflowContext) -> PublishingWorkflowReport:
        deliverables = self._foundation.deliverables(project_id, context)
        page_reference = deliverables.package.page_reference
        workflow_id = f"publishing-workflow:{project_id}:{page_reference}"
        return PublishingWorkflowReport(
            deliverables=deliverables,
            export_workflow=ExportWorkflowDTO(
                workflow_id=workflow_id,
                package_id=deliverables.package.package_id,
                page_reference=page_reference,
            ),
            profile=PublicationProfileDTO(
                profile_id=f"publication-profile:{project_id}:{page_reference}",
                workflow_id=workflow_id,
            ),
            schedule=ReleaseScheduleDTO(
                schedule_id=f"release-schedule:{project_id}:{page_reference}",
                workflow_id=workflow_id,
            ),
            distribution=DistributionReportDTO(workflow_id=workflow_id),
            summary=PublishingSummary(),
        )

    def project_analytics(self, project_id: str, context: WorkflowContext) -> ProjectAnalyticsReport:
        workspace = self._foundation.project_workspace(project_id, context)
        pipeline = self._foundation.production_pipeline(project_id, context)
        page_reference = workspace.workspace.page_reference
        return ProjectAnalyticsReport(
            workspace=workspace,
            progress=ProgressAnalyticsDTO(
                project_id=project_id,
                page_reference=page_reference,
            ),
            kpi=ProjectKPIDTO(
                project_id=project_id,
                value=len(context.artifacts),
            ),
            velocity=VelocityReportDTO(
                project_id=project_id,
                page_reference=page_reference,
                observed_completed_stage_count=pipeline.summary.completed_stage_count,
            ),
            resources=ResourceMetricsDTO(project_id=project_id),
            dashboard=ProjectDashboardSummary(),
        )
