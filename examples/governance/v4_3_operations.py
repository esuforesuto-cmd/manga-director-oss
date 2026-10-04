"""Preview v4.3 production governance without policy enforcement or approval."""

from manga_director.domain.state_machine import PageState
from manga_director.production import V43ProductionOperationsService
from manga_director.workflow import WorkflowContext

context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
report = V43ProductionOperationsService().production_governance("project-1", context)

assert report.planning_only is True
assert report.policy.policy_enforced is False
assert report.approval_matrix.approval_granted is False
print(report.to_json())
