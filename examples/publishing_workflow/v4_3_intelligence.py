"""Preview a v4.3 publishing-workflow report without export or distribution."""

from manga_director.domain.state_machine import PageState
from manga_director.production import V43ProductionIntelligenceService
from manga_director.workflow import WorkflowContext

context = WorkflowContext(page={"id": "page-1"}, state=PageState.QUALITY_CHECKED)
report = V43ProductionIntelligenceService().publishing_workflow("project-1", context)

assert report.planning_only is True
assert report.export_workflow.export_performed is False
assert report.distribution.external_delivery_performed is False
print(report.to_json())
