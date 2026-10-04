"""Render v3.4 Knowledge Intelligence without writes or remote search."""

from manga_director.domain.project import Page, Project
from manga_director.production import V34FoundationService, V34InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="knowledge-demo", title="Knowledge demo", pages=[Page(page_number=1)]))
foundation = V34FoundationService(repository)
print(
    V34InsightsService(foundation, repository)
    .knowledge_intelligence_dashboard(
        "knowledge-demo", WorkflowContext(page={"id": "knowledge-demo-1"})
    )
    .to_json()
)
