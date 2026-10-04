"""Render v3.4 Organization Analytics without personnel action."""

from manga_director.domain.project import Page, Project
from manga_director.production import V34FoundationService, V34InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(
    Project(id="organization-demo", title="Organization demo", pages=[Page(page_number=1)])
)
foundation = V34FoundationService(repository)
print(
    V34InsightsService(foundation, repository)
    .organization_analytics_dashboard(
        "organization-demo", WorkflowContext(page={"id": "organization-demo-1"})
    )
    .to_json()
)
