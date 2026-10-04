"""Small in-process performance summaries and threshold-based warnings."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

from manga_director.observability.metrics import MetricsRegistry


@dataclass(frozen=True)
class PerformanceWarning:
    metric: str
    observed_seconds: float
    threshold_seconds: float


class PerformanceMonitor:
    """Derive summaries without affecting workflow or repository control flow."""

    def __init__(
        self, metrics: MetricsRegistry, thresholds: Mapping[str, float] | None = None
    ) -> None:
        self._metrics = metrics
        self._thresholds = dict(thresholds or {})

    def summary(self) -> dict[str, object]:
        return self._metrics.snapshot()["durations"]  # type: ignore[return-value]

    def warnings(self) -> list[PerformanceWarning]:
        durations = cast(dict[str, dict[str, float]], self._metrics.snapshot()["durations"])
        return [
            PerformanceWarning(
                metric=name,
                observed_seconds=durations[name]["average_seconds"],
                threshold_seconds=threshold,
            )
            for name, threshold in self._thresholds.items()
            if name in durations and durations[name]["average_seconds"] > threshold
        ]
