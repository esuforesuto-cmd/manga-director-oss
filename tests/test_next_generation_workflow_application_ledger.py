"""Focused tests for the private Workflow Application Ledger sidecar."""

from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from manga_director.production.next_generation_durable_evidence_workflow_binding import (
    DurableEvidenceWorkflowBindingReport,
    WorkflowApplicationAuthorizationDTO,
)
from manga_director.production.next_generation_workflow_application_ledger import (
    LocalWorkflowApplicationLedgerStore,
    WorkflowApplicationLedgerBindingDTO,
    WorkflowApplicationLedgerService,
    _authoritative_commit_proof,
)

_ATTEMPT = "attempt:workflow:001"
_AUTHORIZATION = "workflow-authorization:001"
_PROJECT = "project:001"
_PAGE = "1"
_TARGET = "page:001"
_PROVIDER = "provider:openai"
_OUTPUT = "asset:generated:001"


def _authorization(**updates: object) -> WorkflowApplicationAuthorizationDTO:
    values: dict[str, object] = {
        "authorization_id": _AUTHORIZATION,
        "authorizer_id": "human:001",
        "authorized_at": datetime(2026, 8, 22, 18, 0, tzinfo=UTC),
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


def _binding_report(**updates: object) -> DurableEvidenceWorkflowBindingReport:
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


def _prepare(
    service: WorkflowApplicationLedgerService,
    store: LocalWorkflowApplicationLedgerStore,
    **updates: object,
):
    authorization_updates = updates.pop("authorization", {})
    report_updates = updates.pop("report", {})
    assert not updates
    return service.prepare(
        _binding_report(**report_updates),
        _authorization(**authorization_updates),
        store,
    )


def _binding() -> WorkflowApplicationLedgerBindingDTO:
    return WorkflowApplicationLedgerBindingDTO(
        attempt_id=_ATTEMPT,
        authorization_id=_AUTHORIZATION,
        project_id=_PROJECT,
        page_id=_PAGE,
        target_page_reference=_TARGET,
        provider_reference=_PROVIDER,
        output_asset_id=_OUTPUT,
        source_state="PromptBuilt",
        target_state="Generated",
    )


def test_schema_v1_initialization_and_absolute_owner_root(tmp_path: Path) -> None:
    store = LocalWorkflowApplicationLedgerStore(tmp_path)
    database = tmp_path / "workflow-application-ledger.sqlite3"

    assert database.is_file()
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (1,)
    with pytest.raises(ValueError, match="workflow application ledger unavailable"):
        LocalWorkflowApplicationLedgerStore(Path("relative-owner-root"))
    assert store.lookup_applied(_PROJECT, _PAGE, _OUTPUT).outcome == "missing"


@pytest.mark.parametrize("version", (1, 2))
def test_malformed_or_unsupported_schema_fails_closed(tmp_path: Path, version: int) -> None:
    database = tmp_path / "workflow-application-ledger.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE unrelated (id TEXT PRIMARY KEY)")
        connection.execute(f"PRAGMA user_version = {version}")

    with pytest.raises(ValueError, match="workflow application ledger unavailable"):
        LocalWorkflowApplicationLedgerStore(tmp_path)


def test_prepare_finalize_and_exact_replays(tmp_path: Path) -> None:
    service = WorkflowApplicationLedgerService()
    store = LocalWorkflowApplicationLedgerStore(tmp_path)

    prepared = _prepare(service, store)
    replay_prepared = _prepare(service, store)
    finalized = service.finalize(prepared.binding, _authoritative_commit_proof(_binding()), store)
    replay_applied = _prepare(service, store)
    replay_finalized = service.finalize(finalized.binding, _authoritative_commit_proof(_binding()), store)

    assert prepared.status == "prepared" and prepared.idempotent_replay is False
    assert replay_prepared.status == "prepared" and replay_prepared.idempotent_replay is True
    assert finalized.status == "applied" and finalized.idempotent_replay is False
    assert replay_applied.status == "applied" and replay_applied.idempotent_replay is True
    assert replay_finalized.status == "applied" and replay_finalized.idempotent_replay is True


