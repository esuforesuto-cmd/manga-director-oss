from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Literal

import pytest

from manga_director.production.next_generation_deterministic_composite_asset_owner import (
    DeterministicCompositeAssetOwner,
)
from manga_director.production.next_generation_deterministic_page_compositor import (
    encode_rgb_png,
)
from manga_director.production.next_generation_page_composition import (
    LocalPageCompositionAuthority,
    PageCompositionAuthorityResult,
)
from manga_director.production.next_generation_page_composition_application_ledger import (
    LocalPageCompositionApplicationLedger,
    PageCompositionApplicationLedgerResult,
)
from manga_director.production.next_generation_page_generation_mode_claim import (
    LocalPageGenerationModeClaimStore,
    PageGenerationModeClaim,
)
from manga_director.production.next_generation_page_generation_plan import (
    PageGenerationPlan,
    PagePanelSpecification,
    PanelRectangle,
)
from manga_director.production.next_generation_panel_execution_attempt import (
    PanelAttemptReservation,
    PanelGenerationRequest,
)
from manga_director.production.next_generation_panel_generation_evidence import (
    LocalPanelGenerationAuthority,
    PanelAsset,
    PanelGenerationAuthorityResult,
    PanelGenerationEvidence,
    PanelGenerationEvidenceLookupResult,
)
from manga_director.workflow.localfile_page_generation_mode_admission import (
    LocalFilePageGenerationModeAdmission,
    PageGenerationModeObservation,
)
from manga_director.workflow.localfile_panel_aware_page_generation import (
    LocalFilePanelAwarePageGeneration,
    PanelAwarePageGenerationOperation,
    PanelGenerationUnit,
    PanelProviderExecution,
)


class _Fence:
    def acquire(self) -> None:
        return None

    def release(self) -> None:
        return None


class _Observation:
    def observe(self, project_id: str, page_id: str) -> PageGenerationModeObservation:
        return PageGenerationModeObservation(
            project_id=project_id,
            page_id=page_id,
            page_revision="revision-1",
            page_fingerprint="f" * 64,
            page_state="PromptBuilt",
        )


class _ChangingObservation(_Observation):
    def __init__(self) -> None:
        self.calls = 0

    def observe(self, project_id: str, page_id: str) -> PageGenerationModeObservation:
        self.calls += 1
        observation = super().observe(project_id, page_id)
        if self.calls > 3:
            return PageGenerationModeObservation(
                project_id=project_id,
                page_id=page_id,
                page_revision="revision-1",
                page_fingerprint="0" * 64,
                page_state="PromptBuilt",
            )
        return observation


class _StaleBeforeSecondPanelObservation(_ChangingObservation):
    def observe(self, project_id: str, page_id: str) -> PageGenerationModeObservation:
        self.calls += 1
        observation = _Observation.observe(self, project_id, page_id)
        if self.calls > 5:
            return PageGenerationModeObservation(
                project_id=project_id,
                page_id=page_id,
                page_revision="revision-1",
                page_fingerprint="0" * 64,
                page_state="PromptBuilt",
            )
        return observation


class _MutableObservation(_Observation):
    def __init__(self) -> None:
        self.page_state = "PromptBuilt"
        self.page_revision = "revision-1"
        self.page_fingerprint = "f" * 64
        self.output_asset_id: str | None = None

    def observe(self, project_id: str, page_id: str) -> PageGenerationModeObservation:
        observation = super().observe(project_id, page_id)
        return replace(
            observation,
            page_revision=self.page_revision,
            page_fingerprint=self.page_fingerprint,
            page_state=self.page_state,
            output_asset_id=self.output_asset_id,
        )

    def mark_generated(self) -> None:
        self.page_state = "Generated"
        self.page_revision = "revision-2"
        self.page_fingerprint = "0" * 64
        self.output_asset_id = "composite-1"


class _Reader:
    def __init__(self) -> None:
        self.values: dict[str, bytes] = {}

    def read(self, asset: PanelAsset) -> bytes | None:
        return self.values.get(asset.asset_id)


