"""v4.1 multi-agent foundation DTOs with no execution or workflow authority.

This module is deliberately separate from the existing workflow-agent registry.
It describes registered agents and collaboration evidence only: it neither
invokes an agent nor dispatches, transports, persists, or approves work.  All
workflow transitions remain the responsibility of the existing StateMachine.
"""

from __future__ import annotations

from pydantic import Field

from manga_director.domain.state_machine import PageState
from manga_director.production.director import DirectorModel
from manga_director.workflow.contracts import WorkflowContext


class CapabilityDTO(DirectorModel):
    """A declared, non-executable capability for an agent profile."""

    capability_id: str
    name: str
    description: str
    execution_enabled: bool = False
    model_invocation_enabled: bool = False


class RoleDTO(DirectorModel):
    """Human-governed responsibility boundary for a registered agent."""

    role_id: str
    name: str
    responsibilities: tuple[str, ...] = ()
    may_approve_page: bool = False
    owns_workflow_state: bool = False


class AgentProfileDTO(DirectorModel):
    profile_id: str
    display_name: str
    role: RoleDTO
    capabilities: tuple[CapabilityDTO, ...] = ()
    lifecycle: str = "defined"
    profile_persisted: bool = False


class AgentDTO(DirectorModel):
    agent_id: str
    profile: AgentProfileDTO
    availability: str = "declared"
    execution_enabled: bool = False
    automatic_action_taken: bool = False


class AgentRegistrySnapshotDTO(DirectorModel):
    agents: tuple[AgentDTO, ...] = ()
    registry_persisted: bool = False
    repository_contract_changed: bool = False


class AgentRegistryRepository:
    """Immutable, local registry projection; it does not replace ProjectRepository."""

    def __init__(self, agents: tuple[AgentDTO, ...] = ()) -> None:
        ids = tuple(agent.agent_id for agent in agents)
        if len(ids) != len(set(ids)):
            raise ValueError("agent IDs must be unique")
        self._agents = tuple(agents)

    def list(self) -> tuple[AgentDTO, ...]:
        return self._agents

    def get(self, agent_id: str) -> AgentDTO | None:
        return next((agent for agent in self._agents if agent.agent_id == agent_id), None)

    def snapshot(self) -> AgentRegistrySnapshotDTO:
        return AgentRegistrySnapshotDTO(agents=self._agents)


class AgentContextDTO(DirectorModel):
    project_id: str
    page_reference: str
    workflow_state: PageState
    context_persisted: bool = False
    multiple_pages_requested: bool = False


class AgentSessionDTO(DirectorModel):
    session_id: str
    agent_id: str
    context: AgentContextDTO
    session_started: bool = False
    long_running: bool = False


class AgentStateDTO(DirectorModel):
    agent_id: str
    state: str = "prepared"
    state_persisted: bool = False
    self_improvement_enabled: bool = False


class ExecutionRequestDTO(DirectorModel):
    request_id: str
    agent_id: str
    page_reference: str
    intent: str = "human_review_required"
    execution_enabled: bool = False
    requires_human_review: bool = True


class ExecutionResultDTO(DirectorModel):
    request_id: str
    agent_id: str
    executed: bool = False
    result_persisted: bool = False
    workflow_changed: bool = False
    automatic_action_taken: bool = False


class AgentRuntimeReport(DirectorModel):
    session: AgentSessionDTO
    state: AgentStateDTO
    request: ExecutionRequestDTO
    result: ExecutionResultDTO
    planning_only: bool = True


class SharedContextDTO(DirectorModel):
    project_id: str
    page_reference: str
    workflow_state: PageState
    shared_context_persisted: bool = False


class TaskDTO(DirectorModel):
    task_id: str
    title: str
    page_reference: str
    planned_only: bool = True
    execution_enabled: bool = False


class AssignmentDTO(DirectorModel):
    assignment_id: str
    task_id: str
    agent_id: str
    accepted: bool = False
    assignment_persisted: bool = False


class ReviewDTO(DirectorModel):
    review_id: str
    task_id: str
    completed: bool = False
    approval_granted: bool = False
    requires_human_review: bool = True


class CollaborationSummary(DirectorModel):
    participant_count: int = Field(ge=0)
    task_count: int = Field(ge=0)
    assignments_persisted: bool = False
    automatic_action_taken: bool = False


class CollaborationReport(DirectorModel):
    shared_context: SharedContextDTO
    task: TaskDTO
    assignment: AssignmentDTO
    review: ReviewDTO
    summary: CollaborationSummary
    planning_only: bool = True


class AgentMessageDTO(DirectorModel):
    message_id: str
    sender_agent_id: str
    recipient_agent_id: str
    channel_id: str
    intent: str = "review_request"
    network_sent: bool = False
    message_persisted: bool = False


