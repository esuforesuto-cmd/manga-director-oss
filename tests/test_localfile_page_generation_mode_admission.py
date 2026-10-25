from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from threading import Barrier, Event, Lock, get_ident
from types import SimpleNamespace

import pytest

from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState, StateMachine
from manga_director.events import MemoryEventBus
from manga_director.production.next_generation_deterministic_composite_asset_owner import (
    DeterministicCompositeAssetOwner,
)
from manga_director.production.next_generation_deterministic_page_compositor import (
    encode_rgb_png,
)
from manga_director.production.next_generation_generation_evidence_persistence import (
    GenerationEvidenceInventoryObservation,
)
from manga_director.production.next_generation_local_durable_asset_owner import (
    DurableAssetBindingObservation,
    DurableAssetInventoryObservation,
    LocalDurableAssetOwner,
    OwnerRegistrationMaterial,
)
from manga_director.production.next_generation_normal_execution_attempt import (
    LocalNormalExecutionAttemptStore,
    NormalExecutionAttemptRecord,
    NormalExecutionAttemptReservationDTO,
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
    PanelGenerationEvidence,
)
from manga_director.production.next_generation_workflow_application_ledger import (
    LocalWorkflowApplicationLedgerStore,
    WorkflowApplicationInventoryObservation,
    WorkflowApplicationLedgerBindingDTO,
    _authoritative_commit_proof,
)
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.repositories.local_file_durability import LocalFileDurabilityError
from manga_director.workflow import localfile_comfyui_real_image_generation as comfyui_module
from manga_director.workflow import localfile_page_generation_mode_admission as admission_module
from manga_director.workflow import localfile_real_image_generation as legacy_module
from manga_director.workflow.engine import WorkflowEngine
from manga_director.workflow.localfile_page_generation_mode_admission import (
    LocalFilePageGenerationModeAdmission,
    LocalFilePageGenerationModeObservation,
    PageGenerationModeObservation,
    _admit_localfile_legacy_generation,
    _legacy_lifecycle_matrix_matches,
    _panel_chain_matches,
)
from manga_director.workflow.localfile_panel_aware_page_generation import (
    LocalFilePanelAwarePageGeneration,
    PanelAwarePageGenerationOperation,
    PanelAwarePageGenerationResult,
    PanelGenerationUnit,
    PanelProviderExecution,
)
from manga_director.workflow.page_execution_fence import PageExecutionFenceError


class _Fence:
    def __init__(self) -> None:
        self.acquired = 0
        self.released = 0
        self.active = False

    def acquire(self) -> None:
        self.acquired += 1
        self.active = True

    def release(self) -> None:
        self.released += 1
        self.active = False


class _SharedFence:
    def __init__(
        self, lock: Lock, project_id: str = "project-1", page_id: str = "1"
    ) -> None:
        self._lock = lock
        self._project_id = project_id
        self._page_id = page_id
        self._held = False

    def acquire(self) -> None:
        self._lock.acquire()
        self._held = True

    def release(self) -> None:
        self._held = False
        self._lock.release()

    def _r26_is_held_for(self, project_id: str, page_id: str) -> bool:
        return self._held and (project_id, page_id) == (
            self._project_id,
            self._page_id,
        )


class _OrderedSharedFence(_SharedFence):
    def __init__(
        self,
        lock: Lock,
        admitted: Event,
        *,
        winner: bool,
        claim_committed: Callable[[], bool],
    ) -> None:
        super().__init__(lock)
        self._admitted = admitted
        self._winner = winner
        self._claim_committed = claim_committed

    def acquire(self) -> None:
        if not self._winner:
            assert self._admitted.wait(timeout=5)
        super().acquire()

    def release(self) -> None:
        super().release()
        if self._winner and self._claim_committed():
            self._admitted.set()


class _Observations:
    def __init__(self, *values: PageGenerationModeObservation) -> None:
        self.values = list(values)

    def observe(self, project_id: str, page_id: str) -> PageGenerationModeObservation:
        del project_id, page_id
        return self.values.pop(0) if len(self.values) > 1 else self.values[0]


def _claim() -> PageGenerationModeClaim:
    return PageGenerationModeClaim(
        claim_id="claim-1",
        project_id="project-1",
        page_id="page-1",
        page_revision="revision-1",
        page_fingerprint="a" * 64,
        mode="panel_aware",
        mode_binding_reference="plan-1",
        authorizer_reference="authorizer-1",
    )


def _observation(**changes: object) -> PageGenerationModeObservation:
    values: dict[str, object] = {
        "project_id": "project-1",
        "page_id": "page-1",
        "page_revision": "revision-1",
        "page_fingerprint": "a" * 64,
        "page_state": "PromptBuilt",
    }
    values.update(changes)
    return PageGenerationModeObservation(**values)


def _repository(root: Path) -> LocalFileRepository:
    repository = LocalFileRepository(root)
    repository.save(
        Project(
            id="project-1",
            title="Mode admission",
            pages=[
                Page(
                    page_number=1,
                    state=PageState.PROMPT_BUILT,
                    page_design={},
                    review={},
                    storyboard={"panels": [{"panel": 1}]},
                    prompt={"prompt_markdown": "one panel"},
                )
            ],
        )
    )
    return repository


def test_admission_commits_and_replays_one_exact_claim_under_fence(tmp_path: Path) -> None:
    store = LocalPageGenerationModeClaimStore(tmp_path / "claims")
    observation = _observation()
    service = LocalFilePageGenerationModeAdmission(
        store, _Observations(observation, observation)
    )
    fence = _Fence()

    assert service.admit(_claim(), fence).admitted
    assert fence.acquired == fence.released == 1
    replay = LocalFilePageGenerationModeAdmission(
        store, _Observations(observation, observation)
    ).admit(_claim(), fence)
    assert replay.admitted
    guarded = LocalFilePageGenerationModeAdmission(
        store, _Observations(observation, observation)
    )
    final, applied = guarded.run_admitted(
        _claim(), fence, lambda: fence.active
    )
    assert final.admitted
    assert applied is True
    assert not fence.active


