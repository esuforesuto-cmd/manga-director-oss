from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from pydantic import BaseModel, Field


class HealthStatus(BaseModel):
    healthy: bool
    checks: dict[str, bool] = Field(default_factory=dict)


class HealthComponent(BaseModel):
    """Transport-safe health detail for one optional runtime boundary."""

    name: str
    healthy: bool
    details: dict[str, object] = Field(default_factory=dict)


class SystemHealthDashboard(BaseModel):
    """Presentation-independent DTO suitable for CLI, MCP, or a future HTTP adapter."""

    healthy: bool
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    components: list[HealthComponent] = Field(default_factory=list)


class HealthMonitor:
    def __init__(self, checks: dict[str, Callable[[], bool]] | None = None) -> None:
        self._checks = checks or {}

    def check(self) -> HealthStatus:
        results = {name: self._safe(check) for name, check in self._checks.items()}
        return HealthStatus(healthy=all(results.values()), checks=results)

    def dashboard(
        self, details: dict[str, dict[str, object]] | None = None
    ) -> SystemHealthDashboard:
        """Build a safe detailed DTO while executing every probe in isolation."""

        status = self.check()
        extra = details or {}
        return SystemHealthDashboard(
            healthy=status.healthy,
            components=[
                HealthComponent(name=name, healthy=healthy, details=dict(extra.get(name, {})))
                for name, healthy in sorted(status.checks.items())
            ],
        )

    @staticmethod
    def _safe(check: Callable[[], bool]) -> bool:
        try:
            return bool(check())
        except Exception:
            return False
