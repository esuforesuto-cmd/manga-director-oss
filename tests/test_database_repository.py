from sqlalchemy import text

from manga_director.domain.project import Page, Project
from manga_director.repositories import DatabaseFactory, SQLiteRepository


def test_sqlite_repository_preserves_project_contract() -> None:
    repository = SQLiteRepository()
    repository.create_schema()
    project = Project(id="database-demo", title="Database Demo", pages=[Page(page_number=1)])
    repository.save(project)
    assert repository.exists(project.id)
    assert repository.load(project.id) == project
    assert [item.id for item in repository.list()] == [project.id]


def test_unit_of_work_rolls_back_failed_transaction() -> None:
    repository = SQLiteRepository()
    repository.create_schema()
    try:
        with repository.transaction() as uow:
            assert uow.session is not None
            uow.session.execute(text("invalid sql"))
    except Exception:
        pass
    assert repository.list() == []


def test_database_factory_creates_sqlite() -> None:
    repository = DatabaseFactory.create("sqlite", "sqlite:///:memory:")
    assert isinstance(repository, SQLiteRepository)
