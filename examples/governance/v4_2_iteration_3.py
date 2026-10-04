"""Prepare execution-governance evidence without policy enforcement."""

from manga_director.domain.state_machine import PageState
from manga_director.production.v4_2_autonomous_operations import V42AutonomousOperationsService
from manga_director.workflow import WorkflowContext

context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
report = V42AutonomousOperationsService().execution_governance("project-1", context)

assert report.planning_only is True
assert report.policy.enforcement_enabled is False
assert report.safety_boundary.boundary_enforced is False
assert report.compliance.compliance_confirmed is False
print(report.to_json())
