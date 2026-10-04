"""Render a Pipeline bottleneck projection without applying a profile."""

from manga_director.production import V32FoundationService, V32InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
service = V32InsightsService(V32FoundationService(repository), repository)
print(
    service.workflow_intelligence_dashboard(
        WorkflowContext(page={"id": "pipeline-demo-1"})
    ).report.bottleneck.to_json()
)
