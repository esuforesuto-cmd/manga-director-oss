from __future__ import annotations

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from manga_director.production import future_external_provider_result_journal as d12i02
from manga_director.repositories.local_file import LocalFileRepository


def _source_database(repository: LocalFileRepository) -> str:
    database = d12i02._d12_i01_database(repository)
    database.parent.mkdir(parents=True)
    binding = {
        "schema_id": "manga_director.future_external_provider_submission_binding",
        "schema_version": "1",
        "dispatch_identity": "a" * 64,
        "idempotency_identity": "b" * 64,
        "attempt_id": "attempt-1",
        "project_id": "project-1",
        "page_id": "page-1",
        "target_page_reference": "page-ref-1",
        "manifest_digest": "c" * 64,
        "provider_binding_digest": "d" * 64,
        "attempt_binding_digest": "e" * 64,
        "profile_identity": "f" * 64,
        "provider_class": "A",
        "provider_reference": "provider-1",
        "request_digest": "1" * 64,
        "metadata_digest": "2" * 64,
    }
    journal_identity = d12i02._digest(binding)
    binding = {**binding, "journal_identity": journal_identity, "binding_digest": journal_identity}
    observation = {"kind": "ACCEPTED_IDENTIFIED", "provider_identity": "provider-job-1", "metadata": {}}
    connection = sqlite3.connect(database)
    try:
        connection.executescript(
            "CREATE TABLE external_submission_journal (journal_identity TEXT PRIMARY KEY, dispatch_identity TEXT NOT NULL, attempt_id TEXT NOT NULL, binding_json TEXT NOT NULL, binding_digest TEXT NOT NULL, phase TEXT NOT NULL, sequence INTEGER NOT NULL, terminal_observation_json TEXT, terminal_observation_digest TEXT);"
            "CREATE UNIQUE INDEX ux_external_submission_dispatch ON external_submission_journal(dispatch_identity);"
            "CREATE UNIQUE INDEX ux_external_submission_attempt ON external_submission_journal(attempt_id);"
            "CREATE TABLE external_submission_events (journal_identity TEXT NOT NULL, sequence INTEGER NOT NULL, phase TEXT NOT NULL, payload_json TEXT NOT NULL, payload_digest TEXT NOT NULL, PRIMARY KEY(journal_identity, sequence));"
            "CREATE INDEX ix_external_submission_events_phase ON external_submission_events(journal_identity, phase);"
        )
        connection.execute("PRAGMA user_version = 1")
        connection.execute(
            "INSERT INTO external_submission_journal VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (journal_identity, binding["dispatch_identity"], binding["attempt_id"], d12i02._canonical(binding), binding["binding_digest"], "ACCEPTED_IDENTIFIED", 3, d12i02._canonical(observation), d12i02._digest(observation)),
        )
        for sequence, phase, event_observation in (
            (0, "DISPATCH_CONSUMED", None),
            (1, "SUBMISSION_STARTED", None),
            (2, "EDGE_ISSUED", None),
            (3, "ACCEPTED_IDENTIFIED", observation),
        ):
            unsigned = {"schema_id": "manga_director.future_external_provider_submission_event", "schema_version": "1", "journal_identity": journal_identity, "binding_digest": binding["binding_digest"], "sequence": sequence, "phase": phase, "observation": event_observation}
            event = {**unsigned, "event_digest": d12i02._digest(unsigned)}
            connection.execute("INSERT INTO external_submission_events VALUES (?, ?, ?, ?, ?)", (journal_identity, sequence, phase, d12i02._canonical(event), event["event_digest"]))
        connection.commit()
    finally:
        connection.close()
    return journal_identity


def _assert_source_ineligible(repository: LocalFileRepository, submission: str) -> None:
    with pytest.raises(ValueError):
        d12i02._read_accepted_source(repository, submission)


def _event_count(repository: LocalFileRepository) -> int:
    connection = sqlite3.connect(d12i02._d12_i02_database(repository))
    try:
        return int(connection.execute("SELECT COUNT(*) FROM external_result_events").fetchone()[0])
    finally:
        connection.close()


def _canonical_candidate(output: d12i02.OutputEvidenceV1) -> d12i02.PostAcceptCandidateProjectionV1:
    return d12i02.PostAcceptCandidateProjectionV1(
        provider_reference="provider-1",
        provider_job_identity="provider-job-1",
        provenance_assurance="UNVERIFIED",
        outputs=(output,),
    )


def test_frozen_owner_paths_are_exact_and_separate(tmp_path) -> None:
    repository = LocalFileRepository(tmp_path / "repository")
    assert d12i02._d12_i01_database(repository) == repository._root.resolve() / "_durability" / "_future_durable_generation" / "external_provider_submission" / "external-provider-submission.sqlite3"
    assert d12i02._d12_i02_database(repository) == repository._root.resolve() / "_durability" / "_future_durable_generation" / "external_provider_result_evidence" / "external-provider-result-evidence.sqlite3"


