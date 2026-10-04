"""Run one page through quality, then record human approval."""

import logging

from manga_director import Director, WorkflowContext

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

director = Director.default()
context = WorkflowContext(page={"project_id": "demo", "page_id": "1"})
quality_result = director.run(context)[-1]
approved_context = quality_result.context.model_copy(
    update={"metadata": {**quality_result.context.metadata, "approved_by": "editor"}},
    deep=True,
)
approval_result = director.execute(approved_context, "approve")
LOGGER.info("Final state: %s", approval_result.current_state.value)
