"""Prepare human-supervision evidence without approval or intervention."""

from manga_director.domain.state_machine import PageState
from manga_director.production.v4_2_autonomous_operations import V42AutonomousOperationsService
from manga_director.workflow import WorkflowContext

context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
report = V42AutonomousOperationsService().human_supervision("project-1", context)

assert report.planning_only is True
assert report.approval_checkpoint.approval_granted is False
assert report.intervention.intervention_applied is False
assert report.override_request.override_granted is False
print(report.to_json())
