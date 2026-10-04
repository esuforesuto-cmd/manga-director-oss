"""Preview v3.4 Production Operations without monitoring or deployment."""

from manga_director.domain.project import Page, Project
from manga_director.production import V34FoundationService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="operations-demo", title="Operations demo", pages=[Page(page_number=1)]))
report = V34FoundationService(repository).production_operations_dashboard(
    "operations-demo", WorkflowContext(page={"id": "operations-demo-1"})
)
print(report.to_json())
