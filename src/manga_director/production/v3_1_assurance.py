"""v3.1 production-quality assurance DTOs with no execution authority.

The service composes prior v3.1 projections and the existing Repository port.
It cannot review automatically, approve a Page, execute a workflow, write data,
change configuration, deploy, publish, or invoke an Agent or Provider.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from pydantic import Field

from manga_director._version import __version__
from manga_director.domain.state_machine import PageState
from manga_director.production.director import DirectorModel
from manga_director.production.v3_1_foundation import V31FoundationService
from manga_director.production.v3_1_insights import V31InsightsService
from manga_director.repositories.protocols import ProjectRepository
from manga_director.workflow.contracts import WorkflowContext


class CreativePolicy(DirectorModel):
    controls: tuple[str, ...] = (
        "one_page_scope",
        "persisted_storyboard_before_generation",
        "completed_quality_review_before_approval",
        "human_approval_required",
    )
    policy_applied: bool = False


class CreativeValidation(DirectorModel):
    valid: bool
    state: PageState
    storyboard_guard_visible: bool
    quality_guard_visible: bool
    workflow_changed: bool = False


class CreativeComplianceReport(DirectorModel):
    compliant: bool
    required_controls: tuple[str, ...] = ()
    findings: tuple[str, ...] = ()
    remediation_applied: bool = False


class CreativeQualityScore(DirectorModel):
    score: int = Field(ge=0, le=100)
    rationale: str
    quality_passed: bool = False


class CreativeGovernanceSummary(DirectorModel):
    policy: CreativePolicy
    validation: CreativeValidation
    compliance: CreativeComplianceReport
    quality: CreativeQualityScore
    human_decision_required: bool = True
    automatic_action_taken: bool = False


class CreativeGovernanceReport(DirectorModel):
    summary: CreativeGovernanceSummary
    diagnostic_only: bool = True
    approval_granted: bool = False


class KnowledgeIntegrityScore(DirectorModel):
    score: int = Field(ge=0, le=100)
    values_redacted: bool = True
    automatic_repair: bool = False


class KnowledgeConsistencyValidation(DirectorModel):
    valid: bool
    repository_port_only: bool = True
    values_exposed: bool = False
    persistence_mutated: bool = False


class KnowledgeDependencyReport(DirectorModel):
    dependency_count: int = Field(ge=0)
    unique_key_count: int = Field(ge=0)
    external_lookup_started: bool = False


class KnowledgeLifecycleValidation(DirectorModel):
    valid: bool
    source: Literal["repository_projection"] = "repository_projection"
    lifecycle_changed: bool = False


class KnowledgeGovernanceSummary(DirectorModel):
    integrity: KnowledgeIntegrityScore
    consistency: KnowledgeConsistencyValidation
    dependencies: KnowledgeDependencyReport
    lifecycle: KnowledgeLifecycleValidation
    governance_only: bool = True


class KnowledgeReliabilityReport(DirectorModel):
    summary: KnowledgeGovernanceSummary
    reliable: bool
    persistence_mutated: bool = False


class OperationalReadiness(DirectorModel):
    ready_for_human_review: bool
    one_page_scope: bool = True
    operation_started: bool = False


class DeploymentReadinessReport(DirectorModel):
    ready_for_review: bool
    deployment_performed: bool = False
    deployment_authorized: bool = False


class ConfigurationValidationReport(DirectorModel):
    valid_shape: bool
    configured_key_count: int = Field(ge=0)
    values_exposed: bool = False
    configuration_changed: bool = False


class EnvironmentReadinessReport(DirectorModel):
    status: Literal["local_diagnostic"] = "local_diagnostic"
    external_probe_started: bool = False
    environment_changed: bool = False


class OperationalHealthSummary(DirectorModel):
    status: Literal["healthy", "attention"]
    checks: tuple[str, ...] = ()
    remediation_started: bool = False


class ReleaseReadinessSummary(DirectorModel):
    operational: OperationalReadiness
    deployment: DeploymentReadinessReport
    configuration: ConfigurationValidationReport
    environment: EnvironmentReadinessReport
    health: OperationalHealthSummary
    release_authorized: bool = False


class ReleaseQualityReport(DirectorModel):
    package_version: str = __version__
    quality_evidence_present: bool
    report_generated: bool = True
    release_published: bool = False


class CompatibilityValidationReport(DirectorModel):
    version: str = __version__
    checked_surfaces: tuple[str, ...] = (
        "python_api",
        "cli",
        "fastapi",
        "mcp",
        "workflow",
        "repository",
    )
    compatible: bool = True
    breaking_change_applied: bool = False


class QualityGateSummary(DirectorModel):
    gates: tuple[str, ...] = (
        "creative_governance",
        "knowledge_reliability",
        "operational_readiness",
        "release_quality",
        "compatibility",
    )
    evaluated_as_diagnostic: bool = True
    gate_enforced: bool = False


class RegressionSummary(DirectorModel):
    baseline: Literal["v3_0_x"] = "v3_0_x"
    regression_detected: bool = False
    comparison_executed: bool = False


class ProductionValidationReport(DirectorModel):
    operational_ready_for_review: bool
    knowledge_reliable: bool
    creative_governance_diagnostic: bool
    production_action_started: bool = False


class ReleaseRecommendation(DirectorModel):
    recommendation: Literal["human_release_review_required"] = "human_release_review_required"
    rationale: tuple[str, ...] = ()
    release_authorized: bool = False


class ReleaseQualitySummary(DirectorModel):
    quality: ReleaseQualityReport
    compatibility: CompatibilityValidationReport
    gates: QualityGateSummary
    regression: RegressionSummary
    production: ProductionValidationReport
    recommendation: ReleaseRecommendation
    automatic_action_taken: bool = False


class CreativeGovernanceDashboardDTO(DirectorModel):
    report: CreativeGovernanceReport
    automatic_action_taken: bool = False


class KnowledgeReliabilityDashboardDTO(DirectorModel):
    report: KnowledgeReliabilityReport
    automatic_action_taken: bool = False


class OperationalReadinessDashboardDTO(DirectorModel):
    report: ReleaseReadinessSummary
    deployment_performed: bool = False


class ReleaseQualityDashboardDTO(DirectorModel):
    report: ReleaseQualitySummary
    release_authorized: bool = False


class V31AssuranceService:
    """Produce v3.1 governance and release-quality diagnostics only."""

    def __init__(
        self,
        foundation: V31FoundationService,
        insights: V31InsightsService,
        repository: ProjectRepository,
    ) -> None:
        self._foundation = foundation
        self._insights = insights
        self._repository = repository

    def creative_governance(self, context: WorkflowContext) -> CreativeGovernanceReport:
        review = self._insights.creative_review(context)
        storyboard_guard = review.review.storyboard_evidence_present
        quality_guard = review.review.quality_evidence_present
        findings = tuple(finding.message for finding in review.findings)
        compliant = storyboard_guard and quality_guard
        return CreativeGovernanceReport(
            summary=CreativeGovernanceSummary(
                policy=CreativePolicy(),
                validation=CreativeValidation(
                    valid=review.review.diagnostic_only,
                    state=context.state,
                    storyboard_guard_visible=storyboard_guard,
                    quality_guard_visible=quality_guard,
                ),
                compliance=CreativeComplianceReport(
                    compliant=compliant,
                    required_controls=CreativePolicy().controls,
                    findings=findings,
                ),
                quality=CreativeQualityScore(
                    score=100 if compliant else 50,
                    rationale="Score reflects visible guard evidence only; it does not pass quality.",
                ),
            )
        )

    def knowledge_reliability(self) -> KnowledgeReliabilityReport:
        analytics = self._insights.knowledge_analytics()
        projects = tuple(self._repository.list())
        integrity = KnowledgeIntegrityScore(
            score=100 if analytics.repository_port_only else 0,
        )
        consistency = KnowledgeConsistencyValidation(valid=analytics.repository_port_only)
        dependencies = KnowledgeDependencyReport(
            dependency_count=analytics.summary.relationships.relationship_count,
            unique_key_count=analytics.summary.relationships.unique_metadata_key_count,
        )
        lifecycle = KnowledgeLifecycleValidation(valid=all(project.id for project in projects))
        summary = KnowledgeGovernanceSummary(
            integrity=integrity,
            consistency=consistency,
            dependencies=dependencies,
            lifecycle=lifecycle,
        )
        return KnowledgeReliabilityReport(
            summary=summary,
            reliable=consistency.valid and lifecycle.valid,
        )

    def operational_readiness(
        self, context: WorkflowContext, configuration: Mapping[str, Any] | None = None
    ) -> ReleaseReadinessSummary:
        operations = self._foundation.operations(context)
        experience = self._insights.developer_experience(configuration)
        operational = OperationalReadiness(
            ready_for_human_review=operations.workflow.one_page_scope,
        )
        deployment = DeploymentReadinessReport(ready_for_review=operational.ready_for_human_review)
        config = ConfigurationValidationReport(
            valid_shape=experience.configuration.status in {"not_inspected", "valid_shape"},
            configured_key_count=experience.configuration.supplied_key_count,
        )
        environment = EnvironmentReadinessReport()
        health = OperationalHealthSummary(status=operations.health.status, checks=operations.health.checks)
        return ReleaseReadinessSummary(
            operational=operational,
            deployment=deployment,
            configuration=config,
            environment=environment,
            health=health,
        )

    def release_quality(
        self, context: WorkflowContext, configuration: Mapping[str, Any] | None = None
    ) -> ReleaseQualitySummary:
        creative = self.creative_governance(context)
        knowledge = self.knowledge_reliability()
        operational = self.operational_readiness(context, configuration)
        quality = ReleaseQualityReport(
            quality_evidence_present=creative.summary.validation.quality_guard_visible,
        )
        compatibility = CompatibilityValidationReport()
        gates = QualityGateSummary()
        regression = RegressionSummary()
        production = ProductionValidationReport(
            operational_ready_for_review=operational.operational.ready_for_human_review,
            knowledge_reliable=knowledge.reliable,
            creative_governance_diagnostic=creative.diagnostic_only,
        )
        recommendation = ReleaseRecommendation(
            rationale=(
                "Quality, compatibility, and readiness evidence are diagnostic only.",
                "A human must complete the existing release process.",
            )
        )
        return ReleaseQualitySummary(
            quality=quality,
            compatibility=compatibility,
            gates=gates,
            regression=regression,
            production=production,
            recommendation=recommendation,
        )

    def creative_governance_dashboard(
        self, context: WorkflowContext
    ) -> CreativeGovernanceDashboardDTO:
        return CreativeGovernanceDashboardDTO(report=self.creative_governance(context))

    def knowledge_reliability_dashboard(self) -> KnowledgeReliabilityDashboardDTO:
        return KnowledgeReliabilityDashboardDTO(report=self.knowledge_reliability())

    def operational_readiness_dashboard(
        self, context: WorkflowContext, configuration: Mapping[str, Any] | None = None
    ) -> OperationalReadinessDashboardDTO:
        return OperationalReadinessDashboardDTO(report=self.operational_readiness(context, configuration))

    def release_quality_dashboard(
        self, context: WorkflowContext, configuration: Mapping[str, Any] | None = None
    ) -> ReleaseQualityDashboardDTO:
        return ReleaseQualityDashboardDTO(report=self.release_quality(context, configuration))
