"""Project a v4 Workspace Foundation DTO without creating a workspace."""

from manga_director.domain.project import Page, Project
from manga_director.production import V4FoundationService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="workspace-demo", title="Workspace demo", pages=[Page(page_number=1)]))
print(
    V4FoundationService(repository)
    .workspace("workspace-demo", WorkflowContext(page={"id": "workspace-demo-1"}))
    .to_json()
)
