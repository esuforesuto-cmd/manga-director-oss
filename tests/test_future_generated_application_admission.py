"""Focused D10-I01 tests for private in-fence Generated admission."""

from __future__ import annotations

import hashlib
import inspect
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest
from generation_admission_v1_fixtures import manifest

import manga_director
import manga_director.production as production
from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState, StateMachine
from manga_director.events import MemoryEventBus
from manga_director.production import future_fake_provider_receipt_journal as d09
from manga_director.production import future_provider_result_evidence_journal as i02
from manga_director.production import (
    next_generation_local_durable_asset_owner as asset_owner_module,
)
from manga_director.production.future_generated_application_admission import (
    GeneratedApplicationExpectedStateV1,
    LocalFileGeneratedApplicationPreApplyGuard,
    prepare_expected_state,
)
from manga_director.production.future_generation_admission_contract import SnapshotIdentityV1
from manga_director.production.next_generation_durable_application_commit_receipt import (
    DurableApplicationCommitReceiptService,
    LocalDurableApplicationCommitReceiptStore,
)
from manga_director.production.next_generation_durable_evidence_workflow_binding import (
    DurableEvidenceWorkflowBindingReport,
    WorkflowApplicationAuthorizationDTO,
)
from manga_director.production.next_generation_local_durable_asset_owner import (
    LocalDurableAssetOwner,
    OwnerRegistrationMaterial,
)
from manga_director.production.next_generation_workflow_application_ledger import (
    LocalWorkflowApplicationLedgerStore,
    WorkflowApplicationLedgerService,
)
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.workflow.durable_execution import LocalFileDurablePageStore
from manga_director.workflow.localfile_external_generated_application import (
    LocalFileExternalGeneratedApplicationCoordinator,
    _ExternalApplicationFenceContext,
)

_PNG = b"\x89PNG\r\n\x1a\nD10-private-owner-bytes"


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()


def _profile() -> dict[str, object]:
    capabilities = (
        "submission",
        "provider_request_identity",
        "client_idempotency_identity",
        "duplicate_submit_semantics",
        "status_reconciliation",
        "result_lookup",
        "cancellation",
        "restart_safe_retention",
    )
    evidence = [
        {
            "capability": capability,
            "asserted_state": "SUPPORTED",
            "provenance_state": "CURRENT",
            "source_reference": f"test:source:{capability}",
            "claim_identifier": f"test:claim:{capability}",
            "source_digest": _digest(capability),
            "provider_revision": "provider:1",
            "source_revision": "source:1",
            "review_revision": "review:1",
        }
        for capability in capabilities
    ]
    return {
        "schema_name": "manga_director.future_provider_capability_profile",
        "schema_version": "1",
        "provider_reference": "fake:deterministic",
        "provider_revision": "provider:1",
        "adapter_version": "fixture:1",
        "review_revision": "review:1",
        "profile_revision": 1,
        "duplicate_submit_semantics": "IDEMPOTENT_SAME_OPERATION",
        "reviewed_source_applicability": [
            {
                "source_reference": item["source_reference"],
                "source_revision": item["source_revision"],
                "provider_reference": "fake:deterministic",
                "provider_revision": "provider:1",
                "review_revision": "review:1",
            }
            for item in evidence
        ],
        "evidence": evidence,
    }


class _Fence:
    def __init__(self) -> None:
        self.held = False

    def acquire(self) -> None:
        assert self.held is False
        self.held = True

    def release(self) -> None:
        self.held = False


class _RecordingStateMachine(StateMachine):
    def __init__(self, order: list[str]) -> None:
        super().__init__()
        self._order = order

    def validate_transition(self, from_state: PageState, to_state: PageState) -> None:
        self._order.append("state-machine")
        super().validate_transition(from_state, to_state)


class _RecordingStore(LocalFileDurablePageStore):
    def __init__(self, repository: LocalFileRepository, order: list[str]) -> None:
        super().__init__(repository)
        self._order = order

    def conditional_commit(self, snapshot: object, project: Project):  # type: ignore[override]
        self._order.append("cas")
        return super().conditional_commit(snapshot, project)  # type: ignore[arg-type]


