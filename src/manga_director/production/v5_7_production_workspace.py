"""Read-only v5.7 Production Workspace v2 projections.

The module composes the v5.7 Foundation with caller-supplied resource and
template evidence. It validates one existing Page only and never allocates a
resource, persists a session, resumes work, changes workflow state, or writes
to a repository. The domain StateMachine remains authoritative.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Literal

from pydantic import Field

from manga_director.domain.state_machine import PageState, StateMachine
from manga_director.production.director import DirectorModel
from manga_director.production.v5_7_platform_foundation import (
    AssetManagerReport,
    PluginRuntimeSource,
    ProjectManagerReport,
    V57AssetLifecycleDTO,
    V57ProductionPlatformFoundationService,
    WorkspaceManagerReport,
)
from manga_director.workflow.contracts import WorkflowContext


class AssetRegistryEntryDTO(DirectorModel):
    asset_id: str
    project_id: str
    page_reference: str
    source_key: str
    source_kind: Literal["artifact", "metadata"]
    lifecycle_state: Literal["observed"] = "observed"
    registry_written: Literal[False] = False


class AssetRegistryReport(DirectorModel):
    entries: tuple[AssetRegistryEntryDTO, ...] = ()
    unique_source_keys: tuple[str, ...] = ()
    lifecycle_valid: bool
    registry_persisted: Literal[False] = False
    repository_mutated: Literal[False] = False
    planning_only: Literal[True] = True


class AssetStorageRecordDTO(DirectorModel):
    asset: V57AssetLifecycleDTO
    storage_reference: str | None = None
    storage_evidence_present: bool = False
    storage_accessed: Literal[False] = False
    storage_written: Literal[False] = False


class AssetStorageReport(DirectorModel):
    records: tuple[AssetStorageRecordDTO, ...] = ()
    storage_evidence_count: int = Field(default=0, ge=0)
    unresolved_asset_ids: tuple[str, ...] = ()
    repository_mutated: Literal[False] = False
    planning_only: Literal[True] = True


class AssetCacheReport(DirectorModel):
    cache_key: str
    assets: AssetManagerReport
    cache_hit: bool
    cache_entry_count: int = Field(default=0, ge=0)
    cache_persisted: Literal[False] = False
    repository_mutated: Literal[False] = False
    planning_only: Literal[True] = True


class AssetCache:
    """Explicit, process-local cache for immutable Asset Manager reports."""

    def __init__(self) -> None:
        self._reports: dict[str, AssetManagerReport] = {}

    def get(self, cache_key: str) -> AssetManagerReport | None:
        return self._reports.get(cache_key)

    def store(self, cache_key: str, report: AssetManagerReport) -> None:
        self._reports[cache_key] = report

    def invalidate(self, cache_key: str | None = None) -> None:
        if cache_key is None:
            self._reports.clear()
        else:
            self._reports.pop(cache_key, None)

    @property
    def entry_count(self) -> int:
        return len(self._reports)


class AssetVersionEvidenceDTO(DirectorModel):
    asset: V57AssetLifecycleDTO
    version_reference: str | None = None
    version_evidence_present: bool = False
    version_created: Literal[False] = False
    version_replaced: Literal[False] = False
    version_history_mutated: Literal[False] = False


class AssetVersioningReport(DirectorModel):
    versions: tuple[AssetVersionEvidenceDTO, ...] = ()
    version_evidence_count: int = Field(default=0, ge=0)
    unresolved_asset_ids: tuple[str, ...] = ()
    repository_mutated: Literal[False] = False
    planning_only: Literal[True] = True


class AssetImportEvidenceDTO(DirectorModel):
    asset: V57AssetLifecycleDTO
    import_reference: str | None = None
    import_evidence_present: bool = False
    import_requested: Literal[False] = False
    import_performed: Literal[False] = False


class AssetExportEvidenceDTO(DirectorModel):
    asset: V57AssetLifecycleDTO
    export_reference: str | None = None
    export_evidence_present: bool = False
    export_requested: Literal[False] = False
    export_performed: Literal[False] = False


class AssetImportExportReport(DirectorModel):
    imports: tuple[AssetImportEvidenceDTO, ...] = ()
    exports: tuple[AssetExportEvidenceDTO, ...] = ()
    import_evidence_count: int = Field(default=0, ge=0)
    export_evidence_count: int = Field(default=0, ge=0)
    unresolved_import_asset_ids: tuple[str, ...] = ()
    unresolved_export_asset_ids: tuple[str, ...] = ()
    repository_mutated: Literal[False] = False
    planning_only: Literal[True] = True


class ProjectWorkspaceDTO(DirectorModel):
    workspace_id: str
    project_id: str
    page_reference: str
    workflow_state: PageState
    page_count: Literal[1] = 1
    workspace_consistent: bool
    workspace_persisted: Literal[False] = False
    project_mutated: Literal[False] = False


class ProjectWorkspaceReport(DirectorModel):
    workspace: ProjectWorkspaceDTO
    asset_reference_count: int = Field(default=0, ge=0)
    workflow_state_owned_by: Literal["StateMachine"] = "StateMachine"
    planning_only: Literal[True] = True


class WorkflowStateManagerDTO(DirectorModel):
    project_id: str
    page_reference: str
    current_state: PageState
    next_command: str | None = None
    storyboard_persisted: bool
    quality_review_completed: bool
    state_changed: Literal[False] = False


class WorkflowStateValidationReport(DirectorModel):
    state: WorkflowStateManagerDTO
    valid: bool
    findings: tuple[str, ...] = ()
    state_machine_authoritative: Literal[True] = True
    planning_only: Literal[True] = True


class ResourceAllocationDTO(DirectorModel):
    resource_id: str
    project_id: str
    page_reference: str
    owner: str
    requested_units: int = Field(default=1, ge=0)
    available_units: int = Field(default=1, ge=0)
    allocation_performed: Literal[False] = False


class ResourceManagerReport(DirectorModel):
    allocations: tuple[ResourceAllocationDTO, ...] = ()
    allocation_valid: bool
    insufficient_resource_ids: tuple[str, ...] = ()
    allocation_mutated: Literal[False] = False
    planning_only: Literal[True] = True


class ProductionTemplateDTO(DirectorModel):
    template_id: str
    page_reference: str
    required_evidence: tuple[str, ...] = ()
    template_loaded: Literal[False] = False
    template_applied: Literal[False] = False


class TemplateRegistryReport(DirectorModel):
    templates: tuple[ProductionTemplateDTO, ...] = ()
    compatible: bool
    missing_evidence: tuple[str, ...] = ()
    registry_mutated: Literal[False] = False
    planning_only: Literal[True] = True


class V57ProductionSessionDTO(DirectorModel):
    session_id: str
    project_id: str
    page_reference: str
    current_state: PageState
    checkpoint_evidence_available: bool
    recovery_eligible: bool
    session_created: Literal[False] = False
    session_persisted: Literal[False] = False
    resumed: Literal[False] = False


class SessionRecoveryReport(DirectorModel):
    session: V57ProductionSessionDTO
    missing_recovery_evidence: tuple[str, ...] = ()
    recovery_performed: Literal[False] = False
    workflow_mutated: Literal[False] = False
    planning_only: Literal[True] = True


class ProductionWorkspaceV2Report(DirectorModel):
    assets: AssetRegistryReport
    workspace: ProjectWorkspaceReport
    workflow: WorkflowStateValidationReport
    resources: ResourceManagerReport
    templates: TemplateRegistryReport
    session: SessionRecoveryReport
    automatic_action_taken: Literal[False] = False
    planning_only: Literal[True] = True


class V57ProductionWorkspaceService:
    """Build one-page Production Workspace v2 diagnostics without side effects."""

    def __init__(
        self,
        plugin_source: PluginRuntimeSource | None = None,
        asset_cache: AssetCache | None = None,
    ) -> None:
        self._foundation = V57ProductionPlatformFoundationService(plugin_source)
        self._asset_cache = asset_cache or AssetCache()

    def asset_registry(self, project_id: str, context: WorkflowContext) -> AssetRegistryReport:
        assets = self._foundation.assets(project_id, context)
        entries = tuple(
            AssetRegistryEntryDTO(
                asset_id=asset.asset_id,
                project_id=asset.project_id,
                page_reference=asset.page_reference,
                source_key=asset.source_key,
                source_kind=asset.source_kind,
            )
            for asset in assets.assets
        )
        return AssetRegistryReport(
            entries=entries,
            unique_source_keys=tuple(sorted({entry.source_key for entry in entries})),
            lifecycle_valid=all(entry.lifecycle_state == "observed" for entry in entries),
        )

    def asset_storage(
        self,
        project_id: str,
        context: WorkflowContext,
        storage_references: Mapping[str, str] | None = None,
    ) -> AssetStorageReport:
        """Report caller-supplied storage references without accessing storage."""

        references = storage_references or {}
        assets = self._foundation.assets(project_id, context).assets
        records = tuple(
            _asset_storage_record(asset, references)
            for asset in assets
        )
        return AssetStorageReport(
            records=records,
            storage_evidence_count=sum(record.storage_evidence_present for record in records),
            unresolved_asset_ids=tuple(
                record.asset.asset_id for record in records if not record.storage_evidence_present
            ),
        )

    def asset_cache(
        self, project_id: str, context: WorkflowContext, *, refresh: bool = False
    ) -> AssetCacheReport:
        """Reuse a current one-page asset projection without repository access."""

        page_reference = self._foundation.workspace(project_id, context).workspace.page_reference
        cache_key = _asset_cache_key(project_id, context, page_reference)
        cached = None if refresh else self._asset_cache.get(cache_key)
        if cached is not None:
            return AssetCacheReport(
                cache_key=cache_key,
                assets=cached,
                cache_hit=True,
                cache_entry_count=self._asset_cache.entry_count,
            )
        assets = self._foundation.assets(project_id, context)
        self._asset_cache.store(cache_key, assets)
        return AssetCacheReport(
            cache_key=cache_key,
            assets=assets,
            cache_hit=False,
            cache_entry_count=self._asset_cache.entry_count,
        )

    def asset_versioning(
        self,
        project_id: str,
        context: WorkflowContext,
        version_references: Mapping[str, str] | None = None,
    ) -> AssetVersioningReport:
        """Report caller-supplied version evidence without changing asset history."""

        references = version_references or {}
        versions = tuple(
            _asset_version_evidence(asset, references)
            for asset in self._foundation.assets(project_id, context).assets
        )
        return AssetVersioningReport(
            versions=versions,
            version_evidence_count=sum(version.version_evidence_present for version in versions),
            unresolved_asset_ids=tuple(
                version.asset.asset_id for version in versions if not version.version_evidence_present
            ),
        )

    def asset_import_export(
        self,
        project_id: str,
        context: WorkflowContext,
        import_references: Mapping[str, str] | None = None,
        export_references: Mapping[str, str] | None = None,
    ) -> AssetImportExportReport:
        """Report caller-supplied transfer evidence without transferring assets."""

        assets = self._foundation.assets(project_id, context).assets
        imports = tuple(
            _asset_import_evidence(asset, import_references or {}) for asset in assets
        )
        exports = tuple(
            _asset_export_evidence(asset, export_references or {}) for asset in assets
        )
        return AssetImportExportReport(
            imports=imports,
            exports=exports,
            import_evidence_count=sum(item.import_evidence_present for item in imports),
            export_evidence_count=sum(item.export_evidence_present for item in exports),
            unresolved_import_asset_ids=tuple(
                item.asset.asset_id for item in imports if not item.import_evidence_present
            ),
            unresolved_export_asset_ids=tuple(
                item.asset.asset_id for item in exports if not item.export_evidence_present
            ),
        )

    def project_workspace(
        self, project_id: str, context: WorkflowContext
    ) -> ProjectWorkspaceReport:
        workspace = self._foundation.workspace(project_id, context)
        project = self._foundation.project(project_id, context)
        assets = self._foundation.assets(project_id, context)
        return _project_workspace_report(workspace, project, assets)

    def workflow_state(
        self, project_id: str, context: WorkflowContext
    ) -> WorkflowStateValidationReport:
        workspace = self._foundation.workspace(project_id, context)
        project = self._foundation.project(project_id, context)
        current_state = context.state
        next_command = None if current_state is PageState.APPROVED else StateMachine().next_command(
            current_state
        )
        findings = _workflow_findings(project)
        return WorkflowStateValidationReport(
            state=WorkflowStateManagerDTO(
                project_id=project_id,
                page_reference=workspace.workspace.page_reference,
                current_state=current_state,
                next_command=next_command,
                storyboard_persisted=project.project.storyboard_persisted,
                quality_review_completed=project.project.quality_review_completed,
            ),
            valid=not findings,
            findings=findings,
        )

    def resources(
        self,
        project_id: str,
        context: WorkflowContext,
        allocations: tuple[ResourceAllocationDTO, ...] = (),
    ) -> ResourceManagerReport:
        page_reference = self._foundation.workspace(project_id, context).workspace.page_reference
        observed = allocations or (
            ResourceAllocationDTO(
                resource_id=f"human-owner:{project_id}:{page_reference}",
                project_id=project_id,
                page_reference=page_reference,
                owner="human-owner",
            ),
        )
        invalid_scope = tuple(
            allocation.resource_id
            for allocation in observed
            if allocation.project_id != project_id or allocation.page_reference != page_reference
        )
        insufficient = tuple(
            allocation.resource_id
            for allocation in observed
            if allocation.available_units < allocation.requested_units
        )
        return ResourceManagerReport(
            allocations=observed,
            allocation_valid=not invalid_scope and not insufficient,
            insufficient_resource_ids=tuple(sorted({*invalid_scope, *insufficient})),
        )

    def templates(
        self,
        project_id: str,
        context: WorkflowContext,
        templates: tuple[ProductionTemplateDTO, ...] = (),
    ) -> TemplateRegistryReport:
        page_reference = self._foundation.workspace(project_id, context).workspace.page_reference
        evidence = {*(str(key) for key in context.artifacts), *(str(key) for key in context.metadata)}
        missing = tuple(
            sorted(
                {
                    evidence_key
                    for template in templates
                    for evidence_key in template.required_evidence
                    if evidence_key not in evidence
                }
            )
        )
        compatible = not missing and all(
            template.page_reference == page_reference
            and not template.template_loaded
            and not template.template_applied
            for template in templates
        )
        return TemplateRegistryReport(
            templates=templates,
            compatible=compatible,
            missing_evidence=missing,
        )

    def production_session(
        self, project_id: str, context: WorkflowContext
    ) -> SessionRecoveryReport:
        workspace = self._foundation.workspace(project_id, context)
        project = self._foundation.project(project_id, context)
        checkpoint_available = bool(context.artifacts) or bool(context.metadata.get("workflow_history"))
        missing: list[str] = []
        if not checkpoint_available:
            missing.append("checkpoint evidence is required")
        if current_state_requires_storyboard(context.state) and not project.project.storyboard_persisted:
            missing.append("persisted storyboard is required")
        if context.state is PageState.APPROVED and not project.project.quality_review_completed:
            missing.append("completed quality review is required")
        return SessionRecoveryReport(
            session=V57ProductionSessionDTO(
                session_id=f"production-session:{project_id}:{workspace.workspace.page_reference}",
                project_id=project_id,
                page_reference=workspace.workspace.page_reference,
                current_state=context.state,
                checkpoint_evidence_available=checkpoint_available,
                recovery_eligible=not missing,
            ),
            missing_recovery_evidence=tuple(missing),
        )

    def production_workspace(
        self,
        project_id: str,
        context: WorkflowContext,
        allocations: tuple[ResourceAllocationDTO, ...] = (),
        templates: tuple[ProductionTemplateDTO, ...] = (),
    ) -> ProductionWorkspaceV2Report:
        return ProductionWorkspaceV2Report(
            assets=self.asset_registry(project_id, context),
            workspace=self.project_workspace(project_id, context),
            workflow=self.workflow_state(project_id, context),
            resources=self.resources(project_id, context, allocations),
            templates=self.templates(project_id, context, templates),
            session=self.production_session(project_id, context),
        )


def _project_workspace_report(
    workspace: WorkspaceManagerReport,
    project: ProjectManagerReport,
    assets: AssetManagerReport,
) -> ProjectWorkspaceReport:
    consistent = (
        workspace.workspace.project_id == project.project.project_id
        and workspace.workspace.page_reference == project.project.page_reference
        and workspace.workspace.current_state == project.project.current_state
    )
    return ProjectWorkspaceReport(
        workspace=ProjectWorkspaceDTO(
            workspace_id=workspace.workspace.workspace_id,
            project_id=project.project.project_id,
            page_reference=project.project.page_reference,
            workflow_state=project.project.current_state,
            workspace_consistent=consistent,
        ),
        asset_reference_count=assets.summary.observed_asset_count,
    )


def _workflow_findings(project: ProjectManagerReport) -> tuple[str, ...]:
    findings: list[str] = []
    state = project.project.current_state
    if current_state_requires_storyboard(state) and not project.project.storyboard_persisted:
        findings.append("persisted storyboard is required")
    if state is PageState.APPROVED and not project.project.quality_review_completed:
        findings.append("completed quality review is required")
    return tuple(findings)


def current_state_requires_storyboard(state: PageState) -> bool:
    return state in (PageState.GENERATED, PageState.QUALITY_CHECKED, PageState.APPROVED)


def _evidence_reference(references: Mapping[str, str], asset_id: str) -> str | None:
    reference = references.get(asset_id)
    if not isinstance(reference, str):
        return None
    return reference.strip() or None


def _asset_storage_record(
    asset: V57AssetLifecycleDTO, references: Mapping[str, str]
) -> AssetStorageRecordDTO:
    reference = _evidence_reference(references, asset.asset_id)
    return AssetStorageRecordDTO(
        asset=asset,
        storage_reference=reference,
        storage_evidence_present=reference is not None,
    )


def _asset_cache_key(
    project_id: str, context: WorkflowContext, page_reference: str
) -> str:
    signature = "\n".join(
        (
            project_id,
            page_reference,
            context.state.value,
            *(f"artifact:{key}" for key in sorted(str(key) for key in context.artifacts)),
            *(f"metadata:{key}" for key in sorted(str(key) for key in context.metadata)),
        )
    )
    return f"asset-cache:{hashlib.sha256(signature.encode('utf-8')).hexdigest()}"


def _asset_version_evidence(
    asset: V57AssetLifecycleDTO, references: Mapping[str, str]
) -> AssetVersionEvidenceDTO:
    reference = _evidence_reference(references, asset.asset_id)
    return AssetVersionEvidenceDTO(
        asset=asset,
        version_reference=reference,
        version_evidence_present=reference is not None,
    )


def _asset_import_evidence(
    asset: V57AssetLifecycleDTO, references: Mapping[str, str]
) -> AssetImportEvidenceDTO:
    reference = _evidence_reference(references, asset.asset_id)
    return AssetImportEvidenceDTO(
        asset=asset,
        import_reference=reference,
        import_evidence_present=reference is not None,
    )


def _asset_export_evidence(
    asset: V57AssetLifecycleDTO, references: Mapping[str, str]
) -> AssetExportEvidenceDTO:
    reference = _evidence_reference(references, asset.asset_id)
    return AssetExportEvidenceDTO(
        asset=asset,
        export_reference=reference,
        export_evidence_present=reference is not None,
    )
