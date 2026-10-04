"""Prepare a pipeline definition without starting or dispatching a stage."""

from manga_director.domain.state_machine import PageState
from manga_director.production.v4_2_autonomous_workflow import V42AutonomousWorkflowService
from manga_director.workflow import WorkflowContext

context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
report = V42AutonomousWorkflowService().pipeline_automation("project-1", context)

assert report.planning_only is True
assert report.definition.execution_enabled is False
assert report.stage.stage_started is False
assert report.rule.automatic_dispatch_enabled is False
print(report.to_json())
