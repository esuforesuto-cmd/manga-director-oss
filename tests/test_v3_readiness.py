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
    V3ReadinessService,
    WorkflowPlanner,
)
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext


def _service() -> tuple[V3ReadinessService, InMemoryRepository]:
    repository = InMemoryRepository()
    repository.save(
        Project(
            id="pilot",
            title="Pilot",
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
    return V3ReadinessService(foundation, CollaborationPlanningService(foundation)), repository


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


def test_director_reliability_validates_one_page_planning_without_execution() -> None:
    service, _ = _service()
    context = _context()

    report = service.director_reliability(context)

    assert report.session.valid is True
    assert report.planning.state_machine_derived is True
    assert report.consistency.consistent is True
    assert report.creative_strategy.strategy_executed is False
    assert report.readiness.execution_enabled is False
    assert report.automatic_action_taken is False
    assert context.state is PageState.PROMPT_BUILT


def test_creative_governance_remains_audit_only_and_preserves_review_stages() -> None:
    service, _ = _service()
    context = _context()

    report = service.creative_governance(context)

    assert report.summary.policy.valid is True
    assert report.summary.standards.compliant is True
    assert report.compliance.workflow_changed is False
    assert report.audit.audit_only is True
    assert report.audit.persistence_mutated is False
    assert context.state is PageState.PROMPT_BUILT


def test_knowledge_integrity_is_repository_read_only_and_never_exposes_values() -> None:
    service, repository = _service()

    report = service.knowledge_integrity(_context())
    rendered = report.to_json()

    assert report.governance.integrity.valid is True
    assert report.governance.lifecycle.persistence_mutated is False
    assert report.governance.quality.score == 100
    assert report.risk.automatic_remediation is False
    assert "not exposed" not in rendered
    assert repository.load("pilot").metadata["world"] == "not exposed"


def test_production_and_release_readiness_are_checklists_not_deployments() -> None:
    service, _ = _service()
    context = _context()

    readiness = service.production_readiness(context, {"profile": "testing"})
    release = service.release_dashboard(context, {"profile": "testing"})

    assert readiness.workflow.deployment_performed is False
    assert readiness.configuration.values_exposed is False
    assert readiness.operations.operation_started is False
    assert release.production.deployment_performed is False
    assert release.release_authorized is False
    assert release.automatic_release is False
    assert context.state is PageState.PROMPT_BUILT


def test_v3_readiness_delivery_callbacks_and_mcp_tools_return_safe_dtos() -> None:
    service, _ = _service()
    context = _context()
    application = ObservabilityApplication(
        health=lambda: None,  # type: ignore[arg-type]
        diagnostics=lambda: None,  # type: ignore[arg-type]
        repository_check=lambda: None,  # type: ignore[arg-type]
        director_reliability_v3=lambda: service.director_executive(context),
        creative_governance=lambda: service.creative_executive(context),
        knowledge_integrity=lambda: service.knowledge_executive(context),
        production_readiness=lambda: service.production_executive(context, {"profile": "testing"}),
        release_readiness=lambda: service.release_dashboard(context, {"profile": "testing"}),
    )
    registry = default_tool_registry(
        cast(MangaApplicationService, None),
        director_reliability_v3_provider=lambda: service.director_executive(context),
        creative_governance_provider=lambda: service.creative_executive(context),
        knowledge_integrity_provider=lambda: service.knowledge_executive(context),
        production_readiness_provider=lambda: service.production_executive(context),
        release_readiness_provider=lambda: service.release_dashboard(context),
    )

    assert application.director_reliability_v3_preview()["automatic_action_taken"] is False
    assert application.creative_governance_preview()["automatic_action_taken"] is False
    assert application.knowledge_integrity_preview()["report"]["persistence_mutated"] is False
    assert application.production_readiness_preview()["deployment_performed"] is False
    assert application.release_readiness_preview()["automatic_release"] is False
    routes = {route.path for route in create_observability_app(application).routes}
    assert {"/v3/reliability", "/v3/governance", "/v3/knowledge-integrity", "/v3/production-readiness", "/v3/release-readiness"} <= routes
    assert registry.invoke("director_reliability_v3", {}).data["automatic_action_taken"] is False
    assert registry.invoke("creative_governance", {}).data["automatic_action_taken"] is False
    assert registry.invoke("knowledge_integrity", {}).data["report"]["persistence_mutated"] is False
    assert registry.invoke("production_readiness", {}).data["deployment_performed"] is False
    assert registry.invoke("release_readiness", {}).data["automatic_release"] is False
