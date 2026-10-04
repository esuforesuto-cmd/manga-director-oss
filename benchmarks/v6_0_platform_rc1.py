"""Local, provider-free benchmark for the v6.0 RC1 Platform Kernel report."""

from __future__ import annotations

from time import perf_counter

from manga_director.domain.state_machine import PageState
from manga_director.production import V60CreativeProductionPlatformCoreService
from manga_director.workflow import WorkflowContext


def run(iterations: int = 500, *, context: WorkflowContext | None = None) -> float:
    """Measure read-only Platform Kernel report composition for one Page."""

    benchmark_context = context or WorkflowContext(
        page={"id": "benchmark-page"},
        state=PageState.QUALITY_CHECKED,
        artifacts={
            PageState.STORYBOARDED.value: {"panels": []},
            PageState.QUALITY_CHECKED.value: {"status": "passed"},
        },
        metadata={
            "story_context": {},
            "character_context": {},
            "world_context": {},
            "timeline_context": {},
        },
    )
    service = V60CreativeProductionPlatformCoreService()
    started = perf_counter()
    for _ in range(iterations):
        service.platform_core("benchmark-project", benchmark_context)
    return perf_counter() - started


if __name__ == "__main__":
    print(f"{run():.6f}")
