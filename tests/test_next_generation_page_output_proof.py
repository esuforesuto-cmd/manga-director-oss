from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace
from typing import Literal

import pytest
from pydantic import ValidationError

from manga_director.domain.state_machine import PageState
from manga_director.production.next_generation_deterministic_composite_asset_owner import (
    DeterministicCompositeAssetOwner,
    DeterministicCompositeReadResult,
)
from manga_director.production.next_generation_deterministic_page_compositor import (
    encode_rgb_png,
)
from manga_director.production.next_generation_page_composition import (
    AcceptedPanelSource,
    LocalPageCompositionAuthority,
    PageCompositeAsset,
    PageCompositionAttempt,
    PageCompositionAuthorityResult,
    PageCompositionEvidence,
    PageCompositionRequest,
)
from manga_director.production.next_generation_page_composition_application_ledger import (
    LocalPageCompositionApplicationLedger,
    PageCompositionApplicationBinding,
)
from manga_director.production.next_generation_page_generation_plan import PanelRectangle
from manga_director.production.next_generation_page_output_proof import (
    CompositionApplicationBindingLookupResult,
    DeterministicCompositionPageOutputProof,
    LocalPageOutputProofResolver,
    PageOutputApplicationAdmission,
    PageOutputProofUnavailable,
    ProviderGenerationPageOutputProof,
    ProviderProofLookupResult,
    build_local_page_output_proof_resolver,
    composition_evidence_sha256,
)
from manga_director.workflow.localfile_page_output_proof_bridge import (
    _PageOutputQualityGate,
)


def _source(**changes: object) -> AcceptedPanelSource:
    values: dict[str, object] = {
        "plan_id": "plan-1",
        "plan_fingerprint": "a" * 64,
        "project_id": "project-1",
        "page_id": "page-1",
        "panel_id": "panel-1",
        "panel_order": 1,
        "request_id": "request-1",
        "request_fingerprint": "b" * 64,
        "attempt_id": "attempt-1",
        "evidence_id": "evidence-1",
        "asset_id": "panel-asset-1",
        "content_sha256": "c" * 64,
        "width": 1,
        "height": 1,
        "rectangle": PanelRectangle(
            left=46875, top=31250, right=953125, bottom=968750
        ),
    }
    values.update(changes)
    return AcceptedPanelSource(**values)


def _composition_proof(**changes: object) -> DeterministicCompositionPageOutputProof:
    values: dict[str, object] = {
        "project_id": "project-1",
        "page_id": "page-1",
        "target_page_reference": "page.project-1.page-1",
        "attempt_id": "composition-1",
        "provenance_reference": "composition-provenance-1",
        "asset_id": "composite-1",
        "content_sha256": "d" * 64,
        "plan_id": "plan-1",
        "plan_fingerprint": "a" * 64,
        "request_fingerprint": "e" * 64,
        "evidence_id": "composition-evidence-1",
        "evidence_sha256": "f" * 64,
        "ordered_sources": (_source(),),
    }
    values.update(changes)
    return DeterministicCompositionPageOutputProof(**values)


def test_closed_output_variants_keep_provider_and_composition_distinct() -> None:
    provider = ProviderGenerationPageOutputProof(
        project_id="project-1",
        page_id="page-1",
        target_page_reference="target:project-1:page-1",
        attempt_id="attempt:v7-04:one",
        provenance_reference="provenance:v7-04:one",
        asset_id="asset:v7-04:one",
        content_sha256=hashlib.sha256(b"png").hexdigest(),
        provider_reference="provider:comfyui",
    )
    composition = _composition_proof()

    assert provider.kind == "provider_generation"
    assert composition.kind == "deterministic_composition"
    assert composition.ordered_sources[0].asset_id == "panel-asset-1"
    admission = PageOutputApplicationAdmission()
    assert not admission.admit(provider).allowed
    assert admission.admit(provider, provider_proof_validated=True).allowed
    assert not admission.admit(composition).allowed


def test_composition_proof_rejects_incomplete_or_mixed_manifest() -> None:
    with pytest.raises(ValidationError):
        _composition_proof(ordered_sources=())
    with pytest.raises(ValidationError):
        _composition_proof(ordered_sources=(_source(plan_id="other-plan"),))
    with pytest.raises(ValidationError):
        _composition_proof(
            ordered_sources=(
                _source(panel_id="panel-2", panel_order=2),
                _source(panel_id="panel-1", panel_order=1),
            )
        )


