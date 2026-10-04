"""Measure non-enforcing governance DTO projection only."""

from timeit import timeit

from manga_director.production.v4_1_agent_foundation import (
    AgentDTO,
    AgentProfileDTO,
    AgentRegistryRepository,
    RoleDTO,
)
from manga_director.production.v4_1_assurance import V41PlatformAssuranceService


def main() -> None:
    agent = AgentDTO(
        agent_id="agent",
        profile=AgentProfileDTO(
            profile_id="profile", display_name="Agent", role=RoleDTO(role_id="role", name="Role")
        ),
    )
    service = V41PlatformAssuranceService(AgentRegistryRepository((agent,)))
    print(
        f"governance projections: {timeit(lambda: service.governance('agent'), number=1_000):.6f}s"
    )


if __name__ == "__main__":
    main()
