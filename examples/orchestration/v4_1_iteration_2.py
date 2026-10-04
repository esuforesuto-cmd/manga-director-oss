"""Inspect a v4.1 one-page orchestration plan without dispatching tasks."""

from manga_director.domain.state_machine import PageState
from manga_director.production.v4_1_agent_foundation import (
    AgentDTO,
    AgentProfileDTO,
    AgentRegistryRepository,
    RoleDTO,
)
from manga_director.production.v4_1_orchestration import V41OrchestrationService
from manga_director.workflow import WorkflowContext


def _service() -> V41OrchestrationService:
    agent = AgentDTO(
        agent_id="editor-1",
        profile=AgentProfileDTO(
            profile_id="editor",
            display_name="Editor",
            role=RoleDTO(role_id="editor", name="Editor"),
        ),
    )
    return V41OrchestrationService(AgentRegistryRepository((agent,)))


def main() -> None:
    context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
    print(_service().orchestration("project-1", context).to_json())


if __name__ == "__main__":
    main()
