"""Use bounded history reads without changing the repository port."""

from manga_director.domain.project import Page, Project
from manga_director.repositories import InMemoryRepository, RepositoryScalability

repository = InMemoryRepository()
repository.save(Project(id="example", title="Large project", pages=[Page(page_number=1)]))
scalability = RepositoryScalability(repository)
print(scalability.scan("example").model_dump())
