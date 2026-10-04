"""Show an immutable v4.1 agent registry; no agent is invoked."""

from manga_director.production.v4_1_agent_foundation import (
    AgentDTO,
    AgentProfileDTO,
    AgentRegistryRepository,
    CapabilityDTO,
    RoleDTO,
    V41AgentFoundationService,
)


def main() -> None:
    role = RoleDTO(role_id="editor", name="Editor", responsibilities=("prepare review",))
    capability = CapabilityDTO(
        capability_id="review-preparation",
        name="Review preparation",
        description="Descriptive only.",
    )
    agent = AgentDTO(
        agent_id="editor-1",
        profile=AgentProfileDTO(
            profile_id="editor-profile",
            display_name="Editor",
            role=role,
            capabilities=(capability,),
        ),
    )
    print(V41AgentFoundationService(AgentRegistryRepository((agent,))).registry().to_json())


if __name__ == "__main__":
    main()
