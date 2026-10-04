"""Project v4 Creative Memory DTOs without creating a memory store."""

from manga_director.domain.project import Page, Project
from manga_director.production import V4FoundationService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="memory-demo", title="Memory demo", pages=[Page(page_number=1)]))
print(
    V4FoundationService(repository)
    .memory("memory-demo", WorkflowContext(page={"id": "memory-demo-1"}))
    .to_json()
)
