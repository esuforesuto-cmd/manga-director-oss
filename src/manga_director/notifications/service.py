"""Application service that delivers notifications and records delivery history."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import sleep
from typing import Any

from manga_director.domain.events import WorkflowEvent
from manga_director.events.bus import EventBus
from manga_director.notifications.models import NotificationMessage, NotificationResult
from manga_director.notifications.providers import NotificationProvider


@dataclass(frozen=True)
class RetryPolicy:
    """Bounded retry policy for transient notification delivery failures."""

    max_attempts: int = 3
    initial_delay: float = 0.1
    max_delay: float = 1.0
    backoff_multiplier: float = 2.0
    retryable_status_codes: frozenset[int] = frozenset({408, 429, 500, 502, 503, 504})


@dataclass
class DeliveryHistory:
    """In-memory, redacted delivery history used for diagnostics."""

    entries: list[dict[str, Any]] = field(default_factory=list)

    def append(
        self,
        result: NotificationResult,
        destination: str | None = None,
    ) -> None:
        self.entries.append(
            {
                "notification_id": result.message_id,
                "provider": result.provider,
                "destination": destination,
                "status": "sent" if result.success else "failed",
                "attempts": result.attempts,
                "error_code": result.status_code,
                "trace_id": result.metadata.get("trace_id"),
            }
        )


class NotificationService:
    """Deliver event-driven notifications through one provider boundary."""

    def __init__(
        self,
        provider: NotificationProvider,
        *,
        retry_policy: RetryPolicy | None = None,
        history: DeliveryHistory | None = None,
    ) -> None:
        self._provider = provider
        self._policy = retry_policy or RetryPolicy()
        self.history = history or DeliveryHistory()

    def subscribe(self, bus: EventBus, event_types: list[str]) -> None:
        for event_type in event_types:
            bus.subscribe(event_type, self.handle_event)

    def handle_event(self, event: WorkflowEvent) -> None:
        self.send(
            NotificationMessage(
                event_type=str(event.event_type),
                title=str(event.event_type),
                body="Workflow event received",
                metadata=event.data,
            )
        )

    def send(self, message: NotificationMessage) -> NotificationResult:
        """Deliver a message, retrying network failures and known transient statuses."""

        delay = self._policy.initial_delay
        result: NotificationResult | None = None

        for attempt in range(1, self._policy.max_attempts + 1):
            provider_result = self._provider.send(message)
            result = provider_result.model_copy(
                update={
                    "attempts": attempt,
                    "metadata": {
                        "trace_id": message.trace_id,
                        "correlation_id": message.correlation_id,
                    },
                }
            )
            retryable = (
                result.status_code is None
                or result.status_code in self._policy.retryable_status_codes
            )
            if result.success or not retryable:
                self.history.append(result)
                return result

            if attempt < self._policy.max_attempts:
                sleep(min(delay, self._policy.max_delay))
                delay *= self._policy.backoff_multiplier

        if result is None:  # Defensive guard for an invalid retry policy.
            raise RuntimeError("Notification delivery did not execute")
        self.history.append(result)
        return result