class _Provider:
    def __init__(
        self,
        reader: _Reader,
        *,
        outcome: Literal["succeeded", "declared_failure", "recovery_required"] = (
            "succeeded"
        ),
    ) -> None:
        self.reader = reader
        self.outcome = outcome
        self.calls = 0

    def invoke(
        self, request: PanelGenerationRequest, reservation: PanelAttemptReservation
    ) -> PanelProviderExecution:
        self.calls += 1
        if self.outcome == "declared_failure":
            return PanelProviderExecution("declared_failure")
        if self.outcome == "recovery_required":
            return PanelProviderExecution("recovery_required")
        image_bytes = encode_rgb_png(1, 1, b"\x10\x20\x30")
        digest = hashlib.sha256(image_bytes).hexdigest()
        asset = PanelAsset(
            asset_id=f"panel-asset-{request.panel_order}",
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
            evidence_id=f"panel-evidence-{request.panel_order}",
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
            provider_configuration_fingerprint="d" * 64,
            provenance_reference=request.provenance_reference,
            output_asset_id=asset.asset_id,
            output_sha256=asset.content_sha256,
            media_type="image/png",
            width=asset.width,
            height=asset.height,
            outcome="accepted",
            attempt_state="PANEL_ACCEPTED",
        )
        self.reader.values[asset.asset_id] = image_bytes
        return PanelProviderExecution("succeeded", asset, evidence, image_bytes)


class _Generate:
    def __init__(
        self,
        result: bool = True,
        on_generate: Callable[[], None] | None = None,
    ) -> None:
        self.calls = 0
        self.result = result
        self.on_generate = on_generate

    def generate(self, binding: object, proof: object) -> bool:
        del binding, proof
        self.calls += 1
        if self.on_generate is not None:
            self.on_generate()
        return self.result


def _operation() -> PanelAwarePageGenerationOperation:
    panel = PagePanelSpecification(
        panel_id="panel-1",
        order=1,
        rectangle=PanelRectangle(
            left=46875, top=31250, right=953125, bottom=968750
        ),
        narrative_intent="The detective identifies the hidden mechanism.",
        character_identities=("detective-v1",),
        continuity_bindings=("costume-blue-coat",),
        action="The detective points at the revealed mechanism.",
        background="A locked archive room at midnight.",
        composition="Medium shot with the detective on screen left.",
        constraints=("No lettering",),
    )
    plan = PageGenerationPlan(
        plan_id="plan-1",
        project_id="project-1",
        page_id="page-1",
        page_number=1,
        storyboard_reference="storyboard-1",
        storyboard_sha256="a" * 64,
        prompt_built_reference="prompt-1",
        prompt_built_sha256="b" * 64,
        panel_count=1,
        panels=(panel,),
    )
    request = PanelGenerationRequest(
        request_id="request-1",
        plan_id=plan.plan_id,
        plan_fingerprint=plan.plan_fingerprint or "",
        project_id=plan.project_id,
        page_id=plan.page_id,
        panel_id=panel.panel_id,
        panel_order=panel.order,
        panel_prompt=panel,
        capability_requirements=("text-prompt", "png-output"),
        input_reference="input-1",
        input_sha256="c" * 64,
        provenance_reference="panel-provenance-1",
    )
    reservation = PanelAttemptReservation(
        attempt_id="panel-attempt-1",
        plan_id=plan.plan_id,
        plan_fingerprint=plan.plan_fingerprint or "",
        project_id=plan.project_id,
        page_id=plan.page_id,
        panel_id=panel.panel_id,
        panel_order=panel.order,
        request_id=request.request_id,
        request_fingerprint=request.request_fingerprint or "",
        provider_reference="provider-comfyui",
        authorization_reference="authorization-1",
        execution_fingerprint="e" * 64,
    )
    claim = PageGenerationModeClaim(
        claim_id="claim-1",
        project_id=plan.project_id,
        page_id=plan.page_id,
        page_revision="revision-1",
        page_fingerprint="f" * 64,
        mode="panel_aware",
        mode_binding_reference=plan.plan_id,
        authorizer_reference="authorizer-1",
    )
    return PanelAwarePageGenerationOperation(
        plan=plan,
        mode_claim=claim,
        panel_units=(PanelGenerationUnit(request, reservation),),
        page_revision="revision-1",
        composition_attempt_id="composition-1",
        composition_authorization_reference="composition-authorization-1",
        composition_provenance_reference="composition-provenance-1",
        composition_evidence_id="composition-evidence-1",
        composite_asset_id="composite-1",
        application_id="application-1",
    )


