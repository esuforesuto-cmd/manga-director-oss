"""Read-only workflow analytics, provider optimization, and enterprise diagnostics."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from manga_director._version import __version__
from manga_director.adapters.runtime import ImageBackendRuntime, LLMProviderRuntime
from manga_director.cli.config import AppConfig, configuration_governance
from manga_director.production.operations import BackendManagement
from manga_director.production.planning import (
    PlanningService,
    ProviderOrchestrator,
    ProviderSelectionReport,
    StepDependencyGraph,
    WorkflowBottleneckReport,
    WorkflowComplexityAnalysis,
)
from manga_director.production.quality import RepositoryMaintenance
from manga_director.workflow.contracts import WorkflowContext


class AnalyticsModel(BaseModel):
    """Immutable DTO base with portable JSON and Markdown renderers."""

    model_config = ConfigDict(frozen=True)

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def to_markdown(self) -> str:
        return _markdown(_title(self.__class__.__name__), self.model_dump(mode="json"))


class CriticalPathAnalysis(AnalyticsModel):
    """The remaining linear Page workflow path; analysis never schedules it."""

    states: tuple[str, ...] = ()
    commands: tuple[str, ...] = ()
    length: int = Field(ge=0)
    execution_enabled: bool = False


class WorkflowScore(AnalyticsModel):
    """A transparent bounded health score for one workflow context."""

    score: int = Field(ge=0, le=100)
    completed_steps: int = Field(ge=0)
    remaining_steps: int = Field(ge=0)
    rationale: tuple[str, ...] = ()


class WorkflowComparison(AnalyticsModel):
    """A comparison of two read-only workflow contexts."""

    current_state: str
    reference_state: str
    progress_delta_steps: int
    current_artifacts: int = Field(ge=0)
    reference_artifacts: int = Field(ge=0)
    messages: tuple[str, ...] = ()


class WorkflowAnalysisReport(AnalyticsModel):
    """Dependency, complexity, bottleneck, critical-path, and score evidence."""

    dependency_graph: StepDependencyGraph
    complexity: WorkflowComplexityAnalysis
    bottlenecks: WorkflowBottleneckReport
    critical_path: CriticalPathAnalysis
    score: WorkflowScore
    comparison: WorkflowComparison | None = None
    analysis_only: bool = True


class ProviderComparison(AnalyticsModel):
    """Registered Provider metadata compared without a Provider request."""

    provider: str
    capability_score: float = Field(ge=0)
    capabilities: tuple[str, ...] = ()
    relative_latency_milliseconds: float = Field(ge=0)
    estimated_cost: float | None = None
    cost_known: bool = False
    locally_healthy: bool
    reliability: Literal["local_healthy", "local_unavailable"]


class SelectionExplanation(AnalyticsModel):
    """Explain a recommendation with metadata-only and non-executing evidence."""

    selected_provider: str | None = None
    strategy: str
    explanation: str
    fallback_execution_enabled: bool = False


class ProviderOptimizationReport(AnalyticsModel):
    """Capability, cost, latency, reliability, and recommendation comparison."""

    selection: ProviderSelectionReport
    comparisons: tuple[ProviderComparison, ...] = ()
    explanation: SelectionExplanation
    optimization_performed: bool = False


class BoundaryAudit(AnalyticsModel):
    """A safe audit result for an application or infrastructure boundary."""

    name: str
    healthy: bool
    findings: dict[str, Any] = Field(default_factory=dict)
    messages: tuple[str, ...] = ()


class SystemOverview(AnalyticsModel):
    """Local system facts that do not expose delivery or secret internals."""

    package_version: str
    mode: Literal["local"] = "local"
    one_page_workflow: bool = True
    network_probes: bool = False


class EnterpriseSummary(AnalyticsModel):
    """Executive health summary for enterprise-oriented review."""

    healthy: bool
    workflow_score: int = Field(ge=0, le=100)
    provider_recommended: str | None = None
    repository_healthy: bool
    optimization_actions: tuple[str, ...] = ()


class EnterpriseDiagnosticsReport(AnalyticsModel):
    """Presentation-independent enterprise diagnostics composed from safe DTOs."""

    system: SystemOverview
    configuration: BoundaryAudit
    workflow: BoundaryAudit
    provider: BoundaryAudit
    backend: BoundaryAudit
    repository: BoundaryAudit
    executive: EnterpriseSummary


class Trend(AnalyticsModel):
    """A supplied or local metric series; it never creates background collection."""

    name: str
    values: tuple[float, ...] = ()
    direction: Literal["up", "down", "stable"]
    latest: float = 0.0


class AnalyticsSummary(AnalyticsModel):
    """Workflow, repository, Provider, performance, and operations trends."""

    workflow: Trend
    repository: Trend
    provider: Trend
    performance: Trend
    operations: Trend
    analysis_only: bool = True


class WorkflowExecutiveReport(AnalyticsModel):
    """Compact workflow-only executive view."""

    state: str
    score: WorkflowScore
    critical_path: CriticalPathAnalysis
    bottlenecks: WorkflowBottleneckReport


class ProviderExecutiveReport(AnalyticsModel):
    """Compact Provider-only executive view."""

    selected_provider: str | None = None
    healthy_providers: int = Field(ge=0)
    recommendation: SelectionExplanation


class OperationsExecutiveReport(AnalyticsModel):
    """Compact operations view that uses existing Repository evidence."""

    repository_healthy: bool
    projects: int = Field(ge=0)
    pages: int = Field(ge=0)
    trend: Trend


class OptimizationSummary(AnalyticsModel):
    """Advisory findings only; no automatic action is ever attempted."""

    recommendations: tuple[str, ...] = ()
    automatic_action_taken: bool = False


class ExecutiveAnalyticsReport(AnalyticsModel):
    """Composite executive DTO for CLI, FastAPI, and MCP delivery adapters."""

    workflow: WorkflowExecutiveReport
    provider: ProviderExecutiveReport
    operations: OperationsExecutiveReport
    enterprise: EnterpriseSummary
    optimization: OptimizationSummary


class WorkflowDependencyAnalyzer:
    """Analyze the existing StateMachine-derived plan without controlling the Engine."""

    def __init__(self, planning: PlanningService) -> None:
        self._planning = planning

    def analyze(
        self, context: WorkflowContext, reference: WorkflowContext | None = None
    ) -> WorkflowAnalysisReport:
        plan = self._planning.summary(context)
        graph = plan.dependency_report.graph
        path_states = (context.state.value, *(item.target_state.value for item in graph.steps))
        critical_path = CriticalPathAnalysis(
            states=path_states,
            commands=tuple(item.command for item in graph.steps),
            length=len(graph.steps),
        )
        score = _workflow_score(graph, plan.intelligence.bottlenecks)
        comparison = _workflow_comparison(context, reference) if reference is not None else None
        return WorkflowAnalysisReport(
            dependency_graph=graph,
            complexity=plan.workflow.complexity,
            bottlenecks=plan.intelligence.bottlenecks,
            critical_path=critical_path,
            score=score,
            comparison=comparison,
        )

    def intelligence(self, context: WorkflowContext) -> WorkflowBottleneckReport:
        """Return existing read-only bottleneck evidence without exposing planner internals."""

        return self._planning.workflow_intelligence(context).bottlenecks

    def recommendations(self, context: WorkflowContext) -> tuple[str, ...]:
        """Return advisory workflow recommendations without taking an action."""

        return tuple(
            item.message for item in self._planning.workflow_intelligence(context).recommendations
        )


class ProviderOptimizer:
    """Compare existing Provider metadata and local construction evidence only."""

    def __init__(self, runtime: LLMProviderRuntime, orchestrator: ProviderOrchestrator) -> None:
        self._runtime = runtime
        self._orchestrator = orchestrator

    def compare(self, required_capabilities: Sequence[str] = ()) -> ProviderOptimizationReport:
        selection = self._orchestrator.select(required_capabilities)
        health = {item.name: item.healthy for item in self._runtime.health()}
        latency = {item.provider: item.relative_milliseconds for item in selection.latency}
        scores = {item.provider: item.score for item in selection.scoring}
        comparisons = tuple(
            ProviderComparison(
                provider=item.name,
                capability_score=scores.get(item.name, 0.0),
                capabilities=item.capabilities,
                relative_latency_milliseconds=latency.get(item.name, 0.0),
                locally_healthy=health.get(item.name, False),
                reliability="local_healthy" if health.get(item.name, False) else "local_unavailable",
            )
            for item in selection.matrix.providers
        )
        selected = selection.selected_provider
        explanation = SelectionExplanation(
            selected_provider=selected,
            strategy=selection.strategy,
            explanation=(
                "No compatible locally registered Provider was found."
                if selected is None
                else "Selected by requested capability coverage and stable registry priority; no Provider was invoked."
            ),
        )
        return ProviderOptimizationReport(
            selection=selection,
            comparisons=comparisons,
            explanation=explanation,
        )


class EnterpriseDiagnostics:
    """Compose audits from existing application ports without presentation dependencies."""

    def __init__(
        self,
        *,
        configuration: AppConfig,
        workflow: WorkflowDependencyAnalyzer,
        providers: ProviderOptimizer,
        backends: ImageBackendRuntime,
        repository: RepositoryMaintenance,
    ) -> None:
        self._configuration = configuration
        self._workflow = workflow
        self._providers = providers
        self._backends = backends
        self._repository = repository

    def report(self, context: WorkflowContext) -> EnterpriseDiagnosticsReport:
        workflow = self._workflow.analyze(context)
        providers = self._providers.compare()
        backend_inventory = BackendManagement(self._backends).inventory()
        repository = self._repository.report()
        governance = configuration_governance(self._configuration)
        configuration_audit = BoundaryAudit(
            name="configuration",
            healthy=governance.compatible and governance.integrity_valid,
            findings=governance.model_dump(mode="json"),
        )
        workflow_audit = BoundaryAudit(
            name="workflow",
            healthy=workflow.bottlenecks.severity != "medium",
            findings={"state": context.state.value, "score": workflow.score.score},
            messages=workflow.bottlenecks.bottlenecks,
        )
        provider_audit = BoundaryAudit(
            name="provider",
            healthy=any(item.locally_healthy for item in providers.comparisons),
            findings={"selected": providers.selection.selected_provider, "providers": len(providers.comparisons)},
            messages=(providers.explanation.explanation,),
        )
        backend_audit = BoundaryAudit(
            name="backend",
            healthy=all(bool(item["healthy"]) for item in backend_inventory.backends),
            findings={"backends": len(backend_inventory.backends)},
        )
        repository_audit = BoundaryAudit(
            name="repository",
            healthy=repository.healthy,
            findings={
                "projects": repository.statistics.projects,
                "pages": repository.statistics.pages,
                "integrity": repository.consistency.healthy,
            },
        )
        recommendations = self._workflow.recommendations(context)
        executive = EnterpriseSummary(
            healthy=all(
                item.healthy
                for item in (configuration_audit, workflow_audit, provider_audit, backend_audit, repository_audit)
            ),
            workflow_score=workflow.score.score,
            provider_recommended=providers.selection.selected_provider,
            repository_healthy=repository.healthy,
            optimization_actions=recommendations,
        )
        return EnterpriseDiagnosticsReport(
            system=SystemOverview(package_version=__version__),
            configuration=configuration_audit,
            workflow=workflow_audit,
            provider=provider_audit,
            backend=backend_audit,
            repository=repository_audit,
            executive=executive,
        )


class OperationalAnalytics:
    """Derive bounded trends from supplied observations; no collector is started."""

    def summary(
        self,
        workflow: WorkflowAnalysisReport,
        providers: ProviderOptimizationReport,
        repository: RepositoryMaintenance,
        *,
        history: Mapping[str, Sequence[float]] | None = None,
    ) -> AnalyticsSummary:
        report = repository.report()
        values = history or {}
        return AnalyticsSummary(
            workflow=_trend("workflow", values.get("workflow", (float(workflow.score.score),))),
            repository=_trend("repository", values.get("repository", (float(report.statistics.pages),))),
            provider=_trend("provider", values.get("provider", (float(len(providers.comparisons)),))),
            performance=_trend("performance", values.get("performance", (0.0,))),
            operations=_trend("operations", values.get("operations", (1.0 if report.healthy else 0.0,))),
        )


class AnalyticsService:
    """Application facade for analysis, diagnostics, trends, and executive reports."""

    def __init__(
        self,
        *,
        workflow: WorkflowDependencyAnalyzer,
        providers: ProviderOptimizer,
        enterprise: EnterpriseDiagnostics,
        operations: OperationalAnalytics,
        repository: RepositoryMaintenance,
    ) -> None:
        self._workflow = workflow
        self._providers = providers
        self._enterprise = enterprise
        self._operations = operations
        self._repository = repository

    def workflow_analysis(self, context: WorkflowContext) -> WorkflowAnalysisReport:
        return self._workflow.analyze(context)

    def provider_comparison(self, required_capabilities: Sequence[str] = ()) -> ProviderOptimizationReport:
        return self._providers.compare(required_capabilities)

    def enterprise_diagnostics(self, context: WorkflowContext) -> EnterpriseDiagnosticsReport:
        return self._enterprise.report(context)

    def operational_analytics(self, context: WorkflowContext) -> AnalyticsSummary:
        return self._operations.summary(
            self.workflow_analysis(context), self.provider_comparison(), self._repository
        )

    def executive_report(self, context: WorkflowContext) -> ExecutiveAnalyticsReport:
        workflow = self.workflow_analysis(context)
        providers = self.provider_comparison()
        operations = self.operational_analytics(context)
        enterprise = self.enterprise_diagnostics(context).executive
        optimization = OptimizationSummary(
            recommendations=self._workflow.recommendations(context)
        )
        return ExecutiveAnalyticsReport(
            workflow=WorkflowExecutiveReport(
                state=context.state.value,
                score=workflow.score,
                critical_path=workflow.critical_path,
                bottlenecks=workflow.bottlenecks,
            ),
            provider=ProviderExecutiveReport(
                selected_provider=providers.selection.selected_provider,
                healthy_providers=sum(item.locally_healthy for item in providers.comparisons),
                recommendation=providers.explanation,
            ),
            operations=OperationsExecutiveReport(
                repository_healthy=self._repository.report().healthy,
                projects=self._repository.statistics().projects,
                pages=self._repository.statistics().pages,
                trend=operations.operations,
            ),
            enterprise=enterprise,
            optimization=optimization,
        )


def _workflow_score(graph: StepDependencyGraph, bottlenecks: WorkflowBottleneckReport) -> WorkflowScore:
    total_steps = 7
    remaining = len(graph.steps)
    completed = total_steps - remaining
    penalty = 10 * len(bottlenecks.bottlenecks)
    score = max(0, min(100, round((completed / total_steps) * 100) - penalty))
    return WorkflowScore(
        score=score,
        completed_steps=completed,
        remaining_steps=remaining,
        rationale=("Progress is derived from remaining StateMachine transitions.", "Bottlenecks reduce the advisory score by ten points each."),
    )


def _workflow_comparison(current: WorkflowContext, reference: WorkflowContext) -> WorkflowComparison:
    states = ("Draft", "Designed", "Reviewed", "Storyboarded", "PromptBuilt", "Generated", "QualityChecked", "Approved")
    current_index = states.index(current.state.value)
    reference_index = states.index(reference.state.value)
    return WorkflowComparison(
        current_state=current.state.value,
        reference_state=reference.state.value,
        progress_delta_steps=current_index - reference_index,
        current_artifacts=len(current.artifacts),
        reference_artifacts=len(reference.artifacts),
        messages=("Comparison is advisory and does not merge or alter either context.",),
    )


def _trend(name: str, observations: Sequence[float]) -> Trend:
    values = tuple(float(item) for item in observations)
    latest = values[-1] if values else 0.0
    direction: Literal["up", "down", "stable"] = "stable"
    if len(values) >= 2 and values[-1] > values[0]:
        direction = "up"
    elif len(values) >= 2 and values[-1] < values[0]:
        direction = "down"
    return Trend(name=name, values=values, direction=direction, latest=latest)


def _title(name: str) -> str:
    parts: list[str] = []
    current = ""
    for character in name:
        if character.isupper() and current:
            parts.append(current)
            current = character
        else:
            current += character
    if current:
        parts.append(current)
    return " ".join(parts)


def _markdown(title: str, values: dict[str, Any]) -> str:
    lines = [f"# {title}", ""]
    for key, value in values.items():
        lines.extend([f"## {key.replace('_', ' ').title()}", "", "```json"])
        lines.append(json.dumps(value, indent=2, default=str))
        lines.extend(["```", ""])
    return "\n".join(lines)
