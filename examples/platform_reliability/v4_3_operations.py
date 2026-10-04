"""Preview v4.3 platform reliability without checks, recovery, or remediation."""

from manga_director.domain.state_machine import PageState
from manga_director.production import V43ProductionOperationsService
from manga_director.workflow import WorkflowContext

context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
report = V43ProductionOperationsService().platform_reliability("project-1", context)

assert report.planning_only is True
assert report.health.check_executed is False
assert report.recovery_policy.automatic_recovery_enabled is False
print(report.to_json())
