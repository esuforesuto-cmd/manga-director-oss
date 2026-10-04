"""Read-only v5.7 Manga Production Platform foundation projections.

This Application-layer module composes one existing ``WorkflowContext`` with
optional plugin-registry evidence.  It never owns project, asset, workspace,
automation, or plugin lifecycle state; it cannot execute a workflow, mutate a
repository, register or load a plugin, or bypass the domain ``StateMachine``.
"""

from __future__ import annotations

from typing import Literal, Protocol

from pydantic import Field

from manga_director.domain.state_machine import PageState
from manga_director.production.director import DirectorModel
from manga_director.workflow.contracts import WorkflowContext


class PluginContributionSource(Protocol):
    """Structural, read-only view of a plugin contribution."""

    name: str
    plugin_name: str
    plugin_type: object


class PluginRuntimeSource(Protocol):
    """Small read-only protocol implemented by the existing PluginRegistry."""

    def list(self) -> list[PluginContributionSource]: ...


class WorkspaceManagerDTO(DirectorModel):
    workspace_id: str
    project_id: str
    page_reference: str
    current_state: PageState
    page_count: Literal[1] = 1
    workspace_created: Literal[False] = False
    workspace_persisted: Literal[False] = False


class WorkspaceManagerReport(DirectorModel):
    workspace: WorkspaceManagerDTO
    referenced_metadata_keys: tuple[str, ...] = ()
    referenced_artifact_keys: tuple[str, ...] = ()
    workflow_mutated: Literal[False] = False
    planning_only: Literal[True] = True


class ProjectManagerDTO(DirectorModel):
    project_id: str
    page_reference: str
    current_state: PageState
    storyboard_persisted: bool
    quality_review_completed: bool
    project_created: Literal[False] = False
    project_persisted: Literal[False] = False


class ProjectManagerReport(DirectorModel):
    project: ProjectManagerDTO
    required_state_authority: Literal["StateMachine"] = "StateMachine"
    project_mutated: Literal[False] = False
    planning_only: Literal[True] = True


class V57AssetLifecycleDTO(DirectorModel):
    asset_id: str
    project_id: str
    page_reference: str
    source_key: str
    source_kind: Literal["artifact", "metadata"]
    lifecycle_state: Literal["observed"] = "observed"
    asset_created: Literal[False] = False
    asset_persisted: Literal[False] = False


class AssetManagerSummary(DirectorModel):
    observed_asset_count: int = Field(default=0, ge=0)
    artifact_asset_count: int = Field(default=0, ge=0)
    metadata_asset_count: int = Field(default=0, ge=0)
    lifecycle_changed: Literal[False] = False
    repository_mutated: Literal[False] = False


class AssetManagerReport(DirectorModel):
    assets: tuple[V57AssetLifecycleDTO, ...] = ()
    summary: AssetManagerSummary
    planning_only: Literal[True] = True


class AutomationFoundationDTO(DirectorModel):
    automation_id: str
    project_id: str
    page_reference: str
    template_references: tuple[str, ...] = ()
    rule_references: tuple[str, ...] = ()
    evidence_keys: tuple[str, ...] = ()
    human_approval_required: Literal[True] = True
    execution_requested: Literal[False] = False
    execution_performed: Literal[False] = False
    workflow_mutated: Literal[False] = False


class AutomationFoundationReport(DirectorModel):
    automation: AutomationFoundationDTO
    source_contract: Literal["existing_automation_engine_unchanged"] = (
        "existing_automation_engine_unchanged"
    )
    planning_only: Literal[True] = True


class PluginRuntimeDescriptorDTO(DirectorModel):
    contribution_name: str
    plugin_name: str
    plugin_type: str
    runtime_state: Literal["observed"] = "observed"
    plugin_loaded_by_service: Literal[False] = False
    plugin_executed_by_service: Literal[False] = False


class PluginRuntimeSummary(DirectorModel):
    contribution_count: int = Field(default=0, ge=0)
    registry_observed: bool = False
    plugin_registered: Literal[False] = False
    plugin_loaded: Literal[False] = False
    plugin_executed: Literal[False] = False
    plugin_runtime_mutated: Literal[False] = False


class PluginRuntimeReport(DirectorModel):
    descriptors: tuple[PluginRuntimeDescriptorDTO, ...] = ()
    summary: PluginRuntimeSummary
    source_contract: Literal["existing_plugin_registry_unchanged"] = (
        "existing_plugin_registry_unchanged"
    )
    planning_only: Literal[True] = True


class PlatformPromptReferenceDTO(DirectorModel):
    """Compact references that prevent duplicated production context prompts."""

    project_id: str
    page_reference: str
    reused_context_keys: tuple[str, ...] = ()
    duplicate_context_elided: Literal[True] = True
    prompt_generated: Literal[False] = False


class ProductionPlatformFoundationReport(DirectorModel):
    workspace: WorkspaceManagerReport
    project: ProjectManagerReport
    assets: AssetManagerReport
    automation: AutomationFoundationReport
    plugins: PluginRuntimeReport
    prompt_references: PlatformPromptReferenceDTO
    planning_only: Literal[True] = True


