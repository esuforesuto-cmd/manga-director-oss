"""Focused tests for the trusted, pre-provider D05 LocalFile boundary."""

from __future__ import annotations

import inspect
import sqlite3
import threading
from pathlib import Path

import pytest
from generation_admission_v1_fixtures import manifest
from pydantic import ValidationError

import manga_director
import manga_director.production as production
from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.production import future_durable_generation_boundary as boundary_module
from manga_director.production import (
    future_localfile_durable_generation_boundary as localfile_module,
)
from manga_director.production.future_durable_generation_attempt import (
    _LocalFutureGenerationAttemptStore,
)
from manga_director.production.future_durable_generation_boundary import _new_attempt
from manga_director.production.future_generation_admission_contract import (
    GenerationAdmissionManifestV1,
    SnapshotIdentityV1,
)
from manga_director.production.future_generation_admission_evaluator import (
    GenerationAdmissionEvaluator,
)
from manga_director.repositories.local_file import LocalFileRepository


def _repository(
    tmp_path: Path, *, storyboard_changed: bool = False, provider_binding_missing: bool = False
) -> tuple[LocalFileRepository, GenerationAdmissionManifestV1]:
    admitted = manifest().model_copy(
        update={"project_id": "project-d05", "attempt_id": "attempt-d05-001"}
    )
    storyboard = admitted.storyboard.model_dump(mode="json")
    if storyboard_changed:
        storyboard["panels"][0]["action"] = "changed"
    metadata: dict[str, object] = {
        "future_generation_target_reference": admitted.execution_target_reference,
    }
    if not provider_binding_missing:
        metadata["future_generation_provider_binding"] = admitted.provider_request.model_dump(mode="json")
    repository = LocalFileRepository(tmp_path / "repository")
    repository.save(
        Project(
            id=admitted.project_id,
            title="D05",
            pages=[
                Page(
                    page_number=1,
                    state=PageState.PROMPT_BUILT,
                    page_design={},
                    review={},
                    storyboard=storyboard,
                    prompt=admitted.prompt.model_dump(mode="json"),
                    metadata=metadata,
                )
            ],
        )
    )
    snapshot = repository._load_revisioned(admitted.project_id)
    return repository, admitted.model_copy(
        update={
            "page_id": "1",
            "snapshot": SnapshotIdentityV1(revision=snapshot.revision, fingerprint=snapshot.fingerprint),
        }
    )


def _boundary(
    tmp_path: Path,
) -> tuple[localfile_module.LocalFileDurableGenerationBoundary, LocalFileRepository, GenerationAdmissionManifestV1]:
    repository, admitted = _repository(tmp_path)
    return localfile_module.LocalFileDurableGenerationBoundary(repository), repository, admitted


def _prepared_boundary(
    tmp_path: Path,
) -> tuple[
    localfile_module.LocalFileDurableGenerationBoundary,
    LocalFileRepository,
    GenerationAdmissionManifestV1,
    boundary_module.ProviderInvocationPermitV1,
]:
    boundary, repository, admitted = _boundary(tmp_path)
    assert boundary.reserve(admitted).code == "RESERVATION_RESERVED"
    permit = boundary.prepare_provider_start(admitted).permit
    assert permit is not None
    return boundary, repository, admitted, permit


def _replace_page(repository: LocalFileRepository, project_id: str, replacement: Page) -> None:
    snapshot = repository._load_revisioned(project_id)
    repository.save(snapshot.project.replace_page(replacement))


def test_trusted_constructor_accepts_only_repository_and_derives_private_root(tmp_path: Path) -> None:
    boundary, repository, _admitted = _boundary(tmp_path)
    expected = repository._root.resolve() / "_durability" / "_future_durable_generation" / "attempts"

    assert tuple(inspect.signature(localfile_module.LocalFileDurableGenerationBoundary).parameters) == (
        "repository",
    )
    assert boundary._core._store._root == expected
    assert boundary._core._store._root != repository._workflow_application_ledger_owner_root()


