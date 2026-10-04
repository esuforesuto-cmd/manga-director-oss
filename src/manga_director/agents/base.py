from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from manga_director.domain.events import WorkflowEvent
from manga_director.domain.state_machine import PageState
from manga_director.workflow.contracts import AgentResult, WorkflowContext


class BaseAgent(ABC):
    """Stateless base class for all commercial manga production agents."""

    target_state: PageState

    @abstractmethod
    def execute(self, context: WorkflowContext) -> AgentResult:
        """Transform the supplied context without mutating it or invoking another agent."""
        raise NotImplementedError

    def result(
        self,
        *,
        payload: dict[str, Any],
        messages: list[str],
        events: list[WorkflowEvent] | None = None,
    ) -> AgentResult:
        return AgentResult(
            success=True,
            state=self.target_state,
            payload=payload,
            events=events or [],
            messages=messages,
        )
