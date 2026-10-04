from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from manga_director.domain.events import WorkflowEvent
from manga_director.domain.state_machine import PageState


class WorkflowContext(BaseModel):
    """The complete, transport-independent context shared by one page workflow."""

    model_config = ConfigDict(frozen=True)

    page: dict[str, Any] = Field(default_factory=dict)
    state: PageState = PageState.DRAFT
    events: list[WorkflowEvent] = Field(default_factory=list)
    artifacts: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def advance(
        self,
        *,
        state: PageState,
        events: list[WorkflowEvent],
        artifact_name: str,
        payload: dict[str, Any],
    ) -> WorkflowContext:
        artifacts = dict(self.artifacts)
        artifacts[artifact_name] = payload
        metadata = dict(self.metadata)
        history = list(metadata.get("workflow_history", []))
        history.append(
            {
                "kind": "workflow",
                "from": self.state.value,
                "to": state.value,
                "step": artifact_name,
            }
        )
        metadata["workflow_history"] = history
        metadata["current_step"] = artifact_name
        # Existing artifact values are immutable-by-convention workflow history;
        # copy only the containers this transition changes rather than every page artifact.
        return self.model_copy(
            update={
                "state": state,
                "events": [*self.events, *events],
                "artifacts": artifacts,
                "metadata": metadata,
            },
            deep=False,
        )

    def add_support_result(
        self,
        *,
        name: str,
        payload: dict[str, Any],
        events: list[WorkflowEvent],
    ) -> WorkflowContext:
        artifacts = dict(self.artifacts)
        artifacts[f"support:{name}"] = payload
        metadata = dict(self.metadata)
        history = list(metadata.get("workflow_history", []))
        history.append({"kind": "support", "step": name, "state": self.state.value})
        metadata["workflow_history"] = history
        metadata["current_step"] = name
        return self.model_copy(
            update={
                "events": [*self.events, *events],
                "artifacts": artifacts,
                "metadata": metadata,
            },
            deep=False,
        )


class AgentResult(BaseModel):
    """The uniform typed result returned by every workflow agent."""

    model_config = ConfigDict(frozen=True)

    success: bool
    state: PageState
    payload: dict[str, Any] = Field(default_factory=dict)
    events: list[WorkflowEvent] = Field(default_factory=list)
    messages: list[str] = Field(default_factory=list)


class Agent(Protocol):
    def execute(self, context: WorkflowContext) -> AgentResult: ...


class WorkflowResult(BaseModel):
    """The result of exactly one completed workflow step."""

    model_config = ConfigDict(frozen=True)

    current_state: PageState
    completed_step: PageState | str
    events: list[WorkflowEvent] = Field(default_factory=list)
    logs: list[str] = Field(default_factory=list)
    context: WorkflowContext


class WorkflowStatus(BaseModel):
    """Read-only workflow status derived by WorkflowEngine for delivery adapters."""

    model_config = ConfigDict(frozen=True)

    current_state: PageState
    current_step: str | None
    completed_steps: list[str] = Field(default_factory=list)
    executable_step: str | None
    workflow_history: list[dict[str, Any]] = Field(default_factory=list)
