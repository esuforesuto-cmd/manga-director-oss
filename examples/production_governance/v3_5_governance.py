"""Render v3.5 Production Governance evidence without scheduling or deployment."""

from manga_director.domain.project import Page, Project
from manga_director.production import V35FoundationService, V35GovernanceService, V35InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="production-demo", title="Production demo", pages=[Page(page_number=1)]))
foundation = V35FoundationService(repository)
service = V35GovernanceService(foundation, V35InsightsService(foundation, repository), repository)
print(
    service.production_governance_dashboard(
        "production-demo", WorkflowContext(page={"id": "production-demo-1"})
    ).to_json()
)
