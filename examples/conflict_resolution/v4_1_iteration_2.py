"""Build advisory conflict evidence without applying a merge or decision."""

from manga_director.domain.state_machine import PageState
from manga_director.production.v4_1_agent_foundation import AgentRegistryRepository
from manga_director.production.v4_1_orchestration import V41OrchestrationService
from manga_director.workflow import WorkflowContext


def main() -> None:
    service = V41OrchestrationService(AgentRegistryRepository())
    context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
    print(service.conflict_resolution("project-1", context).to_json())


if __name__ == "__main__":
    main()
