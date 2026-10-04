"""Render the v3.5 local Platform Health DTO without starting monitoring."""

from manga_director.domain.project import Page, Project
from manga_director.production import V35FoundationService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="health-demo", title="Health demo", pages=[Page(page_number=1)]))
report = V35FoundationService(repository).platform_analytics(
    "health-demo", WorkflowContext(page={"id": "health-demo-1"})
)
print(report.health.to_json())
