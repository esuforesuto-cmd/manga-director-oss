"""Read-only v5.6 Review Engine v1 for commercial manga quality evidence.

The Review Engine combines supplied story, character, page, storyboard, art,
dialogue, and continuity evidence for one existing page. It never edits creative
material, invokes a reviewer, changes a score artifact, approves a page, or
alters workflow state.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Literal

from pydantic import Field

from manga_director.domain.state_machine import PageState
from manga_director.production.director import DirectorModel
from manga_director.workflow.contracts import WorkflowContext

ReviewStatus = Literal["ready", "needs_review"]
SuggestionArea = Literal["story", "character", "page", "art", "dialogue", "continuity"]


class StoryReviewerDTO(DirectorModel):
    story_context_available: bool
    premise_available: bool
    chapter_goal_available: bool
    status: ReviewStatus


class CharacterReviewerDTO(DirectorModel):
    character_context_available: bool
    name_available: bool
    motivation_available: bool
    status: ReviewStatus


class PageReviewerDTO(DirectorModel):
    page_design_available: bool
    storyboard_available: bool
    panel_count_matches: bool
    status: ReviewStatus


class ArtReviewerDTO(DirectorModel):
    storyboard_panel_count: int = Field(ge=0)
    visual_direction_complete: bool
    status: ReviewStatus


class DialogueReviewerDTO(DirectorModel):
    dialogue_line_count: int = Field(ge=0)
    positioned_dialogue_count: int = Field(ge=0)
    voice_evidence_available: bool
    status: ReviewStatus


class ContinuityReviewerDTO(DirectorModel):
    evidence_available: bool
    mismatched_fields: tuple[str, ...] = ()
    status: ReviewStatus


class QualityScoringEngineDTO(DirectorModel):
    """Deterministic evidence-coverage score; not an approval decision."""

    score: int = Field(ge=0, le=100)
    passed_dimensions: int = Field(ge=0, le=6)
    total_dimensions: Literal[6] = 6
    score_calculated: bool = True
    approval_granted: Literal[False] = False


class RevisionSuggestionDTO(DirectorModel):
    area: SuggestionArea
    message: str
    estimated_scope: Literal["evidence_only"] = "evidence_only"
    revision_applied: Literal[False] = False


class RevisionAdvisorDTO(DirectorModel):
    """Minimal, evidence-only review suggestions without creative changes."""

    suggestions: tuple[RevisionSuggestionDTO, ...] = ()
    manual_review_required: bool
    automatic_action_taken: Literal[False] = False


class ReviewPromptBriefDTO(DirectorModel):
    """Compact review instruction that references existing evidence by key."""

    page_reference: str
    compact_instruction: str = (
        "Review exactly one page using supplied story, character, page, storyboard, and continuity "
        "evidence; report only minimal evidence gaps."
    )
    reused_context_keys: tuple[str, ...] = ()
    duplicate_context_elided: bool = True
    prompt_generated: Literal[False] = False


class CommercialMangaReviewSummary(DirectorModel):
    project_id: str
    page_reference: str
    standard_stages: tuple[str, ...] = (
        "story_review",
        "character_review",
        "page_review",
        "art_review",
        "dialogue_review",
        "continuity_review",
        "quality_scoring",
        "revision_advice",
    )
    review_completed: Literal[False] = False
    approval_granted: Literal[False] = False
    automatic_action_taken: Literal[False] = False
    findings: tuple[str, ...] = ()


class ReviewEngineReport(DirectorModel):
    """Transport-neutral Review Engine v1 report for one immutable context."""

    story: StoryReviewerDTO
    character: CharacterReviewerDTO
    page: PageReviewerDTO
    art: ArtReviewerDTO
    dialogue: DialogueReviewerDTO
    continuity: ContinuityReviewerDTO
    quality: QualityScoringEngineDTO
    revision_advisor: RevisionAdvisorDTO
    prompt_brief: ReviewPromptBriefDTO
    summary: CommercialMangaReviewSummary
    analysis_only: Literal[True] = True


class V56ReviewEngineService:
    """Build a commercial-review evidence report without replacing human review."""

    def review_engine(self, project_id: str, context: WorkflowContext) -> ReviewEngineReport:
        page_reference = _page_reference(context)
        story = _mapping(_context_value(context, "story_context"))
        character = _mapping(_context_value(context, "character_context"))
        design = _design(context)
        storyboard = _storyboard(context)
        panels = _panels(storyboard)

        story_context_available = bool(story)
        premise_available = bool(story.get("premise"))
        chapter_goal_available = bool(story.get("chapter_goal"))
        story_ready = story_context_available and premise_available and chapter_goal_available
        character_context_available = bool(character)
        name_available = bool(character.get("name"))
        motivation_available = bool(character.get("motivation"))
        character_ready = character_context_available and name_available and motivation_available
        page_design_available = bool(design)
        storyboard_available = bool(panels)
        panel_roles = _string_values(design.get("panel_roles"))
        panel_count_matches = bool(panels) and len(panel_roles) == len(panels)
        page_ready = page_design_available and storyboard_available and panel_count_matches
        visual_direction_complete = bool(panels) and all(
            _optional_text(panel.get("camera")) is not None
            and _optional_text(panel.get("composition")) is not None
            and _optional_text(panel.get("background")) is not None
            and _sequence_present(panel.get("characters"))
            for panel in panels
        )
        dialogue_line_count, positioned_dialogue_count = _dialogue_counts(panels)
        voice_evidence_available = bool(_mapping(character.get("voice")).get("style"))
        dialogue_ready = (
            dialogue_line_count == positioned_dialogue_count and voice_evidence_available
        )
        continuity_available, mismatched_fields = _continuity(context)
        continuity_ready = continuity_available and not mismatched_fields

        dimensions = (
            story_ready,
            character_ready,
            page_ready,
            visual_direction_complete,
            dialogue_ready,
            continuity_ready,
        )
        passed_dimensions = sum(dimensions)
        score = round(passed_dimensions / len(dimensions) * 100)
        suggestions = _suggestions(
            story_ready=story_ready,
            character_ready=character_ready,
            page_ready=page_ready,
            visual_direction_complete=visual_direction_complete,
            dialogue_ready=dialogue_ready,
            continuity_ready=continuity_ready,
        )
        findings = tuple(suggestion.message for suggestion in suggestions)

        return ReviewEngineReport(
            story=StoryReviewerDTO(
                story_context_available=story_context_available,
                premise_available=premise_available,
                chapter_goal_available=chapter_goal_available,
                status=_status(story_ready),
            ),
            character=CharacterReviewerDTO(
                character_context_available=character_context_available,
                name_available=name_available,
                motivation_available=motivation_available,
                status=_status(character_ready),
            ),
            page=PageReviewerDTO(
                page_design_available=page_design_available,
                storyboard_available=storyboard_available,
                panel_count_matches=panel_count_matches,
                status=_status(page_ready),
            ),
            art=ArtReviewerDTO(
                storyboard_panel_count=len(panels),
                visual_direction_complete=visual_direction_complete,
                status=_status(visual_direction_complete),
            ),
            dialogue=DialogueReviewerDTO(
                dialogue_line_count=dialogue_line_count,
                positioned_dialogue_count=positioned_dialogue_count,
                voice_evidence_available=voice_evidence_available,
                status=_status(dialogue_ready),
            ),
            continuity=ContinuityReviewerDTO(
                evidence_available=continuity_available,
                mismatched_fields=mismatched_fields,
                status=_status(continuity_ready),
            ),
            quality=QualityScoringEngineDTO(score=score, passed_dimensions=passed_dimensions),
            revision_advisor=RevisionAdvisorDTO(
                suggestions=suggestions,
                manual_review_required=bool(suggestions),
            ),
            prompt_brief=ReviewPromptBriefDTO(
                page_reference=page_reference,
                reused_context_keys=tuple(
                    key
                    for key, value in (
                        ("story_context", story),
                        ("character_context", character),
                        ("page_design", design),
                        ("storyboard", storyboard),
                        ("previous_page", context.metadata.get("previous_page")),
                        ("current_page", context.metadata.get("current_page")),
                    )
                    if value
                ),
            ),
            summary=CommercialMangaReviewSummary(
                project_id=project_id,
                page_reference=page_reference,
                findings=findings,
            ),
        )


def _design(context: WorkflowContext) -> Mapping[str, object]:
    value = context.artifacts.get(PageState.DESIGNED.value, context.metadata.get("page_design"))
    return _mapping(value)


def _storyboard(context: WorkflowContext) -> Mapping[str, object]:
    value = context.artifacts.get(PageState.STORYBOARDED.value, context.artifacts.get("storyboard"))
    return _mapping(value)


def _panels(storyboard: Mapping[str, object]) -> tuple[Mapping[str, object], ...]:
    value = storyboard.get("panels")
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        return ()
    return tuple(_mapping(panel) for panel in value if _mapping(panel))


def _dialogue_counts(panels: tuple[Mapping[str, object], ...]) -> tuple[int, int]:
    dialogue_lines = 0
    positioned_lines = 0
    for panel in panels:
        dialogue = panel.get("dialogue")
        if not isinstance(dialogue, Sequence) or isinstance(dialogue, str | bytes):
            continue
        line_count = len(dialogue)
        dialogue_lines += line_count
        if line_count and _optional_text(panel.get("balloon_position")) is not None:
            positioned_lines += line_count
    return dialogue_lines, positioned_lines


def _continuity(context: WorkflowContext) -> tuple[bool, tuple[str, ...]]:
    previous = _mapping(context.metadata.get("previous_page"))
    current = _mapping(context.metadata.get("current_page", context.page))
    if not previous or not current:
        return False, ()
    fields = ("character", "costume", "props", "time", "location", "emotion")
    return True, tuple(
        field
        for field in fields
        if previous.get(field) is not None
        and current.get(field) is not None
        and previous[field] != current[field]
    )


def _suggestions(
    *,
    story_ready: bool,
    character_ready: bool,
    page_ready: bool,
    visual_direction_complete: bool,
    dialogue_ready: bool,
    continuity_ready: bool,
) -> tuple[RevisionSuggestionDTO, ...]:
    messages: tuple[tuple[SuggestionArea, bool, str], ...] = (
        ("story", story_ready, "Confirm missing story premise or chapter-goal evidence."),
        ("character", character_ready, "Confirm missing character identity or motivation evidence."),
        ("page", page_ready, "Confirm page-design, storyboard, or panel-role evidence."),
        ("art", visual_direction_complete, "Confirm camera, composition, background, and character evidence."),
        ("dialogue", dialogue_ready, "Confirm dialogue placement and voice-style evidence."),
        ("continuity", continuity_ready, "Resolve or document continuity evidence differences."),
    )
    return tuple(
        RevisionSuggestionDTO(area=area, message=message)
        for area, ready, message in messages
        if not ready
    )


def _context_value(context: WorkflowContext, key: str) -> object:
    return context.metadata.get(key) or context.page.get(key)


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _string_values(value: object) -> tuple[str, ...]:
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return tuple(str(item) for item in value if str(item))
    return ()


def _sequence_present(value: object) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, str | bytes) and bool(value)


def _page_reference(context: WorkflowContext) -> str:
    value = context.page.get("id")
    return str(value) if value is not None else "current-page"


def _optional_text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _status(ready: bool) -> ReviewStatus:
    return "ready" if ready else "needs_review"
