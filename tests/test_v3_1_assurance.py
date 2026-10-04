"""Contracts for v3.1 governance, reliability, readiness, and release-quality DTOs."""

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
    V31AssuranceService,
    V31FoundationService,
    V31InsightsService,
    WorkflowPlanner,
)
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext


def _service() -> tuple[V31AssuranceService, InMemoryRepository]:
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
    insights = V31InsightsService(foundation, repository)
    return V31AssuranceService(foundation, insights, repository), repository


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "pilot-1"},
        state=PageState.PROMPT_BUILT,
        artifacts={"storyboard": {"panels": []}},
        metadata={"workflow_history": [{"step": "prompt", "to": "PromptBuilt"}]},
    )


def test_creative_governance_is_diagnostic_and_never_approves_or_remediates() -> None:
    service, _ = _service()
    context = _context()

    report = service.creative_governance(context)

    assert report.diagnostic_only is True
    assert report.summary.policy.policy_applied is False
    assert report.summary.validation.workflow_changed is False
    assert report.summary.compliance.remediation_applied is False
    assert report.summary.quality.quality_passed is False
    assert report.approval_granted is False
    assert context.state is PageState.PROMPT_BUILT


def test_knowledge_reliability_is_redacted_and_repository_read_only() -> None:
    service, repository = _service()

    report = service.knowledge_reliability()
    rendered = report.to_json()

    assert report.summary.integrity.values_redacted is True
    assert report.summary.consistency.values_exposed is False
    assert report.summary.consistency.persistence_mutated is False
    assert report.summary.dependencies.external_lookup_started is False
    assert report.persistence_mutated is False
    assert "not exposed" not in rendered
    assert repository.load("pilot").metadata["world"] == "not exposed"


def test_operational_readiness_never_deploys_or_changes_configuration() -> None:
    service, _ = _service()
    context = _context()

    report = service.operational_readiness(context, {"database_url": "not exposed"})

    assert report.operational.operation_started is False
    assert report.deployment.deployment_performed is False
    assert report.deployment.deployment_authorized is False
    assert report.configuration.values_exposed is False
    assert report.configuration.configuration_changed is False
    assert report.environment.external_probe_started is False
    assert report.release_authorized is False
    assert context.state is PageState.PROMPT_BUILT


def test_release_quality_is_diagnostic_and_requires_human_release_review() -> None:
    service, _ = _service()
    context = _context()

    report = service.release_quality(context, {"mode": "testing"})

    assert report.quality.release_published is False
    assert report.compatibility.compatible is True
    assert report.compatibility.breaking_change_applied is False
    assert report.gates.gate_enforced is False
    assert report.regression.comparison_executed is False
    assert report.production.production_action_started is False
    assert report.recommendation.release_authorized is False
    assert context.state is PageState.PROMPT_BUILT


def test_compatibility_validation_is_stable_and_non_mutating() -> None:
    service, _ = _service()
    context = _context()

    report = service.release_quality(context).compatibility

    assert "workflow" in report.checked_surfaces
    assert "repository" in report.checked_surfaces
    assert report.compatible is True
    assert report.breaking_change_applied is False


def test_v3_1_assurance_dashboards_are_safe_for_fastapi_and_mcp() -> None:
    service, _ = _service()
    context = _context()
    application = ObservabilityApplication(
        health=lambda: None,  # type: ignore[arg-type]
        diagnostics=lambda: None,  # type: ignore[arg-type]
        repository_check=lambda: None,  # type: ignore[arg-type]
        creative_governance_v31=lambda: service.creative_governance_dashboard(context),
        knowledge_reliability=service.knowledge_reliability_dashboard,
        operational_readiness_v31=lambda: service.operational_readiness_dashboard(
            context, {"mode": "testing"}
        ),
        release_quality=lambda: service.release_quality_dashboard(context, {"mode": "testing"}),
        compatibility_validation=lambda: service.release_quality_dashboard(
            context, {"mode": "testing"}
        ).report.compatibility,
    )
    registry = default_tool_registry(
        cast(MangaApplicationService, None),
        creative_governance_v31_provider=lambda: service.creative_governance_dashboard(context),
        knowledge_reliability_provider=service.knowledge_reliability_dashboard,
        operational_readiness_v31_provider=lambda: service.operational_readiness_dashboard(
            context, {"mode": "testing"}
        ),
        release_quality_provider=lambda: service.release_quality_dashboard(
            context, {"mode": "testing"}
        ),
        compatibility_validation_provider=lambda: service.release_quality_dashboard(
            context, {"mode": "testing"}
        ).report.compatibility,
    )

    assert application.creative_governance_v31_preview()["report"]["approval_granted"] is False
    assert application.knowledge_reliability_preview()["report"]["persistence_mutated"] is False
    assert application.operational_readiness_v31_preview()["deployment_performed"] is False
    assert application.release_quality_preview()["release_authorized"] is False
    assert application.compatibility_validation_preview()["breaking_change_applied"] is False
    routes = {route.path for route in create_observability_app(application).routes}
    assert {
        "/v3.1/creative-governance",
        "/v3.1/knowledge-reliability",
        "/v3.1/operational-readiness",
        "/v3.1/release-quality",
        "/v3.1/compatibility-validation",
    } <= routes
    assert registry.invoke("creative_governance_v31", {}).data["report"]["approval_granted"] is False
    assert registry.invoke("knowledge_reliability", {}).data["report"]["persistence_mutated"] is False
    assert registry.invoke("operational_readiness_v31", {}).data["deployment_performed"] is False
    assert registry.invoke("release_quality", {}).data["release_authorized"] is False
    assert registry.invoke("compatibility_validation", {}).data["breaking_change_applied"] is False
