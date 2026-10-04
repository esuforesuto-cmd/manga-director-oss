from manga_director.domain.events import EventType, WorkflowEvent
from manga_director.events import MemoryEventBus
from manga_director.notifications import (
    MockNotificationProvider,
    NotificationFactory,
    NotificationMessage,
    NotificationService,
    RetryPolicy,
)


def test_factory_and_event_subscription() -> None:
    assert "mock" in NotificationFactory.available()
    provider = MockNotificationProvider()
    service = NotificationService(provider)
    bus = MemoryEventBus()
    service.subscribe(bus, [EventType.PAGE_DESIGNED])
    bus.publish([WorkflowEvent(event_type=EventType.PAGE_DESIGNED)])
    assert len(provider.sent) == 1
    assert service.history.entries[0]["status"] == "sent"


def test_retry_records_attempts() -> None:
    service = NotificationService(
        MockNotificationProvider(False),
        retry_policy=RetryPolicy(max_attempts=2, initial_delay=0),
    )
    result = service.send(NotificationMessage(event_type="test", title="Test", body="body"))
    assert not result.success
    assert result.attempts == 2
