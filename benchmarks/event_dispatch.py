"""Measure synchronous EventBus lookup and dispatch with bounded duplicate tracking."""

from __future__ import annotations

from time import perf_counter

from manga_director.domain.events import EventType, WorkflowEvent
from manga_director.events import MemoryEventBus


def run(event_count: int = 1000, listener_count: int = 8) -> float:
    bus = MemoryEventBus()
    received: list[str] = []
    for _ in range(listener_count):
        bus.subscribe(EventType.PAGE_DESIGNED, lambda event: received.append(event.event_id))
    events = [WorkflowEvent(event_type=EventType.PAGE_DESIGNED) for _ in range(event_count)]
    started = perf_counter()
    bus.publish(events)
    elapsed = perf_counter() - started
    assert len(received) == event_count * listener_count
    return elapsed


if __name__ == "__main__":
    print(f"event_dispatch: {run():.6f}s")
