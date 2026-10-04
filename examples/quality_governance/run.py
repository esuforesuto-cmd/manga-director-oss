"""Preview Quality Governance without scoring or approval authority."""

from manga_director.domain.project import Page, Project
from manga_director.production import V33FoundationService, V33GovernanceService, V33InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="quality-governance", title="Quality governance", pages=[Page(page_number=1)]))
foundation = V33FoundationService(repository)
service = V33GovernanceService(foundation, V33InsightsService(foundation, repository), repository)
print(service.quality_governance_dashboard(WorkflowContext(page={"id": "quality-governance-1"})).to_json())