def test_mixed_modes_and_changed_page_authority_fail_closed(tmp_path: Path) -> None:
    store = LocalPageGenerationModeClaimStore(tmp_path / "claims")
    mixed = _observation(
        legacy_record_references=("legacy-1",),
        panel_record_references=("plan-1",),
    )
    assert (
        LocalFilePageGenerationModeAdmission(store, _Observations(mixed))
        .admit(_claim(), _Fence())
        .code
        == "mixed_generation_modes"
    )

    before = _observation()
    after = _observation(page_fingerprint="b" * 64)
    changed = LocalFilePageGenerationModeAdmission(
        store, _Observations(before, after)
    ).admit(_claim(), _Fence())
    assert changed.code == "page_authority_changed"


def test_concurrent_modes_have_one_durable_winner(tmp_path: Path) -> None:
    store = LocalPageGenerationModeClaimStore(tmp_path / "claims")
    observation = _observation()
    shared_lock = Lock()
    panel = _claim()
    legacy = PageGenerationModeClaim(
        claim_id="claim-legacy",
        project_id="project-1",
        page_id="page-1",
        page_revision="revision-1",
        page_fingerprint="a" * 64,
        mode="legacy_single_canvas",
        mode_binding_reference="legacy-page-1",
        authorizer_reference="authorizer-1",
    )

    side_effects = {"panel_aware": 0, "legacy_single_canvas": 0}

    def admit(claim: PageGenerationModeClaim) -> tuple[str, bool | None]:
        service = LocalFilePageGenerationModeAdmission(
            store, _Observations(observation)
        )

        def provider_or_workflow_start() -> bool:
            side_effects[claim.mode] += 1
            return True

        result, action = service.run_provider_start_admitted(
            claim, _SharedFence(shared_lock), provider_or_workflow_start
        )
        return result.outcome, action

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = tuple(executor.map(admit, (panel, legacy)))

    assert sorted(item[0] for item in outcomes) == ["admitted", "blocked"]
    assert sorted(item[1] for item in outcomes if item[1] is not None) == [True]
    assert sum(side_effects.values()) == 1
    lookup = store.lookup_active("project-1", "page-1", "revision-1")
    assert lookup.outcome == "found"
    assert lookup.claim in {panel, legacy}


