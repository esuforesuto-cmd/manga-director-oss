"""Render redacted Asset Governance diagnostics without asset management."""

from manga_director.domain.project import Project
from manga_director.production import V32AssuranceService, V32FoundationService, V32InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(
    Project(id="asset-demo", title="Asset demo", metadata={"reference": {"name": "map"}})
)
foundation = V32FoundationService(repository)
service = V32AssuranceService(foundation, V32InsightsService(foundation, repository), repository)
print(
    service.asset_governance_dashboard(
        "asset-demo", WorkflowContext(page={"id": "asset-demo-1"})
    ).to_json()
)
