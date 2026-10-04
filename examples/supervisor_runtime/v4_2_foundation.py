"""Prepare a supervisor report without activating monitoring or escalation."""

from manga_director.domain.state_machine import PageState
from manga_director.production.v4_2_autonomous_foundation import V42AutonomousFoundationService
from manga_director.workflow import WorkflowContext

context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
report = V42AutonomousFoundationService().supervisor("project-1", context)

assert report.planning_only is True
assert report.progress.monitoring_active is False
assert report.escalation.escalation_sent is False
print(report.to_json())
