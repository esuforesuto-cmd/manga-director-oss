"""Internal read-only validation for caller-supplied Character Identity Packs.

This preview module validates logical identity evidence only.  It never reads
assets, calculates hashes, selects a version, grants approval, or changes a
workflow, repository, or provider.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from typing import Literal

from pydantic import ConfigDict, field_validator

from manga_director.production.director import DirectorModel

_CORE_REFERENCE_ROLES = frozenset(
    {
        "primary_identity",
        "face",
        "full_body",
        "costume",
        "expression",
        "pose",
        "prop",
        "color",
        "other",
    }
)
_WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:[\\/]")
_STATUS_PRIORITY = {"blocked": 3, "needs_evidence": 2, "needs_review": 1}


class _IdentityModel(DirectorModel):
    """Private base for frozen, closed preview DTOs."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class IdentityApprovalEvidenceDTO(_IdentityModel):
    """Caller-supplied human approval evidence; authorization is out of scope."""

    approved_by: str
    approved_at: datetime

    @field_validator("approved_by")
    @classmethod
    def _require_approver_reference(cls, value: str) -> str:
        return _require_nonblank(value, "approved_by")


class ReferenceAssetDescriptorDTO(_IdentityModel):
    """Logical reference to identity evidence, without asset ownership or access."""

    reference_asset_id: str
    reference_role: str
    source_reference: str
    provenance: str
    content_hash: str | None = None
    media_type: str | None = None

    @field_validator("reference_asset_id", "reference_role", "provenance")
    @classmethod
    def _require_nonblank_value(cls, value: str) -> str:
        return _require_nonblank(value, "reference asset descriptor value")

    @field_validator("source_reference")
    @classmethod
    def _require_logical_source_reference(cls, value: str) -> str:
        value = _require_nonblank(value, "source_reference")
        if value.startswith(("/", "\\")) or "://" in value or _WINDOWS_ABSOLUTE_PATH.match(value):
            raise ValueError("source_reference must be a logical reference, not a path or URL")
        return value

    @field_validator("content_hash", "media_type")
    @classmethod
    def _reject_blank_optional_values(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("optional evidence values must not be blank")
        return value


class CharacterIdentityPackDTO(_IdentityModel):
    """One caller-supplied character identity version and its reference evidence."""

    identity_id: str
    character_id: str
    version: str
    references: tuple[ReferenceAssetDescriptorDTO, ...] = ()
    display_name: str = ""
    approval: IdentityApprovalEvidenceDTO | None = None

    @field_validator("identity_id", "character_id", "version")
    @classmethod
    def _require_identity_value(cls, value: str) -> str:
        return _require_nonblank(value, "identity pack value")


class IdentityFindingDTO(_IdentityModel):
    """One deterministic advisory finding from identity evidence validation."""

    code: str
    status: Literal["blocked", "needs_evidence", "needs_review"]
    message: str
    identity_id: str = ""
    character_id: str = ""
    version: str = ""
    reference_asset_id: str = ""
    panel_index: int | None = None


class IdentityValidationReport(_IdentityModel):
    """Canonical read-only validation snapshot for supplied identity packs."""

    identity_packs: tuple[CharacterIdentityPackDTO, ...] = ()
    findings: tuple[IdentityFindingDTO, ...] = ()
    status: Literal["ready", "needs_evidence", "needs_review", "blocked"]
    ready: bool
    analysis_only: Literal[True] = True
    approval_granted: Literal[False] = False
    version_selected: Literal[False] = False
    assets_read: Literal[False] = False
    content_hash_calculated: Literal[False] = False
    network_accessed: Literal[False] = False
    persistence_performed: Literal[False] = False


class CharacterIdentityValidationService:
    """Validate supplied identity evidence without selecting, storing, or approving it."""

    def validate(
        self,
        identity_packs: Sequence[CharacterIdentityPackDTO] = (),
        *,
        storyboard: Mapping[str, object] | None = None,
    ) -> IdentityValidationReport:
        """Return a deterministic report for caller-supplied identity and storyboard evidence."""

        canonical_packs = _canonical_packs(identity_packs)
        findings = _pack_findings(canonical_packs)
        if storyboard is not None:
            findings.extend(_storyboard_findings(canonical_packs, storyboard))
        ordered_findings = tuple(sorted(findings, key=_finding_key))
        status = _report_status(ordered_findings)
        return IdentityValidationReport(
            identity_packs=canonical_packs,
            findings=ordered_findings,
            status=status,
            ready=status == "ready",
        )


def _require_nonblank(value: str, field_name: str) -> str:
    if not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    return value


def _canonical_packs(
    identity_packs: Sequence[CharacterIdentityPackDTO],
) -> tuple[CharacterIdentityPackDTO, ...]:
    return tuple(
        pack.model_copy(
            update={
                "references": tuple(
                    sorted(
                        pack.references,
                        key=lambda reference: (
                            reference.reference_asset_id,
                            reference.reference_role,
                            reference.source_reference,
                            reference.provenance,
                            reference.content_hash or "",
                            reference.media_type or "",
                        ),
                    )
                )
            }
        )
        for pack in sorted(
            identity_packs,
            key=lambda item: (item.identity_id, item.character_id, item.version),
        )
    )


def _pack_findings(
    identity_packs: tuple[CharacterIdentityPackDTO, ...],
) -> list[IdentityFindingDTO]:
    findings: list[IdentityFindingDTO] = []
    _append_duplicate_identity_findings(identity_packs, findings)
    _append_duplicate_character_version_findings(identity_packs, findings)
    _append_pack_readiness_findings(identity_packs, findings)
    _append_asset_consistency_findings(identity_packs, findings)
    return findings


def _append_duplicate_identity_findings(
    identity_packs: tuple[CharacterIdentityPackDTO, ...], findings: list[IdentityFindingDTO]
) -> None:
    for identity_id in _duplicate_strings(pack.identity_id for pack in identity_packs):
        findings.append(
            IdentityFindingDTO(
                code="duplicate_identity_id",
                status="blocked",
                message=f"identity_id {identity_id} is supplied more than once",
                identity_id=identity_id,
            )
        )


def _append_duplicate_character_version_findings(
    identity_packs: tuple[CharacterIdentityPackDTO, ...], findings: list[IdentityFindingDTO]
) -> None:
    seen: set[tuple[str, str]] = set()
    duplicates: set[tuple[str, str]] = set()
    for pack in identity_packs:
        key = (pack.character_id, pack.version)
        if key in seen:
            duplicates.add(key)
        seen.add(key)
    for character_id, version in sorted(duplicates):
        findings.append(
            IdentityFindingDTO(
                code="duplicate_character_version",
                status="blocked",
                message=f"character_id {character_id} has duplicate version {version}",
                character_id=character_id,
                version=version,
            )
        )


def _append_pack_readiness_findings(
    identity_packs: tuple[CharacterIdentityPackDTO, ...], findings: list[IdentityFindingDTO]
) -> None:
    for pack in identity_packs:
        if pack.approval is None:
            findings.append(
                _pack_finding(
                    pack,
                    "missing_approval_evidence",
                    "needs_evidence",
                    "identity pack has no human approval evidence",
                )
            )
        if not _has_primary_identity(pack):
            findings.append(
                _pack_finding(
                    pack,
                    "missing_primary_identity",
                    "needs_evidence",
                    "identity pack has no primary_identity reference",
                )
            )
        for reference in pack.references:
            if reference.reference_role not in _CORE_REFERENCE_ROLES:
                findings.append(
                    IdentityFindingDTO(
                        code="unknown_reference_role",
                        status="needs_review",
                        message=(
                            f"reference role {reference.reference_role} is not a core identity role"
                        ),
                        identity_id=pack.identity_id,
                        character_id=pack.character_id,
                        version=pack.version,
                        reference_asset_id=reference.reference_asset_id,
                    )
                )
        _append_duplicate_reference_pair_findings(pack, findings)


def _append_duplicate_reference_pair_findings(
    pack: CharacterIdentityPackDTO, findings: list[IdentityFindingDTO]
) -> None:
    pairs = tuple((reference.reference_asset_id, reference.reference_role) for reference in pack.references)
    for reference_asset_id, reference_role in _duplicate_pairs(pairs):
        findings.append(
            IdentityFindingDTO(
                code="duplicate_reference_pair",
                status="blocked",
                message=(
                    "identity pack repeats reference_asset_id "
                    f"{reference_asset_id} with role {reference_role}"
                ),
                identity_id=pack.identity_id,
                character_id=pack.character_id,
                version=pack.version,
                reference_asset_id=reference_asset_id,
            )
        )


def _append_asset_consistency_findings(
    identity_packs: tuple[CharacterIdentityPackDTO, ...], findings: list[IdentityFindingDTO]
) -> None:
    references_by_asset: dict[str, list[ReferenceAssetDescriptorDTO]] = {}
    for pack in identity_packs:
        for reference in pack.references:
            references_by_asset.setdefault(reference.reference_asset_id, []).append(reference)

    for asset_id in sorted(references_by_asset):
        references = references_by_asset[asset_id]
        supplied_hashes = {reference.content_hash for reference in references if reference.content_hash}
        if len(supplied_hashes) > 1:
            findings.append(
                IdentityFindingDTO(
                    code="conflicting_asset_content_hash",
                    status="blocked",
                    message=f"reference asset {asset_id} has conflicting caller-supplied content_hash values",
                    reference_asset_id=asset_id,
                )
            )
        if len({reference.provenance for reference in references}) > 1:
            findings.append(
                IdentityFindingDTO(
                    code="conflicting_asset_provenance",
                    status="blocked",
                    message=f"reference asset {asset_id} has conflicting provenance values",
                    reference_asset_id=asset_id,
                )
            )


def _storyboard_findings(
    identity_packs: tuple[CharacterIdentityPackDTO, ...], storyboard: Mapping[str, object]
) -> list[IdentityFindingDTO]:
    panels = storyboard.get("panels")
    if not isinstance(panels, Sequence) or isinstance(panels, (str, bytes)):
        return [
            IdentityFindingDTO(
                code="invalid_storyboard_panels",
                status="needs_review",
                message="storyboard panels must be a sequence for identity coverage diagnostics",
            )
        ]

    findings: list[IdentityFindingDTO] = []
    for panel_index, panel in enumerate(panels, start=1):
        if not isinstance(panel, Mapping):
            findings.append(
                IdentityFindingDTO(
                    code="invalid_storyboard_panel",
                    status="needs_review",
                    message="storyboard panel must be a mapping for identity coverage diagnostics",
                    panel_index=panel_index,
                )
            )
            continue
        characters = panel.get("characters")
        if characters is None:
            continue
        if not isinstance(characters, Sequence) or isinstance(characters, (str, bytes)):
            findings.append(
                IdentityFindingDTO(
                    code="invalid_storyboard_characters",
                    status="needs_review",
                    message="storyboard panel characters must be a sequence",
                    panel_index=panel_index,
                )
            )
            continue
        character_ids: set[str] = set()
        for character_id in characters:
            if not isinstance(character_id, str) or not character_id.strip():
                findings.append(
                    IdentityFindingDTO(
                        code="invalid_storyboard_character_id",
                        status="needs_review",
                        message="storyboard panel characters must contain nonblank string identifiers",
                        panel_index=panel_index,
                    )
                )
                continue
            character_ids.add(character_id)
        for character_id in sorted(character_ids):
            _append_storyboard_coverage_finding(identity_packs, character_id, panel_index, findings)
    return findings


def _append_storyboard_coverage_finding(
    identity_packs: tuple[CharacterIdentityPackDTO, ...],
    character_id: str,
    panel_index: int,
    findings: list[IdentityFindingDTO],
) -> None:
    candidates = tuple(pack for pack in identity_packs if pack.character_id == character_id)
    approved_primary_candidates = tuple(pack for pack in candidates if _is_ready(pack))
    if not candidates:
        findings.append(
            IdentityFindingDTO(
                code="missing_storyboard_identity_pack",
                status="needs_evidence",
                message=f"storyboard character {character_id} has no identity pack",
                character_id=character_id,
                panel_index=panel_index,
            )
        )
    elif not approved_primary_candidates:
        findings.append(
            IdentityFindingDTO(
                code="storyboard_character_not_ready",
                status="needs_evidence",
                message=f"storyboard character {character_id} has no approved primary_identity evidence",
                character_id=character_id,
                panel_index=panel_index,
            )
        )
    elif len(approved_primary_candidates) > 1:
        findings.append(
            IdentityFindingDTO(
                code="storyboard_character_version_selection_required",
                status="needs_review",
                message=(
                    f"storyboard character {character_id} has multiple approved identity versions; "
                    "explicit version selection is required by a future consumer"
                ),
                character_id=character_id,
                panel_index=panel_index,
            )
        )


def _has_primary_identity(pack: CharacterIdentityPackDTO) -> bool:
    return any(reference.reference_role == "primary_identity" for reference in pack.references)


def _is_ready(pack: CharacterIdentityPackDTO) -> bool:
    return pack.approval is not None and _has_primary_identity(pack)


def _duplicate_strings(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return tuple(sorted(duplicates))


def _duplicate_pairs(values: Iterable[tuple[str, str]]) -> tuple[tuple[str, str], ...]:
    seen: set[tuple[str, str]] = set()
    duplicates: set[tuple[str, str]] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return tuple(sorted(duplicates))


def _pack_finding(
    pack: CharacterIdentityPackDTO, code: str, status: Literal["needs_evidence"], message: str
) -> IdentityFindingDTO:
    return IdentityFindingDTO(
        code=code,
        status=status,
        message=message,
        identity_id=pack.identity_id,
        character_id=pack.character_id,
        version=pack.version,
    )


def _finding_key(finding: IdentityFindingDTO) -> tuple[str, str, str, str, str, int, str]:
    return (
        finding.code,
        finding.identity_id,
        finding.character_id,
        finding.version,
        finding.reference_asset_id,
        finding.panel_index or 0,
        finding.message,
    )


def _report_status(
    findings: tuple[IdentityFindingDTO, ...],
) -> Literal["ready", "needs_evidence", "needs_review", "blocked"]:
    if not findings:
        return "ready"
    return max(findings, key=lambda finding: _STATUS_PRIORITY[finding.status]).status
