"""Focused fake-only tests for private LocalFile Manual Reconciliation."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock

import manga_director.production.next_generation_workflow_application_ledger as ledger_module
from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState, StateMachine
from manga_director.events import MemoryEventBus
from manga_director.production.next_generation_durable_application_commit_receipt import (
    DurableApplicationCommitReceiptService,
    LocalDurableApplicationCommitReceiptStore,
)
from manga_director.production.next_generation_durable_evidence_workflow_binding import (
    DurableEvidenceWorkflowBindingReport,
    WorkflowApplicationAuthorizationDTO,
)
from manga_director.production.next_generation_workflow_application_ledger import (
    LocalWorkflowApplicationLedgerStore,
    WorkflowApplicationLedgerService,
    _authoritative_commit_proof,
)
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.workflow.contracts import WorkflowContext
from manga_director.workflow.localfile_external_generated_application import (
    LocalFileExternalGeneratedApplicationCoordinator,
    LocalFileLogicalOutputAssetQualityGate,
)
from manga_director.workflow.localfile_manual_reconciliation import (
    LocalFileManualReconciliationComposition,
    ManualReconciliationInputDTO,
    build_localfile_manual_reconciliation_composition,
)

_ATTEMPT = "attempt:manual-reconciliation:001"
_AUTHORIZATION = "authorization:manual-reconciliation:001"
_PROJECT = "project-manual-reconciliation-001"
_PAGE = "1"
_TARGET = "page:manual-reconciliation:001"
_PROVIDER = "provider:manual-reconciliation:001"
_OUTPUT = "asset:manual-reconciliation:001"


class _TestManualReconciliationProof:
    __slots__ = ("_binding", "_seal")

    def __init__(self, binding: object, seal: object) -> None:
        self._binding = binding
        self._seal = seal

    def matches(self, binding: object, seal: object) -> bool:
        return self._binding == binding and self._seal is seal


class _TestManualReconciliationAuthority:
    def __init__(self) -> None:
        self._seal = object()

    def mint(self, binding: object) -> object:
        return _TestManualReconciliationProof(binding, self._seal)

    def validates(self, proof: object, binding: object) -> bool:
        return isinstance(proof, _TestManualReconciliationProof) and proof.matches(
            binding, self._seal
        )


def _report(**updates: object) -> DurableEvidenceWorkflowBindingReport:
    values: dict[str, object] = {
        "attempt_id": _ATTEMPT,
        "provider_reference": _PROVIDER,
        "output_asset_id": _OUTPUT,
        "project_id": _PROJECT,
        "page_id": _PAGE,
        "target_page_reference": _TARGET,
        "status": "eligible",
        "eligible": True,
    }
    values.update(updates)
    return DurableEvidenceWorkflowBindingReport.model_validate(values)


def _authorization(**updates: object) -> WorkflowApplicationAuthorizationDTO:
    values: dict[str, object] = {
        "authorization_id": _AUTHORIZATION,
        "authorizer_id": "human:manual-reconciliation:001",
        "authorized_at": datetime(2026, 8, 23, tzinfo=UTC),
        "attempt_id": _ATTEMPT,
        "provider_reference": _PROVIDER,
        "project_id": _PROJECT,
        "page_id": _PAGE,
        "target_page_reference": _TARGET,
        "source_state": "PromptBuilt",
        "target_state": "Generated",
    }
    values.update(updates)
    return WorkflowApplicationAuthorizationDTO.model_validate(values)


def _input(**updates: object) -> ManualReconciliationInputDTO:
    values: dict[str, object] = {"binding_report": _report(), "authorization": _authorization()}
    values.update(updates)
    return ManualReconciliationInputDTO.model_validate(values)


def _recursive_closure_callable_names(value: object, seen: set[int] | None = None) -> set[str]:
    """Model the historical ordinary-introspection route without invoking internals."""

    visited = seen if seen is not None else set()
    function = getattr(value, "__func__", value)
    if not callable(function) or id(function) in visited:
        return set()
    visited.add(id(function))
    closure = getattr(function, "__closure__", None)
    if closure is None:
        return set()
    names: set[str] = set()
    for cell in closure:
        try:
            captured = cell.cell_contents
        except ValueError:
            continue
        if callable(captured):
            names.add(getattr(captured, "__name__", type(captured).__name__))
            names.update(_recursive_closure_callable_names(captured, visited))
    return names


@dataclass(frozen=True)
class _Snapshot:
    revision: int
    fingerprint: str


class _PageStore:
    def __init__(self, context: WorkflowContext, *, revision: int = 7, fingerprint: str = "a" * 64) -> None:
        self.context = context
        self.revision = revision
        self.fingerprint = fingerprint
        self.load_calls = 0
        self.project_mutations = 0
        self.cas_calls = 0

    def load_revisioned(self, project_id: str) -> _Snapshot:
        assert project_id == _PROJECT
        self.load_calls += 1
        return _Snapshot(self.revision, self.fingerprint)

    def context_from_snapshot(self, snapshot: _Snapshot, page_id: str) -> WorkflowContext:
        del snapshot
        assert page_id == _PAGE
        return self.context

    def project_from_context(self, snapshot: object, page_id: str, context: WorkflowContext) -> object:
        del snapshot, page_id, context
        self.project_mutations += 1
        raise AssertionError("reconciliation must not build a Project mutation")

    def conditional_commit(self, snapshot: object, project: object) -> object:
        del snapshot, project
        self.cas_calls += 1
        raise AssertionError("reconciliation must not perform a Project CAS")

    def verify_committed(self, project_id: str, page_id: str, expected_project: object) -> bool:
        del project_id, page_id, expected_project
        raise AssertionError("reconciliation must not verify a new Project commit")


class _SharedFence:
    def __init__(self, lock: Lock) -> None:
        self._lock = lock

    def acquire(self) -> None:
        self._lock.acquire()

    def release(self) -> None:
        self._lock.release()


def _generated_context(
    *, state: PageState = PageState.GENERATED, artifact: object | None = None
) -> WorkflowContext:
    return WorkflowContext(
        page={"project_id": _PROJECT, "page_id": _PAGE},
        state=state,
        artifacts={
            "Generated": artifact
            if artifact is not None
            else {"artifact_kind": "logical_output_asset", "output_asset_id": _OUTPUT}
        },
    )


def _seed(
    tmp_path: Path,
    *,
    ledger_service: WorkflowApplicationLedgerService | None = None,
    reconciliation_proof_minter: Callable[[object], object] | None = None,
    receipt: bool = True,
    applied: bool = False,
    context: WorkflowContext | None = None,
    page_revision: int | None = None,
    page_fingerprint: str | None = None,
) -> tuple[
    object,
    WorkflowApplicationLedgerService,
    LocalWorkflowApplicationLedgerStore,
    LocalDurableApplicationCommitReceiptStore,
    _PageStore,
]:
    del ledger_service, reconciliation_proof_minter
    workflow_context = context or _generated_context()
    image = workflow_context.artifacts[PageState.GENERATED.value]
    repository = LocalFileRepository(tmp_path)
    repository.save(
        Project(
            id=_PROJECT,
            title="Manual reconciliation",
            pages=[
                Page(
                    page_number=1,
                    state=workflow_context.state,
                    page_design={},
                    review={},
                    storyboard={},
                    prompt={},
                    image=image,
                    quality={} if workflow_context.state == PageState.QUALITY_CHECKED else None,
                )
            ],
        )
    )
    snapshot = repository._load_revisioned(_PROJECT)
    owner_root = repository._workflow_application_ledger_owner_root()
    ledger_service = WorkflowApplicationLedgerService()
    ledger_store = LocalWorkflowApplicationLedgerStore(owner_root)
    receipt_service = DurableApplicationCommitReceiptService()
    receipt_store = LocalDurableApplicationCommitReceiptStore(owner_root)
    prepared = ledger_service.prepare(_report(), _authorization(), ledger_store)
    assert prepared.binding is not None
    if receipt:
        assert receipt_service.commit(
            prepared.binding,
            _authoritative_commit_proof(prepared.binding),
            post_commit_revision=page_revision if page_revision is not None else snapshot.revision,
            post_commit_fingerprint=page_fingerprint or snapshot.fingerprint,
            receipt_store=receipt_store,
        ).committed
    if applied:
        assert ledger_service.finalize(
            prepared.binding, _authoritative_commit_proof(prepared.binding), ledger_store
        ).applied
    page_store = _PageStore(workflow_context, revision=snapshot.revision, fingerprint=snapshot.fingerprint)
    composition = build_localfile_manual_reconciliation_composition(repository)
    return composition.coordinator, ledger_service, ledger_store, receipt_store, page_store


def test_valid_reconciliation_is_ledger_only_and_exactly_idempotent(tmp_path: Path) -> None:
    coordinator, service, ledger, _, page_store = _seed(tmp_path)

    applied = coordinator.reconcile(_input())
    confirmed = coordinator.reconcile(_input())

    assert applied.status == "reconciled" and applied.reconciled is True
    assert confirmed.status == "confirmed" and confirmed.confirmed is True
    assert service.lookup_exact(
        service.prepare(_report(), _authorization(), ledger).binding, ledger
    ).outcome == "applied"
    assert page_store.project_mutations == 0 and page_store.cas_calls == 0


def test_missing_receipt_and_stale_project_cannot_reconcile(tmp_path: Path) -> None:
    missing, service, ledger, _, page_store = _seed(tmp_path / "missing", receipt=False)
    stale, _, _, _, stale_page = _seed(tmp_path / "stale", page_revision=8)

    missing_result = missing.reconcile(_input())
    stale_result = stale.reconcile(_input())

    assert missing_result.findings[0].code == "MANUAL_RECONCILIATION_RECEIPT_MISSING"
    assert stale_result.findings[0].code == "MANUAL_RECONCILIATION_RECEIPT_CONFLICT"
    assert service.lookup_exact(service.prepare(_report(), _authorization(), ledger).binding, ledger).outcome == "prepared"
    assert page_store.cas_calls == stale_page.cas_calls == 0


def test_corrupt_or_conflicting_receipt_fails_closed(tmp_path: Path) -> None:
    corrupt, _, _, store, _ = _seed(tmp_path / "corrupt")
    database = store._database_path
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE durable_application_commit_receipts SET receipt_digest = 'tampered'")
    corrupt_result = corrupt.reconcile(_input())

    conflicting, _, _, _, _ = _seed(
        tmp_path / "conflict",
        context=_generated_context(
            artifact={"artifact_kind": "logical_output_asset", "output_asset_id": "asset:other"}
        ),
    )
    conflict_result = conflicting.reconcile(_input(binding_report=_report(output_asset_id="asset:other")))

    assert corrupt_result.findings[0].code == "MANUAL_RECONCILIATION_RECEIPT_CORRUPT"
    assert conflict_result.findings[0].code == "MANUAL_RECONCILIATION_RECEIPT_CONFLICT"
    assert store is not None


def test_invalid_authorization_binding_state_and_legacy_artifact_fail_closed(tmp_path: Path) -> None:
    authorization_mismatch, _, _, _, _ = _seed(tmp_path / "authorization")
    prompt_built, _, _, _, _ = _seed(
        tmp_path / "prompt", context=_generated_context(state=PageState.PROMPT_BUILT)
    )
    legacy, _, _, _, _ = _seed(
        tmp_path / "legacy", context=_generated_context(artifact={"image_path": "legacy.png"})
    )
    quality_checked, _, _, _, _ = _seed(
        tmp_path / "quality", context=_generated_context(state=PageState.QUALITY_CHECKED)
    )

    assert authorization_mismatch.reconcile(
        _input(authorization=_authorization(provider_reference="provider:other"))
    ).status == "blocked"
    assert prompt_built.reconcile(_input()).status == "blocked"
    assert legacy.reconcile(_input()).status == "blocked"
    assert quality_checked.reconcile(_input()).status == "blocked"


def test_binding_and_arbitrary_objects_cannot_finalize_reconciliation(tmp_path: Path) -> None:
    _, service, ledger, _, _ = _seed(tmp_path)
    prepared = service.prepare(_report(), _authorization(), ledger)
    assert prepared.binding is not None

    normal = service.finalize(prepared.binding, object(), ledger)
    direct_store = ledger.finalize(prepared.binding, object())  # type: ignore[arg-type]

    assert normal.status == "blocked"
    assert normal.findings[0].code == "AUTHORITATIVE_COMMIT_PROOF_INVALID"
    assert direct_store.outcome == "failed"
    assert not hasattr(service, "reconcile_finalize")
    assert not hasattr(service, "_begin_reconciliation_scope")
    source = (
        Path(__file__).resolve().parents[1]
        / "src/manga_director/production/next_generation_workflow_application_ledger.py"
    ).read_text(encoding="utf-8")
    assert "reconciliation_proof_validator" not in source
    assert "_WorkflowApplicationLedgerStoreFinalizeCapability" not in source
    assert not hasattr(ledger_module, "_WorkflowApplicationLedgerStoreFinalizeCapability")
    assert not hasattr(ledger_module, "_STORE_FINALIZE_SEAL")
    assert not hasattr(ledger, "_connect")
    assert not hasattr(ledger, "_update_lifecycle")


def test_bare_service_and_composition_cannot_issue_reconciliation_authority(tmp_path: Path) -> None:
    bare_service = WorkflowApplicationLedgerService()
    ledger = LocalWorkflowApplicationLedgerStore(tmp_path / "ledger")
    prepared = bare_service.prepare(_report(), _authorization(), ledger)
    assert prepared.binding is not None

    try:
        WorkflowApplicationLedgerService(reconciliation_proof_validator=lambda *_: True)  # type: ignore[call-arg]
    except TypeError:
        pass
    else:
        raise AssertionError("caller-injected reconciliation validator remained available")
    assert not hasattr(bare_service, "reconcile_finalize")
    assert not hasattr(bare_service, "_begin_reconciliation_scope")
    assert tuple(LocalFileManualReconciliationComposition.__dataclass_fields__) == ("coordinator",)


def test_composition_reachability_cannot_bypass_validated_reconciliation(tmp_path: Path) -> None:
    coordinator, service, ledger, _, _ = _seed(tmp_path)
    prepared = service.prepare(_report(), _authorization(), ledger)
    assert prepared.binding is not None

    assert not hasattr(coordinator, "__dict__")
    for name in (
        "_ledger_service",
        "_ledger_store",
        "_receipt_store",
        "_reconciliation_proof_minter",
        "reconcile_finalize",
        "finalize",
    ):
        assert not hasattr(coordinator, name)
    assert service.finalize(prepared.binding, object(), ledger).status == "blocked"
    assert ledger.finalize(prepared.binding, object()).outcome == "failed"  # type: ignore[arg-type]
    assert service.lookup_exact(prepared.binding, ledger).outcome == "prepared"


def test_historical_recursive_closure_exploit_requires_full_reconciliation_validation(
    tmp_path: Path,
) -> None:
    coordinator, service, ledger, _, _ = _seed(tmp_path, receipt=False)
    prepared = service.prepare(_report(), _authorization(), ledger)
    assert prepared.binding is not None

    method = coordinator.reconcile
    function = method.__func__
    assert function.__closure__ is None
    assert _recursive_closure_callable_names(method) == set()

    # The previously exploitable route started here.  Calling the recovered
    # method still executes the complete owner operation and cannot apply the
    # prepared row when its authoritative Receipt is absent.
    result = function(coordinator, _input())

    assert result.status == "blocked"
    assert result.findings[0].code == "MANUAL_RECONCILIATION_RECEIPT_MISSING"
    assert service.lookup_exact(prepared.binding, ledger).outcome == "prepared"


def test_cross_binding_and_authority_shaped_inputs_cannot_apply_prepared_row(tmp_path: Path) -> None:
    changes = {
        "project_id": "project-manual-reconciliation-other",
        "page_id": "2",
        "attempt_id": "attempt:manual-reconciliation:other",
        "authorization_id": "authorization:manual-reconciliation:other",
        "target_page_reference": "page:manual-reconciliation:other",
        "provider_reference": "provider:manual-reconciliation:other",
        "output_asset_id": "asset:manual-reconciliation:other",
    }
    for field, replacement in changes.items():
        coordinator, service, ledger, _, _ = _seed(tmp_path / field)
        prepared = service.prepare(_report(), _authorization(), ledger)
        assert prepared.binding is not None
        report_updates = {field: replacement} if field != "authorization_id" else {}
        authorization_updates = {
            field: replacement
        } if field != "output_asset_id" else {}
        result = coordinator.reconcile(
            _input(
                binding_report=_report(**report_updates),
                authorization=_authorization(**authorization_updates),
            )
        )

        assert result.status == "blocked"
        assert service.lookup_exact(prepared.binding, ledger).outcome == "prepared"

    _, service, ledger, receipt, _ = _seed(tmp_path / "authority")
    prepared = service.prepare(_report(), _authorization(), ledger)
    assert prepared.binding is not None
    shaped_values = (
        object(),
        _TestManualReconciliationProof(prepared.binding, object()),
        {"proof": "applied", "capability": "copied", "scope": "all"},
        receipt,
    )
    for value in shaped_values:
        assert service.finalize(prepared.binding, value, ledger).status == "blocked"
        assert ledger.finalize(prepared.binding, value).outcome == "failed"  # type: ignore[arg-type]
    assert service.lookup_exact(prepared.binding, ledger).outcome == "prepared"


def test_validated_capability_cannot_finalize_another_binding(tmp_path: Path) -> None:
    coordinator, service, ledger, _, _ = _seed(tmp_path)
    prepared = service.prepare(_report(), _authorization(), ledger)
    assert prepared.binding is not None
    other = prepared.binding.model_copy(
        update={
            "attempt_id": "attempt:manual-reconciliation:002",
            "authorization_id": "authorization:manual-reconciliation:002",
        }
    )
    assert ledger.prepare(other).outcome == "prepared"

    assert coordinator.reconcile(_input()).status == "reconciled"
    rejected = service.finalize(other, object(), ledger)

    assert rejected.status == "blocked"
    assert rejected.findings[0].code == "AUTHORITATIVE_COMMIT_PROOF_INVALID"
    assert service.lookup_exact(other, ledger).outcome == "prepared"


def test_quality_is_blocked_before_and_eligible_after_reconciliation(tmp_path: Path) -> None:
    coordinator, service, ledger, _, page_store = _seed(tmp_path)
    gate = LocalFileLogicalOutputAssetQualityGate(service, ledger)

    before = gate.require_applied(page_store.context)
    assert coordinator.reconcile(_input()).status == "reconciled"
    after = gate.require_applied(page_store.context)

    assert before == "LOGICAL_OUTPUT_ASSET_QUALITY_PROOF_UNAVAILABLE"
    assert after is None


def test_concurrent_exact_requests_are_one_apply_and_one_confirmation(tmp_path: Path) -> None:
    coordinator, _, _, _, page_store = _seed(tmp_path)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(executor.map(lambda _: coordinator.reconcile(_input()), range(2)))

    assert {result.status for result in results} == {"reconciled", "confirmed"}
    assert page_store.cas_calls == 0


def test_normal_external_application_sees_reconciled_result_as_replay(tmp_path: Path) -> None:
    coordinator, service, ledger, receipt_store, page_store = _seed(tmp_path)
    assert coordinator.reconcile(_input()).status == "reconciled"
    external = LocalFileExternalGeneratedApplicationCoordinator(
        StateMachine(),
        MemoryEventBus(),
        service,
        ledger,
        DurableApplicationCommitReceiptService(),
        receipt_store,
        page_store,  # type: ignore[arg-type]
        fence_factory=lambda project_id, page_id: _SharedFence(Lock()),
    )

    replay = external.apply(_report(), _authorization())

    assert replay.status == "application_replay_confirmed"
    assert page_store.cas_calls == 0


def test_workflow_recovery_remains_excluded() -> None:
    root = Path(__file__).resolve().parents[1] / "src/manga_director"
    recovery = (root / "workflow/recovery.py").read_text(encoding="utf-8")
    bridge = (root / "workflow/localfile_recovery_external_application.py").read_text(encoding="utf-8")

    assert "ManualReconciliation" not in recovery
    assert "ManualReconciliation" not in bridge
