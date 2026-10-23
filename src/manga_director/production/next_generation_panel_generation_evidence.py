"""Immutable, exact-binding evidence contracts for Panel outputs."""

from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict, Field, field_validator, model_validator

from manga_director.production.director import DirectorModel
from manga_director.production.next_generation_page_generation_plan import (
    logical_reference,
    sha256_digest,
)


class _PanelEvidenceModel(DirectorModel):
    model_config = ConfigDict(
        frozen=True, extra="forbid", strict=True, validate_default=True
    )


class PanelAsset(_PanelEvidenceModel):
    """One accepted Provider output bound to one exact Panel attempt."""

    asset_id: str
    plan_id: str
    plan_fingerprint: str
    project_id: str
    page_id: str
    panel_id: str
    panel_order: int = Field(ge=1, le=16)
    request_id: str
    request_fingerprint: str
    attempt_id: str
    media_type: Literal["image/png"] = "image/png"
    width: int = Field(gt=0, le=4096)
    height: int = Field(gt=0, le=4096)
    content_sha256: str

    @field_validator(
        "asset_id",
        "plan_id",
        "project_id",
        "page_id",
        "panel_id",
        "request_id",
        "attempt_id",
        mode="before",
    )
    @classmethod
    def _references(cls, value: object) -> str:
        return logical_reference(value, "Panel asset reference")

    @field_validator("plan_fingerprint", "request_fingerprint", "content_sha256")
    @classmethod
    def _digests(cls, value: str) -> str:
        return sha256_digest(value)


class PanelGenerationEvidence(_PanelEvidenceModel):
    evidence_id: str
    plan_id: str
    plan_fingerprint: str
    project_id: str
    page_id: str
    panel_id: str
    panel_order: int = Field(ge=1, le=16)
    request_id: str
    request_fingerprint: str
    attempt_id: str
    input_reference: str
    input_sha256: str
    provider_reference: str
    provider_configuration_fingerprint: str
    provenance_reference: str
    output_asset_id: str | None = None
    output_sha256: str | None = None
    media_type: Literal["image/png"] | None = None
    width: int | None = Field(default=None, gt=0, le=4096)
    height: int | None = Field(default=None, gt=0, le=4096)
    outcome: Literal["accepted", "declared_failure", "recovery_required"]
    attempt_state: Literal["PANEL_ACCEPTED", "DECLARED_FAILURE", "RECOVERY_REQUIRED"]

    @field_validator(
        "evidence_id", "plan_id", "project_id", "page_id", "panel_id", "request_id", "attempt_id",
        "input_reference", "provider_reference", "provenance_reference",
        mode="before",
    )
    @classmethod
    def _logical_reference(cls, value: object) -> str:
        return logical_reference(value, "Panel evidence reference")

    @field_validator("output_asset_id")
    @classmethod
    def _optional_reference(cls, value: str | None) -> str | None:
        return None if value is None else logical_reference(value, "output asset")

    @field_validator(
        "plan_fingerprint",
        "request_fingerprint",
        "input_sha256",
        "provider_configuration_fingerprint",
    )
    @classmethod
    def _digest(cls, value: str) -> str:
        return sha256_digest(value)

    @field_validator("output_sha256")
    @classmethod
    def _optional_digest(cls, value: str | None) -> str | None:
        return None if value is None else sha256_digest(value)

    @model_validator(mode="after")
    def _accepted_output_is_complete(self) -> PanelGenerationEvidence:
        output_fields = (
            self.output_asset_id,
            self.output_sha256,
            self.media_type,
            self.width,
            self.height,
        )
        expected_state = {
            "accepted": "PANEL_ACCEPTED",
            "declared_failure": "DECLARED_FAILURE",
            "recovery_required": "RECOVERY_REQUIRED",
        }[self.outcome]
        if self.attempt_state != expected_state:
            raise ValueError("evidence outcome must match the exact terminal attempt state")
        if self.outcome == "accepted" and any(value is None for value in output_fields):
            raise ValueError("accepted Panel evidence requires one complete PNG output")
        if self.outcome != "accepted" and any(value is not None for value in output_fields):
            raise ValueError("non-success Panel evidence cannot name an accepted output")
        return self