def test_result_owner_rejects_target_collision(tmp_path) -> None:
    repository = LocalFileRepository(tmp_path / "repository")
    target = repository._root / "_durability" / "_future_durable_generation" / "external_provider_result_evidence"
    target.parent.mkdir(parents=True)
    target.write_text("collision", encoding="utf-8")
    try:
        d12i02._d12_i02_database(repository)
    except ValueError:
        pass
    else:
        raise AssertionError("collision was accepted")


def test_normal_capture_is_started_then_captured_atomically(tmp_path) -> None:
    repository = LocalFileRepository(tmp_path / "repository")
    submission = _source_database(repository)
    journal = d12i02.LocalFileExternalProviderResultJournal(repository)
    started, capability = journal.start(submission)
    assert started.status == "RESULT_CAPTURE_STARTED" and capability is not None
    output = d12i02.OutputEvidenceV1(
        logical_output_id="output-1",
        sha256="3" * 64,
        media_type="image/png",
        byte_length=1,
        metadata={"label": "synthetic"},
        metadata_digest=d12i02._digest({"label": "synthetic"}),
    )
    captured = journal.capture(capability, d12i02.AcceptedObservationInputV1(outputs=(output,)))
    assert captured.status == "RESULT_CAPTURED" and captured.evidence is not None
    assert journal.reopen(submission).status == "RESULT_CAPTURED"
    connection = sqlite3.connect(d12i02._d12_i02_database(repository))
    try:
        assert connection.execute("SELECT COUNT(*) FROM external_result_events").fetchone()[0] == 3
        assert connection.execute("SELECT COUNT(*) FROM external_result_accepted_results").fetchone()[0] == 1
    finally:
        connection.close()


def test_normal_capability_is_non_serializable_and_tombstoned(tmp_path) -> None:
    repository = LocalFileRepository(tmp_path / "repository")
    submission = _source_database(repository)
    journal = d12i02.LocalFileExternalProviderResultJournal(repository)
    _, capability = journal.start(submission)
    assert capability is not None
    try:
        capability.__reduce__()
    except TypeError:
        pass
    else:
        raise AssertionError("capability was serializable")
    assert journal.capture(capability, object()).status == "CORRUPT"
    assert journal.capture(capability, object()).status == "RESULT_NOT_AVAILABLE"


def test_rejected_and_ambiguous_inputs_close_the_normal_lifecycle(tmp_path) -> None:
    for number, observation, status in (
        (3, d12i02.RejectedObservationInputV1(rejection_code="SYNTHETIC_REJECTED"), "RESULT_REJECTED"),
        (4, d12i02.AmbiguousObservationInputV1(reason_code="SYNTHETIC_OBSERVATION_AMBIGUOUS"), "RESULT_AMBIGUOUS"),
    ):
        repository = LocalFileRepository(tmp_path / f"repository-{number}")
        submission = _source_database(repository)
        journal = d12i02.LocalFileExternalProviderResultJournal(repository)
        _, capability = journal.start(submission)
        assert capability is not None
        assert journal.capture(capability, observation).status == status
        assert journal.reopen(submission).status == status


def test_reopen_of_committed_start_requires_recovery(tmp_path) -> None:
    repository = LocalFileRepository(tmp_path / "repository")
    submission = _source_database(repository)
    journal = d12i02.LocalFileExternalProviderResultJournal(repository)
    started, capability = journal.start(submission)
    assert started.status == "RESULT_CAPTURE_STARTED" and capability is not None
    reopened = d12i02.LocalFileExternalProviderResultJournal(repository)
    assert reopened.reopen(submission).status == "RECOVERY_REQUIRED"


def test_event_digest_tampering_fails_closed_on_reopen(tmp_path) -> None:
    repository = LocalFileRepository(tmp_path / "repository")
    submission = _source_database(repository)
    journal = d12i02.LocalFileExternalProviderResultJournal(repository)
    _, capability = journal.start(submission)
    assert capability is not None
    assert journal.capture(capability, d12i02.RejectedObservationInputV1(rejection_code="SYNTHETIC_REJECTED")).status == "RESULT_REJECTED"
    connection = sqlite3.connect(d12i02._d12_i02_database(repository))
    try:
        connection.execute("UPDATE external_result_events SET event_digest=? WHERE sequence=1", ("0" * 64,))
        connection.commit()
    finally:
        connection.close()
    assert journal.reopen(submission).status == "CORRUPT"


def _accepted_journal(tmp_path):
    repository = LocalFileRepository(tmp_path / "repository")
    submission = _source_database(repository)
    journal = d12i02.LocalFileExternalProviderResultJournal(repository)
    _, capability = journal.start(submission)
    assert capability is not None
    output = d12i02.OutputEvidenceV1(
        logical_output_id="output-1",
        sha256="3" * 64,
        media_type="image/png",
        byte_length=1,
        metadata={"label": "synthetic"},
        metadata_digest=d12i02._digest({"label": "synthetic"}),
    )
    assert journal.capture(capability, d12i02.AcceptedObservationInputV1(outputs=(output,))).status == "RESULT_CAPTURED"
    return journal, submission, output


