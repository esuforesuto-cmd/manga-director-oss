"""Preview existing StateMachine stages without requesting a transition."""

from manga_director.domain.state_machine import PageState
from manga_director.production import V32FoundationService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

report = V32FoundationService(InMemoryRepository()).workflow_profile_dashboard(
    WorkflowContext(page={"id": "profile-demo-1"}, state=PageState.PROMPT_BUILT)
)
print(report.to_json())
