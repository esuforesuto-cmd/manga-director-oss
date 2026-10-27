from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.production.next_generation_deterministic_composite_asset_owner import (
    DeterministicCompositeAssetOwner,
)
from manga_director.production.next_generation_deterministic_page_compositor import (
    encode_rgb_png,
)
from manga_director.production.next_generation_page_composition import (
    LocalPageCompositionAuthority,
)
from manga_director.production.next_generation_page_composition_application_ledger import (
    LocalPageCompositionApplicationLedger,
)
from manga_director.production.next_generation_page_generation_mode_claim import (
    LocalPageGenerationModeClaimStore,
    PageGenerationModeClaim,
)
from manga_director.production.next_generation_page_generation_plan import PanelRectangle
from manga_director.production.next_generation_panel_execution_attempt import (
    PanelAttemptReservation,
    PanelGenerationRequest,
)
from manga_director.production.next_generation_panel_generation_evidence import (
    LocalPanelGenerationAuthority,
    PanelAsset,
    PanelGenerationEvidence,
)
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.repositories.local_file_durability import RevisionedProjectSnapshot
from manga_director.workflow.localfile_page_generation_mode_admission import (
    LocalFilePageGenerationModeAdmission,
    PageGenerationModeObservation,
)
from manga_director.workflow.localfile_panel_aware_activation_bridge import (
    _build_panel_aware_page_generation_operation,
    _convert_revisioned_page_snapshot,
    _snapshot_page_binding,
)
from manga_director.workflow.localfile_panel_aware_page_generation import (
    LocalFilePanelAwarePageGeneration,
    PanelProviderExecution,
)


class _Fence:
    def acquire(self) -> None:
        return None

    def release(self) -> None:
        return None


class _Observation:
    def __init__(self, snapshot: RevisionedProjectSnapshot) -> None:
        project_id, page_id, _number, page_revision, page_fingerprint, _page = (
            _snapshot_page_binding(snapshot, 1)
        )
        self.value = PageGenerationModeObservation(
            project_id=project_id,
            page_id=page_id,
            page_revision=page_revision,
            page_fingerprint=page_fingerprint,
            page_state="PromptBuilt",
        )

    def observe(self, project_id: str, page_id: str) -> PageGenerationModeObservation:
        assert (project_id, page_id) == (self.value.project_id, self.value.page_id)
        return self.value


class _Reader:
    def __init__(self) -> None:
        self.assets: dict[str, bytes] = {}

    def read(self, asset: PanelAsset) -> bytes | None:
        return self.assets.get(asset.asset_id)


class _FakeProvider:
    def __init__(self) -> None:
        self.reader = _Reader()
        self.calls = 0

    def invoke(
        self, request: PanelGenerationRequest, reservation: PanelAttemptReservation
    ) -> PanelProviderExecution:
        self.calls += 1
        image_bytes = encode_rgb_png(1, 1, b"\x10\x20\x30")
        digest = hashlib.sha256(image_bytes).hexdigest()
        asset = PanelAsset(
            asset_id="panel-asset-v7-014-test",
            plan_id=request.plan_id,
            plan_fingerprint=request.plan_fingerprint,
            project_id=request.project_id,
            page_id=request.page_id,
            panel_id=request.panel_id,
            panel_order=request.panel_order,
            request_id=request.request_id,
            request_fingerprint=request.request_fingerprint or "",
            attempt_id=reservation.attempt_id,
            width=1,
            height=1,
            content_sha256=digest,
        )
        evidence = PanelGenerationEvidence(
            evidence_id="panel-evidence-v7-014-test",
            plan_id=request.plan_id,
            plan_fingerprint=request.plan_fingerprint,
            project_id=request.project_id,
            page_id=request.page_id,
            panel_id=request.panel_id,
            panel_order=request.panel_order,
            request_id=request.request_id,
            request_fingerprint=request.request_fingerprint or "",
            attempt_id=reservation.attempt_id,
            input_reference=request.input_reference,
            input_sha256=request.input_sha256,
            provider_reference=reservation.provider_reference,
            provider_configuration_fingerprint="e" * 64,
            provenance_reference=request.provenance_reference,
            output_asset_id=asset.asset_id,
            output_sha256=digest,
            media_type="image/png",
            width=1,
            height=1,
            outcome="accepted",
            attempt_state="PANEL_ACCEPTED",
        )
        self.reader.assets[asset.asset_id] = image_bytes
        return PanelProviderExecution("succeeded", asset, evidence, image_bytes)


