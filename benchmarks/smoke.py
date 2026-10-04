"""Small deterministic benchmark smoke suite; it reports timings, not pass/fail budgets."""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter

from benchmarks.v6_0_platform_rc1 import run as run_platform_kernel_benchmark
from manga_director import Director, WorkflowContext
from manga_director.adapters import ImageGeneratorFactory, LLMFactory, PromptRequest
from manga_director.domain.project import Chapter, Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.notifications import MockNotificationProvider, NotificationMessage
from manga_director.prompting import PromptPipeline
from manga_director.repositories import InMemoryRepository, SQLiteRepository
from manga_director.workflow import ExecutionPlanner, SequentialExecution


def _measure(operation: Callable[[], object]) -> float:
    started = perf_counter()
    operation()
    return perf_counter() - started


def _save_and_load(repository: InMemoryRepository | SQLiteRepository, project: Project) -> Project:
    repository.save(project)
    return repository.load(project.id)


def run_smoke() -> dict[str, float]:
    """Run one provider-free operation per supported benchmark category."""

    project = Project(
        id="benchmark",
        title="Benchmark",
        chapters=[Chapter(id="chapter-1", title="One", page_numbers=[1])],
        pages=[Page(page_number=1)],
    )
    repository = InMemoryRepository()
    database = SQLiteRepository()
    database.create_schema()
    context = WorkflowContext(page={"project_id": "benchmark", "page_id": "1"})
    prompt_context = WorkflowContext(
        page={"page_id": "1"},
        state=PageState.STORYBOARDED,
        artifacts={
            "Designed": {
                "page_type": "drama",
                "purpose": "Reveal a clue",
                "featured_character": "Aki",
            },
            "Storyboarded": {"panels": [{"number": 1, "action": "turn"}]},
        },
    )

    return {
        "workflow": _measure(lambda: Director.default().execute(context, "design")),
        "repository": _measure(lambda: _save_and_load(repository, project)),
        "database": _measure(lambda: _save_and_load(database, project)),
        "prompt": _measure(lambda: PromptPipeline().run(prompt_context)),
        "llm": _measure(
            lambda: LLMFactory.create("mock").generate(PromptRequest(user_prompt="test"))
        ),
        "image": _measure(lambda: ImageGeneratorFactory.create("mock").generate("test")),
        "notification": _measure(
            lambda: MockNotificationProvider().send(
                NotificationMessage(event_type="benchmark", title="Benchmark", body="smoke")
            )
        ),
        "batch": _measure(lambda: ExecutionPlanner().plan(project, SequentialExecution())),
        "platform_kernel": run_platform_kernel_benchmark(iterations=1),
    }


if __name__ == "__main__":
    for name, elapsed in run_smoke().items():
        print(f"{name}: {elapsed:.6f}s")