def test_equivalent_post_accept_audit_preserves_acceptance(tmp_path) -> None:
    journal, submission, output = _accepted_journal(tmp_path)
    started, capability = journal.issue_post_accept_audit(submission)
    assert started.status == "POST_ACCEPT_AUDIT_STARTED" and capability is not None
    candidate = d12i02.PostAcceptCandidateProjectionV1(
        provider_reference="provider-1",
        provider_job_identity="provider-job-1",
        provenance_assurance="UNVERIFIED",
        outputs=(output,),
    )
    assert journal.audit(capability, candidate).status == "RESULT_CAPTURED"
    assert journal.reopen(submission).status == "RESULT_CAPTURED"


def test_conflicting_post_accept_audit_closes_ambiguously(tmp_path) -> None:
    journal, submission, output = _accepted_journal(tmp_path)
    _, capability = journal.issue_post_accept_audit(submission)
    assert capability is not None
    changed = output.model_copy(update={"sha256": "4" * 64})
    candidate = d12i02.PostAcceptCandidateProjectionV1(
        provider_reference="provider-1",
        provider_job_identity="provider-job-1",
        provenance_assurance="UNVERIFIED",
        outputs=(changed,),
    )
    assert journal.audit(capability, candidate).status == "RESULT_AMBIGUOUS"
    assert journal.reopen(submission).status == "RESULT_AMBIGUOUS"


def test_audit_capability_is_separate_nonserializable_and_one_shot(tmp_path) -> None:
    journal, submission, output = _accepted_journal(tmp_path)
    _, normal = journal.start(submission)
    assert normal is None
    started, audit = journal.issue_post_accept_audit(submission)
    assert started.status == "POST_ACCEPT_AUDIT_STARTED" and audit is not None
    try:
        audit.__reduce__()
    except TypeError:
        pass
    else:
        raise AssertionError("audit capability was serializable")
    assert journal.capture(audit, object()).status == "RESULT_NOT_AVAILABLE"
    assert journal.audit(audit, object()).status == "RESULT_AMBIGUOUS"
    assert journal.audit(audit, object()).status == "RESULT_NOT_AVAILABLE"


def test_malformed_audit_closes_without_persisting_candidate(tmp_path) -> None:
    journal, submission, _ = _accepted_journal(tmp_path)
    _, audit = journal.issue_post_accept_audit(submission)
    assert audit is not None
    assert journal.audit(audit, {"not": "a candidate"}).status == "RESULT_AMBIGUOUS"
    assert journal.reopen(submission).status == "RESULT_AMBIGUOUS"


def test_d12_i01_intermediate_event_tampering_is_ineligible(tmp_path) -> None:
    repository = LocalFileRepository(tmp_path / "repository")
    submission = _source_database(repository)
    connection = sqlite3.connect(d12i02._d12_i01_database(repository))
    try:
        connection.execute("UPDATE external_submission_events SET payload_digest=? WHERE sequence=1", ("0" * 64,))
        connection.commit()
    finally:
        connection.close()
    try:
        d12i02._read_accepted_source(repository, submission)
    except ValueError:
        pass
    else:
        raise AssertionError("tampered D12-I01 event was accepted")


def test_d12_i01_terminal_identity_and_sequence_tampering_are_ineligible(tmp_path) -> None:
    repository = LocalFileRepository(tmp_path / "repository")
    submission = _source_database(repository)
    database = d12i02._d12_i01_database(repository)
    connection = sqlite3.connect(database)
    try:
        connection.execute("UPDATE external_submission_journal SET sequence=2 WHERE journal_identity=?", (submission,))
        connection.commit()
    finally:
        connection.close()
    try:
        d12i02._read_accepted_source(repository, submission)
    except ValueError:
        pass
    else:
        raise AssertionError("tampered D12-I01 sequence was accepted")


def test_forged_audit_capability_has_no_authority(tmp_path) -> None:
    journal, submission, _ = _accepted_journal(tmp_path)
    _, issued = journal.issue_post_accept_audit(submission)
    assert issued is not None
    forged = d12i02._PostAcceptAuditCapability(issued.journal, issued.receipt, issued.evidence, issued.sequence, issued.nonce)
    assert journal.audit(forged, object()).status == "RESULT_NOT_AVAILABLE"
    assert journal.audit(issued, object()).status == "RESULT_AMBIGUOUS"


def test_audit_start_reopens_as_recovery_required(tmp_path) -> None:
    journal, submission, _ = _accepted_journal(tmp_path)
    started, capability = journal.issue_post_accept_audit(submission)
    assert started.status == "POST_ACCEPT_AUDIT_STARTED" and capability is not None
    reopened = d12i02.LocalFileExternalProviderResultJournal(journal._repository)
    assert reopened.reopen(submission).status == "RECOVERY_REQUIRED"


