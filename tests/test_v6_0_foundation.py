"""Contracts for the read-only v6.0 Creative Production Platform foundation."""

from __future__ import annotations

from pathlib import Path

import pytest

from manga_director.domain.state_machine import PageState
from manga_director.production import (
    CollaborationAssignmentDTO,
    CollaborationNotificationDTO,
    CollaborationUpdateDTO,
    CollaborationUserDTO,
    KnowledgeCoreReferenceDTO,
    ProjectHubReferenceDTO,
    ServiceRegistryEntryDTO,
    V60CreativeProductionPlatformFoundationService,
    WorkspaceHubReferenceDTO,
)
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "volume-1-page-1"},
        state=PageState.QUALITY_CHECKED,
        artifacts={
            PageState.STORYBOARDED.value: {"panels": []},
            PageState.QUALITY_CHECKED.value: {"status": "passed"},
        },
        metadata={
            "story_context": {"beat": "resolution"},
            "character_context": {"hero": "Aki"},
            "world_context": {"location": "station"},
            "timeline_context": {"scene": 8},
        },
    )


def test_production_core_reuses_v5_evidence_without_workflow_mutation() -> None:
    context = _context()
    before = context.model_dump()

    report = V60CreativeProductionPlatformFoundationService().production_core("volume-1", context)

    assert report.production.page_count == 1
    assert report.production.production_executed is False
    assert report.state_machine_authoritative is True
    assert report.v5_7_evidence.project.project.quality_review_completed is True
    assert context.model_dump() == before


def test_workspace_and_project_hubs_support_references_across_multiple_projects() -> None:
    service = V60CreativeProductionPlatformFoundationService()
    projects = service.project_hub(
        (
            ProjectHubReferenceDTO(project_id="volume-2", title="Two"),
            ProjectHubReferenceDTO(project_id="volume-1", title="One"),
        )
    )
    workspaces = service.workspace_hub(
        (
            WorkspaceHubReferenceDTO(workspace_id="workspace:two", project_id="volume-2", label="Two"),
            WorkspaceHubReferenceDTO(workspace_id="workspace:one", project_id="volume-1", label="One"),
        )
    )

    assert tuple(project.project_id for project in projects.projects) == ("volume-1", "volume-2")
    assert projects.cross_project_workflow_executed is False
    assert workspaces.workspace_count == 2
    assert workspaces.multi_workspace_ready is True
    assert workspaces.workspace_mutated is False


def test_project_hub_rejects_duplicate_project_references() -> None:
    with pytest.raises(ValueError, match="project_id values must be unique"):
        V60CreativeProductionPlatformFoundationService().project_hub(
            (
                ProjectHubReferenceDTO(project_id="volume-1", title="One"),
                ProjectHubReferenceDTO(project_id="volume-1", title="Duplicate"),
            )
        )


def test_knowledge_core_is_provenance_bearing_and_read_only() -> None:
    report = V60CreativeProductionPlatformFoundationService().knowledge_core(
        (
            KnowledgeCoreReferenceDTO(
                knowledge_id="story:volume-1",
                project_id="volume-1",
                kind="story",
                source_reference="story_context",
                provenance="workflow-metadata",
            ),
        )
    )

    assert report.knowledge_count == 1
    assert report.references[0].knowledge_persisted is False
    assert report.graph_built is False
    assert report.source_repository_changed is False


def test_knowledge_core_sorts_references_and_rejects_duplicate_identifiers() -> None:
    service = V60CreativeProductionPlatformFoundationService()
    report = service.knowledge_core(
        (
            KnowledgeCoreReferenceDTO(
                knowledge_id="world:volume-1",
                project_id="volume-1",
                kind="world",
                source_reference="world_context",
                provenance="workflow-metadata",
            ),
            KnowledgeCoreReferenceDTO(
                knowledge_id="story:volume-1",
                project_id="volume-1",
                kind="story",
                source_reference="story_context",
                provenance="workflow-metadata",
            ),
        )
    )

    assert tuple(reference.knowledge_id for reference in report.references) == (
        "story:volume-1",
        "world:volume-1",
    )

    with pytest.raises(ValueError, match="knowledge_id values must be unique"):
        service.knowledge_core(
            (
                KnowledgeCoreReferenceDTO(
                    knowledge_id="story:volume-1",
                    project_id="volume-1",
                    kind="story",
                    source_reference="story_context",
                    provenance="workflow-metadata",
                ),
                KnowledgeCoreReferenceDTO(
                    knowledge_id="story:volume-1",
                    project_id="volume-1",
                    kind="story",
                    source_reference="alternate_story_context",
                    provenance="workflow-metadata",
                ),
            )
        )


