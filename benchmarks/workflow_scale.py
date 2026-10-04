"""Measure repeated page-scoped workflow transitions with mock agents only."""

from __future__ import annotations

from time import perf_counter

from manga_director import Director, WorkflowContext


def run(page_count: int = 200) -> float:
    director = Director.default()
    started = perf_counter()
    for page_number in range(1, page_count + 1):
        director.execute(
            WorkflowContext(page={"project_id": "workflow-scale", "page_id": str(page_number)}),
            "design",
        )
    return perf_counter() - started


if __name__ == "__main__":
    print(f"workflow_scale: {run():.6f}s")