def test_finalize_requires_prepared_record_and_exact_private_proof(tmp_path: Path) -> None:
    service = WorkflowApplicationLedgerService()
    store = LocalWorkflowApplicationLedgerStore(tmp_path)
    binding = _binding()

    missing = service.finalize(binding, _authoritative_commit_proof(binding), store)
    invalid = service.finalize(binding, object(), store)

    assert missing.status == "blocked"
    assert missing.findings[0].code == "LEDGER_PREPARED_RECORD_MISSING"
    assert invalid.status == "blocked"
    assert invalid.findings[0].code == "AUTHORITATIVE_COMMIT_PROOF_INVALID"


@pytest.mark.parametrize(
    ("authorization_updates", "report_updates"),
    [
        ({"attempt_id": "attempt:other"}, {}),
        ({}, {"provider_reference": "provider:other"}),
        ({"project_id": "project:other"}, {}),
        ({"page_id": "2"}, {}),
        ({"target_page_reference": "page:other"}, {}),
        ({"provider_reference": "provider:other"}, {}),
    ],
)
def test_prepare_rejects_mismatched_eligibility_facts(
    tmp_path: Path,
    authorization_updates: dict[str, object],
    report_updates: dict[str, object],
) -> None:
    service = WorkflowApplicationLedgerService()
    store = LocalWorkflowApplicationLedgerStore(tmp_path)

    result = _prepare(
        service,
        store,
        authorization=authorization_updates,
        report=report_updates,
    )

    assert result.status == "blocked"
    assert result.findings[0].code == "LEDGER_PREPARE_BINDING_INVALID"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("authorization_id", "workflow-authorization:other"),
        ("project_id", "project:other"),
        ("page_id", "2"),
        ("target_page_reference", "page:other"),
        ("provider_reference", "provider:other"),
        ("output_asset_id", "asset:other"),
        ("source_state", "Draft"),
        ("target_state", "Approved"),
    ],
)
def test_immutable_attempt_binding_conflicts(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    store = LocalWorkflowApplicationLedgerStore(tmp_path)
    original = _binding()
    assert store.prepare(original).outcome == "prepared"
    mutated = original.model_copy(update={field: value})

    result = store.prepare(mutated)

    assert result.outcome == "conflict"


def test_authorization_is_durably_unique(tmp_path: Path) -> None:
    store = LocalWorkflowApplicationLedgerStore(tmp_path)
    first = _binding()
    second = first.model_copy(update={"attempt_id": "attempt:other"})

    assert store.prepare(first).outcome == "prepared"
    assert store.prepare(second).outcome == "conflict"


def test_concurrent_prepares_and_finalization_are_serialized(tmp_path: Path) -> None:
    store = LocalWorkflowApplicationLedgerStore(tmp_path)
    binding = _binding()
    with ThreadPoolExecutor(max_workers=2) as executor:
        prepares = tuple(executor.map(store.prepare, (binding, binding)))
    assert {result.outcome for result in prepares} == {"prepared", "confirmed_prepared"}

    proof = _authoritative_commit_proof(binding)
    service = WorkflowApplicationLedgerService()
    with ThreadPoolExecutor(max_workers=2) as executor:
        finalized = tuple(executor.map(lambda _: service.finalize(binding, proof, store), range(2)))
    assert {result.status for result in finalized} == {"applied"}
    assert sorted(result.idempotent_replay for result in finalized) == [False, True]


def test_concurrent_authorization_conflict_has_one_reservation(tmp_path: Path) -> None:
    store = LocalWorkflowApplicationLedgerStore(tmp_path)
    first = _binding()
    second = first.model_copy(update={"attempt_id": "attempt:other"})
    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = tuple(executor.map(store.prepare, (first, second)))

    assert sorted(result.outcome for result in outcomes) == ["conflict", "prepared"]


def test_integrity_corruption_and_ambiguous_lookup_fail_closed(tmp_path: Path) -> None:
    service = WorkflowApplicationLedgerService()
    store = LocalWorkflowApplicationLedgerStore(tmp_path)
    first = _binding()
    assert store.prepare(first).outcome == "prepared"
    assert service.finalize(first, _authoritative_commit_proof(first), store).applied
    database = tmp_path / "workflow-application-ledger.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE workflow_application_ledger SET binding_digest = 'tampered'")
    assert store.lookup_applied(_PROJECT, _PAGE, _OUTPUT).outcome == "corrupt"

    clean_root = tmp_path / "clean"
    clean = LocalWorkflowApplicationLedgerStore(clean_root)
    assert clean.prepare(first).outcome == "prepared"
    assert service.finalize(first, _authoritative_commit_proof(first), clean).applied
    second = first.model_copy(
        update={"attempt_id": "attempt:other", "authorization_id": "workflow-authorization:other"}
    )
    assert clean.prepare(second).outcome == "prepared"
    assert service.finalize(second, _authoritative_commit_proof(second), clean).applied
    assert clean.lookup_applied(_PROJECT, _PAGE, _OUTPUT).outcome == "ambiguous"


