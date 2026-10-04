from manga_director.domain.state_machine import PageState, StateMachine
from manga_director.events import MemoryEventBus
from manga_director.observability import (
    Diagnostics,
    HealthMonitor,
    MetricsRegistry,
    WorkflowObserver,
)
from manga_director.workflow import AgentResult, WorkflowContext, WorkflowEngine


class Agent:
    def execute(self, context: WorkflowContext) -> AgentResult:
        return AgentResult(success=True, state=PageState.DESIGNED, payload={})


def test_metrics_trace_timeline_and_diagnostics() -> None:
    metrics = MetricsRegistry()
    observer = WorkflowObserver(metrics)
    engine = WorkflowEngine(
        state_machine=StateMachine(),
        event_bus=MemoryEventBus(),
        agents={PageState.DESIGNED: Agent()},
        observer=observer,
    )
    engine.execute(WorkflowContext())
    snapshot = metrics.snapshot()
    assert snapshot["counters"]["workflow.executions"] == 1  # type: ignore[index]
    trace_id = next(iter(observer._timeline))
    assert Diagnostics(metrics, observer).report(trace_id).execution_timeline


def test_health_monitor_isolates_failed_check() -> None:
    health = HealthMonitor({"repository": lambda: True, "adapter": lambda: False})
    assert not health.check().healthy
