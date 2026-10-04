"""Render v3.5 Executive Analytics without external collection or release authority."""

from manga_director.domain.project import Page, Project
from manga_director.production import V35FoundationService, V35InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="executive-demo", title="Executive demo", pages=[Page(page_number=1)]))
foundation = V35FoundationService(repository)
print(
    V35InsightsService(foundation, repository)
    .executive_analytics_dashboard("executive-demo", WorkflowContext(page={"id": "executive-demo-1"}))
    .to_json()
)
