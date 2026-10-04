"""v3 advisory foundation DTOs for Director, Creative, Knowledge, and Workflow views.

This module is intentionally an Application-layer read model.  It composes the
existing Director and planning services but never calls an Agent, changes a
``WorkflowContext``, writes through a repository, or invokes a Provider.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from pydantic import Field

from manga_director.domain.state_machine import PageState
from manga_director.production.director import DirectorFoundationService, DirectorModel
from manga_director.production.planning import PlanningService
from manga_director.workflow.contracts import WorkflowContext


class ProjectGoal(DirectorModel):
    """A human-owned project outcome used as planning input only."""

    title: str
    outcome: str
    priority: Literal["low", "medium", "high"] = "medium"
    source: Literal["human", "context"] = "human"


class CreativeGoal(DirectorModel):
    """A bounded creative intent; it carries no generation instruction."""

    purpose: str
    reader_effect: str
    hook: str | None = None
    source: Literal["human", "page_design", "context"] = "context"


class PlanningContext(DirectorModel):
    """Safe, one-page projection of an existing workflow context."""

    page_reference: str
    current_state: PageState
    artifact_names: tuple[str, ...] = ()
    history_entries: int = Field(ge=0)
    page_scope: Literal["one_page"] = "one_page"
    state_mutated: bool = False


class ExecutionContext(DirectorModel):
    """A non-executable next-step recommendation derived from StateMachine evidence."""

    recommended_command: str | None = None
    target_state: PageState | None = None
    human_review_required: bool = True
    execution_enabled: bool = False


class DirectorSession(DirectorModel):
    """An advisory planning session; it does not represent an active runtime session."""

    session_id: str
    project_goal: ProjectGoal
    creative_goal: CreativeGoal
    planning_context: PlanningContext
    execution_context: ExecutionContext
    decision_trace: tuple[str, ...] = ()
    planning_only: bool = True


class PlanningSummary(DirectorModel):
    """Compact Director session summary suitable for a presentation adapter."""

    session_id: str
    current_state: PageState
    recommended_command: str | None = None
    ready: bool
    messages: tuple[str, ...] = ()
    execution_performed: bool = False


class DirectorSessionReport(DirectorModel):
    """Director session, underlying evidence, and a safe summary."""

    session: DirectorSession
    summary: PlanningSummary
    planning_only: bool = True


class StoryPlanning(DirectorModel):
    theme: str
    story_goal: str
    advisory_only: bool = True


class ChapterPlanning(DirectorModel):
    chapter_reference: str | None = None
    chapter_goal: str
    page_order_considered: bool = True
    advisory_only: bool = True


class PagePlanning(DirectorModel):
    page_reference: str
    state: PageState
    purpose: str
    next_command: str | None = None
    execution_enabled: bool = False


class PanelPlanning(DirectorModel):
    panel_count: int = Field(ge=0)
    panel_roles: tuple[str, ...] = ()
    storyboard_persisted: bool = False
    advisory_only: bool = True


class PlanningTimelineEntry(DirectorModel):
    name: str
    state: PageState | None = None
    source: Literal["workflow_history", "current_context"]


class PlanningTimeline(DirectorModel):
    entries: tuple[PlanningTimelineEntry, ...] = ()
    timeline_only: bool = True


class CreativePlanningReport(DirectorModel):
    story: StoryPlanning
    chapter: ChapterPlanning
    page: PagePlanning
    panels: PanelPlanning
    timeline: PlanningTimeline
    image_generation_invoked: bool = False


class KnowledgeNamespace(DirectorModel):
    name: str
    description: str


class KnowledgeCategory(DirectorModel):
    name: Literal["project", "chapter", "page", "character", "world", "lore", "scene", "prompt", "asset"]
    namespace: str


class KnowledgeTag(DirectorModel):
    value: str
    category: str


class KnowledgeReference(DirectorModel):
    namespace: str
    category: KnowledgeCategory
    identifier: str
    label: str
    tags: tuple[KnowledgeTag, ...] = ()
    source: Literal["repository"] = "repository"
    redacted: bool = True


class KnowledgeSnapshot(DirectorModel):
    namespace: KnowledgeNamespace
    references: tuple[KnowledgeReference, ...] = ()
    source: Literal["repository"] = "repository"
    persistence_mutated: bool = False


class KnowledgeIndexSummary(DirectorModel):
    reference_count: int = Field(ge=0)
    category_counts: dict[str, int] = Field(default_factory=dict)
    repository_read_only: bool = True


class KnowledgeFoundationReport(DirectorModel):
    snapshot: KnowledgeSnapshot
    index: KnowledgeIndexSummary
    health: Literal["healthy", "empty"]
    recommendations: tuple[str, ...] = ()
    persistence_mutated: bool = False


class PlanningDependencyGraph(DirectorModel):
    current_state: PageState
    nodes: tuple[str, ...] = ()
    edges: tuple[tuple[str, str], ...] = ()
    state_machine_derived: bool = True
    execution_enabled: bool = False


class CreativeProgressReport(DirectorModel):
    current_state: PageState
    completed_artifacts: tuple[str, ...] = ()
    required_checkpoint: str | None = None
    progress_only: bool = True


class ExecutionTimeline(DirectorModel):
    entries: tuple[PlanningTimelineEntry, ...] = ()
    execution_performed: bool = False


class WorkflowRecommendation(DirectorModel):
    command: str | None = None
    target_state: PageState | None = None
    rationale: str
    diagnostic_only: bool = True


class WorkflowIntelligenceReport(DirectorModel):
    dependency_graph: PlanningDependencyGraph
    creative_progress: CreativeProgressReport
    execution_timeline: ExecutionTimeline
    recommendation: WorkflowRecommendation
    workflow_modified: bool = False


class DirectorPlatformDTO(DirectorModel):
    session: DirectorSessionReport
    automatic_action_taken: bool = False


class CreativePlanningDTO(DirectorModel):
    report: CreativePlanningReport
    automatic_action_taken: bool = False


class KnowledgeDashboardDTO(DirectorModel):
    report: KnowledgeFoundationReport
    automatic_action_taken: bool = False


class WorkflowIntelligenceDTO(DirectorModel):
    report: WorkflowIntelligenceReport
    automatic_action_taken: bool = False


class DirectorPlanningService:
    """Compose v3 Foundation reports through existing, read-only application services."""

    def __init__(self, foundation: DirectorFoundationService, planning: PlanningService) -> None:
        self._foundation = foundation
        self._planning = planning

    def director_session(
        self,
        context: WorkflowContext,
        *,
        project_goal: ProjectGoal | None = None,
        creative_goal: CreativeGoal | None = None,
    ) -> DirectorSessionReport:
        plan = self._foundation.director_plan(context)
        project = project_goal or _project_goal(context)
        creative = creative_goal or _creative_goal(context)
        planning_context = _planning_context(context)
        execution_context = ExecutionContext(
            recommended_command=plan.strategy.command,
            target_state=plan.strategy.target_state,
        )
        session = DirectorSession(
            session_id=f"{planning_context.page_reference}:{context.state.value}",
            project_goal=project,
            creative_goal=creative,
            planning_context=planning_context,
            execution_context=execution_context,
            decision_trace=plan.trace.evidence,
        )
        return DirectorSessionReport(
            session=session,
            summary=PlanningSummary(
                session_id=session.session_id,
                current_state=context.state,
                recommended_command=plan.strategy.command,
                ready=plan.readiness.ready,
                messages=("Planning only; select an existing workflow command to execute.",),
            ),
        )

    def creative_planning(self, context: WorkflowContext) -> CreativePlanningReport:
        page_design = _mapping(context.artifacts.get("page_design", context.metadata.get("page_design")))
        storyboard = _mapping(context.artifacts.get("storyboard"))
        plan = self._foundation.director_plan(context)
        panel_roles = _string_tuple(page_design.get("panel_roles"))
        panel_count = _non_negative_int(page_design.get("panel_count"), len(panel_roles))
        timeline = _timeline(context)
        return CreativePlanningReport(
            story=StoryPlanning(
                theme=_text(context.metadata.get("theme"), "Unspecified story theme"),
                story_goal=_text(context.metadata.get("story_goal"), "Support the current page goal."),
            ),
            chapter=ChapterPlanning(
                chapter_reference=_optional_text(context.metadata.get("chapter_id")),
                chapter_goal=_text(context.metadata.get("chapter_goal"), "Maintain chapter continuity."),
            ),
            page=PagePlanning(
                page_reference=_page_reference(context),
                state=context.state,
                purpose=_text(page_design.get("purpose"), "Clarify the next page purpose."),
                next_command=plan.strategy.command,
            ),
            panels=PanelPlanning(
                panel_count=panel_count,
                panel_roles=panel_roles,
                storyboard_persisted=bool(storyboard) or PageState.STORYBOARDED.value in context.artifacts,
            ),
            timeline=timeline,
        )

    def knowledge_foundation(self) -> KnowledgeFoundationReport:
        knowledge = self._foundation.knowledge_report()
        namespace = KnowledgeNamespace(
            name="project",
            description="Repository-derived project and metadata references.",
        )
        references = tuple(
            KnowledgeReference(
                namespace=namespace.name,
                category=KnowledgeCategory(name="project", namespace=namespace.name),
                identifier=entry.project_id,
                label=entry.title,
                tags=tuple(KnowledgeTag(value=key, category="metadata") for key in entry.metadata_keys),
            )
            for entry in knowledge.snapshot.entries
        )
        category_counts = {"project": len(references)} if references else {}
        return KnowledgeFoundationReport(
            snapshot=KnowledgeSnapshot(namespace=namespace, references=references),
            index=KnowledgeIndexSummary(
                reference_count=len(references), category_counts=category_counts
            ),
            health="healthy" if references else "empty",
            recommendations=(
                "Knowledge is repository-derived, redacted, and advisory; review provenance before reuse.",
            ),
        )

    def workflow_intelligence(self, context: WorkflowContext) -> WorkflowIntelligenceReport:
        orchestration = self._foundation.orchestration(context)
        planning = self._planning.workflow_intelligence(context)
        recommendation = self._foundation.director_plan(context).recommendation
        checkpoint = _checkpoint(context.state)
        return WorkflowIntelligenceReport(
            dependency_graph=PlanningDependencyGraph(
                current_state=context.state,
                nodes=orchestration.graph.nodes,
                edges=orchestration.graph.edges,
            ),
            creative_progress=CreativeProgressReport(
                current_state=context.state,
                completed_artifacts=tuple(sorted(str(name) for name in context.artifacts)),
                required_checkpoint=checkpoint,
            ),
            execution_timeline=ExecutionTimeline(entries=_timeline(context).entries),
            recommendation=WorkflowRecommendation(
                command=recommendation.strategy.command,
                target_state=recommendation.strategy.target_state,
                rationale=planning.recommendations[0].message,
            ),
        )

    def planning_summary(self, context: WorkflowContext) -> PlanningSummary:
        session = self.director_session(context)
        return PlanningSummary(
            session_id=session.session.session_id,
            current_state=context.state,
            recommended_command=session.summary.recommended_command,
            ready=session.summary.ready,
            messages=(
                "Director, Creative, Knowledge, and Workflow foundation reports are advisory only.",
            ),
        )

    def director_platform(self, context: WorkflowContext) -> DirectorPlatformDTO:
        return DirectorPlatformDTO(session=self.director_session(context))

    def creative_dashboard(self, context: WorkflowContext) -> CreativePlanningDTO:
        return CreativePlanningDTO(report=self.creative_planning(context))

    def knowledge_dashboard(self) -> KnowledgeDashboardDTO:
        return KnowledgeDashboardDTO(report=self.knowledge_foundation())

    def workflow_dashboard(self, context: WorkflowContext) -> WorkflowIntelligenceDTO:
        return WorkflowIntelligenceDTO(report=self.workflow_intelligence(context))


def _project_goal(context: WorkflowContext) -> ProjectGoal:
    return ProjectGoal(
        title=_text(context.metadata.get("project_title"), "Current manga project"),
        outcome=_text(context.metadata.get("project_goal"), "Advance one reviewed page safely."),
        source="context",
    )


def _creative_goal(context: WorkflowContext) -> CreativeGoal:
    design = _mapping(context.artifacts.get("page_design", context.metadata.get("page_design")))
    return CreativeGoal(
        purpose=_text(design.get("purpose"), "Clarify the page purpose."),
        reader_effect=_text(design.get("reader_emotion"), "Maintain reader clarity."),
        hook=_optional_text(design.get("hook")),
        source="page_design" if design else "context",
    )


def _planning_context(context: WorkflowContext) -> PlanningContext:
    history = context.metadata.get("workflow_history", [])
    return PlanningContext(
        page_reference=_page_reference(context),
        current_state=context.state,
        artifact_names=tuple(sorted(str(name) for name in context.artifacts)),
        history_entries=len(history) if isinstance(history, list) else 0,
    )


def _timeline(context: WorkflowContext) -> PlanningTimeline:
    history = context.metadata.get("workflow_history", [])
    entries: list[PlanningTimelineEntry] = []
    if isinstance(history, list):
        for item in history:
            if isinstance(item, Mapping):
                value = item.get("to", item.get("state"))
                state = _page_state(value)
                entries.append(
                    PlanningTimelineEntry(
                        name=str(item.get("step", "workflow")),
                        state=state,
                        source="workflow_history",
                    )
                )
    if not entries:
        entries.append(
            PlanningTimelineEntry(
                name=context.state.value,
                state=context.state,
                source="current_context",
            )
        )
    return PlanningTimeline(entries=tuple(entries))


def _checkpoint(state: PageState) -> str | None:
    if state is PageState.PROMPT_BUILT:
        return "Persisted storyboard is required before image generation."
    if state is PageState.QUALITY_CHECKED:
        return "Human Approval is required to reach Approved."
    return None


def _page_reference(context: WorkflowContext) -> str:
    value = context.page.get("id", context.page.get("page_number", "page"))
    return str(value)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _text(value: Any, default: str) -> str:
    return str(value).strip() if isinstance(value, str) and value.strip() else default


def _optional_text(value: Any) -> str | None:
    return _text(value, "") or None


def _string_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(str(item) for item in value if str(item))


def _non_negative_int(value: Any, fallback: int) -> int:
    return value if isinstance(value, int) and value >= 0 else fallback


def _page_state(value: Any) -> PageState | None:
    if not isinstance(value, str):
        return None
    try:
        return PageState(value)
    except ValueError:
        return None