def _service(
    tmp_path: Path,
    provider: _Provider,
    generate: _Generate,
    *,
    observation: _Observation | None = None,
    panel_authority: LocalPanelGenerationAuthority | None = None,
    composition_authority: LocalPageCompositionAuthority | None = None,
) -> LocalFilePanelAwarePageGeneration:
    return LocalFilePanelAwarePageGeneration(
        mode_admission=LocalFilePageGenerationModeAdmission(
            LocalPageGenerationModeClaimStore(tmp_path / "claims"),
            observation or _Observation(),
        ),
        panel_authority=panel_authority
        or LocalPanelGenerationAuthority(tmp_path / "panels"),
        provider=provider,
        panel_reader=provider.reader,
        composition_authority=composition_authority
        or LocalPageCompositionAuthority(tmp_path / "composition"),
        composite_owner=DeterministicCompositeAssetOwner(tmp_path / "composites"),
        application_ledger=LocalPageCompositionApplicationLedger(tmp_path / "application"),
        generate_command=generate,
    )


def _two_panel_operation() -> PanelAwarePageGenerationOperation:
    base = _operation()
    first = base.plan.panels[0].model_copy(
        update={
            "rectangle": PanelRectangle(
                left=46875, top=31250, right=484375, bottom=968750
            )
        }
    )
    second = first.model_copy(
        update={
            "panel_id": "panel-2",
            "order": 2,
            "rectangle": PanelRectangle(
                left=515625, top=31250, right=953125, bottom=968750
            ),
            "action": "The assistant verifies the exposed mechanism.",
        }
    )
    plan_values = base.plan.model_dump(exclude={"plan_fingerprint"})
    plan_values.update({"panel_count": 2, "panels": (first, second)})
    plan = PageGenerationPlan(**plan_values)
    units: list[PanelGenerationUnit] = []
    for index, panel in enumerate(plan.panels, start=1):
        request = PanelGenerationRequest(
            request_id=f"request-{index}",
            plan_id=plan.plan_id,
            plan_fingerprint=plan.plan_fingerprint or "",
            project_id=plan.project_id,
            page_id=plan.page_id,
            panel_id=panel.panel_id,
            panel_order=panel.order,
            panel_prompt=panel,
            capability_requirements=("text-prompt", "png-output"),
            input_reference=f"input-{index}",
            input_sha256="c" * 64,
            provenance_reference=f"panel-provenance-{index}",
        )
        reservation = PanelAttemptReservation(
            attempt_id=f"panel-attempt-{index}",
            plan_id=plan.plan_id,
            plan_fingerprint=plan.plan_fingerprint or "",
            project_id=plan.project_id,
            page_id=plan.page_id,
            panel_id=panel.panel_id,
            panel_order=panel.order,
            request_id=request.request_id,
            request_fingerprint=request.request_fingerprint or "",
            provider_reference="provider-comfyui",
            authorization_reference=f"authorization-{index}",
            execution_fingerprint=str(index) * 64,
        )
        units.append(PanelGenerationUnit(request, reservation))
    return replace(base, plan=plan, panel_units=tuple(units))


def test_complete_panel_set_composes_and_invokes_generate_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reader = _Reader()
    provider = _Provider(reader)
    generate = _Generate()
    output = encode_rgb_png(2048, 3072, b"\xff" * (2048 * 3072 * 3))
    monkeypatch.setattr(
        "manga_director.workflow.localfile_panel_aware_page_generation.compose_page",
        lambda request, panel_pngs: output,
    )

    result = _service(tmp_path, provider, generate).execute(
        _operation(), admission_fence=_Fence()
    )

    assert result.generated
    assert result.provider_calls == provider.calls == 1
    assert generate.calls == 1
    assert result.proof is not None
    assert tuple(source.asset_id for source in result.proof.ordered_sources) == (
        "panel-asset-1",
    )


def test_exact_two_panel_set_preserves_order_and_completeness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reader = _Reader()
    provider = _Provider(reader)
    generate = _Generate()
    output = encode_rgb_png(2048, 3072, b"\xff" * (2048 * 3072 * 3))
    monkeypatch.setattr(
        "manga_director.workflow.localfile_panel_aware_page_generation.compose_page",
        lambda request, panel_pngs: output,
    )

    result = _service(tmp_path, provider, generate).execute(
        _two_panel_operation(), admission_fence=_Fence()
    )

    assert result.generated
    assert result.provider_calls == provider.calls == 2
    assert result.accepted_panel_ids == ("panel-1", "panel-2")
    assert result.proof is not None
    assert tuple(source.panel_order for source in result.proof.ordered_sources) == (1, 2)
    assert tuple(source.panel_id for source in result.proof.ordered_sources) == (
        "panel-1",
        "panel-2",
    )


