"""Measure advisory conflict-resolution DTO construction only."""

from timeit import timeit

from manga_director.domain.state_machine import PageState
from manga_director.production.v4_1_agent_foundation import AgentRegistryRepository
from manga_director.production.v4_1_orchestration import V41OrchestrationService
from manga_director.workflow import WorkflowContext


def main() -> None:
    service = V41OrchestrationService(AgentRegistryRepository())
    context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
    print(
        f"conflict projections: {timeit(lambda: service.conflict_resolution('project', context), number=1_000):.6f}s"
    )


if __name__ == "__main__":
    main()
