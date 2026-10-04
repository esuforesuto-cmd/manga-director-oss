"""Preview Asset Governance without retention or Repository mutation."""

from manga_director.domain.project import Page, Project
from manga_director.production import V33FoundationService, V33GovernanceService, V33InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="asset-governance", title="Asset governance", pages=[Page(page_number=1)]))
foundation = V33FoundationService(repository)
service = V33GovernanceService(foundation, V33InsightsService(foundation, repository), repository)
print(service.asset_governance_dashboard("asset-governance", WorkflowContext(page={"id": "asset-governance-1"})).to_json())