class _MutationAttemptingStore(_RecordingStore):
    """Attempt a Windows write exactly during the guarded CAS interval."""

    def __init__(self, repository: LocalFileRepository, asset_path: Path) -> None:
        super().__init__(repository, [])
        self._asset_path = asset_path
        self.write_blocked = False
        self.delete_blocked = False

    def conditional_commit(self, snapshot: object, project: Project):  # type: ignore[override]
        try:
            self._asset_path.write_bytes(b"replacement")
        except OSError:
            self.write_blocked = True
        try:
            self._asset_path.unlink()
        except OSError:
            self.delete_blocked = True
        return super().conditional_commit(snapshot, project)


class _RecordingGuard:
    def __init__(self, delegate: LocalFileGeneratedApplicationPreApplyGuard, fence: _Fence, order: list[str]) -> None:
        self._delegate = delegate
        self._fence = fence
        self._order = order

    def validate(self, binding: object, snapshot: object, context: object, fence_context: object):
        assert self._fence.held is True
        self._order.append("guard")
        return self._delegate.validate(binding, snapshot, context, fence_context)  # type: ignore[arg-type]


class _RaisingEventBus(MemoryEventBus):
    def publish(self, events: list[object]) -> None:
        del events
        raise RuntimeError("test-only post-commit interruption")


def _expected_with(
    expected: GeneratedApplicationExpectedStateV1, **updates: object
) -> GeneratedApplicationExpectedStateV1:
    values = expected.model_dump()
    values.update(updates)
    values["package_digest"] = _digest(
        {key: value for key, value in values.items() if key != "package_digest"}
    )
    return GeneratedApplicationExpectedStateV1.model_validate(values)


def _environment(tmp_path: Path):
    admitted = manifest().model_copy(
        update={"project_id": "project-d10", "attempt_id": "attempt:d10"}
    )
    repository = LocalFileRepository(tmp_path / "repository")
    repository.save(
        Project(
            id=admitted.project_id,
            title="D10",
            pages=[
                Page(
                    page_number=1,
                    state=PageState.PROMPT_BUILT,
                    page_design={},
                    review={},
                    storyboard=admitted.storyboard.model_dump(mode="json"),
                    prompt=admitted.prompt.model_dump(mode="json"),
                    metadata={
                        "future_generation_target_reference": admitted.execution_target_reference,
                        "future_generation_provider_binding": admitted.provider_request.model_dump(mode="json"),
                    },
                )
            ],
        )
    )
    snapshot = repository._load_revisioned(admitted.project_id)
    bound = admitted.model_copy(
        update={
            "page_id": "1",
            "snapshot": SnapshotIdentityV1(
                revision=snapshot.revision, fingerprint=snapshot.fingerprint
            ),
        }
    )
    journal = d09._LocalFileFakeProviderReceiptJournal(repository)
    assert journal._d05.reserve(bound).code == "RESERVATION_RESERVED"
    permit = journal._d05.prepare_provider_start(bound).permit
    assert permit is not None
    assert journal.submit(manifest=bound, permit=permit, raw_provider_profile=_profile()).status == "ACCEPTED"

    asset_owner = LocalDurableAssetOwner(
        repository._next_generation_normal_execution_owner_root() / "d10-assets"
    )
    registered = asset_owner.register(
        OwnerRegistrationMaterial(
            attempt_id=bound.attempt_id,
            provider_reference="fake:deterministic",
            image_bytes=_PNG,
        )
    )
    assert registered.output is not None
    output_asset_id = registered.output.output_asset_id
    result_journal = i02._LocalFileProviderResultEvidenceJournal(repository)
    capture = result_journal.capture(
        attempt_id=bound.attempt_id,
        observation={
            "provider_job_identity": None,
            "outputs": [
                {
                    "logical_output_id": "output:d10",
                    "sha256": hashlib.sha256(_PNG).hexdigest(),
                    "media_type": "image/png",
                    "metadata": {"kind": "fake"},
                }
            ],
            "capture_metadata": {"fixture": "d10"},
        },
    )
    assert capture.status == "RESULT_CAPTURED"
    expected = prepare_expected_state(
        repository,
        asset_owner,
        attempt_id=bound.attempt_id,
        logical_output_identity="output:d10",
        expected_asset_identity=output_asset_id,
    )
    authorization = WorkflowApplicationAuthorizationDTO(
        authorization_id="authorization:d10",
        authorizer_id="human:test:d10",
        authorized_at=datetime.now(UTC),
        attempt_id=bound.attempt_id,
        provider_reference="fake:deterministic",
        project_id=bound.project_id,
        page_id="1",
        target_page_reference=bound.execution_target_reference,
        source_state="PromptBuilt",
        target_state="Generated",
    )
    report = DurableEvidenceWorkflowBindingReport(
        attempt_id=bound.attempt_id,
        provider_reference="fake:deterministic",
        output_asset_id=output_asset_id,
        project_id=bound.project_id,
        page_id="1",
        target_page_reference=bound.execution_target_reference,
        status="eligible",
        eligible=True,
    )
    return repository, asset_owner, expected, report, authorization, result_journal


