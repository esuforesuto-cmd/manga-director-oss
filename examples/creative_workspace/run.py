"""Render one Creative Workspace analysis DTO without creating tasks."""

from manga_director.domain.project import Page, Project
from manga_director.production import V32FoundationService, V32InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="workspace-demo", title="Workspace demo", pages=[Page(page_number=1)]))
service = V32InsightsService(V32FoundationService(repository), repository)
print(
    service.creative_workspace_dashboard(
        "workspace-demo", WorkflowContext(page={"id": "workspace-demo-1"})
    ).to_json()
)
