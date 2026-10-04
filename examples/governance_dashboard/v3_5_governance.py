"""Render the v3.5 Knowledge Governance dashboard without enforcing a policy."""

from manga_director.domain.project import Page, Project
from manga_director.production import V35FoundationService, V35GovernanceService, V35InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="governance-demo", title="Governance demo", pages=[Page(page_number=1)]))
foundation = V35FoundationService(repository)
service = V35GovernanceService(foundation, V35InsightsService(foundation, repository), repository)
print(
    service.knowledge_governance_dashboard(
        "governance-demo", WorkflowContext(page={"id": "governance-demo-1"})
    ).to_json()
)