def test_conflict_difference_code_tampering_fails_closed(tmp_path) -> None:
    journal, submission, output = _accepted_journal(tmp_path)
    _, capability = journal.issue_post_accept_audit(submission)
    assert capability is not None
    candidate = d12i02.PostAcceptCandidateProjectionV1(provider_reference="provider-1", provider_job_identity="provider-job-1", provenance_assurance="UNVERIFIED", outputs=(output.model_copy(update={"sha256": "4" * 64}),))
    assert journal.audit(capability, candidate).status == "RESULT_AMBIGUOUS"
    connection = sqlite3.connect(d12i02._d12_i02_database(journal._repository))
    try:
        row = connection.execute("SELECT event_json FROM external_result_events WHERE sequence=4").fetchone()
        event = __import__("json").loads(row[0])
        event["payload"]["difference_codes"] = []
        event["payload_digest"] = d12i02._digest(event["payload"])
        unsigned = {key: value for key, value in event.items() if key != "event_digest"}
        event["event_digest"] = d12i02._digest(unsigned)
        connection.execute("UPDATE external_result_events SET event_json=?,event_digest=? WHERE sequence=4", (d12i02._canonical(event), event["event_digest"]))
        connection.execute("UPDATE external_result_state SET last_event_digest=?", (event["event_digest"],))
        connection.commit()
    finally:
        connection.close()
    assert journal.reopen(submission).status == "CORRUPT"


def test_invalid_provenance_routes_to_bounded_malformed_code(tmp_path) -> None:
    journal, submission, output = _accepted_journal(tmp_path)
    _, capability = journal.issue_post_accept_audit(submission)
    assert capability is not None
    candidate = {"provider_reference": "provider-1", "provider_job_identity": "provider-job-1", "provenance_assurance": "AUTHENTICATED", "outputs": [output.model_dump(mode="json")]}
    assert journal.audit(capability, candidate).status == "RESULT_AMBIGUOUS"
    connection = sqlite3.connect(d12i02._d12_i02_database(journal._repository))
    try:
        payload = __import__("json").loads(connection.execute("SELECT event_json FROM external_result_events WHERE sequence=4").fetchone()[0])["payload"]
        assert payload == {"accepted_evidence_identity": payload["accepted_evidence_identity"], "failure_code": "INVALID_PROVENANCE"}
    finally:
        connection.close()


@pytest.mark.parametrize(
    "mutation",
    (
        "missing_event",
        "sequence_gap",
        "unexpected_phase",
        "extra_previous_digest",
        "payload_digest",
        "event_digest",
        "malformed_json",
        "binding_json",
        "binding_digest",
        "dispatch_mismatch",
        "terminal_observation_digest",
        "schema_index",
    ),
)
def test_d12_i01_corruption_matrix_is_fail_closed(tmp_path, mutation: str) -> None:
    repository = LocalFileRepository(tmp_path / mutation)
    submission = _source_database(repository)
    database = d12i02._d12_i01_database(repository)
    connection = sqlite3.connect(database)
    try:
        if mutation == "missing_event":
            connection.execute("DELETE FROM external_submission_events WHERE sequence=1")
        elif mutation == "sequence_gap":
            connection.execute("UPDATE external_submission_events SET sequence=4 WHERE sequence=3")
        elif mutation == "unexpected_phase":
            connection.execute("UPDATE external_submission_events SET phase='REJECTED' WHERE sequence=1")
        elif mutation == "extra_previous_digest":
            event = json.loads(connection.execute("SELECT payload_json FROM external_submission_events WHERE sequence=1").fetchone()[0])
            event["previous_event_digest"] = "0" * 64
            connection.execute("UPDATE external_submission_events SET payload_json=? WHERE sequence=1", (d12i02._canonical(event),))
        elif mutation == "payload_digest":
            connection.execute("UPDATE external_submission_events SET payload_digest=? WHERE sequence=1", ("0" * 64,))
        elif mutation == "event_digest":
            event = json.loads(connection.execute("SELECT payload_json FROM external_submission_events WHERE sequence=1").fetchone()[0])
            event["event_digest"] = "0" * 64
            connection.execute("UPDATE external_submission_events SET payload_json=?,payload_digest=? WHERE sequence=1", (d12i02._canonical(event), event["event_digest"]))
        elif mutation == "malformed_json":
            connection.execute("UPDATE external_submission_events SET payload_json='{' WHERE sequence=1")
        elif mutation == "binding_json":
            connection.execute("UPDATE external_submission_journal SET binding_json='{}' WHERE journal_identity=?", (submission,))
        elif mutation == "binding_digest":
            connection.execute("UPDATE external_submission_journal SET binding_digest=? WHERE journal_identity=?", ("0" * 64, submission))
        elif mutation == "dispatch_mismatch":
            connection.execute("UPDATE external_submission_journal SET dispatch_identity=? WHERE journal_identity=?", ("f" * 64, submission))
        elif mutation == "terminal_observation_digest":
            connection.execute("UPDATE external_submission_journal SET terminal_observation_digest=? WHERE journal_identity=?", ("0" * 64, submission))
        else:
            connection.execute("CREATE INDEX unexpected_source_index ON external_submission_events(phase)")
        connection.commit()
    finally:
        connection.close()
    _assert_source_ineligible(repository, submission)


