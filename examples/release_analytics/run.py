"""Render v3.4 Release Analytics without deployment or publication."""

from manga_director.domain.project import Page, Project
from manga_director.production import V34FoundationService, V34InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="release-demo", title="Release demo", pages=[Page(page_number=1)]))
foundation = V34FoundationService(repository)
print(
    V34InsightsService(foundation, repository)
    .release_analytics_dashboard("release-demo", WorkflowContext(page={"id": "release-demo-1"}))
    .to_json()
)
