"""Show a pending handoff/review/approval workflow with no execution."""

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
    role = RoleDTO(role_id="creative", name="Creative")
    agents = tuple(
        AgentDTO(
            agent_id=name, profile=AgentProfileDTO(profile_id=name, display_name=name, role=role)
        )
        for name in ("editor-1", "reviewer-1")
    )
    service = V41OrchestrationService(AgentRegistryRepository(agents))
    context = WorkflowContext(page={"id": "page-1"}, state=PageState.QUALITY_CHECKED)
    print(service.collaboration_workflow("editor-1", "reviewer-1", "project-1", context).to_json())


if __name__ == "__main__":
    main()
