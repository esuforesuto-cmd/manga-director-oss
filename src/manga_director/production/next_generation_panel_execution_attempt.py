"""Pure immutable contracts for Panel-scoped provider attempts."""

from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict, Field, field_validator, model_validator

from manga_director.production.director import DirectorModel
from manga_director.production.next_generation_page_generation_plan import (
    PagePanelSpecification,
    canonical_digest,
    logical_reference,
    sha256_digest,
)

PanelAttemptState = Literal[
    "RESERVED",
    "PROVIDER_STARTED",
    "PROVIDER_COMPLETED",
    "ASSET_REGISTERED",
    "EVIDENCE_COMMITTED",
    "PANEL_ACCEPTED",
    "DECLARED_FAILURE",
    "RECOVERY_REQUIRED",
]
PanelAttemptOutcome = Literal[
    "reserved",
    "provider_started",
    "provider_completed",
    "asset_registered",
    "evidence_committed",
    "panel_accepted",
    "declared_failure",
    "recovery_required",
    "blocked",
]


class _PanelAttemptModel(DirectorModel):
    model_config = ConfigDict(
        frozen=True, extra="forbid", strict=True, validate_default=True
    )


class PanelGenerationRequest(_PanelAttemptModel):
    """One admitted provider-neutral request for one exact plan Panel."""

    request_id: str
    plan_id: str
    plan_fingerprint: str
    project_id: str
    page_id: str
    panel_id: str
    panel_order: int = Field(ge=1, le=16)
    panel_prompt: PagePanelSpecification
    capability_requirements: tuple[str, ...] = Field(min_length=1, max_length=32)
    input_reference: str
    input_sha256: str
    provenance_reference: str
    request_fingerprint: str | None = None

    @field_validator(
        "request_id",
        "plan_id",
        "project_id",
        "page_id",
        "panel_id",
        "input_reference",
        "provenance_reference",
        mode="before",
    )
    @classmethod
    def _logical_fields(cls, value: object) -> str:
        return logical_reference(value, "Panel request reference")

    @field_validator("plan_fingerprint", "input_sha256")
    @classmethod
    def _digest_fields(cls, value: str) -> str:
        return sha256_digest(value)

    @field_validator("capability_requirements")
    @classmethod
    def _capabilities(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        validated = tuple(logical_reference(item, "capability requirement") for item in value)
        if len(set(validated)) != len(validated):
            raise ValueError("capability requirements must be unique")
        return validated

    @model_validator(mode="after")
    def _exact_panel_binding(self) -> PanelGenerationRequest:
        if (
            self.panel_prompt.panel_id != self.panel_id
            or self.panel_prompt.order != self.panel_order
        ):
            raise ValueError("Panel prompt identity does not match the request")
        expected = canonical_digest(
            self.model_dump(mode="json", exclude={"request_fingerprint"})
        )
        if self.request_fingerprint is not None and self.request_fingerprint != expected:
            raise ValueError("request_fingerprint does not match canonical request content")
        object.__setattr__(self, "request_fingerprint", expected)
        return self


class PanelAttemptReservation(_PanelAttemptModel):
    attempt_id: str
    plan_id: str
    plan_fingerprint: str
    project_id: str
    page_id: str
    panel_id: str
    panel_order: int = Field(ge=1, le=16)
    request_id: str
    request_fingerprint: str
    provider_reference: str
    authorization_reference: str
    execution_fingerprint: str

    @field_validator(
        "attempt_id", "plan_id", "project_id", "page_id", "panel_id", "request_id",
        "provider_reference", "authorization_reference",
    )
    @classmethod
    def _logical_reference(cls, value: str) -> str:
        return logical_reference(value, "attempt reference")

    @field_validator("plan_fingerprint", "request_fingerprint", "execution_fingerprint")
    @classmethod
    def _fingerprint(cls, value: str) -> str:
        return sha256_digest(value)


class PanelAttemptRecord(_PanelAttemptModel):
    reservation: PanelAttemptReservation
    state: PanelAttemptState
    provider_start_consumed: bool
    output_asset_id: str | None = None
    evidence_id: str | None = None
    accepted_asset_id: str | None = None

    @field_validator("output_asset_id", "evidence_id", "accepted_asset_id")
    @classmethod
    def _asset_reference(cls, value: str | None) -> str | None:
        return None if value is None else logical_reference(value, "attempt record reference")

    def model_post_init(self, __context: object) -> None:
        if self.state == "RESERVED" and self.provider_start_consumed:
            raise ValueError("reserved attempt cannot consume the Provider start opportunity")
        post_start = {
            "PROVIDER_STARTED",
            "PROVIDER_COMPLETED",
            "ASSET_REGISTERED",
            "EVIDENCE_COMMITTED",
            "PANEL_ACCEPTED",
            "DECLARED_FAILURE",
            "RECOVERY_REQUIRED",
        }
        if self.state in post_start and not self.provider_start_consumed:
            raise ValueError(
                "post-start attempt states must consume the Provider start opportunity"
            )
        if (
            self.state in {"ASSET_REGISTERED", "EVIDENCE_COMMITTED", "PANEL_ACCEPTED"}
            and not self.output_asset_id
        ):
            raise ValueError("post-registration states require the exact output asset")
        if (
            self.state in {"RESERVED", "PROVIDER_STARTED", "PROVIDER_COMPLETED"}
            and self.output_asset_id is not None
        ):
            raise ValueError("pre-registration states cannot name an output asset")
        if self.state in {"EVIDENCE_COMMITTED", "PANEL_ACCEPTED"} and not self.evidence_id:
            raise ValueError("post-evidence states require the exact evidence")
        if (
            self.state
            in {"RESERVED", "PROVIDER_STARTED", "PROVIDER_COMPLETED", "ASSET_REGISTERED"}
            and self.evidence_id is not None
        ):
            raise ValueError("pre-evidence states cannot name evidence")
        if self.state == "PANEL_ACCEPTED" and not self.accepted_asset_id:
            raise ValueError("accepted Panel attempt requires its exact asset ID")
        if self.accepted_asset_id is not None and self.accepted_asset_id != self.output_asset_id:
            raise ValueError("accepted asset must equal the registered output asset")
        if self.state != "PANEL_ACCEPTED" and self.accepted_asset_id is not None:
            raise ValueError("only accepted Panel attempts may expose an accepted asset")
        if self.state == "DECLARED_FAILURE" and self.output_asset_id is not None:
            raise ValueError("declared failure cannot name a registered output asset")


class PanelGenerationResult(_PanelAttemptModel):
    """Closed outcome for one exact request and attempt."""

    request_id: str
    request_fingerprint: str
    attempt_id: str
    outcome: Literal["success", "declared_failure", "recovery_required", "blocked"]
    accepted_asset_id: str | None = None

    @field_validator("request_id", "attempt_id", mode="before")
    @classmethod
    def _references(cls, value: object) -> str:
        return logical_reference(value, "Panel result reference")

    @field_validator("accepted_asset_id")
    @classmethod
    def _accepted_asset(cls, value: str | None) -> str | None:
        return None if value is None else logical_reference(value, "accepted asset")

    @field_validator("request_fingerprint")
    @classmethod
    def _request_digest(cls, value: str) -> str:
        return sha256_digest(value)

    @model_validator(mode="after")
    def _closed_outcome(self) -> PanelGenerationResult:
        if (self.outcome == "success") != (self.accepted_asset_id is not None):
            raise ValueError("only success names exactly one accepted Panel asset")
        return self
