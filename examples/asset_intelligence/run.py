"""Preview redacted Asset Intelligence; no assets or indexes are written."""

from manga_director.domain.project import Project
from manga_director.production import V32FoundationService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(
    Project(id="asset-demo", title="Asset demo", metadata={"reference": {"name": "map"}})
)
report = V32FoundationService(repository).asset_intelligence_dashboard(
    "asset-demo",
    WorkflowContext(page={"id": "asset-demo-1"}, artifacts={"storyboard": {"panels": []}}),
)
print(report.to_json())
