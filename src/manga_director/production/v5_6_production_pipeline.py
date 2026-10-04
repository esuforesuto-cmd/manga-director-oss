"""Read-only v5.6 production-pipeline planning for exactly one manga page.

The domain StateMachine remains the authority for every workflow transition.
This module only turns the current one-page context into a human-reviewable
production plan; it never generates art, approves a page, exports output, or
changes workflow state.
"""

from __future__ import annotations

from typing import Literal

from manga_director.domain.state_machine import PageState, StateMachine
from manga_director.production.director import DirectorModel
from manga_director.workflow.contracts import WorkflowContext

PipelineStatus = Literal["ready", "blocked", "complete"]


class StoryPipelineDTO(DirectorModel):
    """Story and timeline evidence needed for the current page."""

    project_id: str
    page_reference: str
    story_context_available: bool
    timeline_context_available: bool
    status: PipelineStatus


class CharacterPipelineDTO(DirectorModel):
    """Character and world evidence needed for the current page."""

    project_id: str
    page_reference: str
    character_context_available: bool
    world_context_available: bool
    status: PipelineStatus


class PagePipelineDTO(DirectorModel):
    """Read-only page-stage projection with a strict one-page scope."""

    project_id: str
    page_reference: str
    current_state: PageState
    page_count: Literal[1] = 1
    storyboard_persisted: bool
    next_command: str | None = None


class ArtPipelineDTO(DirectorModel):
    """Art-generation eligibility without invoking an image provider."""

    current_state: PageState
    storyboard_persisted: bool
    generation_allowed: bool
    generation_performed: Literal[False] = False
    status: PipelineStatus


class V56ReviewPipelineDTO(DirectorModel):
    """Quality-review readiness without approving the page."""

    current_state: PageState
    quality_review_completed: bool
    approval_eligible: bool
    approval_performed: Literal[False] = False
    status: PipelineStatus


class ExportPipelineDTO(DirectorModel):
    """Export readiness without creating, publishing, or distributing output."""

    current_state: PageState
    approval_completed: bool
    export_eligible: bool
    export_performed: Literal[False] = False
    status: PipelineStatus


class ProductionPromptBriefDTO(DirectorModel):
    """A compact prompt envelope that reuses persisted page context."""

    page_reference: str
    compact_instruction: str = (
        "Produce exactly one page using supplied context; preserve continuity and obey StateMachine gates."
    )
    reused_context_keys: tuple[str, ...] = ()
    required_constraints: tuple[str, ...] = (
        "exactly_one_page",
        "preserve_story_character_world_timeline",
        "require_persisted_storyboard_before_generation",
        "require_completed_quality_review_before_approval",
    )
    duplicate_context_elided: bool = True
    prompt_generated: Literal[False] = False


class ProductionPipelineSummary(DirectorModel):
    """Explicit boundary record for the v5.6 production standard."""

    project_id: str
    page_reference: str
    standard_stages: tuple[str, ...] = (
        "story",
        "character",
        "page",
        "art",
        "review",
        "export",
    )
    workflow_changed: Literal[False] = False
    automatic_action_taken: Literal[False] = False
    prompt_compaction_available: bool = True
    findings: tuple[str, ...] = ()


class MangaProductionPipelineReport(DirectorModel):
    """Transport-neutral v5.6 Production Pipeline v1 report."""

    story: StoryPipelineDTO
    character: CharacterPipelineDTO
    page: PagePipelineDTO
    art: ArtPipelineDTO
    review: V56ReviewPipelineDTO
    export: ExportPipelineDTO
    prompt_brief: ProductionPromptBriefDTO
    summary: ProductionPipelineSummary
    planning_only: Literal[True] = True


