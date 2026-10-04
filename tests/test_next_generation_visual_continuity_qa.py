"""Focused contracts for internal structured Visual Continuity QA."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from manga_director.production.next_generation_character_identity import (
    CharacterIdentityPackDTO,
    CharacterIdentityValidationService,
    IdentityApprovalEvidenceDTO,
    ReferenceAssetDescriptorDTO,
)
from manga_director.production.next_generation_generation_evidence import (
    EvidenceValueDTO,
    GenerationConfigurationEvidenceDTO,
    GenerationEvidenceEnvelopeDTO,
    GenerationEvidenceValidationService,
    GenerationIdentityBindingDTO,
    GenerationInputEvidenceDTO,
    GenerationOutputEvidenceDTO,
)
from manga_director.production.next_generation_visual_continuity_qa import (
    ContinuityCharacterEvidenceDTO,
    ContinuityComparisonDTO,
    HumanReviewChecklistItemDTO,
    PanelContinuityEvidenceDTO,
    VisualContinuityQAService,
)

ROOT = Path(__file__).resolve().parents[1]


def _known(value: str) -> EvidenceValueDTO:
    return EvidenceValueDTO(availability="known", value=value)


def _binding(version: str = "v1") -> GenerationIdentityBindingDTO:
    return GenerationIdentityBindingDTO(
        character_id="character:aki",
        identity_id=f"identity:aki:{version}",
        identity_version=version,
        reference_asset_ids=("asset:aki-primary",),
    )


def _identity_report(*, version: str = "v1"):
    pack = CharacterIdentityPackDTO(
        identity_id=f"identity:aki:{version}",
        character_id="character:aki",
        version=version,
        references=(
            ReferenceAssetDescriptorDTO(
                reference_asset_id="asset:aki-primary",
                reference_role="primary_identity",
                source_reference="asset-registry:aki",
                provenance="asset-registry:approved",
            ),
        ),
        approval=IdentityApprovalEvidenceDTO(
            approved_by="reviewer:aki", approved_at="2026-08-21T00:00:00Z"
        ),
    )
    return CharacterIdentityValidationService().validate((pack,))


def _generation_report(*, binding: GenerationIdentityBindingDTO | None = None):
    configuration = GenerationConfigurationEvidenceDTO(
        provider_id=_known("provider:mock"),
        model_id=_known("model:mock"),
        model_version=_known("v1"),
        workflow_id=_known("workflow:page"),
        workflow_version=_known("v1"),
        seed=_known("1"),
    )
    envelope = GenerationEvidenceEnvelopeDTO(
        attempt_id="attempt:aki",
        observed_at=datetime(2026, 8, 21, tzinfo=UTC),
        provenance_reference="provenance:aki",
        input=GenerationInputEvidenceDTO(input_reference="input:aki"),
        output=GenerationOutputEvidenceDTO(output_asset_id="asset:generated:aki"),
        configuration=configuration,
        identity_bindings=(_binding() if binding is None else binding,),
    )
    return GenerationEvidenceValidationService().validate((envelope,))


def _panel(
    *,
    page_id: str,
    panel_id: str,
    costume: EvidenceValueDTO | None = None,
    props: tuple[str, ...] | None = ("prop:book",),
    location: EvidenceValueDTO | None = None,
    time: EvidenceValueDTO | None = None,
    emotion: EvidenceValueDTO | None = None,
    binding: GenerationIdentityBindingDTO | None = None,
    characters: tuple[ContinuityCharacterEvidenceDTO, ...] | None = None,
    attempt_id: str | None = "attempt:aki",
    output_asset_id: str | None = "asset:generated:aki",
    provenance: str | None = "provenance:aki",
) -> PanelContinuityEvidenceDTO:
    return PanelContinuityEvidenceDTO(
        page_id=page_id,
        panel_id=panel_id,
        storyboard_panel_reference=f"storyboard:{page_id}:{panel_id}",
        generation_attempt_id=attempt_id,
        generation_output_asset_id=output_asset_id,
        generation_provenance_reference=provenance,
        characters=characters
        if characters is not None
        else (
            ContinuityCharacterEvidenceDTO(
                character_id="character:aki",
                identity_binding=_binding() if binding is None else binding,
                costume=costume or _known("costume:school"),
                emotion=emotion or _known("emotion:calm"),
            ),
        ),
        prop_ids=props,
        location=location or _known("location:library"),
        time=time or _known("time:afternoon"),
    )


def _comparison(
    *,
    comparison_id: str = "comparison:001",
    previous: PanelContinuityEvidenceDTO | None = None,
    current: PanelContinuityEvidenceDTO | None = None,
) -> ContinuityComparisonDTO:
    return ContinuityComparisonDTO(
        comparison_id=comparison_id,
        previous_panel=previous or _panel(page_id="page:001", panel_id="panel:001"),
        current_panel=current or _panel(page_id="page:001", panel_id="panel:002"),
    )


def _report(*comparisons: ContinuityComparisonDTO):
    return VisualContinuityQAService().validate(
        comparisons,
        identity_validation_report=_identity_report(),
        generation_evidence_validation_report=_generation_report(),
    )


def test_dtos_are_frozen_closed_and_report_has_no_decision_or_execution_fields() -> None:
    panel = _panel(page_id="page:001", panel_id="panel:001")

    with pytest.raises(ValidationError):
        panel.page_id = "page:002"
    with pytest.raises(ValidationError):
        PanelContinuityEvidenceDTO(page_id="page:001", panel_id="panel:001", raw_image="x")

    report = _report(_comparison())
    for forbidden in (
        "approved",
        "rejected",
        "regenerate",
        "retry",
        "workflow_transition",
        "provider_choice",
    ):
        assert forbidden not in type(report).model_fields
    assert report.analysis_only is True
    assert report.needs_human_review is True


def test_canonical_ordering_repeated_result_and_input_non_mutation() -> None:
    later = _comparison(comparison_id="comparison:002")
    earlier = _comparison(comparison_id="comparison:001")
    supplied = (later, earlier)
    before = tuple(item.model_dump(mode="json") for item in supplied)

    first = _report(*supplied)
    second = _report(*supplied)

    assert tuple(item.comparison_id for item in first.comparisons) == (
        "comparison:001",
        "comparison:002",
    )
    assert first == second
    assert tuple(item.model_dump(mode="json") for item in supplied) == before


def test_confirmed_structured_evidence_and_visual_review_are_separate() -> None:
    report = _report(_comparison())

    confirmed = {(item.criterion, item.status) for item in report.checklist}
    assert ("costume", "confirmed") in confirmed
    assert ("props", "confirmed") in confirmed
    assert ("location", "confirmed") in confirmed
    assert ("time", "confirmed") in confirmed
    assert ("emotion", "confirmed") in confirmed
    assert ("character_identity", "confirmed") in confirmed
    assert all(item.status == "review_required" for item in report.checklist if "visual" in item.criterion)
    assert "VISUAL_REVIEW_REQUIRED" in {item.code for item in report.findings}


def test_missing_evidence_never_becomes_conflict() -> None:
    previous = _panel(page_id="page:001", panel_id="panel:001", costume=EvidenceValueDTO(availability="unknown"))
    report = _report(_comparison(previous=previous))

    costume = [item for item in report.checklist if item.criterion == "costume"]
    assert costume[0].status == "missing_evidence"
    assert "MISSING_COSTUME_EVIDENCE" in {item.code for item in report.findings}
    assert "COSTUME_EVIDENCE_CONFLICT" not in {item.code for item in report.findings}


@pytest.mark.parametrize(
    ("criterion", "previous", "current", "code"),
    (
        ("costume", _panel(page_id="page:001", panel_id="panel:001", costume=_known("costume:school")), _panel(page_id="page:001", panel_id="panel:002", costume=_known("costume:uniform")), "COSTUME_EVIDENCE_CONFLICT"),
        ("props", _panel(page_id="page:001", panel_id="panel:001", props=("prop:book",)), _panel(page_id="page:001", panel_id="panel:002", props=("prop:phone",)), "PROPS_EVIDENCE_CONFLICT"),
        ("location", _panel(page_id="page:001", panel_id="panel:001", location=_known("location:library")), _panel(page_id="page:001", panel_id="panel:002", location=_known("location:street")), "LOCATION_EVIDENCE_CONFLICT"),
        ("time", _panel(page_id="page:001", panel_id="panel:001", time=_known("time:afternoon")), _panel(page_id="page:001", panel_id="panel:002", time=_known("time:night")), "TIME_EVIDENCE_CONFLICT"),
        ("emotion", _panel(page_id="page:001", panel_id="panel:001", emotion=_known("emotion:calm")), _panel(page_id="page:001", panel_id="panel:002", emotion=_known("emotion:angry")), "EMOTION_EVIDENCE_CONFLICT"),
        ("character_identity", _panel(page_id="page:001", panel_id="panel:001"), _panel(page_id="page:001", panel_id="panel:002", binding=_binding("v2")), "CHARACTER_IDENTITY_EVIDENCE_CONFLICT"),
    ),
)
def test_known_structured_differences_are_conflicts(
    criterion: str,
    previous: PanelContinuityEvidenceDTO,
    current: PanelContinuityEvidenceDTO,
    code: str,
) -> None:
    report = _report(_comparison(previous=previous, current=current))

    assert code in {item.code for item in report.findings}
    assert any(item.criterion == criterion and item.status == "evidence_conflict" for item in report.checklist)
    assert report.status == "needs_human_review"


def test_missing_previous_panel_is_missing_evidence() -> None:
    current = _panel(page_id="page:002", panel_id="panel:001")
    comparison = ContinuityComparisonDTO(comparison_id="comparison:missing", current_panel=current)

    report = _report(comparison)

    assert "MISSING_PREVIOUS_PANEL_EVIDENCE" in {item.code for item in report.findings}
    assert any(item.status == "missing_evidence" for item in report.checklist)


def test_duplicate_comparison_id_and_conflicting_panel_evidence_are_blocked() -> None:
    first = _comparison(comparison_id="comparison:duplicate")
    changed = _panel(page_id="page:001", panel_id="panel:002", costume=_known("costume:uniform"))
    second = _comparison(comparison_id="comparison:duplicate", current=changed)

    report = _report(first, second)

    codes = {item.code for item in report.findings}
    assert {"DUPLICATE_COMPARISON_ID", "CONFLICTING_PANEL_LOGICAL_EVIDENCE"} <= codes
    assert report.status == "blocked"


def test_duplicate_character_evidence_is_blocked() -> None:
    character = ContinuityCharacterEvidenceDTO(character_id="character:aki", identity_binding=_binding())
    panel = _panel(page_id="page:001", panel_id="panel:002", characters=(character, character))

    report = _report(_comparison(current=panel))

    assert "DUPLICATE_CHARACTER_EVIDENCE" in {item.code for item in report.findings}
    assert report.status == "blocked"


def test_ambiguous_identity_binding_is_blocked_without_version_selection() -> None:
    report = CharacterIdentityValidationService().validate(
        (
            CharacterIdentityPackDTO(
                identity_id="identity:aki:v1",
                character_id="character:aki",
                version="v1",
                references=(
                    ReferenceAssetDescriptorDTO(
                        reference_asset_id="asset:aki-primary",
                        reference_role="primary_identity",
                        source_reference="asset-registry:aki",
                        provenance="asset-registry:approved",
                    ),
                ),
                approval=IdentityApprovalEvidenceDTO(
                    approved_by="reviewer:aki", approved_at="2026-08-21T00:00:00Z"
                ),
            ),
            CharacterIdentityPackDTO(
                identity_id="identity:aki:v1",
                character_id="character:aki",
                version="v1",
                references=(
                    ReferenceAssetDescriptorDTO(
                        reference_asset_id="asset:aki-primary",
                        reference_role="primary_identity",
                        source_reference="asset-registry:aki",
                        provenance="asset-registry:approved",
                    ),
                ),
                approval=IdentityApprovalEvidenceDTO(
                    approved_by="reviewer:aki", approved_at="2026-08-21T00:00:00Z"
                ),
            ),
        )
    )
    service = VisualContinuityQAService()

    qa_report = service.validate(
        (_comparison(),),
        identity_validation_report=report,
        generation_evidence_validation_report=_generation_report(),
    )

    assert "AMBIGUOUS_IDENTITY_BINDING" in {item.code for item in qa_report.findings}
    assert "selected_version" not in type(qa_report).model_fields


def test_ambiguous_generation_binding_is_blocked() -> None:
    configuration = GenerationConfigurationEvidenceDTO(
        provider_id=_known("provider:mock"),
        model_id=_known("model:mock"),
        model_version=_known("v1"),
        workflow_id=_known("workflow:page"),
        workflow_version=_known("v1"),
        seed=_known("1"),
    )
    envelope = GenerationEvidenceEnvelopeDTO(
        attempt_id="attempt:aki",
        observed_at=datetime(2026, 8, 21, tzinfo=UTC),
        provenance_reference="provenance:aki",
        input=GenerationInputEvidenceDTO(input_reference="input:aki"),
        output=GenerationOutputEvidenceDTO(output_asset_id="asset:generated:aki"),
        configuration=configuration,
        identity_bindings=(_binding(),),
    )
    duplicate_report = GenerationEvidenceValidationService().validate((envelope, envelope))
    qa_report = VisualContinuityQAService().validate(
        (_comparison(),),
        identity_validation_report=_identity_report(),
        generation_evidence_validation_report=duplicate_report,
    )

    assert "AMBIGUOUS_GENERATION_BINDING" in {item.code for item in qa_report.findings}
    assert qa_report.status == "blocked"


def test_multiple_approved_versions_are_not_selected() -> None:
    identity_report = CharacterIdentityValidationService().validate(
        (
            _identity_report().identity_packs[0],
            CharacterIdentityPackDTO(
                identity_id="identity:aki:v2",
                character_id="character:aki",
                version="v2",
                references=(
                    ReferenceAssetDescriptorDTO(
                        reference_asset_id="asset:aki-primary",
                        reference_role="primary_identity",
                        source_reference="asset-registry:aki",
                        provenance="asset-registry:approved",
                    ),
                ),
                approval=IdentityApprovalEvidenceDTO(
                    approved_by="reviewer:aki", approved_at="2026-08-21T00:00:00Z"
                ),
            ),
        )
    )

    qa_report = VisualContinuityQAService().validate(
        (_comparison(),),
        identity_validation_report=identity_report,
        generation_evidence_validation_report=_generation_report(),
    )

    assert "AMBIGUOUS_IDENTITY_BINDING" not in {item.code for item in qa_report.findings}
    assert "selected_version" not in type(qa_report).model_fields
    assert "latest_version" not in type(qa_report).model_fields


def test_source_has_no_public_export_or_io_provider_or_workflow_boundary() -> None:
    source = (
        ROOT / "src/manga_director/production/next_generation_visual_continuity_qa.py"
    ).read_text(encoding="utf-8")

    for forbidden in (
        "manga_director.api",
        "manga_director.cli",
        "manga_director.mcp",
        "manga_director.workflow",
        "manga_director.providers",
        ".execute(",
        ".advance(",
        "open(",
        "read_text(",
        "requests.",
        "httpx.",
        "hashlib",
        "datetime.now",
    ):
        assert forbidden not in source
    production_init = (ROOT / "src/manga_director/production/__init__.py").read_text(
        encoding="utf-8"
    )
    assert "next_generation_visual_continuity_qa" not in production_init
    assert HumanReviewChecklistItemDTO.__module__.endswith("next_generation_visual_continuity_qa")
