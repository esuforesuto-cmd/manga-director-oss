"""Deterministic, secret-free fixtures for the future admission contract."""

from __future__ import annotations

from typing import Final

from manga_director.production.future_generation_admission_contract import (
    CharacterIdentityReferenceV1,
    GenerationAdmissionManifestV1,
    GenerationParameterV1,
    PromptEvidenceV1,
    ProviderRequestBindingV1,
    SnapshotIdentityV1,
    StoryboardEvidenceV1,
    StoryboardPanelV1,
    content_digest,
)

SNAPSHOT_FINGERPRINT = content_digest({"project": "volume:one", "revision": 7})
PROMPT_DIGEST = content_digest({"prompt": "redacted fixture content"})

EMPTY_STORYBOARD: Final[dict[str, object]] = {
    "schema_id": "manga.storyboard",
    "schema_version": "1",
    "panels": (),
}
MISSING_PANEL_ID: Final[dict[str, object]] = {
    "order": 1,
    "purpose": "setup",
    "scene": "station",
    "action": "arrive",
}
DUPLICATE_PANEL_ID: Final[tuple[str, str]] = ("panel:1", "panel:1")
UNSTABLE_PANEL_ORDER: Final[tuple[int, int]] = (2, 1)
MISSING_PURPOSE: Final[dict[str, object]] = {
    "panel_id": "panel:1",
    "order": 1,
    "scene": "station",
    "action": "arrive",
}
MISSING_SCENE: Final[dict[str, object]] = {
    "panel_id": "panel:1",
    "order": 1,
    "purpose": "setup",
    "action": "arrive",
}
MISSING_ACTION: Final[dict[str, object]] = {
    "panel_id": "panel:1",
    "order": 1,
    "purpose": "setup",
    "scene": "station",
}
MALFORMED_VERSION: Final[dict[str, object]] = {"schema_id": "", "schema_version": ""}
LEGACY_PAGE: Final[dict[str, object]] = {
    "state": "PromptBuilt",
    "storyboard": {},
    "prompt": {"prompt_markdown": "legacy"},
}
SECRET_SHAPED_PARAMETER: Final[dict[str, str]] = {"api_key": "not-a-real-secret"}


def storyboard(*, panel_count: int = 1, with_identity: bool = False) -> StoryboardEvidenceV1:
    panels = tuple(
        StoryboardPanelV1(
            panel_id=f"panel:{index}",
            order=index,
            purpose="setup" if index == 1 else "escalation",
            scene="station-platform",
            action="character arrives" if index == 1 else "character responds",
            character_identity_references=(
                CharacterIdentityReferenceV1(
                    character_id="character:aki",
                    identity_id="identity:aki",
                    identity_version="1",
                ),
            )
            if with_identity
            else (),
            reference_asset_ids=("asset:aki:face",) if with_identity else (),
        )
        for index in range(1, panel_count + 1)
    )
    return StoryboardEvidenceV1(
        schema_id="manga.storyboard",
        schema_version="1",
        storyboard_reference="storyboard:volume:one:page:1",
        panels=panels,
    )


def prompt(storyboard_evidence: StoryboardEvidenceV1) -> PromptEvidenceV1:
    return PromptEvidenceV1(
        prompt_reference="prompt:volume:one:page:1",
        prompt_content_digest=PROMPT_DIGEST,
        source_storyboard_digest=storyboard_evidence.content_digest,
    )


def provider_request(*, parameter_value: object = 1024) -> ProviderRequestBindingV1:
    return ProviderRequestBindingV1(
        provider_reference="provider:fixture",
        plugin_reference="plugin:fixture",
        model_id="model:fixture",
        model_version="1",
        workflow_id="workflow:fixture",
        workflow_version="1",
        workflow_content_digest=content_digest({"workflow": "fixture"}),
        parameters=(GenerationParameterV1.from_value("width", parameter_value),),
    )


def manifest(
    *,
    storyboard_evidence: StoryboardEvidenceV1 | None = None,
    prompt_evidence: PromptEvidenceV1 | None = None,
    provider: ProviderRequestBindingV1 | None = None,
    attempt_id: str = "attempt:volume:one:page:1:001",
) -> GenerationAdmissionManifestV1:
    admitted_storyboard = storyboard_evidence or storyboard()
    return GenerationAdmissionManifestV1(
        project_id="project:volume:one",
        page_id="page:1",
        execution_target_reference="target:page:1",
        snapshot=SnapshotIdentityV1(revision=7, fingerprint=SNAPSHOT_FINGERPRINT),
        storyboard=admitted_storyboard,
        prompt=prompt_evidence or prompt(admitted_storyboard),
        provider_request=provider or provider_request(),
        attempt_id=attempt_id,
    )