@pytest.mark.parametrize("winner", ("legacy", "panel"))
def test_real_legacy_entry_races_panel_workflow_with_one_successful_winner(  # noqa: C901
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, winner: str
) -> None:
    repository = _repository(tmp_path.parent / f"race-{winner}")
    observation = LocalFilePageGenerationModeObservation(repository)
    current = observation.observe("project-1", "1")
    assert current is not None
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
        plan_id="plan-race",
        project_id="project-1",
        page_id="1",
        page_number=1,
        storyboard_reference="storyboard-race",
        storyboard_sha256="a" * 64,
        prompt_built_reference="prompt-race",
        prompt_built_sha256="b" * 64,
        panel_count=1,
        panels=(panel,),
    )
    request = PanelGenerationRequest(
        request_id="panel-request-race",
        plan_id=plan.plan_id,
        plan_fingerprint=plan.plan_fingerprint or "",
        project_id=plan.project_id,
        page_id=plan.page_id,
        panel_id=panel.panel_id,
        panel_order=panel.order,
        panel_prompt=panel,
        capability_requirements=("text-prompt", "png-output"),
        input_reference="input-race",
        input_sha256="c" * 64,
        provenance_reference="panel-provenance-race",
    )
    reservation = PanelAttemptReservation(
        attempt_id="panel-attempt-race",
        plan_id=plan.plan_id,
        plan_fingerprint=plan.plan_fingerprint or "",
        project_id=plan.project_id,
        page_id=plan.page_id,
        panel_id=panel.panel_id,
        panel_order=panel.order,
        request_id=request.request_id,
        request_fingerprint=request.request_fingerprint or "",
        provider_reference="provider-fake",
        authorization_reference="authorization-race",
        execution_fingerprint="d" * 64,
    )
    panel_claim = PageGenerationModeClaim(
        claim_id="claim-panel-race",
        project_id="project-1",
        page_id="1",
        page_revision=current.page_revision,
        page_fingerprint=current.page_fingerprint,
        mode="panel_aware",
        mode_binding_reference=plan.plan_id,
        authorizer_reference="authorizer-1",
    )
    operation = PanelAwarePageGenerationOperation(
        plan=plan,
        mode_claim=panel_claim,
        panel_units=(PanelGenerationUnit(request, reservation),),
        page_revision=current.page_revision,
        composition_attempt_id="composition-race",
        composition_authorization_reference="composition-authorization-race",
        composition_provenance_reference="composition-provenance-race",
        composition_evidence_id="composition-evidence-race",
        composite_asset_id="composite-race",
        application_id="application-race",
    )

    class PanelAssetReader:
        def __init__(self) -> None:
            self.values: dict[str, bytes] = {}

        def read(self, asset: PanelAsset) -> bytes | None:
            return self.values.get(asset.asset_id)

    class CountedPanelProvider:
        def __init__(
            self, reader: PanelAssetReader, asset_owner: LocalDurableAssetOwner
        ) -> None:
            self.calls = 0
            self.reader = reader
            self.asset_owner = asset_owner

        def invoke(
            self,
            panel_request: PanelGenerationRequest,
            panel_reservation: PanelAttemptReservation,
        ) -> PanelProviderExecution:
            self.calls += 1
            image_bytes = encode_rgb_png(1, 1, b"\x10\x20\x30")
            registered = self.asset_owner.register(
                OwnerRegistrationMaterial(
                    panel_reservation.attempt_id,
                    panel_reservation.provider_reference,
                    image_bytes,
                )
            )
            assert registered.output is not None
            digest = hashlib.sha256(image_bytes).hexdigest()
            asset = PanelAsset(
                asset_id=registered.output.output_asset_id,
                plan_id=panel_request.plan_id,
                plan_fingerprint=panel_request.plan_fingerprint or "",
                project_id=panel_request.project_id,
                page_id=panel_request.page_id,
                panel_id=panel_request.panel_id,
                panel_order=panel_request.panel_order,
                request_id=panel_request.request_id,
                request_fingerprint=panel_request.request_fingerprint or "",
                attempt_id=panel_reservation.attempt_id,
                width=1,
                height=1,
                content_sha256=digest,
            )
            evidence = PanelGenerationEvidence(
                evidence_id="panel-evidence-race",
                plan_id=panel_request.plan_id,
                plan_fingerprint=panel_request.plan_fingerprint or "",
                project_id=panel_request.project_id,
                page_id=panel_request.page_id,
                panel_id=panel_request.panel_id,
                panel_order=panel_request.panel_order,
                request_id=panel_request.request_id,
                request_fingerprint=panel_request.request_fingerprint or "",
                attempt_id=panel_reservation.attempt_id,
                input_reference=panel_request.input_reference,
                input_sha256=panel_request.input_sha256,
                provider_reference=panel_reservation.provider_reference,
                provider_configuration_fingerprint="e" * 64,
                provenance_reference=panel_request.provenance_reference,
                output_asset_id=asset.asset_id,
                output_sha256=digest,
                media_type="image/png",
                width=1,
                height=1,
                outcome="accepted",
                attempt_state="PANEL_ACCEPTED",
            )
            self.reader.values[asset.asset_id] = image_bytes
            return PanelProviderExecution(
                "succeeded", asset, evidence, image_bytes
            )

    class CountedGenerate:
        def __init__(self) -> None:
            self.calls = 0

        def generate(self, *_args: object) -> bool:
            self.calls += 1
            return True

    class CountedLegacyClient:
        def __init__(self) -> None:
            self.calls = 0

        def generate_image(self, **_kwargs: object) -> object:
            self.calls += 1
            encoded = base64.b64encode(
                encode_rgb_png(1, 1, b"\x20\x30\x40")
            ).decode("ascii")
            return SimpleNamespace(data=[SimpleNamespace(b64_json=encoded)])

        def close(self) -> None:
            return None

    class CountedLegacyFactory:
        def __init__(self, client: CountedLegacyClient) -> None:
            self.client = client
            self.create_calls = 0

        def create(
            self, credential: str, *, timeout_seconds: int, max_retries: int
        ) -> CountedLegacyClient:
            assert credential == "race-secret"
            assert timeout_seconds == 120
            assert max_retries == 0
            self.create_calls += 1
            return self.client

    root = repository._next_generation_normal_execution_owner_root()
    claim_store = LocalPageGenerationModeClaimStore(observation.claim_root)
    reader = PanelAssetReader()
    provider = CountedPanelProvider(
        reader, LocalDurableAssetOwner(root / "assets")
    )
    generate = CountedGenerate()
    legacy_client = CountedLegacyClient()
    legacy_factory = CountedLegacyFactory(legacy_client)
    panel_workflow = LocalFilePanelAwarePageGeneration(
        mode_admission=LocalFilePageGenerationModeAdmission(
            claim_store, observation
        ),
        panel_authority=LocalPanelGenerationAuthority(
            root / "panel-generation-authority"
        ),
        provider=provider,
        panel_reader=reader,
        composition_authority=LocalPageCompositionAuthority(
            root / "page-composition-authority"
        ),
        composite_owner=DeterministicCompositeAssetOwner(
            root / "deterministic-composite-owner"
        ),
        application_ledger=LocalPageCompositionApplicationLedger(
            root / "page-composition-application"
        ),
        generate_command=generate,
    )
    shared_lock = Lock()
    start = Barrier(2)
    winner_admitted = Event()

    def claim_committed() -> bool:
        return claim_store.lookup_active(
            "project-1", "1", current.page_revision
        ).outcome == "found"

    monkeypatch.setattr(
        legacy_module,
        "_legacy_fence_factory",
        lambda _project_id, _page_id: _OrderedSharedFence(
            shared_lock,
            winner_admitted,
            winner=winner == "legacy",
            claim_committed=claim_committed,
        ),
    )

    def secret_lookup(name: str) -> str | None:
        return "race-secret" if name == "OPENAI_API_KEY" else None

    legacy_events = MemoryEventBus()

    def legacy_route() -> object:
        start.wait()
        return legacy_module.execute_localfile_real_image_generation(
            repository,
            WorkflowEngine(
                state_machine=StateMachine(),
                event_bus=legacy_events,
                agents={},
            ),
            "project-1",
            "1",
            "human:editor",
            secret_lookup=secret_lookup,
            client_factory=legacy_factory,
            now=lambda: datetime(2026, 10, 25, 12, 0, tzinfo=UTC),
            token_factory=lambda: "7" * 32,
        )

    def panel_route() -> PanelAwarePageGenerationResult:
        start.wait()
        return panel_workflow.execute(
            operation,
            admission_fence=_OrderedSharedFence(
                shared_lock,
                winner_admitted,
                winner=winner == "panel",
                claim_committed=claim_committed,
            ),
        )

    # Every competing repository read must use the same Page fence. POSIX's
    # project fence rejects overlapping in-process reads instead of waiting.
    fence_owner: list[int | None] = [None]
    unguarded_reads: list[int] = []
    original_acquire = _SharedFence.acquire
    original_release = _SharedFence.release
    original_load = repository._load_revisioned

    def tracked_acquire(fence: _SharedFence) -> None:
        original_acquire(fence)
        fence_owner[0] = get_ident()

    def tracked_release(fence: _SharedFence) -> None:
        fence_owner[0] = None
        original_release(fence)

    def guarded_load(project_id: str):
        if fence_owner[0] != get_ident():
            unguarded_reads.append(get_ident())
            raise AssertionError("repository read outside the shared Page fence")
        return original_load(project_id)

    with monkeypatch.context() as guard_patch:
        guard_patch.setattr(_SharedFence, "acquire", tracked_acquire)
        guard_patch.setattr(_SharedFence, "release", tracked_release)
        guard_patch.setattr(repository, "_load_revisioned", guarded_load)
        with ThreadPoolExecutor(max_workers=2) as executor:
            legacy_future = executor.submit(legacy_route)
            panel_future = executor.submit(panel_route)
            outcomes = (legacy_future.result(), panel_future.result())
    assert unguarded_reads == []

    active = claim_store.lookup_active(
        "project-1", "1", current.page_revision
    )
    assert active.outcome == "found" and active.claim is not None
    assert active.claim.mode == (
        "legacy_single_canvas" if winner == "legacy" else "panel_aware"
    )
    assert legacy_client.calls + provider.calls == 1
    if winner == "legacy":
        assert legacy_factory.create_calls == 1
        assert legacy_client.calls == 1
        assert provider.calls == 0
        assert generate.calls == 0
        assert getattr(outcomes[0], "completed", False) is True
        assert outcomes[1].status == "blocked", outcomes[1]
        applied = LocalWorkflowApplicationLedgerStore.observe_page(
            repository._workflow_application_ledger_owner_root(),
            "project-1",
            "1",
        )
        assert applied.outcome == "found"
        assert len(applied.bindings) == 1
        assert LocalPageCompositionApplicationLedger.observe_page_at(
            root / "page-composition-application", "project-1", "1"
        ).outcome == "missing"
    else:
        assert outcomes[1].status == "generated", outcomes[1]
        assert provider.calls == 1
        assert generate.calls == 1
        assert legacy_factory.create_calls == 0
        assert legacy_client.calls == 0
        assert getattr(outcomes[0], "status", None) == "blocked"
        assert legacy_events.published == []
        assert not (root / "attempts").exists()
        applied = LocalPageCompositionApplicationLedger.observe_page_at(
            root / "page-composition-application", "project-1", "1"
        )
        assert applied.outcome == "found"
        assert len(applied.bindings) == 1
        assert LocalWorkflowApplicationLedgerStore.observe_page(
            repository._workflow_application_ledger_owner_root(),
            "project-1",
            "1",
        ).outcome == "missing"