def _coordinator(
    repository: LocalFileRepository,
    guard: object | None = None,
    order: list[str] | None = None,
):
    order = order if order is not None else []
    fence = _Fence()
    root = repository._workflow_application_ledger_owner_root()
    return (
        LocalFileExternalGeneratedApplicationCoordinator(
            _RecordingStateMachine(order),
            MemoryEventBus(),
            WorkflowApplicationLedgerService(),
            LocalWorkflowApplicationLedgerStore(root),
            DurableApplicationCommitReceiptService(),
            LocalDurableApplicationCommitReceiptStore(root),
            _RecordingStore(repository, order),
            fence_factory=lambda project_id, page_id: fence,
            pre_apply_guard=guard,  # type: ignore[arg-type]
        ),
        fence,
        order,
    )


def test_valid_expected_state_allows_only_inside_fence_before_state_machine_and_cas(tmp_path: Path) -> None:
    repository, owner, expected, report, authorization, _ = _environment(tmp_path)
    order: list[str] = []
    coordinator, fence, _ = _coordinator(repository, order=order)
    guard = _RecordingGuard(LocalFileGeneratedApplicationPreApplyGuard(repository, owner, expected), fence, order)
    coordinator._pre_apply_guard = guard  # private trusted composition seam

    result = coordinator.apply(report, authorization)

    assert result.status == "application_applied_event_published"
    assert order == ["guard", "state-machine", "cas"]
    assert repository._load_revisioned("project-d10").project.page(1).state == PageState.GENERATED


@pytest.mark.parametrize(
    "field,value",
    [
        ("expected_revision", 999),
        ("expected_fingerprint", "b" * 64),
        ("page_id", "2"),
        ("target_page_reference", "target:other"),
        ("attempt_id", "attempt:other"),
        ("manifest_digest", "b" * 64),
        ("dispatch_identity", "b" * 64),
        ("idempotency_identity", "b" * 64),
        ("attempt_binding_digest", "b" * 64),
        ("provider_binding_digest", "b" * 64),
        ("profile_identity", "b" * 64),
        ("provider_class", "C"),
        ("receipt_identity", "b" * 64),
        ("receipt_digest", "b" * 64),
        ("receipt_sequence", 99),
        ("evidence_identity", "b" * 64),
        ("evidence_digest", "b" * 64),
        ("expected_asset_sha256", "b" * 64),
        ("expected_asset_file_index", 999),
    ],
)
def test_stale_or_cross_binding_expected_state_is_rejected(
    tmp_path: Path, field: str, value: object
) -> None:
    repository, owner, expected, report, authorization, _ = _environment(tmp_path)
    coordinator, _, _ = _coordinator(
        repository, LocalFileGeneratedApplicationPreApplyGuard(repository, owner, _expected_with(expected, **{field: value}))
    )

    result = coordinator.apply(report, authorization)

    assert result.status == "application_not_applied"
    assert repository._load_revisioned("project-d10").project.page(1).state == PageState.PROMPT_BUILT


@pytest.mark.parametrize("field", ["storyboard", "prompt"])
def test_changed_persisted_storyboard_or_prompt_is_rejected(tmp_path: Path, field: str) -> None:
    repository, owner, expected, report, authorization, _ = _environment(tmp_path)
    snapshot = repository._load_revisioned("project-d10")
    page = snapshot.project.page(1)
    replacement = page.model_copy(update={field: {"changed": field}})
    repository._conditional_commit(snapshot, snapshot.project.replace_page(replacement))
    coordinator, _, _ = _coordinator(repository, LocalFileGeneratedApplicationPreApplyGuard(repository, owner, expected))

    assert coordinator.apply(report, authorization).status == "application_not_applied"


