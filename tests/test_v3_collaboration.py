from __future__ import annotations

from typing import cast

from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.api import ObservabilityApplication
from manga_director.api.observability import create_observability_app
from manga_director.domain.project import Page, Project
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
    WorkflowPlanner,
)
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext


def _service() -> tuple[CollaborationPlanningService, InMemoryRepository]:
    repository = InMemoryRepository()
    repository.save(
        Project(
            id="pilot",
            title="Pilot",
            pages=[Page(page_number=1)],
            metadata={
                "character_roster": "not projected",
                "world": "not projected",
                "story_theme": "not projected",
                "asset_library": "not projected",
            },
        )
    )
    planning = PlanningService(
        planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime())
    )
    platform = DirectorPlanningService(
        DirectorFoundationService(planning, KnowledgeService(repository)), planning
    )
    return CollaborationPlanningService(platform), repository


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "pilot-1"},
        state=PageState.PROMPT_BUILT,
        artifacts={
            "page_design": {"purpose": "Reveal the map", "panel_count": 2},
            "storyboard": {"panels": []},
        },
        metadata={"workflow_history": [{"step": "prompt", "to": "PromptBuilt"}]},
    )


def test_multi_agent_foundation_plans_roles_without_agent_execution() -> None:
    service, _ = _service()
    context = _context()

    report = service.multi_agent_foundation(context)

    assert report.plan.current_state is PageState.PROMPT_BUILT
    assert report.summary.participant_count == len(report.plan.assignments)
    assert all(not assignment.assigned_for_execution for assignment in report.plan.assignments)
    assert report.plan.execution_dispatched is False
    assert context.state is PageState.PROMPT_BUILT


def test_creative_knowledge_and_relationships_are_repository_read_only() -> None:
    service, repository = _service()

    report = service.creative_knowledge(_context())
    rendered = report.to_json()

    assert "character_roster" in report.character.references
    assert "world" in report.world.references
    assert report.relationships.relationship_count >= 4
    assert report.repository_read_only is True
    assert "not projected" not in rendered
    assert repository.load("pilot").metadata["world"] == "not projected"


def test_director_intelligence_is_advisory_and_never_changes_the_workflow() -> None:
    service, _ = _service()
    context = _context()

    report = service.director_intelligence(context)

    assert report.decision.next_command == "generate"
    assert report.alternatives.execution_enabled is False
    assert report.risk.automatic_mitigation is False
    assert report.recommendation.execution_enabled is False
    assert report.workflow_modified is False
    assert context.state is PageState.PROMPT_BUILT


def test_review_pipeline_is_diagnostic_and_cannot_pass_quality_or_approve() -> None:
    service, _ = _service()
    context = _context()

    report = service.review_pipeline(context)

    assert report.storyboard.storyboard_persisted is True
    assert report.quality.quality_passed is False
    assert report.quality.approval_granted is False
    assert report.summary.review_performed is False
    assert report.diagnostics_only is True
    assert context.state is PageState.PROMPT_BUILT


def test_collaboration_delivery_callbacks_and_mcp_tools_return_safe_dtos() -> None:
    service, _ = _service()
    context = _context()
    application = ObservabilityApplication(
        health=lambda: None,  # type: ignore[arg-type]
        diagnostics=lambda: None,  # type: ignore[arg-type]
        repository_check=lambda: None,  # type: ignore[arg-type]
        multi_agent=lambda: service.agent_dashboard(context),
        creative_knowledge=lambda: service.creative_knowledge_dashboard(context),
        director_intelligence=lambda: service.director_intelligence_dashboard(context),
        review_pipeline=lambda: service.review_pipeline_dashboard(context),
        knowledge_relationship=lambda: service.creative_knowledge(context).relationships,
    )
    registry = default_tool_registry(
        cast(MangaApplicationService, None),
        multi_agent_provider=lambda: service.agent_dashboard(context),
        creative_knowledge_provider=lambda: service.creative_knowledge_dashboard(context),
        director_intelligence_provider=lambda: service.director_intelligence_dashboard(context),
        review_pipeline_provider=lambda: service.review_pipeline_dashboard(context),
        knowledge_relationship_provider=lambda: service.creative_knowledge(context).relationships,
    )

    assert application.multi_agent_preview()["report"]["plan"]["execution_dispatched"] is False
    assert application.creative_knowledge_preview()["report"]["repository_read_only"] is True
    assert application.director_intelligence_preview()["report"]["workflow_modified"] is False
    assert application.review_pipeline_preview()["report"]["quality"]["approval_granted"] is False
    assert application.knowledge_relationship_preview()["analysis_only"] is True
    routes = {route.path for route in create_observability_app(application).routes}
    assert {"/v3/agents", "/v3/creative-knowledge", "/v3/director-intelligence", "/v3/review", "/v3/knowledge-relationships"} <= routes
    assert registry.invoke("multi_agent_foundation", {}).data["report"]["plan"]["execution_dispatched"] is False
    assert registry.invoke("creative_knowledge", {}).data["report"]["repository_read_only"] is True
    assert registry.invoke("director_intelligence", {}).data["report"]["workflow_modified"] is False
    assert registry.invoke("review_pipeline", {}).data["report"]["quality"]["approval_granted"] is False
    assert registry.invoke("knowledge_relationship", {}).data["analysis_only"] is True
