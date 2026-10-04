"""Prepare reliability diagnostics without retry or recovery."""

from manga_director.domain.state_machine import PageState
from manga_director.production.v4_2_autonomous_operations import V42AutonomousOperationsService
from manga_director.workflow import WorkflowContext

context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
report = V42AutonomousOperationsService().reliability("project-1", context)

assert report.planning_only is True
assert report.retry_policy.max_automatic_attempts == 0
assert report.recovery_workflow.recovery_started is False
assert report.dashboard.recovery_execution_enabled is False
print(report.to_json())