def test_ai_orchestrator_keeps_human_approval_and_execution_boundaries() -> None:
    report = V60CreativeProductionPlatformFoundationService().ai_orchestrator("volume-1", _context())

    assert report.orchestrator.human_approval_required is True
    assert report.orchestrator.plan_generated is False
    assert report.orchestrator.execution_dispatched is False
    assert report.orchestrator.workflow_mutated is False
    assert report.orchestrator.evidence_references == (
        "story_context",
        "character_context",
        "world_context",
        "timeline_context",
    )


def test_ai_orchestrator_reports_only_supplied_evidence_without_autonomous_completion() -> None:
    context = _context().model_copy(update={"metadata": {"story_context": {"beat": "hook"}}})
    before = context.model_dump()

    report = V60CreativeProductionPlatformFoundationService().ai_orchestrator("volume-1", context)

    assert report.orchestrator.evidence_references == ("story_context",)
    assert report.orchestrator.plan_generated is False
    assert report.orchestrator.execution_dispatched is False
    assert report.orchestrator.workflow_mutated is False
    assert context.model_dump() == before


def test_collaboration_and_service_registry_are_observational() -> None:
    service = V60CreativeProductionPlatformFoundationService()
    collaboration = service.collaboration_core(
        (
            CollaborationAssignmentDTO(
                assignment_id="review:volume-1",
                project_id="volume-1",
                workspace_id="workspace:one",
                role="reviewer",
                assignee_reference="editor-1",
            ),
        )
    )
    registry = service.service_registry(
        (
            ServiceRegistryEntryDTO(
                service_id="production-core",
                capability="one-page-evidence",
                owner="platform_core",
                compatibility="v5_additive",
            ),
        )
    )

    assert collaboration.assignments[0].approval_granted is False
    assert collaboration.collaboration_executed is False
    assert registry.services[0].service_registered is False
    assert registry.registry_mutated is False


def test_user_role_management_reports_supplied_members_without_provisioning() -> None:
    report = V60CreativeProductionPlatformFoundationService().user_role_management(
        (
            CollaborationUserDTO(
                user_id="reviewer-1",
                display_name="Reviewer",
                role="reviewer",
                workspace_ids=("workspace:one",),
            ),
            CollaborationUserDTO(
                user_id="editor-1",
                display_name="Editor",
                role="editor",
                workspace_ids=("workspace:one",),
            ),
        )
    )

    assert tuple(user.user_id for user in report.users) == ("editor-1", "reviewer-1")
    assert tuple(coverage.role for coverage in report.roles) == ("editor", "reviewer")
    assert report.roles[0].member_ids == ("editor-1",)
    assert report.user_count == report.role_count == 2
    assert report.users[0].user_registered is False
    assert report.users[0].membership_changed is False
    assert report.identity_provider_changed is False
    assert report.membership_persisted is False


def test_user_role_management_rejects_duplicate_user_references() -> None:
    user = CollaborationUserDTO(user_id="editor-1", display_name="Editor", role="editor")

    with pytest.raises(ValueError, match="user_id values must be unique"):
        V60CreativeProductionPlatformFoundationService().user_role_management((user, user))


