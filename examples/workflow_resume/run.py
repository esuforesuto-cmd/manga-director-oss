"""Validate a persisted Page before manually resuming exactly one legal step."""

from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState, StateMachine
from manga_director.events import MemoryEventBus
from manga_director.production import ReliabilityOperations
from manga_director.repositories import InMemoryRepository, ProjectLoader
from manga_director.workflow import AgentResult, WorkflowContext, WorkflowEngine


class DesignAgent:
    def execute(self, context: WorkflowContext) -> AgentResult:
        del context
        return AgentResult(success=True, state=PageState.DESIGNED)


def main() -> None:
    repository = InMemoryRepository()
    repository.save(Project(id="demo", title="Demo", pages=[Page(page_number=1)]))
    loader = ProjectLoader(repository)
    engine = WorkflowEngine(
        state_machine=StateMachine(), event_bus=MemoryEventBus(), agents={PageState.DESIGNED: DesignAgent()}
    )
    report = ReliabilityOperations(engine=engine, loader=loader, repository=repository).validate_resume(
        "demo", 1
    )
    print(report.to_markdown())


if __name__ == "__main__":
    main()