def test_trusted_path_binds_concrete_reader_evaluator_and_fence(tmp_path: Path) -> None:
    boundary, _repository_value, _admitted = _boundary(tmp_path)

    assert isinstance(boundary._core._reader, localfile_module._LocalFileCurrentAdmissionEvidenceReader)
    assert type(boundary._core._evaluator) is GenerationAdmissionEvaluator
    assert boundary._core._fence_factory.__name__ == "WindowsPageExecutionFence"


@pytest.mark.parametrize("storyboard_changed,provider_binding_missing", ((True, False), (False, True)))
def test_fabricated_or_missing_persisted_evidence_cannot_issue_permit(
    tmp_path: Path, storyboard_changed: bool, provider_binding_missing: bool
) -> None:
    repository, admitted = _repository(
        tmp_path, storyboard_changed=storyboard_changed, provider_binding_missing=provider_binding_missing
    )
    boundary = localfile_module.LocalFileDurableGenerationBoundary(repository)

    assert boundary.reserve(admitted).code == "RESERVATION_RESERVED"
    report = boundary.prepare_provider_start(admitted)

    assert report.eligibility == "BLOCKED"
    assert report.permit is None


def test_valid_flow_returns_only_immutable_pre_provider_permit(tmp_path: Path) -> None:
    boundary, _repository_value, admitted = _boundary(tmp_path)

    assert boundary.reserve(admitted).code == "RESERVATION_RESERVED"
    report = boundary.prepare_provider_start(admitted)

    assert report.eligibility == "ELIGIBLE"
    assert report.permit is not None
    assert report.permit.lifecycle == "PROVIDER_STARTING"
    assert boundary.permit_is_current(admitted, report.permit) is True
    with pytest.raises(ValidationError):
        report.permit.sequence = 0


def test_reopen_makes_permit_invalid_and_blocks_new_attempt(tmp_path: Path) -> None:
    boundary, _repository_value, admitted = _boundary(tmp_path)
    assert boundary.reserve(admitted).code == "RESERVATION_RESERVED"
    permit = boundary.prepare_provider_start(admitted).permit
    assert permit is not None

    assert boundary.reopen(admitted).eligibility == "RECOVERY_REQUIRED"
    assert boundary.permit_is_current(admitted, permit) is False
    competing = admitted.model_copy(update={"attempt_id": "attempt:competing"})
    assert boundary.reserve(competing).code == "RESERVATION_TARGET_CONFLICT"


def test_missing_required_index_and_corrupt_row_fail_closed(tmp_path: Path) -> None:
    boundary, repository, admitted = _boundary(tmp_path)
    assert boundary.reserve(admitted).code == "RESERVATION_RESERVED"
    database = boundary._core._store._database
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE future_generation_attempts SET payload_digest='0'")
    assert boundary.reopen(admitted).code == "REOPEN_ATTEMPT_CORRUPT"

    with sqlite3.connect(database) as connection:
        connection.execute("DROP INDEX active_or_recovery_future_generation_target")
    with pytest.raises(ValueError, match="attempt store is unavailable"):
        localfile_module.LocalFileDurableGenerationBoundary(repository)


def test_terminal_failed_attempt_allows_only_a_new_distinct_attempt(tmp_path: Path) -> None:
    _boundary_value, repository, admitted = _boundary(tmp_path)
    store = _LocalFutureGenerationAttemptStore(
        repository._root.resolve() / "_durability" / "_future_durable_generation_test_only"
    )
    first = _new_attempt(admitted)
    assert store.reserve(first).outcome == "reserved"
    starting = store.transition(first, "PROVIDER_STARTING").attempt
    assert starting is not None
    started = store.transition(starting, "PROVIDER_STARTED", evidence_digest="1" * 64).attempt
    assert started is not None
    assert store.transition(started, "FAILED").outcome == "transitioned"
    second = _new_attempt(admitted.model_copy(update={"attempt_id": "attempt:after-failure"}))
    assert store.reserve(second).outcome == "reserved"
    assert store.reserve(first).outcome == "conflict"