class PluginRuntimeFoundation:
    """Create a read-only capability inventory from an existing registry."""

    def __init__(self, source: PluginRuntimeSource | None = None) -> None:
        self._source = source

    def report(self) -> PluginRuntimeReport:
        contributions = () if self._source is None else tuple(self._source.list())
        descriptors = tuple(
            PluginRuntimeDescriptorDTO(
                contribution_name=contribution.name,
                plugin_name=contribution.plugin_name,
                plugin_type=str(contribution.plugin_type),
            )
            for contribution in sorted(
                contributions,
                key=lambda item: (str(item.plugin_type), item.plugin_name, item.name),
            )
        )
        return PluginRuntimeReport(
            descriptors=descriptors,
            summary=PluginRuntimeSummary(
                contribution_count=len(descriptors),
                registry_observed=self._source is not None,
            ),
        )


class V57ProductionPlatformFoundationService:
    """Compose v5.7 platform projections without altering existing owners."""

    def __init__(self, plugin_source: PluginRuntimeSource | None = None) -> None:
        self._plugin_runtime = PluginRuntimeFoundation(plugin_source)

    def workspace(self, project_id: str, context: WorkflowContext) -> WorkspaceManagerReport:
        page_reference = _page_reference(context)
        return WorkspaceManagerReport(
            workspace=WorkspaceManagerDTO(
                workspace_id=f"workspace:{project_id}",
                project_id=project_id,
                page_reference=page_reference,
                current_state=context.state,
            ),
            referenced_metadata_keys=tuple(sorted(str(key) for key in context.metadata)),
            referenced_artifact_keys=tuple(sorted(str(key) for key in context.artifacts)),
        )

    def project(self, project_id: str, context: WorkflowContext) -> ProjectManagerReport:
        page_reference = _page_reference(context)
        quality_review_completed = (
            context.state in (PageState.QUALITY_CHECKED, PageState.APPROVED)
            and PageState.QUALITY_CHECKED.value in context.artifacts
        )
        return ProjectManagerReport(
            project=ProjectManagerDTO(
                project_id=project_id,
                page_reference=page_reference,
                current_state=context.state,
                storyboard_persisted=PageState.STORYBOARDED.value in context.artifacts,
                quality_review_completed=quality_review_completed,
            )
        )

    def assets(self, project_id: str, context: WorkflowContext) -> AssetManagerReport:
        page_reference = _page_reference(context)
        source_groups: tuple[
            tuple[Literal["artifact", "metadata"], tuple[str, ...]], ...
        ] = (
            ("artifact", tuple(sorted(str(key) for key in context.artifacts))),
            ("metadata", tuple(sorted(str(key) for key in context.metadata))),
        )
        assets = tuple(
            V57AssetLifecycleDTO(
                asset_id=f"asset:{project_id}:{page_reference}:{source_kind}:{source_key}",
                project_id=project_id,
                page_reference=page_reference,
                source_key=source_key,
                source_kind=source_kind,
            )
            for source_kind, keys in source_groups
            for source_key in keys
        )
        return AssetManagerReport(
            assets=assets,
            summary=AssetManagerSummary(
                observed_asset_count=len(assets),
                artifact_asset_count=sum(asset.source_kind == "artifact" for asset in assets),
                metadata_asset_count=sum(asset.source_kind == "metadata" for asset in assets),
            ),
        )

    def automation(self, project_id: str, context: WorkflowContext) -> AutomationFoundationReport:
        page_reference = _page_reference(context)
        return AutomationFoundationReport(
            automation=AutomationFoundationDTO(
                automation_id=f"automation:{project_id}:{page_reference}",
                project_id=project_id,
                page_reference=page_reference,
                template_references=_reference_values(context.metadata.get("automation_templates")),
                rule_references=_reference_values(context.metadata.get("automation_rules")),
                evidence_keys=tuple(
                    sorted({*(str(key) for key in context.artifacts), *(str(key) for key in context.metadata)})
                ),
            )
        )

    def plugin_runtime(self) -> PluginRuntimeReport:
        return self._plugin_runtime.report()

    def foundation(
        self, project_id: str, context: WorkflowContext
    ) -> ProductionPlatformFoundationReport:
        page_reference = _page_reference(context)
        workspace = self.workspace(project_id, context)
        project = self.project(project_id, context)
        assets = self.assets(project_id, context)
        automation = self.automation(project_id, context)
        return ProductionPlatformFoundationReport(
            workspace=workspace,
            project=project,
            assets=assets,
            automation=automation,
            plugins=self.plugin_runtime(),
            prompt_references=PlatformPromptReferenceDTO(
                project_id=project_id,
                page_reference=page_reference,
                reused_context_keys=tuple(
                    key
                    for key in (
                        "story_context",
                        "character_context",
                        "world_context",
                        "timeline_context",
                    )
                    if key in context.metadata
                ),
            ),
        )


def _page_reference(context: WorkflowContext) -> str:
    if "pages" in context.page:
        raise ValueError("v5.7 platform foundation requires exactly one Page context")
    return str(context.page.get("id", "current-page"))


def _reference_values(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple, set, frozenset)):
        return tuple(sorted(str(item) for item in value))
    return (str(value),)