def test_team_workspace_scopes_team_evidence_without_workspace_mutation() -> None:
    report = V60CreativeProductionPlatformFoundationService().team_workspace(
        "volume-1",
        "workspace:one",
        users=(
            CollaborationUserDTO(
                user_id="editor-1",
                display_name="Editor",
                role="editor",
                workspace_ids=("workspace:one",),
            ),
            CollaborationUserDTO(
                user_id="reviewer-2",
                display_name="Reviewer",
                role="reviewer",
                workspace_ids=("workspace:two",),
            ),
        ),
        assignments=(
            CollaborationAssignmentDTO(
                assignment_id="review:one",
                project_id="volume-1",
                workspace_id="workspace:one",
                role="editor",
                assignee_reference="editor-1",
            ),
            CollaborationAssignmentDTO(
                assignment_id="review:other",
                project_id="volume-2",
                workspace_id="workspace:two",
                role="reviewer",
                assignee_reference="reviewer-2",
            ),
        ),
    )

    assert report.workspace.member_ids == ("editor-1",)
    assert report.workspace.assignment_ids == ("review:one",)
    assert tuple(coverage.role for coverage in report.roles) == ("editor",)
    assert report.all_reviews_required is True
    assert report.workspace.workspace_created is False
    assert report.workspace.membership_changed is False
    assert report.workspace.assignments_changed is False
    assert report.workspace_persisted is False
    assert report.collaboration_executed is False


def test_realtime_collaboration_scopes_update_evidence_without_transport() -> None:
    report = V60CreativeProductionPlatformFoundationService().realtime_collaboration(
        "volume-1",
        "workspace:one",
        (
            CollaborationUpdateDTO(
                update_id="presence:one",
                project_id="volume-1",
                workspace_id="workspace:one",
                actor_reference="editor-1",
                update_kind="presence",
                sequence=2,
            ),
            CollaborationUpdateDTO(
                update_id="comment:one",
                project_id="volume-1",
                workspace_id="workspace:one",
                actor_reference="reviewer-1",
                update_kind="comment",
                sequence=1,
            ),
            CollaborationUpdateDTO(
                update_id="review:other",
                project_id="volume-2",
                workspace_id="workspace:two",
                actor_reference="reviewer-2",
                update_kind="review_request",
                sequence=3,
            ),
        ),
    )

    assert tuple(update.update_id for update in report.updates) == ("comment:one", "presence:one")
    assert report.update_count == 2
    assert report.latest_sequence == 2
    assert report.existing_event_bus_preserved is True
    assert report.transport_connected is False
    assert report.update_published is False
    assert report.collaboration_executed is False


def test_realtime_collaboration_rejects_duplicate_update_references() -> None:
    update = CollaborationUpdateDTO(
        update_id="presence:one",
        project_id="volume-1",
        workspace_id="workspace:one",
        actor_reference="editor-1",
        update_kind="presence",
        sequence=1,
    )

    with pytest.raises(ValueError, match="update_id values must be unique"):
        V60CreativeProductionPlatformFoundationService().realtime_collaboration(
            "volume-1", "workspace:one", (update, update)
        )


def test_collaboration_history_audit_scopes_evidence_without_persisting_history() -> None:
    report = V60CreativeProductionPlatformFoundationService().collaboration_history_audit(
        "volume-1",
        "workspace:one",
        updates=(
            CollaborationUpdateDTO(
                update_id="comment:one",
                project_id="volume-1",
                workspace_id="workspace:one",
                actor_reference="reviewer-1",
                update_kind="comment",
                sequence=2,
            ),
            CollaborationUpdateDTO(
                update_id="comment:other",
                project_id="volume-2",
                workspace_id="workspace:two",
                actor_reference="reviewer-2",
                update_kind="comment",
                sequence=3,
            ),
        ),
        assignments=(
            CollaborationAssignmentDTO(
                assignment_id="review:one",
                project_id="volume-1",
                workspace_id="workspace:one",
                role="reviewer",
                assignee_reference="reviewer-1",
            ),
            CollaborationAssignmentDTO(
                assignment_id="review:other",
                project_id="volume-2",
                workspace_id="workspace:two",
                role="reviewer",
                assignee_reference="reviewer-2",
            ),
        ),
    )

    assert tuple(entry.entry_id for entry in report.entries) == (
        "audit:assignment:review:one",
        "audit:update:comment:one",
    )
    assert report.assignment_evidence_count == 1
    assert report.update_evidence_count == 1
    assert report.latest_update_sequence == 2
    assert report.history_persisted is False
    assert report.retention_enforced is False
    assert report.audit_exported is False


