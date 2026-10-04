"""Render v3.5 Production Intelligence evidence without scheduling work."""

from manga_director.domain.project import Page, Project
from manga_director.production import V35FoundationService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="production-demo", title="Production demo", pages=[Page(page_number=1)]))
report = V35FoundationService(repository).production_intelligence_dashboard(
    "production-demo", WorkflowContext(page={"id": "production-demo-1"})
)
print(report.to_json())
