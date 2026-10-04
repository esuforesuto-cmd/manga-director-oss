"""Measure local immutable registry projection only; no agents are invoked."""

from timeit import timeit

from manga_director.production.v4_1_agent_foundation import (
    AgentDTO,
    AgentProfileDTO,
    AgentRegistryRepository,
    RoleDTO,
    V41AgentFoundationService,
)


def main() -> None:
    agent = AgentDTO(
        agent_id="agent",
        profile=AgentProfileDTO(
            profile_id="profile", display_name="Agent", role=RoleDTO(role_id="role", name="Role")
        ),
    )
    service = V41AgentFoundationService(AgentRegistryRepository((agent,)))
    print(f"registry projections: {timeit(service.registry, number=1_000):.6f}s")


if __name__ == "__main__":
    main()
