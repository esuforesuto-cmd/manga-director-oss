"""Contracts for the internal read-only Character Identity validation preview."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from manga_director.production.next_generation_character_identity import (
    CharacterIdentityPackDTO,
    CharacterIdentityValidationService,
    IdentityApprovalEvidenceDTO,
    ReferenceAssetDescriptorDTO,
)

ROOT = Path(__file__).resolve().parents[1]


def _reference(
    *,
    asset_id: str = "asset:aki-primary",
    role: str = "primary_identity",
    provenance: str = "asset-registry:approved",
    content_hash: str | None = "caller-supplied-hash",
) -> ReferenceAssetDescriptorDTO:
    return ReferenceAssetDescriptorDTO(
        reference_asset_id=asset_id,
        reference_role=role,
        source_reference="asset-registry:aki",
        provenance=provenance,
        content_hash=content_hash,
    )


def _approval() -> IdentityApprovalEvidenceDTO:
    return IdentityApprovalEvidenceDTO(approved_by="reviewer:aki", approved_at="2026-08-21T00:00:00Z")


def _pack(
    *,
    identity_id: str = "identity:aki:v1",
    character_id: str = "character:aki",
    version: str = "v1",
    references: tuple[ReferenceAssetDescriptorDTO, ...] | None = None,
    approval: IdentityApprovalEvidenceDTO | None = None,
) -> CharacterIdentityPackDTO:
    return CharacterIdentityPackDTO(
        identity_id=identity_id,
        character_id=character_id,
        version=version,
        references=references if references is not None else (_reference(),),
        approval=approval if approval is not None else _approval(),
    )


def test_dtos_are_frozen_and_closed() -> None:
    pack = _pack()

    with pytest.raises(ValidationError):
        pack.character_id = "character:mio"
    with pytest.raises(ValidationError):
        CharacterIdentityPackDTO(
            identity_id="identity:aki:v1",
            character_id="character:aki",
            version="v1",
            unexpected=True,
        )


def test_validation_is_canonical_and_preserves_caller_input() -> None:
    face = _reference(asset_id="asset:aki-face", role="face")
    primary = _reference()
    second = _pack(
        identity_id="identity:mio:v1",
        character_id="character:mio",
        references=(face, primary),
    )
    first = _pack(identity_id="identity:aki:v1")
    supplied = (second, first)
    before = tuple(pack.model_dump(mode="json") for pack in supplied)

    report = CharacterIdentityValidationService().validate(supplied)

    assert tuple(pack.identity_id for pack in report.identity_packs) == (
        "identity:aki:v1",
        "identity:mio:v1",
    )
    assert tuple(reference.reference_role for reference in report.identity_packs[1].references) == (
        "face",
        "primary_identity",
    )
    assert tuple(pack.model_dump(mode="json") for pack in supplied) == before
    assert report.status == "ready"
    assert report.ready is True
    assert report.analysis_only is True
    assert report.assets_read is False
    assert report.content_hash_calculated is False
    assert report.network_accessed is False
    assert report.persistence_performed is False


def test_missing_approval_and_primary_identity_are_needs_evidence() -> None:
    report = CharacterIdentityValidationService().validate(
        (
            CharacterIdentityPackDTO(
                identity_id="identity:aki:v1",
                character_id="character:aki",
                version="v1",
                references=(_reference(role="face"),),
            ),
        )
    )

    assert report.status == "needs_evidence"
    assert tuple(finding.code for finding in report.findings) == (
        "missing_approval_evidence",
        "missing_primary_identity",
    )
    assert report.approval_granted is False


def test_duplicate_identity_character_version_and_reference_pairs_are_blocked() -> None:
    duplicate_reference = _reference()
    report = CharacterIdentityValidationService().validate(
        (
            _pack(references=(duplicate_reference, duplicate_reference)),
            _pack(identity_id="identity:aki:v1"),
        )
    )

    assert report.status == "blocked"
    assert tuple(finding.code for finding in report.findings) == (
        "duplicate_character_version",
        "duplicate_identity_id",
        "duplicate_reference_pair",
    )


def test_conflicting_asset_hash_and_provenance_are_blocked_without_hash_calculation() -> None:
    report = CharacterIdentityValidationService().validate(
        (
            _pack(references=(_reference(content_hash="hash-a", provenance="registry:a"),)),
            _pack(
                identity_id="identity:mio:v1",
                character_id="character:mio",
                references=(_reference(content_hash="hash-b", provenance="registry:b"),),
            ),
        )
    )

    assert report.status == "blocked"
    assert tuple(finding.code for finding in report.findings) == (
        "conflicting_asset_content_hash",
        "conflicting_asset_provenance",
    )
    assert report.content_hash_calculated is False


def test_multiple_approved_versions_are_allowed_without_version_selection() -> None:
    report = CharacterIdentityValidationService().validate(
        (
            _pack(),
            _pack(identity_id="identity:aki:v2", version="v2"),
        )
    )

    assert report.status == "ready"
    assert report.version_selected is False
    assert "selected_version" not in type(report).model_fields
    assert "latest_version" not in type(report).model_fields


def test_unknown_extensible_role_requires_deterministic_review() -> None:
    report = CharacterIdentityValidationService().validate(
        (
            _pack(
                references=(
                    _reference(),
                    _reference(
                        asset_id="asset:aki-turnaround", role="studio:profile_turnaround"
                    ),
                )
            ),
        )
    )

    assert report.status == "needs_review"
    assert tuple(finding.code for finding in report.findings) == ("unknown_reference_role",)


def test_storyboard_coverage_never_selects_a_version() -> None:
    report = CharacterIdentityValidationService().validate(
        (
            _pack(),
            _pack(identity_id="identity:aki:v2", version="v2"),
        ),
        storyboard={"panels": [{"characters": ["character:aki", "character:missing"]}]},
    )

    assert report.status == "needs_evidence"
    assert tuple(finding.code for finding in report.findings) == (
        "missing_storyboard_identity_pack",
        "storyboard_character_version_selection_required",
    )
    assert report.version_selected is False


def test_primary_identity_exception_cannot_be_declared_in_the_initial_dto() -> None:
    with pytest.raises(ValidationError):
        CharacterIdentityPackDTO(
            identity_id="identity:crowd:v1",
            character_id="character:crowd",
            version="v1",
            primary_identity_exception=True,
        )


def test_source_keeps_file_network_storage_and_execution_boundaries_out() -> None:
    source = (
        ROOT / "src/manga_director/production/next_generation_character_identity.py"
    ).read_text(encoding="utf-8")

    for forbidden in (
        "manga_director.api",
        "manga_director.cli",
        "manga_director.mcp",
        "manga_director.repositories",
        "manga_director.workflow",
        "manga_director.providers",
        ".execute(",
        ".advance(",
        "save(",
        ".load(",
        "open(",
        "read_text(",
        "requests.",
        "httpx.",
        "hashlib",
    ):
        assert forbidden not in source
