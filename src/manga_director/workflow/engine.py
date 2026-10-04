from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from manga_director.domain.events import EventType, WorkflowEvent
from manga_director.domain.exceptions import (
    AgentExecutionError,
    AgentNotAvailableError,
    InvalidPageTransition,
)
from manga_director.domain.state_machine import PageState, StateMachine
from manga_director.events.bus import EventBus
from manga_director.observability.observer import WorkflowObserver
from manga_director.workflow.contracts import (
    Agent,
    AgentResult,
    WorkflowContext,
    WorkflowResult,
    WorkflowStatus,
)


class WorkflowEngine:
    """Safely executes one legal page workflow step without agent-to-agent calls."""

    _event_for_state: dict[PageState, EventType] = {
        PageState.DESIGNED: EventType.PAGE_DESIGNED,
        PageState.REVIEWED: EventType.PAGE_REVIEWED,
        PageState.STORYBOARDED: EventType.STORYBOARD_CREATED,
        PageState.PROMPT_BUILT: EventType.PROMPT_BUILT,
        PageState.GENERATED: EventType.IMAGE_GENERATED,
        PageState.QUALITY_CHECKED: EventType.QUALITY_PASSED,
        PageState.APPROVED: EventType.PAGE_APPROVED,
    }

    def __init__(
        self,
        *,
        state_machine: StateMachine,
        event_bus: EventBus,
        agents: Mapping[PageState, Agent],
        support_agents: Mapping[str, Agent] | None = None,
        observer: WorkflowObserver | None = None,
    ) -> None:
        self._state_machine = state_machine
        self._event_bus = event_bus
        self._agents = dict(agents)
        self._support_agents = dict(support_agents or {})
        self._observer = observer

    def execute(self, context: WorkflowContext) -> WorkflowResult:
        """Invoke only the agent for the next legal state and publish its resulting events."""
        unpublished = self._execute_unpublished(context)
        self._publish_unpublished(unpublished)
        return unpublished.result

    def execute_command(self, context: WorkflowContext, command: str) -> WorkflowResult:
        """Execute a named primary workflow command only when it is currently legal."""
        unpublished = self._execute_unpublished(context, command=command)
        self._publish_unpublished(unpublished)
        return unpublished.result

    def _execute_unpublished(
        self, context: WorkflowContext, *, command: str | None = None
    ) -> _UnpublishedWorkflowStep:
        """Build one normal primary step without publishing its events.

        This is intentionally private for durable composition.  Public callers
        continue through ``execute`` and ``execute_command`` above.
        """

        if command is not None:
            self._state_machine.validate_command(context.state, command)
        next_state = self._state_machine.next_state(context.state)
        trace_id = self._observer.begin(context, next_state) if self._observer else None
        agent = self._agent_for(next_state)
        try:
            agent_result = agent.execute(context)
        except Exception:
            if self._observer and trace_id:
                self._observer.fail(trace_id)
            raise

        if not agent_result.success:
            raise AgentExecutionError(
                f"Agent for {next_state.value} failed: {'; '.join(agent_result.messages)}"
            )
        self._state_machine.validate_transition(context.state, agent_result.state)

        transition_event = self._transition_event(next_state, agent_result)
        step_events = [*agent_result.events, transition_event]
        next_context = context.advance(
            state=next_state,
            events=step_events,
            artifact_name=next_state.value,
            payload=agent_result.payload,
        )
        logs = [f"{context.state.value} -> {next_state.value}", *agent_result.messages]
        result = WorkflowResult(
            current_state=next_context.state,
            completed_step=next_state,
            events=step_events,
            logs=logs,
            context=next_context,
        )
        return _UnpublishedWorkflowStep(
            result=result,
            canonical_event=transition_event,
            events=tuple(step_events),
            trace_id=trace_id,
        )

    def _publish_unpublished(self, step: _UnpublishedWorkflowStep) -> None:
        """Publish an already-created step after its owner accepts the result."""

        self._event_bus.publish(list(step.events))
        if self._observer and step.trace_id:
            completed_step = step.result.completed_step
            if isinstance(completed_step, PageState):
                self._observer.complete(step.trace_id, completed_step)

    def _discard_unpublished(self, step: object) -> None:
        """Mark a private step unsuccessful when durable persistence rejects it."""

        if self._observer and isinstance(step, _UnpublishedWorkflowStep) and step.trace_id:
            self._observer.fail(step.trace_id)

    def _is_canonical_unpublished(self, step: object) -> bool:
        """Accept only the Engine-created transition event in durable composition."""

        return (
            isinstance(step, _UnpublishedWorkflowStep)
            and step.events == (step.canonical_event,)
            and step.result.events == [step.canonical_event]
            and step.result.completed_step == step.result.current_state
        )

    def _unpublished_context(self, step: _UnpublishedWorkflowStep) -> WorkflowContext:
        """Return the private context produced by an unpublished primary step."""

        return step.result.context

    def _unpublished_result(self, step: _UnpublishedWorkflowStep) -> WorkflowResult:
        """Return the private result for the durable coordinator only."""

        return step.result

    def _next_command_for_context(self, context: WorkflowContext) -> str:
        """Return the StateMachine-owned next command for private durable routing."""

        return self._state_machine.next_command(context.state)

    def execute_support(self, context: WorkflowContext, name: str) -> WorkflowResult:
        """Run a stateless support agent without changing the workflow state."""
        try:
            agent = self._support_agents[name]
        except KeyError as exc:
            raise AgentNotAvailableError(f"No support agent is registered as '{name}'.") from exc
        result = agent.execute(context)
        if not result.success:
            raise AgentExecutionError(
                f"Support agent '{name}' failed: {'; '.join(result.messages)}"
            )
        next_context = context.add_support_result(
            name=name,
            payload=result.payload,
            events=result.events,
        )
        self._event_bus.publish(result.events)
        return WorkflowResult(
            current_state=next_context.state,
            completed_step=name,
            events=result.events,
            logs=[f"support agent: {name}", *result.messages],
            context=next_context,
        )

    def run(self, context: WorkflowContext) -> list[WorkflowResult]:
        """Run primary steps through quality; approval stays an explicit human command."""
        results: list[WorkflowResult] = []
        current = context
        while current.state != PageState.QUALITY_CHECKED:
            if current.state == PageState.APPROVED:
                break
            results.append(self.execute(current))
            current = results[-1].context
        return results

    def status(self, context: WorkflowContext) -> WorkflowStatus:
        """Return delivery-ready status without placing workflow logic in CLI code."""
        history = list(context.metadata.get("workflow_history", []))
        completed_steps = [str(item["step"]) for item in history if "step" in item]
        try:
            executable_step: str | None = self._state_machine.next_command(context.state)
        except InvalidPageTransition:  # Approved is terminal; status must remain readable.
            executable_step = None
        return WorkflowStatus(
            current_state=context.state,
            current_step=context.metadata.get("current_step"),
            completed_steps=completed_steps,
            executable_step=executable_step,
            workflow_history=history,
        )

    def _agent_for(self, next_state: PageState) -> Agent:
        try:
            return self._agents[next_state]
        except KeyError as exc:
            raise AgentNotAvailableError(f"No agent is registered for {next_state.value}.") from exc

    def _transition_event(self, state: PageState, result: AgentResult) -> WorkflowEvent:
        event_type = self._event_for_state[state]
        if state == PageState.QUALITY_CHECKED and self._quality_failed(result):
            event_type = EventType.QUALITY_FAILED
        return WorkflowEvent(event_type=event_type, data={"state": state.value})

    @staticmethod
    def _quality_failed(result: AgentResult) -> bool:
        return result.payload.get("passed") is False


@dataclass(frozen=True)
class _UnpublishedWorkflowStep:
    """Private Engine product whose events are not yet published."""

    result: WorkflowResult
    canonical_event: WorkflowEvent
    events: tuple[WorkflowEvent, ...]
    trace_id: str | None
