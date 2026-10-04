"""v3.4 read-only foundations for knowledge, operations, organization, and release.

The services in this module expose immutable Application DTO projections from
the existing Repository and one-page workflow evidence. They do not save,
transition, dispatch, generate, approve, schedule, assess people, deploy, tag,
sign, publish, or otherwise operate a project. The StateMachine remains the
sole authority for legal workflow transitions.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from pydantic import Field

from manga_director._version import __version__
from manga_director.domain.state_machine import PageState
from manga_director.production.director import DirectorModel
from manga_director.repositories.protocols import ProjectRepository
from manga_director.workflow.contracts import WorkflowContext


class KnowledgeCatalogDTO(DirectorModel):
    catalog_id: str
    project_id: str
    entry_count: int = Field(ge=0)
    repository_read_only: bool = True


class KnowledgeRelationshipDTO(DirectorModel):
    source_id: str
    target_reference: str
    relation: Literal["belongs_to_page", "observed_in_project"]
    relationship_persisted: bool = False


class KnowledgeClassificationDTO(DirectorModel):
    category: Literal["workflow", "artifact", "project_metadata"]
    entry_count: int = Field(ge=0)
    classification_applied: bool = False


class KnowledgeQualityDTO(DirectorModel):
    observed_entry_count: int = Field(ge=0)
    provenance_available: bool = True
    quality_score_computed: bool = False


class KnowledgeIndexDTO(DirectorModel):
    index_id: str
    entry_count: int = Field(ge=0)
    index_persisted: bool = False
    remote_search_performed: bool = False


class KnowledgePlatformSummary(DirectorModel):
    catalog_count: int = Field(ge=0)
    relationship_count: int = Field(ge=0)
    automatic_action_taken: bool = False


class KnowledgePlatformReport(DirectorModel):
    catalog: KnowledgeCatalogDTO
    relationships: tuple[KnowledgeRelationshipDTO, ...] = ()
    classifications: tuple[KnowledgeClassificationDTO, ...] = ()
    quality: KnowledgeQualityDTO
    index: KnowledgeIndexDTO
    summary: KnowledgePlatformSummary
    analysis_only: bool = True


class OperationsDashboardDTO(DirectorModel):
    project_id: str
    current_state: PageState
    workflow_execution_enabled: bool = False


class OperationsStatusDTO(DirectorModel):
    status: Literal["observed", "quality_pending", "ready_for_human_approval"]
    observed_history_count: int = Field(ge=0)
    status_changed: bool = False


class ProductionCapacityDTO(DirectorModel):
    observed_page_count: int = Field(ge=0)
    observed_chapter_count: int = Field(ge=0)
    capacity_planned: bool = False
    allocation_applied: bool = False


class OperationsTimelineDTO(DirectorModel):
    labels: tuple[str, ...] = ()
    event_count: int = Field(ge=0)
    timeline_persisted: bool = False


class OperationsSummaryDTO(DirectorModel):
    project_id: str
    observation_count: int = Field(ge=0)
    monitoring_started: bool = False
    automatic_action_taken: bool = False


class ProductionOperationsReport(DirectorModel):
    dashboard: OperationsDashboardDTO
    status: OperationsStatusDTO
    capacity: ProductionCapacityDTO
    timeline: OperationsTimelineDTO
    summary: OperationsSummaryDTO
    analysis_only: bool = True


class TeamHealthDTO(DirectorModel):
    observed_member_count: int = Field(ge=0)
    health_score_computed: bool = False
    personnel_action_taken: bool = False


class RoleAnalysisDTO(DirectorModel):
    role_label: Literal["project_owner", "workflow_reviewer"]
    observed: bool
    assignment_changed: bool = False


class WorkloadSummaryDTO(DirectorModel):
    observed_page_count: int = Field(ge=0)
    observed_history_count: int = Field(ge=0)
    workload_assigned: bool = False


class CollaborationMetricsDTO(DirectorModel):
    observed_handoff_count: int = Field(ge=0)
    metrics_persisted: bool = False
    notification_sent: bool = False


class OrganizationRiskDTO(DirectorModel):
    risk_count: int = Field(ge=0)
    risks: tuple[str, ...] = ()
    risk_mitigated: bool = False


class OrganizationExecutiveSummary(DirectorModel):
    observation_count: int = Field(ge=0)
    delivery_confidence_computed: bool = False
    automatic_action_taken: bool = False


class OrganizationIntelligenceReport(DirectorModel):
    team_health: TeamHealthDTO
    roles: tuple[RoleAnalysisDTO, ...] = ()
    workload: WorkloadSummaryDTO
    collaboration: CollaborationMetricsDTO
    risks: OrganizationRiskDTO
    executive: OrganizationExecutiveSummary
    analysis_only: bool = True


class ReleaseHealthDTO(DirectorModel):
    release_version: str
    current_state: PageState
    health_computed: bool = False
    release_authorized: bool = False


class DeploymentSummaryDTO(DirectorModel):
    deployment_evidence_count: int = Field(ge=0)
    deployment_started: bool = False
    deployment_completed: bool = False


class CompatibilitySummaryDTO(DirectorModel):
    preserved_baselines: tuple[str, ...] = ("v1.x", "v2.x", "v3.0-v3.3")
    compatibility_validated: bool = False
    public_api_changed: bool = False


class RegressionSummaryDTO(DirectorModel):
    observed_history_count: int = Field(ge=0)
    regression_detected: bool = False
    remediation_applied: bool = False


class ReleaseExecutiveSummary(DirectorModel):
    release_version: str
    evidence_count: int = Field(ge=0)
    tag_created: bool = False
    publication_started: bool = False


class ReleaseIntelligenceReport(DirectorModel):
    health: ReleaseHealthDTO
    deployment: DeploymentSummaryDTO
    compatibility: CompatibilitySummaryDTO
    regression: RegressionSummaryDTO
    executive: ReleaseExecutiveSummary
    analysis_only: bool = True


class KnowledgePlatformDashboardDTO(DirectorModel):
    report: KnowledgePlatformReport
    automatic_action_taken: bool = False


class ProductionOperationsDashboardDTO(DirectorModel):
    report: ProductionOperationsReport
    automatic_action_taken: bool = False


class OrganizationIntelligenceDashboardDTO(DirectorModel):
    report: OrganizationIntelligenceReport
    automatic_action_taken: bool = False


class ReleaseIntelligenceDashboardDTO(DirectorModel):
    report: ReleaseIntelligenceReport
    automatic_action_taken: bool = False


class V34FoundationService:
    """Build v3.4 DTO projections without workflow or operational authority."""

    def __init__(self, repository: ProjectRepository) -> None:
        self._repository = repository

    def knowledge_platform(
        self, project_id: str, context: WorkflowContext
    ) -> KnowledgePlatformReport:
        project = self._repository.load(project_id)
        page_reference = _page_reference(context)
        history = _history_labels(context)
        metadata_count = len(project.metadata)
        artifact_count = len(context.artifacts)
        workflow_count = len(history)
        entry_count = metadata_count + artifact_count + workflow_count
        catalog = KnowledgeCatalogDTO(
            catalog_id=f"knowledge:{project.id}:{page_reference}",
            project_id=project.id,
            entry_count=entry_count,
        )
        relationships = tuple(
            KnowledgeRelationshipDTO(
                source_id=f"knowledge:{project.id}:{page_reference}:{category}",
                target_reference=page_reference,
                relation="belongs_to_page",
            )
            for category, count in (
                ("workflow", workflow_count),
                ("artifact", artifact_count),
                ("project_metadata", metadata_count),
            )
            if count
        )
        classifications = (
            KnowledgeClassificationDTO(category="workflow", entry_count=workflow_count),
            KnowledgeClassificationDTO(category="artifact", entry_count=artifact_count),
            KnowledgeClassificationDTO(
                category="project_metadata", entry_count=metadata_count
            ),
        )
        return KnowledgePlatformReport(
            catalog=catalog,
            relationships=relationships,
            classifications=classifications,
            quality=KnowledgeQualityDTO(observed_entry_count=entry_count),
            index=KnowledgeIndexDTO(
                index_id=f"knowledge-index:{project.id}:{page_reference}", entry_count=entry_count
            ),
            summary=KnowledgePlatformSummary(
                catalog_count=1, relationship_count=len(relationships)
            ),
        )

    def production_operations(
        self, project_id: str, context: WorkflowContext
    ) -> ProductionOperationsReport:
        project = self._repository.load(project_id)
        history = _history_labels(context)
        status: Literal["observed", "quality_pending", "ready_for_human_approval"] = (
            "ready_for_human_approval"
            if context.state is PageState.QUALITY_CHECKED
            else "quality_pending"
            if context.state is PageState.GENERATED
            else "observed"
        )
        return ProductionOperationsReport(
            dashboard=OperationsDashboardDTO(project_id=project.id, current_state=context.state),
            status=OperationsStatusDTO(status=status, observed_history_count=len(history)),
            capacity=ProductionCapacityDTO(
                observed_page_count=len(project.pages), observed_chapter_count=len(project.chapters)
            ),
            timeline=OperationsTimelineDTO(labels=history, event_count=len(history)),
            summary=OperationsSummaryDTO(
                project_id=project.id, observation_count=len(history) + 1
            ),
        )

    def organization_intelligence(
        self, project_id: str, context: WorkflowContext
    ) -> OrganizationIntelligenceReport:
        project = self._repository.load(project_id)
        history = _history_labels(context)
        risks = () if history else ("No observed workflow handoff for this Page.",)
        roles = (
            RoleAnalysisDTO(role_label="project_owner", observed=bool(project.id)),
            RoleAnalysisDTO(
                role_label="workflow_reviewer",
                observed=context.state in {PageState.QUALITY_CHECKED, PageState.APPROVED},
            ),
        )
        return OrganizationIntelligenceReport(
            team_health=TeamHealthDTO(observed_member_count=1),
            roles=roles,
            workload=WorkloadSummaryDTO(
                observed_page_count=len(project.pages), observed_history_count=len(history)
            ),
            collaboration=CollaborationMetricsDTO(observed_handoff_count=len(history)),
            risks=OrganizationRiskDTO(risk_count=len(risks), risks=risks),
            executive=OrganizationExecutiveSummary(observation_count=len(roles) + len(history)),
        )

    def release_intelligence(
        self, project_id: str, context: WorkflowContext
    ) -> ReleaseIntelligenceReport:
        self._repository.load(project_id)
        history = _history_labels(context)
        evidence_count = len(history) + len(context.artifacts)
        return ReleaseIntelligenceReport(
            health=ReleaseHealthDTO(release_version=__version__, current_state=context.state),
            deployment=DeploymentSummaryDTO(deployment_evidence_count=evidence_count),
            compatibility=CompatibilitySummaryDTO(),
            regression=RegressionSummaryDTO(observed_history_count=len(history)),
            executive=ReleaseExecutiveSummary(
                release_version=__version__, evidence_count=evidence_count
            ),
        )

    def knowledge_platform_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> KnowledgePlatformDashboardDTO:
        return KnowledgePlatformDashboardDTO(report=self.knowledge_platform(project_id, context))

    def production_operations_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> ProductionOperationsDashboardDTO:
        return ProductionOperationsDashboardDTO(
            report=self.production_operations(project_id, context)
        )

    def organization_intelligence_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> OrganizationIntelligenceDashboardDTO:
        return OrganizationIntelligenceDashboardDTO(
            report=self.organization_intelligence(project_id, context)
        )

    def release_intelligence_dashboard(
        self, project_id: str, context: WorkflowContext
    ) -> ReleaseIntelligenceDashboardDTO:
        return ReleaseIntelligenceDashboardDTO(report=self.release_intelligence(project_id, context))


def _page_reference(context: WorkflowContext) -> str:
    return str(context.page.get("id", context.page.get("page_number", "page")))


def _history_labels(context: WorkflowContext) -> tuple[str, ...]:
    history = context.metadata.get("workflow_history", ())
    if not isinstance(history, list | tuple):
        return ()
    return tuple(
        str(entry.get("step", entry.get("to", "workflow")))
        for entry in history
        if isinstance(entry, Mapping)
    )
