"""Preview v3.3 Quality Analytics without scoring or approval."""

from manga_director.domain.project import Page, Project
from manga_director.production import V33FoundationService, V33InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="quality-demo", title="Quality demo", pages=[Page(page_number=1)]))
service = V33InsightsService(V33FoundationService(repository), repository)
print(service.quality_analytics_dashboard(WorkflowContext(page={"id": "quality-demo-1"})).to_json())
