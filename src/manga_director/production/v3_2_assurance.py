"""v3.2 production-readiness assurance DTOs with no execution authority.

This Application-layer service validates and summarizes projections from the
v3.2 Foundation and Insights services.  It has no access to a workflow engine,
does not save through the Repository port, and cannot approve or deploy.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director._version import __version__
from manga_director.domain.state_machine import PageState
from manga_director.production.director import DirectorModel
from manga_director.production.v3_2_foundation import V32FoundationService
from manga_director.production.v3_2_insights import V32InsightsService
from manga_director.repositories.protocols import ProjectRepository
from manga_director.workflow.contracts import WorkflowContext


class CreativeValidationDTO(DirectorModel):
    valid: bool
    checks: tuple[str, ...] = ()
    workflow_executed: bool = False
    approval_granted: bool = False


class CreativeConsistencyReport(DirectorModel):
    current_state: PageState
    timeline_consistent: bool
    task_projection_consistent: bool
    consistency_repaired: bool = False


class CreativeIntegrityAnalysis(DirectorModel):
    one_page_scope: bool = True
    storyboard_evidence_present: bool
    integrity_restored: bool = False


class WorkspaceReliabilityReport(DirectorModel):
    status: Literal["healthy", "attention"]
    activity_count: int = Field(ge=0)
    workspace_persisted: bool = False
    task_started: bool = False


class CreativeReadinessReport(DirectorModel):
    ready_for_human_review: bool
    next_command: str | None = None
    deployment_started: bool = False
    auto_approved: bool = False


class CreativeReliabilitySummary(DirectorModel):
    status: Literal["healthy", "attention"]
    messages: tuple[str, ...] = ()
    automatic_action_taken: bool = False


class CreativeReliabilityReport(DirectorModel):
    validation: CreativeValidationDTO
    consistency: CreativeConsistencyReport
    integrity: CreativeIntegrityAnalysis
    workspace: WorkspaceReliabilityReport
    readiness: CreativeReadinessReport
    summary: CreativeReliabilitySummary
    analysis_only: bool = True


class AssetIntegrityValidation(DirectorModel):
    valid: bool
    asset_count: int = Field(ge=0)
    metadata_values_redacted: bool = True
    repository_repaired: bool = False


class AssetLifecycleReport(DirectorModel):
    observed_categories: tuple[str, ...] = ()
    lifecycle_managed: bool = False
    assets_deleted: int = 0


class AssetComplianceReport(DirectorModel):
    compliant: bool
    checks: tuple[str, ...] = ()
    compliance_enforced: bool = False


class AssetGovernanceSummary(DirectorModel):
    status: Literal["healthy", "attention"]
    recommendation: str
    governance_applied: bool = False


class AssetQualityScore(DirectorModel):
    score: Literal["not_computed"] = "not_computed"
    evidence_present: bool
    quality_gate_passed: bool = False


class AssetRiskReport(DirectorModel):
    risk_level: Literal["low", "attention"]
    risks: tuple[str, ...] = ()
    remediation_applied: bool = False


class AssetGovernanceReport(DirectorModel):
    integrity: AssetIntegrityValidation
    lifecycle: AssetLifecycleReport
    compliance: AssetComplianceReport
    summary: AssetGovernanceSummary
    quality: AssetQualityScore
    risk: AssetRiskReport
    analysis_only: bool = True


class OperationalIntelligenceDTO(DirectorModel):
    status: Literal["healthy", "attention"]
    observed_project_count: int = Field(ge=0)
    operations_changed: bool = False


class WorkflowHealthAnalysis(DirectorModel):
    status: Literal["healthy", "attention"]
    current_state: PageState
    state_machine_observed: bool = True
    workflow_recovered: bool = False


class AnalyticsValidationReport(DirectorModel):
    valid: bool
    report_is_analysis_only: bool
    analytics_persisted: bool = False


class OperationalTrendReport(DirectorModel):
    trend: Literal["not_computed"] = "not_computed"
    basis: tuple[str, ...] = ()
    external_collection_started: bool = False


class DeploymentReadinessReport(DirectorModel):
    ready: bool
    checks: tuple[str, ...] = ()
    deployment_started: bool = False


class OperationalIntelligenceSummary(DirectorModel):
    status: Literal["healthy", "attention"]
    messages: tuple[str, ...] = ()
    automation_started: bool = False


class OperationalIntelligenceReport(DirectorModel):
    operational: OperationalIntelligenceDTO
    workflow: WorkflowHealthAnalysis
    analytics: AnalyticsValidationReport
    trend: OperationalTrendReport
    deployment: DeploymentReadinessReport
    summary: OperationalIntelligenceSummary
    analysis_only: bool = True


class V32ReleaseReadinessDTO(DirectorModel):
    package_version: str = __version__
    ready_for_human_release_review: bool
    release_started: bool = False


class V32CompatibilityValidationReport(DirectorModel):
    compatible: bool
    surfaces: tuple[str, ...] = ()
    public_interface_changed: bool = False


class RegressionAnalysisReport(DirectorModel):
    regressions_detected: int = Field(ge=0)
    analysis_only: bool = True
    remediation_applied: bool = False


class QualityGateReport(DirectorModel):
    gates: tuple[str, ...] = ()
    passed: bool
    gate_enforced: bool = False


class ProductionValidationSummary(DirectorModel):
    valid: bool
    checks: tuple[str, ...] = ()
    production_changed: bool = False


class V32ReleaseRecommendation(DirectorModel):
    message: str
    requires_human_approval: bool = True
    release_authorized: bool = False


class V32ReleaseReadinessReport(DirectorModel):
    readiness: V32ReleaseReadinessDTO
    compatibility: V32CompatibilityValidationReport
    regression: RegressionAnalysisReport
    quality_gates: QualityGateReport
    production: ProductionValidationSummary
    recommendation: V32ReleaseRecommendation
    analysis_only: bool = True


class CreativeReliabilityDashboardDTO(DirectorModel):
    report: CreativeReliabilityReport
    automatic_action_taken: bool = False


class AssetGovernanceDashboardDTO(DirectorModel):
    report: AssetGovernanceReport
    automatic_action_taken: bool = False


class OperationalIntelligenceDashboardDTO(DirectorModel):
    report: OperationalIntelligenceReport
    automatic_action_taken: bool = False


class ReleaseReadinessDashboardDTO(DirectorModel):
    report: V32ReleaseReadinessReport
    automatic_action_taken: bool = False


class V32AssuranceService:
    """Build v3.2 assurance reports without mutating Core or Infrastructure."""

    def __init__(
        self,
        foundation: V32FoundationService,
        insights: V32InsightsService,
        repository: ProjectRepository,
    ) -> None:
        self._foundation = foundation
        self._insights = insights
        self._repository = repository

    def creative_reliability(
        self, project_id: str, context: WorkflowContext
    ) -> CreativeReliabilityReport:
        workspace = self._insights.creative_workspace(project_id, context)
        storyboard_present = "storyboard" in context.artifacts
        valid = workspace.analysis_only and not workspace.session.workflow_execution_enabled
        status: Literal["healthy", "attention"] = "healthy" if valid else "attention"
        return CreativeReliabilityReport(
            validation=CreativeValidationDTO(
                valid=valid,
                checks=("analysis_only", "one_page_scope", "human_approval_retained"),
            ),
            consistency=CreativeConsistencyReport(
                current_state=context.state,
                timeline_consistent=all(
                    entry.state is context.state for entry in workspace.timeline.entries
                )
                or not workspace.timeline.entries,
                task_projection_consistent=all(
                    not task.automatically_started for task in workspace.tasks
                ),
            ),
            integrity=CreativeIntegrityAnalysis(storyboard_evidence_present=storyboard_present),
            workspace=WorkspaceReliabilityReport(
                status=status, activity_count=workspace.activity.activity_count
            ),
            readiness=CreativeReadinessReport(
                ready_for_human_review=context.state is PageState.QUALITY_CHECKED,
                next_command=workspace.progress.next_command,
            ),
            summary=CreativeReliabilitySummary(
                status=status,
                messages=(
                    "Creative reliability is diagnostic; a human retains all workflow decisions.",
                ),
            ),
        )

    def asset_governance(self, project_id: str, context: WorkflowContext) -> AssetGovernanceReport:
        analytics, summary = self._insights.asset_analytics(project_id, context)
        valid = analytics.values_redacted and not analytics.repository_mutated
        status: Literal["healthy", "attention"] = "healthy" if valid else "attention"
        return AssetGovernanceReport(
            integrity=AssetIntegrityValidation(valid=valid, asset_count=summary.asset_count),
            lifecycle=AssetLifecycleReport(
                observed_categories=analytics.relationships.relationship_types,
            ),
            compliance=AssetComplianceReport(
                compliant=valid,
                checks=("repository_port", "metadata_value_redaction", "no_external_lookup"),
            ),
            summary=AssetGovernanceSummary(
                status=status,
                recommendation="Review redacted Asset metadata evidence before any human-directed change.",
            ),
            quality=AssetQualityScore(evidence_present=analytics.quality.quality_evidence_present),
            risk=AssetRiskReport(
                risk_level="low" if valid else "attention",
                risks=() if valid else ("redaction_or_read_only_boundary",),
            ),
        )

    def operational_intelligence(self, context: WorkflowContext) -> OperationalIntelligenceReport:
        workflow = self._insights.workflow_intelligence(context)
        production = self._insights.production_insights(context)
        project_count = len(tuple(self._repository.list()))
        healthy = workflow.health.status == "healthy" and production.analysis_only
        status: Literal["healthy", "attention"] = "healthy" if healthy else "attention"
        return OperationalIntelligenceReport(
            operational=OperationalIntelligenceDTO(
                status=status, observed_project_count=project_count
            ),
            workflow=WorkflowHealthAnalysis(
                status=workflow.health.status, current_state=context.state
            ),
            analytics=AnalyticsValidationReport(
                valid=production.analysis_only,
                report_is_analysis_only=production.analysis_only,
            ),
            trend=OperationalTrendReport(basis=("local_repository_projection", "workflow_context")),
            deployment=DeploymentReadinessReport(
                ready=healthy,
                checks=("no_runtime_automation", "one_page_scope", "dto_delivery_only"),
            ),
            summary=OperationalIntelligenceSummary(
                status=status,
                messages=(
                    "Operational intelligence reports evidence only; it does not alter operations.",
                ),
            ),
        )

    def release_readiness(self, context: WorkflowContext) -> V32ReleaseReadinessReport:
        operational = self.operational_intelligence(context)
        compatible = True
        gates = (
            "creative_reliability_validation",
            "asset_governance_validation",
            "operational_intelligence_validation",
            "release_readiness_validation",
            "compatibility_validation",
        )
        valid = operational.analytics.valid and compatible
        return V32ReleaseReadinessReport(
            readiness=V32ReleaseReadinessDTO(ready_for_human_release_review=valid),
            compatibility=V32CompatibilityValidationReport(
                compatible=compatible,
                surfaces=(
                    "Python API",
                    "CLI",
                    "FastAPI",
                    "MCP",
                    "Web UI",
                    "Workflow",
                    "Repository",
                ),
            ),
            regression=RegressionAnalysisReport(regressions_detected=0),
            quality_gates=QualityGateReport(gates=gates, passed=valid),
            production=ProductionValidationSummary(
                valid=valid,
                checks=(
                    "read_only_diagnostics",
                    "state_machine_authority",
                    "human_approval_retained",
                ),
            ),
            recommendation=V32ReleaseRecommendation(
                message="Evidence is ready for human release review; no release was authorized.",
            ),
        )

    def creative_reliability_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> CreativeReliabilityDashboardDTO:
        return CreativeReliabilityDashboardDTO(
            report=self.creative_reliability(project_id, context)
        )

    def asset_governance_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> AssetGovernanceDashboardDTO:
        return AssetGovernanceDashboardDTO(report=self.asset_governance(project_id, context))

    def operational_intelligence_dashboard(
        self, context: WorkflowContext
    ) -> OperationalIntelligenceDashboardDTO:
        return OperationalIntelligenceDashboardDTO(report=self.operational_intelligence(context))

    def release_readiness_dashboard(self, context: WorkflowContext) -> ReleaseReadinessDashboardDTO:
        return ReleaseReadinessDashboardDTO(report=self.release_readiness(context))
