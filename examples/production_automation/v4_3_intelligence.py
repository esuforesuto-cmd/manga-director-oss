"""Preview a v4.3 production-automation report without starting a workflow."""

from manga_director.domain.state_machine import PageState
from manga_director.production import V43ProductionIntelligenceService
from manga_director.workflow import WorkflowContext

context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
report = V43ProductionIntelligenceService().production_automation("project-1", context)

assert report.planning_only is True
assert report.stage_automation.automation_enabled is False
assert report.schedule.schedule_registered is False
print(report.to_json())
