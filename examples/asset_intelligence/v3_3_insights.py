"""Preview v3.3 redacted Asset Intelligence without repository mutation."""

from manga_director.domain.project import Page, Project
from manga_director.production import V33FoundationService, V33InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="asset-demo", title="Asset demo", pages=[Page(page_number=1)]))
service = V33InsightsService(V33FoundationService(repository), repository)
print(service.asset_intelligence_dashboard("asset-demo", WorkflowContext(page={"id": "asset-demo-1"})).to_json())
