"""Build a single-page collaboration plan with pending human review."""

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
        agent_id="reviewer-1",
        profile=AgentProfileDTO(
            profile_id="reviewer-profile",
            display_name="Reviewer",
            role=RoleDTO(role_id="reviewer", name="Reviewer"),
        ),
    )
    context = WorkflowContext(page={"id": "page-1"}, state=PageState.QUALITY_CHECKED)
    service = V41AgentFoundationService(AgentRegistryRepository((agent,)))
    print(service.collaboration("reviewer-1", "project-1", context).to_json())


if __name__ == "__main__":
    main()
