"""Internal read-only QA for caller-supplied visual continuity evidence.

This preview service compares structured logical evidence only.  It never
approves, rejects, executes a provider, accesses an asset, or changes a
workflow, storyboard, identity pack, or generation record.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from typing import Literal

from pydantic import ConfigDict, field_validator

from manga_director.production.director import DirectorModel
from manga_director.production.next_generation_character_identity import (
    IdentityValidationReport,
)
from manga_director.production.next_generation_generation_evidence import (
    EvidenceValueDTO,
    GenerationEvidenceEnvelopeDTO,
    GenerationEvidenceValidationReport,
    GenerationIdentityBindingDTO,
)

_WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:[\\\\/]")

FindingClassification = Literal[
    "blocked", "missing_evidence", "evidence_conflict", "review_required"
]
FindingSeverity = Literal["blocked", "warning"]
ChecklistStatus = Literal[
    "confirmed", "missing_evidence", "evidence_conflict", "review_required", "not_applicable"
]
ReportStatus = Literal["blocked", "needs_human_review"]
ChecklistCriterion = Literal[
    "character_identity",
    "costume",
    "props",
    "location",
    "time",
    "emotion",
    "face_visual_similarity",
    "costume_visual_similarity",
    "pose",
    "screen_direction",
    "gaze",
    "composition",
]


class _VisualContinuityModel(DirectorModel):
    """Private base for closed, immutable internal-preview DTOs."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class ContinuityCharacterEvidenceDTO(_VisualContinuityModel):
    """Structured evidence for one character in one supplied panel."""

    character_id: str
    identity_binding: GenerationIdentityBindingDTO | None = None
    costume: EvidenceValueDTO | None = None
    emotion: EvidenceValueDTO | None = None

    @field_validator("character_id")
    @classmethod
    def _validate_character_id(cls, value: str) -> str:
        return _logical_reference(value, "character_id")

    @field_validator("costume", "emotion")
    @classmethod
    def _validate_attribute_evidence(cls, value: EvidenceValueDTO | None) -> EvidenceValueDTO | None:
        return _logical_evidence(value, "character attribute")


class PanelContinuityEvidenceDTO(_VisualContinuityModel):
    """Logical, caller-supplied panel evidence without storyboard or asset access."""

    page_id: str
    panel_id: str
    storyboard_panel_reference: str | None = None
    generation_attempt_id: str | None = None
    generation_output_asset_id: str | None = None
    generation_provenance_reference: str | None = None
    characters: tuple[ContinuityCharacterEvidenceDTO, ...] | None = None
    prop_ids: tuple[str, ...] | None = None
    location: EvidenceValueDTO | None = None
    time: EvidenceValueDTO | None = None

    @field_validator("page_id", "panel_id")
    @classmethod
    def _validate_panel_identity(cls, value: str) -> str:
        return _logical_reference(value, "panel identity")

    @field_validator(
        "storyboard_panel_reference",
        "generation_attempt_id",
        "generation_output_asset_id",
        "generation_provenance_reference",
    )
    @classmethod
    def _validate_optional_reference(cls, value: str | None) -> str | None:
        return _logical_reference(value, "panel evidence reference") if value is not None else None

    @field_validator("prop_ids")
    @classmethod
    def _validate_prop_ids(cls, values: tuple[str, ...] | None) -> tuple[str, ...] | None:
        if values is None:
            return None
        return tuple(_logical_reference(value, "prop_id") for value in values)

    @field_validator("location", "time")
    @classmethod
    def _validate_panel_attribute_evidence(
        cls, value: EvidenceValueDTO | None
    ) -> EvidenceValueDTO | None:
        return _logical_evidence(value, "panel attribute")


class ContinuityComparisonDTO(_VisualContinuityModel):
    """One caller-declared previous/current panel comparison."""

    comparison_id: str
    current_panel: PanelContinuityEvidenceDTO
    previous_panel: PanelContinuityEvidenceDTO | None = None

    @field_validator("comparison_id")
    @classmethod
    def _validate_comparison_id(cls, value: str) -> str:
        return _logical_reference(value, "comparison_id")


