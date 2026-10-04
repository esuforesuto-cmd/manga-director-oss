"""Read-only AI Director, Knowledge, and orchestration application DTOs.

These services advise delivery layers only. They never execute Agents, mutate a
Project, dispatch work, or bypass the StateMachine.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from manga_director.domain.state_machine import PageState
from manga_director.production.planning import PlanningService, StepDependencyGraph
from manga_director.repositories.protocols import ProjectRepository
from manga_director.workflow.contracts import WorkflowContext


class DirectorModel(BaseModel):
    """Immutable transport-neutral DTO base."""

    model_config = ConfigDict(frozen=True)

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def to_markdown(self) -> str:
        return f"# {self.__class__.__name__}\n\n```json\n{json.dumps(self.model_dump(mode='json'), indent=2)}\n```"


class ExecutionStrategy(DirectorModel):
    name: Literal["state_machine_next_step"] = "state_machine_next_step"
    command: str | None = None
    target_state: PageState | None = None
    execution_enabled: bool = False
    rationale: str


class DecisionTrace(DirectorModel):
    decision: str
    assumptions: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    side_effects: Literal["none"] = "none"


class TaskDependencyGraph(DirectorModel):
    current_state: PageState
    nodes: tuple[str, ...] = ()
    edges: tuple[tuple[str, str], ...] = ()
    human_checkpoints: tuple[str, ...] = ()
    execution_enabled: bool = False


class ExecutionReadinessAnalysis(DirectorModel):
    ready: bool
    next_command: str | None = None
    blockers: tuple[str, ...] = ()
    execution_performed: bool = False


class DirectorRecommendation(DirectorModel):
    message: str
    strategy: ExecutionStrategy
    requires_human_review: bool = True


class DirectorPlanningReport(DirectorModel):
    strategy: ExecutionStrategy
    trace: DecisionTrace
    dependencies: TaskDependencyGraph
    readiness: ExecutionReadinessAnalysis
    recommendation: DirectorRecommendation
    planning_only: bool = True


class KnowledgeEntry(DirectorModel):
    project_id: str
    title: str
    page_count: int = Field(ge=0)
    chapter_count: int = Field(ge=0)
    metadata_keys: tuple[str, ...] = ()


class KnowledgeSnapshot(DirectorModel):
    entries: tuple[KnowledgeEntry, ...] = ()
    source: Literal["repository"] = "repository"
    mutated_repository: bool = False


class KnowledgeSummary(DirectorModel):
    project_count: int = Field(ge=0)
    page_count: int = Field(ge=0)
    chapter_count: int = Field(ge=0)
    metadata_key_count: int = Field(ge=0)


class KnowledgeSearchResult(DirectorModel):
    query: str
    matches: tuple[KnowledgeEntry, ...] = ()
    searched_repository: bool = True


class KnowledgeHealthReport(DirectorModel):
    healthy: bool
    project_count: int = Field(ge=0)
    messages: tuple[str, ...] = ()


class KnowledgeRecommendation(DirectorModel):
    message: str
    action_required: bool = False


class KnowledgeReport(DirectorModel):
    snapshot: KnowledgeSnapshot
    summary: KnowledgeSummary
    health: KnowledgeHealthReport
    recommendation: KnowledgeRecommendation


class WorkflowPlanGraph(DirectorModel):
    dependency_graph: StepDependencyGraph
    nodes: tuple[str, ...] = ()
    edges: tuple[tuple[str, str], ...] = ()
    visualization_only: bool = True


class ExecutionSequencePreview(DirectorModel):
    commands: tuple[str, ...] = ()
    next_command: str | None = None
    execution_performed: bool = False


class TaskGrouping(DirectorModel):
    name: str
    commands: tuple[str, ...] = ()


class OrchestrationSummary(DirectorModel):
    graph: WorkflowPlanGraph
    preview: ExecutionSequencePreview
    groups: tuple[TaskGrouping, ...] = ()
    messages: tuple[str, ...] = ("Visualization only; no work was scheduled.",)


class PlanningExecutiveSummary(DirectorModel):
    director: DirectorPlanningReport
    knowledge: KnowledgeReport
    orchestration: OrchestrationSummary
    execution_performed: bool = False


class KnowledgeService:
    """Repository-port-only knowledge projection with no persistence mutation."""

    def __init__(self, repository: ProjectRepository) -> None:
        self._repository = repository

    def snapshot(self) -> KnowledgeSnapshot:
        return KnowledgeSnapshot(
            entries=tuple(_entry(project) for project in self._repository.list())
        )

    def summary(self) -> KnowledgeSummary:
        entries = self.snapshot().entries
        return KnowledgeSummary(
            project_count=len(entries),
            page_count=sum(item.page_count for item in entries),
            chapter_count=sum(item.chapter_count for item in entries),
            metadata_key_count=sum(len(item.metadata_keys) for item in entries),
        )

    def search(self, query: str) -> KnowledgeSearchResult:
        normalized = query.strip().lower()
        matches = tuple(
            entry
            for entry in self.snapshot().entries
            if not normalized
            or normalized in " ".join((entry.project_id, entry.title, *entry.metadata_keys)).lower()
        )
        return KnowledgeSearchResult(query=query, matches=matches)

    def report(self) -> KnowledgeReport:
        snapshot = self.snapshot()
        summary = self.summary()
        return KnowledgeReport(
            snapshot=snapshot,
            summary=summary,
            health=KnowledgeHealthReport(healthy=True, project_count=summary.project_count),
            recommendation=KnowledgeRecommendation(
                message="Knowledge is repository-derived and advisory; review ownership before adding indexed content."
            ),
        )


class DirectorFoundationService:
    """Compose Director, Knowledge, and orchestration DTOs without execution."""

    def __init__(self, planning: PlanningService, knowledge: KnowledgeService) -> None:
        self._planning = planning
        self._knowledge = knowledge

    def director_plan(self, context: WorkflowContext) -> DirectorPlanningReport:
        plan = self._planning.summary(context).workflow.plan
        recommendation = plan.recommendation
        strategy = ExecutionStrategy(
            command=recommendation.command,
            target_state=recommendation.target_state,
            rationale=recommendation.reason,
        )
        graph = _graph(plan.dependency_graph)
        blockers = tuple(
            step.command
            for step in plan.dependency_graph.steps
            if step.requires_artifacts and step.target_state is context.state
        )
        readiness = ExecutionReadinessAnalysis(
            ready=recommendation.actionable and not blockers,
            next_command=recommendation.command,
            blockers=blockers,
        )
        trace = DecisionTrace(
            decision=recommendation.command or "no_legal_command",
            assumptions=("StateMachine is authoritative.", "Exactly one Page is in scope."),
            evidence=tuple(step.command for step in plan.dependency_graph.steps[:1]),
        )
        return DirectorPlanningReport(
            strategy=strategy,
            trace=trace,
            dependencies=graph,
            readiness=readiness,
            recommendation=DirectorRecommendation(message=recommendation.reason, strategy=strategy),
        )

    def orchestration(self, context: WorkflowContext) -> OrchestrationSummary:
        dependency = self._planning.summary(context).dependency_report.graph
        commands = tuple(step.command for step in dependency.steps)
        return OrchestrationSummary(
            graph=WorkflowPlanGraph(
                dependency_graph=dependency,
                nodes=tuple(step.target_state.value for step in dependency.steps),
                edges=tuple(
                    (commands[index], commands[index + 1])
                    for index in range(max(0, len(commands) - 1))
                ),
            ),
            preview=ExecutionSequencePreview(
                commands=commands, next_command=commands[0] if commands else None
            ),
            groups=(TaskGrouping(name="remaining_legal_steps", commands=commands),),
        )

    def knowledge_report(self) -> KnowledgeReport:
        return self._knowledge.report()

    def knowledge_search(self, query: str) -> KnowledgeSearchResult:
        """Search repository-derived knowledge without exposing repository internals."""

        return self._knowledge.search(query)

    def executive_summary(self, context: WorkflowContext) -> PlanningExecutiveSummary:
        return PlanningExecutiveSummary(
            director=self.director_plan(context),
            knowledge=self.knowledge_report(),
            orchestration=self.orchestration(context),
        )


def _entry(project: Any) -> KnowledgeEntry:
    return KnowledgeEntry(
        project_id=str(project.id),
        title=str(project.title),
        page_count=len(project.pages),
        chapter_count=len(project.chapters),
        metadata_keys=tuple(sorted(str(key) for key in project.metadata)),
    )


def _graph(graph: StepDependencyGraph) -> TaskDependencyGraph:
    commands = tuple(step.command for step in graph.steps)
    return TaskDependencyGraph(
        current_state=graph.current_state,
        nodes=commands,
        edges=tuple(
            (commands[index], commands[index + 1]) for index in range(max(0, len(commands) - 1))
        ),
        human_checkpoints=tuple(
            step.command for step in graph.steps if step.human_decision_required
        ),
    )
