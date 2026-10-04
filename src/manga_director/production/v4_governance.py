"""Read-only governance DTOs for the v4 Creative Operating System.

Governance projections observe v4 Intelligence reports and describe policy,
audit, integrity, and compliance evidence for a human reviewer.  They cannot
persist or enforce policies, alter content or graph evidence, execute a
workflow, complete review, generate an image, or approve a page.
"""

from __future__ import annotations

from pydantic import Field

from manga_director.production.director import DirectorModel
from manga_director.production.v4_intelligence import V4IntelligenceService
from manga_director.repositories.protocols import ProjectRepository
from manga_director.workflow.contracts import WorkflowContext


class WorkspacePolicyDTO(DirectorModel):
    policy_id: str
    required_checks: tuple[str, ...] = ()
    requires_human_review: bool = True
    policy_persisted: bool = False
    policy_enforced: bool = False


class WorkspaceComplianceDTO(DirectorModel):
    compliant: bool
    observed_checks: tuple[str, ...] = ()
    compliance_persisted: bool = False
    remediation_performed: bool = False


class WorkspaceAuditReport(DirectorModel):
    observed_signal_count: int = Field(ge=0)
    findings: tuple[str, ...] = ()
    audit_persisted: bool = False
    workspace_changed: bool = False


class WorkspaceGovernanceSummary(DirectorModel):
    project_id: str
    compliant: bool
    requires_human_review: bool = True
    automatic_action_taken: bool = False


class WorkspaceGovernanceDashboard(DirectorModel):
    policy: WorkspacePolicyDTO
    compliance: WorkspaceComplianceDTO
    audit: WorkspaceAuditReport
    summary: WorkspaceGovernanceSummary
    analysis_only: bool = True


class MemoryPolicyDTO(DirectorModel):
    policy_id: str
    required_categories: tuple[str, ...] = ()
    policy_persisted: bool = False
    policy_enforced: bool = False


class MemoryComplianceDTO(DirectorModel):
    compliant: bool
    observed_categories: tuple[str, ...] = ()
    compliance_persisted: bool = False
    retention_changed: bool = False


class MemoryAuditReport(DirectorModel):
    observed_entry_count: int = Field(ge=0)
    findings: tuple[str, ...] = ()
    audit_persisted: bool = False
    evidence_changed: bool = False


class MemoryRetentionPolicy(DirectorModel):
    retention_scope: str = "human-governed"
    retention_persisted: bool = False
    retention_enforced: bool = False


class MemoryGovernanceSummary(DirectorModel):
    compliant: bool
    requires_human_review: bool = True
    automatic_action_taken: bool = False


class MemoryGovernanceDashboard(DirectorModel):
    policy: MemoryPolicyDTO
    compliance: MemoryComplianceDTO
    audit: MemoryAuditReport
    retention: MemoryRetentionPolicy
    summary: MemoryGovernanceSummary
    analysis_only: bool = True


class GraphPolicyDTO(DirectorModel):
    policy_id: str
    required_checks: tuple[str, ...] = ()
    policy_persisted: bool = False
    policy_enforced: bool = False


class GraphIntegrityReport(DirectorModel):
    consistent: bool
    unresolved_edge_count: int = Field(ge=0)
    repair_performed: bool = False
    graph_changed: bool = False


class GraphComplianceDTO(DirectorModel):
    compliant: bool
    observed_checks: tuple[str, ...] = ()
    compliance_persisted: bool = False
    remediation_performed: bool = False


class GraphAuditReport(DirectorModel):
    observed_node_count: int = Field(ge=0)
    observed_edge_count: int = Field(ge=0)
    findings: tuple[str, ...] = ()
    audit_persisted: bool = False


class GraphGovernanceDashboard(DirectorModel):
    policy: GraphPolicyDTO
    integrity: GraphIntegrityReport
    compliance: GraphComplianceDTO
    audit: GraphAuditReport
    requires_human_review: bool = True
    automatic_action_taken: bool = False
    analysis_only: bool = True


class QualityPolicyDTO(DirectorModel):
    policy_id: str
    required_checks: tuple[str, ...] = ()
    requires_completed_review_before_approval: bool = True
    policy_persisted: bool = False
    policy_enforced: bool = False


class EditorialComplianceReport(DirectorModel):
    compliant: bool
    review_completed: bool = False
    approval_granted: bool = False
    compliance_persisted: bool = False
    remediation_performed: bool = False


