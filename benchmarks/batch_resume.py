"""Measure deterministic sequential Batch checkpoint, resume, and retry paths."""

from __future__ import annotations

import sys
from pathlib import Path
from time import perf_counter

if __package__ in {None, ""}:  # Supports direct ``python benchmarks/...`` execution.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks.large_project import make_large_project
from manga_director.domain.state_machine import PageState
from manga_director.events import MemoryEventBus
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import BatchWorkflowEngine, WorkflowContext, WorkflowResult


class _ContextStore:
    def __init__(self, page_count: int) -> None:
        self._contexts = {
            page_number: WorkflowContext(page={"page_id": str(page_number)})
            for page_number in range(1, page_count + 1)
        }

    def load(self, project_id: str, page_id: str) -> WorkflowContext:
        del project_id
        return self._contexts[int(page_id)]

    def save(self, project_id: str, page_id: str, context: WorkflowContext) -> None:
        del project_id
        self._contexts[int(page_id)] = context


class _Worker:
    def __init__(self, fail_page: int) -> None:
        self.fail_page: int | None = fail_page

    def run(self, context: WorkflowContext) -> WorkflowResult:
        page_number = int(context.page["page_id"])
        if self.fail_page == page_number:
            raise RuntimeError("planned benchmark failure")
        completed = context.model_copy(update={"state": PageState.QUALITY_CHECKED}, deep=False)
        return WorkflowResult(
            current_state=PageState.QUALITY_CHECKED,
            completed_step=PageState.QUALITY_CHECKED,
            context=completed,
        )


def run(page_count: int = 80) -> float:
    project = make_large_project(page_count=page_count, chapter_size=20)
    repository = InMemoryRepository()
    repository.save(project)
    worker = _Worker(fail_page=40)
    engine = BatchWorkflowEngine(
        repository,
        _ContextStore(page_count),
        worker,
        MemoryEventBus(),
    )
    started = perf_counter()
    engine.run(project.id, batch_id="resume-benchmark")
    engine.resume(project.id, "resume-benchmark")
    worker.fail_page = None
    engine.retry(project.id, "resume-benchmark")
    return perf_counter() - started


if __name__ == "__main__":
    print(f"batch_resume: {run():.6f}s")
