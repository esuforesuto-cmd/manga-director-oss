from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Callable, Sequence
from typing import Protocol

from manga_director.domain.events import WorkflowEvent

EventHandler = Callable[[WorkflowEvent], None]


class EventBus(Protocol):
    def publish(self, events: Sequence[WorkflowEvent]) -> None: ...

    def subscribe(self, event_type: str, handler: EventHandler) -> None: ...


class MemoryEventBus:
    """Synchronous in-memory EventBus implementation for unit testing."""

    def __init__(self, *, duplicate_cache_size: int = 4096) -> None:
        if duplicate_cache_size < 1:
            raise ValueError("duplicate_cache_size must be at least 1")
        self.published: list[WorkflowEvent] = []
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._handler_cache: dict[str, tuple[EventHandler, ...]] = {}
        self._published_ids: set[str] = set()
        self._published_order: deque[str] = deque(maxlen=duplicate_cache_size)
        self.duplicate_events = 0

    def publish(self, events: Sequence[WorkflowEvent]) -> None:
        for event in events:
            if event.event_id in self._published_ids:
                self.duplicate_events += 1
                continue
            self._remember(event.event_id)
            self.published.append(event)
            event_type = str(event.event_type)
            for handler in self._handler_cache.get(event_type, ()):
                handler(event)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        handlers = self._handlers[event_type]
        if handler in handlers:
            return
        handlers.append(handler)
        self._handler_cache[event_type] = tuple(handlers)

    def diagnostics(self) -> dict[str, object]:
        return {
            "published": len(self.published),
            "event_types": len(self._handlers),
            "subscriptions": sum(len(items) for items in self._handlers.values()),
            "duplicate_events": self.duplicate_events,
            "duplicate_cache_size": self._published_order.maxlen or 0,
        }

    def _remember(self, event_id: str) -> None:
        if len(self._published_order) == self._published_order.maxlen:
            oldest = self._published_order[0]
            self._published_ids.discard(oldest)
        self._published_order.append(event_id)
        self._published_ids.add(event_id)
