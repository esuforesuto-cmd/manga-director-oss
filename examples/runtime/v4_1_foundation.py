"""Prepare, but never execute, a v4.1 agent runtime request."""

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
        agent_id="editor-1",
        profile=AgentProfileDTO(
            profile_id="editor-profile",
            display_name="Editor",
            role=RoleDTO(role_id="editor", name="Editor"),
        ),
    )
    context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
    service = V41AgentFoundationService(AgentRegistryRepository((agent,)))
    print(service.runtime("editor-1", "project-1", context).to_json())


if __name__ == "__main__":
    main()
