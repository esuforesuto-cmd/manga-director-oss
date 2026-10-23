"""Pure contracts for complete-set deterministic Page composition."""

from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict, Field, field_validator, model_validator

from manga_director.production.director import DirectorModel
from manga_director.production.next_generation_page_generation_plan import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    COMPOSITOR_PROFILE_ID,
    MIN_GUTTER_PX,
    MIN_MARGIN_PX,
    PanelRectangle,
    canonical_digest,
    logical_reference,
    sha256_digest,
    validate_geometry,
)


class _CompositionModel(DirectorModel):
    model_config = ConfigDict(
        frozen=True, extra="forbid", strict=True, validate_default=True
    )


class AcceptedPanelSource(_CompositionModel):
    plan_id: str
    plan_fingerprint: str
    project_id: str
    page_id: str
    panel_id: str
    panel_order: int = Field(ge=1, le=16)
    request_id: str
    request_fingerprint: str
    attempt_id: str
    evidence_id: str
    asset_id: str
    content_sha256: str
    width: int = Field(gt=0, le=4096)
    height: int = Field(gt=0, le=4096)
    media_type: Literal["image/png"] = "image/png"
    rectangle: PanelRectangle

    @field_validator(
        "plan_id",
        "project_id",
        "page_id",
        "panel_id",
        "request_id",
        "attempt_id",
        "evidence_id",
        "asset_id",
        mode="before",
    )
    @classmethod
    def _references(cls, value: object) -> str:
        return logical_reference(value, "composition source reference")

    @field_validator("plan_fingerprint", "request_fingerprint", "content_sha256")
    @classmethod
    def _sha256(cls, value: str) -> str:
        return sha256_digest(value)


