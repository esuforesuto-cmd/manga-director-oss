"""Focused D09-I01 tests for the private fake-only durable submission journal."""

from __future__ import annotations

import inspect
import json
import sqlite3
import threading
from pathlib import Path
from typing import get_args

import pytest
from generation_admission_v1_fixtures import manifest

import manga_director
import manga_director.production as production
from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.production import future_fake_provider_receipt_journal as d09
from manga_director.production.future_durable_generation_boundary import (
    ProviderDispatchRequestV1,
    ProviderInvocationPermitV1,
)
from manga_director.production.future_generation_admission_contract import (
    GenerationAdmissionManifestV1,
    ProviderRequestBindingV1,
    SnapshotIdentityV1,
    content_digest,
)
from manga_director.production.future_provider_capability_profile import (
    CAPABILITY_NAMES,
    comfyui_capability_profile_fixture_v1,
)
from manga_director.repositories.local_file import LocalFileRepository


def _digest(value: str) -> str:
    return content_digest({"value": value})


def _dispatch(identity: str = "dispatch-one") -> ProviderDispatchRequestV1:
    return ProviderDispatchRequestV1(
        attempt_id="attempt:d09",
        project_id="project:d09",
        page_id="1",
        execution_target_reference="target:d09",
        manifest_digest=_digest("manifest"),
        provider_binding_digest=_digest("provider"),
        attempt_binding_digest=_digest("attempt"),
        consumption_sequence=1,
        dispatch_request_identity=_digest(identity),
        idempotency_identity=_digest(identity),
        provider_request=ProviderRequestBindingV1(provider_reference="fake:provider"),
    )


