"""Use the Repository interface through the built-in SQLite adapter."""

import logging

from manga_director import Page, Project
from manga_director.repositories import SQLiteRepository

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

repository = SQLiteRepository()
repository.create_schema()
repository.save(Project(id="database-demo", title="Database Demo", pages=[Page(page_number=1)]))

LOGGER.info("loaded project=%s", repository.load("database-demo").title)
