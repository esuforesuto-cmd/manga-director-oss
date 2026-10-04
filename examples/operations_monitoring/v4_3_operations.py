"""Preview v4.3 operations monitoring without telemetry or alert delivery."""

from manga_director.domain.state_machine import PageState
from manga_director.production import V43ProductionOperationsService
from manga_director.workflow import WorkflowContext

context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
report = V43ProductionOperationsService().operations_monitoring("project-1", context)

assert report.planning_only is True
assert report.timeline.monitoring_active is False
assert report.alert.alert_sent is False
print(report.to_json())
