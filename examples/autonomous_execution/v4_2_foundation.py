"""Prepare a v4.2 execution foundation report without starting work."""

from manga_director.domain.state_machine import PageState
from manga_director.production.v4_2_autonomous_foundation import V42AutonomousFoundationService
from manga_director.workflow import WorkflowContext

context = WorkflowContext(
    page={"id": "page-1", "storyboard": {"panels": []}},
    state=PageState.PROMPT_BUILT,
    artifacts={"storyboard": {"panels": []}},
)
report = V42AutonomousFoundationService().execution(
    "project-1", context, "Prepare one page for human review"
)

assert report.planning_only is True
assert report.session.session_started is False
assert report.goal.page_count == 1
print(report.to_json())
