"""Passive repository/database metrics helpers."""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from typing import TypeVar

from manga_director.observability.metrics import MetricsRegistry

T = TypeVar("T")


class RepositoryMetrics:
    """Record repository operations without changing their persistence semantics."""

    def __init__(
        self, metrics: MetricsRegistry | None = None, *, boundary: str = "repository"
    ) -> None:
        self.metrics = metrics or MetricsRegistry()
        self.boundary = boundary

    def measure(self, operation: str, action: Callable[[], T]) -> T:
        started = perf_counter()
        try:
            return action()
        finally:
            self.metrics.increment(f"{self.boundary}.operations.{operation}")
            self.metrics.observe(
                f"{self.boundary}.duration_seconds.{operation}", perf_counter() - started
            )
