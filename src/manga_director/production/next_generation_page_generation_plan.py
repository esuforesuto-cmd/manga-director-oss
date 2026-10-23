"""Immutable private contracts for panel-aware Page generation."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Literal

from pydantic import ConfigDict, Field, field_validator, model_validator

from manga_director.production.director import DirectorModel

COORDINATE_SCALE = 1_000_000
MAX_PANELS = 16
COMPOSITOR_PROFILE_ID = "md-page-compositor-v1"
CANVAS_WIDTH = 2048
CANVAS_HEIGHT = 3072
MIN_MARGIN_PX = 96
MIN_GUTTER_PX = 48

_LOGICAL_REFERENCE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_ABSTRACT_PROMPT_VALUES = {
    "advance the page purpose",
    "character",
    "continue",
    "continuity",
    "protagonist",
    "same as above",
    "tbd",
}


class _PageGenerationModel(DirectorModel):
    model_config = ConfigDict(
        frozen=True, extra="forbid", strict=True, validate_default=True
    )


class PanelRectangle(_PageGenerationModel):
    """One half-open rectangle in integer normalized coordinates."""

    left: int = Field(ge=0, le=COORDINATE_SCALE)
    top: int = Field(ge=0, le=COORDINATE_SCALE)
    right: int = Field(ge=0, le=COORDINATE_SCALE)
    bottom: int = Field(ge=0, le=COORDINATE_SCALE)

    @model_validator(mode="after")
    def _positive_area(self) -> PanelRectangle:
        if self.left >= self.right or self.top >= self.bottom:
            raise ValueError("panel rectangle must have positive area")
        return self

    def to_pixels(self, width: int, height: int) -> tuple[int, int, int, int]:
        """Convert all endpoints by the profile's required integer floor rule."""

        return (
            self.left * width // COORDINATE_SCALE,
            self.top * height // COORDINATE_SCALE,
            self.right * width // COORDINATE_SCALE,
            self.bottom * height // COORDINATE_SCALE,
        )


