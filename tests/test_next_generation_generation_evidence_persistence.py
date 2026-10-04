"""Focused private-sidecar contracts for immutable Generation Evidence persistence."""

from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from manga_director.production.next_generation_asset_registration import (
    OutputAssetRegistrationReport,
)
from manga_director.production.next_generation_attempt_to_evidence_binding import (
    AttemptToEvidenceBindingReport,
)
from manga_director.production.next_generation_attempt_to_evidence_construction import (
    AttemptToEvidenceConstructionReport,
)
from manga_director.production.next_generation_generation_evidence import (
    EvidenceValueDTO,
    GenerationConfigurationEvidenceDTO,
    GenerationEvidenceEnvelopeDTO,
    GenerationEvidenceValidationService,
    GenerationInputEvidenceDTO,
    GenerationOutputEvidenceDTO,
)
from manga_director.production.next_generation_generation_evidence_persistence import (
    GenerationEvidencePersistenceFindingDTO,
    GenerationEvidencePersistenceReport,
    GenerationEvidencePersistenceService,
    LocalGenerationEvidenceStore,
)

ROOT = Path(__file__).resolve().parents[1]
_ATTEMPT = "attempt:evidence-store:001"
_PROVIDER = "provider:local-a"


class FailingStore(LocalGenerationEvidenceStore):
    def _insert(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        del args, kwargs
        raise sqlite3.OperationalError("private storage failure")


def _known(value: str) -> EvidenceValueDTO:
    return EvidenceValueDTO(availability="known", value=value)


def _evidence(
    *,
    attempt_id: str = _ATTEMPT,
    output_asset_id: str = "asset:generated:001",
    observed_at: datetime = datetime(2026, 8, 22, 16, 0, tzinfo=UTC),
    provenance_reference: str = "provenance:001",
    media_type: str = "image/png",
    input_hash: EvidenceValueDTO | None = None,
    parameter_value: EvidenceValueDTO | None = None,
) -> GenerationEvidenceEnvelopeDTO:
    parameters = ()
    if parameter_value is not None:
        from manga_director.production.next_generation_generation_evidence import (
            GenerationParameterEvidenceDTO,
        )

        parameters = (GenerationParameterEvidenceDTO(key="quality", value=parameter_value),)
    return GenerationEvidenceEnvelopeDTO(
        attempt_id=attempt_id,
        observed_at=observed_at,
        provenance_reference=provenance_reference,
        input=GenerationInputEvidenceDTO(input_reference="input:001", input_content_hash=input_hash),
        output=GenerationOutputEvidenceDTO(
            output_asset_id=output_asset_id,
            media_type=media_type,
        ),
        configuration=GenerationConfigurationEvidenceDTO(
            provider_id=_known("provider:local"),
            model_id=_known("model:001"),
            model_version=_known("v1"),
            workflow_id=_known("workflow:001"),
            workflow_version=_known("v1"),
            seed=_known("42"),
            parameters=parameters,
        ),
    )


def _construction(
    evidence: GenerationEvidenceEnvelopeDTO | None = None,
    *,
    constructed: bool = True,
    bound: bool = True,
    status: str | None = None,
    validation_status: str | None = None,
    provider_reference: str = _PROVIDER,
) -> AttemptToEvidenceConstructionReport:
    candidate = evidence or _evidence()
    validation = GenerationEvidenceValidationService().validate((candidate,))
    if validation_status is not None:
        validation = validation.model_copy(
            update={"status": validation_status, "ready": validation_status == "ready"}
        )
    effective_status = status or validation.status
    registration = OutputAssetRegistrationReport.model_construct(
        provider_reference=provider_reference,
        attempt_id=_ATTEMPT,
    )
    binding = AttemptToEvidenceBindingReport.model_construct(
        generation_evidence_validation_report=validation,
        output_asset_registration_report=registration,
        attempt_id=_ATTEMPT,
        status=effective_status,
        bound=bound,
        ready=effective_status == "ready" and bound,
    )
    return AttemptToEvidenceConstructionReport.model_construct(
        attempt_id=_ATTEMPT,
        provider_reference=provider_reference,
        generation_evidence=candidate if evidence is not None or constructed else None,
        generation_evidence_validation_report=validation,
        attempt_to_evidence_binding_report=binding,
        status=effective_status,
        constructed=constructed,
        bound=bound,
        ready=effective_status == "ready" and bound,
    )


def _persist(root: Path, report: AttemptToEvidenceConstructionReport):
    return GenerationEvidencePersistenceService().persist(report, LocalGenerationEvidenceStore(root))


def _database(root: Path) -> Path:
    return root / "generation-evidence.sqlite3"


def test_ready_bound_evidence_persists_only_after_commit(tmp_path: Path) -> None:
    report = _persist(tmp_path / "store", _construction())

    assert report.status == "persisted"
    assert report.persisted is True
    assert report.idempotent_replay is False
    assert report.persistence_performed is True
    assert report.generation_evidence is not None
    assert report.generation_evidence.observed_at == datetime(2026, 8, 22, 16, 0, tzinfo=UTC)
    assert _database(tmp_path / "store").is_file()


@pytest.mark.parametrize("status", ("needs_evidence", "needs_review"))
def test_bound_nonready_evidence_remains_persistable(tmp_path: Path, status: str) -> None:
    report = _persist(tmp_path / status, _construction(status=status))

    assert report.status == "persisted"
    assert report.persisted is True
    assert report.generation_evidence is not None


@pytest.mark.parametrize(
    ("report", "code"),
    (
        (_construction(constructed=False), "EVIDENCE_CONSTRUCTION_NOT_COMPLETED"),
        (_construction(bound=False), "EVIDENCE_BINDING_NOT_ELIGIBLE"),
        (_construction(status="blocked"), "EVIDENCE_BINDING_NOT_ELIGIBLE"),
        (_construction(validation_status="blocked"), "EVIDENCE_VALIDATION_NOT_ELIGIBLE"),
    ),
)
def test_ineligible_construction_reports_never_persist(
    tmp_path: Path, report: AttemptToEvidenceConstructionReport, code: str
) -> None:
    result = _persist(tmp_path / code, report)

    assert result.status == "blocked"
    assert result.persisted is False
    assert result.persistence_performed is False
    assert [item.code for item in result.findings] == [code]
    with sqlite3.connect(_database(tmp_path / code)) as connection:
        assert connection.execute("SELECT COUNT(*) FROM generation_evidence").fetchone()[0] == 0


def test_missing_candidate_evidence_never_persists(tmp_path: Path) -> None:
    report = _construction().model_copy(update={"generation_evidence": None})

    result = _persist(tmp_path / "store", report)

    assert [item.code for item in result.findings] == ["EVIDENCE_CANDIDATE_MISSING"]
    assert result.persistence_performed is False


def test_exact_replay_confirms_the_existing_immutable_record(tmp_path: Path) -> None:
    root = tmp_path / "store"
    construction = _construction()
    first = _persist(root, construction)
    replay = _persist(root, construction)

    assert first.persisted is True
    assert replay.persisted is True
    assert replay.idempotent_replay is True
    with sqlite3.connect(_database(root)) as connection:
        assert connection.execute("SELECT COUNT(*) FROM generation_evidence").fetchone()[0] == 1


@pytest.mark.parametrize(
    "evidence",
    (
        _evidence(output_asset_id="asset:generated:other"),
        _evidence(provenance_reference="provenance:other"),
        _evidence(observed_at=datetime(2026, 8, 22, 17, 0, tzinfo=UTC)),
        _evidence(media_type="image/jpeg"),
        _evidence(input_hash=_known("input-hash:other")),
        _evidence(parameter_value=_known("high")),
    ),
)
def test_same_attempt_canonical_evidence_differences_conflict(
    tmp_path: Path, evidence: GenerationEvidenceEnvelopeDTO
) -> None:
    root = tmp_path / "store"
    assert _persist(root, _construction()).persisted is True

    conflict = _persist(root, _construction(evidence))

    assert conflict.status == "blocked"
    assert conflict.persisted is False
    assert [item.code for item in conflict.findings] == ["EVIDENCE_PERSISTENCE_CONFLICT"]
    with sqlite3.connect(_database(root)) as connection:
        assert connection.execute("SELECT COUNT(*) FROM generation_evidence").fetchone()[0] == 1


def test_same_attempt_provider_binding_difference_conflicts(tmp_path: Path) -> None:
    root = tmp_path / "store"
    assert _persist(root, _construction()).persisted is True

    result = _persist(root, _construction(provider_reference="provider:other"))

    assert [item.code for item in result.findings] == ["EVIDENCE_PERSISTENCE_CONFLICT"]


def test_lookup_verifies_canonical_payload_and_private_digest(tmp_path: Path) -> None:
    root = tmp_path / "store"
    construction = _construction()
    assert _persist(root, construction).persisted is True
    store = LocalGenerationEvidenceStore(root)

    found = store.lookup(_ATTEMPT)
    assert found.outcome == "found"
    assert found.generation_evidence == construction.generation_evidence
    assert found.evidence_status == "ready"
    with sqlite3.connect(_database(root)) as connection:
        connection.execute("UPDATE generation_evidence SET payload_digest = '0'")

    assert LocalGenerationEvidenceStore(root).lookup(_ATTEMPT).outcome == "corrupt"
    assert _persist(root, construction).status == "blocked"


def test_malformed_payload_and_schema_fail_closed(tmp_path: Path) -> None:
    root = tmp_path / "store"
    construction = _construction()
    assert _persist(root, construction).persisted is True
    with sqlite3.connect(_database(root)) as connection:
        connection.execute("UPDATE generation_evidence SET payload_json = '{not-json}'")

    assert LocalGenerationEvidenceStore(root).lookup(_ATTEMPT).outcome == "corrupt"
    with sqlite3.connect(_database(root)) as connection:
        connection.execute("PRAGMA user_version = 2")

    with pytest.raises(ValueError, match="evidence store is unavailable"):
        LocalGenerationEvidenceStore(root)


def test_malformed_existing_schema_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "store"
    root.mkdir()
    with sqlite3.connect(_database(root)) as connection:
        connection.execute("CREATE TABLE unexpected (value TEXT)")
        connection.execute("PRAGMA user_version = 1")

    with pytest.raises(ValueError, match="evidence store is unavailable"):
        LocalGenerationEvidenceStore(root)


def test_concurrent_exact_replay_serializes_to_one_record(tmp_path: Path) -> None:
    root = tmp_path / "store"
    construction = _construction()

    with ThreadPoolExecutor(max_workers=2) as executor:
        reports = list(executor.map(lambda _: _persist(root, construction), range(2)))

    assert {report.status for report in reports} == {"persisted"}
    assert sum(report.idempotent_replay for report in reports) == 1
    with sqlite3.connect(_database(root)) as connection:
        assert connection.execute("SELECT COUNT(*) FROM generation_evidence").fetchone()[0] == 1


def test_transaction_failure_is_redacted_and_leaves_other_asset_state_untouched(tmp_path: Path) -> None:
    asset_marker = tmp_path / "asset-owner" / "asset.png"
    asset_marker.parent.mkdir()
    asset_marker.write_bytes(b"synthetic asset bytes")
    store = FailingStore(tmp_path / "evidence-store")

    result = GenerationEvidencePersistenceService().persist(_construction(), store)

    assert result.status == "blocked"
    assert result.persisted is False
    assert result.persistence_performed is True
    assert [item.code for item in result.findings] == ["EVIDENCE_PERSISTENCE_FAILED"]
    assert asset_marker.read_bytes() == b"synthetic asset bytes"


def test_owner_root_is_explicit_and_no_database_path_is_a_caller_input(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="evidence store is unavailable"):
        LocalGenerationEvidenceStore(Path("relative-store"))
    with pytest.raises(ValueError, match="evidence store is unavailable"):
        LocalGenerationEvidenceStore(tmp_path / "store" / ".." / "escaped")


def test_reports_are_frozen_closed_and_redact_private_store_metadata(tmp_path: Path) -> None:
    result = _persist(tmp_path / "store", _construction())
    finding = GenerationEvidencePersistenceFindingDTO(code="TEST", status="blocked", message="test")

    with pytest.raises(ValidationError):
        finding.code = "changed"
    with pytest.raises(ValidationError):
        GenerationEvidencePersistenceReport(**result.model_dump(), private_digest="secret")
    serialized = result.model_dump_json()
    for private_value in (
        "generation-evidence.sqlite3",
        "payload_digest",
        "binding_fingerprint",
        "SYNTHETIC-PRIVATE-PROMPT",
        "SYNTHETIC-PRIVATE-OUTPUT",
        "private storage failure",
    ):
        assert private_value not in serialized


def test_service_does_not_mutate_caller_reports_or_perform_runtime_actions(tmp_path: Path) -> None:
    construction = _construction()
    before = construction.model_dump(mode="json")

    result = _persist(tmp_path / "store", construction)

    assert result.persisted is True
    assert construction.model_dump(mode="json") == before


def test_source_keeps_public_workflow_asset_provider_and_knowledge_boundaries_out() -> None:
    source = (
        ROOT
        / "src/manga_director/production/next_generation_generation_evidence_persistence.py"
    ).read_text(encoding="utf-8")
    for forbidden in (
        "LocalDurableAssetOwner",
        "OpaqueGeneratedOutputHandle",
        "AssetRegistrationPort",
        "ProviderGenerationInvocationPort",
        "WorkflowEngine",
        "StateMachine",
        "FailureEvidence",
        "CredentialManager",
        "openai",
        "requests.",
        "httpx.",
        "datetime.now",
        "GenerationEvidenceValidationService",
        "AttemptToEvidenceBindingService",
    ):
        assert forbidden not in source
    production_init = (ROOT / "src/manga_director/production/__init__.py").read_text(
        encoding="utf-8"
    )
    root_init = (ROOT / "src/manga_director/__init__.py").read_text(encoding="utf-8")
    assert "next_generation_generation_evidence_persistence" not in production_init
    assert "next_generation_generation_evidence_persistence" not in root_init
