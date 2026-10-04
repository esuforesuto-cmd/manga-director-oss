"""v3.5 governance evidence for human-led Enterprise review.

Governance DTOs observe v3.5 Foundation and Insights reports. They do not save
or enforce a policy, persist an audit, alter knowledge/creative/production
evidence, execute a workflow, approve a Page, schedule, remediate, deploy, or
authorize a release.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.production.director import DirectorModel
from manga_director.production.v3_5_foundation import V35FoundationService
from manga_director.production.v3_5_insights import V35InsightsService
from manga_director.repositories.protocols import ProjectRepository
from manga_director.workflow.contracts import WorkflowContext


class KnowledgePolicyDTO(DirectorModel):
    policy_id: Literal["repository_read_only", "no_graph_persistence"]
    description: str
    enforcement_applied: bool = False


class KnowledgeComplianceDTO(DirectorModel):
    policy_id: str
    observed: bool
    compliance_verified: bool = False
    remediation_applied: bool = False


class KnowledgeAuditReport(DirectorModel):
    observed_node_count: int = Field(ge=0)
    observed_edge_count: int = Field(ge=0)
    audit_persisted: bool = False


class KnowledgeLifecyclePolicy(DirectorModel):
    policy_id: Literal["human_lifecycle_decision"] = "human_lifecycle_decision"
    lifecycle_applied: bool = False


class KnowledgeGovernanceSummary(DirectorModel):
    policy_count: int = Field(ge=0)
    compliance_count: int = Field(ge=0)
    repository_mutated: bool = False
    automatic_action_taken: bool = False


class KnowledgeGovernanceReport(DirectorModel):
    policies: tuple[KnowledgePolicyDTO, ...] = ()
    compliance: tuple[KnowledgeComplianceDTO, ...] = ()
    audit: KnowledgeAuditReport
    lifecycle: KnowledgeLifecyclePolicy
    summary: KnowledgeGovernanceSummary
    analysis_only: bool = True


class CreativePolicyDTO(DirectorModel):
    policy_id: Literal["human_creative_decision", "quality_review_required"]
    description: str
    enforcement_applied: bool = False


class CreativeQualityPolicy(DirectorModel):
    policy_id: Literal["approval_requires_completed_quality_review"]
    quality_completed: bool = False
    approval_authorized: bool = False


class CreativeComplianceReport(DirectorModel):
    policy_count: int = Field(ge=0)
    compliance_verified: bool = False
    creative_changed: bool = False


class CreativeAuditReport(DirectorModel):
    observed_metric_count: int = Field(ge=0)
    audit_persisted: bool = False


class CreativeGovernanceDashboard(DirectorModel):
    policies: tuple[CreativePolicyDTO, ...] = ()
    quality: CreativeQualityPolicy
    compliance: CreativeComplianceReport
    audit: CreativeAuditReport
    automatic_action_taken: bool = False


class ProductionPolicyDTO(DirectorModel):
    policy_id: Literal["state_machine_authority", "no_automatic_optimization"]
    description: str
    enforcement_applied: bool = False


class ProductionComplianceReport(DirectorModel):
    policy_count: int = Field(ge=0)
    compliance_verified: bool = False
    workflow_modified: bool = False


class ProductionAuditReport(DirectorModel):
    observed_metric_count: int = Field(ge=0)
    audit_persisted: bool = False


class ProductionGovernanceSummary(DirectorModel):
    policy_count: int = Field(ge=0)
    optimization_applied: bool = False
    deployment_started: bool = False
    automatic_action_taken: bool = False


class ProductionGovernanceDashboard(DirectorModel):
    policies: tuple[ProductionPolicyDTO, ...] = ()
    compliance: ProductionComplianceReport
    audit: ProductionAuditReport
    summary: ProductionGovernanceSummary
    analysis_only: bool = True


class PlatformPolicyDTO(DirectorModel):
    policy_id: Literal["local_evidence_only", "no_external_action"]
    description: str
    enforcement_applied: bool = False


class PlatformAuditDTO(DirectorModel):
    observed_kpi_count: int = Field(ge=0)
    audit_persisted: bool = False


class PlatformComplianceReport(DirectorModel):
    policy_count: int = Field(ge=0)
    compliance_verified: bool = False
    external_action_taken: bool = False


class PlatformGovernanceSummary(DirectorModel):
    policy_count: int = Field(ge=0)
    monitoring_started: bool = False
    release_authorized: bool = False
    automatic_action_taken: bool = False


class PlatformGovernanceDashboard(DirectorModel):
    policies: tuple[PlatformPolicyDTO, ...] = ()
    audit: PlatformAuditDTO
    compliance: PlatformComplianceReport
    summary: PlatformGovernanceSummary
    analysis_only: bool = True


class KnowledgeGovernanceDashboardDTO(DirectorModel):
    report: KnowledgeGovernanceReport
    automatic_action_taken: bool = False


class CreativeGovernanceDashboardDTO(DirectorModel):
    report: CreativeGovernanceDashboard
    automatic_action_taken: bool = False


class ProductionGovernanceDashboardDTO(DirectorModel):
    report: ProductionGovernanceDashboard
    automatic_action_taken: bool = False


class PlatformGovernanceDashboardDTO(DirectorModel):
    report: PlatformGovernanceDashboard
    automatic_action_taken: bool = False


class V35GovernanceService:
    """Compose policy/compliance/audit evidence without governance authority."""

    def __init__(
        self,
        foundation: V35FoundationService,
        insights: V35InsightsService,
        repository: ProjectRepository,
    ) -> None:
        self._foundation = foundation
        self._insights = insights
        self._repository = repository

    def knowledge_governance(
        self, project_id: str, context: WorkflowContext
    ) -> KnowledgeGovernanceReport:
        graph = self._foundation.knowledge_graph(project_id, context)
        policies = (
            KnowledgePolicyDTO(
                policy_id="repository_read_only",
                description="Knowledge evidence is read through the existing Repository port only.",
            ),
            KnowledgePolicyDTO(
                policy_id="no_graph_persistence",
                description="Governance never persists a graph, index, or relationship.",
            ),
        )
        compliance = tuple(
            KnowledgeComplianceDTO(policy_id=item.policy_id, observed=True) for item in policies
        )
        return KnowledgeGovernanceReport(
            policies=policies,
            compliance=compliance,
            audit=KnowledgeAuditReport(
                observed_node_count=len(graph.graph.nodes),
                observed_edge_count=len(graph.graph.edges),
            ),
            lifecycle=KnowledgeLifecyclePolicy(),
            summary=KnowledgeGovernanceSummary(
                policy_count=len(policies), compliance_count=len(compliance)
            ),
        )

    def creative_governance(
        self, project_id: str, context: WorkflowContext
    ) -> CreativeGovernanceDashboard:
        creative = self._insights.creative_analytics(project_id, context)
        policies = (
            CreativePolicyDTO(
                policy_id="human_creative_decision",
                description="Creative analysis is advisory and does not alter creative inputs.",
            ),
            CreativePolicyDTO(
                policy_id="quality_review_required",
                description="Completed quality review remains required before approval.",
            ),
        )
        return CreativeGovernanceDashboard(
            policies=policies,
            quality=CreativeQualityPolicy(policy_id="approval_requires_completed_quality_review"),
            compliance=CreativeComplianceReport(policy_count=len(policies)),
            audit=CreativeAuditReport(observed_metric_count=creative.trend.observed_metric_count),
        )

    def production_governance(
        self, project_id: str, context: WorkflowContext
    ) -> ProductionGovernanceDashboard:
        production = self._insights.production_analytics(project_id, context)
        policies = (
            ProductionPolicyDTO(
                policy_id="state_machine_authority",
                description="Only the existing StateMachine validates workflow transitions.",
            ),
            ProductionPolicyDTO(
                policy_id="no_automatic_optimization",
                description="Production optimization reports cannot change workflow or capacity.",
            ),
        )
        return ProductionGovernanceDashboard(
            policies=policies,
            compliance=ProductionComplianceReport(policy_count=len(policies)),
            audit=ProductionAuditReport(
                observed_metric_count=production.optimization.observed_metric_count
            ),
            summary=ProductionGovernanceSummary(policy_count=len(policies)),
        )

    def platform_governance(
        self, project_id: str, context: WorkflowContext
    ) -> PlatformGovernanceDashboard:
        platform = self._insights.platform_intelligence(project_id, context)
        self._repository.load(project_id)
        policies = (
            PlatformPolicyDTO(
                policy_id="local_evidence_only",
                description="Platform reports aggregate supplied local evidence only.",
            ),
            PlatformPolicyDTO(
                policy_id="no_external_action",
                description="Platform governance cannot monitor, enforce, authorize, or act.",
            ),
        )
        return PlatformGovernanceDashboard(
            policies=policies,
            audit=PlatformAuditDTO(observed_kpi_count=len(platform.kpis)),
            compliance=PlatformComplianceReport(policy_count=len(policies)),
            summary=PlatformGovernanceSummary(policy_count=len(policies)),
        )

    def knowledge_governance_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> KnowledgeGovernanceDashboardDTO:
        return KnowledgeGovernanceDashboardDTO(
            report=self.knowledge_governance(project_id, context)
        )

    def creative_governance_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> CreativeGovernanceDashboardDTO:
        return CreativeGovernanceDashboardDTO(report=self.creative_governance(project_id, context))

    def production_governance_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> ProductionGovernanceDashboardDTO:
        return ProductionGovernanceDashboardDTO(
            report=self.production_governance(project_id, context)
        )

    def platform_governance_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> PlatformGovernanceDashboardDTO:
        return PlatformGovernanceDashboardDTO(report=self.platform_governance(project_id, context))
