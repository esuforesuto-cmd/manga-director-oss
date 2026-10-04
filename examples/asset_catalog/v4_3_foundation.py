"""Preview a v4.3 asset-catalog DTO report without asset mutation."""

from manga_director.domain.state_machine import PageState
from manga_director.production import V43ProductionFoundationService
from manga_director.workflow import WorkflowContext

context = WorkflowContext(
    page={"id": "page-1"},
    state=PageState.DRAFT,
    artifacts={"storyboard": {"panels": []}},
    metadata={"source": "human"},
)
report = V43ProductionFoundationService().asset_management("project-1", context)

assert report.planning_only is True
assert report.asset.asset_created is False
assert report.summary.distribution_enabled is False
print(report.to_json())
