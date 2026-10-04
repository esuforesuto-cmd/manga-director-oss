"""Check a Project aggregate through the repository port."""

from manga_director.domain.project import Page, Project
from manga_director.repositories import InMemoryRepository, RepositorySelfCheck

repository = InMemoryRepository()
repository.save(Project(id="checked", title="Checked", pages=[Page(page_number=1)]))
print(RepositorySelfCheck(repository).check("checked").model_dump())
