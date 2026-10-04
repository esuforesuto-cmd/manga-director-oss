"""Measure deterministic Mock notification delivery repeatability."""

from __future__ import annotations

from time import perf_counter

from benchmarks.repeatability import RepeatabilityResult, measure
from manga_director.notifications import MockNotificationProvider, NotificationMessage


def run(runs: int = 5) -> RepeatabilityResult:
    def operation() -> float:
        provider = MockNotificationProvider()
        started = perf_counter()
        provider.send(NotificationMessage(event_type="benchmark", title="Benchmark", body="test"))
        return perf_counter() - started

    return measure(operation, runs=runs)


if __name__ == "__main__":
    print(run().model_dump_json())
