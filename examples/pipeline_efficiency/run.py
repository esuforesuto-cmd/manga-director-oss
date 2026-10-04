"""Inspect v3.3 pipeline efficiency evidence without applying optimization."""

from manga_director.domain.project import Page, Project
from manga_director.production import V33FoundationService, V33InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="efficiency-demo", title="Efficiency demo", pages=[Page(page_number=1)]))
service = V33InsightsService(V33FoundationService(repository), repository)
print(service.production_intelligence_dashboard("efficiency-demo", WorkflowContext(page={"id": "efficiency-demo-1"})).to_json())