class VisualContinuityFindingDTO(_VisualContinuityModel):
    """One advisory continuity finding, with no approval or execution meaning."""

    code: str
    classification: FindingClassification
    severity: FindingSeverity
    message: str
    comparison_id: str = ""
    page_id: str = ""
    panel_id: str = ""
    character_id: str = ""
    criterion: str = ""


class HumanReviewChecklistItemDTO(_VisualContinuityModel):
    """One deterministic item for human visual-continuity review."""

    criterion: ChecklistCriterion
    status: ChecklistStatus
    comparison_id: str
    instruction: str
    page_id: str = ""
    panel_id: str = ""
    character_id: str = ""


class VisualContinuityQAReport(_VisualContinuityModel):
    """Canonical advisory report that deliberately records no human decision."""

    comparisons: tuple[ContinuityComparisonDTO, ...] = ()
    findings: tuple[VisualContinuityFindingDTO, ...] = ()
    checklist: tuple[HumanReviewChecklistItemDTO, ...] = ()
    status: ReportStatus
    needs_human_review: Literal[True] = True
    analysis_only: Literal[True] = True


class VisualContinuityQAService:
    """Compare supplied logical continuity evidence without inference or I/O."""

    def validate(
        self,
        comparisons: Sequence[ContinuityComparisonDTO] = (),
        *,
        identity_validation_report: IdentityValidationReport | None = None,
        generation_evidence_validation_report: GenerationEvidenceValidationReport | None = None,
    ) -> VisualContinuityQAReport:
        """Return a canonical human-review report for explicit panel comparisons."""

        canonical_comparisons = _canonical_comparisons(comparisons)
        findings: list[VisualContinuityFindingDTO] = []
        checklist: list[HumanReviewChecklistItemDTO] = []
        _append_input_integrity_findings(canonical_comparisons, findings)
        for comparison in canonical_comparisons:
            _append_comparison_results(
                comparison,
                identity_validation_report,
                generation_evidence_validation_report,
                findings,
                checklist,
            )
        ordered_findings = tuple(sorted(findings, key=_finding_key))
        return VisualContinuityQAReport(
            comparisons=canonical_comparisons,
            findings=ordered_findings,
            checklist=tuple(sorted(checklist, key=_checklist_key)),
            status="blocked" if any(item.classification == "blocked" for item in findings) else "needs_human_review",
        )


def _logical_reference(value: str, label: str) -> str:
    if not value.strip():
        raise ValueError(f"{label} must not be blank")
    if value.startswith(("/", "\\")) or "://" in value or _WINDOWS_ABSOLUTE_PATH.match(value):
        raise ValueError(f"{label} must be a logical reference, not a path or URL")
    return value


def _logical_evidence(value: EvidenceValueDTO | None, label: str) -> EvidenceValueDTO | None:
    if value is None or value.availability != "known":
        return value
    if not isinstance(value.value, str):
        raise ValueError(f"{label} must be a logical string when known")
    _logical_reference(value.value, label)
    return value


def _canonical_comparisons(
    comparisons: Sequence[ContinuityComparisonDTO],
) -> tuple[ContinuityComparisonDTO, ...]:
    return tuple(
        _canonical_comparison(comparison)
        for comparison in sorted(comparisons, key=lambda item: item.comparison_id)
    )


def _canonical_comparison(comparison: ContinuityComparisonDTO) -> ContinuityComparisonDTO:
    return comparison.model_copy(
        update={
            "current_panel": _canonical_panel(comparison.current_panel),
            "previous_panel": (
                _canonical_panel(comparison.previous_panel)
                if comparison.previous_panel is not None
                else None
            ),
        }
    )


def _canonical_panel(panel: PanelContinuityEvidenceDTO) -> PanelContinuityEvidenceDTO:
    characters = panel.characters
    if characters is not None:
        characters = tuple(
            character.model_copy(
                update={
                    "identity_binding": _canonical_binding(character.identity_binding),
                }
            )
            for character in sorted(characters, key=lambda item: item.character_id)
        )
    return panel.model_copy(
        update={
            "characters": characters,
            "prop_ids": tuple(sorted(panel.prop_ids)) if panel.prop_ids is not None else None,
        }
    )


