from __future__ import annotations

import pytest
from pydantic import ValidationError

from manga_director.production.next_generation_panel_generation_evidence import (
    PanelAsset,
    PanelGenerationEvidence,
)


def _evidence(**changes: object) -> PanelGenerationEvidence:
    values: dict[str, object] = {
        "evidence_id": "evidence-1", "plan_id": "plan-1", "plan_fingerprint": "a" * 64,
        "project_id": "project-1", "page_id": "page-1", "panel_id": "panel-1", "panel_order": 1,
        "request_id": "request-1", "request_fingerprint": "e" * 64,
        "attempt_id": "attempt-1", "input_reference": "input-1",
        "input_sha256": "b" * 64, "provider_reference": "provider-1",
        "provider_configuration_fingerprint": "c" * 64, "provenance_reference": "provenance-1",
        "output_asset_id": "asset-1", "output_sha256": "d" * 64, "media_type": "image/png",
        "width": 512, "height": 512, "outcome": "accepted", "attempt_state": "PANEL_ACCEPTED",
    }
    values.update(changes)
    return PanelGenerationEvidence(**values)


def test_accepted_evidence_binds_one_panel_attempt_and_asset() -> None:
    evidence = _evidence()
    assert evidence.attempt_id == "attempt-1"
    assert evidence.output_asset_id == "asset-1"


def test_evidence_rejects_provider_paths_and_invalid_hashes() -> None:
    with pytest.raises(ValidationError):
        _evidence(provider_reference="https://example.invalid")
    with pytest.raises(ValidationError):
        _evidence(output_sha256="not-a-hash")
    with pytest.raises(ValidationError):
        _evidence(request_fingerprint="not-a-hash")


def test_evidence_rejects_out_of_bound_dimensions() -> None:
    with pytest.raises(ValidationError):
        _evidence(width=4097)


def test_failure_evidence_cannot_alias_an_accepted_output() -> None:
    with pytest.raises(ValidationError):
        _evidence(outcome="declared_failure", attempt_state="DECLARED_FAILURE")
    failure = _evidence(
        outcome="declared_failure",
        attempt_state="DECLARED_FAILURE",
        output_asset_id=None,
        output_sha256=None,
        media_type=None,
        width=None,
        height=None,
    )
    assert failure.output_asset_id is None


def test_panel_asset_binds_exact_plan_page_panel_and_attempt() -> None:
    asset = PanelAsset(
        asset_id="asset-1",
        plan_id="plan-1",
        plan_fingerprint="a" * 64,
        project_id="project-1",
        page_id="page-1",
        panel_id="panel-1",
        panel_order=1,
        request_id="request-1",
        request_fingerprint="e" * 64,
        attempt_id="attempt-1",
        width=512,
        height=512,
        content_sha256="d" * 64,
    )
    assert asset.media_type == "image/png"
