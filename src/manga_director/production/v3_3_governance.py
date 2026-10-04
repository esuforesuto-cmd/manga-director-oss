"""v3.3 governance projections for production-grade, human-led operation.

The services in this module expose policies, compliance observations, audits,
and summaries using existing v3.3 read-only reports.  They never enforce a
policy, modify a workflow, approve work, apply retention, mutate Repository
data, allocate resources, schedule work, or commit delivery.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.domain.state_machine import PageState
from manga_director.production.director import DirectorModel
from manga_director.production.v3_3_foundation import V33FoundationService
from manga_director.production.v3_3_insights import V33InsightsService
from manga_director.repositories.protocols import ProjectRepository
from manga_director.workflow.contracts import WorkflowContext


class ProductionPolicyDTO(DirectorModel):
    policy_id: Literal["state_machine_authority", "human_approval_required"]
    description: str
    enforcement_applied: bool = False


class ProductionComplianceDTO(DirectorModel):
    policy_id: str
    observed: bool
    compliance_verified: bool = False
    remediation_applied: bool = False


class PipelineGovernanceDTO(DirectorModel):
    current_state: PageState
    suggested_next_command: str | None = None
    pipeline_changed: bool = False
    execution_started: bool = False


class ProductionAuditReport(DirectorModel):
    observations: tuple[str, ...] = ()
    observation_count: int = Field(ge=0)
    audit_persisted: bool = False


class ProductionComplianceReport(DirectorModel):
    compliance: tuple[ProductionComplianceDTO, ...] = ()
    policy_enforced: bool = False
    approval_authorized: bool = False


class ProductionGovernanceSummary(DirectorModel):
    policy_count: int = Field(ge=0)
    compliance_count: int = Field(ge=0)
    automatic_action_taken: bool = False


class ProductionGovernanceReport(DirectorModel):
    policies: tuple[ProductionPolicyDTO, ...] = ()
    pipeline: PipelineGovernanceDTO
    audit: ProductionAuditReport
    compliance: ProductionComplianceReport
    summary: ProductionGovernanceSummary
    analysis_only: bool = True


class QualityPolicyDTO(DirectorModel):
    policy_id: Literal["quality_before_approval", "storyboard_before_generation"]
    description: str
    enforcement_applied: bool = False


class QualityComplianceDTO(DirectorModel):
    policy_id: str
    observed: bool
    compliance_verified: bool = False
    correction_applied: bool = False


class QualityAuditDTO(DirectorModel):
    finding_count: int = Field(ge=0)
    review_evidence_present: bool
    audit_persisted: bool = False


class QualityComplianceReport(DirectorModel):
    compliance: tuple[QualityComplianceDTO, ...] = ()
    approval_authorized: bool = False
    remediation_applied: bool = False


class QualityGovernanceSummary(DirectorModel):
    policy_count: int = Field(ge=0)
    audit_finding_count: int = Field(ge=0)
    automatic_action_taken: bool = False


class QualityGovernanceReport(DirectorModel):
    policies: tuple[QualityPolicyDTO, ...] = ()
    audit: QualityAuditDTO
    compliance: QualityComplianceReport
    summary: QualityGovernanceSummary
    analysis_only: bool = True


class AssetGovernanceDTO(DirectorModel):
    asset_count: int = Field(ge=0)
    values_redacted: bool = True
    governance_applied: bool = False


class AssetComplianceDTO(DirectorModel):
    control_id: Literal["repository_port", "redacted_metadata", "no_implicit_mutation"]
    observed: bool
    compliance_verified: bool = False
    remediation_applied: bool = False


class AssetAuditDTO(DirectorModel):
    dependency_count: int = Field(ge=0)
    history_count: int = Field(ge=0)
    audit_persisted: bool = False


class AssetRetentionPolicyDTO(DirectorModel):
    policy_id: Literal["human_retention_decision"] = "human_retention_decision"
    retention_evaluated: bool = False
    retention_applied: bool = False


class AssetGovernanceSummary(DirectorModel):
    asset_count: int = Field(ge=0)
    control_count: int = Field(ge=0)
    repository_mutated: bool = False
    automatic_action_taken: bool = False


class AssetGovernanceReport(DirectorModel):
    governance: AssetGovernanceDTO
    compliance: tuple[AssetComplianceDTO, ...] = ()
    audit: AssetAuditDTO
    retention: AssetRetentionPolicyDTO
    summary: AssetGovernanceSummary
    analysis_only: bool = True


class ProjectGovernanceDTO(DirectorModel):
    project_id: str
    current_state: PageState
    governance_applied: bool = False
    operation_started: bool = False


class ProjectComplianceDTO(DirectorModel):
    control_id: Literal["no_scheduling", "no_allocation", "no_delivery_commitment"]
    observed: bool
    compliance_verified: bool = False
    remediation_applied: bool = False


class RiskGovernanceDTO(DirectorModel):
    observed_risk_count: int = Field(ge=0)
    risk_accepted: bool = False
    mitigation_applied: bool = False


class GovernanceDashboardDTO(DirectorModel):
    project_id: str
    policy_count: int = Field(ge=0)
    observation_count: int = Field(ge=0)
    automatic_action_taken: bool = False


class ProjectGovernanceSummary(DirectorModel):
    project_id: str
    compliance_count: int = Field(ge=0)
    delivery_committed: bool = False
    automatic_action_taken: bool = False


class ProjectGovernanceReport(DirectorModel):
    governance: ProjectGovernanceDTO
    compliance: tuple[ProjectComplianceDTO, ...] = ()
    risk: RiskGovernanceDTO
    dashboard: GovernanceDashboardDTO
    summary: ProjectGovernanceSummary
    analysis_only: bool = True


class ProductionGovernanceDashboardDTO(DirectorModel):
    report: ProductionGovernanceReport
    automatic_action_taken: bool = False


class QualityGovernanceDashboardDTO(DirectorModel):
    report: QualityGovernanceReport
    automatic_action_taken: bool = False


class AssetGovernanceDashboardDTO(DirectorModel):
    report: AssetGovernanceReport
    automatic_action_taken: bool = False


class ProjectGovernanceDashboardDTO(DirectorModel):
    report: ProjectGovernanceReport
    automatic_action_taken: bool = False


class V33GovernanceService:
    """Build v3.3 governance DTOs without operational authority."""

    def __init__(
        self,
        foundation: V33FoundationService,
        insights: V33InsightsService,
        repository: ProjectRepository,
    ) -> None:
        self._foundation = foundation
        self._insights = insights
        self._repository = repository

    def production_governance(
        self, project_id: str, context: WorkflowContext
    ) -> ProductionGovernanceReport:
        production = self._insights.production_intelligence(project_id, context)
        policies = (
            ProductionPolicyDTO(
                policy_id="state_machine_authority",
                description="Only the existing StateMachine validates a workflow transition.",
            ),
            ProductionPolicyDTO(
                policy_id="human_approval_required",
                description="Human approval remains required after completed quality review.",
            ),
        )
        compliance = tuple(
            ProductionComplianceDTO(policy_id=policy.policy_id, observed=True)
            for policy in policies
        )
        return ProductionGovernanceReport(
            policies=policies,
            pipeline=PipelineGovernanceDTO(
                current_state=context.state,
                suggested_next_command=production.summary.next_command,
            ),
            audit=ProductionAuditReport(
                observations=tuple(insight.message for insight in production.insights),
                observation_count=len(production.insights),
            ),
            compliance=ProductionComplianceReport(compliance=compliance),
            summary=ProductionGovernanceSummary(
                policy_count=len(policies), compliance_count=len(compliance)
            ),
        )

    def quality_governance(self, context: WorkflowContext) -> QualityGovernanceReport:
        quality = self._foundation.quality_intelligence(context)
        policies = (
            QualityPolicyDTO(
                policy_id="quality_before_approval",
                description="A completed quality review is required before approval.",
            ),
            QualityPolicyDTO(
                policy_id="storyboard_before_generation",
                description="A persisted storyboard is required before image generation.",
            ),
        )
        observed = {rule.rule_id: rule.observed for rule in quality.rules}
        compliance = tuple(
            QualityComplianceDTO(policy_id=policy.policy_id, observed=observed.get(policy.policy_id, False))
            for policy in policies
        )
        return QualityGovernanceReport(
            policies=policies,
            audit=QualityAuditDTO(
                finding_count=quality.summary.finding_count,
                review_evidence_present=quality.dashboard.quality_review_completed,
            ),
            compliance=QualityComplianceReport(compliance=compliance),
            summary=QualityGovernanceSummary(
                policy_count=len(policies), audit_finding_count=quality.summary.finding_count
            ),
        )

    def asset_governance(
        self, project_id: str, context: WorkflowContext
    ) -> AssetGovernanceReport:
        lifecycle = self._foundation.asset_lifecycle(project_id, context)
        controls = (
            AssetComplianceDTO(control_id="repository_port", observed=True),
            AssetComplianceDTO(control_id="redacted_metadata", observed=True),
            AssetComplianceDTO(control_id="no_implicit_mutation", observed=True),
        )
        return AssetGovernanceReport(
            governance=AssetGovernanceDTO(asset_count=lifecycle.summary.asset_count),
            compliance=controls,
            audit=AssetAuditDTO(
                dependency_count=lifecycle.summary.dependency_count,
                history_count=len(lifecycle.history),
            ),
            retention=AssetRetentionPolicyDTO(),
            summary=AssetGovernanceSummary(
                asset_count=lifecycle.summary.asset_count, control_count=len(controls)
            ),
        )

    def project_governance(
        self, project_id: str, context: WorkflowContext
    ) -> ProjectGovernanceReport:
        project = self._repository.load(project_id)
        operations = self._insights.project_operations(project_id, context)
        controls = (
            ProjectComplianceDTO(control_id="no_scheduling", observed=True),
            ProjectComplianceDTO(control_id="no_allocation", observed=True),
            ProjectComplianceDTO(control_id="no_delivery_commitment", observed=True),
        )
        return ProjectGovernanceReport(
            governance=ProjectGovernanceDTO(project_id=project.id, current_state=context.state),
            compliance=controls,
            risk=RiskGovernanceDTO(observed_risk_count=operations.risks.risk_count),
            dashboard=GovernanceDashboardDTO(
                project_id=project.id,
                policy_count=len(controls),
                observation_count=operations.summary.observation_count,
            ),
            summary=ProjectGovernanceSummary(
                project_id=project.id, compliance_count=len(controls)
            ),
        )

    def production_governance_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> ProductionGovernanceDashboardDTO:
        return ProductionGovernanceDashboardDTO(
            report=self.production_governance(project_id, context)
        )

    def quality_governance_dashboard(
        self, context: WorkflowContext
    ) -> QualityGovernanceDashboardDTO:
        return QualityGovernanceDashboardDTO(report=self.quality_governance(context))

    def asset_governance_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> AssetGovernanceDashboardDTO:
        return AssetGovernanceDashboardDTO(report=self.asset_governance(project_id, context))

    def project_governance_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> ProjectGovernanceDashboardDTO:
        return ProjectGovernanceDashboardDTO(report=self.project_governance(project_id, context))