class QualityAuditReport(DirectorModel):
    observed_signal_count: int = Field(ge=0)
    findings: tuple[str, ...] = ()
    audit_persisted: bool = False
    quality_changed: bool = False


class CreativeGovernanceSummary(DirectorModel):
    compliant: bool
    requires_human_review: bool = True
    quality_enforced: bool = False
    automatic_action_taken: bool = False


class QualityGovernanceDashboard(DirectorModel):
    policy: QualityPolicyDTO
    editorial: EditorialComplianceReport
    audit: QualityAuditReport
    summary: CreativeGovernanceSummary
    analysis_only: bool = True


class V4GovernanceService:
    """Build read-only governance evidence from v4 Intelligence reports."""

    def __init__(self, repository: ProjectRepository) -> None:
        self._intelligence = V4IntelligenceService(repository)

    def workspace(self, project_id: str, context: WorkflowContext) -> WorkspaceGovernanceDashboard:
        report = self._intelligence.workspace(project_id, context)
        checks = ("read_only_evidence", "human_review_required", "no_workflow_change")
        compliant = (
            report.analysis_only
            and not report.timeline.workflow_changed
            and not report.recommendations.automatic_action_taken
        )
        return WorkspaceGovernanceDashboard(
            policy=WorkspacePolicyDTO(policy_id="workspace-read-only", required_checks=checks),
            compliance=WorkspaceComplianceDTO(compliant=compliant, observed_checks=checks),
            audit=WorkspaceAuditReport(
                observed_signal_count=report.health.observed_signal_count,
                findings=("Workspace governance is observational only.",),
            ),
            summary=WorkspaceGovernanceSummary(project_id=project_id, compliant=compliant),
        )

    def memory(self, project_id: str, context: WorkflowContext) -> MemoryGovernanceDashboard:
        report = self._intelligence.memory(project_id, context)
        categories = report.coverage.observed_categories
        compliant = (
            report.analysis_only
            and report.consistency.consistent
            and not report.recommendations.automatic_action_taken
        )
        return MemoryGovernanceDashboard(
            policy=MemoryPolicyDTO(
                policy_id="memory-human-governed", required_categories=categories
            ),
            compliance=MemoryComplianceDTO(compliant=compliant, observed_categories=categories),
            audit=MemoryAuditReport(
                observed_entry_count=report.insight.observed_entry_count,
                findings=("Memory governance does not retain or mutate evidence.",),
            ),
            retention=MemoryRetentionPolicy(),
            summary=MemoryGovernanceSummary(compliant=compliant),
        )

    def graph(self, project_id: str, context: WorkflowContext) -> GraphGovernanceDashboard:
        report = self._intelligence.graph(project_id, context)
        checks = ("read_only_projection", "integrity_checked", "no_graph_repair")
        compliant = report.analysis_only and report.consistency.consistent
        return GraphGovernanceDashboard(
            policy=GraphPolicyDTO(policy_id="graph-read-only", required_checks=checks),
            integrity=GraphIntegrityReport(
                consistent=report.consistency.consistent,
                unresolved_edge_count=report.consistency.unresolved_edge_count,
            ),
            compliance=GraphComplianceDTO(compliant=compliant, observed_checks=checks),
            audit=GraphAuditReport(
                observed_node_count=report.analytics.node_count,
                observed_edge_count=report.analytics.edge_count,
                findings=("Graph audit does not repair or persist graph evidence.",),
            ),
        )

    def quality(self, project_id: str, context: WorkflowContext) -> QualityGovernanceDashboard:
        dashboard = self._intelligence.quality(project_id, context)
        checks = ("human_review_required", "approval_not_automatic", "quality_not_enforced")
        compliant = (
            dashboard.analysis_only
            and not dashboard.editorial.approval_granted
            and not dashboard.quality_enforced
        )
        return QualityGovernanceDashboard(
            policy=QualityPolicyDTO(policy_id="quality-human-review", required_checks=checks),
            editorial=EditorialComplianceReport(
                compliant=compliant,
                review_completed=dashboard.editorial.review_completed,
                approval_granted=dashboard.editorial.approval_granted,
            ),
            audit=QualityAuditReport(
                observed_signal_count=dashboard.observed_signal_count,
                findings=("Quality governance cannot complete review or approve a page.",),
            ),
            summary=CreativeGovernanceSummary(compliant=compliant),
        )