def test_changed_owned_asset_hash_is_rejected_before_generated_application(tmp_path: Path) -> None:
    repository, owner, expected, report, authorization, _ = _environment(tmp_path)
    with sqlite3.connect(owner._registry_path) as connection:
        storage_name = connection.execute("SELECT storage_name FROM asset_registry").fetchone()[0]
    (owner._assets_directory / storage_name).write_bytes(_PNG + b"changed")
    coordinator, _, _ = _coordinator(repository, LocalFileGeneratedApplicationPreApplyGuard(repository, owner, expected))

    assert coordinator.apply(report, authorization).status == "application_not_applied"
    assert repository._load_revisioned("project-d10").project.page(1).state == PageState.PROMPT_BUILT


def test_missing_owned_asset_is_rejected_before_generated_application(tmp_path: Path) -> None:
    repository, owner, expected, report, authorization, _ = _environment(tmp_path)
    with sqlite3.connect(owner._registry_path) as connection:
        storage_name = connection.execute("SELECT storage_name FROM asset_registry").fetchone()[0]
    (owner._assets_directory / storage_name).unlink()
    coordinator, _, _ = _coordinator(repository, LocalFileGeneratedApplicationPreApplyGuard(repository, owner, expected))

    assert coordinator.apply(report, authorization).status == "application_not_applied"


def test_d09_i01_corruption_is_rejected(tmp_path: Path) -> None:
    repository, owner, expected, report, authorization, journal = _environment(tmp_path)
    with sqlite3.connect(journal._reader._database) as connection:
        connection.execute("UPDATE d09_journals SET lifecycle = 'REJECTED'")
    coordinator, _, _ = _coordinator(repository, LocalFileGeneratedApplicationPreApplyGuard(repository, owner, expected))

    assert coordinator.apply(report, authorization).status == "application_not_applied"


def test_d09_i02_corruption_is_rejected(tmp_path: Path) -> None:
    repository, owner, expected, report, authorization, journal = _environment(tmp_path)
    with sqlite3.connect(journal._journal._database) as connection:
        connection.execute("UPDATE d09i02_journal_state SET phase = 'PENDING'")
    coordinator, _, _ = _coordinator(repository, LocalFileGeneratedApplicationPreApplyGuard(repository, owner, expected))

    assert coordinator.apply(report, authorization).status == "application_not_applied"


def test_owner_rejects_wrong_media_type(tmp_path: Path) -> None:
    _, owner, expected, _, _, _ = _environment(tmp_path)

    with pytest.raises(ValueError):
        owner._verify_for_generated_application(
            attempt_id=expected.attempt_id,
            provider_reference="fake:deterministic",
            output_asset_id=expected.expected_asset_identity,
            expected_sha256=expected.expected_asset_sha256,
            expected_media_type="image/jpeg",
        )


def test_windows_asset_lease_blocks_mutation_between_rehash_and_cas(tmp_path: Path) -> None:
    repository, owner, expected, report, authorization, _ = _environment(tmp_path)
    with sqlite3.connect(owner._registry_path) as connection:
        storage_name = connection.execute("SELECT storage_name FROM asset_registry").fetchone()[0]
    store = _MutationAttemptingStore(repository, owner._assets_directory / storage_name)
    root = repository._workflow_application_ledger_owner_root()
    coordinator = LocalFileExternalGeneratedApplicationCoordinator(
        StateMachine(),
        MemoryEventBus(),
        WorkflowApplicationLedgerService(),
        LocalWorkflowApplicationLedgerStore(root),
        DurableApplicationCommitReceiptService(),
        LocalDurableApplicationCommitReceiptStore(root),
        store,
        fence_factory=lambda project_id, page_id: _Fence(),
        pre_apply_guard=LocalFileGeneratedApplicationPreApplyGuard(repository, owner, expected),
    )

    assert coordinator.apply(report, authorization).status == "application_applied_event_published"
    assert store.write_blocked is True
    assert store.delete_blocked is True
    assert (owner._assets_directory / storage_name).read_bytes() == _PNG


