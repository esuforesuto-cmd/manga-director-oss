from __future__ import annotations

import pytest
from pydantic import ValidationError

from manga_director.production.next_generation_page_generation_plan import (
    PageGenerationPlan,
    PagePanelSpecification,
    PanelRectangle,
)


def _panel(panel_id: str, order: int, left: int, right: int) -> PagePanelSpecification:
    return PagePanelSpecification(
        panel_id=panel_id,
        order=order,
        rectangle=PanelRectangle(left=left, top=40_000, right=right, bottom=960_000),
        narrative_intent="A distinct moment",
        character_identities=("character-1",),
        continuity_bindings=("continuity-1",),
        action="The character opens a door",
        background="A quiet room at dusk",
        composition="Medium shot, character left of center",
        constraints=("Keep the red scarf",),
    )


def _plan(**changes: object) -> PageGenerationPlan:
    values: dict[str, object] = {
        "plan_id": "plan-1",
        "project_id": "project-1",
        "page_id": "page-1",
        "page_number": 1,
        "storyboard_reference": "storyboard-1",
        "storyboard_sha256": "a" * 64,
        "prompt_built_reference": "prompt-1",
        "prompt_built_sha256": "b" * 64,
        "panel_count": 2,
        "panels": (_panel("panel-1", 1, 50_000, 450_000), _panel("panel-2", 2, 550_000, 950_000)),
    }
    values.update(changes)
    return PageGenerationPlan(**values)


def _coordinate(pixel: int, size: int) -> int:
    return (pixel * 1_000_000 + size - 1) // size


def _grid_panels(panel_count: int) -> tuple[PagePanelSpecification, ...]:
    side = {1: 1, 4: 2, 16: 4}[panel_count]
    width = (1856 - (side - 1) * 48) // side
    height = (2880 - (side - 1) * 48) // side
    panels: list[PagePanelSpecification] = []
    for row in range(side):
        for column in range(side):
            order = len(panels) + 1
            left = 96 + column * (width + 48)
            top = 96 + row * (height + 48)
            panel = _panel("panel-grid", order, 50_000, 950_000).model_copy(
                update={
                    "panel_id": f"panel-{order}",
                    "rectangle": PanelRectangle(
                        left=_coordinate(left, 2048),
                        top=_coordinate(top, 3072),
                        right=_coordinate(left + width, 2048),
                        bottom=_coordinate(top + height, 3072),
                    ),
                }
            )
            panels.append(panel)
    return tuple(panels)


def test_plan_fingerprint_is_canonical_and_immutable() -> None:
    plan = _plan()
    assert len(plan.plan_fingerprint or "") == 64
    with pytest.raises(ValidationError):
        plan.plan_id = "changed"  # type: ignore[misc]
    assert _plan().plan_fingerprint == plan.plan_fingerprint


@pytest.mark.parametrize("panel_count", [1, 4, 16])
def test_profile_accepts_one_four_and_sixteen_panel_plans(panel_count: int) -> None:
    plan = _plan(panel_count=panel_count, panels=_grid_panels(panel_count))
    assert len(plan.panels) == panel_count


@pytest.mark.parametrize("bad_order", [0, 1, 3])
def test_plan_rejects_non_contiguous_panel_orders(bad_order: int) -> None:
    with pytest.raises(ValidationError):
        _plan(
            panels=(
                _panel("panel-1", 1, 50_000, 450_000),
                _panel("panel-2", bad_order, 550_000, 950_000),
            )
        )


def test_plan_rejects_noncanonical_input_order() -> None:
    with pytest.raises(ValidationError):
        _plan(
            panels=(
                _panel("panel-2", 2, 50_000, 450_000),
                _panel("panel-1", 1, 550_000, 950_000),
            )
        )


def test_plan_rejects_overlap_and_duplicate_ids() -> None:
    with pytest.raises(ValidationError):
        _plan(
            panels=(
                _panel("panel-1", 1, 50_000, 600_000),
                _panel("panel-2", 2, 500_000, 950_000),
            )
        )
    with pytest.raises(ValidationError):
        _plan(
            panels=(
                _panel("panel-1", 1, 50_000, 450_000),
                _panel("panel-1", 2, 550_000, 950_000),
            )
        )


def test_plan_rejects_changed_fingerprint() -> None:
    _plan()
    with pytest.raises(ValidationError):
        _plan(plan_fingerprint="c" * 64)


def test_plan_rejects_out_of_bounds_collapsed_and_insufficient_gutter() -> None:
    with pytest.raises(ValidationError):
        _plan(panels=(_panel("panel-1", 1, 1, 2),), panel_count=1)
    with pytest.raises(ValidationError):
        _plan(panels=(_panel("panel-1", 1, 0, 450_000),), panel_count=1)
    with pytest.raises(ValidationError):
        _plan(
            panels=(
                _panel("panel-1", 1, 50_000, 450_000),
                _panel("panel-2", 2, 460_000, 950_000),
            )
        )


def test_plan_rejects_abstract_or_unbounded_prompt_contract() -> None:
    panel = _panel("panel-1", 1, 50_000, 950_000).model_dump()
    panel["narrative_intent"] = "protagonist"
    with pytest.raises(ValidationError):
        _plan(panels=(PagePanelSpecification(**panel),), panel_count=1)
    panel["narrative_intent"] = "A concrete scene"
    panel["constraints"] = ("x" * 513,)
    with pytest.raises(ValidationError):
        PagePanelSpecification(**panel)


@pytest.mark.parametrize("panel_count", [0, 17])
def test_plan_rejects_panel_count_outside_profile(panel_count: int) -> None:
    with pytest.raises(ValidationError):
        _plan(panel_count=panel_count)
