"""Preview a v4.3 production-pipeline DTO report without workflow execution."""

from manga_director.domain.state_machine import PageState
from manga_director.production import V43ProductionFoundationService
from manga_director.workflow import WorkflowContext

context = WorkflowContext(
    page={"id": "page-1", "storyboard": {"panels": []}},
    state=PageState.PROMPT_BUILT,
    artifacts={"storyboard": {"panels": []}},
)
report = V43ProductionFoundationService().production_pipeline("project-1", context)

assert report.planning_only is True
assert report.project.page_count == 1
assert report.stage.stage_started is False
print(report.to_json())