def test_applied_lookup_rejects_prepared_and_accepts_applied(tmp_path: Path) -> None:
    service = WorkflowApplicationLedgerService()
    store = LocalWorkflowApplicationLedgerStore(tmp_path)
    prepared = _prepare(service, store)

    rejected = service.lookup_applied(_PROJECT, _PAGE, _OUTPUT, store)
    completed = service.finalize(prepared.binding, _authoritative_commit_proof(_binding()), store)
    accepted = service.lookup_applied(_PROJECT, _PAGE, _OUTPUT, store)

    assert rejected.status == "blocked"
    assert rejected.findings[0].code == "LEDGER_APPLIED_PROOF_NOT_APPLIED"
    assert completed.status == "applied"
    assert accepted.status == "applied"
    assert accepted.binding == _binding()


def test_corrupt_store_errors_are_redacted_and_inputs_are_not_mutated(tmp_path: Path) -> None:
    class RaisingStore:
        def prepare(self, binding: WorkflowApplicationLedgerBindingDTO):
            del binding
            raise RuntimeError("PRIVATE-SQLITE-DETAIL-CREDENTIAL-PROMPT")

        def finalize(self, binding: WorkflowApplicationLedgerBindingDTO, mutation_capability: object):
            del binding, mutation_capability
            raise RuntimeError("PRIVATE-SQLITE-DETAIL-CREDENTIAL-PROMPT")

        def lookup_applied(self, project_id: str, page_id: str, output_asset_id: str):
            del project_id, page_id, output_asset_id
            raise RuntimeError("PRIVATE-SQLITE-DETAIL-CREDENTIAL-PROMPT")

    service = WorkflowApplicationLedgerService()
    report = _binding_report()
    authorization = _authorization()
    before = (report.model_dump(mode="json"), authorization.model_dump(mode="json"))
    prepared = service.prepare(report, authorization, RaisingStore())  # type: ignore[arg-type]
    lookup = service.lookup_applied(_PROJECT, _PAGE, _OUTPUT, RaisingStore())  # type: ignore[arg-type]

    serialized = prepared.model_dump_json() + lookup.model_dump_json()
    assert "PRIVATE-SQLITE-DETAIL-CREDENTIAL-PROMPT" not in serialized
    assert "workflow-application-ledger.sqlite3" not in serialized
    assert before == (report.model_dump(mode="json"), authorization.model_dump(mode="json"))
    assert prepared.status == "blocked"
    assert lookup.status == "blocked"


def test_dtos_are_frozen_closed_and_slice_has_no_external_owners(tmp_path: Path) -> None:
    binding = _binding()
    with pytest.raises(ValidationError):
        binding.attempt_id = "attempt:other"
    with pytest.raises(ValidationError):
        WorkflowApplicationLedgerBindingDTO(**binding.model_dump(), private_value="secret")

    source = (
        Path(__file__).resolve().parents[1]
        / "src/manga_director/production/next_generation_workflow_application_ledger.py"
    ).read_text(encoding="utf-8")
    for forbidden in (
        "WorkflowEngine",
        "StateMachine",
        "ProjectRepository",
        "LocalFileRepository",
        "EventBus",
        "openai",
        "requests.",
        "httpx.",
        "GenerationEvidenceEnvelopeDTO",
    ):
        assert forbidden not in source
    assert LocalWorkflowApplicationLedgerStore(tmp_path).lookup_applied(
        _PROJECT, _PAGE, _OUTPUT
    ).outcome == "missing"
