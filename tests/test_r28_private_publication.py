from __future__ import annotations

import copy
import hashlib
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState, StateMachine
from manga_director.events import MemoryEventBus
from manga_director.production.next_generation_durable_evidence_workflow_binding import (
    DurableEvidenceWorkflowBindingReport,
    WorkflowApplicationAuthorizationDTO,
)
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.repositories.local_file_durability import (
    LocalFileDurabilityError,
    StaleRevisionError,
    _canonical_json_bytes,
    _r27_committed_dict,
    _r27_lineage,
    _r27_prepared_dict,
    _R27CommittedRecord,
    _R27PreparedRecord,
    _R27RevisionPublicationRequest,
    _read_revision_metadata,
    _RevisionRecord,
)
from manga_director.workflow.durable_execution import (
    LocalFileDurablePageStore,
    _R27PublicationIntent,
)
from manga_director.workflow.localfile_external_generated_application import (
    _build_localfile_r27_publication_test_composition,
    _R27PublicationIntentFactory,
    build_localfile_external_generation_composition,
)


def _project(title: str = "R28") -> Project:
    return Project(id="r28-demo", title=title, pages=[Page(page_number=1)])


def _prompt_built_project() -> Project:
    return Project(
        id="r28-demo",
        title="R28",
        pages=[
            Page(
                page_number=1,
                state=PageState.PROMPT_BUILT,
                page_design={},
                review={},
                storyboard={},
                prompt={"prompt_markdown": "private prompt"},
            )
        ],
    )


def _binding_report(
    *, page_id: str = "1", attempt_id: str = "attempt-001", output_asset_id: str = "asset-001"
) -> DurableEvidenceWorkflowBindingReport:
    return DurableEvidenceWorkflowBindingReport.model_validate(
        {
            "attempt_id": attempt_id,
            "provider_reference": "provider-001",
            "output_asset_id": output_asset_id,
            "project_id": "r28-demo",
            "page_id": page_id,
            "target_page_reference": f"page:{page_id}",
            "status": "eligible",
            "eligible": True,
        }
    )


def _authorization(
    *, page_id: str = "1", attempt_id: str = "attempt-001"
) -> WorkflowApplicationAuthorizationDTO:
    return WorkflowApplicationAuthorizationDTO.model_validate(
        {
            "authorization_id": f"authorization-{attempt_id}",
            "authorizer_id": "human-001",
            "authorized_at": datetime(2026, 9, 1, tzinfo=UTC),
            "attempt_id": attempt_id,
            "provider_reference": "provider-001",
            "project_id": "r28-demo",
            "page_id": page_id,
            "target_page_reference": f"page:{page_id}",
            "source_state": "PromptBuilt",
            "target_state": "Generated",
        }
    )


def _request(
    repository: LocalFileRepository,
    *,
    fingerprint: str,
    revision: int,
    pair: object | None = None,
) -> _R27RevisionPublicationRequest:
    return _R27RevisionPublicationRequest(
        repository_pair=repository._r27_repository_pair if pair is None else pair,
        application_binding_identity=hashlib.sha256(b"binding").hexdigest(),
        attempt_id="attempt-001",
        project_id="r28-demo",
        page_id="page-001",
        target_page_reference="page:1",
        source_state="PromptBuilt",
        target_state="Generated",
        expected_revision=revision,
        expected_aggregate_fingerprint=fingerprint,
    )


def _field_reconstructed_intent(intent: _R27PublicationIntent) -> _R27PublicationIntent:
    return _R27PublicationIntent(
        pair=intent.pair,
        application_binding_identity=intent.application_binding_identity,
        attempt_id=intent.attempt_id,
        project_id=intent.project_id,
        page_id=intent.page_id,
        target_page_reference=intent.target_page_reference,
        source_state=intent.source_state,
        target_state=intent.target_state,
        expected_revision=intent.expected_revision,
        expected_aggregate_fingerprint=intent.expected_aggregate_fingerprint,
    )


def _invalid_intent_for_case(
    case: str, intent: _R27PublicationIntent, factory: _R27PublicationIntentFactory
) -> object:
    replacements: dict[str, dict[str, object]] = {
        "wrong_project": {"project_id": "other-project"},
        "wrong_page": {"page_id": "other-page"},
        "wrong_snapshot": {"expected_revision": intent.expected_revision + 1},
        "stale_expected_revision": {"expected_revision": intent.expected_revision + 1},
        "wrong_expected_f0": {"expected_aggregate_fingerprint": "0" * 64},
        "wrong_attempt": {"attempt_id": "other-attempt"},
        "wrong_binding": {"application_binding_identity": "0" * 64},
        "same_pair_field_clone": {},
        "different_factory_pair": {"pair": object()},
    }
    if case == "missing":
        return None
    if case == "malformed":
        return object()
    if case == "copy_copy":
        return copy.copy(intent)
    if case == "copy_deepcopy":
        return copy.deepcopy(intent)
    if case == "field_reconstruction":
        return _field_reconstructed_intent(intent)
    if case == "consumed":
        assert factory._consume_issued(intent) is True
        return intent
    return replace(intent, **replacements[case])


