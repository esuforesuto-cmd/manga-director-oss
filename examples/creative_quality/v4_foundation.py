"""Project v4 Creative Quality DTOs without changing review or approval."""

from manga_director.domain.project import Page, Project
from manga_director.production import V4FoundationService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="quality-demo", title="Quality demo", pages=[Page(page_number=1)]))
print(
    V4FoundationService(repository)
    .quality("quality-demo", WorkflowContext(page={"id": "quality-demo-1"}))
    .to_json()
)