class PageCompositionRequest(_CompositionModel):
    composition_attempt_id: str
    plan_id: str
    plan_fingerprint: str
    project_id: str
    page_id: str
    source_state: Literal["PromptBuilt"] = "PromptBuilt"
    target_state: Literal["Generated"] = "Generated"
    explicit_authorization_reference: str
    composition_provenance_reference: str
    compositor_profile_id: Literal["md-page-compositor-v1"] = COMPOSITOR_PROFILE_ID
    compositor_profile_version: Literal[1] = 1
    canvas_width: Literal[2048] = CANVAS_WIDTH
    canvas_height: Literal[3072] = CANVAS_HEIGHT
    margins: tuple[int, int, int, int] = (
        MIN_MARGIN_PX,
        MIN_MARGIN_PX,
        MIN_MARGIN_PX,
        MIN_MARGIN_PX,
    )
    gutter_px: int = Field(default=MIN_GUTTER_PX, ge=MIN_GUTTER_PX)
    pixel_fit_policy: Literal["cover-center"] = "cover-center"
    color_policy: Literal["srgb-rgba-on-white-v1"] = "srgb-rgba-on-white-v1"
    encoder_profile: Literal["rgb8-png-stored-deflate-v1"] = (
        "rgb8-png-stored-deflate-v1"
    )
    panel_count: int = Field(ge=1, le=16)
    sources: tuple[AcceptedPanelSource, ...] = Field(min_length=1, max_length=16)
    request_fingerprint: str | None = None

    @field_validator(
        "composition_attempt_id",
        "plan_id",
        "project_id",
        "page_id",
        "explicit_authorization_reference",
        "composition_provenance_reference",
        mode="before",
    )
    @classmethod
    def _logical_reference(cls, value: object) -> str:
        return logical_reference(value, "composition reference")

    @field_validator("plan_fingerprint")
    @classmethod
    def _plan_hash(cls, value: str) -> str:
        return sha256_digest(value)

    @field_validator("margins")
    @classmethod
    def _margins(cls, value: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        if len(value) != 4 or any(item < MIN_MARGIN_PX for item in value):
            raise ValueError("all composition margins must be at least 96 pixels")
        if value[1] + value[3] >= CANVAS_WIDTH or value[0] + value[2] >= CANVAS_HEIGHT:
            raise ValueError("composition margins must leave a positive content area")
        return value

    @model_validator(mode="after")
    def _canonical_complete_sources(self) -> PageCompositionRequest:
        if len(self.sources) != self.panel_count:
            raise ValueError("sources must contain the plan's complete Panel set")
        _validate_source_manifest(self.sources)
        for source in self.sources:
            if (
                source.plan_id != self.plan_id
                or source.plan_fingerprint != self.plan_fingerprint
                or source.project_id != self.project_id
                or source.page_id != self.page_id
            ):
                raise ValueError("every source must match the exact plan and Page binding")
        validate_geometry(
            tuple(source.rectangle for source in self.sources),
            self.canvas_width,
            self.canvas_height,
            self.margins,
            self.gutter_px,
        )
        if sum(source.width * source.height for source in self.sources) > 32_000_000:
            raise ValueError("source manifest exceeds the aggregate pixel limit")
        expected = canonical_digest(
            self.model_dump(mode="json", exclude={"request_fingerprint"})
        )
        if self.request_fingerprint is not None and self.request_fingerprint != expected:
            raise ValueError("request fingerprint does not match composition inputs")
        object.__setattr__(self, "request_fingerprint", expected)
        return self


class PageCompositionAttempt(_CompositionModel):
    """One local deterministic composition operation; never a Provider attempt."""

    composition_attempt_id: str
    request_fingerprint: str
    plan_id: str
    plan_fingerprint: str
    project_id: str
    page_id: str
    explicit_authorization_reference: str
    composition_provenance_reference: str
    compositor_profile_id: Literal["md-page-compositor-v1"] = COMPOSITOR_PROFILE_ID
    compositor_profile_version: Literal[1] = 1
    ordered_source_asset_ids: tuple[str, ...] = Field(min_length=1, max_length=16)
    ordered_source_hashes: tuple[str, ...] = Field(min_length=1, max_length=16)
    outcome: Literal["reserved", "completed", "failed", "recovery_required"] = "reserved"

    @field_validator(
        "composition_attempt_id",
        "plan_id",
        "project_id",
        "page_id",
        "explicit_authorization_reference",
        "composition_provenance_reference",
        mode="before",
    )
    @classmethod
    def _attempt_references(cls, value: object) -> str:
        return logical_reference(value, "composition attempt reference")

    @field_validator("ordered_source_asset_ids")
    @classmethod
    def _source_ids(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        validated = tuple(logical_reference(value, "source asset") for value in values)
        if len(set(validated)) != len(validated):
            raise ValueError("composition source assets must be unique")
        return validated

    @field_validator("request_fingerprint", "plan_fingerprint")
    @classmethod
    def _attempt_digest(cls, value: str) -> str:
        return sha256_digest(value)

    @field_validator("ordered_source_hashes")
    @classmethod
    def _source_hashes(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(sha256_digest(value) for value in values)

    @model_validator(mode="after")
    def _same_source_cardinality(self) -> PageCompositionAttempt:
        if len(self.ordered_source_asset_ids) != len(self.ordered_source_hashes):
            raise ValueError("composition source IDs and hashes must have equal cardinality")
        return self


class PageCompositionEvidence(_CompositionModel):
    evidence_id: str
    composition_attempt_id: str
    plan_id: str
    plan_fingerprint: str
    project_id: str
    page_id: str
    request_fingerprint: str
    operation_kind: Literal["deterministic_page_composition"] = "deterministic_page_composition"
    provider_invocation_performed: Literal[False] = False
    composition_provenance_reference: str
    compositor_profile_id: Literal["md-page-compositor-v1"] = COMPOSITOR_PROFILE_ID
    compositor_profile_version: Literal[1] = 1
    ordered_sources: tuple[AcceptedPanelSource, ...] = Field(min_length=1, max_length=16)
    output_asset_id: str | None = None
    output_sha256: str | None = None
    outcome: Literal["completed", "failed", "recovery_required"]

    @field_validator(
        "composition_attempt_id",
        "evidence_id",
        "plan_id",
        "project_id",
        "page_id",
        "composition_provenance_reference",
        mode="before",
    )
    @classmethod
    def _references(cls, value: object) -> str:
        return logical_reference(value, "composition evidence reference")

    @field_validator("output_asset_id")
    @classmethod
    def _output_reference(cls, value: str | None) -> str | None:
        return None if value is None else logical_reference(value, "composite asset")

    @field_validator("plan_fingerprint", "request_fingerprint")
    @classmethod
    def _evidence_digests(cls, value: str) -> str:
        return sha256_digest(value)

    @field_validator("output_sha256")
    @classmethod
    def _output_digest(cls, value: str | None) -> str | None:
        return None if value is None else sha256_digest(value)

    @model_validator(mode="after")
    def _terminal_binding(self) -> PageCompositionEvidence:
        _validate_source_manifest(self.ordered_sources)
        for source in self.ordered_sources:
            if (
                source.plan_id != self.plan_id
                or source.plan_fingerprint != self.plan_fingerprint
                or source.project_id != self.project_id
                or source.page_id != self.page_id
            ):
                raise ValueError("evidence sources must match its exact plan and Page")
        if self.outcome == "completed":
            if self.output_asset_id is None or self.output_sha256 is None:
                raise ValueError("completed composition evidence requires one output")
        elif self.output_asset_id is not None or self.output_sha256 is not None:
            raise ValueError("non-success composition evidence cannot name an output")
        return self


class PageCompositeAsset(_CompositionModel):
    """Registered deterministic Page output and its complete source manifest."""

    composition_attempt_id: str
    request_fingerprint: str
    composition_provenance_reference: str
    ordered_sources: tuple[AcceptedPanelSource, ...] = Field(min_length=1, max_length=16)
    asset_id: str
    width: Literal[2048] = CANVAS_WIDTH
    height: Literal[3072] = CANVAS_HEIGHT
    media_type: Literal["image/png"] = "image/png"
    content_sha256: str

    @field_validator(
        "composition_attempt_id",
        "composition_provenance_reference",
        "asset_id",
        mode="before",
    )
    @classmethod
    def _asset_references(cls, value: object) -> str:
        return logical_reference(value, "composite asset reference")

    @field_validator("request_fingerprint", "content_sha256")
    @classmethod
    def _asset_digests(cls, value: str) -> str:
        return sha256_digest(value)

    @model_validator(mode="after")
    def _canonical_source_manifest(self) -> PageCompositeAsset:
        _validate_source_manifest(self.ordered_sources)
        bindings = {
            (
                source.plan_id,
                source.plan_fingerprint,
                source.project_id,
                source.page_id,
            )
            for source in self.ordered_sources
        }
        if len(bindings) != 1:
            raise ValueError("composite sources must share one exact plan and Page binding")
        return self


def _validate_source_manifest(sources: tuple[AcceptedPanelSource, ...]) -> None:
    if [source.panel_order for source in sources] != list(range(1, len(sources) + 1)):
        raise ValueError("sources must remain in canonical contiguous Panel order")
    unique_fields = {
        "Panel IDs": (source.panel_id for source in sources),
        "request IDs": (source.request_id for source in sources),
        "attempt IDs": (source.attempt_id for source in sources),
        "evidence IDs": (source.evidence_id for source in sources),
        "asset IDs": (source.asset_id for source in sources),
    }
    for label, values in unique_fields.items():
        resolved = tuple(values)
        if len(set(resolved)) != len(resolved):
            raise ValueError(f"source {label} must be unique")