def test_incomplete_declared_panel_set_is_blocked_before_provider_start(
    tmp_path: Path,
) -> None:
    reader = _Reader()
    provider = _Provider(reader)
    generate = _Generate()
    operation = _two_panel_operation()
    incomplete = replace(operation, panel_units=operation.panel_units[:1])

    result = _service(tmp_path, provider, generate).execute(
        incomplete, admission_fence=_Fence()
    )

    assert result.status == "blocked"
    assert result.code == "operation_binding_mismatch"
    assert provider.calls == 0
    assert generate.calls == 0


def test_declared_panel_failure_stops_without_composition_or_generate(tmp_path: Path) -> None:
    reader = _Reader()
    provider = _Provider(reader, outcome="declared_failure")
    generate = _Generate()

    result = _service(tmp_path, provider, generate).execute(
        _operation(), admission_fence=_Fence()
    )

    assert result.status == "partial"
    assert result.code == "panel_declared_failure"
    assert provider.calls == 1
    assert generate.calls == 0


def test_declared_failure_write_exception_requires_recovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reader = _Reader()
    provider = _Provider(reader, outcome="declared_failure")
    generate = _Generate()
    authority = LocalPanelGenerationAuthority(tmp_path / "panels")

    def fail_write(reservation: PanelAttemptReservation) -> PanelGenerationAuthorityResult:
        del reservation
        raise OSError("unavailable")

    monkeypatch.setattr(authority, "declare_failure", fail_write)

    result = _service(
        tmp_path,
        provider,
        generate,
        panel_authority=authority,
    ).execute(_operation(), admission_fence=_Fence())

    assert result.status == "recovery_required"
    assert result.code == "panel_declared_failure_not_recorded"
    assert provider.calls == 1
    assert generate.calls == 0


def test_stale_page_authority_blocks_before_provider_start(tmp_path: Path) -> None:
    reader = _Reader()
    provider = _Provider(reader)
    generate = _Generate()

    result = _service(
        tmp_path,
        provider,
        generate,
        observation=_ChangingObservation(),
    ).execute(_operation(), admission_fence=_Fence())

    assert result.status == "blocked"
    assert result.code == "page_authority_mismatch"
    assert result.provider_calls == provider.calls == 0
    assert generate.calls == 0


def test_authority_is_rechecked_before_every_panel_provider_start(
    tmp_path: Path,
) -> None:
    reader = _Reader()
    provider = _Provider(reader)
    generate = _Generate()

    result = _service(
        tmp_path,
        provider,
        generate,
        observation=_StaleBeforeSecondPanelObservation(),
    ).execute(_two_panel_operation(), admission_fence=_Fence())

    assert result.status == "blocked"
    assert result.code == "page_authority_mismatch"
    assert result.provider_calls == provider.calls == 1
    assert result.accepted_panel_ids == ("panel-1",)
    assert generate.calls == 0


def test_ambiguous_provider_result_requires_recovery_without_retry(
    tmp_path: Path,
) -> None:
    reader = _Reader()
    provider = _Provider(reader, outcome="recovery_required")
    generate = _Generate()
    authority = LocalPanelGenerationAuthority(tmp_path / "panels")

    result = _service(
        tmp_path,
        provider,
        generate,
        panel_authority=authority,
    ).execute(_operation(), admission_fence=_Fence())

    assert result.status == "recovery_required"
    assert result.code == "provider_outcome_ambiguous"
    assert result.provider_calls == provider.calls == 1
    assert generate.calls == 0
    stored = authority.lookup_attempt("panel-attempt-1")
    assert stored.record is not None
    assert stored.record.state == "RECOVERY_REQUIRED"


@pytest.mark.parametrize("raises", (False, True))
def test_failed_or_throwing_recovery_write_is_reported_without_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, raises: bool
) -> None:
    reader = _Reader()
    provider = _Provider(reader, outcome="recovery_required")
    generate = _Generate()
    authority = LocalPanelGenerationAuthority(tmp_path / "panels")

    def fail_recovery(
        reservation: PanelAttemptReservation,
    ) -> PanelGenerationAuthorityResult:
        if raises:
            raise OSError("unavailable")
        return PanelGenerationAuthorityResult(reservation.attempt_id, "failed")

    monkeypatch.setattr(authority, "require_recovery", fail_recovery)

    result = _service(
        tmp_path,
        provider,
        generate,
        panel_authority=authority,
    ).execute(_operation(), admission_fence=_Fence())

    assert result.status == "recovery_required"
    assert result.code == "panel_recovery_not_recorded"
    assert provider.calls == 1
    assert generate.calls == 0


