"""Prepare observability evidence without telemetry or monitoring."""

from manga_director.domain.state_machine import PageState
from manga_director.production.v4_2_autonomous_operations import V42AutonomousOperationsService
from manga_director.workflow import WorkflowContext

context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
report = V42AutonomousOperationsService().observability("project-1", context)

assert report.planning_only is True
assert report.metrics.metric_collection_active is False
assert report.trace.trace_recorded is False
assert report.dashboard.monitoring_active is False
print(report.to_json())
