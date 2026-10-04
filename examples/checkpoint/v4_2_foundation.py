"""Prepare checkpoint evidence without persistence or resume."""

from manga_director.domain.state_machine import PageState
from manga_director.production.v4_2_autonomous_foundation import V42AutonomousFoundationService
from manga_director.workflow import WorkflowContext

context = WorkflowContext(
    page={"id": "page-1", "storyboard": {"panels": []}},
    state=PageState.STORYBOARDED,
    artifacts={"storyboard": {"panels": []}},
)
report = V42AutonomousFoundationService().checkpoint("project-1", context)

assert report.checkpoint.checkpoint_persisted is False
assert report.resume_result.resumed is False
assert report.resume_request.human_authorization_required is True
print(report.to_json())
