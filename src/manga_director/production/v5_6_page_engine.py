"""Read-only v5.6 Page Engine v1 for commercial manga page design evidence.

This module evaluates one existing page design and storyboard projection. It
does not create a name, alter panels, generate dialogue, or change the workflow.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Literal

from manga_director.domain.state_machine import PageState
from manga_director.production.director import DirectorModel
from manga_director.workflow.contracts import WorkflowContext

EvidenceStatus = Literal["ready", "needs_evidence"]


class PagePlannerDTO(DirectorModel):
    """One-page purpose, emotion, and hook evidence."""

    project_id: str
    page_reference: str
    current_state: PageState
    purpose_available: bool
    reader_emotion_available: bool
    hook_available: bool
    panel_count: int
    page_count: Literal[1] = 1
    status: EvidenceStatus
    page_changed: Literal[False] = False


class PanelLayoutDTO(DirectorModel):
    """Panel-order and role evidence without modifying the storyboard."""

    storyboard_available: bool
    panel_numbers: tuple[int, ...] = ()
    panel_roles: tuple[str, ...] = ()
    layout_valid: bool
    status: EvidenceStatus
    layout_changed: Literal[False] = False


class CameraDirectorDTO(DirectorModel):
    """Camera direction evidence for every declared storyboard panel."""

    camera_count: int
    camera_consistent: bool
    status: EvidenceStatus
    camera_changed: Literal[False] = False


class ReaderFlowDTO(DirectorModel):
    """Reader-flow evidence based on ordered panels and focal direction."""

    panel_order_valid: bool
    focal_direction_available: bool
    reader_flow_valid: bool
    status: EvidenceStatus
    flow_changed: Literal[False] = False


class DialogueLayoutDTO(DirectorModel):
    """Dialogue placement evidence without writing or moving dialogue."""

    dialogue_line_count: int
    positioned_dialogue_count: int
    placement_valid: bool
    status: EvidenceStatus
    dialogue_changed: Literal[False] = False


class SceneTransitionManagerDTO(DirectorModel):
    """Scene-transition evidence for the current page hand-off."""

    transition_available: bool
    story_context_available: bool
    transition_valid: bool
    status: EvidenceStatus
    transition_changed: Literal[False] = False


class ImpactPanelManagerDTO(DirectorModel):
    """Impact-panel evidence for a planned reveal, turn, or page hook."""

    big_moment_available: bool
    impact_panel_available: bool
    hook_available: bool
    impact_valid: bool
    status: EvidenceStatus
    impact_changed: Literal[False] = False


class PagePromptBriefDTO(DirectorModel):
    """Compact prompt constraints that reuse approved page evidence by key."""

    page_reference: str
    compact_instruction: str = (
        "Create exactly one page using supplied page and storyboard evidence; preserve panel order, "
        "camera, reader flow, dialogue placement, transition, and impact constraints."
    )
    reused_context_keys: tuple[str, ...] = ()
    duplicate_context_elided: bool = True
    prompt_generated: Literal[False] = False


class CommercialMangaPageSummary(DirectorModel):
    """Boundary record for the Commercial Manga Page Standard."""

    project_id: str
    page_reference: str
    standard_stages: tuple[str, ...] = (
        "page_plan",
        "panel_layout",
        "camera_direction",
        "reader_flow",
        "dialogue_layout",
        "scene_transition",
        "impact_panel",
    )
    layout_changed: Literal[False] = False
    storyboard_changed: Literal[False] = False
    dialogue_changed: Literal[False] = False
    automatic_action_taken: Literal[False] = False
    findings: tuple[str, ...] = ()


class PageEngineReport(DirectorModel):
    """Transport-neutral Page Engine v1 report for one immutable context."""

    planner: PagePlannerDTO
    panel_layout: PanelLayoutDTO
    camera: CameraDirectorDTO
    reader_flow: ReaderFlowDTO
    dialogue_layout: DialogueLayoutDTO
    scene_transition: SceneTransitionManagerDTO
    impact_panel: ImpactPanelManagerDTO
    prompt_brief: PagePromptBriefDTO
    summary: CommercialMangaPageSummary
    analysis_only: Literal[True] = True


class V56PageEngineService:
    """Build a read-only Commercial Manga Page Standard report for one page."""

    def page_engine(self, project_id: str, context: WorkflowContext) -> PageEngineReport:
        page_reference = _page_reference(context)
        design = _design(context)
        storyboard = _storyboard(context)
        panels = _panels(storyboard)
        panel_roles = _string_values(design.get("panel_roles"))
        panel_count = _positive_int(design.get("panel_count"), len(panel_roles))
        panel_numbers = _panel_numbers(panels)
        ordered_panels = panel_numbers == tuple(range(1, len(panels) + 1))
        storyboard_available = bool(panels)
        purpose_available = bool(design.get("purpose"))
        reader_emotion_available = bool(design.get("reader_emotion"))
        hook_available = bool(design.get("hook"))
        layout_valid = storyboard_available and ordered_panels and len(panel_roles) == len(panels)
        camera_count = sum(1 for panel in panels if _optional_text(panel.get("camera")) is not None)
        camera_consistent = bool(panels) and camera_count == len(panels)
        focal_direction_available = all(
            _optional_text(panel.get("composition")) is not None for panel in panels
        )
        reader_flow_valid = ordered_panels and focal_direction_available and reader_emotion_available
        dialogue_line_count, positioned_dialogue_count = _dialogue_counts(panels)
        placement_valid = dialogue_line_count == positioned_dialogue_count
        transition_available = bool(design.get("scene_transition"))
        story_context_available = bool(_context_value(context, "story_context"))
        transition_valid = transition_available and story_context_available
        big_moment_available = bool(design.get("big_moment"))
        impact_panel_available = any(role in {"big moment", "impact"} for role in panel_roles)
        impact_valid = big_moment_available and impact_panel_available and hook_available
        findings = _findings(
            purpose_available=purpose_available,
            reader_emotion_available=reader_emotion_available,
            hook_available=hook_available,
            storyboard_available=storyboard_available,
            layout_valid=layout_valid,
            camera_consistent=camera_consistent,
            reader_flow_valid=reader_flow_valid,
            placement_valid=placement_valid,
            transition_valid=transition_valid,
            impact_valid=impact_valid,
        )

        return PageEngineReport(
            planner=PagePlannerDTO(
                project_id=project_id,
                page_reference=page_reference,
                current_state=context.state,
                purpose_available=purpose_available,
                reader_emotion_available=reader_emotion_available,
                hook_available=hook_available,
                panel_count=panel_count,
                status=_status(purpose_available and reader_emotion_available and hook_available),
            ),
            panel_layout=PanelLayoutDTO(
                storyboard_available=storyboard_available,
                panel_numbers=panel_numbers,
                panel_roles=panel_roles,
                layout_valid=layout_valid,
                status=_status(layout_valid),
            ),
            camera=CameraDirectorDTO(
                camera_count=camera_count,
                camera_consistent=camera_consistent,
                status=_status(camera_consistent),
            ),
            reader_flow=ReaderFlowDTO(
                panel_order_valid=ordered_panels,
                focal_direction_available=focal_direction_available,
                reader_flow_valid=reader_flow_valid,
                status=_status(reader_flow_valid),
            ),
            dialogue_layout=DialogueLayoutDTO(
                dialogue_line_count=dialogue_line_count,
                positioned_dialogue_count=positioned_dialogue_count,
                placement_valid=placement_valid,
                status=_status(placement_valid),
            ),
            scene_transition=SceneTransitionManagerDTO(
                transition_available=transition_available,
                story_context_available=story_context_available,
                transition_valid=transition_valid,
                status=_status(transition_valid),
            ),
            impact_panel=ImpactPanelManagerDTO(
                big_moment_available=big_moment_available,
                impact_panel_available=impact_panel_available,
                hook_available=hook_available,
                impact_valid=impact_valid,
                status=_status(impact_valid),
            ),
            prompt_brief=PagePromptBriefDTO(
                page_reference=page_reference,
                reused_context_keys=tuple(
                    key
                    for key, value in (
                        ("page_design", design),
                        ("storyboard", storyboard),
                        ("story_context", _context_value(context, "story_context")),
                        ("character_context", _context_value(context, "character_context")),
                    )
                    if value
                ),
            ),
            summary=CommercialMangaPageSummary(
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


def _panel_numbers(panels: tuple[Mapping[str, object], ...]) -> tuple[int, ...]:
    values: list[int] = []
    for panel in panels:
        number = panel.get("number")
        if not isinstance(number, int) or isinstance(number, bool):
            return ()
        values.append(number)
    return tuple(values)


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


def _context_value(context: WorkflowContext, key: str) -> object:
    return context.metadata.get(key) or context.page.get(key)


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _string_values(value: object) -> tuple[str, ...]:
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return tuple(str(item) for item in value if str(item))
    return ()


def _positive_int(value: object, fallback: int) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else fallback


def _page_reference(context: WorkflowContext) -> str:
    value = context.page.get("id")
    return str(value) if value is not None else "current-page"


def _optional_text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _status(valid: bool) -> EvidenceStatus:
    return "ready" if valid else "needs_evidence"


def _findings(
    *,
    purpose_available: bool,
    reader_emotion_available: bool,
    hook_available: bool,
    storyboard_available: bool,
    layout_valid: bool,
    camera_consistent: bool,
    reader_flow_valid: bool,
    placement_valid: bool,
    transition_valid: bool,
    impact_valid: bool,
) -> tuple[str, ...]:
    findings: list[str] = []
    for name, available in (
        ("page purpose", purpose_available),
        ("reader emotion", reader_emotion_available),
        ("page hook", hook_available),
        ("storyboard", storyboard_available),
        ("panel layout", layout_valid),
        ("camera direction", camera_consistent),
        ("reader flow", reader_flow_valid),
        ("dialogue placement", placement_valid),
        ("scene transition", transition_valid),
        ("impact panel", impact_valid),
    ):
        if not available:
            findings.append(f"Missing or invalid {name} evidence.")
    return tuple(findings)
