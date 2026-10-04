"""Render release health evidence without release authority."""

from manga_director.domain.project import Page, Project
from manga_director.production import V34FoundationService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="health-demo", title="Health demo", pages=[Page(page_number=1)]))
report = V34FoundationService(repository).release_intelligence(
    "health-demo", WorkflowContext(page={"id": "health-demo-1"})
)
print(report.health.to_json())
