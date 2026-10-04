"""Render a preview without executing the recommended `design` command."""

from manga_director.domain.state_machine import PageState
from manga_director.production import WorkflowPlanner
from manga_director.workflow import WorkflowContext

preview = WorkflowPlanner().execution_preview(
    WorkflowContext(page={"id": "example-page"}, state=PageState.DRAFT)
)
print(preview.to_json())
