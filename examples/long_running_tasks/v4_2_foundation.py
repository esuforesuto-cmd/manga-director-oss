"""Prepare a long-running-task plan without a queue or background worker."""

from manga_director.domain.state_machine import PageState
from manga_director.production.v4_2_autonomous_foundation import V42AutonomousFoundationService
from manga_director.workflow import WorkflowContext

context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
report = V42AutonomousFoundationService().long_running_tasks("project-1", context)

assert report.planning_only is True
assert report.queue.queued_for_dispatch is False
assert report.background_task.background_started is False
print(report.to_json())