class V56ProductionPipelineService:
    """Create a standardized, read-only production plan for one existing page."""

    def production_pipeline(
        self, project_id: str, context: WorkflowContext
    ) -> MangaProductionPipelineReport:
        page_reference = str(context.page.get("id", "current-page"))
        story_available = _has_context(context, "story_context")
        character_available = _has_context(context, "character_context")
        world_available = _has_context(context, "world_context")
        timeline_available = _has_context(context, "timeline_context")
        storyboard_persisted = PageState.STORYBOARDED.value in context.artifacts
        quality_review_completed = (
            context.state in (PageState.QUALITY_CHECKED, PageState.APPROVED)
            and PageState.QUALITY_CHECKED.value in context.artifacts
        )
        approval_completed = context.state is PageState.APPROVED and quality_review_completed
        next_command = _next_command(context.state)
        generation_allowed = storyboard_persisted and next_command == "generate"
        approval_eligible = quality_review_completed and next_command == "approve"
        export_eligible = approval_completed

        return MangaProductionPipelineReport(
            story=StoryPipelineDTO(
                project_id=project_id,
                page_reference=page_reference,
                story_context_available=story_available,
                timeline_context_available=timeline_available,
                status=_evidence_status(story_available and timeline_available),
            ),
            character=CharacterPipelineDTO(
                project_id=project_id,
                page_reference=page_reference,
                character_context_available=character_available,
                world_context_available=world_available,
                status=_evidence_status(character_available and world_available),
            ),
            page=PagePipelineDTO(
                project_id=project_id,
                page_reference=page_reference,
                current_state=context.state,
                storyboard_persisted=storyboard_persisted,
                next_command=next_command,
            ),
            art=ArtPipelineDTO(
                current_state=context.state,
                storyboard_persisted=storyboard_persisted,
                generation_allowed=generation_allowed,
                status=_stage_status(
                    allowed=generation_allowed,
                    completed=context.state
                    in (PageState.GENERATED, PageState.QUALITY_CHECKED, PageState.APPROVED),
                ),
            ),
            review=V56ReviewPipelineDTO(
                current_state=context.state,
                quality_review_completed=quality_review_completed,
                approval_eligible=approval_eligible,
                status=_stage_status(
                    allowed=next_command == "quality",
                    completed=quality_review_completed,
                ),
            ),
            export=ExportPipelineDTO(
                current_state=context.state,
                approval_completed=approval_completed,
                export_eligible=export_eligible,
                status=_stage_status(allowed=export_eligible, completed=False),
            ),
            prompt_brief=ProductionPromptBriefDTO(
                page_reference=page_reference,
                reused_context_keys=tuple(
                    key
                    for key, available in (
                        ("story_context", story_available),
                        ("character_context", character_available),
                        ("world_context", world_available),
                        ("timeline_context", timeline_available),
                    )
                    if available
                ),
            ),
            summary=ProductionPipelineSummary(
                project_id=project_id,
                page_reference=page_reference,
                findings=_findings(
                    story_available=story_available,
                    character_available=character_available,
                    world_available=world_available,
                    timeline_available=timeline_available,
                    storyboard_persisted=storyboard_persisted,
                    quality_review_completed=quality_review_completed,
                    approval_completed=approval_completed,
                ),
            ),
        )


def _has_context(context: WorkflowContext, key: str) -> bool:
    """Accept caller-supplied evidence without copying or changing it."""

    return bool(context.metadata.get(key) or context.page.get(key))


def _next_command(current_state: PageState) -> str | None:
    if current_state is PageState.APPROVED:
        return None
    return StateMachine().next_command(current_state)


def _evidence_status(available: bool) -> PipelineStatus:
    return "ready" if available else "blocked"


def _stage_status(*, allowed: bool, completed: bool) -> PipelineStatus:
    if completed:
        return "complete"
    return "ready" if allowed else "blocked"


def _findings(
    *,
    story_available: bool,
    character_available: bool,
    world_available: bool,
    timeline_available: bool,
    storyboard_persisted: bool,
    quality_review_completed: bool,
    approval_completed: bool,
) -> tuple[str, ...]:
    findings: list[str] = []
    for key, available in (
        ("story_context", story_available),
        ("character_context", character_available),
        ("world_context", world_available),
        ("timeline_context", timeline_available),
    ):
        if not available:
            findings.append(f"Missing {key} evidence.")
    if not storyboard_persisted:
        findings.append("Persist a storyboard before image generation.")
    if not quality_review_completed:
        findings.append("Complete quality review before approval.")
    if not approval_completed:
        findings.append("Human approval is required before export.")
    return tuple(findings)
