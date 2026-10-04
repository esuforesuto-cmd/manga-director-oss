"""Smallest in-memory workflow example."""

import logging

from manga_director import Director, WorkflowContext

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

director = Director.default()
result = director.execute(WorkflowContext(page={"project_id": "demo", "page_id": "1"}), "design")
LOGGER.info("Current state: %s", result.current_state.value)
