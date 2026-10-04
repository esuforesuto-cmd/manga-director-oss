"""Inspect an in-memory Project before allowing an operator to resume it."""

import logging

from manga_director.domain.project import Page, Project
from manga_director.repositories import InMemoryRepository, RepositoryRecovery

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

repository = InMemoryRepository()
repository.save(Project(id="recovery-demo", title="Recovery", pages=[Page(page_number=1)]))
report = RepositoryRecovery(repository).validate_for_resume("recovery-demo")
LOGGER.info("%s", report.model_dump(mode="json"))