def test_composition_proof_equality_covers_ordered_source_membership_order_and_hash() -> None:
    first = _source()
    second = _source(
        panel_id="panel-2",
        panel_order=2,
        request_id="request-2",
        request_fingerprint="9" * 64,
        attempt_id="attempt-2",
        evidence_id="evidence-2",
        asset_id="panel-asset-2",
        content_sha256="8" * 64,
    )
    proof = _composition_proof(ordered_sources=(first, second))

    missing_source = proof.model_copy(update={"ordered_sources": (second,)})
    changed_order = proof.model_copy(update={"ordered_sources": (second, first)})
    changed_hash_source = first.model_copy(update={"content_sha256": "7" * 64})
    changed_hash = proof.model_copy(
        update={"ordered_sources": (changed_hash_source, second)}
    )

    assert proof != missing_source
    assert proof != changed_order
    assert proof != changed_hash


def test_quality_gate_checks_only_deterministic_composition_precondition() -> None:
    composition = _composition_proof()
    output = SimpleNamespace(proof=composition, released=0)
    output.release = lambda: setattr(output, "released", output.released + 1)

    class Resolver:
        def resolve(self, *_args: str) -> object:
            return output

    class PreQualityGate:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str, object]] = []

        def require_pre_quality_evidence(
            self,
            project_id: str,
            page_id: str,
            proof: DeterministicCompositionPageOutputProof,
        ) -> str | None:
            self.calls.append((project_id, page_id, proof))
            return None

    pre_quality_gate = PreQualityGate()
    gate = _PageOutputQualityGate(
        Resolver(), pre_quality_gate  # type: ignore[arg-type]
    )
    context = SimpleNamespace(
        state=PageState.GENERATED,
        page={"project_id": "project-1", "page_id": "page-1"},
        artifacts={
            "Generated": {
                "artifact_kind": "logical_output_asset",
                "output_asset_id": composition.asset_id,
            }
        },
    )

    assert gate.require_applied(context) is None
    assert pre_quality_gate.calls == [("project-1", "page-1", composition)]
    assert output.released == 1


def test_quality_gate_fails_closed_without_composition_precondition() -> None:
    composition = _composition_proof()

    class Resolver:
        def resolve(self, *_args: str) -> object:
            output = SimpleNamespace(proof=composition)
            output.release = lambda: None
            return output

    gate = _PageOutputQualityGate(Resolver())  # type: ignore[arg-type]
    context = SimpleNamespace(
        state=PageState.GENERATED,
        page={"project_id": "project-1", "page_id": "page-1"},
        artifacts={
            "Generated": {
                "artifact_kind": "logical_output_asset",
                "output_asset_id": composition.asset_id,
            }
        },
    )

    assert gate.require_applied(context) == "PANEL_VISUAL_QA_EVIDENCE_REQUIRED"


def test_quality_gate_preserves_legacy_provider_proof_behavior() -> None:
    provider = ProviderGenerationPageOutputProof(
        project_id="project-1",
        page_id="page-1",
        target_page_reference="target:project-1:page-1",
        attempt_id="attempt:v7-04:one",
        provenance_reference="provenance:v7-04:one",
        asset_id="asset:v7-04:one",
        content_sha256=hashlib.sha256(b"png").hexdigest(),
        provider_reference="provider:comfyui",
    )
    output = SimpleNamespace(proof=provider, released=0)
    output.release = lambda: setattr(output, "released", output.released + 1)

    class Resolver:
        def resolve(self, *_args: str) -> object:
            return output

    class PreQualityGate:
        def require_pre_quality_evidence(self, *_args: object) -> str | None:
            raise AssertionError("legacy proof must not use panel review gate")

    gate = _PageOutputQualityGate(Resolver(), PreQualityGate())  # type: ignore[arg-type]
    context = SimpleNamespace(
        state=PageState.GENERATED,
        page={"project_id": "project-1", "page_id": "page-1"},
        artifacts={
            "Generated": {
                "artifact_kind": "logical_output_asset",
                "output_asset_id": provider.asset_id,
            }
        },
    )

    assert gate.require_applied(context) is None
    assert output.released == 1


class _ProviderLookup:
    def __init__(
        self,
        outcome: Literal["found", "missing", "invalid"] = "missing",
        proof: object | None = None,
    ) -> None:
        self._outcome = outcome
        self._proof = proof

    def lookup(
        self, project_id: str, page_id: str, asset_id: str
    ) -> ProviderProofLookupResult:
        del project_id, page_id, asset_id
        return ProviderProofLookupResult(self._outcome, self._proof)  # type: ignore[arg-type]


class _CompositeOwner:
    def __init__(
        self,
        asset: PageCompositeAsset,
        image_bytes: bytes,
        *,
        outcome: Literal["found", "missing", "corrupt"] = "found",
    ) -> None:
        self._asset = asset
        self._image_bytes = image_bytes
        self._outcome = outcome

    def read_verified(self, asset_id: str) -> DeterministicCompositeReadResult:
        if self._outcome != "found":
            return DeterministicCompositeReadResult(asset_id, self._outcome)
        return DeterministicCompositeReadResult(
            asset_id,
            "found",
            self._asset,
            self._image_bytes,
        )


