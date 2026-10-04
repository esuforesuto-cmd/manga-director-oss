from manga_director.domain.events import EventType, WorkflowEvent
from manga_director.events import MemoryEventBus


def test_memory_event_bus_publishes_and_notifies_subscribers() -> None:
    bus = MemoryEventBus()
    received: list[WorkflowEvent] = []
    bus.subscribe(EventType.PAGE_DESIGNED, received.append)
    event = WorkflowEvent(event_type=EventType.PAGE_DESIGNED, data={"page": "001"})

    bus.publish([event])

    assert bus.published == [event]
    assert received == [event]
