"""Compare a local performance snapshot with an explicit baseline."""

from manga_director.domain.project import Page, Project
from manga_director.observability import MetricsRegistry
from manga_director.production import PerformanceBaseline, ProductionInsights, RepositoryMaintenance
from manga_director.repositories import InMemoryRepository


def main() -> None:
    repository = InMemoryRepository()
    repository.save(Project(id="performance", title="Performance", pages=[Page(page_number=1)]))
    metrics = MetricsRegistry()
    metrics.observe("repository.load.duration_seconds", 0.01)
    report = ProductionInsights(metrics=metrics, maintenance=RepositoryMaintenance(repository)).performance_report(
        baseline=PerformanceBaseline(name="local", averages_seconds={"repository.load.duration_seconds": 0.01})
    )
    print(report.to_markdown())


if __name__ == "__main__":
    main()
