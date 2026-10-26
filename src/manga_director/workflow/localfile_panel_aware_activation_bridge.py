"""Private deterministic LocalFile snapshot-to-panel-plan conversion."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Final, Literal, TypedDict, cast

from manga_director.domain.project import Page
from manga_director.domain.state_machine import PageState
from manga_director.production.next_generation_page_generation_plan import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    COMPOSITOR_PROFILE_ID,
    MIN_GUTTER_PX,
    MIN_MARGIN_PX,
    PageGenerationPlan,
    PagePanelSpecification,
    PanelRectangle,
    logical_reference,
    sha256_digest,
)
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.repositories.local_file_durability import RevisionedProjectSnapshot

_LAYOUT_PROFILE_VERSION: Final[Literal[1]] = 1
_MARGINS = (MIN_MARGIN_PX, MIN_MARGIN_PX, MIN_MARGIN_PX, MIN_MARGIN_PX)


class _SourcePanelV1(TypedDict):
    number: int
    narrative_intent: str
    character_identities: list[str]
    continuity_bindings: list[str]
    action: str
    background: str
    composition: str
    constraints: list[str]
    rectangle: dict[str, int]


@dataclass(frozen=True, slots=True)
class _PageGenerationPlanConversion:
    """Private source-binding evidence retained for later V7-14 slices."""

    plan: PageGenerationPlan
    source_binding_json: str
    source_binding_sha256: str


def _convert_revisioned_page_snapshot(
    repository: LocalFileRepository,
    snapshot: RevisionedProjectSnapshot,
    *,
    page_number: int,
    layout_profile_id: str,
    layout_profile_version: int,
    rectangles: tuple[PanelRectangle, ...],
) -> _PageGenerationPlanConversion:
    """Convert one authoritative PromptBuilt snapshot without inference or repair."""

    authoritative_snapshot = _require_authoritative_snapshot(repository, snapshot)
    project_id, page_id, source_page_number, page_revision, page_fingerprint, page = (
        _snapshot_page_binding(authoritative_snapshot, page_number)
    )
    _require_supported_layout(layout_profile_id, layout_profile_version, rectangles)

    storyboard, storyboard_json = _capture_artifact(page.storyboard, "Page.storyboard")
    prompt_built, prompt_built_json = _capture_artifact(page.prompt, "Page.prompt")
    if type(prompt_built.get("prompt_markdown")) is not str:
        raise ValueError("Page.prompt must contain an exact prompt_markdown string")

    storyboard_sha256 = _sha256(storyboard_json.encode("utf-8"))
    prompt_built_sha256 = _sha256(prompt_built_json.encode("utf-8"))
    storyboard_reference = f"storyboard-v7-014-{storyboard_sha256}"
    prompt_built_reference = f"prompt-v7-014-{prompt_built_sha256}"

    source_panels = _source_panels(storyboard, rectangles)

    source_binding_v1: dict[str, object] = {
        "kind": "source_binding_v1",
        "version": 1,
        "project_id": project_id,
        "page_id": page_id,
        "page_number": source_page_number,
        "page_revision": page_revision,
        "page_fingerprint": page_fingerprint,
        "storyboard_reference": storyboard_reference,
        "storyboard_sha256": storyboard_sha256,
        "prompt_built_reference": prompt_built_reference,
        "prompt_built_sha256": prompt_built_sha256,
        "layout": {
            "profile_id": COMPOSITOR_PROFILE_ID,
            "profile_version": _LAYOUT_PROFILE_VERSION,
            "canvas_width": CANVAS_WIDTH,
            "canvas_height": CANVAS_HEIGHT,
            "margins": list(_MARGINS),
            "gutter_px": MIN_GUTTER_PX,
        },
        "panels": source_panels,
    }
    source_binding_json = _canonical_json(source_binding_v1)
    source_binding_sha256 = _sha256(source_binding_json.encode("utf-8"))
    plan_id = f"plan-v7-014-{source_binding_sha256}"

    panel_specs: list[PagePanelSpecification] = []
    for source_panel, rectangle in zip(source_panels, rectangles, strict=True):
        order = source_panel["number"]
        panel_id_preimage = {
            "kind": "panel_id_v1",
            "version": 1,
            "source_binding_sha256": source_binding_sha256,
            "panel_order": order,
        }
        panel_id = f"panel-v7-014-{_sha256(_canonical_json(panel_id_preimage).encode('utf-8'))}"
        panel_specs.append(
            PagePanelSpecification(
                panel_id=panel_id,
                order=order,
                rectangle=rectangle,
                narrative_intent=source_panel["narrative_intent"],
                character_identities=tuple(source_panel["character_identities"]),
                continuity_bindings=tuple(source_panel["continuity_bindings"]),
                action=source_panel["action"],
                background=source_panel["background"],
                composition=source_panel["composition"],
                constraints=tuple(source_panel["constraints"]),
            )
        )

    plan = PageGenerationPlan(
        plan_id=plan_id,
        project_id=project_id,
        page_id=page_id,
        page_number=source_page_number,
        storyboard_reference=storyboard_reference,
        storyboard_sha256=storyboard_sha256,
        prompt_built_reference=prompt_built_reference,
        prompt_built_sha256=prompt_built_sha256,
        layout_profile_id=COMPOSITOR_PROFILE_ID,
        layout_profile_version=_LAYOUT_PROFILE_VERSION,
        canvas_width=CANVAS_WIDTH,
        canvas_height=CANVAS_HEIGHT,
        margins=_MARGINS,
        gutter_px=MIN_GUTTER_PX,
        panel_count=len(panel_specs),
        panels=tuple(panel_specs),
    )
    return _PageGenerationPlanConversion(
        plan=plan,
        source_binding_json=source_binding_json,
        source_binding_sha256=source_binding_sha256,
    )


def _require_authoritative_snapshot(
    repository: LocalFileRepository, snapshot: RevisionedProjectSnapshot
) -> RevisionedProjectSnapshot:
    if type(repository) is not LocalFileRepository:
        raise ValueError("the authoritative LocalFile repository is required")
    if type(snapshot) is not RevisionedProjectSnapshot:
        raise ValueError("an authoritative revisioned Page snapshot is required")
    authoritative = repository._load_revisioned(snapshot.project.id)
    if (
        authoritative.revision != snapshot.revision
        or authoritative.fingerprint != snapshot.fingerprint
        or authoritative.project != snapshot.project
    ):
        raise ValueError("revisioned Page snapshot does not match LocalFile authority")
    return authoritative


def _snapshot_page_binding(
    snapshot: RevisionedProjectSnapshot, page_number: int
) -> tuple[str, str, int, str, str, Page]:
    if type(page_number) is not int or page_number <= 0:
        raise ValueError("page_number must be a positive integer")
    if type(snapshot.revision) is not int or snapshot.revision <= 0:
        raise ValueError("snapshot revision must be a positive integer")
    page_fingerprint = sha256_digest(snapshot.fingerprint)
    project_id = logical_reference(snapshot.project.id, "project_id")
    page_revision = logical_reference(f"revision-{snapshot.revision}", "page_revision")

    page = snapshot.project.page(page_number)
    if (
        type(page.page_number) is not int
        or page.page_number <= 0
        or page.page_number != page_number
        or page.state is not PageState.PROMPT_BUILT
    ):
        raise ValueError("snapshot Page must be the requested PromptBuilt Page")
    source_page_number = page.page_number
    page_id = str(source_page_number)
    return (
        project_id,
        page_id,
        source_page_number,
        page_revision,
        page_fingerprint,
        page,
    )


def _require_supported_layout(
    layout_profile_id: str,
    layout_profile_version: int,
    rectangles: tuple[PanelRectangle, ...],
) -> None:
    if layout_profile_id != COMPOSITOR_PROFILE_ID:
        raise ValueError("layout profile is unsupported")
    if (
        type(layout_profile_version) is not int
        or layout_profile_version != _LAYOUT_PROFILE_VERSION
    ):
        raise ValueError("layout profile version is unsupported")
    if type(rectangles) is not tuple or any(
        type(rectangle) is not PanelRectangle for rectangle in rectangles
    ):
        raise ValueError("layout rectangles must be an ordered PanelRectangle tuple")


def _source_panels(
    storyboard: dict[str, object], rectangles: tuple[PanelRectangle, ...]
) -> list[_SourcePanelV1]:
    panels = storyboard.get("panels")
    if type(panels) is not list or not panels:
        raise ValueError("Page.storyboard panels must be a non-empty ordered list")
    ordered_panels = cast(list[object], panels)
    if len(rectangles) != len(ordered_panels):
        raise ValueError("layout must provide exactly one rectangle per panel")

    source_panels: list[_SourcePanelV1] = []
    for expected_number, (panel, rectangle) in enumerate(
        zip(ordered_panels, rectangles, strict=True), start=1
    ):
        if type(panel) is not dict:
            raise ValueError("each persisted Storyboard panel must be an object")
        panel_values = cast(dict[str, object], panel)
        number = panel_values.get("number")
        if type(number) is not int or number != expected_number:
            raise ValueError("panel numbers must be strict integers in persisted 1..N order")
        source_panels.append(
            {
                "number": number,
                "narrative_intent": _required_string(panel_values, "narrative_intent"),
                "character_identities": _required_string_list(
                    panel_values, "characters"
                ),
                "continuity_bindings": _required_string_list(
                    panel_values, "continuity_bindings"
                ),
                "action": _required_string(panel_values, "action"),
                "background": _required_string(panel_values, "background"),
                "composition": _required_string(panel_values, "composition"),
                "constraints": _required_string_list(panel_values, "constraints"),
                "rectangle": {
                    "left": rectangle.left,
                    "top": rectangle.top,
                    "right": rectangle.right,
                    "bottom": rectangle.bottom,
                },
            }
        )
    return source_panels


def _capture_artifact(value: object, label: str) -> tuple[dict[str, object], str]:
    if type(value) is not dict:
        raise ValueError(f"{label} must be a persisted dictionary")
    try:
        canonical = _canonical_json(value)
        captured = json.loads(canonical)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must contain canonical JSON values") from exc
    if type(captured) is not dict:
        raise ValueError(f"{label} must be a persisted dictionary")
    return cast(dict[str, object], captured), canonical


def _required_value(panel: dict[str, object], key: str) -> object:
    if key not in panel:
        raise ValueError(f"Storyboard panel requires explicit {key}")
    return panel[key]


def _required_string(panel: dict[str, object], key: str) -> str:
    value = _required_value(panel, key)
    if type(value) is not str:
        raise ValueError(f"Storyboard panel requires explicit string {key}")
    return value


def _required_string_list(panel: dict[str, object], key: str) -> list[str]:
    value = _required_value(panel, key)
    if type(value) is not list or not value or any(type(item) is not str for item in value):
        raise ValueError(f"Storyboard panel {key} must be a non-empty ordered string list")
    return cast(list[str], value)


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()