@pytest.mark.parametrize("provider", ("legacy", "comfyui"))
@pytest.mark.parametrize("failure", ("page-fence", "project-fence"))
def test_initial_entry_contention_is_blocked_without_provider_or_workflow_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, provider: str, failure: str
) -> None:
    repository = _repository(tmp_path)
    before = repository.load("project-1")
    root = repository._next_generation_normal_execution_owner_root()
    events = MemoryEventBus()
    engine = WorkflowEngine(state_machine=StateMachine(), event_bus=events, agents={})
    module = legacy_module if provider == "legacy" else comfyui_module
    loads = 0

    class ContendedFence(_Fence):
        def acquire(self) -> None:
            if failure == "page-fence":
                raise PageExecutionFenceError("page_execution_fence_contended")
            super().acquire()

    def contended_load(project_id: str):
        nonlocal loads
        loads += 1
        raise LocalFileDurabilityError("project_commit_fence_contended")

    monkeypatch.setattr(module, "_legacy_fence_factory", lambda *_args: ContendedFence())
    monkeypatch.setattr(repository, "_load_revisioned", contended_load)
    # Any credential/provider composition would fail: no runtime is supplied.
    execute = (
        legacy_module.execute_localfile_real_image_generation
        if provider == "legacy" else comfyui_module.execute_localfile_comfyui_real_image_generation
    )
    result = execute(repository, engine, "project-1", "1", "human:editor")
    assert result.status == "blocked"
    assert loads == (1 if failure == "project-fence" else 0)
    assert events.published == []
    assert repository.load("project-1") == before
    assert not root.exists()


