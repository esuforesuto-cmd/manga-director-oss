"""Read-only v5.7 Production Platform v1 orchestration diagnostics.

This Application-layer composition joins existing Production Pipeline, Export
Engine, and Production Workspace reports for one supplied Page. It is
automation-ready but never dispatches work, publishes an event, changes plugin
lifecycle, schedules a task, restores a snapshot, transitions a workflow,
approves a Page, or exports content.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.domain.state_machine import PageState
from manga_director.production.director import DirectorModel
from manga_director.production.v5_6_export_engine import ExportEngineReport, V56ExportEngineService
from manga_director.production.v5_6_production_pipeline import (
    MangaProductionPipelineReport,
    V56ProductionPipelineService,
)
from manga_director.production.v5_7_platform_foundation import (
    PluginRuntimeSource,
    V57ProductionPlatformFoundationService,
)
from manga_director.production.v5_7_production_workspace import (
    ProductionTemplateDTO,
    ProductionWorkspaceV2Report,
    ResourceAllocationDTO,
    V57ProductionWorkspaceService,
)
from manga_director.workflow.contracts import WorkflowContext


class AutomationPipelineDTO(DirectorModel):
    pipeline_id: str
    project_id: str
    page_reference: str
    template_references: tuple[str, ...] = ()
    rule_references: tuple[str, ...] = ()
    event_count: int = Field(default=0, ge=0)
    human_approval_required: Literal[True] = True
    automation_ready: bool
    execution_dispatched: Literal[False] = False
    workflow_mutated: Literal[False] = False


class AutomationPipelineReport(DirectorModel):
    pipeline: AutomationPipelineDTO
    findings: tuple[str, ...] = ()
    existing_automation_contract_preserved: Literal[True] = True
    planning_only: Literal[True] = True


class PluginLifecycleDescriptorDTO(DirectorModel):
    plugin_name: str
    version: str
    enabled: bool
    active: bool
    dependency_names: tuple[str, ...] = ()
    lifecycle_changed: Literal[False] = False


class PluginLifecycleReport(DirectorModel):
    plugins: tuple[PluginLifecycleDescriptorDTO, ...] = ()
    enabled_plugin_count: int = Field(default=0, ge=0)
    active_plugin_count: int = Field(default=0, ge=0)
    lifecycle_owner: Literal["existing_plugin_manager"] = "existing_plugin_manager"
    lifecycle_action_performed: Literal[False] = False
    planning_only: Literal[True] = True


class V57EventBusEventDTO(DirectorModel):
    event_id: str
    event_type: str
    page_reference: str
    event_dispatched: Literal[False] = False


class V57EventBusReport(DirectorModel):
    events: tuple[V57EventBusEventDTO, ...] = ()
    event_count: int = Field(default=0, ge=0)
    existing_event_bus_preserved: Literal[True] = True
    publish_performed: Literal[False] = False
    planning_only: Literal[True] = True


class TaskScheduleDTO(DirectorModel):
    task_id: str
    project_id: str
    page_reference: str
    current_state: PageState
    next_command: str | None = None
    scheduler_owner: Literal["existing_workflow_scheduler"] = "existing_workflow_scheduler"
    task_scheduled: Literal[False] = False
    task_dispatched: Literal[False] = False


class TaskSchedulerReport(DirectorModel):
    task: TaskScheduleDTO
    eligible_for_existing_scheduler: bool
    schedule_changed: Literal[False] = False
    planning_only: Literal[True] = True


class V57WorkspaceSnapshotDTO(DirectorModel):
    snapshot_id: str
    project_id: str
    page_reference: str
    current_state: PageState
    artifact_keys: tuple[str, ...] = ()
    metadata_keys: tuple[str, ...] = ()
    snapshot_captured: Literal[False] = False
    snapshot_persisted: Literal[False] = False


class SnapshotRestoreReport(DirectorModel):
    snapshot: V57WorkspaceSnapshotDTO
    restore_eligible: bool
    missing_evidence: tuple[str, ...] = ()
    restore_performed: Literal[False] = False
    workflow_mutated: Literal[False] = False
    planning_only: Literal[True] = True


class V57ProductionAnalyticsDTO(DirectorModel):
    project_id: str
    page_reference: str
    artifact_count: int = Field(default=0, ge=0)
    metadata_count: int = Field(default=0, ge=0)
    event_count: int = Field(default=0, ge=0)
    plugin_count: int = Field(default=0, ge=0)
    quality_review_completed: bool
    export_eligible: bool
    analytics_persisted: Literal[False] = False


class V57ProductionAnalyticsReport(DirectorModel):
    analytics: V57ProductionAnalyticsDTO
    recommendations: tuple[str, ...] = ()
    analysis_only: Literal[True] = True


class ProductionOrchestratorReport(DirectorModel):
    production_pipeline: MangaProductionPipelineReport
    export: ExportEngineReport
    workspace: ProductionWorkspaceV2Report
    automation: AutomationPipelineReport
    plugins: PluginLifecycleReport
    events: V57EventBusReport
    scheduler: TaskSchedulerReport
    snapshot: SnapshotRestoreReport
    analytics: V57ProductionAnalyticsReport
    end_to_end_ready: bool
    automatic_action_taken: Literal[False] = False
    planning_only: Literal[True] = True


class V57ProductionOrchestrator:
    """Join existing one-page evidence into a safe Production Platform report."""

    def __init__(self, plugin_source: PluginRuntimeSource | None = None) -> None:
        self._foundation = V57ProductionPlatformFoundationService(plugin_source)
        self._workspace = V57ProductionWorkspaceService(plugin_source)
        self._pipeline = V56ProductionPipelineService()
        self._export = V56ExportEngineService()

    def automation_pipeline(
        self, project_id: str, context: WorkflowContext
    ) -> AutomationPipelineReport:
        foundation = self._foundation.automation(project_id, context)
        automation = foundation.automation
        findings: list[str] = []
        if not automation.template_references:
            findings.append("automation template reference is required")
        if not automation.rule_references:
            findings.append("automation rule reference is required")
        if not automation.evidence_keys:
            findings.append("automation evidence is required")
        return AutomationPipelineReport(
            pipeline=AutomationPipelineDTO(
                pipeline_id=f"automation-pipeline:{project_id}:{automation.page_reference}",
                project_id=project_id,
                page_reference=automation.page_reference,
                template_references=automation.template_references,
                rule_references=automation.rule_references,
                event_count=len(context.events),
                automation_ready=not findings,
            ),
            findings=tuple(findings),
        )

    def plugin_lifecycle(
        self, plugins: tuple[PluginLifecycleDescriptorDTO, ...] = ()
    ) -> PluginLifecycleReport:
        ordered = tuple(sorted(plugins, key=lambda plugin: plugin.plugin_name))
        return PluginLifecycleReport(
            plugins=ordered,
            enabled_plugin_count=sum(plugin.enabled for plugin in ordered),
            active_plugin_count=sum(plugin.active for plugin in ordered),
        )

    def event_bus(self, context: WorkflowContext) -> V57EventBusReport:
        page_reference = self._foundation.workspace("event-observer", context).workspace.page_reference
        events = tuple(
            V57EventBusEventDTO(
                event_id=event.event_id,
                event_type=str(event.event_type),
                page_reference=page_reference,
            )
            for event in context.events
        )
        return V57EventBusReport(events=events, event_count=len(events))

    def task_scheduler(
        self, project_id: str, context: WorkflowContext
    ) -> TaskSchedulerReport:
        workflow = self._workspace.workflow_state(project_id, context)
        return TaskSchedulerReport(
            task=TaskScheduleDTO(
                task_id=f"scheduled-task:{project_id}:{workflow.state.page_reference}",
                project_id=project_id,
                page_reference=workflow.state.page_reference,
                current_state=workflow.state.current_state,
                next_command=workflow.state.next_command,
            ),
            eligible_for_existing_scheduler=workflow.valid and workflow.state.next_command is not None,
        )

    def workspace_snapshot(
        self, project_id: str, context: WorkflowContext
    ) -> SnapshotRestoreReport:
        session = self._workspace.production_session(project_id, context)
        page_reference = session.session.page_reference
        return SnapshotRestoreReport(
            snapshot=V57WorkspaceSnapshotDTO(
                snapshot_id=f"workspace-snapshot:{project_id}:{page_reference}",
                project_id=project_id,
                page_reference=page_reference,
                current_state=context.state,
                artifact_keys=tuple(sorted(str(key) for key in context.artifacts)),
                metadata_keys=tuple(sorted(str(key) for key in context.metadata)),
            ),
            restore_eligible=session.session.recovery_eligible,
            missing_evidence=session.missing_recovery_evidence,
        )

    def analytics(
        self,
        project_id: str,
        context: WorkflowContext,
        plugins: PluginLifecycleReport,
        export: ExportEngineReport,
    ) -> V57ProductionAnalyticsReport:
        project = self._foundation.project(project_id, context).project
        recommendations: list[str] = []
        if not project.quality_review_completed:
            recommendations.append("complete quality review before approval")
        if not export.manager.export_eligible:
            recommendations.append("supply approved export evidence before publication")
        return V57ProductionAnalyticsReport(
            analytics=V57ProductionAnalyticsDTO(
                project_id=project_id,
                page_reference=project.page_reference,
                artifact_count=len(context.artifacts),
                metadata_count=len(context.metadata),
                event_count=len(context.events),
                plugin_count=len(plugins.plugins),
                quality_review_completed=project.quality_review_completed,
                export_eligible=export.manager.export_eligible,
            ),
            recommendations=tuple(recommendations),
        )

    def production_platform(
        self,
        project_id: str,
        context: WorkflowContext,
        allocations: tuple[ResourceAllocationDTO, ...] = (),
        templates: tuple[ProductionTemplateDTO, ...] = (),
        plugins: tuple[PluginLifecycleDescriptorDTO, ...] = (),
    ) -> ProductionOrchestratorReport:
        production_pipeline = self._pipeline.production_pipeline(project_id, context)
        export = self._export.export_engine(project_id, context)
        workspace = self._workspace.production_workspace(
            project_id, context, allocations, templates
        )
        automation = self.automation_pipeline(project_id, context)
        lifecycle = self.plugin_lifecycle(plugins)
        events = self.event_bus(context)
        scheduler = self.task_scheduler(project_id, context)
        snapshot = self.workspace_snapshot(project_id, context)
        analytics = self.analytics(project_id, context, lifecycle, export)
        end_to_end_ready = (
            workspace.workspace.workspace.workspace_consistent
            and workspace.workflow.valid
            and workspace.resources.allocation_valid
            and workspace.templates.compatible
            and workspace.session.session.recovery_eligible
            and automation.pipeline.automation_ready
            and snapshot.restore_eligible
            and export.manager.export_eligible
        )
        return ProductionOrchestratorReport(
            production_pipeline=production_pipeline,
            export=export,
            workspace=workspace,
            automation=automation,
            plugins=lifecycle,
            events=events,
            scheduler=scheduler,
            snapshot=snapshot,
            analytics=analytics,
            end_to_end_ready=end_to_end_ready,
        )
