from __future__ import annotations

import hashlib
import os
import sqlite3
import struct
import zlib
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from fastapi.testclient import TestClient

from manga_director.api import workflow as workflow_api
from manga_director.api.workflow import create_workflow_app
from manga_director.application.human_visual_review_readiness import (
    HumanVisualReviewReadinessUnavailable,
    ReviewChecklistDecision,
    build_human_visual_review_readiness,
)
from manga_director.application.workflow import WorkflowApplicationService
from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.production.next_generation_deterministic_composite_asset_owner import (
    DeterministicCompositeAssetOwner,
)
from manga_director.production.next_generation_deterministic_page_compositor import (
    encode_rgb_png,
)
from manga_director.production.next_generation_generation_evidence import (
    EvidenceValueDTO,
    GenerationConfigurationEvidenceDTO,
    GenerationEvidenceEnvelopeDTO,
    GenerationIdentityBindingDTO,
    GenerationInputEvidenceDTO,
    GenerationOutputEvidenceDTO,
)
from manga_director.production.next_generation_generation_evidence_persistence import (
    GenerationEvidenceStoreWriteRequest,
    LocalGenerationEvidenceStore,
)
from manga_director.production.next_generation_local_durable_asset_owner import (
    LocalDurableAssetOwner,
    OwnerRegistrationMaterial,
)
from manga_director.production.next_generation_page_composition import (
    AcceptedPanelSource,
    LocalPageCompositionAuthority,
    PageCompositeAsset,
    PageCompositionEvidence,
    PageCompositionRequest,
)
from manga_director.production.next_generation_page_composition_application_ledger import (
    LocalPageCompositionApplicationLedger,
    PageCompositionApplicationBinding,
)
from manga_director.production.next_generation_page_generation_plan import PanelRectangle
from manga_director.production.next_generation_page_output_proof import (
    DeterministicCompositionPageOutputProof,
    ProviderProofLookupResult,
    ResolvedPageOutput,
    build_local_page_output_proof_resolver,
    composition_evidence_sha256,
)
from manga_director.production.next_generation_workflow_application_ledger import (
    LocalWorkflowApplicationLedgerStore,
    WorkflowApplicationLedgerBindingDTO,
    _authoritative_commit_proof,
)
from manga_director.repositories.local_file import LocalFileRepository

_PROJECT = "project-v7-08"
_ATTEMPT = "attempt:v7-08:001"
_PROVIDER = "provider:local"
_CRITERIA = (
    "character_identity",
    "face",
    "costume",
    "props",
    "pose",
    "gaze",
    "emotion",
    "screen_direction",
    "location",
    "time",
    "composition",
    "panel_intent",
    "visible_corruption",
    "truncation",
    "watermark",
    "unsafe_content",
    "unintended_text",
    "continuity_comparison",
)


def _chunk(name: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + name
        + data
        + struct.pack(">I", zlib.crc32(name + data) & 0xFFFFFFFF)
    )


def _png() -> bytes:
    header = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00"))
        + _chunk(b"IEND", b"")
    )


def _known(value: str) -> EvidenceValueDTO:
    return EvidenceValueDTO(availability="known", value=value)


def _evidence(
    asset_id: str,
    digest: str,
    identity_bindings: tuple[GenerationIdentityBindingDTO, ...] = (),
) -> GenerationEvidenceEnvelopeDTO:
    return GenerationEvidenceEnvelopeDTO(
        attempt_id=_ATTEMPT,
        observed_at=datetime(2026, 10, 18, tzinfo=UTC),
        provenance_reference="provenance:v7-08:001",
        input=GenerationInputEvidenceDTO(input_reference="input:v7-08:001"),
        output=GenerationOutputEvidenceDTO(
            output_asset_id=asset_id,
            output_content_hash=_known(digest),
            media_type="image/png",
        ),
        configuration=GenerationConfigurationEvidenceDTO(
            provider_id=_known("local"),
            model_id=_known("model:v7-08"),
            model_version=_known("v1"),
            workflow_id=_known("workflow:v7-08"),
            workflow_version=_known("v1"),
            seed=_known("8"),
        ),
        identity_bindings=identity_bindings,
    )


