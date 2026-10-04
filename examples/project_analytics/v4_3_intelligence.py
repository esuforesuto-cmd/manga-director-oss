"""Preview a v4.3 project-analytics report without operational mutation."""

from manga_director.domain.state_machine import PageState
from manga_director.production import V43ProductionIntelligenceService
from manga_director.workflow import WorkflowContext

context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
report = V43ProductionIntelligenceService().project_analytics("project-1", context)

assert report.planning_only is True
assert report.resources.resources_allocated is False
assert report.dashboard.automation_enabled is False
print(report.to_json())
