from __future__ import annotations

from typing import cast

from pydantic import BaseModel, Field

from manga_director.observability.metrics import MetricsRegistry
from manga_director.observability.observer import WorkflowObserver
from manga_director.observability.performance import PerformanceMonitor


class DiagnosticReport(BaseModel):
    workflow_summary: dict[str, object] = Field(default_factory=dict)
    error_summary: dict[str, object] = Field(default_factory=dict)
    performance_summary: dict[str, object] = Field(default_factory=dict)
    execution_timeline: list[dict[str, object]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class Diagnostics:
    def __init__(
        self,
        metrics: MetricsRegistry,
        observer: WorkflowObserver,
        performance: PerformanceMonitor | None = None,
    ) -> None:
        self._metrics, self._observer = metrics, observer
        self._performance = performance or PerformanceMonitor(metrics)

    def report(self, trace_id: str | None = None) -> DiagnosticReport:
        snapshot = self._metrics.snapshot()
        counters = cast(dict[str, object], snapshot["counters"])
        return DiagnosticReport(
            workflow_summary={"executions": counters.get("workflow.executions", 0)},
            error_summary={"errors": counters.get("workflow.errors", 0)},
            performance_summary=self._performance.summary(),
            execution_timeline=self._observer.timeline(trace_id) if trace_id else [],
            warnings=[warning.metric for warning in self._performance.warnings()],
        )