def test_unproven_declared_failure_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reader = _Reader()
    provider = _Provider(reader, outcome="declared_failure")
    generate = _Generate()
    authority = LocalPanelGenerationAuthority(tmp_path / "panels")
    monkeypatch.setattr(
        authority,
        "declare_failure",
        lambda reservation: PanelGenerationAuthorityResult(
            reservation.attempt_id, "failed"
        ),
    )

    result = _service(
        tmp_path,
        provider,
        generate,
        panel_authority=authority,
    ).execute(_operation(), admission_fence=_Fence())

    assert result.status == "recovery_required"
    assert result.code == "panel_declared_failure_not_recorded"
    assert provider.calls == 1
    assert generate.calls == 0


def test_composition_failure_must_be_durably_recorded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reader = _Reader()
    provider = _Provider(reader)
    generate = _Generate()
    authority = LocalPageCompositionAuthority(tmp_path / "composition")
    monkeypatch.setattr(
        "manga_director.workflow.localfile_panel_aware_page_generation.compose_page",
        lambda request, panel_pngs: (_ for _ in ()).throw(ValueError("invalid")),
    )
    monkeypatch.setattr(
        authority,
        "commit_evidence",
        lambda evidence: PageCompositionAuthorityResult(
            evidence.composition_attempt_id, "failed"
        ),
    )

    result = _service(
        tmp_path,
        provider,
        generate,
        composition_authority=authority,
    ).execute(_operation(), admission_fence=_Fence())

    assert result.status == "recovery_required"
    assert result.code == "composition_failure_not_recorded"
    assert provider.calls == 1
    assert generate.calls == 0


def test_composition_failure_write_exception_requires_recovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reader = _Reader()
    provider = _Provider(reader)
    generate = _Generate()
    authority = LocalPageCompositionAuthority(tmp_path / "composition")
    monkeypatch.setattr(
        "manga_director.workflow.localfile_panel_aware_page_generation.compose_page",
        lambda request, panel_pngs: (_ for _ in ()).throw(ValueError("invalid")),
    )

    def fail_write(evidence: object) -> PageCompositionAuthorityResult:
        del evidence
        raise OSError("unavailable")

    monkeypatch.setattr(authority, "commit_evidence", fail_write)

    result = _service(
        tmp_path,
        provider,
        generate,
        composition_authority=authority,
    ).execute(_operation(), admission_fence=_Fence())

    assert result.status == "recovery_required"
    assert result.code == "composition_failure_not_recorded"
    assert provider.calls == 1
    assert generate.calls == 0


def test_restart_does_not_repeat_provider_or_application(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reader = _Reader()
    provider = _Provider(reader)
    generate = _Generate()
    output = encode_rgb_png(2048, 3072, b"\xff" * (2048 * 3072 * 3))
    monkeypatch.setattr(
        "manga_director.workflow.localfile_panel_aware_page_generation.compose_page",
        lambda request, panel_pngs: output,
    )
    service = _service(tmp_path, provider, generate)

    first = service.execute(_operation(), admission_fence=_Fence())
    second = service.execute(_operation(), admission_fence=_Fence())

    assert first.generated
    assert second.generated
    assert second.code == "generated"
    assert provider.calls == 1
    assert generate.calls == 1


def test_generated_page_replay_verifies_applied_proof_without_side_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observation = _MutableObservation()
    reader = _Reader()
    provider = _Provider(reader)
    generate = _Generate(on_generate=observation.mark_generated)
    output = encode_rgb_png(2048, 3072, b"\xff" * (2048 * 3072 * 3))
    monkeypatch.setattr(
        "manga_director.workflow.localfile_panel_aware_page_generation.compose_page",
        lambda request, panel_pngs: output,
    )
    service = _service(
        tmp_path,
        provider,
        generate,
        observation=observation,
    )

    first = service.execute(_operation(), admission_fence=_Fence())
    second = service.execute(_operation(), admission_fence=_Fence())

    assert first.generated
    assert observation.page_state == "Generated"
    assert second.generated
    assert second.provider_calls == 0
    assert provider.calls == 1
    assert generate.calls == 1


@pytest.mark.parametrize("current_output_asset_id", (None, "composite-other"))
def test_generated_replay_blocks_missing_or_wrong_current_output_asset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    current_output_asset_id: str | None,
) -> None:
    observation = _MutableObservation()
    reader = _Reader()
    provider = _Provider(reader)
    generate = _Generate(on_generate=observation.mark_generated)
    output = encode_rgb_png(2048, 3072, b"\xff" * (2048 * 3072 * 3))
    monkeypatch.setattr(
        "manga_director.workflow.localfile_panel_aware_page_generation.compose_page",
        lambda request, panel_pngs: output,
    )
    service = _service(
        tmp_path,
        provider,
        generate,
        observation=observation,
    )
    assert service.execute(_operation(), admission_fence=_Fence()).generated
    observation.output_asset_id = current_output_asset_id

    replay = service.execute(_operation(), admission_fence=_Fence())

    assert replay.status == "blocked"
    assert replay.code == "generated_replay_output_asset_mismatch"
    assert replay.provider_calls == 0
    assert provider.calls == 1
    assert generate.calls == 1


