"""Measure one provider-free workflow operation as a local smoke sample."""

import logging
from time import perf_counter

from manga_director import Director, WorkflowContext

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

started = perf_counter()
Director.default().execute(WorkflowContext(page={"project_id": "performance", "page_id": "1"}), "design")
LOGGER.info("workflow smoke elapsed_seconds=%.6f", perf_counter() - started)
