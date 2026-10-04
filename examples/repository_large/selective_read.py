"""Use optional selective repository reads for a large Project."""

import logging

from manga_director import Page, Project
from manga_director.repositories import SQLiteRepository

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

repository = SQLiteRepository()
repository.create_schema()
project = Project(
    id="selective-read-demo",
    title="Selective Read Demo",
    pages=[
        Page(page_number=number, history=[{"step": "Draft", "sequence": event} for event in range(4)])
        for number in range(1, 241)
    ],
)
repository.save(project)

metadata = repository.list_metadata(limit=1)[0]
page = repository.load_page(project.id, 120)
history = repository.load_history(project.id, 120, limit=2)
LOGGER.info(
    "project=%s pages=%s page=%s history_entries=%s",
    metadata.id,
    metadata.page_count,
    page.page_number,
    len(history),
)