def test_accepted_evidence_cross_binding_blocks_replay_and_provider_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reader = _Reader()
    provider = _Provider(reader)
    generate = _Generate()
    authority = LocalPanelGenerationAuthority(tmp_path / "panels")
    output = encode_rgb_png(2048, 3072, b"\xff" * (2048 * 3072 * 3))
    monkeypatch.setattr(
        "manga_director.workflow.localfile_panel_aware_page_generation.compose_page",
        lambda request, panel_pngs: output,
    )
    service = _service(
        tmp_path,
        provider,
        generate,
        panel_authority=authority,
    )
    assert service.execute(_operation(), admission_fence=_Fence()).generated
    stored = authority.lookup_evidence("panel-attempt-1")
    assert stored.evidence is not None
    mismatched = stored.evidence.model_copy(update={"panel_id": "panel-other"})
    monkeypatch.setattr(
        authority,
        "lookup_evidence",
        lambda attempt_id: PanelGenerationEvidenceLookupResult(
            attempt_id, "found", mismatched
        ),
    )

    replay = service.execute(_operation(), admission_fence=_Fence())

    assert replay.status == "recovery_required"
    assert replay.code == "panel_attempt_requires_recovery"
    assert provider.calls == 1
    assert generate.calls == 1


def test_restart_resumes_completed_composition_before_application_prepare(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reader = _Reader()
    provider = _Provider(reader)
    generate = _Generate()
    output = encode_rgb_png(2048, 3072, b"\xff" * (2048 * 3072 * 3))
    monkeypatch.setattr(
        "manga_director.workflow.localfile_panel_aware_page_generation.compose_page",
        lambda request, panel_pngs: output,
    )
    service = _service(tmp_path, provider, generate)
    original_prepare = service._application_ledger.prepare
    monkeypatch.setattr(
        service._application_ledger,
        "prepare",
        lambda binding: PageCompositionApplicationLedgerResult(
            binding.application_id, "failed"
        ),
    )

    first = service.execute(_operation(), admission_fence=_Fence())
    monkeypatch.setattr(service._application_ledger, "prepare", original_prepare)
    second = service.execute(_operation(), admission_fence=_Fence())

    assert first.status == "blocked"
    assert first.code == "application_not_prepared"
    assert second.generated
    assert provider.calls == 1
    assert generate.calls == 1


def test_prepared_application_is_not_invoked_twice_after_ambiguous_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reader = _Reader()
    provider = _Provider(reader)
    generate = _Generate(result=False)
    output = encode_rgb_png(2048, 3072, b"\xff" * (2048 * 3072 * 3))
    monkeypatch.setattr(
        "manga_director.workflow.localfile_panel_aware_page_generation.compose_page",
        lambda request, panel_pngs: output,
    )
    service = _service(tmp_path, provider, generate)

    first = service.execute(_operation(), admission_fence=_Fence())
    second = service.execute(_operation(), admission_fence=_Fence())

    assert first.status == "recovery_required"
    assert first.code == "generate_outcome_ambiguous"
    assert second.status == "recovery_required"
    assert second.code == "application_outcome_requires_recovery"
    assert provider.calls == 1
    assert generate.calls == 1
