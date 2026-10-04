"""Render v3.4 Release Governance without release authority."""

from manga_director.domain.project import Page, Project
from manga_director.production import V34FoundationService, V34GovernanceService, V34InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(
    Project(id="release-governance", title="Release governance", pages=[Page(page_number=1)])
)
foundation = V34FoundationService(repository)
insights = V34InsightsService(foundation, repository)
print(
    V34GovernanceService(foundation, insights, repository)
    .release_governance_dashboard("release-governance", WorkflowContext(page={"id": "release-1"}))
    .to_json()
)
