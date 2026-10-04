"""Inspect non-enforcing governance evidence for a declared agent."""

from manga_director.production.v4_1_agent_foundation import (
    AgentDTO,
    AgentProfileDTO,
    AgentRegistryRepository,
    RoleDTO,
)
from manga_director.production.v4_1_assurance import V41PlatformAssuranceService


def main() -> None:
    agent = AgentDTO(
        agent_id="editor-1",
        profile=AgentProfileDTO(
            profile_id="editor",
            display_name="Editor",
            role=RoleDTO(role_id="editor", name="Editor"),
        ),
    )
    service = V41PlatformAssuranceService(AgentRegistryRepository((agent,)))
    print(service.governance("editor-1").to_json())


if __name__ == "__main__":
    main()
