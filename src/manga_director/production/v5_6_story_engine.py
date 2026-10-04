"""Read-only v5.6 Story Engine v1 for a single existing manga page.

The Story Engine standardizes evidence review for story, character, world,
timeline, foreshadowing, conflict, and ending context. It does not rewrite any
creative material, persist knowledge, or change the workflow state machine.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Literal

from manga_director.domain.state_machine import PageState
from manga_director.production.director import DirectorModel
from manga_director.workflow.contracts import WorkflowContext

EvidenceStatus = Literal["ready", "needs_evidence"]


class StoryPlannerDTO(DirectorModel):
    """Read-only story and world-planning evidence for one page."""

    project_id: str
    page_reference: str
    story_context_available: bool
    world_context_available: bool
    premise_available: bool
    chapter_goal_available: bool
    status: EvidenceStatus


class StoryValidatorDTO(DirectorModel):
    """Deterministic evidence checks; it does not judge or rewrite creative content."""

    story_structure_valid: bool
    character_motivation_valid: bool
    timeline_valid: bool
    findings: tuple[str, ...] = ()
    validation_performed: bool = True


class ChapterPlannerDTO(DirectorModel):
    """One-page chapter-planning projection without scheduling or dispatching."""

    chapter_reference: str | None = None
    page_reference: str
    current_state: PageState
    chapter_goal_available: bool
    page_count: Literal[1] = 1
    planning_performed: Literal[False] = False


class ForeshadowManagerDTO(DirectorModel):
    """Read-only setup/payoff traceability with no automatic resolution."""

    setup_references: tuple[str, ...] = ()
    payoff_references: tuple[str, ...] = ()
    unresolved_setup_references: tuple[str, ...] = ()
    payoff_references_valid: bool
    status: EvidenceStatus
    foreshadowing_changed: Literal[False] = False


class ConflictManagerDTO(DirectorModel):
    """Conflict and character-motivation evidence for a human creative review."""

    conflict_available: bool
    character_motivation_available: bool
    world_constraint_available: bool
    status: EvidenceStatus
    conflict_changed: Literal[False] = False


class EndingPlannerDTO(DirectorModel):
    """Ending readiness based on supplied ending and foreshadowing evidence."""

    ending_goal_available: bool
    foreshadowing_payoff_consistent: bool
    status: EvidenceStatus
    ending_changed: Literal[False] = False


class StoryPromptBriefDTO(DirectorModel):
    """Compact prompt constraints that reference approved context by key."""

    page_reference: str
    compact_instruction: str = (
        "Plan exactly one page from supplied story context; preserve character, world, timeline, "
        "foreshadowing, conflict, and ending constraints."
    )
    reused_context_keys: tuple[str, ...] = ()
    duplicate_context_elided: bool = True
    prompt_generated: Literal[False] = False


class StoryWorkflowSummary(DirectorModel):
    """Boundary and quality summary for the Story Workflow Standard."""

    project_id: str
    page_reference: str
    standard_stages: tuple[str, ...] = (
        "story_plan",
        "story_validation",
        "chapter_plan",
        "foreshadow_review",
        "conflict_review",
        "ending_review",
    )
    story_changed: Literal[False] = False
    character_changed: Literal[False] = False
    world_changed: Literal[False] = False
    timeline_changed: Literal[False] = False
    automatic_action_taken: Literal[False] = False
    findings: tuple[str, ...] = ()


class StoryEngineReport(DirectorModel):
    """Transport-neutral Story Engine v1 report for one immutable context."""

    planner: StoryPlannerDTO
    validator: StoryValidatorDTO
    chapter: ChapterPlannerDTO
    foreshadow: ForeshadowManagerDTO
    conflict: ConflictManagerDTO
    ending: EndingPlannerDTO
    prompt_brief: StoryPromptBriefDTO
    summary: StoryWorkflowSummary
    analysis_only: Literal[True] = True


class V56StoryEngineService:
    """Build one-page Story Engine reports from supplied workflow evidence."""

    def story_engine(self, project_id: str, context: WorkflowContext) -> StoryEngineReport:
        page_reference = _page_reference(context)
        story_value = _context_value(context, "story_context")
        character_value = _context_value(context, "character_context")
        world_value = _context_value(context, "world_context")
        timeline_value = _context_value(context, "timeline_context")
        foreshadow_value = _context_value(context, "foreshadow_context")
        story_data = _mapping(story_value)
        character_data = _mapping(character_value)
        foreshadow_data = _mapping(foreshadow_value)

        story_available = bool(story_value)
        character_available = bool(character_value)
        world_available = bool(world_value)
        timeline_available = bool(timeline_value)
        premise_available = bool(story_data.get("premise"))
        chapter_goal_available = bool(
            story_data.get("chapter_goal") or context.metadata.get("chapter_goal")
        )
        conflict_available = bool(story_data.get("conflict"))
        motivation_available = bool(
            character_data.get("motivation") or context.metadata.get("character_motivation")
        )
        ending_goal_available = bool(
            story_data.get("ending_goal") or context.metadata.get("ending_goal")
        )
        timeline_valid = _timeline_valid(timeline_value)
        setup_references = _references(foreshadow_data.get("setups"))
        payoff_references = _references(foreshadow_data.get("payoffs"))
        payoff_references_valid = bool(setup_references) and all(
            payoff in setup_references for payoff in payoff_references
        )
        unresolved_setups = tuple(
            setup for setup in setup_references if setup not in payoff_references
        )
        foreshadow_consistent = payoff_references_valid and not unresolved_setups
        story_structure_valid = story_available and premise_available and chapter_goal_available
        character_motivation_valid = character_available and motivation_available

        findings = _findings(
            story_available=story_available,
            world_available=world_available,
            premise_available=premise_available,
            chapter_goal_available=chapter_goal_available,
            character_available=character_available,
            motivation_available=motivation_available,
            timeline_available=timeline_available,
            timeline_valid=timeline_valid,
            conflict_available=conflict_available,
            setup_references=setup_references,
            payoff_references_valid=payoff_references_valid,
            ending_goal_available=ending_goal_available,
            foreshadow_consistent=foreshadow_consistent,
        )

        return StoryEngineReport(
            planner=StoryPlannerDTO(
                project_id=project_id,
                page_reference=page_reference,
                story_context_available=story_available,
                world_context_available=world_available,
                premise_available=premise_available,
                chapter_goal_available=chapter_goal_available,
                status=_status(story_structure_valid and world_available),
            ),
            validator=StoryValidatorDTO(
                story_structure_valid=story_structure_valid,
                character_motivation_valid=character_motivation_valid,
                timeline_valid=timeline_valid,
                findings=findings,
            ),
            chapter=ChapterPlannerDTO(
                chapter_reference=_optional_text(context.metadata.get("chapter_id")),
                page_reference=page_reference,
                current_state=context.state,
                chapter_goal_available=chapter_goal_available,
            ),
            foreshadow=ForeshadowManagerDTO(
                setup_references=setup_references,
                payoff_references=payoff_references,
                unresolved_setup_references=unresolved_setups,
                payoff_references_valid=payoff_references_valid,
                status=_status(payoff_references_valid and not unresolved_setups),
            ),
            conflict=ConflictManagerDTO(
                conflict_available=conflict_available,
                character_motivation_available=motivation_available,
                world_constraint_available=world_available,
                status=_status(conflict_available and motivation_available and world_available),
            ),
            ending=EndingPlannerDTO(
                ending_goal_available=ending_goal_available,
                foreshadowing_payoff_consistent=foreshadow_consistent,
                status=_status(ending_goal_available and foreshadow_consistent),
            ),
            prompt_brief=StoryPromptBriefDTO(
                page_reference=page_reference,
                reused_context_keys=tuple(
                    key
                    for key, value in (
                        ("story_context", story_value),
                        ("character_context", character_value),
                        ("world_context", world_value),
                        ("timeline_context", timeline_value),
                        ("foreshadow_context", foreshadow_value),
                    )
                    if value
                ),
            ),
            summary=StoryWorkflowSummary(
                project_id=project_id,
                page_reference=page_reference,
                findings=findings,
            ),
        )


def _context_value(context: WorkflowContext, key: str) -> object:
    return context.metadata.get(key) or context.page.get(key)


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _references(value: object) -> tuple[str, ...]:
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return tuple(str(item) for item in value if str(item))
    return ()


def _timeline_valid(value: object) -> bool:
    data = _mapping(value)
    events = data.get("events")
    if not isinstance(events, Sequence) or isinstance(events, str | bytes) or not events:
        return False
    sequence_values: list[int] = []
    for event in events:
        if not isinstance(event, Mapping):
            return False
        sequence = event.get("sequence")
        if not isinstance(sequence, int) or isinstance(sequence, bool):
            return False
        sequence_values.append(sequence)
    return sequence_values == sorted(sequence_values) and len(set(sequence_values)) == len(
        sequence_values
    )


def _page_reference(context: WorkflowContext) -> str:
    value = context.page.get("id")
    return str(value) if value is not None else "current-page"


def _optional_text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _status(valid: bool) -> EvidenceStatus:
    return "ready" if valid else "needs_evidence"


def _findings(
    *,
    story_available: bool,
    world_available: bool,
    premise_available: bool,
    chapter_goal_available: bool,
    character_available: bool,
    motivation_available: bool,
    timeline_available: bool,
    timeline_valid: bool,
    conflict_available: bool,
    setup_references: tuple[str, ...],
    payoff_references_valid: bool,
    ending_goal_available: bool,
    foreshadow_consistent: bool,
) -> tuple[str, ...]:
    findings: list[str] = []
    for name, available in (
        ("story_context", story_available),
        ("world_context", world_available),
        ("story premise", premise_available),
        ("chapter goal", chapter_goal_available),
        ("character_context", character_available),
        ("character motivation", motivation_available),
        ("timeline_context", timeline_available),
        ("story conflict", conflict_available),
        ("ending goal", ending_goal_available),
    ):
        if not available:
            findings.append(f"Missing {name} evidence.")
    if timeline_available and not timeline_valid:
        findings.append("Timeline events must use unique ascending sequence values.")
    if not setup_references:
        findings.append("Missing foreshadow setup evidence.")
    elif not payoff_references_valid:
        findings.append("Each foreshadow payoff must reference a declared setup.")
    elif not foreshadow_consistent:
        findings.append("Resolve or explicitly defer remaining foreshadow setups before ending review.")
    return tuple(findings)