@pytest.mark.parametrize("phase", ("REJECTED", "FAILED_PRE_SEND", "RECOVERY_REQUIRED", "EDGE_ISSUED"))
def test_d12_i01_nonaccepted_terminal_histories_are_ineligible(tmp_path, phase: str) -> None:
    repository = LocalFileRepository(tmp_path / phase)
    submission = _source_database(repository)
    connection = sqlite3.connect(d12i02._d12_i01_database(repository))
    try:
        connection.execute("UPDATE external_submission_journal SET phase=? WHERE journal_identity=?", (phase, submission))
        connection.commit()
    finally:
        connection.close()
    _assert_source_ineligible(repository, submission)


def test_normal_capability_forgery_matrix_has_no_durable_authority(tmp_path) -> None:
    repository = LocalFileRepository(tmp_path / "repository")
    submission = _source_database(repository)
    journal = d12i02.LocalFileExternalProviderResultJournal(repository)
    _, issued = journal.start(submission)
    assert issued is not None
    baseline = _event_count(repository)

    class _Subclass(d12i02._ResultObservationCapability):
        pass

    forged = (
        d12i02._ResultObservationCapability(issued.journal, issued.receipt, issued.sequence, issued.nonce),
        _Subclass(issued.journal, issued.receipt, issued.sequence, issued.nonce),
        d12i02._ResultObservationCapability("0" * 64, issued.receipt, issued.sequence, issued.nonce),
        d12i02._ResultObservationCapability(issued.journal, "0" * 64, issued.sequence, issued.nonce),
        d12i02._ResultObservationCapability(issued.journal, issued.receipt, issued.sequence + 1, issued.nonce),
    )
    for token in forged:
        assert journal.capture(token, object()).status == "RESULT_NOT_AVAILABLE"
        assert _event_count(repository) == baseline
    assert journal.capture(issued, object()).status == "CORRUPT"
    assert journal.capture(issued, object()).status == "RESULT_NOT_AVAILABLE"
    assert _event_count(repository) == baseline


def test_audit_capability_forgery_matrix_has_no_durable_authority(tmp_path) -> None:
    journal, submission, output = _accepted_journal(tmp_path)
    _, issued = journal.issue_post_accept_audit(submission)
    assert issued is not None
    baseline = _event_count(journal._repository)

    class _Subclass(d12i02._PostAcceptAuditCapability):
        pass

    forged = (
        d12i02._PostAcceptAuditCapability(issued.journal, issued.receipt, issued.evidence, issued.sequence, issued.nonce),
        _Subclass(issued.journal, issued.receipt, issued.evidence, issued.sequence, issued.nonce),
        d12i02._PostAcceptAuditCapability("0" * 64, issued.receipt, issued.evidence, issued.sequence, issued.nonce),
        d12i02._PostAcceptAuditCapability(issued.journal, "0" * 64, issued.evidence, issued.sequence, issued.nonce),
        d12i02._PostAcceptAuditCapability(issued.journal, issued.receipt, "0" * 64, issued.sequence, issued.nonce),
        d12i02._PostAcceptAuditCapability(issued.journal, issued.receipt, issued.evidence, issued.sequence + 1, issued.nonce),
    )
    for token in forged:
        assert journal.audit(token, object()).status == "RESULT_NOT_AVAILABLE"
        assert _event_count(journal._repository) == baseline
    assert journal.audit(issued, _canonical_candidate(output)).status == "RESULT_CAPTURED"
    assert journal.audit(issued, _canonical_candidate(output)).status == "RESULT_NOT_AVAILABLE"