def _page(state: PageState, asset_id: str) -> Page:
    history = [
        {
            "kind": "workflow",
            "from": "PromptBuilt",
            "to": "Generated",
            "step": "generate",
        }
    ]
    if state in {PageState.QUALITY_CHECKED, PageState.APPROVED}:
        history.append(
            {
                "kind": "workflow",
                "from": "Generated",
                "to": "QualityChecked",
                "step": "quality",
            }
        )
    if state is PageState.APPROVED:
        history.append(
            {
                "kind": "workflow",
                "from": "QualityChecked",
                "to": "Approved",
                "step": "approve",
            }
        )
    panel = {
        "page_id": "1",
        "props": ["prop:book"],
        "location": "location:studio",
        "time": "time:day",
    }
    return Page(
        page_number=1,
        state=state,
        page_design={},
        review={},
        storyboard={},
        prompt={},
        image={"artifact_kind": "logical_output_asset", "output_asset_id": asset_id},
        quality={} if state in {PageState.QUALITY_CHECKED, PageState.APPROVED} else None,
        approval={} if state is PageState.APPROVED else None,
        metadata={
            "previous_page": {**panel, "panel_id": "panel:before"},
            "current_page": {**panel, "panel_id": "panel:current"},
        },
        history=history,
    )


def _seed(
    tmp_path: Path,
    *,
    state: PageState = PageState.QUALITY_CHECKED,
    identity_bindings: tuple[GenerationIdentityBindingDTO, ...] = (),
) -> tuple[LocalFileRepository, object]:
    png = _png()
    repository = LocalFileRepository(tmp_path / "repository")
    normal_root = repository._next_generation_normal_execution_owner_root()
    registration = LocalDurableAssetOwner(normal_root / "assets").register(
        OwnerRegistrationMaterial(
            attempt_id=_ATTEMPT,
            provider_reference=_PROVIDER,
            image_bytes=png,
        )
    )
    assert registration.output is not None
    asset_id = registration.output.output_asset_id
    assert LocalGenerationEvidenceStore(normal_root / "evidence").persist(
        GenerationEvidenceStoreWriteRequest(
            attempt_id=_ATTEMPT,
            provider_reference=_PROVIDER,
            evidence_status="ready",
            generation_evidence=_evidence(
                asset_id,
                hashlib.sha256(png).hexdigest(),
                identity_bindings,
            ),
        )
    ).outcome == "persisted"
    binding = WorkflowApplicationLedgerBindingDTO(
        attempt_id=_ATTEMPT,
        authorization_id="authorization:v7-08:001",
        project_id=_PROJECT,
        page_id="1",
        target_page_reference="target:v7-08:001",
        provider_reference=_PROVIDER,
        output_asset_id=asset_id,
        source_state="PromptBuilt",
        target_state="Generated",
    )
    ledger = LocalWorkflowApplicationLedgerStore(
        repository._workflow_application_ledger_owner_root()
    )
    assert ledger.prepare(binding).outcome == "prepared"
    assert ledger.finalize(binding, _authoritative_commit_proof(binding)).outcome == "applied"
    repository.save(Project(id=_PROJECT, title="V7-08", pages=[_page(state, asset_id)]))
    return repository, build_human_visual_review_readiness(repository)


def _checklist(*, blocked: str | None = None) -> tuple[ReviewChecklistDecision, ...]:
    return tuple(
        ReviewChecklistDecision(
            criterion=criterion,
            outcome="blocked" if criterion == blocked else "acceptable",
            rationale="Reviewed directly",
        )
        for criterion in _CRITERIA
    )


def _submission(*, blocked: str | None = None) -> dict[str, object]:
    return {
        "reviewer_id": "reviewer:local",
        "reviewed_at": datetime(2026, 10, 18, 12, 0, tzinfo=UTC),
        "checklist": _checklist(blocked=blocked),
        "overall_judgment": "acceptable_for_approval_consideration",
        "rationale": "Complete local visual review",
    }