def test_handle_identity_mismatch_or_modeled_reparse_race_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, owner, expected, report, authorization, _ = _environment(tmp_path)
    original = asset_owner_module._windows_handle_identity

    def _outside_handle_identity(kernel32: object, handle: int):
        identity = original(kernel32, handle)
        return asset_owner_module._OpenedAssetIdentity(
            final_path=tmp_path / "outside-owner-root.png",
            volume_serial=identity.volume_serial,
            file_index=identity.file_index,
            size=identity.size,
            attributes=identity.attributes,
        )

    monkeypatch.setattr(asset_owner_module, "_windows_handle_identity", _outside_handle_identity)
    coordinator, _, _ = _coordinator(repository, LocalFileGeneratedApplicationPreApplyGuard(repository, owner, expected))

    assert coordinator.apply(report, authorization).status == "application_not_applied"


def test_reparse_marked_asset_is_rejected_before_handle_hash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, owner, expected, _, _, _ = _environment(tmp_path)
    with sqlite3.connect(owner._registry_path) as connection:
        storage_name = connection.execute("SELECT storage_name FROM asset_registry").fetchone()[0]
    asset_path = owner._assets_directory / storage_name
    original = asset_owner_module._is_link_or_reparse_point
    monkeypatch.setattr(
        asset_owner_module,
        "_is_link_or_reparse_point",
        lambda path: path == asset_path or original(path),
    )

    with pytest.raises(ValueError):
        owner._verify_for_generated_application(
            attempt_id=expected.attempt_id,
            provider_reference="fake:deterministic",
            output_asset_id=expected.expected_asset_identity,
            expected_sha256=expected.expected_asset_sha256,
            expected_media_type="image/png",
        )


def test_owner_root_identity_mismatch_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, owner, expected, _, _, _ = _environment(tmp_path)
    monkeypatch.setattr(asset_owner_module, "_owner_root_identity_matches", lambda root, expected: False)

    with pytest.raises(ValueError):
        owner._verify_for_generated_application(
            attempt_id=expected.attempt_id,
            provider_reference="fake:deterministic",
            output_asset_id=expected.expected_asset_identity,
            expected_sha256=expected.expected_asset_sha256,
            expected_media_type="image/png",
        )


def test_asset_hash_uses_the_verified_handle_without_path_reopen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, owner, expected, _, _, _ = _environment(tmp_path)
    with sqlite3.connect(owner._registry_path) as connection:
        storage_name = connection.execute("SELECT storage_name FROM asset_registry").fetchone()[0]
    asset_path = owner._assets_directory / storage_name
    original_open = Path.open

    def _reject_asset_path_open(path: Path, *args: object, **kwargs: object):
        if path == asset_path:
            raise AssertionError("D10 must not reopen the verified asset path")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", _reject_asset_path_open)
    lease = owner._verify_for_generated_application(
        attempt_id=expected.attempt_id,
        provider_reference="fake:deterministic",
        output_asset_id=expected.expected_asset_identity,
        expected_sha256=expected.expected_asset_sha256,
        expected_media_type="image/png",
    )
    lease.release()


def test_unverified_evidence_never_becomes_authenticated_or_application_authority(tmp_path: Path) -> None:
    repository, owner, expected, report, authorization, _ = _environment(tmp_path)
    values = expected.model_dump()
    values["provider_origin_assurance"] = "AUTHENTICATED"
    values["package_digest"] = _digest(
        {key: value for key, value in values.items() if key != "package_digest"}
    )
    forged = GeneratedApplicationExpectedStateV1.model_construct(**values)
    with pytest.raises(ValueError):
        LocalFileGeneratedApplicationPreApplyGuard(repository, owner, forged)
    coordinator, _, _ = _coordinator(repository, LocalFileGeneratedApplicationPreApplyGuard(repository, owner, expected))

    assert repository._load_revisioned("project-d10").project.page(1).state == PageState.PROMPT_BUILT
    assert coordinator._pre_apply_guard is not None and report.eligible is True and authorization.target_state == "Generated"