def test_r28_private_publication_writes_framed_aggregate_and_reopens(tmp_path: Path) -> None:
    repository = LocalFileRepository(tmp_path)
    repository.save(_project())
    snapshot = repository._load_revisioned("r28-demo")

    result = repository._conditional_commit_r27(
        snapshot,
        _project("Committed"),
        _request(repository, fingerprint=snapshot.fingerprint, revision=snapshot.revision),
    )

    aggregate = (tmp_path / "projects" / "r28-demo.json").read_bytes()
    assert aggregate.startswith(bytes.fromhex("894D445232370D0A01"))
    assert result.revision == 2
    reopened = repository._load_revisioned("r28-demo")
    assert reopened.revision == 2
    assert reopened.project.title == "Committed"


def test_r28_private_publication_rejects_cross_repository_pair(tmp_path: Path) -> None:
    repository = LocalFileRepository(tmp_path)
    replacement = LocalFileRepository(tmp_path)
    repository.save(_project())
    snapshot = repository._load_revisioned("r28-demo")
    request = _request(
        repository,
        fingerprint=snapshot.fingerprint,
        revision=snapshot.revision,
        pair=replacement._r27_repository_pair,
    )

    with pytest.raises(ValueError, match="r27 repository composition is invalid"):
        repository._conditional_commit_r27(snapshot, _project("Rejected"), request)


def test_r29_canonical_composition_owns_the_private_activation_policy(tmp_path: Path) -> None:
    repository = LocalFileRepository(tmp_path)
    state_machine = StateMachine()
    event_bus = MemoryEventBus()

    ordinary = build_localfile_external_generation_composition(repository, state_machine, event_bus)
    r28_test = _build_localfile_r27_publication_test_composition(repository, state_machine, event_bus)

    assert ordinary.external_application._r27_publication_factory is not None
    assert ordinary.external_application._r29_activation_policy is not None
    assert r28_test.external_application._r27_publication_factory is not None
    assert r28_test.external_application._r29_activation_policy is None
    assert not repository._revision_store._activation_path("r28-demo").exists()


def test_r28_intent_matches_the_frozen_exact_field_schema() -> None:
    assert tuple(_R27PublicationIntent.__dataclass_fields__) == (
        "pair",
        "application_binding_identity",
        "attempt_id",
        "project_id",
        "page_id",
        "target_page_reference",
        "source_state",
        "target_state",
        "expected_revision",
        "expected_aggregate_fingerprint",
    )


def test_r28_canonical_coordinator_path_publishes_only_after_existing_authority_checks(
    tmp_path: Path,
) -> None:
    repository = LocalFileRepository(tmp_path)
    repository.save(_prompt_built_project())
    composition = _build_localfile_r27_publication_test_composition(
        repository, StateMachine(), MemoryEventBus()
    )

    result = composition.external_application.apply(_binding_report(), _authorization())

    assert result.status == "application_applied_event_published"
    aggregate = (tmp_path / "projects" / "r28-demo.json").read_bytes()
    assert aggregate.startswith(bytes.fromhex("894D445232370D0A01"))
    assert repository._load_revisioned("r28-demo").project.page(1).state is PageState.GENERATED


def test_r29_canonical_application_activation_precedes_missing_r25_predecessor_failure(
    tmp_path: Path,
) -> None:
    repository = LocalFileRepository(tmp_path)
    repository.save(_prompt_built_project())
    composition = build_localfile_external_generation_composition(
        repository, StateMachine(), MemoryEventBus()
    )

    result = composition.external_application.apply(_binding_report(), _authorization())

    activation = repository._revision_store._read_r29_activation("r28-demo")
    assert result.status == "application_not_applied"
    assert result.code == "EXTERNAL_APPLICATION_R25_MATERIALIZATION_FAILED"
    assert result.event_published is False
    assert activation is not None
    assert activation.state == "R27_COMMITTED"
    assert (tmp_path / "projects" / "r28-demo.json").read_bytes().startswith(
        bytes.fromhex("894D445232370D0A01")
    )


