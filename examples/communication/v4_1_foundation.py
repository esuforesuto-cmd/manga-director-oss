"""Prepare a local unsent agent message; no transport is connected."""

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
    role = RoleDTO(role_id="creative", name="Creative")
    agents = tuple(
        AgentDTO(
            agent_id=agent_id,
            profile=AgentProfileDTO(profile_id=agent_id, display_name=agent_id, role=role),
        )
        for agent_id in ("editor-1", "reviewer-1")
    )
    context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
    service = V41AgentFoundationService(AgentRegistryRepository(agents))
    print(service.communication("editor-1", "reviewer-1", "project-1", context).to_json())


if __name__ == "__main__":
    main()
