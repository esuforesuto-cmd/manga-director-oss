"""v3.4 governance projections for long-running, human-led production use.

These immutable Application DTOs audit existing v3.4 Foundation and Insight
evidence. They never enforce a policy, persist an audit, mutate a Repository,
apply retention, change a workflow or pipeline, score people, allocate work,
authorize a release, deploy, tag, sign, publish, approve, or remediate.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.domain.state_machine import PageState
from manga_director.production.director import DirectorModel
from manga_director.production.v3_4_foundation import V34FoundationService
from manga_director.production.v3_4_insights import V34InsightsService
from manga_director.repositories.protocols import ProjectRepository
from manga_director.workflow.contracts import WorkflowContext


class KnowledgePolicyDTO(DirectorModel):
    policy_id: Literal["repository_port", "redacted_evidence", "no_implicit_mutation"]
    description: str
    enforcement_applied: bool = False


class KnowledgeComplianceDTO(DirectorModel):
    policy_id: str
    observed: bool
    compliance_verified: bool = False
    remediation_applied: bool = False


class KnowledgeAuditDTO(DirectorModel):
    relationship_count: int = Field(ge=0)
    observed_entry_count: int = Field(ge=0)
    audit_persisted: bool = False


class KnowledgeRetentionPolicyDTO(DirectorModel):
    policy_id: Literal["human_retention_decision"] = "human_retention_decision"
    retention_evaluated: bool = False
    retention_applied: bool = False


class KnowledgeGovernanceSummary(DirectorModel):
    policy_count: int = Field(ge=0)
    compliance_count: int = Field(ge=0)
    repository_mutated: bool = False
    automatic_action_taken: bool = False


class KnowledgeGovernanceReport(DirectorModel):
    policies: tuple[KnowledgePolicyDTO, ...] = ()
    compliance: tuple[KnowledgeComplianceDTO, ...] = ()
    audit: KnowledgeAuditDTO
    retention: KnowledgeRetentionPolicyDTO
    summary: KnowledgeGovernanceSummary
    analysis_only: bool = True


class ProductionOperationsPolicyDTO(DirectorModel):
    policy_id: Literal["state_machine_authority", "human_approval_required"]
    description: str
    enforcement_applied: bool = False


class ProductionComplianceDTO(DirectorModel):
    policy_id: str
    observed: bool
    compliance_verified: bool = False
    remediation_applied: bool = False


class OperationsGovernanceDTO(DirectorModel):
    current_state: PageState
    observed_bottleneck: str | None = None
    pipeline_changed: bool = False
    operation_started: bool = False


class ProductionComplianceReport(DirectorModel):
    compliance: tuple[ProductionComplianceDTO, ...] = ()
    policy_enforced: bool = False
    approval_authorized: bool = False


class ProductionGovernanceSummary(DirectorModel):
    policy_count: int = Field(ge=0)
    compliance_count: int = Field(ge=0)
    workflow_modified: bool = False
    automatic_action_taken: bool = False


class ProductionGovernanceReport(DirectorModel):
    policies: tuple[ProductionOperationsPolicyDTO, ...] = ()
    operations: OperationsGovernanceDTO
    compliance: ProductionComplianceReport
    summary: ProductionGovernanceSummary
    analysis_only: bool = True


class OrganizationPolicyDTO(DirectorModel):
    policy_id: Literal["no_personnel_scoring", "no_assignment", "human_delivery_decision"]
    description: str
    enforcement_applied: bool = False


class OrganizationComplianceDTO(DirectorModel):
    policy_id: str
    observed: bool
    compliance_verified: bool = False
    personnel_action_taken: bool = False


class OrganizationAuditDTO(DirectorModel):
    role_count: int = Field(ge=0)
    handoff_count: int = Field(ge=0)
    audit_persisted: bool = False


class OrganizationGovernanceSummary(DirectorModel):
    policy_count: int = Field(ge=0)
    compliance_count: int = Field(ge=0)
    organization_changed: bool = False
    automatic_action_taken: bool = False


class OrganizationGovernanceReport(DirectorModel):
    policies: tuple[OrganizationPolicyDTO, ...] = ()
    compliance: tuple[OrganizationComplianceDTO, ...] = ()
    audit: OrganizationAuditDTO
    summary: OrganizationGovernanceSummary
    analysis_only: bool = True


class ReleasePolicyDTO(DirectorModel):
    policy_id: Literal["hosted_release_gates", "no_release_authority", "no_implicit_publication"]
    description: str
    enforcement_applied: bool = False


class ReleaseComplianceDTO(DirectorModel):
    policy_id: str
    observed: bool
    compliance_verified: bool = False
    remediation_applied: bool = False


class ReleaseAuditDTO(DirectorModel):
    baseline_count: int = Field(ge=0)
    evidence_count: int = Field(ge=0)
    audit_persisted: bool = False


class ReleaseGovernanceSummary(DirectorModel):
    policy_count: int = Field(ge=0)
    compliance_count: int = Field(ge=0)
    release_authorized: bool = False
    automatic_action_taken: bool = False


class ReleaseGovernanceReport(DirectorModel):
    policies: tuple[ReleasePolicyDTO, ...] = ()
    compliance: tuple[ReleaseComplianceDTO, ...] = ()
    audit: ReleaseAuditDTO
    summary: ReleaseGovernanceSummary
    analysis_only: bool = True


class KnowledgeGovernanceDashboardDTO(DirectorModel):
    report: KnowledgeGovernanceReport
    automatic_action_taken: bool = False


class ProductionGovernanceDashboardDTO(DirectorModel):
    report: ProductionGovernanceReport
    automatic_action_taken: bool = False


class OrganizationGovernanceDashboardDTO(DirectorModel):
    report: OrganizationGovernanceReport
    automatic_action_taken: bool = False


class ReleaseGovernanceDashboardDTO(DirectorModel):
    report: ReleaseGovernanceReport
    automatic_action_taken: bool = False


class V34GovernanceService:
    """Compose governance evidence without operational or release authority."""

    def __init__(
        self,
        foundation: V34FoundationService,
        insights: V34InsightsService,
        repository: ProjectRepository,
    ) -> None:
        self._foundation = foundation
        self._insights = insights
        self._repository = repository

    def knowledge_governance(
        self, project_id: str, context: WorkflowContext
    ) -> KnowledgeGovernanceReport:
        platform = self._foundation.knowledge_platform(project_id, context)
        intelligence = self._insights.knowledge_intelligence(project_id, context)
        policies = (
            KnowledgePolicyDTO(
                policy_id="repository_port",
                description="Knowledge evidence is read through the existing Repository port only.",
            ),
            KnowledgePolicyDTO(
                policy_id="redacted_evidence",
                description="Governance views expose bounded evidence rather than metadata values.",
            ),
            KnowledgePolicyDTO(
                policy_id="no_implicit_mutation",
                description="Knowledge governance never persists, merges, repairs, archives, or deletes.",
            ),
        )
        compliance = tuple(
            KnowledgeComplianceDTO(policy_id=policy.policy_id, observed=True) for policy in policies
        )
        return KnowledgeGovernanceReport(
            policies=policies,
            compliance=compliance,
            audit=KnowledgeAuditDTO(
                relationship_count=intelligence.dependencies.relationship_count,
                observed_entry_count=platform.quality.observed_entry_count,
            ),
            retention=KnowledgeRetentionPolicyDTO(),
            summary=KnowledgeGovernanceSummary(
                policy_count=len(policies), compliance_count=len(compliance)
            ),
        )

    def production_governance(
        self, project_id: str, context: WorkflowContext
    ) -> ProductionGovernanceReport:
        optimization = self._insights.production_optimization(project_id, context)
        policies = (
            ProductionOperationsPolicyDTO(
                policy_id="state_machine_authority",
                description="Only the existing StateMachine validates a workflow transition.",
            ),
            ProductionOperationsPolicyDTO(
                policy_id="human_approval_required",
                description="A completed quality review remains required before approval.",
            ),
        )
        compliance = tuple(
            ProductionComplianceDTO(policy_id=policy.policy_id, observed=True)
            for policy in policies
        )
        return ProductionGovernanceReport(
            policies=policies,
            operations=OperationsGovernanceDTO(
                current_state=context.state,
                observed_bottleneck=optimization.bottleneck.bottleneck,
            ),
            compliance=ProductionComplianceReport(compliance=compliance),
            summary=ProductionGovernanceSummary(
                policy_count=len(policies), compliance_count=len(compliance)
            ),
        )

    def organization_governance(
        self, project_id: str, context: WorkflowContext
    ) -> OrganizationGovernanceReport:
        organization = self._foundation.organization_intelligence(project_id, context)
        policies = (
            OrganizationPolicyDTO(
                policy_id="no_personnel_scoring",
                description="Organization governance does not score people or teams.",
            ),
            OrganizationPolicyDTO(
                policy_id="no_assignment",
                description="Organization governance does not assign work or alter roles.",
            ),
            OrganizationPolicyDTO(
                policy_id="human_delivery_decision",
                description="Delivery commitments remain explicit human decisions.",
            ),
        )
        compliance = tuple(
            OrganizationComplianceDTO(policy_id=policy.policy_id, observed=True)
            for policy in policies
        )
        return OrganizationGovernanceReport(
            policies=policies,
            compliance=compliance,
            audit=OrganizationAuditDTO(
                role_count=len(organization.roles),
                handoff_count=organization.collaboration.observed_handoff_count,
            ),
            summary=OrganizationGovernanceSummary(
                policy_count=len(policies), compliance_count=len(compliance)
            ),
        )

    def release_governance(
        self, project_id: str, context: WorkflowContext
    ) -> ReleaseGovernanceReport:
        release = self._foundation.release_intelligence(project_id, context)
        analytics = self._insights.release_analytics(project_id, context)
        policies = (
            ReleasePolicyDTO(
                policy_id="hosted_release_gates",
                description="Hosted release and compatibility gates remain required outside this DTO.",
            ),
            ReleasePolicyDTO(
                policy_id="no_release_authority",
                description="Governance evidence cannot authorize, tag, sign, or deploy a release.",
            ),
            ReleasePolicyDTO(
                policy_id="no_implicit_publication",
                description="Publication remains an explicit human-controlled release action.",
            ),
        )
        compliance = tuple(
            ReleaseComplianceDTO(policy_id=policy.policy_id, observed=True) for policy in policies
        )
        return ReleaseGovernanceReport(
            policies=policies,
            compliance=compliance,
            audit=ReleaseAuditDTO(
                baseline_count=analytics.compatibility.baseline_count,
                evidence_count=release.executive.evidence_count,
            ),
            summary=ReleaseGovernanceSummary(
                policy_count=len(policies), compliance_count=len(compliance)
            ),
        )

    def knowledge_governance_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> KnowledgeGovernanceDashboardDTO:
        return KnowledgeGovernanceDashboardDTO(
            report=self.knowledge_governance(project_id, context)
        )

    def production_governance_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> ProductionGovernanceDashboardDTO:
        return ProductionGovernanceDashboardDTO(
            report=self.production_governance(project_id, context)
        )

    def organization_governance_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> OrganizationGovernanceDashboardDTO:
        return OrganizationGovernanceDashboardDTO(
            report=self.organization_governance(project_id, context)
        )

    def release_governance_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> ReleaseGovernanceDashboardDTO:
        return ReleaseGovernanceDashboardDTO(report=self.release_governance(project_id, context))
