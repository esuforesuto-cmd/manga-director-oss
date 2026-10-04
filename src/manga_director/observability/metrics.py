from __future__ import annotations

from collections import Counter
from contextlib import AbstractContextManager
from time import perf_counter


class MetricsRegistry:
    """In-process counters and duration summaries; no exporter dependency."""

    def __init__(self) -> None:
        self._counters: Counter[str] = Counter()
        self._durations: dict[str, _DurationSummary] = {}

    def increment(self, name: str, value: int = 1) -> None:
        self._counters[name] += value

    def observe(self, name: str, seconds: float) -> None:
        self._durations.setdefault(name, _DurationSummary()).add(seconds)

    def snapshot(self) -> dict[str, object]:
        return {
            "counters": dict(self._counters),
            "durations": {
                key: {
                    "count": values.count,
                    "total_seconds": values.total_seconds,
                    "average_seconds": values.average_seconds,
                    "max_seconds": values.max_seconds,
                }
                for key, values in self._durations.items()
                if values
            },
        }

    def timer(self, name: str) -> AbstractContextManager[object]:
        registry = self

        class Timer:
            def __enter__(self) -> Timer:
                self.started = perf_counter()
                return self

            def __exit__(self, *args: object) -> None:
                registry.observe(name, perf_counter() - self.started)

        return Timer()


class _DurationSummary:
    """Bounded-memory duration accumulator for long-running large projects."""

    def __init__(self) -> None:
        self.count = 0
        self.total_seconds = 0.0
        self.max_seconds = 0.0

    @property
    def average_seconds(self) -> float:
        return self.total_seconds / self.count if self.count else 0.0

    def add(self, seconds: float) -> None:
        self.count += 1
        self.total_seconds += seconds
        self.max_seconds = max(self.max_seconds, seconds)
