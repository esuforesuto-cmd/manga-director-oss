"""Read-only workflow planning and provider-orchestration application DTOs.

The services in this module advise delivery layers. They never call an Agent or
provider, mutate a workflow context, schedule work, or bypass the StateMachine.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.adapters.runtime_models import AdapterMetadata
from manga_director.domain.state_machine import PageState, StateMachine
from manga_director.workflow.contracts import WorkflowContext

_TRANSITIONS: tuple[tuple[PageState, PageState, str], ...] = (
    (PageState.DRAFT, PageState.DESIGNED, "design"),
    (PageState.DESIGNED, PageState.REVIEWED, "review"),
    (PageState.REVIEWED, PageState.STORYBOARDED, "storyboard"),
    (PageState.STORYBOARDED, PageState.PROMPT_BUILT, "prompt"),
    (PageState.PROMPT_BUILT, PageState.GENERATED, "generate"),
    (PageState.GENERATED, PageState.QUALITY_CHECKED, "quality"),
    (PageState.QUALITY_CHECKED, PageState.APPROVED, "approve"),
)


class PlanningModel(BaseModel):
    """Immutable JSON/Markdown DTO base for planning delivery adapters."""

    model_config = ConfigDict(frozen=True)

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def to_markdown(self) -> str:
        return _markdown(_title(self.__class__.__name__), self.model_dump(mode="json"))


class StepDependency(PlanningModel):
    """A single workflow step and its required predecessor evidence."""

    command: str
    target_state: PageState
    requires_states: tuple[PageState, ...] = ()
    requires_artifacts: tuple[str, ...] = ()
    human_decision_required: bool = False


class StepDependencyGraph(PlanningModel):
    """Static one-page dependency graph derived from the StateMachine contract."""

    current_state: PageState
    steps: tuple[StepDependency, ...] = ()
    mutates_workflow: bool = False


class WorkflowComplexityAnalysis(PlanningModel):
    """Bounded complexity observation; it is not an execution estimate guarantee."""

    remaining_steps: int = Field(ge=0)
    artifact_count: int = Field(ge=0)
    history_entries: int = Field(ge=0)
    complexity: Literal["low", "medium", "high"]
    rationale: tuple[str, ...] = ()


class EstimatedExecutionReport(PlanningModel):
    """Static estimate based only on known remaining legal steps."""

    estimated_steps: int = Field(ge=0)
    estimated_seconds: float = Field(ge=0)
    confidence: Literal["low"] = "low"
    assumptions: tuple[str, ...] = ()


class WorkflowRecommendation(PlanningModel):
    """A recommended legal next action that cannot perform that action."""

    command: str | None = None
    target_state: PageState | None = None
    actionable: bool
    reason: str
    human_approval_required: bool = False


class ExecutionPlan(PlanningModel):
    """Reviewable one-page execution plan; execution is always disabled."""

    page_reference: str
    current_state: PageState
    recommendation: WorkflowRecommendation
    dependency_graph: StepDependencyGraph
    estimated_execution: EstimatedExecutionReport
    execution_performed: bool = False
    messages: tuple[str, ...] = ("Plan only; no workflow step was executed.",)


class WorkflowPlanningReport(PlanningModel):
    """Complete planning DTO for one existing WorkflowContext."""

    plan: ExecutionPlan
    complexity: WorkflowComplexityAnalysis
    preview_kind: Literal["workflow", "execution"] = "workflow"


class WorkflowSummary(PlanningModel):
    """Summary and observed timeline for one workflow context."""

    current_state: PageState
    completed_states: tuple[PageState, ...] = ()
    timeline: tuple[str, ...] = ()
    terminal: bool


class ExecutionGraph(PlanningModel):
    """A delivery-neutral representation of legal remaining transitions."""

    nodes: tuple[str, ...] = ()
    edges: tuple[tuple[str, str], ...] = ()


class WorkflowBottleneckReport(PlanningModel):
    """Diagnostic-only bottleneck observations based on local context evidence."""

    bottlenecks: tuple[str, ...] = ()
    severity: Literal["none", "low", "medium"]


class WorkflowOptimizationRecommendation(PlanningModel):
    """Non-executing workflow recommendation with no Engine control."""

    priority: Literal["low", "medium"]
    message: str


class WorkflowIntelligenceReport(PlanningModel):
    """Workflow summary, timeline, execution graph, and diagnostic advice."""

    summary: WorkflowSummary
    execution_graph: ExecutionGraph
    bottlenecks: WorkflowBottleneckReport
    recommendations: tuple[WorkflowOptimizationRecommendation, ...] = ()


class ProviderCapability(PlanningModel):
    """Provider metadata projected into a selection-safe capability matrix."""

    name: str
    capabilities: tuple[str, ...] = ()
    models: tuple[str, ...] = ()
    priority: int = Field(ge=0)


class ProviderCapabilityMatrix(PlanningModel):
    """Registered provider capabilities without constructing or invoking providers."""

    providers: tuple[ProviderCapability, ...] = ()
    capability_index: dict[str, tuple[str, ...]] = Field(default_factory=dict)


class CapabilityReport(PlanningModel):
    """A named planning diagnostic for the provider capability matrix."""

    matrix: ProviderCapabilityMatrix


class DependencyReport(PlanningModel):
    """A named planning diagnostic for the remaining step dependencies."""

    graph: StepDependencyGraph


class CapabilityScoring(PlanningModel):
    """Deterministic metadata score for a provider recommendation."""

    provider: str
    requested_capabilities: tuple[str, ...] = ()
    matched_capabilities: tuple[str, ...] = ()
    missing_capabilities: tuple[str, ...] = ()
    score: float = Field(ge=0)


class LatencyEstimate(PlanningModel):
    """Relative estimate derived only from priority metadata, not live timing."""

    provider: str
    relative_milliseconds: float = Field(ge=0)
    confidence: Literal["low"] = "low"
    source: str = "priority metadata; no network probe"


class CostEstimate(PlanningModel):
    """Explicitly unknown cost estimate until a provider price source is approved."""

    provider: str
    estimated_currency_units: float | None = None
    known: bool = False
    source: str = "no provider pricing source configured"


class FallbackRecommendation(PlanningModel):
    """A declaration of candidates; it never performs fallback execution."""

    providers: tuple[str, ...] = ()
    execution_enabled: bool = False
    reason: str


class ProviderSelectionReport(PlanningModel):
    """Explainable Provider selection planning DTO with no provider invocation."""

    strategy: Literal["capability_then_priority"] = "capability_then_priority"
    matrix: ProviderCapabilityMatrix
    scoring: tuple[CapabilityScoring, ...] = ()
    latency: tuple[LatencyEstimate, ...] = ()
    cost: tuple[CostEstimate, ...] = ()
    selected_provider: str | None = None
    fallback: FallbackRecommendation
    selection_performed: bool = False


class PlanningSummary(PlanningModel):
    """Composite planning diagnostics and developer previews."""

    workflow: WorkflowPlanningReport
    intelligence: WorkflowIntelligenceReport
    providers: ProviderSelectionReport
    capability_report: CapabilityReport
    dependency_report: DependencyReport
    configuration_preview: dict[str, Any] = Field(default_factory=dict)
    architecture_preview: dict[str, Any] = Field(default_factory=dict)
    execution_performed: bool = False


class WorkflowPlanner:
    """Read-only planner that delegates legal-step knowledge to StateMachine."""

    def __init__(self, state_machine: StateMachine | None = None) -> None:
        self._state_machine = state_machine or StateMachine()

    def dependency_graph(self, context: WorkflowContext) -> StepDependencyGraph:
        current_index = _state_index(context.state)
        steps = tuple(
            StepDependency(
                command=command,
                target_state=target,
                requires_states=(source,),
                requires_artifacts=_required_artifacts(target),
                human_decision_required=target is PageState.APPROVED,
            )
            for source, target, command in _TRANSITIONS[current_index:]
        )
        return StepDependencyGraph(current_state=context.state, steps=steps)

    def complexity(self, context: WorkflowContext) -> WorkflowComplexityAnalysis:
        remaining = len(self.dependency_graph(context).steps)
        artifacts = len(context.artifacts)
        history = context.metadata.get("workflow_history", [])
        history_count = len(history) if isinstance(history, list) else 0
        score = remaining + artifacts + history_count
        complexity: Literal["low", "medium", "high"] = "high" if score >= 10 else "medium" if score >= 5 else "low"
        return WorkflowComplexityAnalysis(
            remaining_steps=remaining,
            artifact_count=artifacts,
            history_entries=history_count,
            complexity=complexity,
            rationale=("Derived from remaining legal steps, artifacts, and bounded workflow history.",),
        )

    def recommendation(self, context: WorkflowContext) -> WorkflowRecommendation:
        try:
            target = self._state_machine.next_state(context.state)
            command = self._state_machine.next_command(context.state)
        except Exception:
            return WorkflowRecommendation(
                actionable=False,
                reason="The page is terminal; no additional workflow command is legal.",
            )
        return WorkflowRecommendation(
            command=command,
            target_state=target,
            actionable=True,
            reason="The recommendation is the single successor accepted by StateMachine.",
            human_approval_required=target is PageState.APPROVED,
        )

    def plan(self, context: WorkflowContext) -> WorkflowPlanningReport:
        graph = self.dependency_graph(context)
        recommendation = self.recommendation(context)
        estimate = EstimatedExecutionReport(
            estimated_steps=len(graph.steps),
            estimated_seconds=float(len(graph.steps)),
            assumptions=("One relative planning unit per remaining legal step.", "No Agent or provider execution was measured."),
        )
        reference = str(context.page.get("id", context.page.get("page_number", "one-page-context")))
        return WorkflowPlanningReport(
            plan=ExecutionPlan(
                page_reference=reference,
                current_state=context.state,
                recommendation=recommendation,
                dependency_graph=graph,
                estimated_execution=estimate,
            ),
            complexity=self.complexity(context),
        )

    def execution_preview(self, context: WorkflowContext) -> WorkflowPlanningReport:
        """Return the same non-executing plan, explicitly labelled as a preview."""

        return self.plan(context).model_copy(update={"preview_kind": "execution"})


class ProviderOrchestrator:
    """Metadata-only Provider recommendations over the unchanged runtime protocol."""

    def __init__(self, runtime: LLMProviderRuntime) -> None:
        self._runtime = runtime

    def matrix(self) -> ProviderCapabilityMatrix:
        providers = tuple(
            ProviderCapability(
                name=item.name,
                capabilities=item.capabilities,
                models=item.models,
                priority=item.priority,
            )
            for item in self._runtime.discover()
        )
        index: dict[str, tuple[str, ...]] = {}
        for capability, names in self._runtime.capability_report().items():
            index[capability] = tuple(names)
        return ProviderCapabilityMatrix(providers=providers, capability_index=index)

    def select(self, required_capabilities: Sequence[str] = ()) -> ProviderSelectionReport:
        requested = tuple(sorted({item.strip() for item in required_capabilities if item.strip()}))
        metadata = tuple(self._runtime.discover())
        scoring = tuple(_score(metadata_item, requested) for metadata_item in metadata)
        ordered = tuple(sorted(scoring, key=lambda item: (-item.score, _priority(metadata, item.provider), item.provider)))
        selected = next((item.provider for item in ordered if not item.missing_capabilities), None)
        fallbacks = tuple(item.provider for item in ordered if item.provider != selected and not item.missing_capabilities)
        return ProviderSelectionReport(
            matrix=self.matrix(),
            scoring=ordered,
            latency=tuple(_latency(item) for item in metadata),
            cost=tuple(CostEstimate(provider=item.name) for item in metadata),
            selected_provider=selected,
            fallback=FallbackRecommendation(
                providers=fallbacks,
                reason="Candidates are ordered by capability coverage then registered priority; no fallback was executed.",
            ),
        )


class PlanningService:
    """Application facade for workflow intelligence, Provider advice, and previews."""

    def __init__(self, *, planner: WorkflowPlanner, providers: ProviderOrchestrator) -> None:
        self._planner = planner
        self._providers = providers

    def workflow_intelligence(self, context: WorkflowContext) -> WorkflowIntelligenceReport:
        plan = self._planner.plan(context)
        current_index = _state_index(context.state)
        completed = tuple(target for _, target, _ in _TRANSITIONS[:current_index])
        nodes = tuple(source.value for source, _, _ in _TRANSITIONS[current_index:])
        if current_index < len(_TRANSITIONS):
            nodes += (_TRANSITIONS[-1][1].value,)
        edges = tuple((nodes[index], nodes[index + 1]) for index in range(max(0, len(nodes) - 1)))
        bottlenecks: list[str] = []
        if (
            PageState.STORYBOARDED.value not in context.artifacts
            and _state_index(context.state) >= _state_index(PageState.PROMPT_BUILT)
        ):
            bottlenecks.append("Persisted storyboard evidence is required for generated-or-later work.")
        if plan.complexity.complexity == "high":
            bottlenecks.append("Context complexity is high; review artifacts and history before execution.")
        severity: Literal["none", "low", "medium"] = "medium" if len(bottlenecks) > 1 else "low" if bottlenecks else "none"
        recommendations = tuple(
            WorkflowOptimizationRecommendation(priority="medium", message=item) for item in bottlenecks
        ) or (
            WorkflowOptimizationRecommendation(
                priority="low", message="Execute only the StateMachine-recommended next step after human review.",
            ),
        )
        history = context.metadata.get("workflow_history", [])
        timeline = tuple(str(item.get("step", item.get("to", "workflow"))) for item in history if isinstance(item, Mapping)) if isinstance(history, list) else ()
        return WorkflowIntelligenceReport(
            summary=WorkflowSummary(
                current_state=context.state,
                completed_states=completed,
                timeline=timeline or (context.state.value,),
                terminal=context.state is PageState.APPROVED,
            ),
            execution_graph=ExecutionGraph(nodes=nodes, edges=edges),
            bottlenecks=WorkflowBottleneckReport(bottlenecks=tuple(bottlenecks), severity=severity),
            recommendations=recommendations,
        )

    def provider_preview(
        self, required_capabilities: Sequence[str] = ()
    ) -> ProviderSelectionReport:
        """Preview a Provider recommendation without constructing or invoking it."""

        return self._providers.select(required_capabilities)

    def configuration_preview(self, configuration: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """Return a safe shape-only configuration preview for developer tooling."""

        return {"configured": bool(configuration), "keys": tuple(sorted((configuration or {}).keys()))}

    @staticmethod
    def architecture_preview() -> dict[str, Any]:
        """Declare the fixed boundaries respected by all planning DTOs."""

        return {
            "core_modified": False,
            "workflow_engine_modified": False,
            "provider_invoked": False,
            "execution_scheduled": False,
            "scope": "one_page",
        }

    def summary(
        self,
        context: WorkflowContext,
        *,
        required_capabilities: Sequence[str] = (),
        configuration: Mapping[str, Any] | None = None,
    ) -> PlanningSummary:
        return PlanningSummary(
            workflow=self._planner.plan(context),
            intelligence=self.workflow_intelligence(context),
            providers=self._providers.select(required_capabilities),
            capability_report=CapabilityReport(matrix=self._providers.matrix()),
            dependency_report=DependencyReport(graph=self._planner.dependency_graph(context)),
            configuration_preview=self.configuration_preview(configuration),
            architecture_preview=self.architecture_preview(),
        )


def _state_index(state: PageState) -> int:
    for index, (candidate, _, _) in enumerate(_TRANSITIONS):
        if candidate is state:
            return index
    return len(_TRANSITIONS)


def _required_artifacts(target: PageState) -> tuple[str, ...]:
    if target is PageState.GENERATED:
        return (PageState.STORYBOARDED.value,)
    if target is PageState.APPROVED:
        return (PageState.QUALITY_CHECKED.value,)
    return ()


def _score(metadata: AdapterMetadata, requested: tuple[str, ...]) -> CapabilityScoring:
    available = set(metadata.capabilities)
    matched = tuple(item for item in requested if item in available)
    missing = tuple(item for item in requested if item not in available)
    coverage = len(matched) / len(requested) if requested else 1.0
    return CapabilityScoring(
        provider=metadata.name,
        requested_capabilities=requested,
        matched_capabilities=matched,
        missing_capabilities=missing,
        score=coverage * 100.0 + max(0, 100 - metadata.priority) / 1000.0,
    )


def _priority(metadata: Sequence[AdapterMetadata], provider: str) -> int:
    return next(item.priority for item in metadata if item.name == provider)


def _latency(metadata: AdapterMetadata) -> LatencyEstimate:
    return LatencyEstimate(provider=metadata.name, relative_milliseconds=float((metadata.priority + 1) * 10))


def _title(name: str) -> str:
    chunks: list[str] = []
    current = ""
    for character in name:
        if character.isupper() and current:
            chunks.append(current)
            current = character
        else:
            current += character
    if current:
        chunks.append(current)
    return " ".join(chunks)


def _markdown(title: str, values: dict[str, Any]) -> str:
    lines = [f"# {title}", ""]
    for key, value in values.items():
        lines.extend([f"## {key.replace('_', ' ').title()}", "", "```json"])
        lines.append(json.dumps(value, indent=2, default=str))
        lines.extend(["```", ""])
    return "\n".join(lines)
