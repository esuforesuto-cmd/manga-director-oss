from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState, StateMachine
from manga_director.events.bus import MemoryEventBus
from manga_director.production.next_generation_comfyui_provider_adapter import (
    ComfyUIInMemoryGeneratedImageMaterial,
)
from manga_director.production.next_generation_deterministic_page_compositor import (
    encode_rgb_png,
)
from manga_director.production.next_generation_page_composition_application_ledger import (
    LocalPageCompositionApplicationLedger,
    PageCompositionApplicationBinding,
)
from manga_director.production.next_generation_page_generation_plan import PanelRectangle
from manga_director.production.next_generation_page_output_proof import (
    DeterministicCompositionPageOutputProof,
)
from manga_director.production.next_generation_panel_generation_evidence import (
    LocalPanelGenerationAuthority,
)
from manga_director.production.next_generation_provider_adapter_composition import (
    ProviderPrivateTransportRequest,
    ProviderPrivateTransportResult,
)
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.workflow.engine import WorkflowEngine
from manga_director.workflow.localfile_panel_aware_generation_activation import (
    _SafeGeneratedPageApplication,
    execute_localfile_panel_aware_generation,
)


@pytest.fixture
def tmp_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    # Keep the fixed durability subtree and SHA-256 PNG name below Windows MAX_PATH.
    return tmp_path_factory.mktemp("pa")


class _Fence:
    def acquire(self) -> None:
        return None

    def release(self) -> None:
        return None

    def _r26_is_held_for(self, project_id: str, page_id: str) -> bool:
        return project_id == "project-v7-15-activation" and page_id == "1"


class _FakeTransport:
    def __init__(self, authority_root: Path, image_bytes: bytes) -> None:
        self._authority_root = authority_root
        self._image_bytes = image_bytes
        self.attempt_id = ""
        self.prepared_state: str | None = None
        self.post_state: str | None = None
        self.submit_count = 0
        self.fail_prepare = False
        self.fail_submit = False

    def preflight(self) -> None:
        return None

    def prepare(self, request: ProviderPrivateTransportRequest):
        self.attempt_id = request.attempt_id
        authority = LocalPanelGenerationAuthority(self._authority_root)
        record = authority.lookup_attempt(self.attempt_id).record
        self.prepared_state = record.state if record is not None else None
        if self.prepared_state != "RESERVED" or self.fail_prepare:
            return None

        def submit() -> ProviderPrivateTransportResult:
            record_after_start = authority.lookup_attempt(self.attempt_id).record
            self.post_state = record_after_start.state if record_after_start is not None else None
            if self.post_state != "PROVIDER_STARTED":
                raise AssertionError("submit ran before durable provider-start")
            self.submit_count += 1
            if self.fail_submit:
                raise TimeoutError("simulated uncertain post-start result")
            return ProviderPrivateTransportResult(
                "succeeded",
                ComfyUIInMemoryGeneratedImageMaterial(self._image_bytes),
            )

        return submit


class _NeverRunAgent:
    def execute(self, context: object):
        del context
        raise AssertionError("only the proof-bound Generated agent may execute")


def _repository(tmp_path: Path) -> LocalFileRepository:
    page = Page(
        page_number=1,
        state=PageState.PROMPT_BUILT,
        page_design={},
        review={},
        storyboard={
            "panels": [
                {
                    "number": 1,
                    "narrative_intent": "Aki finds the archive key.",
                    "characters": ["character-aki-v1"],
                    "continuity_bindings": ["costume-aki-blue-coat-v2"],
                    "action": "Aki turns the brass key in the archive lock.",
                    "background": "The east archive corridor at dawn.",
                    "composition": "Medium shot, Aki left and the lock foreground.",
                    "constraints": ["Keep the key visible."],
                }
            ],
            "title": "Archive",
        },
        dialogue={},
        prompt={"prompt_markdown": "Aki finds the archive key.", "tokens": 7},
    )
    project = Project(
        id="project-v7-15-activation",
        title="V7-15 Slice 1",
        pages=[page],
        created_at=datetime(2026, 10, 27, tzinfo=UTC),
        updated_at=datetime(2026, 10, 27, tzinfo=UTC),
    )
    repository = LocalFileRepository((tmp_path / "r").resolve())
    repository.save(project)
    return repository


def _engine() -> tuple[WorkflowEngine, MemoryEventBus]:
    bus = MemoryEventBus()
    engine = WorkflowEngine(
        state_machine=StateMachine(),
        event_bus=bus,
        agents={PageState.GENERATED: _NeverRunAgent()},
    )
    return engine, bus


def _run(repository, engine, transport, *, now=None):
    return execute_localfile_panel_aware_generation(
        repository,
        engine,
        "project-v7-15-activation",
        1,
        "editor-17",
        "checkpoint_test.safetensors",
        (PanelRectangle(left=50_000, top=40_000, right=950_000, bottom=960_000),),
        transport_factory=lambda _checkpoint, _configuration: transport,
        now=now or (lambda: datetime(2026, 10, 28, tzinfo=UTC)),
        fence_factory=lambda _project_id, _page_id: _Fence(),
    )