def test_r29_canonical_post_activation_publication_stays_framed_when_r25_blocks_continuation(
    tmp_path: Path,
) -> None:
    repository = LocalFileRepository(tmp_path)
    repository.save(
        Project(
            id="r28-demo",
            title="R28",
            pages=[
                _prompt_built_project().page(1),
                Page(
                    page_number=2,
                    state=PageState.PROMPT_BUILT,
                    page_design={},
                    review={},
                    storyboard={},
                    prompt={"prompt_markdown": "second private prompt"},
                ),
            ],
        )
    )
    composition = build_localfile_external_generation_composition(
        repository, StateMachine(), MemoryEventBus()
    )

    first = composition.external_application.apply(_binding_report(), _authorization())
    first_snapshot = repository._load_revisioned("r28-demo")
    activation = repository._revision_store._read_r29_activation("r28-demo")
    second = composition.external_application.apply(
        _binding_report(page_id="2", attempt_id="attempt-002", output_asset_id="asset-002"),
        _authorization(page_id="2", attempt_id="attempt-002"),
    )
    second_snapshot = repository._load_revisioned("r28-demo")

    assert first.status == second.status == "application_not_applied"
    assert first.code == second.code == "EXTERNAL_APPLICATION_R25_MATERIALIZATION_FAILED"
    assert first.event_published is second.event_published is False
    assert activation is not None and activation.state == "R27_COMMITTED"
    assert second_snapshot.revision == first_snapshot.revision + 1
    assert second_snapshot.project.page(2).state is PageState.GENERATED
    assert (tmp_path / "projects" / "r28-demo.json").read_bytes().startswith(
        bytes.fromhex("894D445232370D0A01")
    )


def test_r29_stale_legacy_conditional_commit_is_rejected_after_canonical_activation(
    tmp_path: Path,
) -> None:
    repository = LocalFileRepository(tmp_path)
    repository.save(_prompt_built_project())
    stale = repository._load_revisioned("r28-demo")
    composition = build_localfile_external_generation_composition(
        repository, StateMachine(), MemoryEventBus()
    )
    result = composition.external_application.apply(_binding_report(), _authorization())
    assert result.status == "application_not_applied"
    assert result.code == "EXTERNAL_APPLICATION_R25_MATERIALIZATION_FAILED"
    assert result.event_published is False
    aggregate_path = tmp_path / "projects" / "r28-demo.json"
    aggregate_before = aggregate_path.read_bytes()

    with pytest.raises(LocalFileDurabilityError, match="r29_raw_replacement_forbidden"):
        repository._conditional_commit(stale, stale.project)

    assert aggregate_path.read_bytes() == aggregate_before
    assert repository._revision_store._read_r29_activation("r28-demo").state == "R27_COMMITTED"  # type: ignore[union-attr]


