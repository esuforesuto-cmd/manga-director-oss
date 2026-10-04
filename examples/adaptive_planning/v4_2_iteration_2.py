"""Prepare a planning revision without applying or executing it."""

from manga_director.domain.state_machine import PageState
from manga_director.production.v4_2_autonomous_workflow import V42AutonomousWorkflowService
from manga_director.workflow import WorkflowContext

context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
report = V42AutonomousWorkflowService().adaptive_planning(
    "project-1", context, "Prepare one page for human review"
)

assert report.planning_only is True
assert report.session.session_started is False
assert report.revision.revision_applied is False
assert report.dependency_resolver.resolution_applied is False
print(report.to_json())
