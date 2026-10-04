"""Render v3.5 Knowledge Analytics without graph mutation or recommendation application."""

from manga_director.domain.project import Page, Project
from manga_director.production import V35FoundationService, V35InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="insight-demo", title="Insight demo", pages=[Page(page_number=1)]))
foundation = V35FoundationService(repository)
print(
    V35InsightsService(foundation, repository)
    .knowledge_insights_dashboard("insight-demo", WorkflowContext(page={"id": "insight-demo-1"}))
    .to_json()
)
