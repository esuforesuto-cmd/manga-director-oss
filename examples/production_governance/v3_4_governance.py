"""Render v3.4 Production Governance without pipeline modification."""

from manga_director.domain.project import Page, Project
from manga_director.production import V34FoundationService, V34GovernanceService, V34InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(
    Project(id="production-governance", title="Production governance", pages=[Page(page_number=1)])
)
foundation = V34FoundationService(repository)
insights = V34InsightsService(foundation, repository)
print(
    V34GovernanceService(foundation, insights, repository)
    .production_governance_dashboard(
        "production-governance", WorkflowContext(page={"id": "production-1"})
    )
    .to_json()
)
