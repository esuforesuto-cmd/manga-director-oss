"""Prepare a human approval request DTO without dispatching or approving it."""

from manga_director.domain.state_machine import PageState
from manga_director.production.v4_1_agent_foundation import AgentRegistryRepository
from manga_director.production.v4_1_assurance import V41PlatformAssuranceService
from manga_director.workflow import WorkflowContext


def main() -> None:
    service = V41PlatformAssuranceService(AgentRegistryRepository())
    context = WorkflowContext(page={"id": "page-1"}, state=PageState.PROMPT_BUILT)
    print(service.human_review("project-1", context).to_json())


if __name__ == "__main__":
    main()
