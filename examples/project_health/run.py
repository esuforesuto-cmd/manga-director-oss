"""Preview Project Health evidence without changing a Project."""

from manga_director.domain.project import Page, Project
from manga_director.production import V33FoundationService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="project-health-demo", title="Project health demo", pages=[Page(page_number=1)]))
report = V33FoundationService(repository).project_intelligence_dashboard(
    "project-health-demo", WorkflowContext(page={"id": "project-health-demo-1"})
)
print(report.report.health.model_dump_json())
