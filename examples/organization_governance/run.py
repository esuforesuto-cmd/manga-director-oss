"""Render v3.4 Organization Governance without personnel action."""

from manga_director.domain.project import Page, Project
from manga_director.production import V34FoundationService, V34GovernanceService, V34InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(
    Project(
        id="organization-governance", title="Organization governance", pages=[Page(page_number=1)]
    )
)
foundation = V34FoundationService(repository)
insights = V34InsightsService(foundation, repository)
print(
    V34GovernanceService(foundation, insights, repository)
    .organization_governance_dashboard(
        "organization-governance", WorkflowContext(page={"id": "organization-1"})
    )
    .to_json()
)