@pytest.mark.parametrize(
    "case",
    (
        "missing",
        "malformed",
        "wrong_project",
        "wrong_page",
        "wrong_snapshot",
        "stale_expected_revision",
        "wrong_expected_f0",
        "wrong_attempt",
        "wrong_binding",
        "consumed",
        "copy_copy",
        "copy_deepcopy",
        "field_reconstruction",
        "same_pair_field_clone",
        "different_factory_pair",
    ),
)
def test_r28_canonical_coordinator_rejects_invalid_intent_before_r27_durability(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    """All noncanonical handoffs stop before aggregate or R27 PREPARED writes."""

    repository = LocalFileRepository(tmp_path)
    repository.save(_prompt_built_project())
    composition = _build_localfile_r27_publication_test_composition(
        repository, StateMachine(), MemoryEventBus()
    )
    coordinator = composition.external_application
    factory = coordinator._r27_publication_factory
    assert factory is not None
    original_issue = factory._issue
    aggregate_path = tmp_path / "projects" / "r28-demo.json"
    aggregate_before = aggregate_path.read_bytes()

    def issue_invalid(binding: object, snapshot: object, context: object, project: object) -> object:
        intent = original_issue(binding, snapshot, context, project)  # type: ignore[arg-type]
        return _invalid_intent_for_case(case, intent, factory)

    monkeypatch.setattr(factory, "_issue", issue_invalid)
    result = coordinator.apply(_binding_report(), _authorization())

    assert result.status == "application_not_applied"
    assert result.code == "EXTERNAL_APPLICATION_R27_INTENT_INVALID"
    assert aggregate_path.read_bytes() == aggregate_before
    assert not repository._revision_store._prepared_path("r28-demo").exists()


def test_r28_page_store_consumes_private_intent_before_repository_call(tmp_path: Path) -> None:
    repository = LocalFileRepository(tmp_path)
    repository.save(_project())
    pair = object()
    page_store = LocalFileDurablePageStore(repository, _r27_pair=pair)
    snapshot = page_store.load_revisioned("r28-demo")
    intent = _R27PublicationIntent(
        pair=pair,
        application_binding_identity=hashlib.sha256(b"binding").hexdigest(),
        attempt_id="attempt-001",
        project_id="r28-demo",
        page_id="page-001",
        target_page_reference="page:1",
        source_state="PromptBuilt",
        target_state="Generated",
        expected_revision=snapshot.revision,
        expected_aggregate_fingerprint=snapshot.fingerprint,
    )

    assert page_store._conditional_commit_r27(snapshot, _project("Committed"), intent).revision == 2
    with pytest.raises(ValueError, match="already consumed"):
        page_store._conditional_commit_r27(snapshot, _project("Again"), intent)


def test_r28_failed_private_repository_call_tombstones_intent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = LocalFileRepository(tmp_path)
    repository.save(_project())
    pair = object()
    page_store = LocalFileDurablePageStore(repository, _r27_pair=pair)
    snapshot = page_store.load_revisioned("r28-demo")
    intent = _R27PublicationIntent(
        pair=pair,
        application_binding_identity=hashlib.sha256(b"binding").hexdigest(),
        attempt_id="attempt-001",
        project_id="r28-demo",
        page_id="page-001",
        target_page_reference="page:1",
        source_state="PromptBuilt",
        target_state="Generated",
        expected_revision=snapshot.revision,
        expected_aggregate_fingerprint=snapshot.fingerprint,
    )
    monkeypatch.setattr(
        repository,
        "_conditional_commit_r27",
        lambda snapshot, project, request: (_ for _ in ()).throw(LocalFileDurabilityError("test failure")),
    )

    with pytest.raises(LocalFileDurabilityError, match="test failure"):
        page_store._conditional_commit_r27(snapshot, _project("Rejected"), intent)
    with pytest.raises(ValueError, match="already consumed"):
        page_store._conditional_commit_r27(snapshot, _project("Again"), intent)


def test_r28_reopen_finalizes_exact_prepared_publication(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repository = LocalFileRepository(tmp_path)
    repository.save(_project())
    snapshot = repository._load_revisioned("r28-demo")
    original = repository._revision_store._write_committed

    def fail_once(record: object) -> None:
        monkeypatch.setattr(repository._revision_store, "_write_committed", original)
        raise LocalFileDurabilityError("private_revision_write_failed")

    monkeypatch.setattr(repository._revision_store, "_write_committed", fail_once)
    with pytest.raises(LocalFileDurabilityError, match="private_revision_write_failed"):
        repository._conditional_commit_r27(
            snapshot,
            _project("Committed"),
            _request(repository, fingerprint=snapshot.fingerprint, revision=snapshot.revision),
        )

    reopened = repository._load_revisioned("r28-demo")
    assert reopened.revision == 2
    assert reopened.project.title == "Committed"


def test_r28_acknowledgement_loss_replays_the_same_committed_lineage_without_writes(
    tmp_path: Path,
) -> None:
    repository = LocalFileRepository(tmp_path)
    repository.save(_project())
    snapshot = repository._load_revisioned("r28-demo")
    request = _request(repository, fingerprint=snapshot.fingerprint, revision=snapshot.revision)
    assert repository._conditional_commit_r27(snapshot, _project("Committed"), request).revision == 2
    aggregate_path = tmp_path / "projects" / "r28-demo.json"
    committed_path = repository._revision_store._committed_path("r28-demo")
    aggregate_before = aggregate_path.read_bytes()
    committed_before = committed_path.read_bytes()

    assert repository._conditional_commit_r27(snapshot, _project("Committed"), request).revision == 2
    assert aggregate_path.read_bytes() == aggregate_before
    assert committed_path.read_bytes() == committed_before


def test_r28_exact_committed_successor_removes_leftover_prepared_without_rewrite(tmp_path: Path) -> None:
    repository = LocalFileRepository(tmp_path)
    repository.save(_project())
    snapshot = repository._load_revisioned("r28-demo")
    request = _request(repository, fingerprint=snapshot.fingerprint, revision=snapshot.revision)
    repository._conditional_commit_r27(snapshot, _project("Committed"), request)
    committed = repository._revision_store._read_committed("r28-demo")
    assert isinstance(committed, _R27CommittedRecord)
    repository._revision_store._write_prepared(
        _R27PreparedRecord(
            expected=_RevisionRecord("r28-demo", snapshot.revision, snapshot.fingerprint),
            proposed=committed.record,
            lineage=committed.lineage,
        )
    )
    committed_path = repository._revision_store._committed_path("r28-demo")
    before = committed_path.read_bytes()

    assert repository._load_revisioned("r28-demo").revision == 2
    assert not repository._revision_store._prepared_path("r28-demo").exists()
    assert committed_path.read_bytes() == before


def test_r28_cross_lineage_leftover_prepared_is_corrupt(tmp_path: Path) -> None:
    repository = LocalFileRepository(tmp_path)
    repository.save(_project())
    snapshot = repository._load_revisioned("r28-demo")
    request = _request(repository, fingerprint=snapshot.fingerprint, revision=snapshot.revision)
    repository._conditional_commit_r27(snapshot, _project("Committed"), request)
    committed = repository._revision_store._read_committed("r28-demo")
    assert isinstance(committed, _R27CommittedRecord)
    conflicting = _R27RevisionPublicationRequest(
        repository_pair=repository._r27_repository_pair,
        application_binding_identity=hashlib.sha256(b"conflicting binding").hexdigest(),
        attempt_id="attempt-002",
        project_id="r28-demo",
        page_id="page-001",
        target_page_reference="page:1",
        source_state="PromptBuilt",
        target_state="Generated",
        expected_revision=snapshot.revision,
        expected_aggregate_fingerprint=snapshot.fingerprint,
    )
    repository._revision_store._write_prepared(
        _R27PreparedRecord(
            expected=_RevisionRecord("r28-demo", snapshot.revision, snapshot.fingerprint),
            proposed=committed.record,
            lineage=_r27_lineage(conflicting, resulting_revision=committed.record.revision),
        )
    )

    with pytest.raises(LocalFileDurabilityError, match="r27_revision_metadata_corrupt"):
        repository._load_revisioned("r28-demo")


@pytest.mark.parametrize(
    "case",
    (
        "missing_committed",
        "corrupt_prepared",
        "corrupt_committed",
        "wrong_project_lineage",
        "wrong_revision_lineage",
        "wrong_f0_lineage",
        "unknown_metadata_version",
    ),
)
def test_r28_framed_reopen_reconciliation_rejects_non_authoritative_metadata(
    tmp_path: Path, case: str
) -> None:
    """A framed aggregate never synthesizes missing or malformed lineage."""

    repository = LocalFileRepository(tmp_path)
    repository.save(_project())
    snapshot = repository._load_revisioned("r28-demo")
    repository._conditional_commit_r27(
        snapshot,
        _project("Committed"),
        _request(repository, fingerprint=snapshot.fingerprint, revision=snapshot.revision),
    )
    aggregate_path = tmp_path / "projects" / "r28-demo.json"
    aggregate_before = aggregate_path.read_bytes()
    prepared_path = repository._revision_store._prepared_path("r28-demo")
    committed_path = repository._revision_store._committed_path("r28-demo")
    committed = repository._revision_store._read_committed("r28-demo")
    assert isinstance(committed, _R27CommittedRecord)

    if case == "missing_committed":
        committed_path.unlink()
    elif case == "corrupt_prepared":
        prepared_path.write_bytes(b'{"schema_version":2}')
    elif case == "corrupt_committed":
        committed_path.write_bytes(b'{"schema_version":2}')
    elif case == "unknown_metadata_version":
        committed_path.write_bytes(b'{"schema_version":3}')
    else:
        lineage = dict(committed.lineage)
        if case == "wrong_project_lineage":
            lineage["project_id"] = "other-project"
        elif case == "wrong_revision_lineage":
            lineage["resulting_revision"] = 99
        else:
            assert case == "wrong_f0_lineage"
            lineage["expected_aggregate_fingerprint"] = "0" * 64
        altered = _R27CommittedRecord(record=committed.record, lineage=lineage)
        committed_path.write_bytes(_canonical_json_bytes(_r27_committed_dict(altered)))

    with pytest.raises(LocalFileDurabilityError):
        repository._load_revisioned("r28-demo")
    assert aggregate_path.read_bytes() == aggregate_before


def test_r28_legacy_reopen_remains_raw_and_unframed(tmp_path: Path) -> None:
    """The R28-only composition does not activate framed publication for legacy saves."""

    repository = LocalFileRepository(tmp_path)
    repository.save(_project())

    aggregate_path = tmp_path / "projects" / "r28-demo.json"
    assert not aggregate_path.read_bytes().startswith(bytes.fromhex("894D445232370D0A01"))
    assert repository._load_revisioned("r28-demo").revision == 1


def test_r28_competing_intent_cannot_replace_the_winning_publication(tmp_path: Path) -> None:
    repository = LocalFileRepository(tmp_path)
    repository.save(_project())
    first = repository._load_revisioned("r28-demo")
    stale = repository._load_revisioned("r28-demo")
    first_request = _request(repository, fingerprint=first.fingerprint, revision=first.revision)
    competing = _R27RevisionPublicationRequest(
        repository_pair=repository._r27_repository_pair,
        application_binding_identity=hashlib.sha256(b"other binding").hexdigest(),
        attempt_id="attempt-002",
        project_id="r28-demo",
        page_id="page-001",
        target_page_reference="page:1",
        source_state="PromptBuilt",
        target_state="Generated",
        expected_revision=stale.revision,
        expected_aggregate_fingerprint=stale.fingerprint,
    )
    repository._conditional_commit_r27(first, _project("Winner"), first_request)
    aggregate = (tmp_path / "projects" / "r28-demo.json").read_bytes()

    with pytest.raises(StaleRevisionError, match="stale_authoritative_revision"):
        repository._conditional_commit_r27(stale, _project("Loser"), competing)
    assert (tmp_path / "projects" / "r28-demo.json").read_bytes() == aggregate


def test_r28_normative_lineage_digest_vector_is_stable() -> None:
    request = _R27RevisionPublicationRequest(
        repository_pair=object(),
        application_binding_identity="21318355bf420544fe2ca04b6d98ae74580432d76e17141d8d563d3c0ead76bc",
        attempt_id="attempt-01",
        project_id="project-01",
        page_id="page-01",
        target_page_reference="target-page-01",
        source_state="PromptBuilt",
        target_state="Generated",
        expected_revision=7,
        expected_aggregate_fingerprint="a" * 64,
    )

    lineage = _r27_lineage(request, resulting_revision=8)

    assert lineage["pending_lineage_identity"] == (
        "f3b65979b5e50e6d2ffce9f6b5600916eab3cc6d2ea9ccb0a36ddb4806f20e41"
    )
    assert lineage["pending_lineage_digest"] == (
        "45377e1bc7ac5dcc514205c976a988838c3896c60eb3a1d10ebd4a877b5a71cb"
    )


def test_r28_normative_prepared_and_committed_v2_wire_vectors() -> None:
    lineage: dict[str, object] = {
        "application_binding_identity": "21318355bf420544fe2ca04b6d98ae74580432d76e17141d8d563d3c0ead76bc",
        "attempt_id": "attempt-01",
        "expected_aggregate_fingerprint": "a" * 64,
        "expected_revision": 7,
        "page_id": "page-01",
        "pending_lineage_digest": "45377e1bc7ac5dcc514205c976a988838c3896c60eb3a1d10ebd4a877b5a71cb",
        "pending_lineage_identity": "f3b65979b5e50e6d2ffce9f6b5600916eab3cc6d2ea9ccb0a36ddb4806f20e41",
        "project_id": "project-01",
        "resulting_revision": 8,
        "schema": "manga_director.r27.pending-lineage",
        "source_state": "PromptBuilt",
        "target_page_reference": "target-page-01",
        "target_state": "Generated",
        "version": 1,
    }
    prepared = _R27PreparedRecord(
        _RevisionRecord("project-01", 7, "a" * 64),
        _RevisionRecord("project-01", 8, "b" * 64),
        lineage,
    )
    committed = _R27CommittedRecord(_RevisionRecord("project-01", 8, "b" * 64), lineage)
    expected_prepared = (
        b'{"expected":{"fingerprint":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","project_id":"project-01","revision":7,"schema_version":1},"proposed":{"fingerprint":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","project_id":"project-01","revision":8,"schema_version":1},"r27_pending_lineage":{"application_binding_identity":"21318355bf420544fe2ca04b6d98ae74580432d76e17141d8d563d3c0ead76bc","attempt_id":"attempt-01","expected_aggregate_fingerprint":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","expected_revision":7,"page_id":"page-01","pending_lineage_digest":"45377e1bc7ac5dcc514205c976a988838c3896c60eb3a1d10ebd4a877b5a71cb","pending_lineage_identity":"f3b65979b5e50e6d2ffce9f6b5600916eab3cc6d2ea9ccb0a36ddb4806f20e41","project_id":"project-01","resulting_revision":8,"schema":"manga_director.r27.pending-lineage","source_state":"PromptBuilt","target_page_reference":"target-page-01","target_state":"Generated","version":1},"r27_phase":"PREPARED","schema_version":2}'
    )
    expected_committed = (
        b'{"fingerprint":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","project_id":"project-01","r27_pending_lineage":{"application_binding_identity":"21318355bf420544fe2ca04b6d98ae74580432d76e17141d8d563d3c0ead76bc","attempt_id":"attempt-01","expected_aggregate_fingerprint":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","expected_revision":7,"page_id":"page-01","pending_lineage_digest":"45377e1bc7ac5dcc514205c976a988838c3896c60eb3a1d10ebd4a877b5a71cb","pending_lineage_identity":"f3b65979b5e50e6d2ffce9f6b5600916eab3cc6d2ea9ccb0a36ddb4806f20e41","project_id":"project-01","resulting_revision":8,"schema":"manga_director.r27.pending-lineage","source_state":"PromptBuilt","target_page_reference":"target-page-01","target_state":"Generated","version":1},"r27_phase":"COMMITTED","revision":8,"schema_version":2}'
    )

    actual_prepared = _canonical_json_bytes(_r27_prepared_dict(prepared))
    actual_committed = _canonical_json_bytes(_r27_committed_dict(committed))

    assert actual_prepared == expected_prepared
    assert len(actual_prepared) == 1_027
    assert hashlib.sha256(actual_prepared).hexdigest() == "b4249e1eb8b692940b45d0b9aa35435d4babfdeca409670f0b7ac3cfd35bf88b"
    assert actual_committed == expected_committed
    assert len(actual_committed) == 844
    assert hashlib.sha256(actual_committed).hexdigest() == "509110528a319b282fd10813e19afd2f0fffd515bd8d5edb4d6b15d0d54025dd"


def test_r28_unpublished_prepared_record_is_cleaned_without_retry_authority(
    tmp_path: Path,
) -> None:
    repository = LocalFileRepository(tmp_path)
    repository.save(_project())
    snapshot = repository._load_revisioned("r28-demo")
    def fail_before_staging(boundary: str) -> None:
        if boundary == "before_aggregate_staging_write":
            raise LocalFileDurabilityError("authoritative_staging_failed")

    repository._revision_store._r27_fault_injector = fail_before_staging
    with pytest.raises(LocalFileDurabilityError, match="authoritative_staging_failed"):
        repository._conditional_commit_r27(
            snapshot,
            _project("Never-published"),
            _request(repository, fingerprint=snapshot.fingerprint, revision=snapshot.revision),
        )
    repository._revision_store._r27_fault_injector = None

    assert repository._load_revisioned("r28-demo").revision == 1
    assert not repository._revision_store._prepared_path("r28-demo").exists()


@pytest.mark.parametrize(
    ("boundary", "outcome"),
    (
        ("before_prepared_metadata_write", "safe_abort"),
        ("during_prepared_metadata_write", "safe_abort"),
        ("after_prepared_metadata_durability", "prepared_old"),
        ("before_aggregate_staging_write", "prepared_old"),
        ("during_aggregate_staging_write", "prepared_old"),
        ("after_aggregate_staging_write", "prepared_old"),
        ("after_aggregate_staging_file_sync", "prepared_old"),
        ("before_aggregate_replace", "prepared_old"),
        ("immediately_after_aggregate_replace", "prepared_new"),
        ("after_aggregate_durability_sync", "prepared_new"),
        ("before_persisted_byte_reread", "prepared_new"),
        ("after_reread_verification", "prepared_new"),
        ("before_committed_metadata_write", "prepared_new"),
        ("during_committed_metadata_write", "prepared_new"),
        ("after_committed_metadata_durability", "committed_prepared"),
        ("before_prepared_cleanup", "committed_prepared"),
        ("after_prepared_cleanup", "committed"),
        ("before_caller_acknowledgement", "committed"),
    ),
)
def test_r28_each_private_durability_boundary_has_a_distinct_fault_observation(
    tmp_path: Path, boundary: str, outcome: str
) -> None:
    """Assert each real private publication point's durable crash state and reopen outcome."""

    repository = LocalFileRepository(tmp_path)
    repository.save(_project())
    snapshot = repository._load_revisioned("r28-demo")
    aggregate_path = tmp_path / "projects" / "r28-demo.json"
    prepared_path = repository._revision_store._prepared_path("r28-demo")
    committed_path = repository._revision_store._committed_path("r28-demo")
    original_aggregate = aggregate_path.read_bytes()
    original_committed = committed_path.read_bytes()

    def inject(point: str) -> None:
        if point == boundary:
            raise LocalFileDurabilityError(f"injected:{boundary}")

    repository._revision_store._r27_fault_injector = inject
    request = _request(repository, fingerprint=snapshot.fingerprint, revision=snapshot.revision)
    with pytest.raises(LocalFileDurabilityError, match=f"injected:{boundary}"):
        repository._conditional_commit_r27(snapshot, _project("Committed"), request)
    repository._revision_store._r27_fault_injector = None

    aggregate_tmp = tuple(aggregate_path.parent.glob("*.tmp"))
    metadata_tmp = tuple(prepared_path.parent.glob("*.tmp"))
    if outcome == "safe_abort":
        assert aggregate_path.read_bytes() == original_aggregate
        assert committed_path.read_bytes() == original_committed
        assert not prepared_path.exists()
        assert not aggregate_tmp
    elif outcome == "prepared_old":
        assert aggregate_path.read_bytes() == original_aggregate
        assert committed_path.read_bytes() == original_committed
        assert prepared_path.exists()
    elif outcome == "prepared_new":
        assert aggregate_path.read_bytes().startswith(bytes.fromhex("894D445232370D0A01"))
        assert committed_path.read_bytes() == original_committed
        assert prepared_path.exists()
    elif outcome == "committed_prepared":
        assert aggregate_path.read_bytes().startswith(bytes.fromhex("894D445232370D0A01"))
        assert repository._revision_store._read_committed("r28-demo") is not None
        assert prepared_path.exists()
    else:
        assert outcome == "committed"
        assert aggregate_path.read_bytes().startswith(bytes.fromhex("894D445232370D0A01"))
        assert repository._revision_store._read_committed("r28-demo") is not None
        assert not prepared_path.exists()
    assert all(item.suffix == ".tmp" for item in aggregate_tmp + metadata_tmp)

    reopened = repository._load_revisioned("r28-demo")
    if outcome in {"prepared_new", "committed_prepared", "committed"}:
        assert reopened.revision == 2
    else:
        assert reopened.revision == 1


def test_r28_acknowledgement_loss_replays_without_new_durable_publication(tmp_path: Path) -> None:
    """A lost caller acknowledgement reuses committed lineage, not an in-memory intent."""

    repository = LocalFileRepository(tmp_path)
    repository.save(_project())
    snapshot = repository._load_revisioned("r28-demo")
    request = _request(repository, fingerprint=snapshot.fingerprint, revision=snapshot.revision)
    assert repository._conditional_commit_r27(snapshot, _project("Committed"), request).revision == 2
    aggregate_path = tmp_path / "projects" / "r28-demo.json"
    committed_path = repository._revision_store._committed_path("r28-demo")
    aggregate_before = aggregate_path.read_bytes()
    committed_before = committed_path.read_bytes()

    assert repository._conditional_commit_r27(snapshot, _project("Committed"), request).revision == 2
    assert aggregate_path.read_bytes() == aggregate_before
    assert committed_path.read_bytes() == committed_before


@pytest.mark.parametrize(
    "payload",
    (
        b'{"schema_version":2,"schema_version":2}',
        b'{"schema_version":2.0}',
        b'{"schema_version":true}',
    ),
)
def test_r28_metadata_classifier_rejects_ambiguous_or_non_integer_v2(
    tmp_path: Path, payload: bytes
) -> None:
    repository = LocalFileRepository(tmp_path)
    repository.save(_project())
    repository._load_revisioned("r28-demo")
    repository._revision_store._committed_path("r28-demo").write_bytes(payload)

    with pytest.raises(LocalFileDurabilityError):
        repository._load_revisioned("r28-demo")


@pytest.mark.parametrize(
    ("raw", "expected"),
    (
        (b'{"schema_version":1}', "LEGACY_V1"),
        (b'{"schema_version":2}', "R27_V2"),
        (b'{"schema_version":true}', None),
        (b'{"schema_version":false}', None),
        (b'{"schema_version":1.0}', None),
        (b'{"schema_version":2.0}', None),
        (b'{"schema_version":1e0}', None),
        (b'{"schema_version":"1"}', None),
        (b'{"schema_version":"2"}', None),
        (b'{"schema_version":null}', None),
        (b'{"other":1}', None),
        (b'{"schema_version":0}', None),
        (b'{"schema_version":-1}', None),
        (b'{"schema_version":3}', None),
        (b'{"schema_version":1,"schema_version":1}', None),
        (b'{"schema_version":2,"schema_version":2}', None),
        (b'{"schema_version":1,"schema_version":2}', None),
        (b'{"schema_version":2,"schema_version":1}', None),
        (b'{"schema_version":true,"schema_version":1}', None),
        (b'{"schema_version":1,"schema_version":true}', None),
        (b'{"schema_version":true,"schema_version":2}', None),
        (b'{"schema_version":2,"schema_version":true}', None),
        (b'{"schema_version":2,"schema_version":3}', None),
        (b'{"schema_version":3,"schema_version":2}', None),
    ),
)
def test_r28_raw_version_classifier_uses_exact_json_kinds(
    tmp_path: Path, raw: bytes, expected: str | None
) -> None:
    path = tmp_path / "metadata.json"
    path.write_bytes(raw)

    if expected is None:
        with pytest.raises(LocalFileDurabilityError):
            _read_revision_metadata(path)
    else:
        assert _read_revision_metadata(path)[0] == expected