class _CompositionAuthority:
    def __init__(
        self, attempt: PageCompositionAttempt, evidence: PageCompositionEvidence
    ) -> None:
        self._attempt = attempt
        self._evidence = evidence

    def lookup(self, attempt_id: str) -> PageCompositionAuthorityResult:
        return PageCompositionAuthorityResult(
            attempt_id, "confirmed", self._attempt, self._evidence
        )


class _ApplicationBindingLookup:
    def __init__(self, binding: PageCompositionApplicationBinding) -> None:
        self._binding = binding

    def lookup_applied(
        self, project_id: str, page_id: str, asset_id: str
    ) -> CompositionApplicationBindingLookupResult:
        if (
            project_id,
            page_id,
            asset_id,
        ) != (
            self._binding.project_id,
            self._binding.page_id,
            self._binding.composite_asset_id,
        ):
            return CompositionApplicationBindingLookupResult("missing")
        return CompositionApplicationBindingLookupResult("found", self._binding)


def test_local_resolver_requires_applied_composition_binding(tmp_path: Path) -> None:
    source = _source()
    asset = PageCompositeAsset(
        composition_attempt_id="composition-1",
        request_fingerprint="d" * 64,
        composition_provenance_reference="composition-provenance-1",
        ordered_sources=(source,),
        asset_id="composite-1",
        content_sha256="e" * 64,
    )
    evidence = PageCompositionEvidence(
        evidence_id="composition-evidence-1",
        composition_attempt_id=asset.composition_attempt_id,
        plan_id="plan-1",
        plan_fingerprint="a" * 64,
        project_id="project-1",
        page_id="page-1",
        request_fingerprint=asset.request_fingerprint,
        composition_provenance_reference=asset.composition_provenance_reference,
        ordered_sources=asset.ordered_sources,
        output_asset_id=asset.asset_id,
        output_sha256=asset.content_sha256,
        outcome="completed",
    )
    attempt = PageCompositionAttempt(
        composition_attempt_id=asset.composition_attempt_id,
        request_fingerprint=asset.request_fingerprint,
        plan_id="plan-1",
        plan_fingerprint="a" * 64,
        project_id="project-1",
        page_id="page-1",
        explicit_authorization_reference="authorization-1",
        composition_provenance_reference=asset.composition_provenance_reference,
        ordered_source_asset_ids=(source.asset_id,),
        ordered_source_hashes=(source.content_sha256,),
        outcome="completed",
    )
    binding = PageCompositionApplicationBinding(
        application_id="application-1",
        project_id="project-1",
        page_id="page-1",
        page_revision="revision-1",
        plan_id="plan-1",
        plan_fingerprint="a" * 64,
        composition_attempt_id=asset.composition_attempt_id,
        composition_provenance_reference=asset.composition_provenance_reference,
        request_fingerprint=asset.request_fingerprint,
        evidence_id=evidence.evidence_id,
        evidence_sha256=composition_evidence_sha256(evidence),
        composite_asset_id=asset.asset_id,
        composite_sha256=asset.content_sha256,
    )
    application_root = tmp_path / "application"
    ledger = LocalPageCompositionApplicationLedger(application_root)
    assert ledger.prepare(binding).outcome == "prepared"
    assert ledger.mark_applied(binding).outcome == "applied"
    resolver = LocalPageOutputProofResolver(
        provider_proof_lookup=_ProviderLookup(),
        composition_authority=_CompositionAuthority(attempt, evidence),
        composite_owner=_CompositeOwner(asset, b"composite"),
        composition_application_ledger=ledger,
        composition_application_binding_resolver=_ApplicationBindingLookup(binding),
    )

    resolved = resolver.resolve("project-1", "page-1", "composite-1")

    assert resolved.image_bytes == b"composite"
    assert resolved.proof.kind == "deterministic_composition"
    assert resolved.proof.ordered_sources == (source,)

    corrupt_provider = LocalPageOutputProofResolver(
        provider_proof_lookup=_ProviderLookup("invalid"),
        composition_authority=_CompositionAuthority(attempt, evidence),
        composite_owner=_CompositeOwner(asset, b"composite"),
        composition_application_ledger=ledger,
        composition_application_binding_resolver=_ApplicationBindingLookup(binding),
    )
    with pytest.raises(PageOutputProofUnavailable):
        corrupt_provider.resolve("project-1", "page-1", "composite-1")

    orphan_binding = LocalPageOutputProofResolver(
        provider_proof_lookup=_ProviderLookup(),
        composition_authority=_CompositionAuthority(attempt, evidence),
        composite_owner=_CompositeOwner(asset, b"composite", outcome="missing"),
        composition_application_ledger=ledger,
        composition_application_binding_resolver=_ApplicationBindingLookup(binding),
    )
    assert (
        orphan_binding._composition_candidate(
            "project-1", "page-1", "composite-1"
        ).outcome
        == "invalid"
    )
    with pytest.raises(PageOutputProofUnavailable):
        orphan_binding.resolve("project-1", "page-1", "composite-1")

    class LegacyProof:
        def __init__(self) -> None:
            self.releases = 0
            self.binding = SimpleNamespace(
                project_id="project-1",
                page_id="page-1",
                target_page_reference="page.project-1.page-1",
                attempt_id="provider-attempt-1",
                output_asset_id="composite-1",
                provider_reference="provider:local",
            )
            self.evidence = SimpleNamespace(
                provenance_reference="provider-provenance-1",
                output=SimpleNamespace(
                    output_content_hash=SimpleNamespace(value=asset.content_sha256)
                ),
            )
            self._lease = SimpleNamespace(image_bytes=b"legacy-png")

        def release(self) -> None:
            self.releases += 1

    competing_proof = LegacyProof()
    competing_candidates = LocalPageOutputProofResolver(
        provider_proof_lookup=_ProviderLookup("found", competing_proof),
        composition_authority=_CompositionAuthority(attempt, evidence),
        composite_owner=_CompositeOwner(asset, b"composite"),
        composition_application_ledger=ledger,
        composition_application_binding_resolver=_ApplicationBindingLookup(binding),
    )
    with pytest.raises(PageOutputProofUnavailable):
        competing_candidates.resolve("project-1", "page-1", "composite-1")
    assert competing_proof.releases == 1


