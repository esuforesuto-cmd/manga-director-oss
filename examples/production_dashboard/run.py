"""Render v3.5 Production Analytics without scheduling or deployment."""

from manga_director.domain.project import Page, Project
from manga_director.production import V35FoundationService, V35InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="production-demo", title="Production demo", pages=[Page(page_number=1)]))
foundation = V35FoundationService(repository)
print(
    V35InsightsService(foundation, repository)
    .production_analytics_dashboard("production-demo", WorkflowContext(page={"id": "production-demo-1"}))
    .to_json()
)
