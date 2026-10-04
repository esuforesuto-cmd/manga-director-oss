"""Render a diagnostic-only performance baseline comparison and trend."""

from manga_director.domain.project import Page, Project
from manga_director.observability import MetricsRegistry
from manga_director.production import PerformanceBaseline, ProductionInsights, RepositoryMaintenance
from manga_director.repositories import InMemoryRepository


def main() -> None:
    repository = InMemoryRepository()
    repository.save(Project(id="baseline", title="Baseline", pages=[Page(page_number=1)]))
    metrics = MetricsRegistry()
    metrics.observe("workflow.step.duration_seconds", 0.02)
    report = ProductionInsights(metrics=metrics, maintenance=RepositoryMaintenance(repository)).performance_report(
        baseline=PerformanceBaseline(name="local", averages_seconds={"workflow.step.duration_seconds": 0.01}),
        history={"workflow.step.duration_seconds": [0.01, 0.015, 0.02]},
    )
    print(report.to_markdown())


if __name__ == "__main__":
    main()