def _evidence(capability: str) -> dict[str, object]:
    return {
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


def _profile(duplicate: str = "IDEMPOTENT_SAME_OPERATION") -> dict[str, object]:
    evidence = [_evidence(capability) for capability in CAPABILITY_NAMES]
    applicability = [
        {
            "source_reference": item["source_reference"],
            "source_revision": item["source_revision"],
            "provider_reference": "test:provider",
            "provider_revision": "provider:1",
            "review_revision": "review:1",
        }
        for item in evidence
    ]
    return {
        "schema_name": "manga_director.future_provider_capability_profile",
        "schema_version": "1",
        "provider_reference": "test:provider",
        "provider_revision": "provider:1",
        "adapter_version": "fixture:1",
        "review_revision": "review:1",
        "profile_revision": 1,
        "duplicate_submit_semantics": duplicate,
        "reviewed_source_applicability": applicability,
        "evidence": evidence,
    }


def _harness(tmp_path: Path) -> d09._D09TestOnlyHarness:
    return d09._D09TestOnlyHarness((tmp_path / "d09").resolve())


def _trusted_runtime(
    tmp_path: Path,
) -> tuple[
    d09._LocalFileFakeProviderReceiptJournal,
    GenerationAdmissionManifestV1,
    ProviderInvocationPermitV1,
]:
    admitted = manifest().model_copy(update={"project_id": "project-d09", "attempt_id": "attempt-d09"})
    repository = LocalFileRepository(tmp_path / "repository")
    repository.save(
        Project(
            id=admitted.project_id,
            title="D09",
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
        update={"page_id": "1", "snapshot": SnapshotIdentityV1(revision=snapshot.revision, fingerprint=snapshot.fingerprint)}
    )
    runtime = d09._LocalFileFakeProviderReceiptJournal(repository)
    assert runtime._d05.reserve(bound).code == "RESERVATION_RESERVED"
    permit = runtime._d05.prepare_provider_start(bound).permit
    assert permit is not None
    return runtime, bound, permit


def test_valid_d05_dispatch_raw_d08_profile_creates_redacted_accepted_receipt(tmp_path: Path) -> None:
    result = _harness(tmp_path).submit_consumed_dispatch(
        _dispatch(), _profile(), d09.FakeSubmissionPlanV1(outcome="ACCEPTED", provider_job_identity="job:1")
    )

    assert result.status == "ACCEPTED"
    assert result.receipt is not None
    assert result.receipt.provider_job_identity == "job:1"
    assert result.receipt.dispatch_identity == _dispatch().dispatch_request_identity


def test_supported_runtime_consumes_d05_in_the_same_submission_flow(tmp_path: Path) -> None:
    runtime, admitted, permit = _trusted_runtime(tmp_path)

    first = runtime.submit(manifest=admitted, permit=permit, raw_provider_profile=_profile())
    second = runtime.submit(manifest=admitted, permit=permit, raw_provider_profile=_profile())

    assert first.status == "ACCEPTED" and first.edge_invoked
    assert second.status == "BLOCKED" and not second.edge_invoked


def test_duplicate_and_reopen_return_existing_history_without_second_fake_submit(tmp_path: Path) -> None:
    harness = _harness(tmp_path)
    dispatch = _dispatch()
    plan = d09.FakeSubmissionPlanV1(outcome="ACCEPTED")
    first = harness.submit_consumed_dispatch(dispatch, _profile(), plan)
    second = harness.submit_consumed_dispatch(dispatch, _profile(), plan)
    assert first.status == second.status == "ACCEPTED"
    assert first.edge_invoked and not second.edge_invoked
    assert harness.reopen_consumed_dispatch(dispatch, _profile()).status == "ACCEPTED"


def test_conflicting_raw_profile_for_same_dispatch_fails_closed(tmp_path: Path) -> None:
    harness = _harness(tmp_path)
    dispatch = _dispatch()
    assert harness.submit_consumed_dispatch(dispatch, _profile(), d09.FakeSubmissionPlanV1(outcome="ACCEPTED")).status == "ACCEPTED"
    assert (
        harness.submit_consumed_dispatch(
            dispatch,
            _profile("REJECTED_NON_IDEMPOTENT"),
            d09.FakeSubmissionPlanV1(outcome="ACCEPTED"),
        ).status
        == "CONFLICT"
    )


def test_class_b_uses_the_durable_dispatch_identity_without_blind_resubmit(tmp_path: Path) -> None:
    harness = _harness(tmp_path)
    dispatch = _dispatch()
    profile = _profile("REJECTED_NON_IDEMPOTENT")
    plan = d09.FakeSubmissionPlanV1(outcome="ACCEPTED")

    assert harness.submit_consumed_dispatch(dispatch, profile, plan).edge_invoked
    assert not harness.submit_consumed_dispatch(dispatch, profile, plan).edge_invoked


def test_edge_is_called_only_after_submission_started_is_durable(tmp_path: Path) -> None:
    result = _harness(tmp_path).submit_consumed_dispatch(
        _dispatch(), _profile(), d09.FakeSubmissionPlanV1(outcome="ACCEPTED")
    )
    assert result.status == "ACCEPTED" and result.edge_invoked
    assert result.durable_start_sequence == 1


def test_ambiguous_class_c_and_reopen_after_start_require_recovery_without_resubmit(tmp_path: Path) -> None:
    harness = _harness(tmp_path)
    result = harness.submit_consumed_dispatch(
        _dispatch(), comfyui_capability_profile_fixture_v1(), d09.FakeSubmissionPlanV1(outcome="AMBIGUOUS")
    )
    assert result.status == "RECOVERY_REQUIRED"

    journal = d09._LocalFakeProviderReceiptJournal((tmp_path / "start").resolve())
    binding = d09.D09DispatchBindingV1(
        attempt_id="attempt:d09",
        project_id="project:d09",
        page_id="1",
        execution_target_reference="target:d09",
        manifest_digest=_digest("manifest"),
        provider_binding_digest=_digest("provider"),
        attempt_binding_digest=_digest("attempt"),
        dispatch_identity=_digest("start"),
        idempotency_identity=_digest("start"),
        profile_identity=_digest("profile"),
        provider_class="A",
    )
    assert journal.reserve(binding)[0] == "reserved"
    assert journal.transition(binding, "DISPATCH_RECEIVED", "SUBMISSION_STARTED")[0] == "transitioned"
    assert journal.reopen(binding).status == "RECOVERY_REQUIRED"


@pytest.mark.parametrize("outcome", ("REJECTED", "FAILED_BEFORE_SEND", "MALFORMED"))
def test_fake_outcomes_are_durable_and_never_result_capture(tmp_path: Path, outcome: d09.FakeOutcome) -> None:
    result = _harness(tmp_path).submit_consumed_dispatch(
        _dispatch(), _profile(), d09.FakeSubmissionPlanV1(outcome=outcome)
    )
    assert result.status in {"REJECTED", "FAILED_BEFORE_SEND", "AMBIGUOUS"}
    assert result.receipt is None if outcome == "MALFORMED" else result.receipt is not None


@pytest.mark.parametrize("round_number", range(8))
def test_concurrent_submit_has_one_fake_winner(tmp_path: Path, round_number: int) -> None:
    del round_number
    first = _harness(tmp_path)
    second = _harness(tmp_path)
    results: list[d09.FakeProviderJournalReport] = []
    barrier = threading.Barrier(3)

    def invoke(harness: d09._D09TestOnlyHarness) -> None:
        barrier.wait()
        results.append(harness.submit_consumed_dispatch(_dispatch(), _profile(), d09.FakeSubmissionPlanV1(outcome="ACCEPTED")))

    threads = [threading.Thread(target=invoke, args=(harness,)) for harness in (first, second)]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join()
    assert sum(result.edge_invoked for result in results) == 1
    assert {result.status for result in results} <= {"ACCEPTED", "IN_PROGRESS"}
    assert all(result.status in get_args(d09.JournalStatus) for result in results)


def test_malformed_and_forged_classification_inputs_fail_closed(tmp_path: Path) -> None:
    harness = _harness(tmp_path)
    forged = d09.D09DispatchBindingV1.model_construct(dispatch_identity=_digest("forged"))
    assert harness.submit_consumed_dispatch(_dispatch(), forged, d09.FakeSubmissionPlanV1(outcome="ACCEPTED")).status == "CORRUPT"
    bad = _profile()
    bad["authorization"] = "Bearer test"
    assert harness.submit_consumed_dispatch(_dispatch(), bad, d09.FakeSubmissionPlanV1(outcome="ACCEPTED")).status == "CORRUPT"


def test_schema_missing_index_and_binding_corruption_fail_closed(tmp_path: Path) -> None:
    root = (tmp_path / "d09").resolve()
    harness = _harness(tmp_path)
    assert harness.submit_consumed_dispatch(_dispatch(), _profile(), d09.FakeSubmissionPlanV1(outcome="ACCEPTED")).status == "ACCEPTED"
    database = root / "fake_provider_receipts.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute("DROP INDEX d09_dispatch_identity_unique")
    with pytest.raises(ValueError, match="schema"):
        d09._LocalFakeProviderReceiptJournal(root)


def test_metadata_less_partial_database_fails_closed(tmp_path: Path) -> None:
    root = (tmp_path / "partial").resolve()
    root.mkdir()
    with sqlite3.connect(root / "fake_provider_receipts.sqlite3") as connection:
        connection.execute("CREATE TABLE d09_journals (value TEXT)")

    with pytest.raises(ValueError, match="schema"):
        d09._LocalFakeProviderReceiptJournal(root)


def test_same_named_non_unique_index_and_missing_primary_key_fail_closed(tmp_path: Path) -> None:
    root = (tmp_path / "schema").resolve()
    d09._LocalFakeProviderReceiptJournal(root)
    database = root / "fake_provider_receipts.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute("DROP INDEX d09_dispatch_identity_unique")
        connection.execute("CREATE INDEX d09_dispatch_identity_unique ON d09_journals(dispatch_identity)")
    with pytest.raises(ValueError, match="unique"):
        d09._LocalFakeProviderReceiptJournal(root)

    root = (tmp_path / "missing-pk").resolve()
    root.mkdir()
    with sqlite3.connect(root / "fake_provider_receipts.sqlite3") as connection:
        connection.execute("CREATE TABLE d09_schema_meta (version INTEGER NOT NULL)")
        connection.execute("INSERT INTO d09_schema_meta VALUES (1)")
        connection.execute(
            "CREATE TABLE d09_journals (journal_identity TEXT, dispatch_identity TEXT NOT NULL, "
            "binding_json TEXT NOT NULL, binding_digest TEXT NOT NULL, lifecycle TEXT NOT NULL, "
            "sequence INTEGER NOT NULL, receipt_json TEXT)"
        )
        connection.execute("CREATE UNIQUE INDEX d09_dispatch_identity_unique ON d09_journals(dispatch_identity)")
        connection.execute(
            "CREATE TABLE d09_journal_events (journal_identity TEXT NOT NULL, sequence INTEGER NOT NULL, "
            "lifecycle TEXT NOT NULL, event_json TEXT NOT NULL)"
        )
    with pytest.raises(ValueError, match="primary key"):
        d09._LocalFakeProviderReceiptJournal(root)


def test_oversized_identifiers_fail_before_durable_persistence(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="bounded"):
        d09.FakeSubmissionPlanV1(outcome="ACCEPTED", provider_job_identity="a" * 161)

    oversized_dispatch = _dispatch().model_copy(update={"attempt_id": "a" * 161})
    result = _harness(tmp_path).submit_consumed_dispatch(
        oversized_dispatch, _profile(), d09.FakeSubmissionPlanV1(outcome="ACCEPTED")
    )
    assert result.status == "CORRUPT"


def _accepted_journal(tmp_path: Path) -> tuple[d09._D09TestOnlyHarness, ProviderDispatchRequestV1, Path]:
    harness = _harness(tmp_path)
    dispatch = _dispatch()
    assert harness.submit_consumed_dispatch(dispatch, _profile(), d09.FakeSubmissionPlanV1(outcome="ACCEPTED")).status == "ACCEPTED"
    return harness, dispatch, (tmp_path / "d09" / "fake_provider_receipts.sqlite3").resolve()


def test_altered_receipt_digest_and_binding_fail_closed_on_replay(tmp_path: Path) -> None:
    harness, dispatch, database = _accepted_journal(tmp_path)
    with sqlite3.connect(database) as connection:
        receipt = json.loads(connection.execute("SELECT receipt_json FROM d09_journals").fetchone()[0])
        receipt["submission_evidence_digest"] = "f" * 64
        connection.execute("UPDATE d09_journals SET receipt_json = ?", (json.dumps(receipt),))
    assert harness.reopen_consumed_dispatch(dispatch, _profile()).status == "CORRUPT"
    assert not harness.submit_consumed_dispatch(dispatch, _profile(), d09.FakeSubmissionPlanV1(outcome="ACCEPTED")).edge_invoked

    harness, dispatch, database = _accepted_journal(tmp_path / "binding")
    with sqlite3.connect(database) as connection:
        receipt = json.loads(connection.execute("SELECT receipt_json FROM d09_journals").fetchone()[0])
        receipt["provider_class"] = "B"
        connection.execute("UPDATE d09_journals SET receipt_json = ?", (json.dumps(receipt),))
    assert harness.reopen_consumed_dispatch(dispatch, _profile()).status == "CORRUPT"


def test_every_replayed_event_is_validated_fail_closed(tmp_path: Path) -> None:
    harness, dispatch, database = _accepted_journal(tmp_path)
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE d09_journal_events SET event_json = ? WHERE sequence = 0", ("{}",))
    assert harness.reopen_consumed_dispatch(dispatch, _profile()).status == "CORRUPT"

    harness, dispatch, database = _accepted_journal(tmp_path / "digest")
    with sqlite3.connect(database) as connection:
        event = json.loads(connection.execute("SELECT event_json FROM d09_journal_events WHERE sequence = 0").fetchone()[0])
        event["event_payload_digest"] = "a" * 64
        connection.execute("UPDATE d09_journal_events SET event_json = ? WHERE sequence = 0", (json.dumps(event),))
    assert harness.reopen_consumed_dispatch(dispatch, _profile()).status == "CORRUPT"

    harness, dispatch, database = _accepted_journal(tmp_path / "gap")
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE d09_journal_events SET sequence = 3 WHERE sequence = 1")
    assert harness.reopen_consumed_dispatch(dispatch, _profile()).status == "CORRUPT"


def test_illegal_intermediate_transition_fails_closed(tmp_path: Path) -> None:
    harness, dispatch, database = _accepted_journal(tmp_path)
    with sqlite3.connect(database) as connection:
        binding = d09.D09DispatchBindingV1.model_validate_json(
            connection.execute("SELECT binding_json FROM d09_journals").fetchone()[0]
        )
        event = json.loads(connection.execute("SELECT event_json FROM d09_journal_events WHERE sequence = 1").fetchone()[0])
        event["lifecycle"] = "ACCEPTED"
        event["event_payload_digest"] = d09._event_payload_digest(binding, "ACCEPTED", 1)
        connection.execute(
            "UPDATE d09_journal_events SET lifecycle = ?, event_json = ? WHERE sequence = 1",
            ("ACCEPTED", json.dumps(event)),
        )
    assert harness.reopen_consumed_dispatch(dispatch, _profile()).status == "CORRUPT"


def test_private_d09_has_no_public_export_or_real_provider_surface() -> None:
    source = inspect.getsource(d09)
    assert not hasattr(manga_director, "ProviderSubmissionReceiptV1")
    assert not hasattr(production, "ProviderSubmissionReceiptV1")
    assert "requests" not in source
    assert "urllib" not in source
    assert "subprocess" not in source
    assert "socket" not in source
    assert "ProviderResultEvidenceV1" not in source
    assert tuple(inspect.signature(d09._LocalFileFakeProviderReceiptJournal).parameters) == ("repository",)


def test_localfile_owner_root_is_dedicated_and_not_the_workflow_ledger(tmp_path: Path) -> None:
    repository = LocalFileRepository(tmp_path / "repository")
    composition = d09._LocalFileFakeProviderReceiptJournal(repository)
    expected = repository._root.resolve() / "_durability" / "_future_durable_generation" / "provider_receipts"

    assert composition._core._journal._root == expected
    assert expected != repository._workflow_application_ledger_owner_root()
    assert tuple(inspect.signature(composition.submit).parameters) == (
        "manifest",
        "permit",
        "raw_provider_profile",
    )
    with pytest.raises(TypeError):
        composition.submit(dispatch=_dispatch(), raw_provider_profile=_profile())  # type: ignore[call-arg]


def test_receipt_rejects_secret_shaped_job_identity() -> None:
    with pytest.raises(ValueError, match="secret"):
        d09.FakeSubmissionPlanV1(outcome="ACCEPTED", provider_job_identity="token:secret")