class _Generate:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, binding: object, proof: object) -> bool:
        del binding, proof
        self.calls += 1
        return True


def _panel() -> dict[str, object]:
    return {
        "number": 1,
        "narrative_intent": "Aki discovers the sealed archive door.",
        "characters": ["character-aki-v1"],
        "continuity_bindings": ["costume-aki-blue-coat-v2"],
        "action": "Aki places the brass key into the archive lock.",
        "background": "The east archive corridor before sunrise.",
        "composition": "Medium shot with Aki left and the lock in the foreground.",
        "constraints": ["Keep the blue coat and brass key visible."],
    }


def _source(tmp_path: Path) -> tuple[LocalFileRepository, RevisionedProjectSnapshot]:
    project = Project(
        id="project-v7-014-activation",
        title="V7-14 Slice 3",
        pages=[
            Page(
                page_number=1,
                state=PageState.PROMPT_BUILT,
                page_design={},
                review={},
                storyboard={"panels": [_panel()], "title": "夜明け"},
                dialogue={},
                prompt={"prompt_markdown": "夜明けの鍵 🔑", "tokens": 12},
            )
        ],
        created_at=datetime(2026, 10, 27, tzinfo=UTC),
        updated_at=datetime(2026, 10, 27, tzinfo=UTC),
    )
    repository = LocalFileRepository((tmp_path / "repository").resolve())
    repository.save(project)
    return repository, repository._load_revisioned(project.id)


def test_composed_private_operation_runs_through_existing_page_authorities(
    tmp_path: Path, monkeypatch
) -> None:
    repository, snapshot = _source(tmp_path)
    project_id, page_id, _number, page_revision, page_fingerprint, _page = _snapshot_page_binding(
        snapshot, 1
    )
    conversion = _convert_revisioned_page_snapshot(
        repository,
        snapshot,
        page_number=1,
        layout_profile_id="md-page-compositor-v1",
        layout_profile_version=1,
        rectangles=(PanelRectangle(left=50_000, top=40_000, right=950_000, bottom=960_000),),
    )
    operation = _build_panel_aware_page_generation_operation(
        repository,
        snapshot,
        page_number=1,
        layout_profile_id="md-page-compositor-v1",
        layout_profile_version=1,
        rectangles=(PanelRectangle(left=50_000, top=40_000, right=950_000, bottom=960_000),),
        mode_claim=PageGenerationModeClaim(
            claim_id="claim-v7-014-activation",
            project_id=project_id,
            page_id=page_id,
            page_revision=page_revision,
            page_fingerprint=page_fingerprint,
            mode="panel_aware",
            mode_binding_reference=conversion.plan.plan_id,
            authorizer_reference="mode-authorizer-v7-014-activation",
        ),
        authorization_references=("authorization-v7-014-activation",),
        composition_authorization_reference="composition-authorization-v7-014-activation",
        checkpoint_name="checkpoint_test.safetensors",
    )

    composite_png = encode_rgb_png(2048, 3072, b"\xff" * (2048 * 3072 * 3))
    monkeypatch.setattr(
        "manga_director.workflow.localfile_panel_aware_page_generation.compose_page",
        lambda request, panel_pngs: composite_png,
    )
    provider = _FakeProvider()
    generate = _Generate()
    service = LocalFilePanelAwarePageGeneration(
        mode_admission=LocalFilePageGenerationModeAdmission(
            LocalPageGenerationModeClaimStore(tmp_path / "claims"),
            _Observation(snapshot),
        ),
        panel_authority=LocalPanelGenerationAuthority(tmp_path / "panels"),
        provider=provider,
        panel_reader=provider.reader,
        composition_authority=LocalPageCompositionAuthority(tmp_path / "composition"),
        composite_owner=DeterministicCompositeAssetOwner(tmp_path / "composites"),
        application_ledger=LocalPageCompositionApplicationLedger(tmp_path / "application"),
        generate_command=generate,
    )

    result = service.execute(operation, admission_fence=_Fence())

    assert result.status == "generated"
    assert result.provider_calls == provider.calls == 1
    assert generate.calls == 1
    assert result.proof is not None
    assert result.proof.plan_id == operation.plan.plan_id
    assert result.proof.attempt_id == operation.composition_attempt_id
    assert result.proof.asset_id == operation.composite_asset_id