def test_notification_presence_scopes_evidence_without_sending_or_connecting() -> None:
    report = V60CreativeProductionPlatformFoundationService().notification_presence(
        "volume-1",
        "workspace:one",
        notifications=(
            CollaborationNotificationDTO(
                notification_id="notification:one",
                project_id="volume-1",
                workspace_id="workspace:one",
                recipient_reference="editor-1",
                update_reference="comment:one",
                notification_kind="comment",
            ),
            CollaborationNotificationDTO(
                notification_id="notification:other",
                project_id="volume-2",
                workspace_id="workspace:two",
                recipient_reference="editor-2",
                update_reference="comment:other",
                notification_kind="comment",
            ),
        ),
        updates=(
            CollaborationUpdateDTO(
                update_id="presence:one",
                project_id="volume-1",
                workspace_id="workspace:one",
                actor_reference="editor-1",
                update_kind="presence",
                sequence=1,
            ),
            CollaborationUpdateDTO(
                update_id="comment:one",
                project_id="volume-1",
                workspace_id="workspace:one",
                actor_reference="reviewer-1",
                update_kind="comment",
                sequence=2,
            ),
        ),
    )

    assert tuple(notification.notification_id for notification in report.notifications) == (
        "notification:one",
    )
    assert report.presences[0].actor_reference == "editor-1"
    assert report.notification_count == report.presence_count == 1
    assert report.existing_notification_service_preserved is True
    assert report.notifications_sent is False
    assert report.presence_transport_connected is False


def test_foundation_composes_all_platform_areas_without_automatic_action() -> None:
    report = V60CreativeProductionPlatformFoundationService().foundation(
        "volume-1",
        _context(),
        projects=(ProjectHubReferenceDTO(project_id="volume-1", title="One"),),
        workspaces=(
            WorkspaceHubReferenceDTO(
                workspace_id="workspace:one", project_id="volume-1", label="One"
            ),
        ),
        knowledge=(
            KnowledgeCoreReferenceDTO(
                knowledge_id="story:volume-1",
                project_id="volume-1",
                kind="story",
                source_reference="story_context",
                provenance="workflow-metadata",
            ),
        ),
        services=(
            ServiceRegistryEntryDTO(
                service_id="production-core",
                capability="one-page-evidence",
                owner="platform_core",
                compatibility="v5_additive",
            ),
        ),
    )

    assert report.v5_compatibility_preserved is True
    assert report.automatic_action_taken is False
    assert report.production.production.page_count == 1
    assert report.knowledge.knowledge_count == 1
    assert report.services.service_count == 1


def test_v6_production_core_rejects_multi_page_context() -> None:
    context = _context().model_copy(update={"page": {"pages": [{"id": "one"}, {"id": "two"}]}})

    with pytest.raises(ValueError, match="exactly one Page"):
        V60CreativeProductionPlatformFoundationService().production_core("volume-1", context)


def test_v6_foundation_keeps_delivery_repository_and_execution_boundaries_out() -> None:
    source = (ROOT / "src/manga_director/production/v6_0_foundation.py").read_text(
        encoding="utf-8"
    )

    for forbidden in (
        "manga_director.api",
        "manga_director.cli",
        "manga_director.mcp",
        "manga_director.repositories",
        "workflow.engine",
        ".execute(",
        ".advance(",
        "save(",
        ".publish(",
        ".load(",
    ):
        assert forbidden not in source


def test_v6_foundation_documentation_is_available() -> None:
    documents = (
        "docs/PRODUCTION_CORE.md",
        "docs/WORKSPACE_HUB.md",
        "docs/PROJECT_HUB.md",
        "docs/KNOWLEDGE_CORE.md",
        "docs/AI_ORCHESTRATOR.md",
        "docs/COLLABORATION_CORE.md",
        "docs/USER_ROLE_MANAGEMENT.md",
        "docs/TEAM_WORKSPACE.md",
        "docs/REALTIME_COLLABORATION.md",
        "docs/COLLABORATION_HISTORY_AUDIT.md",
        "docs/NOTIFICATION_PRESENCE.md",
        "docs/SERVICE_REGISTRY.md",
    )

    assert all((ROOT / document).is_file() for document in documents)
