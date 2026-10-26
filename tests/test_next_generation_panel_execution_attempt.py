from __future__ import annotations

import pytest
from pydantic import ValidationError

from manga_director.production.next_generation_page_generation_plan import (
    PagePanelSpecification,
    PanelRectangle,
)
from manga_director.production.next_generation_panel_execution_attempt import (
    PanelAttemptRecord,
    PanelAttemptReservation,
    PanelGenerationRequest,
    PanelGenerationResult,
)


def _prompt() -> PagePanelSpecification:
    return PagePanelSpecification(
        panel_id="panel-1",
        order=1,
        rectangle=PanelRectangle(left=50_000, top=40_000, right=950_000, bottom=960_000),
        narrative_intent="A character makes a decision",
        character_identities=("character-1",),
        continuity_bindings=("red-scarf",),
        action="The character opens the sealed door",
        background="A quiet room at dusk",
        composition="Medium shot with the character left of center",
        constraints=("Keep the red scarf visible",),
    )


def _reservation() -> PanelAttemptReservation:
    return PanelAttemptReservation(
        attempt_id="attempt-1", plan_id="plan-1", plan_fingerprint="a" * 64,
        project_id="project-1", page_id="page-1", panel_id="panel-1", panel_order=1,
        request_id="request-1", request_fingerprint="c" * 64,
        provider_reference="provider-1", authorization_reference="auth-1",
        execution_fingerprint="b" * 64,
    )


def test_panel_acceptance_is_a_terminal_asset_bound_state() -> None:
    record = PanelAttemptRecord(
        reservation=_reservation(),
        state="PANEL_ACCEPTED",
        provider_start_consumed=True,
        output_asset_id="asset-1",
        evidence_id="evidence-1",
        accepted_asset_id="asset-1",
    )
    assert record.accepted_asset_id == "asset-1"


def test_panel_cannot_be_accepted_without_consumed_start_and_asset() -> None:
    with pytest.raises(ValidationError):
        PanelAttemptRecord(
            reservation=_reservation(),
            state="PANEL_ACCEPTED",
            provider_start_consumed=False,
        )


def test_declared_failure_requires_a_consumed_start_and_has_no_output() -> None:
    with pytest.raises(ValidationError):
        PanelAttemptRecord(
            reservation=_reservation(),
            state="DECLARED_FAILURE",
            provider_start_consumed=False,
        )
    with pytest.raises(ValidationError):
        PanelAttemptRecord(
            reservation=_reservation(),
            state="DECLARED_FAILURE",
            provider_start_consumed=True,
            output_asset_id="asset-1",
        )


def test_panel_request_is_exactly_bound_and_fingerprinted() -> None:
    request = PanelGenerationRequest(
        request_id="request-1",
        plan_id="plan-1",
        plan_fingerprint="a" * 64,
        project_id="project-1",
        page_id="page-1",
        panel_id="panel-1",
        panel_order=1,
        panel_prompt=_prompt(),
        capability_requirements=("static-png", "rgb-or-rgba"),
        input_reference="prompt-input-1",
        input_sha256="b" * 64,
        provenance_reference="provenance-1",
    )
    assert len(request.request_fingerprint or "") == 64
    with pytest.raises(ValidationError):
        PanelGenerationRequest(**(request.model_dump() | {"panel_id": "panel-2"}))


def test_panel_result_is_a_closed_outcome() -> None:
    success = PanelGenerationResult(
        request_id="request-1",
        request_fingerprint="a" * 64,
        attempt_id="attempt-1",
        outcome="success",
        accepted_asset_id="asset-1",
    )
    assert success.accepted_asset_id == "asset-1"
    with pytest.raises(ValidationError):
        PanelGenerationResult(
            request_id="request-1",
            request_fingerprint="a" * 64,
            attempt_id="attempt-1",
            outcome="blocked",
            accepted_asset_id="asset-1",
        )


def test_attempt_identity_rejects_path_like_values() -> None:
    with pytest.raises(ValidationError):
        PanelAttemptReservation(
            attempt_id="attempt-1", plan_id="plan-1", plan_fingerprint="a" * 64,
            project_id="project-1", page_id="page-1", panel_id="../panel", panel_order=1,
            request_id="request-1", request_fingerprint="c" * 64,
            provider_reference="provider-1", authorization_reference="auth-1",
            execution_fingerprint="b" * 64,
        )
