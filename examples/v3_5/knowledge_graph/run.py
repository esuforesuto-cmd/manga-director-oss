"""Render a v3.5 Knowledge Graph dashboard without persisting a graph."""

from manga_director.domain.project import Page, Project
from manga_director.production import V35FoundationService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="graph-demo", title="Graph demo", pages=[Page(page_number=1)]))
report = V35FoundationService(repository).knowledge_graph_dashboard(
    "graph-demo", WorkflowContext(page={"id": "graph-demo-1"})
)
print(report.to_json())