def test_real_slice2_sidecars_resolve_one_applied_composite(tmp_path: Path) -> None:
    source = _source()
    request = PageCompositionRequest(
        composition_attempt_id="composition-1",
        plan_id="plan-1",
        plan_fingerprint="a" * 64,
        project_id="project-1",
        page_id="page-1",
        explicit_authorization_reference="authorization-1",
        composition_provenance_reference="composition-provenance-1",
        panel_count=1,
        sources=(source,),
    )
    authority = LocalPageCompositionAuthority(tmp_path / "composition")
    assert authority.reserve(request).outcome == "created"
    image_bytes = encode_rgb_png(2048, 3072, b"\xff" * (2048 * 3072 * 3))
    asset = PageCompositeAsset(
        composition_attempt_id=request.composition_attempt_id,
        request_fingerprint=request.request_fingerprint or "",
        composition_provenance_reference=request.composition_provenance_reference,
        ordered_sources=request.sources,
        asset_id="composite-1",
        content_sha256=hashlib.sha256(image_bytes).hexdigest(),
    )
    owner = DeterministicCompositeAssetOwner(tmp_path / "composites")
    assert owner.register(asset, image_bytes).outcome == "registered"
    evidence = PageCompositionEvidence(
        evidence_id="composition-evidence-1",
        composition_attempt_id=request.composition_attempt_id,
        plan_id=request.plan_id,
        plan_fingerprint=request.plan_fingerprint,
        project_id=request.project_id,
        page_id=request.page_id,
        request_fingerprint=request.request_fingerprint or "",
        composition_provenance_reference=request.composition_provenance_reference,
        ordered_sources=request.sources,
        output_asset_id=asset.asset_id,
        output_sha256=asset.content_sha256,
        outcome="completed",
    )
    assert authority.commit_evidence(evidence).outcome == "updated"
    binding = PageCompositionApplicationBinding(
        application_id="application-1",
        project_id=request.project_id,
        page_id=request.page_id,
        page_revision="revision-1",
        plan_id=request.plan_id,
        plan_fingerprint=request.plan_fingerprint,
        composition_attempt_id=request.composition_attempt_id,
        composition_provenance_reference=request.composition_provenance_reference,
        request_fingerprint=request.request_fingerprint or "",
        evidence_id=evidence.evidence_id,
        evidence_sha256=composition_evidence_sha256(evidence),
        composite_asset_id=asset.asset_id,
        composite_sha256=asset.content_sha256,
    )
    ledger = LocalPageCompositionApplicationLedger(tmp_path / "application")
    assert ledger.prepare(binding).outcome == "prepared"
    assert ledger.mark_applied(binding).outcome == "applied"
    resolver = build_local_page_output_proof_resolver(
        provider_proof_lookup=_ProviderLookup(),
        composition_authority=authority,
        composite_owner=owner,
        composition_application_ledger=ledger,
    )

    resolved = resolver.resolve("project-1", "page-1", "composite-1")

    assert resolved.proof.kind == "deterministic_composition"
    assert resolved.image_bytes == image_bytes
