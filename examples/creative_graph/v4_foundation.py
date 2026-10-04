"""Project v4 Creative Graph DTOs without persisting or repairing a graph."""

from manga_director.domain.project import Page, Project
from manga_director.production import V4FoundationService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="graph-demo", title="Graph demo", pages=[Page(page_number=1)]))
print(
    V4FoundationService(repository)
    .graph("graph-demo", WorkflowContext(page={"id": "graph-demo-1"}))
    .to_json()
)
