from __future__ import annotations

from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.domain.state_machine import PageState
from manga_director.production import PlanningService, ProviderOrchestrator, WorkflowPlanner
from manga_director.workflow import WorkflowContext


def _service() -> PlanningService:
    return PlanningService(
        planner=WorkflowPlanner(),
        providers=ProviderOrchestrator(LLMProviderRuntime()),
    )


def test_workflow_planner_uses_the_legal_next_state_without_mutating_context() -> None:
    context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)

    report = WorkflowPlanner().plan(context)

    assert report.plan.recommendation.command == "design"
    assert report.plan.recommendation.target_state is PageState.DESIGNED
    assert report.plan.execution_performed is False
    assert context.state is PageState.DRAFT


def test_dependency_graph_preserves_storyboard_and_human_approval_requirements() -> None:
    graph = WorkflowPlanner().dependency_graph(
        WorkflowContext(state=PageState.PROMPT_BUILT)
    )

    assert graph.steps[0].target_state is PageState.GENERATED
    assert graph.steps[0].requires_artifacts == (PageState.STORYBOARDED.value,)
    assert graph.steps[-1].target_state is PageState.APPROVED
    assert graph.steps[-1].human_decision_required is True


def test_provider_selection_is_capability_and_priority_advice_only() -> None:
    report = _service().provider_preview(("text", "deterministic"))

    assert report.selected_provider == "mock"
    assert report.selection_performed is False
    assert report.fallback.execution_enabled is False
    assert all(item.known is False for item in report.cost)


def test_model_router_reports_unavailable_capabilities_without_switching_providers() -> None:
    runtime = LLMProviderRuntime()
    before = runtime.discover()

    report = ProviderOrchestrator(runtime).select((" vision ", "vision"))

    assert report.selected_provider is None
    assert report.fallback.providers == ()
    assert report.fallback.execution_enabled is False
    assert report.selection_performed is False
    assert all(item.missing_capabilities == ("vision",) for item in report.scoring)
    assert runtime.discover() == before


def test_capability_matrix_contains_registered_provider_metadata() -> None:
    matrix = ProviderOrchestrator(LLMProviderRuntime()).matrix()

    assert "text" in matrix.capability_index
    assert "mock" in matrix.capability_index["text"]
    assert any(item.name == "mock" for item in matrix.providers)


def test_planning_summary_exposes_json_and_markdown_diagnostics() -> None:
    context = WorkflowContext(
        page={"id": "page-9"},
        state=PageState.PROMPT_BUILT,
        artifacts={PageState.STORYBOARDED.value: {"panels": []}},
    )

    summary = _service().summary(context, configuration={"profile": "testing"})

    assert summary.dependency_report.graph.current_state is PageState.PROMPT_BUILT
    assert summary.capability_report.matrix.providers
    assert '"execution_performed": false' in summary.to_json()
    assert "# Planning Summary" in summary.to_markdown()


def test_execution_preview_and_workflow_analysis_are_read_only() -> None:
    context = WorkflowContext(state=PageState.GENERATED, artifacts={})
    service = _service()

    preview = WorkflowPlanner().execution_preview(context)
    intelligence = service.workflow_intelligence(context)

    assert preview.preview_kind == "execution"
    assert intelligence.bottlenecks.severity == "low"
    assert "Persisted storyboard evidence" in intelligence.bottlenecks.bottlenecks[0]
    assert context.state is PageState.GENERATED
