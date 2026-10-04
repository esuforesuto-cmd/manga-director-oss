"""Render a non-destructive repository maintenance report."""

from manga_director.domain.project import Page, Project
from manga_director.production import RepositoryMaintenance
from manga_director.repositories import InMemoryRepository


def main() -> None:
    repository = InMemoryRepository()
    repository.save(Project(id="repository", title="Repository", pages=[Page(page_number=1)]))
    print(RepositoryMaintenance(repository).report("repository").to_markdown())


if __name__ == "__main__":
    main()