def test_allow_is_not_generated_and_existing_replay_prevents_a_second_application(tmp_path: Path) -> None:
    repository, owner, expected, report, authorization, _ = _environment(tmp_path)
    guard = LocalFileGeneratedApplicationPreApplyGuard(repository, owner, expected)
    snapshot = repository._load_revisioned("project-d10")
    context = LocalFileDurablePageStore(repository).context_from_snapshot(snapshot, "1")
    binding = WorkflowApplicationLedgerService().prepare(
        report, authorization, LocalWorkflowApplicationLedgerStore(repository._workflow_application_ledger_owner_root())
    ).binding
    assert binding is not None
    with pytest.raises(TypeError):
        guard.validate(binding, snapshot, context)  # type: ignore[call-arg]
    assert repository._load_revisioned("project-d10").project.page(1).state == PageState.PROMPT_BUILT

    coordinator, _, _ = _coordinator(repository, guard)
    assert coordinator.apply(report, authorization).status == "application_applied_event_published"
    assert coordinator.apply(report, authorization).status == "application_replay_confirmed"


def test_guard_rejects_mismatched_fence_context(tmp_path: Path) -> None:
    repository, owner, expected, report, authorization, _ = _environment(tmp_path)
    guard = LocalFileGeneratedApplicationPreApplyGuard(repository, owner, expected)
    snapshot = repository._load_revisioned("project-d10")
    context = LocalFileDurablePageStore(repository).context_from_snapshot(snapshot, "1")
    binding = WorkflowApplicationLedgerService().prepare(
        report, authorization, LocalWorkflowApplicationLedgerStore(repository._workflow_application_ledger_owner_root())
    ).binding
    assert binding is not None
    mismatched = _ExternalApplicationFenceContext(
        project_id=binding.project_id,
        page_id=binding.page_id,
        target_page_reference=binding.target_page_reference,
        revision=snapshot.revision + 1,
        fingerprint=snapshot.fingerprint,
        _issuer=object(),
        _attempt_token=object(),
    )

    assert guard.validate(binding, snapshot, context, mismatched).allowed is False


def test_post_commit_interruption_reopens_as_existing_replay_without_d10_retry(tmp_path: Path) -> None:
    repository, owner, expected, report, authorization, _ = _environment(tmp_path)
    root = repository._workflow_application_ledger_owner_root()
    coordinator = LocalFileExternalGeneratedApplicationCoordinator(
        StateMachine(),
        _RaisingEventBus(),
        WorkflowApplicationLedgerService(),
        LocalWorkflowApplicationLedgerStore(root),
        DurableApplicationCommitReceiptService(),
        LocalDurableApplicationCommitReceiptStore(root),
        LocalFileDurablePageStore(repository),
        fence_factory=lambda project_id, page_id: _Fence(),
        pre_apply_guard=LocalFileGeneratedApplicationPreApplyGuard(repository, owner, expected),
    )

    assert coordinator.apply(report, authorization).status == "application_applied_event_failed"
    assert repository._load_revisioned("project-d10").project.page(1).state == PageState.GENERATED
    assert coordinator.apply(report, authorization).status == "application_replay_confirmed"


def test_non_d10_coordinator_call_remains_compatible_and_d10_is_not_public(tmp_path: Path) -> None:
    repository, _, _, report, authorization, _ = _environment(tmp_path)
    coordinator, _, _ = _coordinator(repository)

    assert coordinator.apply(report, authorization).status == "application_applied_event_published"
    assert tuple(inspect.signature(LocalFileExternalGeneratedApplicationCoordinator.apply).parameters) == (
        "self",
        "binding_report",
        "authorization",
    )
    assert "future_generated_application_admission" not in inspect.getsource(manga_director)
    assert "GeneratedApplicationExpectedStateV1" not in inspect.getsource(production)


def test_asset_owner_rejects_caller_path_and_reparse_style_asset_identity(tmp_path: Path) -> None:
    repository, owner, expected, _, _, _ = _environment(tmp_path)
    del repository
    with pytest.raises(ValueError):
        owner._verify_for_generated_application(
            attempt_id=expected.attempt_id,
            provider_reference="fake:deterministic",
            output_asset_id="../asset",
            expected_sha256=expected.expected_asset_sha256,
            expected_media_type="image/png",
        )
