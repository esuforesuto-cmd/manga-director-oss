"""Contracts for v3.1 collaboration, knowledge, operations, and template DTOs."""

from __future__ import annotations

from typing import cast

from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.api import ObservabilityApplication
from manga_director.api.observability import create_observability_app
from manga_director.domain.project import Chapter, Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.mcp.application import MangaApplicationService
from manga_director.mcp.registry import default_tool_registry
from manga_director.production import (
    CollaborationPlanningService,
    DirectorFoundationService,
    DirectorPlanningService,
    KnowledgeService,
    PlanningService,
    ProviderOrchestrator,
    V31FoundationService,
    WorkflowPlanner,
)
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext


def _service() -> tuple[V31FoundationService, InMemoryRepository]:
    repository = InMemoryRepository()
    repository.save(
        Project(
            id="pilot",
            title="Pilot",
            chapters=[Chapter(id="one", title="One", page_numbers=[1])],
            pages=[Page(page_number=1)],
            metadata={"world": "not exposed", "story_theme": "not exposed"},
        )
    )
    planning = PlanningService(
        planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime())
    )
    foundation = DirectorPlanningService(
        DirectorFoundationService(planning, KnowledgeService(repository)), planning
    )
    return V31FoundationService(foundation, CollaborationPlanningService(foundation), repository), repository


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "pilot-1"},
        state=PageState.PROMPT_BUILT,
        artifacts={"page_design": {"purpose": "Reveal the map"}, "storyboard": {"panels": []}},
        metadata={"workflow_history": [{"step": "prompt", "to": "PromptBuilt"}]},
    )


def test_creative_collaboration_is_human_owned_and_cannot_approve_or_execute() -> None:
    service, _ = _service()
    context = _context()

    report = service.creative_collaboration(context)

    assert report.session.workspace.persisted is False
    assert report.session.execution_enabled is False
    assert report.approval.approval_granted is False
    assert report.approval.state_transitioned is False
    assert report.summary.automatic_action_taken is False
    assert context.state is PageState.PROMPT_BUILT


def test_knowledge_evolution_is_redacted_and_repository_read_only() -> None:
    service, repository = _service()

    report = service.knowledge_evolution()
    rendered = report.to_json()

    assert report.snapshot is not None
    assert report.snapshot.values_redacted is True
    assert report.diff is not None and report.diff.merge_performed is False
    assert report.history.repository_read_only is True
    assert "not exposed" not in rendered
    assert repository.load("pilot").metadata["world"] == "not exposed"


def test_operations_foundation_is_one_page_analysis_without_automation() -> None:
    service, _ = _service()
    context = _context()

    report = service.operations(context)

    assert report.project.project_count == 1
    assert report.project.page_count == 1
    assert report.workflow.one_page_scope is True
    assert report.workflow.execution_started is False
    assert report.release.release_authorized is False
    assert report.health.operation_started is False
    assert context.state is PageState.PROMPT_BUILT


def test_developer_productivity_templates_do_not_generate_files_or_validation() -> None:
    service, _ = _service()

    report = service.developer_productivity()

    assert report.filesystem_mutated is False
    assert report.project.generated is False
    assert report.planning.execution_enabled is False
    assert report.validation.validation_executed is False
    assert report.workspace.persisted is False
    assert report.summary.generated_files == 0


def test_v3_1_delivery_dtos_are_safe_for_fastapi_and_mcp() -> None:
    service, _ = _service()
    context = _context()
    application = ObservabilityApplication(
        health=lambda: None,  # type: ignore[arg-type]
        diagnostics=lambda: None,  # type: ignore[arg-type]
        repository_check=lambda: None,  # type: ignore[arg-type]
        collaboration_foundation=lambda: service.collaboration_dashboard(context),
        knowledge_evolution=service.knowledge_evolution_dashboard,
        operations_foundation=lambda: service.operations_dashboard(context),
        developer_productivity=service.developer_productivity_dashboard,
        project_metrics=lambda: service.operations_dashboard(context).report.project,
    )
    registry = default_tool_registry(
        cast(MangaApplicationService, None),
        collaboration_foundation_provider=lambda: service.collaboration_dashboard(context),
        knowledge_evolution_provider=service.knowledge_evolution_dashboard,
        operations_foundation_provider=lambda: service.operations_dashboard(context),
        developer_productivity_provider=service.developer_productivity_dashboard,
        project_metrics_provider=lambda: service.operations_dashboard(context).report.project,
    )

    assert application.collaboration_foundation_preview()["automatic_action_taken"] is False
    assert application.knowledge_evolution_preview()["report"]["persistence_mutated"] is False
    assert application.operations_foundation_preview()["automatic_action_taken"] is False
    assert application.developer_productivity_preview()["report"]["filesystem_mutated"] is False
    assert application.project_metrics_preview()["aggregation_only"] is True
    routes = {route.path for route in create_observability_app(application).routes}
    assert {
        "/v3.1/collaboration",
        "/v3.1/knowledge-evolution",
        "/v3.1/operations",
        "/v3.1/developer-productivity",
        "/v3.1/project-metrics",
    } <= routes
    assert registry.invoke("collaboration_foundation", {}).data["automatic_action_taken"] is False
    assert registry.invoke("knowledge_evolution", {}).data["report"]["persistence_mutated"] is False
    assert registry.invoke("operations_foundation", {}).data["automatic_action_taken"] is False
    assert registry.invoke("developer_productivity", {}).data["report"]["filesystem_mutated"] is False
    assert registry.invoke("project_metrics", {}).data["aggregation_only"] is True
