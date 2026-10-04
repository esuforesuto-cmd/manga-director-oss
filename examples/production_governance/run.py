"""Preview Production Governance without enforcement or workflow execution."""

from manga_director.domain.project import Page, Project
from manga_director.production import V33FoundationService, V33GovernanceService, V33InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="governance-demo", title="Governance demo", pages=[Page(page_number=1)]))
foundation = V33FoundationService(repository)
service = V33GovernanceService(foundation, V33InsightsService(foundation, repository), repository)
print(service.production_governance_dashboard("governance-demo", WorkflowContext(page={"id": "governance-demo-1"})).to_json())