def _canonical_binding(
    binding: GenerationIdentityBindingDTO | None,
) -> GenerationIdentityBindingDTO | None:
    if binding is None:
        return None
    return binding.model_copy(update={"reference_asset_ids": tuple(sorted(binding.reference_asset_ids))})


def _append_input_integrity_findings(
    comparisons: tuple[ContinuityComparisonDTO, ...], findings: list[VisualContinuityFindingDTO]
) -> None:
    for comparison_id in _duplicate_strings(item.comparison_id for item in comparisons):
        findings.append(
            _finding(
                "DUPLICATE_COMPARISON_ID",
                "blocked",
                f"comparison_id {comparison_id} is supplied more than once",
                comparison_id=comparison_id,
            )
        )
    panels = tuple(_panels(comparisons))
    for page_id, panel_id in _conflicting_panel_identities(panels):
        findings.append(
            _finding(
                "CONFLICTING_PANEL_LOGICAL_EVIDENCE",
                "blocked",
                "one panel logical identity has conflicting supplied evidence",
                page_id=page_id,
                panel_id=panel_id,
            )
        )
    for panel in panels:
        if panel.characters is None:
            continue
        for character_id in _duplicate_strings(item.character_id for item in panel.characters):
            findings.append(
                _finding(
                    "DUPLICATE_CHARACTER_EVIDENCE",
                    "blocked",
                    "one panel supplies character evidence more than once",
                    page_id=panel.page_id,
                    panel_id=panel.panel_id,
                    character_id=character_id,
                )
            )


def _panels(comparisons: Iterable[ContinuityComparisonDTO]) -> Iterable[PanelContinuityEvidenceDTO]:
    for comparison in comparisons:
        if comparison.previous_panel is not None:
            yield comparison.previous_panel
        yield comparison.current_panel


def _conflicting_panel_identities(
    panels: tuple[PanelContinuityEvidenceDTO, ...],
) -> tuple[tuple[str, str], ...]:
    values: dict[tuple[str, str], list[PanelContinuityEvidenceDTO]] = {}
    for panel in panels:
        values.setdefault((panel.page_id, panel.panel_id), []).append(panel)
    return tuple(
        identity
        for identity in sorted(values)
        if any(panel != values[identity][0] for panel in values[identity][1:])
    )


def _append_comparison_results(
    comparison: ContinuityComparisonDTO,
    identity_report: IdentityValidationReport | None,
    generation_report: GenerationEvidenceValidationReport | None,
    findings: list[VisualContinuityFindingDTO],
    checklist: list[HumanReviewChecklistItemDTO],
) -> None:
    _append_generation_results(comparison, generation_report, findings)
    _append_panel_identity_results(comparison, identity_report, findings)
    previous = comparison.previous_panel
    if previous is None:
        findings.append(
            _finding(
                "MISSING_PREVIOUS_PANEL_EVIDENCE",
                "missing_evidence",
                "previous panel evidence is not supplied",
                comparison_id=comparison.comparison_id,
                page_id=comparison.current_panel.page_id,
                panel_id=comparison.current_panel.panel_id,
            )
        )
        _append_missing_previous_checklist(comparison, checklist)
    else:
        _append_structured_comparison(previous, comparison.current_panel, comparison, findings, checklist)
    _append_visual_review_items(comparison, checklist, findings)


