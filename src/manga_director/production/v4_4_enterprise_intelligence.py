"""v4.4 Enterprise Creative Platform intelligence DTOs without side effects.

These Application-layer reports analyze supplied v4.4 foundation evidence. They
do not change workspace, team, portfolio, extension, marketplace, repository,
or workflow state; they do not discover, install, load, execute, publish, pay,
bill, schedule, allocate, monitor, or call external services.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.production.director import DirectorModel
from manga_director.production.v4_4_enterprise_foundation import (
    ExtensionRegistryFoundationReport,
    MarketplaceCatalogFoundationReport,
    PortfolioFoundationReport,
    TeamFoundationReport,
    V44EnterpriseFoundationService,
)
from manga_director.workflow.contracts import WorkflowContext


class V44CollaborationMetricDTO(DirectorModel):
    team_id: str
    observed_member_count: int = Field(default=1, ge=0)
    observed_review_count: int = Field(default=1, ge=0)
    assignment_count: int = 0
    metric_persisted: bool = False


class V44CollaborationInsightDTO(DirectorModel):
    team_id: str
    status: Literal["review_required"] = "review_required"
    storyboard_evidence_required: bool = True
    completed_quality_review_required: bool = True
    recommendation: str = "Keep collaboration decisions with the human owner."
    automatic_action_taken: bool = False


class CollaborationIntelligenceReport(DirectorModel):
    team: TeamFoundationReport
    metrics: V44CollaborationMetricDTO
    insight: V44CollaborationInsightDTO
    planning_only: bool = True


class V44PortfolioMetricDTO(DirectorModel):
    portfolio_id: str
    observed_project_count: int = Field(default=1, ge=0)
    observed_page_count: int = Field(default=1, ge=0)
    health_score: int = Field(default=0, ge=0, le=100)
    metric_persisted: bool = False


class V44PortfolioRiskDTO(DirectorModel):
    portfolio_id: str
    risk_level: Literal["not_assessed"] = "not_assessed"
    schedule_alert_sent: bool = False
    allocation_changed: bool = False
    remediation_applied: bool = False


class PortfolioAnalyticsReport(DirectorModel):
    portfolio: PortfolioFoundationReport
    metrics: V44PortfolioMetricDTO
    risk: V44PortfolioRiskDTO
    planning_only: bool = True


class V44ExtensionInsightDTO(DirectorModel):
    extension_id: str
    declared_capability_count: int = Field(default=0, ge=0)
    provenance_available: bool = False
    compatibility_status: Literal["not_assessed"] = "not_assessed"
    extension_loaded: bool = False
    extension_executed: bool = False


class V44ExtensionRecommendationDTO(DirectorModel):
    extension_id: str
    message: str = "Require human provenance and compatibility review before any opt-in use."
    permission_granted: bool = False
    automatic_action_taken: bool = False


class ExtensionIntelligenceReport(DirectorModel):
    registry: ExtensionRegistryFoundationReport
    insight: V44ExtensionInsightDTO
    recommendation: V44ExtensionRecommendationDTO
    planning_only: bool = True


class V44MarketplaceInsightDTO(DirectorModel):
    entry_id: str
    workflow_id: str
    page_count: Literal[1] = 1
    provenance_available: bool = False
    compatibility_status: Literal["not_assessed"] = "not_assessed"
    catalog_persisted: bool = False


class V44MarketplaceReadinessDTO(DirectorModel):
    entry_id: str
    human_review_required: bool = True
    download_enabled: bool = False
    installation_enabled: bool = False
    execution_enabled: bool = False
    publication_enabled: bool = False
    payment_enabled: bool = False
    billing_enabled: bool = False


class MarketplaceInsightsReport(DirectorModel):
    marketplace: MarketplaceCatalogFoundationReport
    insight: V44MarketplaceInsightDTO
    readiness: V44MarketplaceReadinessDTO
    planning_only: bool = True


class V44EnterpriseDashboardDTO(DirectorModel):
    project_id: str
    page_reference: str
    workspace_id: str
    team_id: str
    portfolio_id: str
    extension_registry_id: str
    marketplace_catalog_id: str
    collaboration: CollaborationIntelligenceReport
    portfolio: PortfolioAnalyticsReport
    extension: ExtensionIntelligenceReport
    marketplace: MarketplaceInsightsReport
    dashboard_persisted: bool = False
    dashboard_published: bool = False
    automatic_action_taken: bool = False


class EnterpriseDashboardReport(DirectorModel):
    dashboard: V44EnterpriseDashboardDTO
    planning_only: bool = True


class V44EnterpriseIntelligenceService:
    """Build non-executing collaboration, portfolio, extension, and catalog reports."""

    def __init__(self, foundation: V44EnterpriseFoundationService | None = None) -> None:
        self._foundation = foundation or V44EnterpriseFoundationService()

    def collaboration_intelligence(
        self, project_id: str, context: WorkflowContext
    ) -> CollaborationIntelligenceReport:
        team = self._foundation.team(project_id, context)
        return CollaborationIntelligenceReport(
            team=team,
            metrics=V44CollaborationMetricDTO(team_id=team.team.team_id),
            insight=V44CollaborationInsightDTO(team_id=team.team.team_id),
        )

    def portfolio_analytics(
        self, project_id: str, context: WorkflowContext
    ) -> PortfolioAnalyticsReport:
        portfolio = self._foundation.portfolio(project_id, context)
        return PortfolioAnalyticsReport(
            portfolio=portfolio,
            metrics=V44PortfolioMetricDTO(portfolio_id=portfolio.portfolio.portfolio_id),
            risk=V44PortfolioRiskDTO(portfolio_id=portfolio.portfolio.portfolio_id),
        )

    def extension_intelligence(
        self, project_id: str, context: WorkflowContext
    ) -> ExtensionIntelligenceReport:
        registry = self._foundation.extension_registry(project_id, context)
        extension_id = registry.manifest.extension_id
        return ExtensionIntelligenceReport(
            registry=registry,
            insight=V44ExtensionInsightDTO(
                extension_id=extension_id,
                declared_capability_count=len(registry.manifest.capabilities),
                provenance_available=registry.manifest.provenance_supplied,
            ),
            recommendation=V44ExtensionRecommendationDTO(extension_id=extension_id),
        )

    def marketplace_insights(
        self, project_id: str, context: WorkflowContext
    ) -> MarketplaceInsightsReport:
        marketplace = self._foundation.marketplace_catalog(project_id, context)
        entry = marketplace.entry
        return MarketplaceInsightsReport(
            marketplace=marketplace,
            insight=V44MarketplaceInsightDTO(
                entry_id=entry.entry_id,
                workflow_id=entry.workflow_id,
                provenance_available=entry.provenance_supplied,
            ),
            readiness=V44MarketplaceReadinessDTO(entry_id=entry.entry_id),
        )

    def enterprise_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> EnterpriseDashboardReport:
        workspace = self._foundation.enterprise_workspace(project_id, context)
        collaboration = self.collaboration_intelligence(project_id, context)
        portfolio = self.portfolio_analytics(project_id, context)
        extension = self.extension_intelligence(project_id, context)
        marketplace = self.marketplace_insights(project_id, context)
        return EnterpriseDashboardReport(
            dashboard=V44EnterpriseDashboardDTO(
                project_id=project_id,
                page_reference=workspace.workspace.page_reference,
                workspace_id=workspace.workspace.workspace_id,
                team_id=collaboration.team.team.team_id,
                portfolio_id=portfolio.portfolio.portfolio.portfolio_id,
                extension_registry_id=extension.registry.registry.registry_id,
                marketplace_catalog_id=marketplace.marketplace.catalog.catalog_id,
                collaboration=collaboration,
                portfolio=portfolio,
                extension=extension,
                marketplace=marketplace,
            )
        )
