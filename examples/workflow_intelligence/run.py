"""Render StateMachine-based Workflow Intelligence without a transition."""

from manga_director.production import V32FoundationService, V32InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
service = V32InsightsService(V32FoundationService(repository), repository)
print(
    service.workflow_intelligence_dashboard(
        WorkflowContext(page={"id": "workflow-demo-1"})
    ).to_json()
)
