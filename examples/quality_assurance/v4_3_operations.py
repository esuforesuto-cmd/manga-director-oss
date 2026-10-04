"""Preview v4.3 quality assurance without evaluation, remediation, or approval."""

from manga_director.domain.state_machine import PageState
from manga_director.production import V43ProductionOperationsService
from manga_director.workflow import WorkflowContext

context = WorkflowContext(page={"id": "page-1"}, state=PageState.PROMPT_BUILT)
report = V43ProductionOperationsService().quality_assurance("project-1", context)

assert report.planning_only is True
assert report.rule.rule_evaluated is False
assert report.checklist.approval_granted is False
print(report.to_json())