def _append_generation_results(
    comparison: ContinuityComparisonDTO,
    report: GenerationEvidenceValidationReport | None,
    findings: list[VisualContinuityFindingDTO],
) -> None:
    for panel in _panels((comparison,)):
        references = (
            panel.generation_attempt_id,
            panel.generation_output_asset_id,
            panel.generation_provenance_reference,
        )
        if all(value is None for value in references):
            findings.append(
                _finding(
                    "MISSING_GENERATION_EVIDENCE",
                    "missing_evidence",
                    "generation attempt, output asset, and provenance evidence are not supplied",
                    comparison_id=comparison.comparison_id,
                    page_id=panel.page_id,
                    panel_id=panel.panel_id,
                )
            )
            continue
        if any(value is None for value in references) or report is None:
            findings.append(
                _finding(
                    "MISSING_GENERATION_EVIDENCE",
                    "missing_evidence",
                    "complete generation evidence and its validation report are required",
                    comparison_id=comparison.comparison_id,
                    page_id=panel.page_id,
                    panel_id=panel.panel_id,
                )
            )
            continue
        matching = tuple(
            envelope for envelope in report.envelopes if envelope.attempt_id == panel.generation_attempt_id
        )
        if len(matching) > 1:
            findings.append(
                _finding(
                    "AMBIGUOUS_GENERATION_BINDING",
                    "blocked",
                    "generation attempt reference matches multiple supplied envelopes",
                    comparison_id=comparison.comparison_id,
                    page_id=panel.page_id,
                    panel_id=panel.panel_id,
                )
            )
            continue
        if not matching:
            findings.append(
                _finding(
                    "MISSING_GENERATION_EVIDENCE",
                    "missing_evidence",
                    "generation attempt reference is not present in the supplied report",
                    comparison_id=comparison.comparison_id,
                    page_id=panel.page_id,
                    panel_id=panel.panel_id,
                )
            )
            continue
        envelope = matching[0]
        if (
            envelope.output.output_asset_id != panel.generation_output_asset_id
            or envelope.provenance_reference != panel.generation_provenance_reference
        ):
            findings.append(
                _finding(
                    "GENERATION_EVIDENCE_CONFLICT",
                    "evidence_conflict",
                    "generation output or provenance does not match the supplied attempt",
                    comparison_id=comparison.comparison_id,
                    page_id=panel.page_id,
                    panel_id=panel.panel_id,
                )
            )
        _append_generation_binding_conflicts(comparison, panel, envelope, findings)


def _append_generation_binding_conflicts(
    comparison: ContinuityComparisonDTO,
    panel: PanelContinuityEvidenceDTO,
    envelope: GenerationEvidenceEnvelopeDTO,
    findings: list[VisualContinuityFindingDTO],
) -> None:
    if panel.characters is None:
        return
    for character in panel.characters:
        binding = character.identity_binding
        if binding is not None and binding not in envelope.identity_bindings:
            findings.append(
                _finding(
                    "GENERATION_IDENTITY_BINDING_CONFLICT",
                    "evidence_conflict",
                    "generation attempt does not contain the supplied character identity binding",
                    comparison_id=comparison.comparison_id,
                    page_id=panel.page_id,
                    panel_id=panel.panel_id,
                    character_id=character.character_id,
                    criterion="character_identity",
                )
            )


def _append_panel_identity_results(
    comparison: ContinuityComparisonDTO,
    report: IdentityValidationReport | None,
    findings: list[VisualContinuityFindingDTO],
) -> None:
    for panel in _panels((comparison,)):
        if panel.characters is None:
            continue
        for character in panel.characters:
            binding = character.identity_binding
            if binding is None or report is None:
                findings.append(
                    _finding(
                        "MISSING_APPROVED_IDENTITY_EVIDENCE",
                        "missing_evidence",
                        "explicit identity binding and identity validation report are required",
                        comparison_id=comparison.comparison_id,
                        page_id=panel.page_id,
                        panel_id=panel.panel_id,
                        character_id=character.character_id,
                        criterion="character_identity",
                    )
                )
                continue
            packs = tuple(
                pack
                for pack in report.identity_packs
                if (
                    pack.character_id,
                    pack.identity_id,
                    pack.version,
                )
                == (
                    binding.character_id,
                    binding.identity_id,
                    binding.identity_version,
                )
            )
            if len(packs) > 1:
                findings.append(
                    _finding(
                        "AMBIGUOUS_IDENTITY_BINDING",
                        "blocked",
                        "identity binding matches multiple supplied identity packs",
                        comparison_id=comparison.comparison_id,
                        page_id=panel.page_id,
                        panel_id=panel.panel_id,
                        character_id=character.character_id,
                        criterion="character_identity",
                    )
                )
                continue
            if len(packs) != 1 or not _approved_primary_binding(packs[0], binding):
                findings.append(
                    _finding(
                        "MISSING_APPROVED_IDENTITY_EVIDENCE",
                        "missing_evidence",
                        "identity pack does not provide the explicit approved primary identity binding",
                        comparison_id=comparison.comparison_id,
                        page_id=panel.page_id,
                        panel_id=panel.panel_id,
                        character_id=character.character_id,
                        criterion="character_identity",
                    )
                )


