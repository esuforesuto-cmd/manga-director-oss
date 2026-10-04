"""Render v3.5 Creative Intelligence evidence without generating content."""

from manga_director.domain.project import Page, Project
from manga_director.production import V35FoundationService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="creative-demo", title="Creative demo", pages=[Page(page_number=1)]))
report = V35FoundationService(repository).creative_intelligence_dashboard(
    "creative-demo", WorkflowContext(page={"id": "creative-demo-1"})
)
print(report.to_json())
