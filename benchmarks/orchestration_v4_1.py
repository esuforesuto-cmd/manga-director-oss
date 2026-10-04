"""Measure one-page orchestration DTO construction with dispatch disabled."""

from timeit import timeit

from manga_director.domain.state_machine import PageState
from manga_director.production.v4_1_agent_foundation import (
    AgentDTO,
    AgentProfileDTO,
    AgentRegistryRepository,
    RoleDTO,
)
from manga_director.production.v4_1_orchestration import V41OrchestrationService
from manga_director.workflow import WorkflowContext


def main() -> None:
    agent = AgentDTO(
        agent_id="agent",
        profile=AgentProfileDTO(
            profile_id="profile", display_name="Agent", role=RoleDTO(role_id="role", name="Role")
        ),
    )
    service = V41OrchestrationService(AgentRegistryRepository((agent,)))
    context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
    print(
        f"orchestration projections: {timeit(lambda: service.orchestration('project', context), number=1_000):.6f}s"
    )


if __name__ == "__main__":
    main()
