from manga_director.domain.project import Chapter, Page, Project
from manga_director.repositories import InMemoryRepository, RepositoryScalability


def _project() -> Project:
    return Project(
        id="scalable-project",
        title="Scalable",
        chapters=[Chapter(id="chapter-1", title="One", page_numbers=[1, 2])],
        pages=[
            Page(page_number=1, history=[{"step": "Draft"}, {"step": "Designed"}]),
            Page(page_number=2, history=[{"step": "Draft"}]),
        ],
        metadata={"genre": "drama", "audience": "all"},
        workflow={"snapshot_v1": {"completed": 1}},
    )


def test_repository_scalability_indexes_and_paginates_history() -> None:
    repository = InMemoryRepository()
    project = _project()
    repository.save(project)
    scalability = RepositoryScalability(repository)

    assert scalability.chapter_index(project.id) == {"chapter-1": (1, 2)}
    assert scalability.page_index(project.id) == {1: "Draft", 2: "Draft"}
    assert scalability.metadata_cache(project.id) == ("audience", "genre")
    assert scalability.snapshot_index(project.id) == ("snapshot_v1",)

    history = scalability.history_page(project.id, 1, offset=1, limit=1)
    assert history.total == 2
    assert history.entries == ({"step": "Designed"},)
    assert scalability.scan(project.id).history_entries == 3


def test_repository_scalability_cache_is_explicitly_invalidatable_and_scans_in_batches() -> None:
    repository = InMemoryRepository()
    project = _project()
    repository.save(project)
    scalability = RepositoryScalability(repository)

    first = scalability.project_index(project.id)
    assert first is scalability.project_index(project.id)
    scalability.invalidate(project.id)
    assert first is not scalability.project_index(project.id)
    assert list(scalability.iter_projects(batch_size=1)) == [(project,)]
