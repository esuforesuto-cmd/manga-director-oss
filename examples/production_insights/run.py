"""Render Production Insights without forecasting, release, or automation."""

from manga_director.production import V32FoundationService, V32InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
service = V32InsightsService(V32FoundationService(repository), repository)
print(
    service.production_insights_dashboard(WorkflowContext(page={"id": "insights-demo-1"})).to_json()
)
