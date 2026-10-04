"""Preview v3.3 Production Intelligence without running a workflow."""

from manga_director.domain.project import Page, Project
from manga_director.production import V33FoundationService, V33InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="production-demo", title="Production demo", pages=[Page(page_number=1)]))
service = V33InsightsService(V33FoundationService(repository), repository)
print(service.production_intelligence_dashboard("production-demo", WorkflowContext(page={"id": "production-demo-1"})).to_json())
