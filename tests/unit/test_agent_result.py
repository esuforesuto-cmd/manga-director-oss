from manga_director.domain.events import EventType, WorkflowEvent
from manga_director.domain.state_machine import PageState
from manga_director.workflow import AgentResult


def test_agent_result_exposes_the_shared_required_fields() -> None:
    event = WorkflowEvent(event_type=EventType.PAGE_DESIGNED)
    result = AgentResult(
        success=True,
        state=PageState.DESIGNED,
        payload={"brief": "opening page"},
        events=[event],
        messages=["design complete"],
    )

    assert result.success is True
    assert result.state == PageState.DESIGNED
    assert result.payload["brief"] == "opening page"
    assert result.events == [event]
    assert result.messages == ["design complete"]
