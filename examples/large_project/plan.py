"""Plan a multi-chapter Project without changing one-page execution semantics."""

import logging

from manga_director.domain.project import Chapter, Page, Project
from manga_director.workflow import ExecutionPlanner, SequentialExecution

project = Project(
    id="planning-demo",
    title="Large Project Planning",
    chapters=[
        Chapter(id="chapter-1", title="Opening", page_numbers=[1, 2]),
        Chapter(id="chapter-2", title="Turning Point", page_numbers=[3, 4]),
    ],
    pages=[Page(page_number=number) for number in range(1, 5)],
)

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

batch = ExecutionPlanner().plan(project, SequentialExecution(), batch_id="planning-demo")
LOGGER.info("planned pages=%s", [(item.chapter_id, item.page_number) for item in batch.queue])
