"""Measure unsent local message DTO construction only."""

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
    role = RoleDTO(role_id="role", name="Role")
    agents = tuple(
        AgentDTO(
            agent_id=item, profile=AgentProfileDTO(profile_id=item, display_name=item, role=role)
        )
        for item in ("one", "two")
    )
    service = V41AgentFoundationService(AgentRegistryRepository(agents))
    context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
    print(
        f"message projections: {timeit(lambda: service.communication('one', 'two', 'project', context), number=1_000):.6f}s"
    )


if __name__ == "__main__":
    main()