def _approved_primary_binding(
    pack: object, binding: GenerationIdentityBindingDTO
) -> bool:
    references = getattr(pack, "references", ())
    primary_ids = tuple(
        reference.reference_asset_id
        for reference in references
        if reference.reference_role == "primary_identity"
    )
    return (
        getattr(pack, "approval", None) is not None
        and bool(primary_ids)
        and tuple(sorted(primary_ids)) == binding.reference_asset_ids
    )


def _append_structured_comparison(
    previous: PanelContinuityEvidenceDTO,
    current: PanelContinuityEvidenceDTO,
    comparison: ContinuityComparisonDTO,
    findings: list[VisualContinuityFindingDTO],
    checklist: list[HumanReviewChecklistItemDTO],
) -> None:
    previous_characters = _character_map(previous.characters)
    current_characters = _character_map(current.characters)
    for character_id in sorted(set(previous_characters) | set(current_characters)):
        before = previous_characters.get(character_id)
        after = current_characters.get(character_id)
        _compare_character_criterion(
            "character_identity",
            before.identity_binding if before is not None else None,
            after.identity_binding if after is not None else None,
            comparison,
            current,
            character_id,
            findings,
            checklist,
        )
        _compare_character_criterion(
            "costume",
            before.costume if before is not None else None,
            after.costume if after is not None else None,
            comparison,
            current,
            character_id,
            findings,
            checklist,
        )
        _compare_character_criterion(
            "emotion",
            before.emotion if before is not None else None,
            after.emotion if after is not None else None,
            comparison,
            current,
            character_id,
            findings,
            checklist,
        )
    _compare_panel_criterion(
        "props", previous.prop_ids, current.prop_ids, comparison, current, findings, checklist
    )
    _compare_panel_criterion(
        "location", previous.location, current.location, comparison, current, findings, checklist
    )
    _compare_panel_criterion(
        "time", previous.time, current.time, comparison, current, findings, checklist
    )


def _character_map(
    characters: tuple[ContinuityCharacterEvidenceDTO, ...] | None,
) -> dict[str, ContinuityCharacterEvidenceDTO]:
    return {character.character_id: character for character in characters or ()}


def _compare_character_criterion(
    criterion: Literal["character_identity", "costume", "emotion"],
    previous: GenerationIdentityBindingDTO | EvidenceValueDTO | None,
    current: GenerationIdentityBindingDTO | EvidenceValueDTO | None,
    comparison: ContinuityComparisonDTO,
    panel: PanelContinuityEvidenceDTO,
    character_id: str,
    findings: list[VisualContinuityFindingDTO],
    checklist: list[HumanReviewChecklistItemDTO],
) -> None:
    status = _comparison_status(previous, current)
    _append_result(
        criterion, status, comparison, panel, findings, checklist, character_id=character_id
    )


def _compare_panel_criterion(
    criterion: Literal["props", "location", "time"],
    previous: tuple[str, ...] | EvidenceValueDTO | None,
    current: tuple[str, ...] | EvidenceValueDTO | None,
    comparison: ContinuityComparisonDTO,
    panel: PanelContinuityEvidenceDTO,
    findings: list[VisualContinuityFindingDTO],
    checklist: list[HumanReviewChecklistItemDTO],
) -> None:
    status = _comparison_status(previous, current)
    _append_result(criterion, status, comparison, panel, findings, checklist)


def _comparison_status(
    previous: GenerationIdentityBindingDTO | EvidenceValueDTO | tuple[str, ...] | None,
    current: GenerationIdentityBindingDTO | EvidenceValueDTO | tuple[str, ...] | None,
) -> ChecklistStatus:
    if not _known(previous) or not _known(current):
        return "missing_evidence"
    return "confirmed" if previous == current else "evidence_conflict"


def _known(value: GenerationIdentityBindingDTO | EvidenceValueDTO | tuple[str, ...] | None) -> bool:
    if value is None:
        return False
    return not isinstance(value, EvidenceValueDTO) or value.availability == "known"


