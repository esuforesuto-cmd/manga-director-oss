"""Render v3.5 Creative Analytics without generation or approval."""

from manga_director.domain.project import Page, Project
from manga_director.production import V35FoundationService, V35InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="creative-demo", title="Creative demo", pages=[Page(page_number=1)]))
foundation = V35FoundationService(repository)
print(
    V35InsightsService(foundation, repository)
    .creative_analytics_dashboard("creative-demo", WorkflowContext(page={"id": "creative-demo-1"}))
    .to_json()
)
