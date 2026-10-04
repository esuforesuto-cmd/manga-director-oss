"""Focused contracts for internal Generation Recovery Proposal validation."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from manga_director.production.next_generation_generation_evidence import (
    EvidenceValueDTO,
    GenerationConfigurationEvidenceDTO,
    GenerationEvidenceEnvelopeDTO,
    GenerationEvidenceValidationService,
    GenerationInputEvidenceDTO,
    GenerationOutputEvidenceDTO,
)
from manga_director.production.next_generation_generation_recovery_proposal import (
    GenerationRecoveryProposalDTO,
    GenerationRecoveryProposalValidationService,
)
from manga_director.production.next_generation_human_review_decision import (
    HumanReviewDecisionRecordDTO,
    HumanReviewDecisionValidationService,
)

ROOT = Path(__file__).resolve().parents[1]


def _known(value: str) -> EvidenceValueDTO:
    return EvidenceValueDTO(availability="known", value=value)


def _decision(value: str = "change_requested", decision_id: str = "decision:001", reviewer: str = "reviewer:one"):
    return HumanReviewDecisionRecordDTO(decision_id=decision_id, reviewer_id=reviewer, reviewed_at=datetime(2026, 8, 21, tzinfo=UTC), qa_report_reference="qa:001", target_type="finding", target_reference="finding:001", decision=value)


def _decision_report(*records: HumanReviewDecisionRecordDTO):
    return HumanReviewDecisionValidationService().validate(records)


def _generation_report(*, attempt: str = "attempt:001", output: str = "asset:001", provenance: str = "provenance:001"):
    config = GenerationConfigurationEvidenceDTO(provider_id=_known("provider:mock"), model_id=_known("model:mock"), model_version=_known("v1"), workflow_id=_known("workflow:page"), workflow_version=_known("v1"), seed=_known("1"))
    envelope = GenerationEvidenceEnvelopeDTO(attempt_id=attempt, observed_at=datetime(2026, 8, 21, tzinfo=UTC), provenance_reference=provenance, input=GenerationInputEvidenceDTO(input_reference="input:001"), output=GenerationOutputEvidenceDTO(output_asset_id=output), configuration=config)
    return GenerationEvidenceValidationService().validate((envelope,))


def _proposal(**updates: object) -> GenerationRecoveryProposalDTO:
    values: dict[str, object] = {"proposal_id":"proposal:001","source_decision_id":"decision:001","source_attempt_id":"attempt:001","source_output_asset_id":"asset:001","source_provenance_reference":"provenance:001","target_page_id":"page:001","target_panel_id":"panel:001","requested_change_scopes":("prompt", "composition", "parameters"),"preservation_scopes":("identity_bindings", "reference_asset_ids", "generation_input_reference", "provider_configuration", "seed", "output_provenance"),"authorization_required":True}
    values.update(updates)
    return GenerationRecoveryProposalDTO(**values)


def _validate(*proposals: GenerationRecoveryProposalDTO, decisions=None, generation=None):
    return GenerationRecoveryProposalValidationService().validate(proposals or (_proposal(),), human_review_decision_validation_report=decisions or _decision_report(_decision()), generation_evidence_validation_report=generation or _generation_report())


def test_frozen_closed_canonical_and_non_mutating() -> None:
    second = _proposal(proposal_id="proposal:002")
    first = _proposal(proposal_id="proposal:001")
    before = tuple(item.model_dump(mode="json") for item in (second, first))
    report = _validate(second, first)
    with pytest.raises(ValidationError):
        first.proposal_id = "proposal:new"
    with pytest.raises(ValidationError):
        GenerationRecoveryProposalDTO(**first.model_dump(), raw_prompt="private")
    assert tuple(item.proposal_id for item in report.proposals) == ("proposal:001", "proposal:002")
    assert tuple(item.model_dump(mode="json") for item in (second, first)) == before
    assert report.status == "needs_review"


@pytest.mark.parametrize("decision", ("accepted", "unresolved", "not_applicable"))
def test_only_change_requested_is_an_eligible_source(decision: str) -> None:
    report = _validate(decisions=_decision_report(_decision(decision)))
    assert "SOURCE_DECISION_NOT_CHANGE_REQUESTED" in {item.code for item in report.findings}
    assert report.status == "blocked"


def test_duplicate_conflicting_and_missing_source_are_blocked() -> None:
    duplicate = _validate(_proposal(), _proposal())
    conflict = _validate(decisions=_decision_report(_decision(), _decision("accepted", "decision:002", "reviewer:two")))
    missing = _validate(decisions=_decision_report(_decision(decision_id="decision:other")))
    assert "DUPLICATE_PROPOSAL_ID" in {item.code for item in duplicate.findings}
    assert "CONFLICTING_SOURCE_DECISIONS" in {item.code for item in conflict.findings}
    assert "MISSING_OR_AMBIGUOUS_SOURCE_DECISION" in {item.code for item in missing.findings}


@pytest.mark.parametrize("updates", ({"source_output_asset_id":"asset:other"}, {"source_provenance_reference":"provenance:other"}))
def test_generation_target_mismatch_is_blocked(updates: dict[str, str]) -> None:
    report = _validate(_proposal(**updates))
    assert "GENERATION_TARGET_EVIDENCE_CONFLICT" in {item.code for item in report.findings}


def test_missing_generation_and_closed_scope_validation_are_blocked() -> None:
    missing = _validate(generation=_generation_report(attempt="attempt:other"))
    invalid = _validate(_proposal(requested_change_scopes=("identity",), preservation_scopes=("seed",)))
    assert "MISSING_OR_AMBIGUOUS_GENERATION_EVIDENCE" in {item.code for item in missing.findings}
    assert {"INVALID_CHANGE_SCOPE", "MISSING_IDENTITY_BINDING_PRESERVATION"} <= {item.code for item in invalid.findings}


def test_authorization_required_is_advisory_and_false_is_blocked() -> None:
    valid = _validate()
    invalid = _validate(_proposal(authorization_required=False))
    assert "AUTHORIZATION_REQUIRED" in {item.code for item in valid.findings}
    assert valid.status == "needs_review"
    assert "AUTHORIZATION_REQUIRED_MUST_BE_TRUE" in {item.code for item in invalid.findings}


def test_source_has_no_retry_execution_or_private_payload_boundaries() -> None:
    source = (ROOT / "src/manga_director/production/next_generation_generation_recovery_proposal.py").read_text(encoding="utf-8")
    for forbidden in ("manga_director.workflow", "manga_director.providers", ".execute(", ".retry(", ".advance(", "open(", "read_text(", "requests.", "httpx.", "hashlib", "datetime.now"):
        assert forbidden not in source
    init = (ROOT / "src/manga_director/production/__init__.py").read_text(encoding="utf-8")
    assert "next_generation_generation_recovery_proposal" not in init