def test_no_synthetic_or_provider_callback_reaches_trusted_boundary(tmp_path: Path) -> None:
    boundary, _repository_value, admitted = _boundary(tmp_path)
    source = inspect.getsource(boundary_module) + inspect.getsource(localfile_module)

    assert boundary.reserve(admitted).code == "RESERVATION_RESERVED"
    assert boundary.prepare_provider_start(admitted).permit is not None
    assert "SyntheticProviderEvidence" not in source
    assert "InertProviderEdgeSentinel" not in source
    assert "ProviderGenerationInvocationPort" not in source
    assert "import socket" not in source
    assert "import urllib" not in source
    assert "import requests" not in source
    assert not hasattr(manga_director, "ProviderInvocationPermitV1")
    assert not hasattr(production, "ProviderInvocationPermitV1")
    assert tuple(tmp_path.glob("**/*.png")) == ()


def test_valid_permit_consumes_once_and_returns_redacted_immutable_dispatch_request(tmp_path: Path) -> None:
    boundary, _repository_value, admitted, permit = _prepared_boundary(tmp_path)

    request = boundary.consume_for_dispatch(admitted, permit)

    assert request is not None
    assert request.attempt_id == admitted.attempt_id
    assert request.manifest_digest == admitted.content_digest
    assert request.provider_binding_digest == permit.provider_binding_digest
    assert request.provider_request == admitted.provider_request
    assert request.consumption_sequence == permit.sequence
    assert request.idempotency_identity == request.dispatch_request_identity
    assert boundary.permit_is_current(admitted, permit) is False
    with pytest.raises(ValidationError):
        request.attempt_id = "attempt-mutated"
    request_payload = repr(request.model_dump(mode="json")).lower()
    with sqlite3.connect(boundary._core._store._database) as connection:
        durable_payload = str(connection.execute("SELECT payload_json FROM future_generation_attempts").fetchone()[0]).lower()
    for secret_part in ("api_key", "authorization", "credential", "password", "secret", "token"):
        assert secret_part not in request_payload
        assert secret_part not in durable_payload


def test_consumed_permit_and_copy_cannot_issue_a_second_dispatch(tmp_path: Path) -> None:
    boundary, _repository_value, admitted, permit = _prepared_boundary(tmp_path)
    copied_permit = permit.model_copy()

    first = boundary.consume_for_dispatch(admitted, permit)
    second = boundary.consume_for_dispatch(admitted, copied_permit)
    stored = boundary._core._store.lookup(admitted.attempt_id).attempt

    assert first is not None
    assert second is None
    assert stored is not None
    assert stored.dispatch_consumed_sequence == first.consumption_sequence
    assert stored.dispatch_request_identity == first.dispatch_request_identity


def test_concurrent_consumers_have_exactly_one_durable_winner(tmp_path: Path) -> None:
    first_boundary, repository, admitted, permit = _prepared_boundary(tmp_path)
    second_boundary = localfile_module.LocalFileDurableGenerationBoundary(repository)
    barrier = threading.Barrier(3)
    results: list[boundary_module.ProviderDispatchRequestV1 | None] = []

    def consume(boundary: localfile_module.LocalFileDurableGenerationBoundary) -> None:
        barrier.wait()
        results.append(boundary.consume_for_dispatch(admitted, permit.model_copy()))

    threads = [threading.Thread(target=consume, args=(boundary,)) for boundary in (first_boundary, second_boundary)]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join()

    winners = [result for result in results if result is not None]
    stored = first_boundary._core._store.lookup(admitted.attempt_id).attempt
    assert len(winners) == 1
    assert stored is not None
    assert stored.dispatch_request_identity == winners[0].dispatch_request_identity


