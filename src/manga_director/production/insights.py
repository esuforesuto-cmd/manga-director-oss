"""Read-only observability, diagnostics, performance, and operations DTOs."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from manga_director._version import __version__
from manga_director.observability.metrics import MetricsRegistry
from manga_director.production.quality import RepositoryMaintenance, RepositoryMaintenanceReport
from manga_director.workflow.contracts import WorkflowContext


class TimelineEntry(BaseModel):
    """An immutable observation of a workflow or operation step."""

    model_config = ConfigDict(frozen=True)

    scope: Literal["workflow", "operation"]
    name: str
    state: str | None = None
    status: str = "observed"
    duration_seconds: float | None = Field(default=None, ge=0)
    details: dict[str, Any] = Field(default_factory=dict)


class WorkflowTimeline(BaseModel):
    """Read-only page workflow history rendered as timeline DTOs."""

    model_config = ConfigDict(frozen=True)

    current_state: str
    entries: tuple[TimelineEntry, ...] = ()


class OperationTimeline(BaseModel):
    """Read-only operational observations supplied by the application boundary."""

    model_config = ConfigDict(frozen=True)

    entries: tuple[TimelineEntry, ...] = ()


class PerformanceSnapshot(BaseModel):
    """Bounded counters and duration summaries from the in-process registry."""

    model_config = ConfigDict(frozen=True)

    counters: dict[str, int] = Field(default_factory=dict)
    durations: dict[str, dict[str, float]] = Field(default_factory=dict)


class ObservabilityReport(BaseModel):
    """Application-layer observability report independent of a delivery transport."""

    model_config = ConfigDict(frozen=True)

    workflow_timeline: WorkflowTimeline
    operation_timeline: OperationTimeline
    repository_metrics: dict[str, Any] = Field(default_factory=dict)
    provider_metrics: dict[str, Any] = Field(default_factory=dict)
    backend_metrics: dict[str, Any] = Field(default_factory=dict)
    automation_metrics: dict[str, Any] = Field(default_factory=dict)
    release_metrics: dict[str, Any] = Field(default_factory=dict)
    performance_snapshot: PerformanceSnapshot

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def to_markdown(self) -> str:
        return _markdown("Observability Report", self.model_dump(mode="json"))


class DiagnosticsReport(BaseModel):
    """Transport-neutral diagnostics assembled from safe existing snapshots."""

    model_config = ConfigDict(frozen=True)

    system: dict[str, Any] = Field(default_factory=dict)
    repository: dict[str, Any] = Field(default_factory=dict)
    workflow: dict[str, Any] = Field(default_factory=dict)
    provider: dict[str, Any] = Field(default_factory=dict)
    backend: dict[str, Any] = Field(default_factory=dict)
    configuration: dict[str, Any] = Field(default_factory=dict)
    environment: dict[str, Any] = Field(default_factory=dict)
    performance: dict[str, Any] = Field(default_factory=dict)

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def to_markdown(self) -> str:
        return _markdown("Diagnostics Report", self.model_dump(mode="json"))


class PerformanceBaseline(BaseModel):
    """Named baseline averages provided by an approved local measurement."""

    model_config = ConfigDict(frozen=True)

    name: str
    averages_seconds: dict[str, float] = Field(default_factory=dict)


class PerformanceComparison(BaseModel):
    """Current and baseline duration comparison for one metric."""

    model_config = ConfigDict(frozen=True)

    metric: str
    baseline_seconds: float = Field(ge=0)
    current_seconds: float = Field(ge=0)
    change_ratio: float
    regressed: bool


class PerformanceTrend(BaseModel):
    """A supplied historical trend; samples are never persisted by this facade."""

    model_config = ConfigDict(frozen=True)

    metric: str
    samples_seconds: tuple[float, ...] = ()
    direction: Literal["improving", "stable", "regressing", "unknown"]


class OptimizationRecommendation(BaseModel):
    """Diagnostic-only recommendation with no automatic optimization action."""

    model_config = ConfigDict(frozen=True)

    metric: str
    priority: Literal["low", "medium", "high"]
    message: str


class RegressionSummary(BaseModel):
    """Bounded regression status for an approved baseline comparison."""

    model_config = ConfigDict(frozen=True)

    baseline_name: str | None = None
    regressed: bool
    compared_metrics: int = Field(ge=0)
    regressions: tuple[str, ...] = ()


class PerformanceReport(BaseModel):
    """Performance analysis DTO with baseline, comparison, trend, and advice."""

    model_config = ConfigDict(frozen=True)

    snapshot: PerformanceSnapshot
    comparisons: tuple[PerformanceComparison, ...] = ()
    trends: tuple[PerformanceTrend, ...] = ()
    regression: RegressionSummary
    recommendations: tuple[OptimizationRecommendation, ...] = ()

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def to_markdown(self) -> str:
        return _markdown("Performance Report", self.model_dump(mode="json"))


class MaintenanceSchedulerPlan(BaseModel):
    """A declarative maintenance schedule. It never schedules or executes work."""

    model_config = ConfigDict(frozen=True)

    automatic_execution: bool = False
    cadence: str = "operator-triggered"
    planned_tasks: tuple[str, ...] = (
        "repository_consistency_validation",
        "health_summary",
        "diagnostics_summary",
        "release_readiness_review",
    )
    messages: tuple[str, ...] = ("Plan only; no task was scheduled or executed.",)


class CleanupPlan(BaseModel):
    """Read-only candidate plan derived from repository maintenance evidence."""

    model_config = ConfigDict(frozen=True)

    candidates: tuple[str, ...] = ()
    actions: dict[str, str] = Field(default_factory=dict)
    execution_performed: bool = False


class OperationsReport(BaseModel):
    """Health, diagnostics, and maintenance planning evidence without automation."""

    model_config = ConfigDict(frozen=True)

    health_summary: dict[str, Any] = Field(default_factory=dict)
    diagnostics_summary: dict[str, Any] = Field(default_factory=dict)
    maintenance: RepositoryMaintenanceReport
    scheduler_plan: MaintenanceSchedulerPlan
    cleanup_plan: CleanupPlan

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def to_markdown(self) -> str:
        return _markdown("Operations Report", self.model_dump(mode="json"))


class ExecutiveSummary(BaseModel):
    """Compact, presentation-independent summary for an operator or release review."""

    model_config = ConfigDict(frozen=True)

    healthy: bool
    workflow_state: str
    repository_healthy: bool
    performance_regressed: bool
    planned_automation: bool
    messages: tuple[str, ...] = ()

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def to_markdown(self) -> str:
        return _markdown("Executive Summary", self.model_dump(mode="json"))


class ProductionInsights:
    """Compose observation and planning DTOs without influencing workflow execution."""

    def __init__(self, *, metrics: MetricsRegistry, maintenance: RepositoryMaintenance) -> None:
        self._metrics = metrics
        self._maintenance = maintenance

    def workflow_timeline(self, context: WorkflowContext) -> WorkflowTimeline:
        history = context.metadata.get("workflow_history", [])
        entries: list[TimelineEntry] = []
        if isinstance(history, list):
            for item in history:
                if isinstance(item, Mapping):
                    entries.append(
                        TimelineEntry(
                            scope="workflow",
                            name=str(item.get("step", "workflow_step")),
                            state=str(item.get("to", item.get("state", context.state.value))),
                            status=str(item.get("kind", "workflow")),
                            details=dict(item),
                        )
                    )
        if not entries:
            entries.append(
                TimelineEntry(scope="workflow", name="current_state", state=context.state.value)
            )
        return WorkflowTimeline(current_state=context.state.value, entries=tuple(entries))

    def operation_timeline(
        self, operations: Sequence[Mapping[str, Any]] | None = None
    ) -> OperationTimeline:
        entries = tuple(
            TimelineEntry(
                scope="operation",
                name=str(operation.get("name", "operation")),
                status=str(operation.get("status", "observed")),
                duration_seconds=_optional_seconds(operation.get("duration_seconds")),
                details={key: value for key, value in operation.items() if key not in {"name", "status", "duration_seconds"}},
            )
            for operation in operations or ()
        )
        return OperationTimeline(entries=entries)

    def performance_snapshot(self) -> PerformanceSnapshot:
        snapshot = self._metrics.snapshot()
        counters = cast(dict[str, int], snapshot["counters"])
        durations = cast(dict[str, dict[str, float]], snapshot["durations"])
        return PerformanceSnapshot(counters=dict(counters), durations=dict(durations))

    def observability_report(
        self,
        context: WorkflowContext,
        operations: Sequence[Mapping[str, Any]] | None = None,
    ) -> ObservabilityReport:
        snapshot = self._metrics.snapshot()
        counters = cast(dict[str, object], snapshot["counters"])
        durations = cast(dict[str, object], snapshot["durations"])
        return ObservabilityReport(
            workflow_timeline=self.workflow_timeline(context),
            operation_timeline=self.operation_timeline(operations),
            repository_metrics=_metric_category("repository", counters, durations),
            provider_metrics=_metric_category("provider", counters, durations),
            backend_metrics=_metric_category("backend", counters, durations),
            automation_metrics=_metric_category("automation", counters, durations),
            release_metrics=_metric_category("release", counters, durations),
            performance_snapshot=self.performance_snapshot(),
        )

    def diagnostics_report(
        self,
        context: WorkflowContext,
        *,
        configuration: Mapping[str, Any] | None = None,
        environment: Mapping[str, Any] | None = None,
        project_id: str | None = None,
    ) -> DiagnosticsReport:
        maintenance = self._maintenance.report(project_id)
        observability = self.observability_report(context)
        return DiagnosticsReport(
            system={"package_version": __version__, "mode": "local", "network_probes": False},
            repository=maintenance.model_dump(mode="json"),
            workflow=observability.workflow_timeline.model_dump(mode="json"),
            provider=observability.provider_metrics,
            backend=observability.backend_metrics,
            configuration=dict(configuration or {}),
            environment=dict(environment or {}),
            performance=observability.performance_snapshot.model_dump(mode="json"),
        )

    def performance_report(
        self,
        *,
        baseline: PerformanceBaseline | None = None,
        history: Mapping[str, Sequence[float]] | None = None,
        regression_ratio: float = 0.2,
    ) -> PerformanceReport:
        if regression_ratio < 0:
            raise ValueError("regression_ratio must be non-negative")
        snapshot = self.performance_snapshot()
        averages = {
            name: values.get("average_seconds", 0.0) for name, values in snapshot.durations.items()
        }
        comparisons: list[PerformanceComparison] = []
        if baseline is not None:
            for metric, baseline_seconds in sorted(baseline.averages_seconds.items()):
                current = averages.get(metric)
                if current is None:
                    continue
                ratio = (current - baseline_seconds) / baseline_seconds if baseline_seconds else 0.0
                comparisons.append(
                    PerformanceComparison(
                        metric=metric,
                        baseline_seconds=baseline_seconds,
                        current_seconds=current,
                        change_ratio=ratio,
                        regressed=baseline_seconds > 0 and ratio > regression_ratio,
                    )
                )
        trends = tuple(_trend(name, samples) for name, samples in sorted((history or {}).items()))
        regressions = tuple(item.metric for item in comparisons if item.regressed)
        recommendations = tuple(
            OptimizationRecommendation(
                metric=item.metric,
                priority="high" if item.change_ratio > 1 else "medium",
                message="Investigate the measured boundary before accepting an optimization change.",
            )
            for item in comparisons
            if item.regressed
        )
        return PerformanceReport(
            snapshot=snapshot,
            comparisons=tuple(comparisons),
            trends=trends,
            regression=RegressionSummary(
                baseline_name=baseline.name if baseline else None,
                regressed=bool(regressions),
                compared_metrics=len(comparisons),
                regressions=regressions,
            ),
            recommendations=recommendations,
        )

    def operations_report(
        self,
        context: WorkflowContext,
        *,
        health_summary: Mapping[str, Any] | None = None,
        project_id: str | None = None,
    ) -> OperationsReport:
        maintenance = self._maintenance.report(project_id)
        diagnostics = self.diagnostics_report(context, project_id=project_id)
        cleanup = maintenance.cleanup
        return OperationsReport(
            health_summary=dict(health_summary or {"healthy": maintenance.healthy}),
            diagnostics_summary={
                "repository_healthy": maintenance.healthy,
                "workflow_state": context.state.value,
                "performance_metrics": len(self.performance_snapshot().durations),
                "system_mode": diagnostics.system.get("mode", "unknown"),
                "network_probes": diagnostics.system.get("network_probes", False),
            },
            maintenance=maintenance,
            scheduler_plan=MaintenanceSchedulerPlan(),
            cleanup_plan=CleanupPlan(candidates=cleanup.candidates, actions=cleanup.reasons),
        )

    def executive_summary(
        self,
        context: WorkflowContext,
        *,
        baseline: PerformanceBaseline | None = None,
        project_id: str | None = None,
    ) -> ExecutiveSummary:
        operations = self.operations_report(context, project_id=project_id)
        performance = self.performance_report(baseline=baseline)
        healthy = operations.maintenance.healthy and not performance.regression.regressed
        return ExecutiveSummary(
            healthy=healthy,
            workflow_state=context.state.value,
            repository_healthy=operations.maintenance.healthy,
            performance_regressed=performance.regression.regressed,
            planned_automation=operations.scheduler_plan.automatic_execution,
            messages=("All automation output is planning-only.",),
        )


def _metric_category(
    category: str, counters: Mapping[str, object], durations: Mapping[str, object]
) -> dict[str, Any]:
    prefix = f"{category}."
    return {
        "counters": {name: value for name, value in counters.items() if name.startswith(prefix)},
        "durations": {name: value for name, value in durations.items() if name.startswith(prefix)},
    }


def _optional_seconds(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def _trend(metric: str, samples: Sequence[float]) -> PerformanceTrend:
    values = tuple(float(value) for value in samples)
    if len(values) < 2:
        direction: Literal["improving", "stable", "regressing", "unknown"] = "unknown"
    elif values[-1] > values[0]:
        direction = "regressing"
    elif values[-1] < values[0]:
        direction = "improving"
    else:
        direction = "stable"
    return PerformanceTrend(metric=metric, samples_seconds=values, direction=direction)


def _markdown(title: str, values: dict[str, Any]) -> str:
    lines = [f"# {title}", ""]
    for key, value in values.items():
        lines.extend([f"## {key.replace('_', ' ').title()}", "", "```json"])
        lines.append(json.dumps(value, indent=2, default=str))
        lines.extend(["```", ""])
    return "\n".join(lines)
