"""Render v3.5 Platform Analytics evidence without remote collection."""

from manga_director.domain.project import Page, Project
from manga_director.production import V35FoundationService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="analytics-demo", title="Analytics demo", pages=[Page(page_number=1)]))
report = V35FoundationService(repository).platform_analytics_dashboard(
    "analytics-demo", WorkflowContext(page={"id": "analytics-demo-1"})
)
print(report.to_json())