def test_consumed_attempt_reopen_requires_recovery_and_never_reissues_dispatch(tmp_path: Path) -> None:
    boundary, _repository_value, admitted, permit = _prepared_boundary(tmp_path)
    request = boundary.consume_for_dispatch(admitted, permit)
    assert request is not None

    reopened = boundary.reopen(admitted)

    assert reopened.eligibility == "RECOVERY_REQUIRED"
    assert boundary.consume_for_dispatch(admitted, permit) is None
    assert boundary._core._store.lookup(admitted.attempt_id).attempt is not None


@pytest.mark.parametrize("change", ("storyboard", "prompt", "snapshot", "provider"))
def test_fresh_authoritative_evidence_changes_block_consumption(tmp_path: Path, change: str) -> None:
    boundary, repository, admitted, permit = _prepared_boundary(tmp_path)
    snapshot = repository._load_revisioned(admitted.project_id)
    page = snapshot.project.page(1)
    if change == "storyboard":
        storyboard = dict(page.storyboard or {})
        panels = list(storyboard["panels"])
        panels[0] = {**panels[0], "action": "fresh-change"}
        _replace_page(repository, admitted.project_id, page.model_copy(update={"storyboard": {**storyboard, "panels": panels}}))
    elif change == "prompt":
        prompt = dict(page.prompt or {})
        prompt["source_storyboard_digest"] = "0" * 64
        _replace_page(repository, admitted.project_id, page.model_copy(update={"prompt": prompt}))
    elif change == "snapshot":
        _replace_page(repository, admitted.project_id, page)
    else:
        metadata = dict(page.metadata)
        binding = dict(metadata["future_generation_provider_binding"])
        binding["provider_reference"] = "provider-fresh-change"
        metadata["future_generation_provider_binding"] = binding
        _replace_page(repository, admitted.project_id, page.model_copy(update={"metadata": metadata}))

    assert boundary.consume_for_dispatch(admitted, permit) is None
    assert boundary._core._store.lookup(admitted.attempt_id).attempt is not None


@pytest.mark.parametrize(
    "manifest_update,permit_update",
    (
        ({"attempt_id": "attempt-other"}, {}),
        ({"page_id": "2"}, {}),
        ({"execution_target_reference": "target-other"}, {}),
        ({}, {"sequence": 99}),
        ({"snapshot": SnapshotIdentityV1(revision=99, fingerprint="1" * 64)}, {}),
    ),
)
def test_mismatched_attempt_page_target_sequence_or_manifest_cannot_consume(
    tmp_path: Path, manifest_update: dict[str, object], permit_update: dict[str, object]
) -> None:
    boundary, _repository_value, admitted, permit = _prepared_boundary(tmp_path)
    mismatched_manifest = admitted.model_copy(update=manifest_update)
    mismatched_permit = permit.model_copy(update=permit_update)

    assert boundary.consume_for_dispatch(mismatched_manifest, mismatched_permit) is None
    assert boundary.permit_is_current(admitted, permit) is True


def test_corrupt_or_schema_invalid_persistence_blocks_consumption(tmp_path: Path) -> None:
    boundary, repository, admitted, permit = _prepared_boundary(tmp_path)
    database = boundary._core._store._database
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE future_generation_attempts SET payload_digest='0'")

    assert boundary.consume_for_dispatch(admitted, permit) is None
    with sqlite3.connect(database) as connection:
        connection.execute("DROP INDEX active_or_recovery_future_generation_target")
    with pytest.raises(ValueError, match="attempt store is unavailable"):
        localfile_module.LocalFileDurableGenerationBoundary(repository)


def test_dispatch_request_has_no_provider_callback_or_public_export(tmp_path: Path) -> None:
    boundary, _repository_value, admitted, permit = _prepared_boundary(tmp_path)
    source = inspect.getsource(boundary_module) + inspect.getsource(localfile_module)

    assert boundary.consume_for_dispatch(admitted, permit) is not None
    assert "ProviderGenerationInvocationPort" not in source
    assert "import socket" not in source
    assert "import urllib" not in source
    assert "import requests" not in source
    assert not hasattr(manga_director, "ProviderDispatchRequestV1")
    assert not hasattr(production, "ProviderDispatchRequestV1")
