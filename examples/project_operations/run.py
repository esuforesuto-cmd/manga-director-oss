"""Preview v3.3 Project Operations without allocation or scheduling."""

from manga_director.domain.project import Page, Project
from manga_director.production import V33FoundationService, V33InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="operations-demo", title="Operations demo", pages=[Page(page_number=1)]))
service = V33InsightsService(V33FoundationService(repository), repository)
print(service.project_operations_dashboard("operations-demo", WorkflowContext(page={"id": "operations-demo-1"})).to_json())
