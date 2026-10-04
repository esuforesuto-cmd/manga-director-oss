"""Preview a v4.3 asset-intelligence report without asset mutation."""

from manga_director.domain.state_machine import PageState
from manga_director.production import V43ProductionIntelligenceService
from manga_director.workflow import WorkflowContext

context = WorkflowContext(
    page={"id": "page-1"},
    state=PageState.DRAFT,
    artifacts={"storyboard": {}},
    metadata={"provenance": "human"},
)
report = V43ProductionIntelligenceService().asset_intelligence("project-1", context)

assert report.planning_only is True
assert report.dependency_analysis.resolution_applied is False
assert report.duplicates.asset_deleted is False
print(report.to_json())
