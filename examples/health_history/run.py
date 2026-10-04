"""Persist bounded operational health snapshots through the Repository port."""

from manga_director.adapters import LLMProviderRuntime
from manga_director.domain.project import Page, Project
from manga_director.production import HealthHistoryStore, ProviderManagement
from manga_director.repositories import InMemoryRepository


def main() -> None:
    repository = InMemoryRepository()
    repository.save(Project(id="demo", title="Demo", pages=[Page(page_number=1)]))
    history = HealthHistoryStore(repository)
    ProviderManagement(LLMProviderRuntime()).record_health(history, "demo")
    print(history.timeline("demo").to_markdown())


if __name__ == "__main__":
    main()