def test_activation_prepares_before_start_and_applies_only_bound_proof(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    engine, bus = _engine()
    image_bytes = encode_rgb_png(1024, 1024, b"\xff" * (1024 * 1024 * 3))
    owner_root = repository._next_generation_normal_execution_owner_root()
    transport = _FakeTransport(owner_root / "panel-generation-authority", image_bytes)

    result = _run(repository, engine, transport)

    assert result.status == "generated", (result.status, result.code)
    assert result.provider_calls == 1
    assert transport.prepared_state == "RESERVED"
    assert transport.post_state == "PROVIDER_STARTED"
    assert transport.submit_count == 1
    assert repository._load_revisioned("project-v7-15-activation").project.page(1).state == (
        PageState.GENERATED
    )
    assert len(bus.published) == 1
    assert str(bus.published[0].event_type) == "ImageGenerated"


def test_failed_prepare_reuses_the_exact_reserved_attempt_without_submit(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    engine, _ = _engine()
    image_bytes = encode_rgb_png(1024, 1024, b"\xff" * (1024 * 1024 * 3))
    owner_root = repository._next_generation_normal_execution_owner_root()
    authority_root = owner_root / "panel-generation-authority"
    failed_transport = _FakeTransport(authority_root, image_bytes)
    failed_transport.fail_prepare = True

    failed = _run(repository, engine, failed_transport)

    assert failed.status == "blocked"
    assert failed.code == "panel_provider_preparation_failed"
    assert failed.provider_calls == 0
    first_record = (
        LocalPanelGenerationAuthority(authority_root)
        .lookup_attempt(failed_transport.attempt_id)
        .record
    )
    assert first_record is not None
    assert first_record.state == "RESERVED"
    assert first_record.provider_start_consumed is False

    retry_transport = _FakeTransport(authority_root, image_bytes)
    retried = _run(repository, engine, retry_transport)

    assert retried.status == "generated"
    assert retried.provider_calls == 1
    assert retry_transport.attempt_id == failed_transport.attempt_id
    assert retry_transport.prepared_state == "RESERVED"
    assert retry_transport.post_state == "PROVIDER_STARTED"
    assert retry_transport.submit_count == 1


def test_generated_retry_fails_closed_without_provider_call_or_write(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    engine, _ = _engine()
    image_bytes = encode_rgb_png(1024, 1024, b"\xff" * (1024 * 1024 * 3))
    transport = _FakeTransport(
        repository._next_generation_normal_execution_owner_root() / "panel-generation-authority",
        image_bytes,
    )
    generated = _run(repository, engine, transport)
    assert generated.status == "generated"
    snapshot = repository._load_revisioned("project-v7-15-activation")
    revision_before = snapshot.revision
    digest_before = hashlib.sha256(snapshot.fingerprint.encode()).hexdigest()

    retried = _run(repository, engine, transport)

    after = repository._load_revisioned("project-v7-15-activation")
    assert retried.status == "blocked"
    assert retried.code == "revision_conflict"
    assert retried.provider_calls == 0
    assert transport.submit_count == 1
    assert after.revision == revision_before
    assert hashlib.sha256(after.fingerprint.encode()).hexdigest() == digest_before


def test_uncertain_post_start_result_is_never_submitted_again(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    engine, _ = _engine()
    image_bytes = encode_rgb_png(1024, 1024, b"\xff" * (1024 * 1024 * 3))
    authority_root = (
        repository._next_generation_normal_execution_owner_root() / "panel-generation-authority"
    )
    transport = _FakeTransport(authority_root, image_bytes)
    transport.fail_submit = True

    first = _run(repository, engine, transport)
    second = _run(repository, engine, transport)

    record = (
        LocalPanelGenerationAuthority(authority_root).lookup_attempt(transport.attempt_id).record
    )
    assert first.status == "recovery_required"
    assert first.provider_calls == 1
    assert second.status == "recovery_required"
    assert second.provider_calls == 0
    assert transport.submit_count == 1
    assert record is not None
    assert record.provider_start_consumed is True


def test_mismatched_composition_proof_changes_no_page_event_or_ledger(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    engine, bus = _engine()
    snapshot_before = repository._load_revisioned("project-v7-15-activation")
    ledger = LocalPageCompositionApplicationLedger(
        repository._next_generation_normal_execution_owner_root() / "page-composition-application"
    )
    binding = PageCompositionApplicationBinding(
        application_id="application-v7-15-test",
        project_id="project-v7-15-activation",
        page_id="1",
        page_revision=f"revision-{snapshot_before.revision}",
        plan_id="plan-v7-15-test",
        plan_fingerprint="a" * 64,
        composition_attempt_id="composition-attempt-v7-15-test",
        composition_provenance_reference="composition-provenance-v7-15-test",
        request_fingerprint="b" * 64,
        evidence_id="composition-evidence-v7-15-test",
        evidence_sha256="c" * 64,
        composite_asset_id="composite-asset-v7-15-test",
        composite_sha256="d" * 64,
    )
    proof = DeterministicCompositionPageOutputProof.model_construct(
        project_id=binding.project_id,
        page_id=binding.page_id,
        target_page_reference=f"page.{binding.project_id}.{binding.page_id}",
        attempt_id=binding.composition_attempt_id,
        provenance_reference=binding.composition_provenance_reference,
        asset_id="different-composite-asset",
        content_sha256=binding.composite_sha256,
        plan_id=binding.plan_id,
        plan_fingerprint=binding.plan_fingerprint,
        request_fingerprint=binding.request_fingerprint,
        evidence_id=binding.evidence_id,
        evidence_sha256=binding.evidence_sha256,
        ordered_sources=(),
    )
    application = _SafeGeneratedPageApplication(repository, engine, _Fence())

    assert application.generate(binding, proof) is False

    snapshot_after = repository._load_revisioned("project-v7-15-activation")
    assert snapshot_after.revision == snapshot_before.revision
    assert snapshot_after.fingerprint == snapshot_before.fingerprint
    assert snapshot_after.project.page(1).state == PageState.PROMPT_BUILT
    assert bus.published == []
    assert ledger.lookup_exact(binding).outcome == "missing"