def test_localfile_observation_is_noncreating_and_reconciles_one_legacy_attempt(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    observation = LocalFilePageGenerationModeObservation(repository)
    normal_root = repository._next_generation_normal_execution_owner_root()

    empty = observation.observe("project-1", "1")
    assert empty is not None
    assert empty.legacy_record_references == empty.panel_record_references == ()
    assert not normal_root.exists()

    attempts = LocalNormalExecutionAttemptStore(normal_root / "attempts")
    reservation = NormalExecutionAttemptReservationDTO(
        attempt_id="attempt-1",
        request_id="request-1",
        project_id="project-1",
        page_id="1",
        target_page_reference="page-1",
        provider_reference="provider-1",
        execution_fingerprint="a" * 64,
    )
    attempts.reserve(reservation)
    recovered = observation.observe("project-1", "1")
    assert recovered is not None
    assert len(recovered.legacy_record_references) == 1

    service, result, claim = _admit_localfile_legacy_generation(
        repository,
        "project-1",
        "1",
        reservation.attempt_id,
        "authorizer-1",
        _Fence(),
    )
    assert service is not None and result.admitted and claim is not None


@pytest.mark.parametrize("orphan_owner", ("evidence", "assets"))
def test_legacy_observation_blocks_owner_orphan_without_attempt_or_application(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    orphan_owner: str,
) -> None:
    repository = _repository(tmp_path)
    target = (
        admission_module.LocalGenerationEvidenceStore
        if orphan_owner == "evidence"
        else admission_module.LocalDurableAssetOwner
    )
    monkeypatch.setattr(
        target,
        "observe_presence",
        staticmethod(
            lambda _root, _attempt_ids: SimpleNamespace(outcome="orphaned")
        ),
    )

    assert LocalFilePageGenerationModeObservation(repository).observe(
        "project-1", "1"
    ) is None


def test_panel_observation_blocks_orphan_composite_when_all_plan_ids_are_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository(tmp_path)
    monkeypatch.setattr(
        admission_module.DeterministicCompositeAssetOwner,
        "observe_page_at",
        staticmethod(
            lambda _root, _project_id, _page_id: SimpleNamespace(
                outcome="found",
                composition_attempt_ids=("orphan-composition",),
                assets=(),
            )
        ),
    )

    assert LocalFilePageGenerationModeObservation(repository).observe(
        "project-1", "1"
    ) is None


def test_localfile_observation_blocks_orphan_page_application_before_attempt_lookup(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    ledger = LocalWorkflowApplicationLedgerStore(
        repository._workflow_application_ledger_owner_root()
    )
    binding = WorkflowApplicationLedgerBindingDTO(
        attempt_id="orphan-attempt",
        authorization_id="orphan-authorization",
        project_id="project-1",
        page_id="1",
        target_page_reference="page-1",
        provider_reference="provider-1",
        output_asset_id="orphan-asset",
        source_state="PromptBuilt",
        target_state="Generated",
    )
    assert ledger.prepare(binding).outcome == "prepared"
    assert ledger.finalize(
        binding, _authoritative_commit_proof(binding)
    ).outcome == "applied"

    assert LocalFilePageGenerationModeObservation(repository).observe(
        "project-1", "1"
    ) is None
    service, blocked, claim = _admit_localfile_legacy_generation(
        repository,
        "project-1",
        "1",
        "new-attempt",
        "authorizer-1",
        _Fence(),
    )
    assert service is None and claim is None
    assert blocked.code == "authority_unavailable"


def test_orphan_application_attempt_id_drives_complete_downstream_observation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository(tmp_path)
    binding = WorkflowApplicationLedgerBindingDTO(
        attempt_id="orphan-attempt",
        authorization_id="orphan-authorization",
        project_id="project-1",
        page_id="1",
        target_page_reference="page-1",
        provider_reference="provider-1",
        output_asset_id="orphan-asset",
        source_state="PromptBuilt",
        target_state="Generated",
    )
    application = WorkflowApplicationInventoryObservation(
        "found", ("orphan-attempt",), (binding,)
    )
    observed_attempt_ids: list[tuple[str, tuple[str, ...]]] = []

    monkeypatch.setattr(
        LocalNormalExecutionAttemptStore,
        "observe_page",
        lambda _self, _project_id, _page_id: SimpleNamespace(
            outcome="missing", records=(), authority_attempt_ids=()
        ),
    )
    monkeypatch.setattr(
        LocalWorkflowApplicationLedgerStore,
        "observe_page",
        staticmethod(lambda _root, _project_id, _page_id: application),
    )

    def observe_evidence(
        _root: Path, attempt_ids: tuple[str, ...]
    ) -> GenerationEvidenceInventoryObservation:
        observed_attempt_ids.append(("evidence", attempt_ids))
        return GenerationEvidenceInventoryObservation(
            "found",
            attempt_ids,
            (SimpleNamespace(attempt_id="orphan-attempt"),),
            ("provider-1",),
        )

    def observe_assets(
        _root: Path, attempt_ids: tuple[str, ...]
    ) -> DurableAssetInventoryObservation:
        observed_attempt_ids.append(("assets", attempt_ids))
        return DurableAssetInventoryObservation(
            "found",
            attempt_ids,
            (
                DurableAssetBindingObservation(
                    "orphan-attempt",
                    "provider-1",
                    "orphan-asset",
                    "image/png",
                    "a" * 64,
                ),
            ),
        )

    def observe_application(
        _root: Path, attempt_ids: tuple[str, ...]
    ) -> WorkflowApplicationInventoryObservation:
        observed_attempt_ids.append(("application", attempt_ids))
        return application

    monkeypatch.setattr(
        admission_module.LocalGenerationEvidenceStore,
        "observe_attempts",
        staticmethod(observe_evidence),
    )
    monkeypatch.setattr(
        admission_module.LocalDurableAssetOwner,
        "observe_attempts",
        staticmethod(observe_assets),
    )
    monkeypatch.setattr(
        admission_module.LocalWorkflowApplicationLedgerStore,
        "observe_attempts",
        staticmethod(observe_application),
    )

    assert LocalFilePageGenerationModeObservation(repository).observe(
        "project-1", "1"
    ) is None
    assert observed_attempt_ids == [
        ("evidence", ("orphan-attempt",)),
        ("assets", ("orphan-attempt",)),
        ("application", ("orphan-attempt",)),
    ]


def test_localfile_observation_blocks_mixed_legacy_and_panel_authority(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    normal_root = repository._next_generation_normal_execution_owner_root()
    LocalNormalExecutionAttemptStore(normal_root / "attempts").reserve(
        NormalExecutionAttemptReservationDTO(
            attempt_id="attempt-1",
            request_id="request-1",
            project_id="project-1",
            page_id="1",
            target_page_reference="page-1",
            provider_reference="provider-1",
            execution_fingerprint="a" * 64,
        )
    )
    LocalPanelGenerationAuthority(
        normal_root / "panel-generation-authority"
    ).reserve(
        PanelAttemptReservation(
            attempt_id="panel-attempt-1",
            plan_id="plan-1",
            plan_fingerprint="b" * 64,
            project_id="project-1",
            page_id="1",
            panel_id="panel-1",
            panel_order=1,
            request_id="panel-request-1",
            request_fingerprint="c" * 64,
            provider_reference="provider-1",
            authorization_reference="authorizer-1",
            execution_fingerprint="d" * 64,
        )
    )

    observed = LocalFilePageGenerationModeObservation(repository).observe(
        "project-1", "1"
    )
    assert observed is not None
    assert observed.legacy_record_references and observed.panel_record_references
    _service, result, claim = _admit_localfile_legacy_generation(
        repository, "project-1", "1", "attempt-1", "authorizer-1", _Fence()
    )
    assert not result.admitted
    assert result.code == "mixed_generation_modes"
    assert claim is not None


def test_existing_panel_plan_uses_the_same_localfile_claim_authority(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    normal_root = repository._next_generation_normal_execution_owner_root()
    LocalPanelGenerationAuthority(
        normal_root / "panel-generation-authority"
    ).reserve(
        PanelAttemptReservation(
            attempt_id="panel-attempt-1",
            plan_id="plan-1",
            plan_fingerprint="b" * 64,
            project_id="project-1",
            page_id="1",
            panel_id="panel-1",
            panel_order=1,
            request_id="panel-request-1",
            request_fingerprint="c" * 64,
            provider_reference="provider-1",
            authorization_reference="authorizer-1",
            execution_fingerprint="d" * 64,
        )
    )
    observation = LocalFilePageGenerationModeObservation(repository)
    current = observation.observe("project-1", "1")
    assert current is not None
    claim = PageGenerationModeClaim(
        claim_id="claim-panel-1",
        project_id="project-1",
        page_id="1",
        page_revision=current.page_revision,
        page_fingerprint=current.page_fingerprint,
        mode="panel_aware",
        mode_binding_reference="plan-1",
        authorizer_reference="authorizer-1",
    )
    admission = LocalFilePageGenerationModeAdmission(
        LocalPageGenerationModeClaimStore(observation.claim_root), observation
    )

    assert admission.admit(claim, _Fence()).admitted
    _service, legacy, _legacy_claim = _admit_localfile_legacy_generation(
        repository, "project-1", "1", "legacy-attempt", "authorizer-1", _Fence()
    )
    assert not legacy.admitted
    assert legacy.code in {"panel_mode_conflict", "claim_conflict"}


def test_existing_claim_allows_explicit_legacy_retry_but_claimless_multiple_blocks(
    tmp_path: Path,
) -> None:
    def two_attempts(repository: LocalFileRepository) -> None:
        store = LocalNormalExecutionAttemptStore(
            repository._next_generation_normal_execution_owner_root() / "attempts"
        )
        first = NormalExecutionAttemptReservationDTO(
            attempt_id="attempt-1",
            request_id="request-1",
            project_id="project-1",
            page_id="1",
            target_page_reference="page-1",
            provider_reference="provider-1",
            execution_fingerprint="a" * 64,
        )
        store.reserve(first)
        store.start_provider(first)
        store.record_provider_declared_failure(first)
        store.reserve(
            first.model_copy(
                update={"attempt_id": "attempt-2", "request_id": "request-2"}
            )
        )

    claimed_repository = _repository(tmp_path / "claimed")
    claimed_store = LocalNormalExecutionAttemptStore(
        claimed_repository._next_generation_normal_execution_owner_root()
        / "attempts"
    )
    first = NormalExecutionAttemptReservationDTO(
        attempt_id="attempt-1",
        request_id="request-1",
        project_id="project-1",
        page_id="1",
        target_page_reference="page-1",
        provider_reference="provider-1",
        execution_fingerprint="a" * 64,
    )
    claimed_store.reserve(first)
    claimed_store.start_provider(first)
    claimed_store.record_provider_declared_failure(first)
    assert _admit_localfile_legacy_generation(
        claimed_repository, "project-1", "1", "attempt-1", "authorizer-1", _Fence()
    )[1].admitted
    claimed_store.reserve(
        first.model_copy(
            update={"attempt_id": "attempt-2", "request_id": "request-2"}
        )
    )
    assert _admit_localfile_legacy_generation(
        claimed_repository, "project-1", "1", "attempt-2", "authorizer-1", _Fence()
    )[1].admitted

    claimless_repository = _repository(tmp_path / "claimless")
    two_attempts(claimless_repository)
    service, blocked, claim = _admit_localfile_legacy_generation(
        claimless_repository,
        "project-1",
        "1",
        "attempt-2",
        "authorizer-1",
        _Fence(),
    )
    assert service is None and claim is None
    assert blocked.code == "legacy_reconciliation_ambiguous"


def test_existing_claim_cannot_bypass_hashless_reconciliation_block(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository(tmp_path)
    local_observation = LocalFilePageGenerationModeObservation(repository)
    current = local_observation.observe("project-1", "1")
    assert current is not None
    binding_reference = admission_module._legacy_mode_binding(
        "project-1", "1", current.page_revision
    )
    claim = PageGenerationModeClaim(
        claim_id="claim-legacy-existing",
        project_id="project-1",
        page_id="1",
        page_revision=current.page_revision,
        page_fingerprint=current.page_fingerprint,
        mode="legacy_single_canvas",
        mode_binding_reference=binding_reference,
        authorizer_reference="authorizer-existing",
    )
    claim_store = LocalPageGenerationModeClaimStore(local_observation.claim_root)
    assert claim_store.create_or_confirm(claim).outcome == "created"
    incomplete = PageGenerationModeObservation(
        project_id=current.project_id,
        page_id=current.page_id,
        page_revision=current.page_revision,
        page_fingerprint=current.page_fingerprint,
        page_state=current.page_state,
        legacy_record_references=(binding_reference,),
        legacy_candidate_count=1,
        legacy_reconciliation_eligible=False,
    )

    class HashlessObservation:
        def __init__(self, _repository: LocalFileRepository) -> None:
            self.claim_root = local_observation.claim_root

        def observe(
            self, _project_id: str, _page_id: str
        ) -> PageGenerationModeObservation:
            return incomplete

    monkeypatch.setattr(
        admission_module,
        "LocalFilePageGenerationModeObservation",
        HashlessObservation,
    )

    service, blocked, returned_claim = _admit_localfile_legacy_generation(
        repository,
        "project-1",
        "1",
        "attempt-hashless",
        "authorizer-1",
        _Fence(),
    )

    assert service is None and returned_claim is None
    assert blocked.code == "legacy_reconciliation_incomplete"


def test_legacy_lifecycle_matrix_accepts_only_exact_generated_replay_binding() -> None:
    reservation = NormalExecutionAttemptReservationDTO(
        attempt_id="attempt-1",
        request_id="request-1",
        project_id="project-1",
        page_id="1",
        target_page_reference="page-1",
        provider_reference="provider-1",
        execution_fingerprint="a" * 64,
    )
    evidence_item = SimpleNamespace(
        attempt_id="attempt-1",
        output=SimpleNamespace(
            output_asset_id="asset-1",
            media_type="image/png",
            output_content_hash=SimpleNamespace(
                availability="known", value="b" * 64
            ),
        ),
    )
    evidence = GenerationEvidenceInventoryObservation(
        "found", ("attempt-1",), (evidence_item,), ("provider-1",)
    )
    assets = DurableAssetInventoryObservation(
        "found",
        ("attempt-1",),
        (
            DurableAssetBindingObservation(
                "attempt-1",
                "provider-1",
                "asset-1",
                "image/png",
                "b" * 64,
            ),
        ),
    )
    binding = WorkflowApplicationLedgerBindingDTO(
        attempt_id="attempt-1",
        authorization_id="authorization-1",
        project_id="project-1",
        page_id="1",
        target_page_reference="page-1",
        provider_reference="provider-1",
        output_asset_id="asset-1",
        source_state="PromptBuilt",
        target_state="Generated",
    )
    application = WorkflowApplicationInventoryObservation(
        "found", ("attempt-1",), (binding,)
    )
    crash_window = NormalExecutionAttemptRecord(
        reservation, "PROVIDER_COMPLETED"
    )
    completed = NormalExecutionAttemptRecord(
        reservation, "COMPLETED", "application_event_published"
    )

    for record in (crash_window, completed):
        assert _legacy_lifecycle_matrix_matches(
            (record,), evidence, assets, application, "Generated", "asset-1"
        )
    assert not _legacy_lifecycle_matrix_matches(
        (crash_window,), evidence, assets, application, "PromptBuilt", None
    )
    assert not _legacy_lifecycle_matrix_matches(
        (completed,), evidence, assets, application, "Generated", "asset-other"
    )
    wrong_provider = DurableAssetInventoryObservation(
        "found",
        ("attempt-1",),
        (
            DurableAssetBindingObservation(
                "attempt-1", "provider-2", "asset-1", "image/png", "b" * 64
            ),
        ),
    )
    assert not _legacy_lifecycle_matrix_matches(
        (completed,),
        evidence,
        wrong_provider,
        application,
        "Generated",
        "asset-1",
    )
    hashless = GenerationEvidenceInventoryObservation(
        "found",
        ("attempt-1",),
        (
            SimpleNamespace(
                attempt_id="attempt-1",
                output=SimpleNamespace(
                    output_asset_id="asset-1",
                    media_type="image/png",
                    output_content_hash=None,
                ),
            ),
        ),
        ("provider-1",),
    )
    assert not _legacy_lifecycle_matrix_matches(
        (crash_window,),
        hashless,
        assets,
        WorkflowApplicationInventoryObservation("missing"),
        "PromptBuilt",
        None,
    )
    second_active = NormalExecutionAttemptRecord(
        reservation.model_copy(update={"attempt_id": "attempt-2"}), "RESERVED"
    )
    assert not _legacy_lifecycle_matrix_matches(
        (crash_window, second_active),
        GenerationEvidenceInventoryObservation("missing"),
        DurableAssetInventoryObservation("missing"),
        WorkflowApplicationInventoryObservation("missing"),
        "PromptBuilt",
        None,
    )
    wrong_evidence_provider = GenerationEvidenceInventoryObservation(
        "found", ("attempt-1",), evidence.evidence, ("provider-2",)
    )
    wrong_evidence_asset = DurableAssetInventoryObservation(
        "found",
        ("attempt-1",),
        (
            DurableAssetBindingObservation(
                "attempt-1", "provider-2", "asset-1", "image/png", "b" * 64
            ),
        ),
    )
    assert not _legacy_lifecycle_matrix_matches(
        (crash_window,),
        wrong_evidence_provider,
        wrong_evidence_asset,
        WorkflowApplicationInventoryObservation("missing"),
        "PromptBuilt",
        None,
    )


def test_panel_chain_requires_exact_plan_request_sources_evidence_and_asset() -> None:
    reservation = SimpleNamespace(
        attempt_id="panel-attempt-1",
        plan_id="plan-1",
        plan_fingerprint="a" * 64,
        project_id="project-1",
        page_id="1",
        panel_id="panel-1",
        panel_order=1,
        request_id="request-1",
        request_fingerprint="b" * 64,
        provider_reference="provider-1",
    )
    record = SimpleNamespace(
        reservation=reservation,
        state="PANEL_ACCEPTED",
        output_asset_id="asset-1",
    )
    panel_evidence = SimpleNamespace(
        attempt_id="panel-attempt-1",
        evidence_id="panel-evidence-1",
        plan_id="plan-1",
        plan_fingerprint="a" * 64,
        project_id="project-1",
        page_id="1",
        panel_id="panel-1",
        panel_order=1,
        request_id="request-1",
        request_fingerprint="b" * 64,
        output_asset_id="asset-1",
        output_sha256="c" * 64,
        media_type="image/png",
        width=1024,
        height=1024,
        outcome="accepted",
    )
    source = SimpleNamespace(
        plan_id="plan-1",
        plan_fingerprint="a" * 64,
        project_id="project-1",
        page_id="1",
        panel_id="panel-1",
        panel_order=1,
        request_id="request-1",
        request_fingerprint="b" * 64,
        attempt_id="panel-attempt-1",
        evidence_id="panel-evidence-1",
        asset_id="asset-1",
        content_sha256="c" * 64,
        media_type="image/png",
        width=1024,
        height=1024,
    )
    composition_attempt = SimpleNamespace(
        composition_attempt_id="composition-1",
        plan_id="plan-1",
        plan_fingerprint="a" * 64,
        project_id="project-1",
        page_id="1",
        request_fingerprint="d" * 64,
        composition_provenance_reference="composition-provenance-1",
        ordered_source_asset_ids=("asset-1",),
        ordered_source_hashes=("c" * 64,),
        outcome="completed",
    )
    composition_evidence = SimpleNamespace(
        evidence_id="composition-evidence-1",
        composition_attempt_id="composition-1",
        plan_id="plan-1",
        plan_fingerprint="a" * 64,
        project_id="project-1",
        page_id="1",
        request_fingerprint="d" * 64,
        composition_provenance_reference="composition-provenance-1",
        ordered_sources=(source,),
        output_asset_id="composite-asset-1",
        output_sha256="e" * 64,
        outcome="completed",
        model_dump=lambda **_kwargs: {"canonical": "composition-evidence-1"},
    )
    composite = SimpleNamespace(
        composition_attempt_id="composition-1",
        request_fingerprint="d" * 64,
        composition_provenance_reference="composition-provenance-1",
        ordered_sources=(source,),
        asset_id="composite-asset-1",
        content_sha256="e" * 64,
    )
    panel = SimpleNamespace(records=(record,), evidence=(panel_evidence,))
    panel_assets = DurableAssetInventoryObservation(
        "found",
        ("panel-attempt-1",),
        (
            DurableAssetBindingObservation(
                "panel-attempt-1",
                "provider-1",
                "asset-1",
                "image/png",
                "c" * 64,
            ),
        ),
    )
    composition = SimpleNamespace(
        attempts=(composition_attempt,), evidence=(composition_evidence,)
    )
    composites = SimpleNamespace(
        composition_attempt_ids=("composition-1",),
        missing_composition_attempt_ids=(),
        assets=(composite,),
    )
    application = SimpleNamespace(bindings=())

    assert _panel_chain_matches(
        panel,
        panel_assets,
        composition,
        composites,
        application,
        "revision-1",
        "PromptBuilt",
        None,
    )
    wrong_plan = SimpleNamespace(
        **{**vars(composition_attempt), "plan_fingerprint": "f" * 64}
    )
    assert not _panel_chain_matches(
        panel,
        panel_assets,
        SimpleNamespace(attempts=(wrong_plan,), evidence=(composition_evidence,)),
        composites,
        application,
        "revision-1",
        "PromptBuilt",
        None,
    )
    reserved_attempt = SimpleNamespace(
        **{
            **vars(composition_attempt),
            "composition_attempt_id": "composition-reserved",
            "outcome": "reserved",
        }
    )
    reserved_asset = SimpleNamespace(
        **{
            **vars(composite),
            "composition_attempt_id": "composition-reserved",
        }
    )
    assert _panel_chain_matches(
        panel,
        panel_assets,
        SimpleNamespace(attempts=(reserved_attempt,), evidence=()),
        SimpleNamespace(
            composition_attempt_ids=("composition-reserved",),
            missing_composition_attempt_ids=(),
            assets=(reserved_asset,),
        ),
        application,
        "revision-1",
        "PromptBuilt",
        None,
    )
    assert not _panel_chain_matches(
        panel,
        panel_assets,
        SimpleNamespace(attempts=(reserved_attempt,), evidence=()),
        SimpleNamespace(
            composition_attempt_ids=("composition-reserved",),
            missing_composition_attempt_ids=(),
            assets=(
                SimpleNamespace(
                    **{
                        **vars(reserved_asset),
                        "request_fingerprint": "f" * 64,
                    }
                ),
            ),
        ),
        application,
        "revision-1",
        "PromptBuilt",
        None,
    )
    evidence_sha256 = hashlib.sha256(
        json.dumps(
            composition_evidence.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
    application_binding = SimpleNamespace(
        project_id="project-1",
        page_id="1",
        page_revision="revision-1",
        source_state="PromptBuilt",
        target_state="Generated",
        plan_id="plan-1",
        plan_fingerprint="a" * 64,
        composition_attempt_id="composition-1",
        request_fingerprint="d" * 64,
        composition_provenance_reference="composition-provenance-1",
        evidence_id="composition-evidence-1",
        evidence_sha256=evidence_sha256,
        composite_asset_id="composite-asset-1",
        composite_sha256="e" * 64,
    )
    applied = SimpleNamespace(bindings=(application_binding,))
    assert _panel_chain_matches(
        panel,
        panel_assets,
        composition,
        composites,
        applied,
        "revision-2",
        "Generated",
        "composite-asset-1",
    )
    wrong_application = SimpleNamespace(
        bindings=(
            SimpleNamespace(
                **{**vars(application_binding), "request_fingerprint": "f" * 64}
            ),
        )
    )
    assert not _panel_chain_matches(
        panel,
        panel_assets,
        composition,
        composites,
        wrong_application,
        "revision-2",
        "Generated",
        "composite-asset-1",
    )
    wrong_assets = DurableAssetInventoryObservation(
        "found",
        ("panel-attempt-1",),
        (
            DurableAssetBindingObservation(
                "panel-attempt-1",
                "provider-1",
                "asset-1",
                "image/png",
                "f" * 64,
            ),
        ),
    )
    assert not _panel_chain_matches(
        panel,
        wrong_assets,
        composition,
        composites,
        application,
        "revision-1",
        "PromptBuilt",
        None,
    )


def test_provider_start_rechecks_authority_and_runs_under_same_fence(
    tmp_path: Path,
) -> None:
    store = LocalPageGenerationModeClaimStore(tmp_path / "claims")
    observation = _observation()
    service = LocalFilePageGenerationModeAdmission(
        store,
        _Observations(observation, observation, observation, observation),
    )
    fence = _Fence()
    assert service.admit(_claim(), fence).admitted

    admission, active = service.run_provider_start_admitted(
        _claim(), fence, lambda: fence.active
    )

    assert admission.admitted
    assert active is True
    stale = LocalFilePageGenerationModeAdmission(
        store, _Observations(_observation(page_fingerprint="b" * 64))
    )
    called = False

    def start() -> bool:
        nonlocal called
        called = True
        return True

    blocked, result = stale.run_provider_start_admitted(_claim(), fence, start)
    assert not blocked.admitted
    assert blocked.code == "page_authority_mismatch"
    assert result is None
    assert not called


def test_generated_replay_requires_exact_claim_and_runs_under_same_fence(
    tmp_path: Path,
) -> None:
    store = LocalPageGenerationModeClaimStore(tmp_path / "claims")
    prompt_built = _observation()
    fence = _Fence()
    assert LocalFilePageGenerationModeAdmission(
        store, _Observations(prompt_built, prompt_built)
    ).admit(_claim(), fence).admitted
    generated = _observation(
        page_revision="revision-2",
        page_fingerprint="b" * 64,
        page_state="Generated",
        output_asset_id="composite-1",
    )
    service = LocalFilePageGenerationModeAdmission(
        store, _Observations(generated, generated)
    )

    admission, active = service.run_generated_replay_admitted(
        _claim(), fence, "composite-1", lambda: fence.active
    )

    assert admission.admitted
    assert admission.code == "generated_replay_admitted"
    assert active is True
    assert not fence.active


def test_generated_replay_without_the_exact_source_claim_fails_closed(
    tmp_path: Path,
) -> None:
    generated = _observation(
        page_revision="revision-2",
        page_fingerprint="b" * 64,
        page_state="Generated",
        output_asset_id="composite-1",
    )
    called = False

    def replay() -> bool:
        nonlocal called
        called = True
        return True

    admission, result = LocalFilePageGenerationModeAdmission(
        LocalPageGenerationModeClaimStore(tmp_path / "claims"),
        _Observations(generated),
    ).run_generated_replay_admitted(
        _claim(), _Fence(), "composite-1", replay
    )

    assert not admission.admitted
    assert admission.code == "generated_replay_claim_unavailable"
    assert result is None
    assert not called


def test_generated_replay_requires_exact_current_output_asset(
    tmp_path: Path,
) -> None:
    store = LocalPageGenerationModeClaimStore(tmp_path / "claims")
    prompt_built = _observation()
    assert LocalFilePageGenerationModeAdmission(
        store, _Observations(prompt_built, prompt_built)
    ).admit(_claim(), _Fence()).admitted

    for current_output_asset_id in (None, "composite-other"):
        generated = _observation(
            page_revision="revision-2",
            page_fingerprint="b" * 64,
            page_state="Generated",
            output_asset_id=current_output_asset_id,
        )
        called = False

        def replay() -> bool:
            nonlocal called
            called = True
            return True

        admission, result = LocalFilePageGenerationModeAdmission(
            store, _Observations(generated)
        ).run_generated_replay_admitted(
            _claim(), _Fence(), "composite-1", replay
        )

        assert not admission.admitted
        assert admission.code == "generated_replay_output_asset_mismatch"
        assert result is None
        assert not called
