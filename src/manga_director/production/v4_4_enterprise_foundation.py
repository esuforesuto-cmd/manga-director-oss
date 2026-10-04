"""v4.4 Enterprise Creative Platform foundation DTOs without side effects.

The module provides immutable Application-layer projections for enterprise
workspace, team, portfolio, extension-registry, and marketplace-catalog
evidence. It does not alter Projects, repositories, workflows, extensions, or
plugins; it does not discover, install, load, execute, publish, bill, or call
external services. The domain StateMachine remains the transition authority.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.domain.state_machine import PageState
from manga_director.production.director import DirectorModel
from manga_director.workflow.contracts import WorkflowContext


class V44EnterpriseWorkspaceDTO(DirectorModel):
    workspace_id: str
    project_id: str
    page_reference: str
    page_count: Literal[1] = 1
    workspace_created: bool = False
    workspace_persisted: bool = False


class V44WorkspaceSessionDTO(DirectorModel):
    session_id: str
    workspace_id: str
    workflow_state: PageState
    session_started: bool = False
    session_persisted: bool = False


class V44WorkspaceSnapshotDTO(DirectorModel):
    snapshot_id: str
    workspace_id: str
    page_reference: str
    snapshot_captured: bool = False
    snapshot_persisted: bool = False


class V44EnterpriseWorkspaceSummary(DirectorModel):
    workspace_count: int = Field(default=1, ge=0)
    session_count: int = Field(default=1, ge=0)
    snapshot_count: int = 0
    workflow_changed: bool = False
    automatic_action_taken: bool = False


class EnterpriseWorkspaceFoundationReport(DirectorModel):
    workspace: V44EnterpriseWorkspaceDTO
    session: V44WorkspaceSessionDTO
    snapshot: V44WorkspaceSnapshotDTO
    summary: V44EnterpriseWorkspaceSummary
    planning_only: bool = True


class V44TeamDTO(DirectorModel):
    team_id: str
    workspace_id: str
    declared_member_count: int = Field(default=1, ge=0)
    team_created: bool = False
    team_persisted: bool = False


class V44TeamMemberDTO(DirectorModel):
    member_id: str
    team_id: str
    role: Literal["human_owner"] = "human_owner"
    membership_changed: bool = False
    permission_granted: bool = False


class V44TeamReviewDTO(DirectorModel):
    review_id: str
    team_id: str
    page_reference: str
    storyboard_required: bool = True
    completed_quality_review_required: bool = True
    assigned: bool = False
    approval_granted: bool = False


class V44TeamSummary(DirectorModel):
    team_count: int = Field(default=1, ge=0)
    member_count: int = Field(default=1, ge=0)
    review_count: int = Field(default=1, ge=0)
    assignment_count: int = 0
    automatic_action_taken: bool = False


class TeamFoundationReport(DirectorModel):
    team: V44TeamDTO
    member: V44TeamMemberDTO
    review: V44TeamReviewDTO
    summary: V44TeamSummary
    planning_only: bool = True


class V44PortfolioDTO(DirectorModel):
    portfolio_id: str
    project_ids: tuple[str, ...]
    project_count: Literal[1] = 1
    portfolio_created: bool = False
    portfolio_persisted: bool = False


class V44PortfolioProjectDTO(DirectorModel):
    project_id: str
    page_reference: str
    workflow_state: PageState
    health: Literal["observed"] = "observed"
    project_changed: bool = False


class V44PortfolioSummary(DirectorModel):
    project_count: Literal[1] = 1
    observed_project_count: int = Field(default=1, ge=0)
    milestone_count: int = 0
    capacity_allocated: bool = False
    schedule_changed: bool = False


class PortfolioFoundationReport(DirectorModel):
    portfolio: V44PortfolioDTO
    project: V44PortfolioProjectDTO
    summary: V44PortfolioSummary
    planning_only: bool = True


class V44ExtensionManifestDTO(DirectorModel):
    extension_id: str
    declared_version: str = "not_loaded"
    capabilities: tuple[str, ...] = ()
    provenance_supplied: bool = False
    extension_loaded: bool = False
    extension_executed: bool = False


class V44ExtensionCompatibilityDTO(DirectorModel):
    extension_id: str
    extension_sdk_contract: Literal["existing_sdk_unchanged"] = "existing_sdk_unchanged"
    compatibility_assessed: bool = False
    permission_granted: bool = False


class V44ExtensionRegistryDTO(DirectorModel):
    registry_id: str
    extension_ids: tuple[str, ...] = ()
    registry_persisted: bool = False
    remote_discovery_enabled: bool = False


class V44ExtensionRegistrySummary(DirectorModel):
    manifest_count: int = Field(default=1, ge=0)
    loaded_extension_count: int = 0
    executed_extension_count: int = 0
    automatic_action_taken: bool = False


class ExtensionRegistryFoundationReport(DirectorModel):
    manifest: V44ExtensionManifestDTO
    compatibility: V44ExtensionCompatibilityDTO
    registry: V44ExtensionRegistryDTO
    summary: V44ExtensionRegistrySummary
    planning_only: bool = True


class V44MarketplaceCatalogDTO(DirectorModel):
    catalog_id: str
    entry_ids: tuple[str, ...] = ()
    catalog_persisted: bool = False
    remote_discovery_enabled: bool = False


class V44MarketplaceEntryDTO(DirectorModel):
    entry_id: str
    workflow_id: str
    page_count: Literal[1] = 1
    provenance_supplied: bool = False
    downloaded: bool = False
    installed: bool = False
    executed: bool = False
    published: bool = False


class V44MarketplacePolicyDTO(DirectorModel):
    entry_id: str
    human_review_required: bool = True
    policy_enforced: bool = False
    payment_processed: bool = False
    billing_performed: bool = False


class V44MarketplaceCatalogSummary(DirectorModel):
    catalog_count: int = Field(default=1, ge=0)
    entry_count: int = Field(default=1, ge=0)
    installed_entry_count: int = 0
    published_entry_count: int = 0
    automatic_action_taken: bool = False


class MarketplaceCatalogFoundationReport(DirectorModel):
    catalog: V44MarketplaceCatalogDTO
    entry: V44MarketplaceEntryDTO
    policy: V44MarketplacePolicyDTO
    summary: V44MarketplaceCatalogSummary
    planning_only: bool = True


class V44EnterpriseFoundationService:
    """Build non-executing Enterprise Creative Platform DTO projections."""

    def enterprise_workspace(
        self, project_id: str, context: WorkflowContext
    ) -> EnterpriseWorkspaceFoundationReport:
        page_reference = _page_reference(context)
        workspace_id = f"enterprise-workspace:{project_id}"
        return EnterpriseWorkspaceFoundationReport(
            workspace=V44EnterpriseWorkspaceDTO(
                workspace_id=workspace_id,
                project_id=project_id,
                page_reference=page_reference,
            ),
            session=V44WorkspaceSessionDTO(
                session_id=f"workspace-session:{project_id}:{page_reference}",
                workspace_id=workspace_id,
                workflow_state=context.state,
            ),
            snapshot=V44WorkspaceSnapshotDTO(
                snapshot_id=f"workspace-snapshot:{project_id}:{page_reference}",
                workspace_id=workspace_id,
                page_reference=page_reference,
            ),
            summary=V44EnterpriseWorkspaceSummary(),
        )

    def team(self, project_id: str, context: WorkflowContext) -> TeamFoundationReport:
        page_reference = _page_reference(context)
        workspace_id = f"enterprise-workspace:{project_id}"
        team_id = f"team:{project_id}"
        return TeamFoundationReport(
            team=V44TeamDTO(team_id=team_id, workspace_id=workspace_id),
            member=V44TeamMemberDTO(member_id="human-owner", team_id=team_id),
            review=V44TeamReviewDTO(
                review_id=f"team-review:{project_id}:{page_reference}",
                team_id=team_id,
                page_reference=page_reference,
            ),
            summary=V44TeamSummary(),
        )

    def portfolio(self, project_id: str, context: WorkflowContext) -> PortfolioFoundationReport:
        page_reference = _page_reference(context)
        return PortfolioFoundationReport(
            portfolio=V44PortfolioDTO(
                portfolio_id=f"portfolio:{project_id}", project_ids=(project_id,)
            ),
            project=V44PortfolioProjectDTO(
                project_id=project_id,
                page_reference=page_reference,
                workflow_state=context.state,
            ),
            summary=V44PortfolioSummary(),
        )

    def extension_registry(
        self, project_id: str, context: WorkflowContext
    ) -> ExtensionRegistryFoundationReport:
        page_reference = _page_reference(context)
        extension_id = f"extension:{project_id}:{page_reference}"
        return ExtensionRegistryFoundationReport(
            manifest=V44ExtensionManifestDTO(extension_id=extension_id),
            compatibility=V44ExtensionCompatibilityDTO(extension_id=extension_id),
            registry=V44ExtensionRegistryDTO(
                registry_id=f"extension-registry:{project_id}", extension_ids=(extension_id,)
            ),
            summary=V44ExtensionRegistrySummary(),
        )

    def marketplace_catalog(
        self, project_id: str, context: WorkflowContext
    ) -> MarketplaceCatalogFoundationReport:
        page_reference = _page_reference(context)
        entry_id = f"marketplace-entry:{project_id}:{page_reference}"
        return MarketplaceCatalogFoundationReport(
            catalog=V44MarketplaceCatalogDTO(
                catalog_id=f"marketplace-catalog:{project_id}", entry_ids=(entry_id,)
            ),
            entry=V44MarketplaceEntryDTO(entry_id=entry_id, workflow_id="not_installed"),
            policy=V44MarketplacePolicyDTO(entry_id=entry_id),
            summary=V44MarketplaceCatalogSummary(),
        )


def _page_reference(context: WorkflowContext) -> str:
    page_id = context.page.get("id")
    return str(page_id) if page_id is not None else "page"
