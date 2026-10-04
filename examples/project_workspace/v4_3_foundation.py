"""Preview a v4.3 workspace DTO report without assignment or dispatch."""

from manga_director.domain.state_machine import PageState
from manga_director.production import V43ProductionFoundationService
from manga_director.workflow import WorkflowContext

context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
report = V43ProductionFoundationService().project_workspace("project-1", context)

assert report.planning_only is True
assert report.task.assigned is False
assert report.task.dispatched is False
print(report.to_json())
