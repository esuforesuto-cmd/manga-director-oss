"""Measure approval-request DTO projection only; no request is dispatched."""

from timeit import timeit

from manga_director.domain.state_machine import PageState
from manga_director.production.v4_1_agent_foundation import AgentRegistryRepository
from manga_director.production.v4_1_assurance import V41PlatformAssuranceService
from manga_director.workflow import WorkflowContext


def main() -> None:
    service = V41PlatformAssuranceService(AgentRegistryRepository())
    context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
    print(
        f"approval projections: {timeit(lambda: service.human_review('project', context), number=1_000):.6f}s"
    )


if __name__ == "__main__":
    main()
