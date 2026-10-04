"""Measure reliability DTO construction without retry or recovery execution."""

from timeit import timeit

from manga_director.domain.state_machine import PageState
from manga_director.production.v4_1_agent_foundation import AgentRegistryRepository
from manga_director.production.v4_1_assurance import V41PlatformAssuranceService
from manga_director.workflow import WorkflowContext


def main() -> None:
    service = V41PlatformAssuranceService(AgentRegistryRepository())
    context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
    print(
        f"reliability projections: {timeit(lambda: service.reliability('project', context), number=1_000):.6f}s"
    )


if __name__ == "__main__":
    main()
