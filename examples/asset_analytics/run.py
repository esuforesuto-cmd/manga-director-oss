"""Render redacted Asset Analytics without creating an asset index."""

from manga_director.domain.project import Project
from manga_director.production import V32FoundationService, V32InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(
    Project(id="asset-demo", title="Asset demo", metadata={"reference": {"name": "map"}})
)
service = V32InsightsService(V32FoundationService(repository), repository)
print(
    service.asset_analytics_dashboard(
        "asset-demo", WorkflowContext(page={"id": "asset-demo-1"})
    ).to_json()
)
