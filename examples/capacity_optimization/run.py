"""Preview v3.4 capacity recommendations without allocation."""

from manga_director.domain.project import Page, Project
from manga_director.production import V34FoundationService, V34InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="capacity-demo", title="Capacity demo", pages=[Page(page_number=1)]))
foundation = V34FoundationService(repository)
report = V34InsightsService(foundation, repository).production_optimization(
    "capacity-demo", WorkflowContext(page={"id": "capacity-demo-1"})
)
print(report.capacity.to_json())
