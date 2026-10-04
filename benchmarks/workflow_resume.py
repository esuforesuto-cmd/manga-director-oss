"""Read-only workflow-resume validation timing."""

from __future__ import annotations

from time import perf_counter

from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState, StateMachine
from manga_director.events import MemoryEventBus
from manga_director.production import ReliabilityOperations
from manga_director.repositories import InMemoryRepository, ProjectLoader
from manga_director.workflow import AgentResult, WorkflowContext, WorkflowEngine


class _DesignAgent:
    def execute(self, context: WorkflowContext) -> AgentResult:
        del context
        return AgentResult(success=True, state=PageState.DESIGNED)


def build_reliability() -> ReliabilityOperations:
    repository = InMemoryRepository()
    repository.save(Project(id="resume", title="Resume", pages=[Page(page_number=1)]))
    loader = ProjectLoader(repository)
    engine = WorkflowEngine(
        state_machine=StateMachine(), event_bus=MemoryEventBus(), agents={PageState.DESIGNED: _DesignAgent()}
    )
    return ReliabilityOperations(engine=engine, loader=loader, repository=repository)


def run() -> float:
    reliability = build_reliability()
    started = perf_counter()
    assert reliability.validate_resume("resume", 1).resumable is True
    return perf_counter() - started
