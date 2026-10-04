"""Read-only v6.0 Creative Production Platform foundation DTOs.

This Application-layer module composes existing v5.7 one-page evidence with
caller-supplied cross-project references. It does not execute AI work, mutate
projects or workspaces, persist knowledge, alter collaboration, or bypass the
StateMachine.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from pydantic import Field

from manga_director.domain.state_machine import PageState
from manga_director.production.director import DirectorModel
from manga_director.production.v5_7_platform_foundation import (
    ProductionPlatformFoundationReport,
    V57ProductionPlatformFoundationService,
)
from manga_director.workflow.contracts import WorkflowContext

CollaborationRole = Literal["director", "editor", "writer", "artist", "reviewer", "operator"]


class ProductionCoreDTO(DirectorModel):
    platform_id: str
    project_id: str
    page_reference: str
    current_state: PageState
    page_count: Literal[1] = 1
    production_executed: Literal[False] = False
    workflow_mutated: Literal[False] = False


class ProductionCoreReport(DirectorModel):
    production: ProductionCoreDTO
    v5_7_evidence: ProductionPlatformFoundationReport
    state_machine_authoritative: Literal[True] = True
    planning_only: Literal[True] = True


class ProjectHubReferenceDTO(DirectorModel):
    project_id: str
    title: str
    workspace_ids: tuple[str, ...] = ()
    project_loaded: Literal[False] = False
    project_persisted: Literal[False] = False


class ProjectHubReport(DirectorModel):
    projects: tuple[ProjectHubReferenceDTO, ...] = ()
    project_count: int = Field(default=0, ge=0)
    cross_project_workflow_executed: Literal[False] = False
    planning_only: Literal[True] = True


class WorkspaceHubReferenceDTO(DirectorModel):
    workspace_id: str
    project_id: str
    label: str
    page_reference: str | None = None
    workspace_created: Literal[False] = False
    workspace_persisted: Literal[False] = False


class WorkspaceHubReport(DirectorModel):
    workspaces: tuple[WorkspaceHubReferenceDTO, ...] = ()
    workspace_count: int = Field(default=0, ge=0)
    multi_workspace_ready: bool
    workspace_mutated: Literal[False] = False
    planning_only: Literal[True] = True


class KnowledgeCoreReferenceDTO(DirectorModel):
    knowledge_id: str
    project_id: str
    kind: Literal["story", "character", "world", "asset", "production", "review"]
    source_reference: str
    provenance: str
    knowledge_persisted: Literal[False] = False


class KnowledgeCoreReport(DirectorModel):
    references: tuple[KnowledgeCoreReferenceDTO, ...] = ()
    knowledge_count: int = Field(default=0, ge=0)
    graph_built: Literal[False] = False
    source_repository_changed: Literal[False] = False
    analysis_only: Literal[True] = True


class AIOrchestratorFoundationDTO(DirectorModel):
    orchestration_id: str
    project_id: str
    page_reference: str
    capability_references: tuple[str, ...] = ()
    evidence_references: tuple[str, ...] = ()
    human_approval_required: Literal[True] = True
    plan_generated: Literal[False] = False
    execution_dispatched: Literal[False] = False
    workflow_mutated: Literal[False] = False


class AIOrchestratorFoundationReport(DirectorModel):
    orchestrator: AIOrchestratorFoundationDTO
    recommendation: str
    planning_only: Literal[True] = True


class CollaborationAssignmentDTO(DirectorModel):
    assignment_id: str
    project_id: str
    workspace_id: str
    role: CollaborationRole
    assignee_reference: str
    review_required: Literal[True] = True
    assignment_created: Literal[False] = False
    approval_granted: Literal[False] = False


class CollaborationCoreReport(DirectorModel):
    assignments: tuple[CollaborationAssignmentDTO, ...] = ()
    assignment_count: int = Field(default=0, ge=0)
    collaboration_executed: Literal[False] = False
    planning_only: Literal[True] = True


class CollaborationUserDTO(DirectorModel):
    """Caller-supplied collaboration identity reference without user provisioning."""

    user_id: str
    display_name: str
    role: CollaborationRole
    workspace_ids: tuple[str, ...] = ()
    user_registered: Literal[False] = False
    membership_changed: Literal[False] = False


class CollaborationRoleCoverageDTO(DirectorModel):
    role: CollaborationRole
    member_ids: tuple[str, ...] = ()
    member_count: int = Field(default=0, ge=0)
    role_policy_changed: Literal[False] = False


class UserRoleManagementReport(DirectorModel):
    users: tuple[CollaborationUserDTO, ...] = ()
    roles: tuple[CollaborationRoleCoverageDTO, ...] = ()
    user_count: int = Field(default=0, ge=0)
    role_count: int = Field(default=0, ge=0)
    identity_provider_changed: Literal[False] = False
    membership_persisted: Literal[False] = False
    planning_only: Literal[True] = True


class TeamWorkspaceDTO(DirectorModel):
    workspace_id: str
    project_id: str
    member_ids: tuple[str, ...] = ()
    assignment_ids: tuple[str, ...] = ()
    role_count: int = Field(default=0, ge=0)
    workspace_created: Literal[False] = False
    membership_changed: Literal[False] = False
    assignments_changed: Literal[False] = False


class TeamWorkspaceReport(DirectorModel):
    workspace: TeamWorkspaceDTO
    users: tuple[CollaborationUserDTO, ...] = ()
    assignments: tuple[CollaborationAssignmentDTO, ...] = ()
    roles: tuple[CollaborationRoleCoverageDTO, ...] = ()
    all_reviews_required: bool
    workspace_persisted: Literal[False] = False
    collaboration_executed: Literal[False] = False
    planning_only: Literal[True] = True


class CollaborationUpdateDTO(DirectorModel):
    update_id: str
    project_id: str
    workspace_id: str
    actor_reference: str
    update_kind: Literal["presence", "comment", "review_request"]
    sequence: int = Field(ge=0)
    update_received: Literal[False] = False
    update_delivered: Literal[False] = False
    update_persisted: Literal[False] = False


class RealtimeCollaborationReport(DirectorModel):
    project_id: str
    workspace_id: str
    updates: tuple[CollaborationUpdateDTO, ...] = ()
    update_count: int = Field(default=0, ge=0)
    latest_sequence: int | None = Field(default=None, ge=0)
    existing_event_bus_preserved: Literal[True] = True
    transport_connected: Literal[False] = False
    update_published: Literal[False] = False
    collaboration_executed: Literal[False] = False
    planning_only: Literal[True] = True


class CollaborationAuditEntryDTO(DirectorModel):
    entry_id: str
    project_id: str
    workspace_id: str
    evidence_kind: Literal["assignment", "update"]
    evidence_reference: str
    sequence: int | None = Field(default=None, ge=0)
    audit_recorded: Literal[False] = False
    audit_persisted: Literal[False] = False


class CollaborationHistoryAuditReport(DirectorModel):
    project_id: str
    workspace_id: str
    entries: tuple[CollaborationAuditEntryDTO, ...] = ()
    assignment_evidence_count: int = Field(default=0, ge=0)
    update_evidence_count: int = Field(default=0, ge=0)
    latest_update_sequence: int | None = Field(default=None, ge=0)
    history_persisted: Literal[False] = False
    retention_enforced: Literal[False] = False
    audit_exported: Literal[False] = False
    planning_only: Literal[True] = True


class CollaborationNotificationDTO(DirectorModel):
    notification_id: str
    project_id: str
    workspace_id: str
    recipient_reference: str
    update_reference: str
    notification_kind: Literal["comment", "review_request"]
    notification_prepared: Literal[False] = False
    notification_sent: Literal[False] = False
    notification_persisted: Literal[False] = False


class CollaborationPresenceDTO(DirectorModel):
    presence_id: str
    project_id: str
    workspace_id: str
    actor_reference: str
    update_reference: str
    presence_connected: Literal[False] = False
    presence_persisted: Literal[False] = False


class NotificationPresenceReport(DirectorModel):
    project_id: str
    workspace_id: str
    notifications: tuple[CollaborationNotificationDTO, ...] = ()
    presences: tuple[CollaborationPresenceDTO, ...] = ()
    notification_count: int = Field(default=0, ge=0)
    presence_count: int = Field(default=0, ge=0)
    existing_notification_service_preserved: Literal[True] = True
    notifications_sent: Literal[False] = False
    presence_transport_connected: Literal[False] = False
    planning_only: Literal[True] = True


class ServiceRegistryEntryDTO(DirectorModel):
    service_id: str
    capability: str
    owner: Literal[
        "platform_core",
        "workspace_engine",
        "project_manager",
        "knowledge_engine",
        "ai_orchestrator",
        "collaboration_engine",
    ]
    compatibility: Literal["v5_additive", "v6_foundation"]
    service_registered: Literal[False] = False


class ServiceRegistryReport(DirectorModel):
    services: tuple[ServiceRegistryEntryDTO, ...] = ()
    service_count: int = Field(default=0, ge=0)
    registry_mutated: Literal[False] = False
    planning_only: Literal[True] = True


class CreativeProductionPlatformCoreReport(DirectorModel):
    production: ProductionCoreReport
    projects: ProjectHubReport
    workspaces: WorkspaceHubReport
    knowledge: KnowledgeCoreReport
    ai_orchestrator: AIOrchestratorFoundationReport
    collaboration: CollaborationCoreReport
    services: ServiceRegistryReport
    v5_compatibility_preserved: Literal[True] = True
    automatic_action_taken: Literal[False] = False
    planning_only: Literal[True] = True


class V60CreativeProductionPlatformFoundationService:
    """Compose v6.0 platform foundation reports from v5.7 evidence only."""

    def __init__(self) -> None:
        self._v57 = V57ProductionPlatformFoundationService()

    def production_core(self, project_id: str, context: WorkflowContext) -> ProductionCoreReport:
        evidence = self._v57.foundation(project_id, context)
        project = evidence.project.project
        return ProductionCoreReport(
            production=ProductionCoreDTO(
                platform_id=f"creative-production-platform:{project_id}",
                project_id=project_id,
                page_reference=project.page_reference,
                current_state=project.current_state,
            ),
            v5_7_evidence=evidence,
        )

    def project_hub(
        self, projects: tuple[ProjectHubReferenceDTO, ...] = ()
    ) -> ProjectHubReport:
        _require_unique((project.project_id for project in projects), "project_id")
        ordered = tuple(sorted(projects, key=lambda project: project.project_id))
        return ProjectHubReport(projects=ordered, project_count=len(ordered))

    def workspace_hub(
        self, workspaces: tuple[WorkspaceHubReferenceDTO, ...] = ()
    ) -> WorkspaceHubReport:
        _require_unique((workspace.workspace_id for workspace in workspaces), "workspace_id")
        ordered = tuple(sorted(workspaces, key=lambda workspace: workspace.workspace_id))
        return WorkspaceHubReport(
            workspaces=ordered,
            workspace_count=len(ordered),
            multi_workspace_ready=len(ordered) > 1,
        )

    def knowledge_core(
        self, references: tuple[KnowledgeCoreReferenceDTO, ...] = ()
    ) -> KnowledgeCoreReport:
        _require_unique((reference.knowledge_id for reference in references), "knowledge_id")
        ordered = tuple(sorted(references, key=lambda reference: reference.knowledge_id))
        return KnowledgeCoreReport(references=ordered, knowledge_count=len(ordered))

    def ai_orchestrator(self, project_id: str, context: WorkflowContext) -> AIOrchestratorFoundationReport:
        production = self.production_core(project_id, context).production
        evidence_references = tuple(
            key
            for key in ("story_context", "character_context", "world_context", "timeline_context")
            if key in context.metadata
        )
        return AIOrchestratorFoundationReport(
            orchestrator=AIOrchestratorFoundationDTO(
                orchestration_id=f"ai-orchestrator:{project_id}:{production.page_reference}",
                project_id=project_id,
                page_reference=production.page_reference,
                capability_references=("planning", "review-support", "context-reference"),
                evidence_references=evidence_references,
            ),
            recommendation="Use existing StateMachine and human-review boundaries for any next step.",
        )

    def collaboration_core(
        self, assignments: tuple[CollaborationAssignmentDTO, ...] = ()
    ) -> CollaborationCoreReport:
        _require_unique((assignment.assignment_id for assignment in assignments), "assignment_id")
        ordered = tuple(sorted(assignments, key=lambda assignment: assignment.assignment_id))
        return CollaborationCoreReport(assignments=ordered, assignment_count=len(ordered))

    def user_role_management(
        self, users: tuple[CollaborationUserDTO, ...] = ()
    ) -> UserRoleManagementReport:
        """Summarize supplied collaboration users without provisioning or authorization."""

        _require_unique((user.user_id for user in users), "user_id")
        ordered_users = tuple(sorted(users, key=lambda user: user.user_id))
        roles = tuple(
            CollaborationRoleCoverageDTO(
                role=role,
                member_ids=tuple(user.user_id for user in ordered_users if user.role == role),
                member_count=sum(user.role == role for user in ordered_users),
            )
            for role in sorted({user.role for user in ordered_users})
        )
        return UserRoleManagementReport(
            users=ordered_users,
            roles=roles,
            user_count=len(ordered_users),
            role_count=len(roles),
        )

    def team_workspace(
        self,
        project_id: str,
        workspace_id: str,
        users: tuple[CollaborationUserDTO, ...] = (),
        assignments: tuple[CollaborationAssignmentDTO, ...] = (),
    ) -> TeamWorkspaceReport:
        """Scope supplied team evidence without changing a workspace or memberships."""

        users_report = self.user_role_management(users)
        _require_unique((assignment.assignment_id for assignment in assignments), "assignment_id")
        scoped_users = tuple(
            user for user in users_report.users if workspace_id in user.workspace_ids
        )
        scoped_assignments = tuple(
            sorted(
                (
                    assignment
                    for assignment in assignments
                    if assignment.project_id == project_id and assignment.workspace_id == workspace_id
                ),
                key=lambda assignment: assignment.assignment_id,
            )
        )
        roles = self.user_role_management(scoped_users).roles
        return TeamWorkspaceReport(
            workspace=TeamWorkspaceDTO(
                workspace_id=workspace_id,
                project_id=project_id,
                member_ids=tuple(user.user_id for user in scoped_users),
                assignment_ids=tuple(assignment.assignment_id for assignment in scoped_assignments),
                role_count=len(roles),
            ),
            users=scoped_users,
            assignments=scoped_assignments,
            roles=roles,
            all_reviews_required=all(assignment.review_required for assignment in scoped_assignments),
        )

    def realtime_collaboration(
        self,
        project_id: str,
        workspace_id: str,
        updates: tuple[CollaborationUpdateDTO, ...] = (),
    ) -> RealtimeCollaborationReport:
        """Scope supplied collaboration update evidence without live transport."""

        _require_unique((update.update_id for update in updates), "update_id")
        scoped = tuple(
            sorted(
                (
                    update
                    for update in updates
                    if update.project_id == project_id and update.workspace_id == workspace_id
                ),
                key=lambda update: (update.sequence, update.update_id),
            )
        )
        return RealtimeCollaborationReport(
            project_id=project_id,
            workspace_id=workspace_id,
            updates=scoped,
            update_count=len(scoped),
            latest_sequence=scoped[-1].sequence if scoped else None,
        )

    def collaboration_history_audit(
        self,
        project_id: str,
        workspace_id: str,
        updates: tuple[CollaborationUpdateDTO, ...] = (),
        assignments: tuple[CollaborationAssignmentDTO, ...] = (),
    ) -> CollaborationHistoryAuditReport:
        """Build a scoped audit view without recording, retaining, or exporting history."""

        updates_report = self.realtime_collaboration(project_id, workspace_id, updates)
        assignments_report = self.collaboration_core(assignments)
        scoped_assignments = tuple(
            assignment
            for assignment in assignments_report.assignments
            if assignment.project_id == project_id and assignment.workspace_id == workspace_id
        )
        entries = tuple(
            sorted(
                (
                    *(
                        CollaborationAuditEntryDTO(
                            entry_id=f"audit:assignment:{assignment.assignment_id}",
                            project_id=project_id,
                            workspace_id=workspace_id,
                            evidence_kind="assignment",
                            evidence_reference=assignment.assignment_id,
                        )
                        for assignment in scoped_assignments
                    ),
                    *(
                        CollaborationAuditEntryDTO(
                            entry_id=f"audit:update:{update.update_id}",
                            project_id=project_id,
                            workspace_id=workspace_id,
                            evidence_kind="update",
                            evidence_reference=update.update_id,
                            sequence=update.sequence,
                        )
                        for update in updates_report.updates
                    ),
                ),
                key=lambda entry: (
                    entry.sequence is not None,
                    entry.sequence if entry.sequence is not None else -1,
                    entry.entry_id,
                ),
            )
        )
        return CollaborationHistoryAuditReport(
            project_id=project_id,
            workspace_id=workspace_id,
            entries=entries,
            assignment_evidence_count=len(scoped_assignments),
            update_evidence_count=updates_report.update_count,
            latest_update_sequence=updates_report.latest_sequence,
        )

    def notification_presence(
        self,
        project_id: str,
        workspace_id: str,
        notifications: tuple[CollaborationNotificationDTO, ...] = (),
        updates: tuple[CollaborationUpdateDTO, ...] = (),
    ) -> NotificationPresenceReport:
        """Scope notification and presence evidence without sending or connecting."""

        _require_unique((notification.notification_id for notification in notifications), "notification_id")
        updates_report = self.realtime_collaboration(project_id, workspace_id, updates)
        scoped_notifications = tuple(
            sorted(
                (
                    notification
                    for notification in notifications
                    if notification.project_id == project_id
                    and notification.workspace_id == workspace_id
                ),
                key=lambda notification: notification.notification_id,
            )
        )
        presences = tuple(
            CollaborationPresenceDTO(
                presence_id=f"presence:{update.update_id}",
                project_id=project_id,
                workspace_id=workspace_id,
                actor_reference=update.actor_reference,
                update_reference=update.update_id,
            )
            for update in updates_report.updates
            if update.update_kind == "presence"
        )
        return NotificationPresenceReport(
            project_id=project_id,
            workspace_id=workspace_id,
            notifications=scoped_notifications,
            presences=presences,
            notification_count=len(scoped_notifications),
            presence_count=len(presences),
        )

    def service_registry(
        self, services: tuple[ServiceRegistryEntryDTO, ...] = ()
    ) -> ServiceRegistryReport:
        _require_unique((service.service_id for service in services), "service_id")
        ordered = tuple(sorted(services, key=lambda service: service.service_id))
        return ServiceRegistryReport(services=ordered, service_count=len(ordered))

    def foundation(
        self,
        project_id: str,
        context: WorkflowContext,
        *,
        projects: tuple[ProjectHubReferenceDTO, ...] = (),
        workspaces: tuple[WorkspaceHubReferenceDTO, ...] = (),
        knowledge: tuple[KnowledgeCoreReferenceDTO, ...] = (),
        assignments: tuple[CollaborationAssignmentDTO, ...] = (),
        services: tuple[ServiceRegistryEntryDTO, ...] = (),
    ) -> CreativeProductionPlatformCoreReport:
        return CreativeProductionPlatformCoreReport(
            production=self.production_core(project_id, context),
            projects=self.project_hub(projects),
            workspaces=self.workspace_hub(workspaces),
            knowledge=self.knowledge_core(knowledge),
            ai_orchestrator=self.ai_orchestrator(project_id, context),
            collaboration=self.collaboration_core(assignments),
            services=self.service_registry(services),
        )


def _require_unique(values: Iterable[str], field_name: str) -> None:
    items = tuple(values)
    if len(items) != len(set(items)):
        raise ValueError(f"{field_name} values must be unique")
