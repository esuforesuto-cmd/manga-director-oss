"""Contracts for v3.1 review, analytics, operations, and DX diagnostic DTOs."""

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
    V31InsightsService,
    WorkflowPlanner,
)
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext


def _service() -> tuple[V31InsightsService, InMemoryRepository]:
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
    director = DirectorPlanningService(
        DirectorFoundationService(planning, KnowledgeService(repository)), planning
    )
    foundation = V31FoundationService(
        director, CollaborationPlanningService(director), repository
    )
    return V31InsightsService(foundation, repository), repository


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "pilot-1"},
        state=PageState.PROMPT_BUILT,
        artifacts={"page_design": {"purpose": "Reveal the map"}, "storyboard": {"panels": []}},
        metadata={"workflow_history": [{"step": "prompt", "to": "PromptBuilt"}]},
    )


def test_creative_review_is_diagnostic_and_never_approves_or_executes() -> None:
    service, _ = _service()
    context = _context()

    report = service.creative_review(context)

    assert report.review.diagnostic_only is True
    assert report.checklist.review_executed is False
    assert report.approval_recommendation.approval_granted is False
    assert report.approval_recommendation.state_transitioned is False
    assert report.summary.automatic_action_taken is False
    assert context.state is PageState.PROMPT_BUILT


def test_knowledge_analytics_is_redacted_and_repository_read_only() -> None:
    service, repository = _service()

    report = service.knowledge_analytics()
    rendered = report.to_json()

    assert report.repository_port_only is True
    assert report.summary.coverage.values_redacted is True
    assert report.summary.relationships.values_exposed is False
    assert report.summary.usage.external_collection_started is False
    assert "not exposed" not in rendered
    assert repository.load("pilot").metadata["world"] == "not exposed"


def test_operations_intelligence_is_one_page_observation_without_runtime_change() -> None:
    service, _ = _service()
    context = _context()

    report = service.operations_intelligence(context)

    assert report.workflow_efficiency.one_page_scope is True
    assert report.workflow_efficiency.workflow_executed is False
    assert report.project_health.persistence_mutated is False
    assert report.quality_trend.approval_granted is False
    assert report.release_readiness.release_authorized is False
    assert report.automatic_operation_started is False
    assert context.state is PageState.PROMPT_BUILT


def test_developer_experience_hides_configuration_values_and_makes_no_changes() -> None:
    service, _ = _service()

    report = service.developer_experience({"database_url": "not exposed", "mode": "testing"})
    rendered = report.to_json()

    assert report.workspace.workspace_persisted is False
    assert report.workspace.files_generated == 0
    assert report.configuration.status == "valid_shape"
    assert report.configuration.values_exposed is False
    assert report.configuration.configuration_changed is False
    assert report.filesystem_mutated is False
    assert "not exposed" not in rendered


def test_workflow_efficiency_is_a_non_executing_metric_projection() -> None:
    service, _ = _service()
    context = _context()

    report = service.operations_intelligence(context).workflow_efficiency

    assert report.page_reference == "pilot-1"
    assert report.observed_history_entries == 1
    assert report.workflow_executed is False
    assert context.state is PageState.PROMPT_BUILT


def test_v3_1_insight_dashboards_are_safe_for_fastapi_and_mcp() -> None:
    service, _ = _service()
    context = _context()
    application = ObservabilityApplication(
        health=lambda: None,  # type: ignore[arg-type]
        diagnostics=lambda: None,  # type: ignore[arg-type]
        repository_check=lambda: None,  # type: ignore[arg-type]
        creative_review=lambda: service.creative_review_dashboard(context),
        knowledge_analytics=service.knowledge_analytics_dashboard,
        operations_intelligence=lambda: service.operations_intelligence_dashboard(context),
        developer_experience=lambda: service.developer_experience_dashboard({"mode": "testing"}),
        workflow_efficiency=lambda: service.operations_intelligence_dashboard(
            context
        ).report.workflow_efficiency,
    )
    registry = default_tool_registry(
        cast(MangaApplicationService, None),
        creative_review_provider=lambda: service.creative_review_dashboard(context),
        knowledge_analytics_provider=service.knowledge_analytics_dashboard,
        operations_intelligence_provider=lambda: service.operations_intelligence_dashboard(context),
        developer_experience_provider=lambda: service.developer_experience_dashboard(
            {"mode": "testing"}
        ),
        workflow_efficiency_provider=lambda: service.operations_intelligence_dashboard(
            context
        ).report.workflow_efficiency,
    )

    assert application.creative_review_preview()["automatic_action_taken"] is False
    assert application.knowledge_analytics_preview()["report"]["repository_port_only"] is True
    assert application.operations_intelligence_preview()["automatic_action_taken"] is False
    assert application.developer_experience_preview()["report"]["filesystem_mutated"] is False
    assert application.workflow_efficiency_preview()["workflow_executed"] is False
    routes = {route.path for route in create_observability_app(application).routes}
    assert {
        "/v3.1/creative-review",
        "/v3.1/knowledge-analytics",
        "/v3.1/operations-intelligence",
        "/v3.1/developer-experience",
        "/v3.1/workflow-efficiency",
    } <= routes
    assert registry.invoke("creative_review", {}).data["automatic_action_taken"] is False
    assert registry.invoke("knowledge_analytics", {}).data["report"]["repository_port_only"] is True
    assert registry.invoke("operations_intelligence", {}).data["automatic_action_taken"] is False
    assert registry.invoke("developer_experience", {}).data["report"]["filesystem_mutated"] is False
    assert registry.invoke("workflow_efficiency", {}).data["workflow_executed"] is False
