"""Render v3.5 Platform Governance evidence without monitoring or external action."""

from manga_director.domain.project import Page, Project
from manga_director.production import V35FoundationService, V35GovernanceService, V35InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="platform-demo", title="Platform demo", pages=[Page(page_number=1)]))
foundation = V35FoundationService(repository)
service = V35GovernanceService(foundation, V35InsightsService(foundation, repository), repository)
print(
    service.platform_governance_dashboard(
        "platform-demo", WorkflowContext(page={"id": "platform-demo-1"})
    ).to_json()
)