def _append_result(
    criterion: ChecklistCriterion,
    status: ChecklistStatus,
    comparison: ContinuityComparisonDTO,
    panel: PanelContinuityEvidenceDTO,
    findings: list[VisualContinuityFindingDTO],
    checklist: list[HumanReviewChecklistItemDTO],
    *,
    character_id: str = "",
) -> None:
    checklist.append(
        _checklist_item(criterion, status, comparison, panel, character_id=character_id)
    )
    if status == "confirmed":
        return
    code = (
        f"{criterion.upper()}_EVIDENCE_CONFLICT"
        if status == "evidence_conflict"
        else f"MISSING_{criterion.upper()}_EVIDENCE"
    )
    findings.append(
        _finding(
            code,
            "evidence_conflict" if status == "evidence_conflict" else "missing_evidence",
            f"{criterion} continuity evidence is {status}",
            comparison_id=comparison.comparison_id,
            page_id=panel.page_id,
            panel_id=panel.panel_id,
            character_id=character_id,
            criterion=criterion,
        )
    )


def _append_missing_previous_checklist(
    comparison: ContinuityComparisonDTO, checklist: list[HumanReviewChecklistItemDTO]
) -> None:
    panel = comparison.current_panel
    for criterion in ("character_identity", "costume", "props", "location", "time", "emotion"):
        checklist.append(_checklist_item(criterion, "missing_evidence", comparison, panel))


def _append_visual_review_items(
    comparison: ContinuityComparisonDTO,
    checklist: list[HumanReviewChecklistItemDTO],
    findings: list[VisualContinuityFindingDTO],
) -> None:
    panel = comparison.current_panel
    for criterion in (
        "face_visual_similarity",
        "costume_visual_similarity",
        "pose",
        "screen_direction",
        "gaze",
        "composition",
    ):
        checklist.append(_checklist_item(criterion, "review_required", comparison, panel))
        findings.append(
            _finding(
                "VISUAL_REVIEW_REQUIRED",
                "review_required",
                f"{criterion} requires human visual review",
                comparison_id=comparison.comparison_id,
                page_id=panel.page_id,
                panel_id=panel.panel_id,
                criterion=criterion,
            )
        )


def _append_result_message(status: ChecklistStatus) -> str:
    return "Confirm supplied structured continuity evidence." if status == "confirmed" else "Review continuity evidence."


def _checklist_item(
    criterion: ChecklistCriterion,
    status: ChecklistStatus,
    comparison: ContinuityComparisonDTO,
    panel: PanelContinuityEvidenceDTO,
    *,
    character_id: str = "",
) -> HumanReviewChecklistItemDTO:
    instruction = (
        f"Human review required for {criterion}."
        if status == "review_required"
        else _append_result_message(status)
    )
    return HumanReviewChecklistItemDTO(
        criterion=criterion,
        status=status,
        comparison_id=comparison.comparison_id,
        instruction=instruction,
        page_id=panel.page_id,
        panel_id=panel.panel_id,
        character_id=character_id,
    )


def _finding(
    code: str,
    classification: FindingClassification,
    message: str,
    *,
    comparison_id: str = "",
    page_id: str = "",
    panel_id: str = "",
    character_id: str = "",
    criterion: str = "",
) -> VisualContinuityFindingDTO:
    return VisualContinuityFindingDTO(
        code=code,
        classification=classification,
        severity="blocked" if classification == "blocked" else "warning",
        message=message,
        comparison_id=comparison_id,
        page_id=page_id,
        panel_id=panel_id,
        character_id=character_id,
        criterion=criterion,
    )


def _duplicate_strings(values: Iterable[str]) -> tuple[str, ...]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return tuple(sorted(value for value, count in counts.items() if count > 1))


def _finding_key(item: VisualContinuityFindingDTO) -> tuple[str, ...]:
    return (
        item.code,
        item.classification,
        item.comparison_id,
        item.page_id,
        item.panel_id,
        item.character_id,
        item.criterion,
        item.message,
    )


def _checklist_key(item: HumanReviewChecklistItemDTO) -> tuple[str, ...]:
    return (
        item.comparison_id,
        item.page_id,
        item.panel_id,
        item.character_id,
        item.criterion,
        item.status,
    )
