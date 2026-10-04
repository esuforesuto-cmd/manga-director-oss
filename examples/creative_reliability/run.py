"""Render Creative Reliability diagnostics without changing a workflow."""

from manga_director.domain.project import Page, Project
from manga_director.production import V32AssuranceService, V32FoundationService, V32InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="creative-demo", title="Creative demo", pages=[Page(page_number=1)]))
foundation = V32FoundationService(repository)
service = V32AssuranceService(foundation, V32InsightsService(foundation, repository), repository)
print(
    service.creative_reliability_dashboard(
        "creative-demo", WorkflowContext(page={"id": "creative-demo-1"})
    ).to_json()
)
