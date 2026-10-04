"""Prepare a Goal Management report without registering or selecting work."""

from manga_director.domain.state_machine import PageState
from manga_director.production.v4_2_autonomous_workflow import V42AutonomousWorkflowService
from manga_director.workflow import WorkflowContext

context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
report = V42AutonomousWorkflowService().goal_management(
    "project-1", context, "Prepare one page for human review"
)

assert report.planning_only is True
assert report.manager.goal.page_count == 1
assert report.manager.goal.execution_enabled is False
assert report.milestone.completed is False
print(report.to_json())
