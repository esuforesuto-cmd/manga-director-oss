"""Measure disabled runtime-request DTO construction only."""

from timeit import timeit

from manga_director.domain.state_machine import PageState
from manga_director.production.v4_1_agent_foundation import (
    AgentDTO,
    AgentProfileDTO,
    AgentRegistryRepository,
    RoleDTO,
    V41AgentFoundationService,
)
from manga_director.workflow import WorkflowContext


def main() -> None:
    agent = AgentDTO(
        agent_id="agent",
        profile=AgentProfileDTO(
            profile_id="profile", display_name="Agent", role=RoleDTO(role_id="role", name="Role")
        ),
    )
    service = V41AgentFoundationService(AgentRegistryRepository((agent,)))
    context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
    print(
        f"runtime projections: {timeit(lambda: service.runtime('agent', 'project', context), number=1_000):.6f}s"
    )


if __name__ == "__main__":
    main()