class EventDTO(DirectorModel):
    event_id: str
    event_type: str
    agent_id: str
    event_persisted: bool = False


class MessageChannelDTO(DirectorModel):
    channel_id: str
    participants: tuple[str, ...] = ()
    transport_connected: bool = False
    channel_persisted: bool = False


class CommunicationLogDTO(DirectorModel):
    channel: MessageChannelDTO
    messages: tuple[AgentMessageDTO, ...] = ()
    events: tuple[EventDTO, ...] = ()
    log_persisted: bool = False


class MessageSummary(DirectorModel):
    message_count: int = Field(ge=0)
    event_count: int = Field(ge=0)
    delivered_message_count: int = 0
    automatic_action_taken: bool = False


class CommunicationReport(DirectorModel):
    log: CommunicationLogDTO
    summary: MessageSummary
    planning_only: bool = True


class V41AgentFoundationService:
    """Build non-executing agent, collaboration, and message DTO projections."""

    def __init__(self, registry: AgentRegistryRepository) -> None:
        self._registry = registry

    def registry(self) -> AgentRegistrySnapshotDTO:
        return self._registry.snapshot()

    def runtime(
        self, agent_id: str, project_id: str, context: WorkflowContext
    ) -> AgentRuntimeReport:
        agent = self._agent(agent_id)
        agent_context = _context(project_id, context)
        request_id = f"agent-request:{agent.agent_id}:{agent_context.page_reference}"
        return AgentRuntimeReport(
            session=AgentSessionDTO(
                session_id=f"agent-session:{agent.agent_id}:{agent_context.page_reference}",
                agent_id=agent.agent_id,
                context=agent_context,
            ),
            state=AgentStateDTO(agent_id=agent.agent_id),
            request=ExecutionRequestDTO(
                request_id=request_id,
                agent_id=agent.agent_id,
                page_reference=agent_context.page_reference,
            ),
            result=ExecutionResultDTO(request_id=request_id, agent_id=agent.agent_id),
        )

    def collaboration(
        self, agent_id: str, project_id: str, context: WorkflowContext
    ) -> CollaborationReport:
        agent = self._agent(agent_id)
        agent_context = _context(project_id, context)
        task = TaskDTO(
            task_id=f"collaboration-task:{agent_context.page_reference}",
            title="Human review preparation",
            page_reference=agent_context.page_reference,
        )
        return CollaborationReport(
            shared_context=SharedContextDTO(
                project_id=project_id,
                page_reference=agent_context.page_reference,
                workflow_state=context.state,
            ),
            task=task,
            assignment=AssignmentDTO(
                assignment_id=f"assignment:{agent.agent_id}:{task.task_id}",
                task_id=task.task_id,
                agent_id=agent.agent_id,
            ),
            review=ReviewDTO(review_id=f"review:{task.task_id}", task_id=task.task_id),
            summary=CollaborationSummary(participant_count=1, task_count=1),
        )

    def communication(
        self,
        sender_agent_id: str,
        recipient_agent_id: str,
        project_id: str,
        context: WorkflowContext,
    ) -> CommunicationReport:
        sender = self._agent(sender_agent_id)
        recipient = self._agent(recipient_agent_id)
        agent_context = _context(project_id, context)
        channel = MessageChannelDTO(
            channel_id=f"channel:{sender.agent_id}:{recipient.agent_id}:{agent_context.page_reference}",
            participants=(sender.agent_id, recipient.agent_id),
        )
        message = AgentMessageDTO(
            message_id=f"message:{sender.agent_id}:{recipient.agent_id}:{agent_context.page_reference}",
            sender_agent_id=sender.agent_id,
            recipient_agent_id=recipient.agent_id,
            channel_id=channel.channel_id,
        )
        event = EventDTO(
            event_id=f"event:message-prepared:{agent_context.page_reference}",
            event_type="message_prepared",
            agent_id=sender.agent_id,
        )
        return CommunicationReport(
            log=CommunicationLogDTO(channel=channel, messages=(message,), events=(event,)),
            summary=MessageSummary(message_count=1, event_count=1),
        )

    def _agent(self, agent_id: str) -> AgentDTO:
        agent = self._registry.get(agent_id)
        if agent is None:
            raise ValueError(f"unknown agent: {agent_id}")
        return agent


def _context(project_id: str, context: WorkflowContext) -> AgentContextDTO:
    page_id = context.page.get("id")
    page_reference = str(page_id) if page_id is not None else "page"
    return AgentContextDTO(
        project_id=project_id,
        page_reference=page_reference,
        workflow_state=context.state,
    )
