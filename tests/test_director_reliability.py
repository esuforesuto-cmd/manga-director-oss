from __future__ import annotations

from typing import cast

from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.api import ObservabilityApplication
from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.mcp.application import MangaApplicationService
from manga_director.mcp.registry import default_tool_registry
from manga_director.production import (
    DirectorFoundationService,
    DirectorReliabilityService,
    KnowledgeIntelligenceService,
    KnowledgeService,
    PlanningService,
    ProviderOrchestrator,
    WorkflowPlanner,
)
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext


def _service() -> tuple[DirectorReliabilityService, InMemoryRepository]:
    repository = InMemoryRepository()
    repository.save(
        Project(
            id="alpha",
            title="Alpha",
            pages=[Page(page_number=1)],
            metadata={"world": "city"},
        )
    )
    foundation = DirectorFoundationService(
        PlanningService(
            planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime())
        ),
        KnowledgeService(repository),
    )
    return DirectorReliabilityService(foundation, KnowledgeIntelligenceService(foundation)), repository


def test_director_reliability_validates_one_legal_step_without_execution() -> None:
    service, _ = _service()
    context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)

    report = service.director_reliability(context)
    summary = service.director_summary(context)

    assert report.integrity.page_scope == "one_page"
    assert report.consistency.valid is True
    assert report.decision_trace.side_effects == "none"
    assert report.next_command == "design"
    assert report.execution_performed is False
    assert summary.reliable is True
    assert context.state is PageState.DRAFT


def test_knowledge_governance_is_repository_port_only_and_redacted() -> None:
    service, repository = _service()

    report = service.knowledge_governance()

    assert report.policy.valid is True
    assert report.lifecycle.persistence_mutated is False
    assert report.quality.score == 100
    assert report.governance_only is True
    assert repository.load("alpha").metadata["world"] == "city"


def test_enterprise_diagnostics_and_dashboard_are_dto_only() -> None:
    service, _ = _service()
    context = WorkflowContext(page={"id": "page-1"}, state=PageState.PROMPT_BUILT)

    readiness = service.enterprise_ai_readiness(context)
    diagnostics = service.diagnostics(context)
    dashboard = service.dashboard(context)

    assert readiness.deployment_performed is False
    assert diagnostics.diagnostics_only is True
    assert diagnostics.architecture["workflow_engine_modified"] is False
    assert dashboard.workflow.execution_performed is False
    assert dashboard.release.automatic_release is False
    assert '"automatic_release": false' in dashboard.to_json()
    assert "# DirectorExecutiveDashboard" in dashboard.to_markdown()
    assert context.state is PageState.PROMPT_BUILT


def test_director_reliability_delivery_callbacks_return_safe_dtos() -> None:
    service, _ = _service()
    context = WorkflowContext(page={"id": "page-1"})
    application = ObservabilityApplication(
        health=lambda: None,  # type: ignore[arg-type]
        diagnostics=lambda: None,  # type: ignore[arg-type]
        repository_check=lambda: None,  # type: ignore[arg-type]
        director_reliability=lambda: service.director_reliability(context),
        knowledge_governance=service.knowledge_governance,
        enterprise_ai_readiness=lambda: service.enterprise_ai_readiness(context),
        ai_workflow_diagnostics=lambda: service.diagnostics(context),
        director_dashboard=lambda: service.dashboard(context),
    )

    assert application.director_reliability_preview()["execution_performed"] is False
    assert application.knowledge_governance_preview()["governance_only"] is True
    assert application.enterprise_ai_readiness_preview()["deployment_performed"] is False
    assert application.ai_workflow_diagnostics_preview()["diagnostics_only"] is True
    assert application.director_dashboard_preview()["release"]["automatic_release"] is False


def test_mcp_director_reliability_tools_are_read_only_dto_adapters() -> None:
    service, _ = _service()
    context = WorkflowContext(page={"id": "page-1"})
    registry = default_tool_registry(
        cast(MangaApplicationService, None),
        director_reliability_provider=lambda: service.director_reliability(context),
        knowledge_governance_provider=service.knowledge_governance,
        enterprise_ai_readiness_provider=lambda: service.enterprise_ai_readiness(context),
        ai_workflow_diagnostics_provider=lambda: service.diagnostics(context),
        director_dashboard_provider=lambda: service.dashboard(context),
    )

    assert registry.invoke("director_reliability", {}).data["execution_performed"] is False
    assert registry.invoke("knowledge_governance", {}).data["governance_only"] is True
    assert registry.invoke("enterprise_ai_readiness", {}).data["deployment_performed"] is False
    assert registry.invoke("ai_workflow_diagnostics", {}).data["diagnostics_only"] is True
    assert registry.invoke("director_dashboard", {}).data["release"]["automatic_release"] is False
