from __future__ import annotations

from time import perf_counter
from uuid import uuid4

from manga_director.domain.state_machine import PageState
from manga_director.observability.metrics import MetricsRegistry
from manga_director.workflow.contracts import WorkflowContext


class WorkflowObserver:
    """Passive workflow observer. It never selects agents or changes state."""

    def __init__(self, metrics: MetricsRegistry | None = None) -> None:
        self.metrics = metrics or MetricsRegistry()
        self._timeline: dict[str, list[dict[str, object]]] = {}
        self._started: dict[str, float] = {}

    def begin(self, context: WorkflowContext, target: PageState) -> str:
        trace_id = str(context.metadata.get("trace_id") or uuid4())
        correlation_id = str(context.metadata.get("correlation_id") or trace_id)
        self._started[trace_id] = perf_counter()
        self._timeline.setdefault(trace_id, []).append(
            {
                "state": context.state.value,
                "target": target.value,
                "started": perf_counter(),
                "trace_id": trace_id,
                "correlation_id": correlation_id,
            }
        )
        self.metrics.increment("workflow.executions")
        self.metrics.increment(f"agent.executions.{target.value}")
        return trace_id

    def complete(self, trace_id: str, state: PageState) -> None:
        elapsed = perf_counter() - self._started.pop(trace_id, perf_counter())
        self.metrics.observe("workflow.duration_seconds", elapsed)
        self.metrics.observe(f"agent.duration_seconds.{state.value}", elapsed)
        self._timeline.setdefault(trace_id, []).append(
            {"state": state.value, "ended": perf_counter(), "duration_seconds": elapsed}
        )

    def fail(self, trace_id: str) -> None:
        self._started.pop(trace_id, None)
        self.metrics.increment("workflow.errors")

    def timeline(self, trace_id: str) -> list[dict[str, object]]:
        return list(self._timeline.get(trace_id, []))

    def timeline_summary(self, trace_id: str) -> dict[str, object]:
        """Return a compact timeline summary suitable for long workflow traces."""

        timeline = self._timeline.get(trace_id, [])
        durations = [
            duration
            for item in timeline
            if isinstance((duration := item.get("duration_seconds")), (int, float))
        ]
        return {
            "trace_id": trace_id,
            "transition_count": sum(1 for item in timeline if "target" in item),
            "total_duration_seconds": sum(durations),
            "max_step_duration_seconds": max(durations, default=0.0),
        }