@pytest.mark.parametrize("mutation", ("completion_without_start", "wrong_completion_sequence", "extra_difference", "unsorted_difference", "wrong_candidate_digest", "unknown_malformed_code", "accepted_row"))
def test_audit_replay_corruption_matrix_is_fail_closed(tmp_path, mutation: str) -> None:
    journal, submission, output = _accepted_journal(tmp_path)
    _, capability = journal.issue_post_accept_audit(submission)
    assert capability is not None
    changed = _canonical_candidate(output.model_copy(update={"sha256": "4" * 64, "media_type": "image/jpeg"}))
    assert journal.audit(capability, changed).status == "RESULT_AMBIGUOUS"
    database = d12i02._d12_i02_database(journal._repository)
    connection = sqlite3.connect(database)
    try:
        if mutation == "accepted_row":
            connection.execute("UPDATE external_result_accepted_results SET evidence_digest=?", ("0" * 64,))
        else:
            row = connection.execute("SELECT event_json FROM external_result_events WHERE sequence=4").fetchone()
            event = json.loads(row[0])
            if mutation == "completion_without_start":
                event["event_type"] = "POST_ACCEPT_EQUIVALENT_RECORDED"
                event["payload"] = {"accepted_evidence_identity": event["payload"]["accepted_evidence_identity"], "candidate_canonical_result_identity": event["payload"]["accepted_canonical_result_identity"], "comparison_result": "EQUIVALENT"}
            elif mutation == "wrong_completion_sequence":
                event["sequence"] = 7
            elif mutation == "extra_difference":
                event["payload"]["difference_codes"].append("EXTRA")
            elif mutation == "unsorted_difference":
                event["payload"]["difference_codes"] = list(reversed(event["payload"]["difference_codes"]))
            elif mutation == "wrong_candidate_digest":
                event["payload"]["candidate_projection_digest"] = "0" * 64
            else:
                event["event_type"] = "POST_ACCEPT_MALFORMED_RECORDED"
                event["payload"] = {"accepted_evidence_identity": event["payload"]["accepted_evidence_identity"], "failure_code": "UNKNOWN"}
            event["payload_digest"] = d12i02._digest(event["payload"])
            unsigned = {key: value for key, value in event.items() if key != "event_digest"}
            event["event_digest"] = d12i02._digest(unsigned)
            connection.execute("UPDATE external_result_events SET sequence=?,event_type=?,event_json=?,event_digest=? WHERE sequence=4", (event["sequence"], event["event_type"], d12i02._canonical(event), event["event_digest"]))
            if mutation != "wrong_completion_sequence":
                connection.execute("UPDATE external_result_state SET last_event_digest=?", (event["event_digest"],))
        connection.commit()
    finally:
        connection.close()
    assert journal.reopen(submission).status == "CORRUPT"


def test_audit_capacity_preserves_the_last_complete_pair(tmp_path) -> None:
    journal, submission, output = _accepted_journal(tmp_path)
    candidate = _canonical_candidate(output)
    for _ in range(13):
        started, capability = journal.issue_post_accept_audit(submission)
        assert started.status == "POST_ACCEPT_AUDIT_STARTED" and capability is not None
        assert journal.audit(capability, candidate).status == "RESULT_CAPTURED"
    assert _event_count(journal._repository) == 29
    started, capability = journal.issue_post_accept_audit(submission)
    assert started.status == "POST_ACCEPT_AUDIT_STARTED" and capability is not None
    assert _event_count(journal._repository) == 30
    assert journal.audit(capability, candidate).status == "RESULT_CAPTURED"
    assert _event_count(journal._repository) == 31
    blocked, unavailable = journal.issue_post_accept_audit(submission)
    assert blocked.status == "AUDIT_EVENT_CAPACITY_EXHAUSTED" and unavailable is None
    assert _event_count(journal._repository) == 31


@pytest.mark.parametrize(
    ("candidate", "code"),
    (
        ({}, "INVALID_CANDIDATE_STRUCTURE"),
        ({"provider_reference": "provider-1", "provider_job_identity": "provider-job-1", "provenance_assurance": "AUTHENTICATED", "outputs": []}, "INVALID_PROVENANCE"),
        ({"provider_reference": "provider-1", "provider_job_identity": "provider-job-1", "provenance_assurance": "UNVERIFIED", "outputs": []}, "INVALID_OUTPUT_SET"),
        ({"provider_reference": "provider-1", "provider_job_identity": "provider-job-1", "provenance_assurance": "UNVERIFIED", "outputs": [{"logical_output_id": "../bad", "sha256": "3" * 64, "media_type": "image/png", "byte_length": 1, "metadata": {}, "metadata_digest": d12i02._digest({})}]}, "INVALID_LOGICAL_OUTPUT_ID"),
        ({"provider_reference": "provider-1", "provider_job_identity": "provider-job-1", "provenance_assurance": "UNVERIFIED", "outputs": [{"logical_output_id": "good", "sha256": "Z" * 64, "media_type": "image/png", "byte_length": 1, "metadata": {}, "metadata_digest": d12i02._digest({})}]}, "INVALID_SHA256"),
    ),
)
def test_malformed_audit_codes_are_bounded_and_do_not_store_input(tmp_path, candidate: object, code: str) -> None:
    journal, submission, _ = _accepted_journal(tmp_path)
    _, capability = journal.issue_post_accept_audit(submission)
    assert capability is not None
    assert journal.audit(capability, candidate).status == "RESULT_AMBIGUOUS"
    connection = sqlite3.connect(d12i02._d12_i02_database(journal._repository))
    try:
        payload = json.loads(connection.execute("SELECT event_json FROM external_result_events WHERE sequence=4").fetchone()[0])["payload"]
        assert payload["failure_code"] == code
        assert set(payload) == {"accepted_evidence_identity", "failure_code"}
    finally:
        connection.close()


