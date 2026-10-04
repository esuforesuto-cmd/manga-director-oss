"""v3.1 diagnostic DTOs for review, analytics, operations, and developer experience.

This Application-layer service reads existing DTO projections and the Repository
port. It never invokes an Agent or Provider, transitions a Page, writes a
Project, changes runtime configuration, or grants approval.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from pydantic import Field

from manga_director.domain.state_machine import PageState
from manga_director.production.director import DirectorModel
from manga_director.production.v3_1_foundation import V31FoundationService
from manga_director.repositories.protocols import ProjectRepository
from manga_director.workflow.contracts import WorkflowContext


class ReviewChecklist(DirectorModel):
    """Existing workflow guard evidence; no review step is executed."""

    items: tuple[str, ...] = (
        "one_page_scope",
        "persisted_storyboard_required",
        "completed_quality_review_required",
        "human_approval_required",
    )
    completed: bool = False
    review_executed: bool = False


class ReviewFinding(DirectorModel):
    category: Literal["workflow_guard", "storyboard", "quality", "approval"]
    severity: Literal["info", "warning"]
    message: str
    resolved: bool = False
    remediation_applied: bool = False


class ApprovalRecommendation(DirectorModel):
    recommendation: Literal["human_review_required", "not_ready"]
    rationale: tuple[str, ...] = ()
    approval_granted: bool = False
    state_transitioned: bool = False


class CreativeReview(DirectorModel):
    page_reference: str
    state: PageState
    storyboard_evidence_present: bool
    quality_evidence_present: bool
    diagnostic_only: bool = True


class ReviewSummary(DirectorModel):
    finding_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    human_decision_required: bool = True
    automatic_action_taken: bool = False


class CreativeReviewReport(DirectorModel):
    review: CreativeReview
    checklist: ReviewChecklist
    findings: tuple[ReviewFinding, ...] = ()
    approval_recommendation: ApprovalRecommendation
    summary: ReviewSummary
    review_persisted: bool = False


class KnowledgeCoverageMetrics(DirectorModel):
    project_count: int = Field(ge=0)
    project_with_metadata_count: int = Field(ge=0)
    metadata_key_count: int = Field(ge=0)
    values_redacted: bool = True


class KnowledgeUsageMetrics(DirectorModel):
    chapter_count: int = Field(ge=0)
    page_count: int = Field(ge=0)
    repository_reads: int = Field(ge=0)
    external_collection_started: bool = False


class KnowledgeRelationshipMetrics(DirectorModel):
    unique_metadata_key_count: int = Field(ge=0)
    relationship_count: int = Field(ge=0)
    values_exposed: bool = False


class KnowledgeTrendReport(DirectorModel):
    direction: Literal["baseline_only"] = "baseline_only"
    observation_count: int = Field(ge=0)
    persistence_mutated: bool = False


class KnowledgeAnalyticsSummary(DirectorModel):
    coverage: KnowledgeCoverageMetrics
    usage: KnowledgeUsageMetrics
    relationships: KnowledgeRelationshipMetrics
    trend: KnowledgeTrendReport
    automatic_recommendation_applied: bool = False


class KnowledgeAnalytics(DirectorModel):
    summary: KnowledgeAnalyticsSummary
    repository_port_only: bool = True


class OperationalInsight(DirectorModel):
    category: Literal["workflow", "project", "quality", "release"]
    message: str
    action_applied: bool = False


class WorkflowEfficiencyReport(DirectorModel):
    page_reference: str
    state: PageState
    observed_history_entries: int = Field(ge=0)
    observed_artifact_count: int = Field(ge=0)
    one_page_scope: bool = True
    workflow_executed: bool = False


class ProjectHealthDashboard(DirectorModel):
    status: Literal["healthy", "attention"]
    project_count: int = Field(ge=0)
    page_count: int = Field(ge=0)
    persistence_mutated: bool = False


class QualityTrendReport(DirectorModel):
    direction: Literal["baseline_only"] = "baseline_only"
    quality_evidence_present: bool
    approval_evidence_present: bool
    quality_passed: bool = False
    approval_granted: bool = False


class ReleaseReadinessMetrics(DirectorModel):
    package_version: str
    release_assets_checked: bool
    release_authorized: bool = False
    publication_started: bool = False


class OperationsIntelligenceSummary(DirectorModel):
    workflow_efficiency: WorkflowEfficiencyReport
    project_health: ProjectHealthDashboard
    quality_trend: QualityTrendReport
    release_readiness: ReleaseReadinessMetrics
    insights: tuple[OperationalInsight, ...] = ()
    automatic_operation_started: bool = False


class WorkspaceDiagnostics(DirectorModel):
    template_count: int = Field(ge=0)
    workspace_persisted: bool = False
    files_generated: int = Field(ge=0)
    diagnostic_only: bool = True


class TemplateRecommendation(DirectorModel):
    template_name: str
    rationale: str
    template_generated: bool = False


class DeveloperInsights(DirectorModel):
    messages: tuple[str, ...] = ()
    automatic_change_applied: bool = False


class ConfigurationHealthReport(DirectorModel):
    status: Literal["not_inspected", "valid_shape"]
    supplied_key_count: int = Field(ge=0)
    values_exposed: bool = False
    configuration_changed: bool = False


class DXSummary(DirectorModel):
    workspace: WorkspaceDiagnostics
    recommendation_count: int = Field(ge=0)
    configuration: ConfigurationHealthReport
    automatic_action_taken: bool = False


class DeveloperExperienceReport(DirectorModel):
    workspace: WorkspaceDiagnostics
    recommendations: tuple[TemplateRecommendation, ...] = ()
    insights: DeveloperInsights
    configuration: ConfigurationHealthReport
    summary: DXSummary
    filesystem_mutated: bool = False


class CreativeReviewDashboardDTO(DirectorModel):
    report: CreativeReviewReport
    automatic_action_taken: bool = False


class KnowledgeAnalyticsDashboardDTO(DirectorModel):
    report: KnowledgeAnalytics
    automatic_action_taken: bool = False


class OperationsIntelligenceDashboardDTO(DirectorModel):
    report: OperationsIntelligenceSummary
    automatic_action_taken: bool = False


class DeveloperExperienceDashboardDTO(DirectorModel):
    report: DeveloperExperienceReport
    automatic_action_taken: bool = False


class V31InsightsService:
    """Compose v3.1 analysis-only reports over existing Application DTOs."""

    def __init__(self, foundation: V31FoundationService, repository: ProjectRepository) -> None:
        self._foundation = foundation
        self._repository = repository

    def creative_review(self, context: WorkflowContext) -> CreativeReviewReport:
        storyboard_present = bool(context.artifacts.get("storyboard", context.page.get("storyboard")))
        quality_present = context.state in {PageState.QUALITY_CHECKED, PageState.APPROVED} or bool(
            context.artifacts.get("quality", context.page.get("quality"))
        )
        findings: list[ReviewFinding] = []
        if not storyboard_present:
            findings.append(
                ReviewFinding(
                    category="storyboard",
                    severity="warning",
                    message="Persisted storyboard evidence is required before image generation.",
                )
            )
        if not quality_present:
            findings.append(
                ReviewFinding(
                    category="quality",
                    severity="warning",
                    message="A completed quality review is required before approval.",
                )
            )
        if context.state is not PageState.QUALITY_CHECKED:
            findings.append(
                ReviewFinding(
                    category="approval",
                    severity="warning",
                    message="Approval remains a human decision after the existing quality stage.",
                )
            )
        recommendation = ApprovalRecommendation(
            recommendation="human_review_required" if quality_present else "not_ready",
            rationale=("This diagnostic cannot approve or transition a Page.",),
        )
        return CreativeReviewReport(
            review=CreativeReview(
                page_reference=_page_reference(context),
                state=context.state,
                storyboard_evidence_present=storyboard_present,
                quality_evidence_present=quality_present,
            ),
            checklist=ReviewChecklist(completed=storyboard_present and quality_present),
            findings=tuple(findings),
            approval_recommendation=recommendation,
            summary=ReviewSummary(
                finding_count=len(findings),
                warning_count=len(findings),
            ),
        )

    def knowledge_analytics(self) -> KnowledgeAnalytics:
        projects = tuple(self._repository.list())
        keys = {str(key) for project in projects for key in project.metadata}
        coverage = KnowledgeCoverageMetrics(
            project_count=len(projects),
            project_with_metadata_count=sum(1 for project in projects if project.metadata),
            metadata_key_count=sum(len(project.metadata) for project in projects),
        )
        usage = KnowledgeUsageMetrics(
            chapter_count=sum(len(project.chapters) for project in projects),
            page_count=sum(len(project.pages) for project in projects),
            repository_reads=1,
        )
        relationships = KnowledgeRelationshipMetrics(
            unique_metadata_key_count=len(keys),
            relationship_count=sum(len(project.metadata) for project in projects),
        )
        return KnowledgeAnalytics(
            summary=KnowledgeAnalyticsSummary(
                coverage=coverage,
                usage=usage,
                relationships=relationships,
                trend=KnowledgeTrendReport(observation_count=len(projects)),
            )
        )

    def operations_intelligence(self, context: WorkflowContext) -> OperationsIntelligenceSummary:
        operations = self._foundation.operations(context)
        efficiency = WorkflowEfficiencyReport(
            page_reference=_page_reference(context),
            state=context.state,
            observed_history_entries=operations.workflow.history_entries,
            observed_artifact_count=operations.workflow.artifact_count,
        )
        health = ProjectHealthDashboard(
            status=operations.health.status,
            project_count=operations.project.project_count,
            page_count=operations.project.page_count,
        )
        quality = QualityTrendReport(
            quality_evidence_present=operations.quality.quality_evidence_present,
            approval_evidence_present=operations.quality.approval_evidence_present,
        )
        release = ReleaseReadinessMetrics(
            package_version=operations.release.package_version,
            release_assets_checked=operations.release.release_assets_checked,
        )
        return OperationsIntelligenceSummary(
            workflow_efficiency=efficiency,
            project_health=health,
            quality_trend=quality,
            release_readiness=release,
            insights=(
                OperationalInsight(
                    category="workflow",
                    message="Workflow efficiency is an observation; no workflow command was run.",
                ),
                OperationalInsight(
                    category="release",
                    message="Release readiness evidence does not authorize publication.",
                ),
            ),
        )

    def developer_experience(
        self, configuration: Mapping[str, Any] | None = None
    ) -> DeveloperExperienceReport:
        templates = self._foundation.developer_productivity()
        configuration_health = ConfigurationHealthReport(
            status="valid_shape" if configuration is not None else "not_inspected",
            supplied_key_count=len(configuration) if configuration is not None else 0,
        )
        workspace = WorkspaceDiagnostics(
            template_count=templates.summary.template_count,
            files_generated=templates.summary.generated_files,
        )
        recommendations = (
            TemplateRecommendation(
                template_name=templates.planning.name,
                rationale="Use the existing one-Page planning descriptor before an explicit workflow action.",
            ),
            TemplateRecommendation(
                template_name=templates.validation.name,
                rationale="Use existing StateMachine guard evidence; this report performs no validation.",
            ),
        )
        insights = DeveloperInsights(
            messages=(
                "Template and workspace guidance is descriptive only.",
                "Configuration values are never returned by this report.",
            )
        )
        return DeveloperExperienceReport(
            workspace=workspace,
            recommendations=recommendations,
            insights=insights,
            configuration=configuration_health,
            summary=DXSummary(
                workspace=workspace,
                recommendation_count=len(recommendations),
                configuration=configuration_health,
            ),
        )

    def creative_review_dashboard(self, context: WorkflowContext) -> CreativeReviewDashboardDTO:
        return CreativeReviewDashboardDTO(report=self.creative_review(context))

    def knowledge_analytics_dashboard(self) -> KnowledgeAnalyticsDashboardDTO:
        return KnowledgeAnalyticsDashboardDTO(report=self.knowledge_analytics())

    def operations_intelligence_dashboard(
        self, context: WorkflowContext
    ) -> OperationsIntelligenceDashboardDTO:
        return OperationsIntelligenceDashboardDTO(report=self.operations_intelligence(context))

    def developer_experience_dashboard(
        self, configuration: Mapping[str, Any] | None = None
    ) -> DeveloperExperienceDashboardDTO:
        return DeveloperExperienceDashboardDTO(report=self.developer_experience(configuration))


def _page_reference(context: WorkflowContext) -> str:
    return str(context.page.get("id", context.page.get("page_number", "page")))
