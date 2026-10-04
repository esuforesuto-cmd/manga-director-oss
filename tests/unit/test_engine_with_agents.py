from manga_director.agents import PageDesignAgent, QualityAgent
from manga_director.domain.events import EventType
from manga_director.domain.state_machine import PageState, StateMachine
from manga_director.events import MemoryEventBus
from manga_director.workflow import WorkflowContext, WorkflowEngine


def test_workflow_engine_calls_a_concrete_agent_and_publishes_its_event() -> None:
    bus = MemoryEventBus()
    engine = WorkflowEngine(
        state_machine=StateMachine(),
        event_bus=bus,
        agents={PageState.DESIGNED: PageDesignAgent()},
    )

    result = engine.execute(WorkflowContext(page={"id": "001"}))

    assert result.current_state == PageState.DESIGNED
    assert result.context.artifacts["Designed"]["purpose"]
    assert result.events[-1].event_type == EventType.PAGE_DESIGNED


def test_quality_agent_failure_flows_through_workflow_engine_event_handling() -> None:
    engine = WorkflowEngine(
        state_machine=StateMachine(),
        event_bus=MemoryEventBus(),
        agents={PageState.QUALITY_CHECKED: QualityAgent()},
    )

    result = engine.execute(
        WorkflowContext(state=PageState.GENERATED, metadata={"quality_scores": {"tempo": 3}})
    )

    assert result.current_state == PageState.QUALITY_CHECKED
    assert result.events[-1].event_type == EventType.QUALITY_FAILED
