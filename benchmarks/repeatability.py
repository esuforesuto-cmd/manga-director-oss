"""Small deterministic repeatability measurements for provider-free boundaries."""

from __future__ import annotations

from collections.abc import Callable
from statistics import mean

from pydantic import BaseModel, Field


class RepeatabilityResult(BaseModel):
    runs: int = Field(ge=1)
    minimum_seconds: float
    maximum_seconds: float
    average_seconds: float
    relative_spread: float


def measure(
    operation: Callable[[], float], *, runs: int = 5, inner_runs: int = 100
) -> RepeatabilityResult:
    """Measure small operations after warm-up in batches to reduce scheduler noise."""

    if inner_runs <= 0:
        raise ValueError("inner_runs must be positive")
    # These local lifecycle probes complete in microseconds.  Prime imports and
    # caches once, then make every sample large enough that an OS timeslice
    # does not dominate the reported repeatability signal.
    operation()
    samples = [sum(operation() for _ in range(inner_runs)) for _ in range(runs)]
    average = mean(samples)
    return RepeatabilityResult(
        runs=runs,
        minimum_seconds=min(samples),
        maximum_seconds=max(samples),
        average_seconds=average,
        relative_spread=(max(samples) - min(samples)) / average if average else 0.0,
    )
