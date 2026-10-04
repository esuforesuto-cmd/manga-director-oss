"""Run a read-only Project integrity self-check through the Repository port."""

from manga_director.domain.project import Page, Project
from manga_director.repositories import InMemoryRepository, RepositorySelfCheck


def main() -> None:
    repository = InMemoryRepository()
    repository.save(Project(id="demo", title="Demo", pages=[Page(page_number=1)]))
    print(RepositorySelfCheck(repository).check("demo").model_dump_json(indent=2))


if __name__ == "__main__":
    main()
