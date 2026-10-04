"""Preview Quality Intelligence DTOs without scoring or approval."""

from manga_director.domain.project import Page, Project
from manga_director.production import V33FoundationService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="quality-demo", title="Quality demo", pages=[Page(page_number=1)]))
report = V33FoundationService(repository).quality_intelligence_dashboard(
    WorkflowContext(page={"id": "quality-demo-1"})
)
print(report.to_json())
