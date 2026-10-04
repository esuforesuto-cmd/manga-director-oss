"""Prepare a recovery recommendation without retrying or restoring work."""

from manga_director.domain.state_machine import PageState
from manga_director.production.v4_2_autonomous_workflow import V42AutonomousWorkflowService
from manga_director.workflow import WorkflowContext

context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
report = V42AutonomousWorkflowService().execution_recovery("project-1", context)

assert report.planning_only is True
assert report.retry.max_automatic_attempts == 0
assert report.result.recovered is False
assert report.result.workflow_changed is False
print(report.to_json())
