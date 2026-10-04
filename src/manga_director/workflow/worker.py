"""Default Worker adapter that delegates a single page to WorkflowEngine."""

from __future__ import annotations

from manga_director.workflow.contracts import WorkflowContext, WorkflowResult
from manga_director.workflow.engine import WorkflowEngine


class WorkflowWorker:
    """Run one page through the existing engine; no Agent is exposed to this layer."""

    def __init__(self, engine: WorkflowEngine) -> None:
        self._engine = engine

    def run(self, page_context: WorkflowContext) -> WorkflowResult:
        results = self._engine.run(page_context)
        if results:
            return results[-1]
        return WorkflowResult(
            current_state=page_context.state,
            completed_step="none",
            logs=["page workflow already at an automatic stopping point"],
            context=page_context,
        )
