"""v4.4 Enterprise governance, compliance, and reliability DTOs.

The reports are immutable Application-layer diagnostics over v4.4 Enterprise
Intelligence. They cannot enforce policies, change workspace/team/portfolio
state, approve workflow or marketplace content, publish, bill, monitor,
recover, or call Cloud or external services. StateMachine authority remains
unchanged.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.production.director import DirectorModel
from manga_director.production.v4_4_enterprise_intelligence import (
    EnterpriseDashboardReport,
    MarketplaceInsightsReport,
    PortfolioAnalyticsReport,
    V44EnterpriseIntelligenceService,
)
from manga_director.workflow.contracts import WorkflowContext


class V44EnterprisePolicyDTO(DirectorModel):
    policy_id: str
    project_id: str
    page_reference: str
    state_machine_authoritative: bool = True
    human_approval_required: bool = True
    policy_enforced: bool = False
    policy_persisted: bool = False


class V44WorkspaceComplianceDTO(DirectorModel):
    workspace_id: str
    policy_id: str
    page_count: Literal[1] = 1
    storyboard_evidence_required: bool = True
    completed_quality_review_required: bool = True
    compliance_confirmed: bool = False
    membership_changed: bool = False
    workflow_changed: bool = False


class V44EnterpriseGovernanceSummary(DirectorModel):
    policy_count: int = Field(default=1, ge=0)
    compliance_count: int = Field(default=1, ge=0)
    enforcement_action_count: int = 0
    automatic_action_taken: bool = False


class EnterpriseGovernanceReport(DirectorModel):
    dashboard: EnterpriseDashboardReport
    policy: V44EnterprisePolicyDTO
    compliance: V44WorkspaceComplianceDTO
    summary: V44EnterpriseGovernanceSummary
    planning_only: bool = True


class V44PortfolioPolicyDTO(DirectorModel):
    policy_id: str
    portfolio_id: str
    human_review_required: bool = True
    policy_enforced: bool = False
    policy_persisted: bool = False


class V44PortfolioComplianceDTO(DirectorModel):
    portfolio_id: str
    observed_project_count: int = Field(default=1, ge=0)
    compliance_confirmed: bool = False
    capacity_allocated: bool = False
    schedule_changed: bool = False
    remediation_applied: bool = False


class PortfolioGovernanceReport(DirectorModel):
    portfolio: PortfolioAnalyticsReport
    policy: V44PortfolioPolicyDTO
    compliance: V44PortfolioComplianceDTO
    planning_only: bool = True


class V44MarketplaceGovernanceDTO(DirectorModel):
    policy_id: str
    entry_id: str
    human_review_required: bool = True
    provenance_reviewed: bool = False
    compatibility_confirmed: bool = False
    policy_enforced: bool = False
    publication_approved: bool = False
    payment_approved: bool = False
    billing_approved: bool = False


class MarketplaceGovernanceReport(DirectorModel):
    marketplace: MarketplaceInsightsReport
    governance: V44MarketplaceGovernanceDTO
    planning_only: bool = True


class V44EnterpriseReliabilityDTO(DirectorModel):
    reliability_id: str
    project_id: str
    page_reference: str
    health_status: Literal["not_checked"] = "not_checked"
    health_check_executed: bool = False
    incident_detected: bool = False
    monitoring_active: bool = False
    alert_sent: bool = False
    recovery_attempted: bool = False
    recovery_completed: bool = False


class V44EnterpriseReliabilitySummary(DirectorModel):
    observed_component_count: int = Field(default=5, ge=0)
    incident_count: int = 0
    recovery_count: int = 0
    automatic_action_taken: bool = False


class EnterpriseReliabilityReport(DirectorModel):
    dashboard: EnterpriseDashboardReport
    reliability: V44EnterpriseReliabilityDTO
    summary: V44EnterpriseReliabilitySummary
    planning_only: bool = True


class EnterpriseOperationsValidationReport(DirectorModel):
    governance: EnterpriseGovernanceReport
    portfolio: PortfolioGovernanceReport
    marketplace: MarketplaceGovernanceReport
    reliability: EnterpriseReliabilityReport
    end_to_end_validated: bool = True
    workflow_executed: bool = False
    planning_only: bool = True


class V44EnterpriseGovernanceService:
    """Build non-enforcing enterprise operations evidence reports."""

    def __init__(self, intelligence: V44EnterpriseIntelligenceService | None = None) -> None:
        self._intelligence = intelligence or V44EnterpriseIntelligenceService()

    def enterprise_governance(
        self, project_id: str, context: WorkflowContext
    ) -> EnterpriseGovernanceReport:
        dashboard = self._intelligence.enterprise_dashboard(project_id, context)
        page_reference = dashboard.dashboard.page_reference
        policy_id = f"enterprise-policy:{project_id}:{page_reference}"
        return EnterpriseGovernanceReport(
            dashboard=dashboard,
            policy=V44EnterprisePolicyDTO(
                policy_id=policy_id,
                project_id=project_id,
                page_reference=page_reference,
            ),
            compliance=V44WorkspaceComplianceDTO(
                workspace_id=dashboard.dashboard.workspace_id,
                policy_id=policy_id,
            ),
            summary=V44EnterpriseGovernanceSummary(),
        )

    def workspace_compliance(
        self, project_id: str, context: WorkflowContext
    ) -> V44WorkspaceComplianceDTO:
        return self.enterprise_governance(project_id, context).compliance

    def portfolio_governance(
        self, project_id: str, context: WorkflowContext
    ) -> PortfolioGovernanceReport:
        portfolio = self._intelligence.portfolio_analytics(project_id, context)
        portfolio_id = portfolio.portfolio.portfolio.portfolio_id
        return PortfolioGovernanceReport(
            portfolio=portfolio,
            policy=V44PortfolioPolicyDTO(
                policy_id=f"portfolio-policy:{project_id}", portfolio_id=portfolio_id
            ),
            compliance=V44PortfolioComplianceDTO(portfolio_id=portfolio_id),
        )

    def marketplace_governance(
        self, project_id: str, context: WorkflowContext
    ) -> MarketplaceGovernanceReport:
        marketplace = self._intelligence.marketplace_insights(project_id, context)
        entry_id = marketplace.insight.entry_id
        return MarketplaceGovernanceReport(
            marketplace=marketplace,
            governance=V44MarketplaceGovernanceDTO(
                policy_id=f"marketplace-policy:{project_id}", entry_id=entry_id
            ),
        )

    def enterprise_reliability(
        self, project_id: str, context: WorkflowContext
    ) -> EnterpriseReliabilityReport:
        dashboard = self._intelligence.enterprise_dashboard(project_id, context)
        return EnterpriseReliabilityReport(
            dashboard=dashboard,
            reliability=V44EnterpriseReliabilityDTO(
                reliability_id=f"enterprise-reliability:{project_id}",
                project_id=project_id,
                page_reference=dashboard.dashboard.page_reference,
            ),
            summary=V44EnterpriseReliabilitySummary(),
        )

    def operations_validation(
        self, project_id: str, context: WorkflowContext
    ) -> EnterpriseOperationsValidationReport:
        return EnterpriseOperationsValidationReport(
            governance=self.enterprise_governance(project_id, context),
            portfolio=self.portfolio_governance(project_id, context),
            marketplace=self.marketplace_governance(project_id, context),
            reliability=self.enterprise_reliability(project_id, context),
        )