def test_concurrent_normal_consumption_has_one_durable_winner(tmp_path) -> None:
    repository = LocalFileRepository(tmp_path / "repository")
    submission = _source_database(repository)
    journal = d12i02.LocalFileExternalProviderResultJournal(repository)
    _, capability = journal.start(submission)
    assert capability is not None
    output = d12i02.OutputEvidenceV1(logical_output_id="output-1", sha256="3" * 64, media_type="image/png", byte_length=1, metadata={"label": "synthetic"}, metadata_digest=d12i02._digest({"label": "synthetic"}))
    with ThreadPoolExecutor(max_workers=2) as executor:
        reports = tuple(executor.map(lambda _: journal.capture(capability, d12i02.AcceptedObservationInputV1(outputs=(output,))), range(2)))
    assert sorted(report.status for report in reports) == ["RESULT_CAPTURED", "RESULT_NOT_AVAILABLE"]
    assert _event_count(repository) == 3
    assert journal.reopen(submission).status == "RESULT_CAPTURED"


def test_concurrent_audit_issuance_and_consumption_have_one_winner(tmp_path) -> None:
    journal, submission, output = _accepted_journal(tmp_path)
    with ThreadPoolExecutor(max_workers=2) as executor:
        issued = tuple(executor.map(lambda _: journal.issue_post_accept_audit(submission), range(2)))
    available = [(report, token) for report, token in issued if token is not None]
    assert len(available) == 1
    assert sorted(report.status for report, _ in issued) == ["CORRUPT", "POST_ACCEPT_AUDIT_STARTED"]
    capability = available[0][1]
    assert capability is not None
    candidate = _canonical_candidate(output)
    with ThreadPoolExecutor(max_workers=2) as executor:
        reports = tuple(executor.map(lambda _: journal.audit(capability, candidate), range(2)))
    assert sorted(report.status for report in reports) == ["RESULT_CAPTURED", "RESULT_NOT_AVAILABLE"]
    assert journal.reopen(submission).status == "RESULT_CAPTURED"


def test_consumed_normal_capability_is_not_reissued_after_sqlite_failure(tmp_path, monkeypatch) -> None:
    repository = LocalFileRepository(tmp_path / "repository")
    submission = _source_database(repository)
    journal = d12i02.LocalFileExternalProviderResultJournal(repository)
    _, capability = journal.start(submission)
    assert capability is not None
    original = journal._connect
    monkeypatch.setattr(journal, "_connect", lambda: (_ for _ in ()).throw(sqlite3.OperationalError("synthetic")))
    assert journal.capture(capability, object()).status == "CORRUPT"
    monkeypatch.setattr(journal, "_connect", original)
    report, replacement = journal.start(submission)
    assert report.status == "RECOVERY_REQUIRED" and replacement is None
    assert journal.capture(capability, object()).status == "RESULT_NOT_AVAILABLE"


def test_consumed_audit_capability_is_not_reissued_after_sqlite_failure(tmp_path, monkeypatch) -> None:
    journal, submission, _ = _accepted_journal(tmp_path)
    _, capability = journal.issue_post_accept_audit(submission)
    assert capability is not None
    original = journal._connect
    monkeypatch.setattr(journal, "_connect", lambda: (_ for _ in ()).throw(sqlite3.OperationalError("synthetic")))
    assert journal.audit(capability, object()).status == "CORRUPT"
    monkeypatch.setattr(journal, "_connect", original)
    report, replacement = journal.issue_post_accept_audit(submission)
    assert report.status == "CORRUPT" and replacement is None
    assert journal.audit(capability, object()).status == "RESULT_NOT_AVAILABLE"


@pytest.mark.parametrize("failure_code", ("SYNTHETIC_MALFORMED", "INVALID_OUTPUT", "INVALID_METADATA"))
def test_normal_malformed_codes_close_with_only_a_bounded_code(tmp_path, failure_code: str) -> None:
    repository = LocalFileRepository(tmp_path / failure_code)
    submission = _source_database(repository)
    journal = d12i02.LocalFileExternalProviderResultJournal(repository)
    _, capability = journal.start(submission)
    assert capability is not None
    report = journal.capture(capability, d12i02.MalformedObservationInputV1(failure_code=failure_code))
    assert report.status == "RESULT_MALFORMED"
    connection = sqlite3.connect(d12i02._d12_i02_database(repository))
    try:
        event = json.loads(connection.execute("SELECT event_json FROM external_result_events WHERE sequence=1").fetchone()[0])
        assert event["payload"] == {"failure_code": failure_code}
        assert connection.execute("SELECT COUNT(*) FROM external_result_accepted_results").fetchone()[0] == 0
    finally:
        connection.close()


