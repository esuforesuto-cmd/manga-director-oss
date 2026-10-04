"""Lifecycle state tracking for adapters without changing adapter protocols."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from manga_director.adapters.runtime_models import AdapterHealth, AdapterMetadata


class AdapterLifecycleState(StrEnum):
    """Operational lifecycle visible to application and diagnostics layers."""

    READY = "ready"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    SHUTDOWN = "shutdown"


class AdapterLifecycleSnapshot(BaseModel):
    """Immutable lifecycle record for one registered adapter."""

    model_config = ConfigDict(frozen=True)

    name: str
    state: AdapterLifecycleState
    updated_at: datetime
    messages: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()


class AdapterLifecycle:
    """Stateful runtime companion; providers and backends themselves stay stateless."""

    def __init__(
        self,
        metadata: Callable[[], list[AdapterMetadata]],
        health: Callable[[], list[AdapterHealth]],
    ) -> None:
        self._metadata = metadata
        self._health = health
        self._snapshots: dict[str, AdapterLifecycleSnapshot] = {}

    def initialize(self) -> list[AdapterLifecycleSnapshot]:
        """Register known adapters as ready without invoking their generation API."""

        now = datetime.now(UTC)
        for item in self._metadata():
            self._snapshots[item.name] = AdapterLifecycleSnapshot(
                name=item.name,
                state=AdapterLifecycleState.READY,
                updated_at=now,
                capabilities=item.capabilities,
            )
        return self.snapshots()

    def refresh_health(self) -> list[AdapterLifecycleSnapshot]:
        """Refresh local construction health; no external request is made."""

        if not self._snapshots:
            self.initialize()
        metadata = {item.name: item for item in self._metadata()}
        now = datetime.now(UTC)
        for check in self._health():
            item = metadata.get(check.name)
            state = AdapterLifecycleState.HEALTHY if check.healthy else AdapterLifecycleState.UNAVAILABLE
            self._snapshots[check.name] = AdapterLifecycleSnapshot(
                name=check.name,
                state=state,
                updated_at=now,
                messages=tuple(check.messages),
                capabilities=item.capabilities if item else (),
            )
        return self.snapshots()

    def mark_degraded(self, name: str, message: str) -> AdapterLifecycleSnapshot:
        """Record a recoverable operational warning reported by an outer layer."""

        previous = self._snapshots.get(name)
        if previous is None:
            raise KeyError(f"Unknown adapter: {name}")
        snapshot = previous.model_copy(
            update={
                "state": AdapterLifecycleState.DEGRADED,
                "updated_at": datetime.now(UTC),
                "messages": (*previous.messages, message),
            }
        )
        self._snapshots[name] = snapshot
        return snapshot

    def shutdown(self) -> list[AdapterLifecycleSnapshot]:
        """Mark runtime handles closed; adapter protocols intentionally have no shutdown hook."""

        if not self._snapshots:
            self.initialize()
        now = datetime.now(UTC)
        for name, previous in list(self._snapshots.items()):
            self._snapshots[name] = previous.model_copy(
                update={"state": AdapterLifecycleState.SHUTDOWN, "updated_at": now}
            )
        return self.snapshots()

    def snapshots(self) -> list[AdapterLifecycleSnapshot]:
        return [self._snapshots[name] for name in sorted(self._snapshots)]

    def summary(self) -> dict[str, int]:
        summary = {state.value: 0 for state in AdapterLifecycleState}
        for snapshot in self._snapshots.values():
            summary[snapshot.state.value] += 1
        return summary
