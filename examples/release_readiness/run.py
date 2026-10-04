"""Render release evidence without release authorization or publication."""

from manga_director.production import V32AssuranceService, V32FoundationService, V32InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
foundation = V32FoundationService(repository)
service = V32AssuranceService(foundation, V32InsightsService(foundation, repository), repository)
print(service.release_readiness_dashboard(WorkflowContext(page={"id": "release-demo-1"})).to_json())
