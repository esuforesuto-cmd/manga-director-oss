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
    DirectorFoundationService,
    DirectorPlanningService,
    KnowledgeService,
    PlanningService,
    ProviderOrchestrator,
    WorkflowPlanner,
)
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext


def _service() -> tuple[DirectorPlanningService, InMemoryRepository]:
    repository = InMemoryRepository()
    repository.save(
        Project(
            id="pilot",
            title="Pilot",
            chapters=[Chapter(id="one", title="One", page_numbers=[1])],
            pages=[Page(page_number=1)],
            metadata={"world": "city", "private_note": "not exposed"},
        )
    )
    planning = PlanningService(
        planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime())
    )
    foundation = DirectorFoundationService(planning, KnowledgeService(repository))
    return DirectorPlanningService(foundation, planning), repository


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "pilot-1"},
        state=PageState.PROMPT_BUILT,
        artifacts={
            "page_design": {
                "purpose": "Reveal a clue",
                "reader_emotion": "curiosity",
                "hook": "A door opens",
                "panel_count": 2,
                "panel_roles": ["setup", "reveal"],
            },
            "storyboard": {"panels": []},
        },
        metadata={
            "project_goal": "Complete the pilot safely",
            "chapter_id": "one",
            "workflow_history": [{"step": "prompt", "to": "PromptBuilt"}],
        },
    )


def test_director_platform_session_and_summary_are_one_page_and_non_executing() -> None:
    service, _ = _service()
    context = _context()

    report = service.director_session(context)
    summary = service.planning_summary(context)

    assert report.session.planning_context.page_scope == "one_page"
    assert report.session.execution_context.recommended_command == "generate"
    assert report.session.execution_context.execution_enabled is False
    assert report.summary.execution_performed is False
    assert summary.execution_performed is False
    assert context.state is PageState.PROMPT_BUILT


def test_creative_planning_uses_existing_artifacts_without_generation_or_state_change() -> None:
    service, _ = _service()
    context = _context()

    report = service.creative_planning(context)

    assert report.page.purpose == "Reveal a clue"
    assert report.panels.panel_count == 2
    assert report.panels.storyboard_persisted is True
    assert report.image_generation_invoked is False
    assert report.timeline.entries[0].source == "workflow_history"
    assert context.state is PageState.PROMPT_BUILT


def test_knowledge_foundation_is_repository_derived_redacted_and_read_only() -> None:
    service, repository = _service()

    report = service.knowledge_foundation()
    rendered = report.to_json()

    assert report.snapshot.source == "repository"
    assert report.index.reference_count == 1
    assert report.snapshot.references[0].redacted is True
    assert "private_note" in rendered
    assert "not exposed" not in rendered
    assert report.persistence_mutated is False
    assert repository.load("pilot").metadata["private_note"] == "not exposed"


def test_knowledge_index_reports_an_empty_repository_without_creating_entries() -> None:
    service, repository = _service()
    repository.delete("pilot")

    report = service.knowledge_foundation()

    assert report.health == "empty"
    assert report.index.reference_count == 0
    assert report.index.category_counts == {}
    assert report.snapshot.references == ()
    assert report.persistence_mutated is False
    assert repository.list() == []


def test_workflow_intelligence_and_executive_dtos_never_modify_the_workflow() -> None:
    service, _ = _service()
    context = _context()

    intelligence = service.workflow_intelligence(context)
    platform = service.director_platform(context)
    creative = service.creative_dashboard(context)
    knowledge = service.knowledge_dashboard()
    workflow = service.workflow_dashboard(context)

    assert intelligence.recommendation.command == "generate"
    assert intelligence.creative_progress.required_checkpoint is not None
    assert intelligence.workflow_modified is False
    assert platform.automatic_action_taken is False
    assert creative.automatic_action_taken is False
    assert knowledge.automatic_action_taken is False
    assert workflow.automatic_action_taken is False
    assert context.state is PageState.PROMPT_BUILT


def test_v3_foundation_fastapi_and_mcp_delivery_are_dto_only() -> None:
    service, _ = _service()
    context = _context()
    application = ObservabilityApplication(
        health=lambda: None,  # type: ignore[arg-type]
        diagnostics=lambda: None,  # type: ignore[arg-type]
        repository_check=lambda: None,  # type: ignore[arg-type]
        director_platform=lambda: service.director_platform(context),
        creative_planning=lambda: service.creative_dashboard(context),
        knowledge_foundation=service.knowledge_dashboard,
        workflow_intelligence=lambda: service.workflow_dashboard(context),
        planning_foundation_summary=lambda: service.planning_summary(context),
    )
    registry = default_tool_registry(
        cast(MangaApplicationService, None),
        director_platform_provider=lambda: service.director_platform(context),
        creative_planning_provider=lambda: service.creative_dashboard(context),
        knowledge_foundation_provider=service.knowledge_dashboard,
        workflow_intelligence_provider=lambda: service.workflow_dashboard(context),
        planning_summary_provider=lambda: service.planning_summary(context),
    )

    assert application.director_platform_preview()["automatic_action_taken"] is False
    assert application.creative_planning_preview()["report"]["image_generation_invoked"] is False
    assert application.knowledge_foundation_preview()["report"]["persistence_mutated"] is False
    assert application.workflow_intelligence_preview()["report"]["workflow_modified"] is False
    assert application.planning_foundation_summary_preview()["execution_performed"] is False
    fastapi_app = create_observability_app(application)
    assert {route.path for route in fastapi_app.routes} >= {
        "/v3/director",
        "/v3/creative",
        "/v3/knowledge",
        "/v3/workflow",
        "/v3/summary",
    }
    assert registry.invoke("director_platform", {}).data["automatic_action_taken"] is False
    assert registry.invoke("creative_planning", {}).data["report"]["image_generation_invoked"] is False
    assert registry.invoke("knowledge_foundation", {}).data["report"]["persistence_mutated"] is False
    assert registry.invoke("workflow_intelligence", {}).data["report"]["workflow_modified"] is False
    assert registry.invoke("planning_foundation_summary", {}).data["execution_performed"] is False
