"""v3.1 read-only DTO foundations for collaboration, knowledge, and operations.

The service in this module is an Application-layer projection over existing
Director planning and the Repository port.  It never invokes an Agent or
Provider, changes a workflow context, writes a Project, or authorizes approval.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import Field

from manga_director._version import __version__
from manga_director.domain.state_machine import PageState
from manga_director.production.director import DirectorModel
from manga_director.production.v3_collaboration import CollaborationPlanningService
from manga_director.production.v3_foundation import DirectorPlanningService
from manga_director.repositories.protocols import ProjectRepository
from manga_director.workflow.contracts import WorkflowContext


class WorkspaceMember(DirectorModel):
    """A human collaboration role, never a live Agent identity."""

    member_id: str
    role: Literal["editor", "scenario", "character", "storyboard", "review", "approver"]
    human_owned: bool = True
    agent_invoked: bool = False


class Workspace(DirectorModel):
    """A one-page collaboration view with no persistence authority."""

    workspace_id: str
    kind: Literal["editor", "scenario", "character", "storyboard", "review", "approval"]
    page_reference: str
    current_state: PageState
    members: tuple[WorkspaceMember, ...] = ()
    persisted: bool = False


class CollaborationSession(DirectorModel):
    session_id: str
    workspace: Workspace
    objective: str
    decision_context: tuple[str, ...] = ()
    active: bool = False
    execution_enabled: bool = False


class ReviewAssignment(DirectorModel):
    reviewer: WorkspaceMember
    criteria: tuple[str, ...] = ("story clarity", "continuity", "workflow evidence")
    assigned_for_review: bool = True
    review_executed: bool = False


class ApprovalState(DirectorModel):
    status: Literal["not_ready", "pending_human_review", "approved"] = "pending_human_review"
    human_approval_required: bool = True
    approval_granted: bool = False
    state_transitioned: bool = False


class CollaborationSummary(DirectorModel):
    workspace_count: int = Field(ge=0)
    member_count: int = Field(ge=0)
    review_assignment_count: int = Field(ge=0)
    next_command: str | None = None
    messages: tuple[str, ...] = ()
    automatic_action_taken: bool = False


class WorkspaceActivityReport(DirectorModel):
    workspace_id: str
    activity_count: int = Field(ge=0)
    activity_labels: tuple[str, ...] = ()
    persistence_mutated: bool = False
    workflow_modified: bool = False


class CreativeCollaborationReport(DirectorModel):
    session: CollaborationSession
    review_assignments: tuple[ReviewAssignment, ...] = ()
    approval: ApprovalState
    activity: WorkspaceActivityReport
    summary: CollaborationSummary
    collaboration_only: bool = True


class KnowledgeVersion(DirectorModel):
    version_id: str
    project_id: str
    source: Literal["repository_projection"] = "repository_projection"
    created_at: datetime
    persistence_mutated: bool = False


class EvolutionKnowledgeSnapshot(DirectorModel):
    version: KnowledgeVersion
    project_title: str
    metadata_keys: tuple[str, ...] = ()
    chapter_count: int = Field(ge=0)
    page_count: int = Field(ge=0)
    values_redacted: bool = True


class KnowledgeDiff(DirectorModel):
    base_version_id: str | None = None
    target_version_id: str
    added_keys: tuple[str, ...] = ()
    removed_keys: tuple[str, ...] = ()
    changed_values_exposed: bool = False
    merge_performed: bool = False


class KnowledgeTimelineEntry(DirectorModel):
    version_id: str
    event: Literal["snapshot", "comparison"]
    observed_at: datetime
    source: Literal["repository_projection"] = "repository_projection"


class KnowledgeTimeline(DirectorModel):
    entries: tuple[KnowledgeTimelineEntry, ...] = ()
    timeline_only: bool = True


class KnowledgeHistorySummary(DirectorModel):
    version_count: int = Field(ge=0)
    latest_version_id: str | None = None
    repository_read_only: bool = True
    merge_authorized: bool = False


class KnowledgeEvolutionReport(DirectorModel):
    snapshot: EvolutionKnowledgeSnapshot | None = None
    diff: KnowledgeDiff | None = None
    timeline: KnowledgeTimeline
    history: KnowledgeHistorySummary
    persistence_mutated: bool = False


class ProjectMetrics(DirectorModel):
    project_count: int = Field(ge=0)
    chapter_count: int = Field(ge=0)
    page_count: int = Field(ge=0)
    selected_page_reference: str | None = None
    aggregation_only: bool = True


class WorkflowMetrics(DirectorModel):
    current_state: PageState
    history_entries: int = Field(ge=0)
    artifact_count: int = Field(ge=0)
    one_page_scope: bool = True
    execution_started: bool = False


class QualityMetrics(DirectorModel):
    quality_evidence_present: bool
    approval_evidence_present: bool
    quality_passed: bool = False
    approval_granted: bool = False
    analysis_only: bool = True


class ReleaseMetrics(DirectorModel):
    package_version: str = __version__
    release_assets_checked: bool = False
    release_authorized: bool = False
    publication_started: bool = False


class OperationalHealthReport(DirectorModel):
    status: Literal["healthy", "attention"]
    checks: tuple[str, ...] = ()
    operation_started: bool = False


class OperationsSummary(DirectorModel):
    project: ProjectMetrics
    workflow: WorkflowMetrics
    quality: QualityMetrics
    release: ReleaseMetrics
    health: OperationalHealthReport
    automatic_action_taken: bool = False


class ProjectTemplate(DirectorModel):
    name: str
    required_fields: tuple[str, ...] = ("project_title", "project_goal")
    generated: bool = False


class PlanningTemplate(DirectorModel):
    name: str
    sections: tuple[str, ...] = ("objective", "state_machine_evidence", "human_review")
    execution_enabled: bool = False


class ValidationTemplate(DirectorModel):
    name: str
    checks: tuple[str, ...] = ("one_page_scope", "storyboard_guard", "quality_guard")
    validation_executed: bool = False


class WorkspaceTemplate(DirectorModel):
    name: str
    workspace_kinds: tuple[str, ...] = ("editor", "scenario", "review")
    persisted: bool = False


class TemplateSummary(DirectorModel):
    template_count: int = Field(ge=0)
    generated_files: int = 0
    messages: tuple[str, ...] = ()


class DeveloperProductivityReport(DirectorModel):
    project: ProjectTemplate
    planning: PlanningTemplate
    validation: ValidationTemplate
    workspace: WorkspaceTemplate
    summary: TemplateSummary
    filesystem_mutated: bool = False


class CollaborationDashboardDTO(DirectorModel):
    report: CreativeCollaborationReport
    automatic_action_taken: bool = False


class KnowledgeEvolutionDashboardDTO(DirectorModel):
    report: KnowledgeEvolutionReport
    automatic_action_taken: bool = False


class OperationsDashboardDTO(DirectorModel):
    report: OperationsSummary
    automatic_action_taken: bool = False


class DeveloperProductivityDashboardDTO(DirectorModel):
    report: DeveloperProductivityReport
    automatic_action_taken: bool = False


class V31FoundationService:
    """Compose v3.1 planning reports without execution or persistence authority."""

    def __init__(
        self,
        foundation: DirectorPlanningService,
        collaboration: CollaborationPlanningService,
        repository: ProjectRepository,
    ) -> None:
        self._foundation = foundation
        self._collaboration = collaboration
        self._repository = repository

    def creative_collaboration(self, context: WorkflowContext) -> CreativeCollaborationReport:
        session = self._foundation.director_session(context)
        coordination = self._collaboration.multi_agent_foundation(context)
        members = tuple(
            WorkspaceMember(member_id=assignment.agent.name, role=_workspace_role(assignment.agent.name))
            for assignment in coordination.plan.assignments
        )
        workspace = Workspace(
            workspace_id=f"workspace:{session.session.planning_context.page_reference}",
            kind="review",
            page_reference=session.session.planning_context.page_reference,
            current_state=context.state,
            members=members,
        )
        assignments = tuple(
            ReviewAssignment(reviewer=member)
            for member in members
            if member.role in {"editor", "review"}
        )
        approval = ApprovalState(
            status="not_ready" if context.state is not PageState.QUALITY_CHECKED else "pending_human_review"
        )
        activity = WorkspaceActivityReport(
            workspace_id=workspace.workspace_id,
            activity_count=len(context.metadata.get("workflow_history", []))
            if isinstance(context.metadata.get("workflow_history"), list)
            else 0,
            activity_labels=("planning", "human_review_required"),
        )
        return CreativeCollaborationReport(
            session=CollaborationSession(
                session_id=f"collaboration:{workspace.page_reference}:{context.state.value}",
                workspace=workspace,
                objective=session.session.creative_goal.purpose,
                decision_context=session.session.decision_trace,
            ),
            review_assignments=assignments,
            approval=approval,
            activity=activity,
            summary=CollaborationSummary(
                workspace_count=1,
                member_count=len(members),
                review_assignment_count=len(assignments),
                next_command=session.summary.recommended_command,
                messages=("Collaboration is advisory; a human chooses any existing workflow command.",),
            ),
        )

    def knowledge_evolution(self) -> KnowledgeEvolutionReport:
        projects = tuple(self._repository.list())
        snapshots = tuple(_snapshot(project) for project in projects)
        entries = tuple(
            KnowledgeTimelineEntry(
                version_id=snapshot.version.version_id,
                event="snapshot",
                observed_at=snapshot.version.created_at,
            )
            for snapshot in snapshots
        )
        latest = snapshots[-1] if snapshots else None
        diff = (
            KnowledgeDiff(target_version_id=latest.version.version_id)
            if latest is not None
            else None
        )
        return KnowledgeEvolutionReport(
            snapshot=latest,
            diff=diff,
            timeline=KnowledgeTimeline(entries=entries),
            history=KnowledgeHistorySummary(
                version_count=len(snapshots),
                latest_version_id=latest.version.version_id if latest else None,
            ),
        )

    def operations(self, context: WorkflowContext) -> OperationsSummary:
        projects = tuple(self._repository.list())
        history = context.metadata.get("workflow_history", [])
        quality = _mapping(context.artifacts.get("quality", context.page.get("quality")))
        approval = _mapping(context.artifacts.get("approval", context.page.get("approval")))
        project_metrics = ProjectMetrics(
            project_count=len(projects),
            chapter_count=sum(len(project.chapters) for project in projects),
            page_count=sum(len(project.pages) for project in projects),
            selected_page_reference=str(context.page.get("id", context.page.get("page_number", "page"))),
        )
        workflow_metrics = WorkflowMetrics(
            current_state=context.state,
            history_entries=len(history) if isinstance(history, list) else 0,
            artifact_count=len(context.artifacts),
        )
        quality_metrics = QualityMetrics(
            quality_evidence_present=bool(quality) or context.state in {PageState.QUALITY_CHECKED, PageState.APPROVED},
            approval_evidence_present=bool(approval) or context.state is PageState.APPROVED,
        )
        release_metrics = ReleaseMetrics(release_assets_checked=True)
        health = OperationalHealthReport(
            status="healthy" if project_metrics.project_count >= 0 else "attention",
            checks=("repository_projection", "one_page_scope", "no_operation_started"),
        )
        return OperationsSummary(
            project=project_metrics,
            workflow=workflow_metrics,
            quality=quality_metrics,
            release=release_metrics,
            health=health,
        )

    def developer_productivity(self) -> DeveloperProductivityReport:
        return DeveloperProductivityReport(
            project=ProjectTemplate(name="project_brief"),
            planning=PlanningTemplate(name="one_page_planning"),
            validation=ValidationTemplate(name="workflow_guard_review"),
            workspace=WorkspaceTemplate(name="human_collaboration"),
            summary=TemplateSummary(
                template_count=4,
                messages=("Templates are descriptors only; no file or workflow was generated.",),
            ),
        )

    def collaboration_dashboard(self, context: WorkflowContext) -> CollaborationDashboardDTO:
        return CollaborationDashboardDTO(report=self.creative_collaboration(context))

    def knowledge_evolution_dashboard(self) -> KnowledgeEvolutionDashboardDTO:
        return KnowledgeEvolutionDashboardDTO(report=self.knowledge_evolution())

    def operations_dashboard(self, context: WorkflowContext) -> OperationsDashboardDTO:
        return OperationsDashboardDTO(report=self.operations(context))

    def developer_productivity_dashboard(self) -> DeveloperProductivityDashboardDTO:
        return DeveloperProductivityDashboardDTO(report=self.developer_productivity())


def _snapshot(project: Any) -> EvolutionKnowledgeSnapshot:
    updated = project.updated_at if isinstance(project.updated_at, datetime) else datetime.now(UTC)
    version = KnowledgeVersion(
        version_id=f"{project.id}:{updated.isoformat()}",
        project_id=project.id,
        created_at=updated,
    )
    return EvolutionKnowledgeSnapshot(
        version=version,
        project_title=project.title,
        metadata_keys=tuple(sorted(str(key) for key in project.metadata)),
        chapter_count=len(project.chapters),
        page_count=len(project.pages),
    )


def _workspace_role(name: str) -> Literal["editor", "scenario", "character", "storyboard", "review", "approver"]:
    mapping: dict[str, Literal["editor", "scenario", "character", "storyboard", "review", "approver"]] = {
        "editor": "editor",
        "story": "scenario",
        "character": "character",
        "storyboard": "storyboard",
        "review": "review",
    }
    return mapping.get(name, "review")


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
