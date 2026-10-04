from dataclasses import dataclass
from typing import Any

import pytest

from manga_director.domain.events import EventType
from manga_director.domain.exceptions import AgentExecutionError, InvalidPageTransition
from manga_director.domain.state_machine import PageState, StateMachine
from manga_director.events import MemoryEventBus
from manga_director.workflow import AgentResult, WorkflowContext, WorkflowEngine


@dataclass
class StubAgent:
    state: PageState
    success: bool = True
    payload: dict[str, Any] | None = None
    messages: list[str] | None = None
    received_context: WorkflowContext | None = None

    def execute(self, context: WorkflowContext) -> AgentResult:
        self.received_context = context
        return AgentResult(
            success=self.success,
            state=self.state,
            payload=self.payload or {},
            messages=self.messages or ["stub complete"],
        )


def test_engine_executes_only_the_agent_for_the_next_state() -> None:
    bus = MemoryEventBus()
    design_agent = StubAgent(PageState.DESIGNED, payload={"brief": "opening"})
    engine = WorkflowEngine(
        state_machine=StateMachine(),
        event_bus=bus,
        agents={PageState.DESIGNED: design_agent},
    )
    context = WorkflowContext(page={"id": "001"}, metadata={"project": "demo"})

    result = engine.execute(context)

    assert design_agent.received_context == context
    assert result.current_state == PageState.DESIGNED
    assert result.completed_step == PageState.DESIGNED
    assert result.context.artifacts["Designed"] == {"brief": "opening"}
    assert [event.event_type for event in result.events] == [EventType.PAGE_DESIGNED]
    assert bus.published == result.events
    assert result.logs[0] == "Draft -> Designed"


def test_engine_rejects_an_agent_that_returns_an_invalid_state() -> None:
    engine = WorkflowEngine(
        state_machine=StateMachine(),
        event_bus=MemoryEventBus(),
        agents={PageState.DESIGNED: StubAgent(PageState.REVIEWED)},
    )

    with pytest.raises(InvalidPageTransition):
        engine.execute(WorkflowContext())


def test_engine_does_not_publish_when_agent_fails() -> None:
    bus = MemoryEventBus()
    engine = WorkflowEngine(
        state_machine=StateMachine(),
        event_bus=bus,
        agents={PageState.DESIGNED: StubAgent(PageState.DESIGNED, success=False)},
    )

    with pytest.raises(AgentExecutionError):
        engine.execute(WorkflowContext())
    assert bus.published == []


def test_quality_failure_is_published_without_skipping_quality_state() -> None:
    quality_agent = StubAgent(PageState.QUALITY_CHECKED, payload={"passed": False})
    engine = WorkflowEngine(
        state_machine=StateMachine(),
        event_bus=MemoryEventBus(),
        agents={PageState.QUALITY_CHECKED: quality_agent},
    )
    context = WorkflowContext(state=PageState.GENERATED)

    result = engine.execute(context)

    assert result.current_state == PageState.QUALITY_CHECKED
    assert result.events[-1].event_type == EventType.QUALITY_FAILED
