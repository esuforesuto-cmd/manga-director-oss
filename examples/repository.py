"""Persist a Project aggregate through the repository contract."""

import logging

from manga_director import Page, Project
from manga_director.repositories import InMemoryRepository

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

repository = InMemoryRepository()
project = Project(id="demo", title="Demo Manga", pages=[Page(page_number=1)])
repository.save(project)
LOGGER.info("Saved projects: %s", [item.id for item in repository.list()])
