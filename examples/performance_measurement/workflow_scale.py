"""Measure a provider-free set of one-page workflow transitions."""

import logging
from time import perf_counter

from manga_director import Director, WorkflowContext

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

director = Director.default()
started = perf_counter()
for page_number in range(1, 101):
    director.execute(
        WorkflowContext(page={"project_id": "measurement", "page_id": str(page_number)}),
        "design",
    )
LOGGER.info("workflow_scale_seconds=%.6f", perf_counter() - started)
