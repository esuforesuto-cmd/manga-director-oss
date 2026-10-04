"""Preview a v4.3 deliverable DTO report without export or publishing."""

from manga_director.domain.state_machine import PageState
from manga_director.production import V43ProductionFoundationService
from manga_director.workflow import WorkflowContext

context = WorkflowContext(page={"id": "page-1"}, state=PageState.QUALITY_CHECKED)
report = V43ProductionFoundationService().deliverables("project-1", context)

assert report.planning_only is True
assert report.export_profile.export_enabled is False
assert report.release_candidate.published is False
print(report.to_json())
