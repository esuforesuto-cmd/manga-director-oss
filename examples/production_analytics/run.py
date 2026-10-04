"""Render analysis-only Production Analytics for one existing workflow context."""

from manga_director.production import V32FoundationService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

report = V32FoundationService(InMemoryRepository()).production_analytics_dashboard(
    WorkflowContext(page={"id": "analytics-demo-1"})
)
print(report.to_json())