def _initialized_result_database(tmp_path, name: str) -> tuple[LocalFileRepository, Path]:
    repository = LocalFileRepository(tmp_path / name)
    d12i02.LocalFileExternalProviderResultJournal(repository)
    return repository, d12i02._d12_i02_database(repository)


_ALTERED_SCHEMA_STATEMENTS = {
    "wrong_type": ("DROP TABLE external_result_state", "CREATE TABLE external_result_state (result_journal_identity TEXT NOT NULL PRIMARY KEY, phase INTEGER NOT NULL, availability_gate TEXT NOT NULL, sequence INTEGER NOT NULL, last_event_digest TEXT NOT NULL)"),
    "nullable": ("DROP TABLE external_result_state", "CREATE TABLE external_result_state (result_journal_identity TEXT NOT NULL PRIMARY KEY, phase TEXT, availability_gate TEXT NOT NULL, sequence INTEGER NOT NULL, last_event_digest TEXT NOT NULL)"),
    "default": ("DROP TABLE external_result_state", "CREATE TABLE external_result_state (result_journal_identity TEXT NOT NULL PRIMARY KEY, phase TEXT NOT NULL DEFAULT 'x', availability_gate TEXT NOT NULL, sequence INTEGER NOT NULL, last_event_digest TEXT NOT NULL)"),
    "missing_pk": ("DROP TABLE external_result_state", "CREATE TABLE external_result_state (result_journal_identity TEXT NOT NULL, phase TEXT NOT NULL, availability_gate TEXT NOT NULL, sequence INTEGER NOT NULL, last_event_digest TEXT NOT NULL)"),
    "wrong_pk_ordinal": ("DROP TABLE external_result_events", "CREATE TABLE external_result_events (result_journal_identity TEXT NOT NULL, sequence INTEGER NOT NULL, event_type TEXT NOT NULL, event_json TEXT NOT NULL, event_digest TEXT NOT NULL, PRIMARY KEY (result_journal_identity, sequence, event_type))"),
    "reversed_event_pk": ("DROP TABLE external_result_events", "CREATE TABLE external_result_events (result_journal_identity TEXT NOT NULL, sequence INTEGER NOT NULL, event_type TEXT NOT NULL, event_json TEXT NOT NULL, event_digest TEXT NOT NULL, PRIMARY KEY (sequence, result_journal_identity))"),
    "unexpected_column": ("ALTER TABLE external_result_state ADD COLUMN unexpected TEXT",),
    "missing_index": ("DROP INDEX ux_external_result_binding_submission_journal",),
    "nonunique_index": ("DROP INDEX ux_external_result_binding_submission_journal", "CREATE INDEX ux_external_result_binding_submission_journal ON external_result_bindings(submission_journal_identity)"),
    "partial_index": ("DROP INDEX ux_external_result_binding_submission_journal", "CREATE UNIQUE INDEX ux_external_result_binding_submission_journal ON external_result_bindings(submission_journal_identity) WHERE submission_journal_identity IS NOT NULL"),
    "wrong_index_column": ("DROP INDEX ux_external_result_binding_submission_journal", "CREATE UNIQUE INDEX ux_external_result_binding_submission_journal ON external_result_bindings(submission_receipt_identity)"),
    "extra_index": ("CREATE INDEX unexpected_result_index ON external_result_state(phase)",),
    "user_version": ("PRAGMA user_version = 2",),
    "schema_meta": ("UPDATE external_result_schema_meta SET schema_version=2",),
    "extra_table": ("CREATE TABLE unexpected_result_table (id TEXT)",),
    "extra_view": ("CREATE VIEW unexpected_result_view AS SELECT * FROM external_result_state",),
    "extra_trigger": ("CREATE TRIGGER unexpected_result_trigger AFTER INSERT ON external_result_state BEGIN SELECT 1; END",),
}


@pytest.mark.parametrize(
    "mutation",
    (
        "wrong_type",
        "nullable",
        "default",
        "missing_pk",
        "wrong_pk_ordinal",
        "reversed_event_pk",
        "unexpected_column",
        "missing_index",
        "nonunique_index",
        "partial_index",
        "wrong_index_column",
        "extra_index",
        "user_version",
        "schema_meta",
        "extra_table",
        "extra_view",
        "extra_trigger",
    ),
)
def test_constructor_rejects_every_altered_existing_schema(tmp_path, mutation: str) -> None:
    repository, database = _initialized_result_database(tmp_path, mutation)
    connection = sqlite3.connect(database)
    try:
        for statement in _ALTERED_SCHEMA_STATEMENTS[mutation]:
            connection.execute(statement)
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(ValueError):
        d12i02.LocalFileExternalProviderResultJournal(repository)


def test_valid_existing_frozen_schema_reopens_without_mutation(tmp_path) -> None:
    repository, database = _initialized_result_database(tmp_path, "valid")
    before = database.read_bytes()
    d12i02.LocalFileExternalProviderResultJournal(repository)
    assert database.read_bytes() == before