class PagePanelSpecification(_PageGenerationModel):
    """One ordered Panel, its frozen geometry, and provider-neutral prompt."""

    panel_id: str
    order: int = Field(ge=1, le=MAX_PANELS)
    rectangle: PanelRectangle
    narrative_intent: str = Field(min_length=1, max_length=4000)
    character_identities: tuple[str, ...] = Field(min_length=1, max_length=32)
    continuity_bindings: tuple[str, ...] = Field(min_length=1, max_length=32)
    action: str = Field(min_length=1, max_length=4000)
    background: str = Field(min_length=1, max_length=4000)
    composition: str = Field(min_length=1, max_length=4000)
    constraints: tuple[str, ...] = Field(min_length=1, max_length=64)

    @field_validator("panel_id", mode="before")
    @classmethod
    def _logical_panel_id(cls, value: object) -> str:
        return logical_reference(value, "panel_id")

    @field_validator(
        "narrative_intent", "action", "background", "composition", mode="before"
    )
    @classmethod
    def _nonblank_prompt_text(cls, value: object) -> str:
        if not isinstance(value, str) or not value.strip() or value != value.strip():
            raise ValueError("panel prompt fields must be non-empty and trimmed")
        if value.casefold() in _ABSTRACT_PROMPT_VALUES:
            raise ValueError("panel prompt fields must be concrete")
        if value.startswith(("# Storyboard", "```")):
            raise ValueError("serialized whole-Page prompts are not Panel prompts")
        return value

    @field_validator("character_identities", "continuity_bindings", "constraints")
    @classmethod
    def _nonblank_prompt_items(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(
            not item
            or item != item.strip()
            or len(item) > 512
            or item.casefold() in _ABSTRACT_PROMPT_VALUES
            for item in values
        ):
            raise ValueError("panel prompt items must be concrete, bounded, and trimmed")
        return values


class PageGenerationPlan(_PageGenerationModel):
    """One immutable Page generation plan and its canonical fingerprint."""

    plan_id: str
    plan_version: Literal[1] = 1
    project_id: str
    page_id: str
    page_number: int = Field(ge=1)
    storyboard_reference: str
    storyboard_sha256: str
    prompt_built_reference: str
    prompt_built_sha256: str
    layout_profile_id: Literal["md-page-compositor-v1"] = COMPOSITOR_PROFILE_ID
    layout_profile_version: Literal[1] = 1
    canvas_width: Literal[2048] = CANVAS_WIDTH
    canvas_height: Literal[3072] = CANVAS_HEIGHT
    margins: tuple[int, int, int, int] = (
        MIN_MARGIN_PX,
        MIN_MARGIN_PX,
        MIN_MARGIN_PX,
        MIN_MARGIN_PX,
    )
    gutter_px: int = Field(default=MIN_GUTTER_PX, ge=MIN_GUTTER_PX)
    panel_count: int = Field(ge=1, le=MAX_PANELS)
    panels: tuple[PagePanelSpecification, ...] = Field(min_length=1, max_length=MAX_PANELS)
    plan_fingerprint: str | None = None

    @field_validator(
        "plan_id",
        "project_id",
        "page_id",
        "storyboard_reference",
        "prompt_built_reference",
        mode="before",
    )
    @classmethod
    def _logical_fields(cls, value: object) -> str:
        return logical_reference(value, "plan reference")

    @field_validator("storyboard_sha256", "prompt_built_sha256")
    @classmethod
    def _sha256(cls, value: str) -> str:
        return sha256_digest(value)

    @field_validator("margins")
    @classmethod
    def _margin_bounds(cls, value: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        if len(value) != 4 or any(margin < MIN_MARGIN_PX for margin in value):
            raise ValueError("all margins must be at least 96 pixels")
        if value[1] + value[3] >= CANVAS_WIDTH or value[0] + value[2] >= CANVAS_HEIGHT:
            raise ValueError("margins must leave a positive content area")
        return value

    @model_validator(mode="after")
    def _validate_plan(self) -> PageGenerationPlan:
        if self.panel_count != len(self.panels):
            raise ValueError("panel_count must equal the number of panels")
        if tuple(panel.order for panel in self.panels) != tuple(
            range(1, self.panel_count + 1)
        ):
            raise ValueError("panel order must be explicit, contiguous, and canonical")
        if len({panel.panel_id for panel in self.panels}) != self.panel_count:
            raise ValueError("panel IDs must be unique")
        validate_geometry(
            tuple(panel.rectangle for panel in self.panels),
            self.canvas_width,
            self.canvas_height,
            self.margins,
            self.gutter_px,
        )
        expected = canonical_digest(
            self.model_dump(mode="json", exclude={"plan_fingerprint"})
        )
        if self.plan_fingerprint is not None and self.plan_fingerprint != expected:
            raise ValueError("plan_fingerprint does not match canonical plan content")
        object.__setattr__(self, "plan_fingerprint", expected)
        return self


def validate_geometry(
    rectangles: tuple[PanelRectangle, ...],
    width: int,
    height: int,
    margins: tuple[int, int, int, int],
    gutter: int,
) -> tuple[tuple[int, int, int, int], ...]:
    """Validate frozen pixel-space bounds and return canonical pixel rectangles."""

    top, right, bottom, left = margins
    pixel_rectangles: list[tuple[int, int, int, int]] = []
    for rectangle in rectangles:
        bounds = rectangle.to_pixels(width, height)
        x0, y0, x1, y1 = bounds
        if x0 >= x1 or y0 >= y1:
            raise ValueError("panel rectangle collapses after pixel conversion")
        if x0 < left or x1 > width - right or y0 < top or y1 > height - bottom:
            raise ValueError("panel rectangle exceeds content margins")
        pixel_rectangles.append(bounds)
    for index, first in enumerate(pixel_rectangles):
        for second in pixel_rectangles[index + 1 :]:
            if _overlaps(first, second):
                raise ValueError("panel rectangles must not overlap")
            gap_x = max(0, max(first[0], second[0]) - min(first[2], second[2]))
            gap_y = max(0, max(first[1], second[1]) - min(first[3], second[3]))
            if max(gap_x, gap_y) < gutter:
                raise ValueError("panel rectangles do not meet minimum gutter")
    return tuple(pixel_rectangles)


def _overlaps(first: tuple[int, int, int, int], second: tuple[int, int, int, int]) -> bool:
    return (
        first[0] < second[2]
        and second[0] < first[2]
        and first[1] < second[3]
        and second[1] < first[3]
    )


def canonical_digest(value: object) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def logical_reference(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or _LOGICAL_REFERENCE.fullmatch(value) is None
        or any(marker in value.casefold() for marker in ("secret", "token", "credential"))
    ):
        raise ValueError(f"{label} must be a safe logical reference")
    return value


def sha256_digest(value: str) -> str:
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ValueError("expected lowercase SHA-256 digest")
    return value