def _body() -> dict[str, object]:
    return {
        "reviewerId": "reviewer:local",
        "reviewedAt": "2026-10-18T12:00:00Z",
        "checklist": [
            {
                "criterion": criterion,
                "outcome": "acceptable",
                "rationale": "Reviewed directly",
            }
            for criterion in _CRITERIA
        ],
        "overallJudgment": "acceptable_for_approval_consideration",
        "rationale": "Complete local visual review",
    }


def _manifest(root: Path) -> tuple[tuple[str, str, int, str], ...]:
    records: list[tuple[str, str, int, str]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_file():
            payload = path.read_bytes()
            records.append((relative, "file", len(payload), hashlib.sha256(payload).hexdigest()))
        else:
            records.append((relative, "directory", 0, ""))
    return tuple(records)


class _Release:
    def release(self) -> None:
        return None


class _CompositionResolver:
    def __init__(self, asset_id: str) -> None:
        self._asset_id = asset_id

    def resolve(
        self, project_id: str, page_id: str, output_asset_id: str
    ) -> ResolvedPageOutput:
        assert (project_id, page_id, output_asset_id) == (_PROJECT, "1", self._asset_id)
        source = AcceptedPanelSource(
            plan_id="plan-1",
            plan_fingerprint="a" * 64,
            project_id=_PROJECT,
            page_id="1",
            panel_id="panel-1",
            panel_order=1,
            request_id="request-1",
            request_fingerprint="b" * 64,
            attempt_id="panel-attempt-1",
            evidence_id="panel-evidence-1",
            asset_id="panel-asset-1",
            content_sha256="c" * 64,
            width=1,
            height=1,
            rectangle=PanelRectangle(
                left=46875, top=31250, right=953125, bottom=968750
            ),
        )
        proof = DeterministicCompositionPageOutputProof(
            project_id=_PROJECT,
            page_id="1",
            target_page_reference="page.project-v7-08.1",
            attempt_id="composition-1",
            provenance_reference="composition-provenance-1",
            asset_id=self._asset_id,
            content_sha256="d" * 64,
            plan_id="plan-1",
            plan_fingerprint="a" * 64,
            request_fingerprint="e" * 64,
            evidence_id="composition-evidence-1",
            evidence_sha256="f" * 64,
            ordered_sources=(source,),
        )
        return ResolvedPageOutput(proof, b"composite", _Release())


class _MissingProviderProofLookup:
    def lookup(
        self, project_id: str, page_id: str, output_asset_id: str
    ) -> ProviderProofLookupResult:
        del project_id, page_id, output_asset_id
        return ProviderProofLookupResult("missing")


def _durable_composition_resolver(
    root: Path,
    *,
    output_asset_id: str,
    image_bytes: bytes,
) -> object:
    source = AcceptedPanelSource(
        plan_id="plan-1",
        plan_fingerprint="a" * 64,
        project_id=_PROJECT,
        page_id="1",
        panel_id="panel-1",
        panel_order=1,
        request_id="request-1",
        request_fingerprint="b" * 64,
        attempt_id="panel-attempt-1",
        evidence_id="panel-evidence-1",
        asset_id="panel-asset-1",
        content_sha256="c" * 64,
        width=1,
        height=1,
        rectangle=PanelRectangle(
            left=46875, top=31250, right=953125, bottom=968750
        ),
    )
    request = PageCompositionRequest(
        composition_attempt_id="composition-1",
        plan_id=source.plan_id,
        plan_fingerprint=source.plan_fingerprint,
        project_id=source.project_id,
        page_id=source.page_id,
        explicit_authorization_reference="composition-authorization-1",
        composition_provenance_reference="composition-provenance-1",
        panel_count=1,
        sources=(source,),
    )
    authority = LocalPageCompositionAuthority(root / "composition")
    assert authority.reserve(request).outcome == "created"
    asset = PageCompositeAsset(
        composition_attempt_id=request.composition_attempt_id,
        request_fingerprint=request.request_fingerprint or "",
        composition_provenance_reference=request.composition_provenance_reference,
        ordered_sources=request.sources,
        asset_id=output_asset_id,
        content_sha256=hashlib.sha256(image_bytes).hexdigest(),
    )
    owner = DeterministicCompositeAssetOwner(root / "composites")
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
        application_id="composition-application-1",
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
    ledger = LocalPageCompositionApplicationLedger(root / "application")
    assert ledger.prepare(binding).outcome == "prepared"
    assert ledger.mark_applied(binding).outcome == "applied"
    return build_local_page_output_proof_resolver(
        provider_proof_lookup=_MissingProviderProofLookup(),
        composition_authority=authority,
        composite_owner=owner,
        composition_application_ledger=ledger,
    )


def test_composition_review_binds_complete_ordered_source_manifest(tmp_path: Path) -> None:
    repository, _legacy = _seed(tmp_path)
    page = repository._load_authoritative_page(_PROJECT, 1)
    asset_id = cast(dict[str, str], page.image)["output_asset_id"]
    service = build_human_visual_review_readiness(
        repository,
        page_output_resolver=_CompositionResolver(asset_id),
    )

    result = service.assess(_PROJECT, 1, **_submission())

    assert result.status == "ready"
    assert result.ready
    assert result.analysis_only


def test_concrete_durable_composition_resolver_drives_review_readiness(
    tmp_path: Path,
) -> None:
    repository, _legacy = _seed(tmp_path)
    asset_id = "composite-1"
    repository.save(
        Project(
            id=_PROJECT,
            title="V7-08",
            pages=[_page(PageState.QUALITY_CHECKED, asset_id)],
        )
    )
    composite = encode_rgb_png(2048, 3072, b"\xff" * (2048 * 3072 * 3))
    resolver = _durable_composition_resolver(
        tmp_path / "composition-sidecars",
        output_asset_id=asset_id,
        image_bytes=composite,
    )
    service = build_human_visual_review_readiness(
        repository, page_output_resolver=resolver
    )

    result = service.assess(_PROJECT, 1, **_submission())

    assert result.status == "ready"
    assert result.ready
    assert result.analysis_only


@pytest.mark.skipif(
    os.name != "nt",
    reason="safe exact-file presentation lease is available only on Windows",
)
@pytest.mark.parametrize(
    ("state", "status", "ready"),
    (
        (PageState.GENERATED, "needs_review", False),
        (PageState.QUALITY_CHECKED, "ready", True),
    ),
)
def test_exact_server_resolved_evidence_is_transient_and_state_bounded(
    tmp_path: Path,
    state: PageState,
    status: str,
    ready: bool,
) -> None:
    repository, service = _seed(tmp_path, state=state)
    before = _manifest(repository._root)

    result = service.assess(_PROJECT, 1, **_submission())

    assert result.status == status
    assert result.ready is ready
    assert result.page_state == state.value
    assert result.analysis_only is True
    assert _manifest(repository._root) == before


@pytest.mark.skipif(
    os.name == "nt",
    reason="non-Windows fail-closed behavior is not applicable on Windows",
)
def test_non_windows_without_safe_exact_file_lease_fails_closed(tmp_path: Path) -> None:
    repository, service = _seed(tmp_path)
    before = _manifest(repository._root)

    with pytest.raises(HumanVisualReviewReadinessUnavailable):
        service.assess(_PROJECT, 1, **_submission())

    assert _manifest(repository._root) == before


def test_missing_sidecars_and_legacy_artifact_fail_without_create_on_read(
    tmp_path: Path,
) -> None:
    repository = LocalFileRepository(tmp_path / "repository")
    repository.save(
        Project(
            id=_PROJECT,
            title="V7-08",
            pages=[
                Page(
                    page_number=1,
                    state=PageState.GENERATED,
                    page_design={},
                    review={},
                    storyboard={},
                    prompt={},
                    image={
                        "artifact_kind": "logical_output_asset",
                        "output_asset_id": "asset:missing",
                    },
                )
            ],
        )
    )
    service = build_human_visual_review_readiness(repository)
    before = _manifest(repository._root)

    with pytest.raises(HumanVisualReviewReadinessUnavailable):
        service.assess(_PROJECT, 1, **_submission())

    assert _manifest(repository._root) == before
    legacy = repository.load(_PROJECT).page(1).model_copy(
        update={"image": {"path": "C:/private/image.png"}}
    )
    repository.save(repository.load(_PROJECT).replace_page(legacy))
    with pytest.raises(HumanVisualReviewReadinessUnavailable):
        service.assess(_PROJECT, 1, **_submission())


@pytest.mark.skipif(
    os.name != "nt",
    reason="safe exact-file presentation lease is available only on Windows",
)
def test_explicit_block_and_approved_page_fail_closed(tmp_path: Path) -> None:
    _repository, service = _seed(tmp_path / "blocked")
    result = service.assess(_PROJECT, 1, **_submission(blocked="face"))
    assert result.status == "blocked"
    assert result.ready is False
    assert any(item.code == "HUMAN_CHECKLIST_BLOCKED" for item in result.findings)

    _repository, approved = _seed(tmp_path / "approved", state=PageState.APPROVED)
    with pytest.raises(HumanVisualReviewReadinessUnavailable):
        approved.assess(_PROJECT, 1, **_submission())


@pytest.mark.skipif(
    os.name != "nt",
    reason="safe exact-file presentation lease is available only on Windows",
)
def test_character_evidence_gaps_never_become_ready(tmp_path: Path) -> None:
    repository, service = _seed(tmp_path / "unbound-character")
    project = repository.load(_PROJECT)
    page = project.page(1)
    current = dict(cast(dict[str, object], page.metadata["current_page"]))
    current["character"] = "character:missing"
    repository.save(
        project.replace_page(
            page.model_copy(update={"metadata": page.metadata | {"current_page": current}})
        )
    )

    unbound = service.assess(_PROJECT, 1, **_submission())

    assert unbound.status == "needs_review"
    assert "VISUAL_QA_EVIDENCE_UNRESOLVED" in {
        finding.code for finding in unbound.findings
    }

    binding = GenerationIdentityBindingDTO(
        character_id="character:expected",
        identity_id="identity:expected:v1",
        identity_version="v1",
        reference_asset_ids=("asset:identity:expected",),
    )
    _repository, missing_panel_character = _seed(
        tmp_path / "missing-panel-character",
        identity_bindings=(binding,),
    )

    incomplete = missing_panel_character.assess(_PROJECT, 1, **_submission())

    assert incomplete.status == "needs_review"
    assert "VISUAL_QA_INCOMPLETE" in {finding.code for finding in incomplete.findings}


@pytest.mark.parametrize("authority", ("ledger", "evidence", "registry"))
def test_missing_or_corrupt_authority_fails_without_create_or_repair(
    tmp_path: Path,
    authority: str,
) -> None:
    repository, service = _seed(tmp_path)
    normal_root = repository._next_generation_normal_execution_owner_root()
    database = {
        "ledger": repository._workflow_application_ledger_owner_root()
        / "workflow-application-ledger.sqlite3",
        "evidence": normal_root / "evidence" / "generation-evidence.sqlite3",
        "registry": normal_root / "assets" / "registry" / "asset-owner.sqlite3",
    }[authority]
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA user_version = 99")
    before = _manifest(repository._root)

    with pytest.raises(HumanVisualReviewReadinessUnavailable):
        service.assess(_PROJECT, 1, **_submission())

    assert _manifest(repository._root) == before


def test_http_contract_rejects_evidence_selection_and_redacts_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, int, dict[str, object]]] = []

    def assess(project_id: str, page_number: int, **values: object) -> SimpleNamespace:
        calls.append((project_id, page_number, values))
        return SimpleNamespace(
            status="ready",
            ready=True,
            page_state="QualityChecked",
            findings=(),
            missing_prerequisites=(),
        )

    monkeypatch.setattr(
        workflow_api,
        "human_visual_review_readiness_for",
        lambda _application: SimpleNamespace(assess=assess),
    )
    application = cast(WorkflowApplicationService, object())
    client = TestClient(create_workflow_app(application))
    response = client.post(
        "/projects/demo/pages/1/visual-review-readiness",
        json=_body(),
    )
    query = client.post(
        "/projects/demo/pages/1/visual-review-readiness?assetId=other",
        json=_body(),
    )
    extra_body = _body() | {"outputAssetId": "asset:other"}
    extra = client.post(
        "/projects/demo/pages/1/visual-review-readiness",
        json=extra_body,
    )
    oversized = client.post(
        "/projects/demo/pages/1/visual-review-readiness",
        json=_body() | {"untrustedPadding": "x" * 33_000},
    )
    transferred = client.post(
        "/projects/demo/pages/1/visual-review-readiness",
        json=_body(),
        headers={"transfer-encoding": "chunked"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "ready": True,
        "pageState": "QualityChecked",
        "findings": [],
        "missingPrerequisites": [],
        "analysisOnly": True,
    }
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert {"etag", "last-modified", "location", "content-disposition"}.isdisjoint(
        response.headers
    )
    assert query.status_code == 422
    assert extra.status_code == 422
    assert oversized.status_code == 422
    assert transferred.status_code == 422
    assert oversized.json() == {
        "code": "invalid_input",
        "message": "Request validation failed.",
    }
    assert all(
        item.headers["cache-control"] == "no-store"
        for item in (query, extra, oversized, transferred)
    )
    assert len(calls) == 1
    assert calls[0][0:2] == ("demo", 1)
    assert "asset" not in repr(calls[0][2]).lower()


@pytest.mark.parametrize(
    "mutation",
    (
        {"reviewedAt": "2026-10-18T12:00:00"},
        {"reviewerId": "reviewer@example.com"},
        {"reviewerId": "C:/private/reviewer"},
        {"reviewerId": "../private/reviewer"},
        {"reviewerId": "reviewer\u0085private"},
        {"rationale": "folder/file"},
        {"rationale": "https://private.invalid/review"},
        {"reviewer_id": "reviewer:alternate"},
        {"reviewed_at": "2026-10-18T12:00:00Z"},
        {"overall_judgment": "acceptable_for_approval_consideration"},
    ),
)
def test_http_contract_rejects_unsafe_human_fields_before_evidence_access(
    monkeypatch: pytest.MonkeyPatch,
    mutation: dict[str, object],
) -> None:
    accessed = False

    def lookup(_application: object) -> None:
        nonlocal accessed
        accessed = True

    monkeypatch.setattr(workflow_api, "human_visual_review_readiness_for", lookup)
    client = TestClient(create_workflow_app(cast(WorkflowApplicationService, object())))

    response = client.post(
        "/projects/demo/pages/1/visual-review-readiness",
        json=_body() | mutation,
    )

    assert response.status_code == 422
    assert response.headers["cache-control"] == "no-store"
    assert accessed is False
    assert "private" not in response.text
    assert "example.com" not in response.text


def test_http_contract_rejects_incomplete_duplicate_and_invalid_not_applicable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    accessed = False

    def lookup(_application: object) -> None:
        nonlocal accessed
        accessed = True

    monkeypatch.setattr(workflow_api, "human_visual_review_readiness_for", lookup)
    client = TestClient(create_workflow_app(cast(WorkflowApplicationService, object())))
    body = _body()
    checklist = cast(list[dict[str, object]], body["checklist"])
    missing = client.post(
        "/projects/demo/pages/1/visual-review-readiness",
        json=body | {"checklist": checklist[:-1]},
    )
    duplicate = client.post(
        "/projects/demo/pages/1/visual-review-readiness",
        json=body | {"checklist": [*checklist[:-1], checklist[0]]},
    )
    invalid_na = [dict(item) for item in checklist]
    invalid_na[0]["outcome"] = "not_applicable"
    not_applicable = client.post(
        "/projects/demo/pages/1/visual-review-readiness",
        json=body | {"checklist": invalid_na},
    )

    assert {missing.status_code, duplicate.status_code, not_applicable.status_code} == {422}
    assert accessed is False
