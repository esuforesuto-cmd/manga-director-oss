"""Render a one-page workspace dashboard without persisting a layout."""

from manga_director.domain.project import Page, Project
from manga_director.production import V32FoundationService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="dashboard-demo", title="Dashboard demo", pages=[Page(page_number=1)]))
dashboard = V32FoundationService(repository).creative_studio_dashboard(
    "dashboard-demo", WorkflowContext(page={"id": "dashboard-demo-1"})
)
print(dashboard.to_json())
