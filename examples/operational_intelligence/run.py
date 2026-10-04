"""Render operational diagnostics without deployment or runtime automation."""

from manga_director.production import V32AssuranceService, V32FoundationService, V32InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
foundation = V32FoundationService(repository)
service = V32AssuranceService(foundation, V32InsightsService(foundation, repository), repository)
print(
    service.operational_intelligence_dashboard(
        WorkflowContext(page={"id": "operations-demo-1"})
    ).to_json()
)
