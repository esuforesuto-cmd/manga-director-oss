"""Render v3.4 Production Optimization without workflow changes."""

from manga_director.domain.project import Page, Project
from manga_director.production import V34FoundationService, V34InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="production-demo", title="Production demo", pages=[Page(page_number=1)]))
foundation = V34FoundationService(repository)
print(
    V34InsightsService(foundation, repository)
    .production_optimization_dashboard(
        "production-demo", WorkflowContext(page={"id": "production-demo-1"})
    )
    .to_json()
)
