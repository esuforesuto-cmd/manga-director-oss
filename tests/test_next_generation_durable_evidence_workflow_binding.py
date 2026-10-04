"""Focused tests for durable Evidence to future-workflow binding validation."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from manga_director.domain.state_machine import PageState
from manga_director.production.next_generation_asset_registration import (
    OutputAssetRegistrationReport,
)
from manga_director.production.next_generation_attempt_to_evidence_binding import (
    AttemptToEvidenceBindingReport,
)
from manga_director.production.next_generation_attempt_to_evidence_construction import (
    AttemptToEvidenceConstructionReport,
)
from manga_director.production.next_generation_durable_evidence_workflow_binding import (
    AuthoritativeWorkflowPageMappingDTO,
    DurableEvidenceWorkflowBindingReport,
    DurableEvidenceWorkflowBindingValidationService,
    WorkflowApplicationAuthorizationDTO,
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
    GenerationEvidencePersistenceReport,
    GenerationEvidenceStoreLookupResult,
)
from manga_director.production.next_generation_structured_generation_request import (
    GenerationProductionProfileDTO,
    StructuredGenerationRequestDTO,
    StructuredGenerationRequestValidationService,
)
from manga_director.workflow.contracts import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]
_ATTEMPT = "attempt:workflow:001"
_PROVIDER = "provider:local-a"
_PROJECT = "project:001"
_PAGE = "1"
_TARGET = "page:001"
_OUTPUT = "asset:generated:001"


class FakeEvidenceStore:
    def __init__(self, result: GenerationEvidenceStoreLookupResult) -> None:
        self.result = result
        self.calls: list[str] = []

    def lookup(self, attempt_id: str) -> GenerationEvidenceStoreLookupResult:
        self.calls.append(attempt_id)
        return self.result


class RaisingEvidenceStore:
    def lookup(self, attempt_id: str) -> GenerationEvidenceStoreLookupResult:
        del attempt_id
        raise RuntimeError("SYNTHETIC-PRIVATE-STORE-DETAIL")


def _known(value: str) -> EvidenceValueDTO:
    return EvidenceValueDTO(availability="known", value=value)


def _evidence(*, output_asset_id: str = _OUTPUT) -> GenerationEvidenceEnvelopeDTO:
    return GenerationEvidenceEnvelopeDTO(
        attempt_id=_ATTEMPT,
        observed_at=datetime(2026, 8, 22, 16, 0, tzinfo=UTC),
        provenance_reference="provenance:001",
        input=GenerationInputEvidenceDTO(input_reference="input:001"),
        output=GenerationOutputEvidenceDTO(output_asset_id=output_asset_id, media_type="image/png"),
        configuration=GenerationConfigurationEvidenceDTO(
            provider_id=_known("provider:local"),
            model_id=_known("model:001"),
            model_version=_known("v1"),
            workflow_id=_known("workflow:001"),
            workflow_version=_known("v1"),
            seed=_known("42"),
        ),
    )


def _request(*, panel: str | None = None) -> StructuredGenerationRequestDTO:
    profile = GenerationProductionProfileDTO(profile_id="profile:001", profile_version="v1")
    request = StructuredGenerationRequestDTO(
        request_id="request:001",
        target_page_reference=_TARGET,
        target_panel_reference=panel,
        generation_intent_reference="intent:001",
        input=GenerationInputEvidenceDTO(input_reference="input:001"),
        capability_requirements=(),
        provenance_reference="provenance:001",
        profile_id=profile.profile_id,
        profile_version=profile.profile_version,
    )
    assert StructuredGenerationRequestValidationService().validate(request, profile).ready is True
    return request


def _construction(
    *,
    evidence: GenerationEvidenceEnvelopeDTO | None = None,
    request: StructuredGenerationRequestDTO | None = None,
    status: str = "ready",
    validation_status: str = "ready",
    binding_ready: bool = True,
    provider_reference: str = _PROVIDER,
    malformed: bool = False,
) -> AttemptToEvidenceConstructionReport:
    candidate = evidence or _evidence()
    validation = GenerationEvidenceValidationService().validate((candidate,))
    if validation_status != "ready":
        validation = validation.model_copy(
            update={"status": validation_status, "ready": False}
        )
    request_report = SimpleNamespace(request=request or _request(), status="ready", ready=True)
    readiness = SimpleNamespace(input=SimpleNamespace(request_validation_report=request_report))
    execution_authorization = SimpleNamespace(readiness_report=readiness)
    envelope_report = SimpleNamespace(
        execution_authorization_validation_report=execution_authorization
    )
    resolution = SimpleNamespace(authorized_execution_envelope_validation_report=envelope_report)
    invocation = SimpleNamespace(
        provider_reference=provider_reference,
        secure_execution_input_resolution_report=resolution,
    )
    registration = OutputAssetRegistrationReport.model_construct(
        attempt_id=_ATTEMPT,
        provider_reference=provider_reference,
        provider_invocation_report=SimpleNamespace() if malformed else invocation,
    )
    binding = AttemptToEvidenceBindingReport.model_construct(
        generation_evidence_validation_report=validation,
        output_asset_registration_report=registration,
        attempt_id=_ATTEMPT,
        status=status,
        bound=binding_ready,
        ready=binding_ready and status == "ready",
    )
    return AttemptToEvidenceConstructionReport.model_construct(
        output_asset_registration_report=registration,
        provider_configuration_normalization_report=SimpleNamespace(),
        attempt_id=_ATTEMPT,
        request_id="request:001",
        provider_reference=provider_reference,
        generation_evidence=candidate,
        generation_evidence_validation_report=validation,
        attempt_to_evidence_binding_report=binding,
        status=status,
        constructed=True,
        bound=binding_ready,
        ready=binding_ready and status == "ready",
    )


def _persistence(
    evidence: GenerationEvidenceEnvelopeDTO,
    *,
    status: str = "persisted",
    persisted: bool = True,
) -> GenerationEvidencePersistenceReport:
    return GenerationEvidencePersistenceReport.model_construct(
        attempt_id=_ATTEMPT,
        generation_evidence=evidence,
        status=status,
        persisted=persisted,
        idempotent_replay=False,
        persistence_performed=True,
    )


def _authorization(**updates: object) -> WorkflowApplicationAuthorizationDTO:
    values: dict[str, object] = {
        "authorization_id": "workflow-authorization:001",
        "authorizer_id": "human:001",
        "authorized_at": datetime(2026, 8, 22, 16, 1, tzinfo=UTC),
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


def _mapping(**updates: object) -> AuthoritativeWorkflowPageMappingDTO:
    values: dict[str, object] = {
        "project_id": _PROJECT,
        "page_id": _PAGE,
        "target_page_reference": _TARGET,
    }
    values.update(updates)
    return AuthoritativeWorkflowPageMappingDTO.model_validate(values)


def _context(**updates: object) -> WorkflowContext:
    page: dict[str, object] = {"project_id": _PROJECT, "page_id": _PAGE}
    page.update(updates.pop("page", {}))
    return WorkflowContext(page=page, state=updates.pop("state", PageState.PROMPT_BUILT))


def _store(evidence: GenerationEvidenceEnvelopeDTO, *, outcome: str = "found") -> FakeEvidenceStore:
    return FakeEvidenceStore(
        GenerationEvidenceStoreLookupResult(
            attempt_id=_ATTEMPT,
            outcome=outcome,
            generation_evidence=evidence if outcome == "found" else None,
            evidence_status="ready" if outcome == "found" else None,
        )
    )


def _validate(
    *,
    authorization: WorkflowApplicationAuthorizationDTO | None = None,
    mapping: AuthoritativeWorkflowPageMappingDTO | None = None,
    context: WorkflowContext | None = None,
    persistence: GenerationEvidencePersistenceReport | None = None,
    store: object | None = None,
    construction: AttemptToEvidenceConstructionReport | None = None,
) -> DurableEvidenceWorkflowBindingReport:
    report = construction or _construction()
    evidence = report.generation_evidence
    assert evidence is not None
    return DurableEvidenceWorkflowBindingValidationService().validate(
        authorization or _authorization(),
        mapping or _mapping(),
        context or _context(),
        persistence or _persistence(evidence),
        store or _store(evidence),  # type: ignore[arg-type]
        report,
    )


def _codes(report: DurableEvidenceWorkflowBindingReport) -> list[str]:
    return [finding.code for finding in report.findings]


def test_exact_page_level_binding_is_eligible_and_read_only() -> None:
    construction = _construction()
    evidence = construction.generation_evidence
    assert evidence is not None
    store = _store(evidence)

    report = _validate(construction=construction, store=store)

    assert report.status == "eligible"
    assert report.eligible is True
    assert store.calls == [_ATTEMPT]
    assert report.workflow_transition_performed is False
    assert report.state_machine_action is False
    assert report.event_published is False


@pytest.mark.parametrize(
    ("authorization", "code"),
    [
        (None, "WORKFLOW_APPLICATION_AUTHORIZATION_MISSING"),
        (_authorization(attempt_id="attempt:other"), "ATTEMPT_BINDING_MISMATCH"),
        (_authorization(provider_reference="provider:other"), "PROVIDER_BINDING_MISMATCH"),
    ],
)
def test_authorization_is_required_and_exact(
    authorization: WorkflowApplicationAuthorizationDTO | None, code: str
) -> None:
    construction = _construction()
    evidence = construction.generation_evidence
    assert evidence is not None
    if authorization is None:
        report = DurableEvidenceWorkflowBindingValidationService().validate(
            None,
            _mapping(),
            _context(),
            _persistence(evidence),
            _store(evidence),
            construction,
        )
    else:
        report = _validate(authorization=authorization, construction=construction)

    assert report.status == "blocked"
    assert code in _codes(report)


@pytest.mark.parametrize(
    ("mapping", "context", "code"),
    [
        (_mapping(target_page_reference="page:other"), _context(), "AUTHORITATIVE_PAGE_MAPPING_MISMATCH"),
        (_mapping(), _context(page={"project_id": "project:other"}), "AUTHORITATIVE_PAGE_MAPPING_MISMATCH"),
        (_mapping(project_id="project:other"), _context(), "AUTHORITATIVE_PAGE_MAPPING_MISMATCH"),
        (_mapping(page_id="2"), _context(), "AUTHORITATIVE_PAGE_MAPPING_MISMATCH"),
    ],
)
def test_authoritative_mapping_must_match_workflow_context(
    mapping: AuthoritativeWorkflowPageMappingDTO, context: WorkflowContext, code: str
) -> None:
    report = _validate(mapping=mapping, context=context)

    assert report.status == "blocked"
    assert code in _codes(report)


@pytest.mark.parametrize(
    ("authorization", "context", "code"),
    [
        (
            WorkflowApplicationAuthorizationDTO.model_construct(
                **{**_authorization().model_dump(), "source_state": "Draft"}
            ),
            _context(),
            "WORKFLOW_SOURCE_STATE_MISMATCH",
        ),
        (
            WorkflowApplicationAuthorizationDTO.model_construct(
                **{**_authorization().model_dump(), "target_state": "Approved"}
            ),
            _context(),
            "WORKFLOW_TARGET_STATE_MISMATCH",
        ),
        (_authorization(), _context(state=PageState.DESIGNED), "WORKFLOW_SOURCE_STATE_MISMATCH"),
    ],
)
def test_only_promptbuilt_to_generated_is_eligible(
    authorization: WorkflowApplicationAuthorizationDTO, context: WorkflowContext, code: str
) -> None:
    report = _validate(authorization=authorization, context=context)

    assert report.status == "blocked"
    assert code in _codes(report)


def test_panel_target_is_rejected_without_page_completion_inference() -> None:
    report = _validate(construction=_construction(request=_request(panel="panel:001")))

    assert report.status == "blocked"
    assert "PANEL_TARGET_UNSUPPORTED" in _codes(report)


def test_structured_request_target_must_match_the_authoritative_page_mapping() -> None:
    construction = _construction(request=_request())
    authorization = _authorization(target_page_reference="page:other")
    mapping = _mapping(target_page_reference="page:other")

    report = _validate(authorization=authorization, mapping=mapping, construction=construction)

    assert report.status == "blocked"
    assert "TARGET_PAGE_REFERENCE_MISMATCH" in _codes(report)


@pytest.mark.parametrize(
    ("construction", "code"),
    [
        (_construction(status="needs_evidence", binding_ready=True), "MALFORMED_OR_UNREADY_EVIDENCE_CHAIN"),
        (_construction(status="needs_review", binding_ready=True), "MALFORMED_OR_UNREADY_EVIDENCE_CHAIN"),
        (_construction(status="blocked", binding_ready=False), "MALFORMED_OR_UNREADY_EVIDENCE_CHAIN"),
        (_construction(validation_status="needs_evidence"), "EVIDENCE_VALIDATION_NOT_READY"),
        (_construction(binding_ready=False), "MALFORMED_OR_UNREADY_EVIDENCE_CHAIN"),
    ],
)
def test_nonready_or_blocked_evidence_chain_is_ineligible(
    construction: AttemptToEvidenceConstructionReport, code: str
) -> None:
    report = _validate(construction=construction)

    assert report.status == "blocked"
    assert code in _codes(report)


def test_persistence_failure_and_canonical_evidence_difference_fail_closed() -> None:
    construction = _construction()
    evidence = construction.generation_evidence
    assert evidence is not None
    failed = _persistence(evidence, status="blocked", persisted=False)
    mismatch = _persistence(_evidence(output_asset_id="asset:other"))

    assert "EVIDENCE_PERSISTENCE_NOT_SUCCESSFUL" in _codes(
        _validate(construction=construction, persistence=failed)
    )
    assert "PERSISTED_EVIDENCE_MISMATCH" in _codes(
        _validate(construction=construction, persistence=mismatch)
    )


@pytest.mark.parametrize(
    ("store", "code"),
    [
        (_store(_evidence(), outcome="missing"), "DURABLE_EVIDENCE_MISSING"),
        (_store(_evidence(), outcome="corrupt"), "DURABLE_EVIDENCE_CORRUPT"),
        (_store(_evidence(output_asset_id="asset:other")), "DURABLE_EVIDENCE_MISMATCH"),
        (RaisingEvidenceStore(), "DURABLE_EVIDENCE_LOOKUP_FAILED"),
    ],
)
def test_missing_corrupt_or_mismatched_durable_evidence_fails_closed(
    store: object, code: str
) -> None:
    report = _validate(store=store)

    assert report.status == "blocked"
    assert code in _codes(report)


def test_malformed_nested_chain_fails_closed() -> None:
    report = _validate(construction=_construction(malformed=True))

    assert report.status == "blocked"
    assert "MALFORMED_NESTED_REPORT_CHAIN" in _codes(report)


def test_deterministic_replay_and_caller_nonmutation() -> None:
    construction = _construction()
    evidence = construction.generation_evidence
    assert evidence is not None
    authorization = _authorization()
    mapping = _mapping()
    context = _context()
    persistence = _persistence(evidence)
    before = (
        authorization.model_dump(mode="json"),
        mapping.model_dump(mode="json"),
        context.model_dump(mode="json"),
        persistence.model_dump(mode="json"),
        construction.model_dump(mode="json"),
    )

    first = _validate(
        authorization=authorization,
        mapping=mapping,
        context=context,
        persistence=persistence,
        store=_store(evidence),
        construction=construction,
    )
    second = _validate(
        authorization=authorization,
        mapping=mapping,
        context=context,
        persistence=persistence,
        store=_store(evidence),
        construction=construction,
    )

    assert first == second
    assert first.status == "eligible"
    assert before == (
        authorization.model_dump(mode="json"),
        mapping.model_dump(mode="json"),
        context.model_dump(mode="json"),
        persistence.model_dump(mode="json"),
        construction.model_dump(mode="json"),
    )


def test_dtos_are_frozen_closed_and_results_redact_private_material() -> None:
    authorization = _authorization()
    with pytest.raises(ValidationError):
        authorization.attempt_id = "attempt:other"
    with pytest.raises(ValidationError):
        WorkflowApplicationAuthorizationDTO(**authorization.model_dump(), private_value="secret")

    report = _validate(store=RaisingEvidenceStore())
    serialized = report.model_dump_json()
    for private_value in (
        "SYNTHETIC-PRIVATE-STORE-DETAIL",
        "prompt",
        "credential",
        "base64",
        "generation-evidence.sqlite3",
        "binding_fingerprint",
    ):
        assert private_value not in serialized


def test_source_keeps_workflow_execution_and_public_boundaries_out() -> None:
    source = (
        ROOT
        / "src/manga_director/production/next_generation_durable_evidence_workflow_binding.py"
    ).read_text(encoding="utf-8")
    for forbidden in (
        "WorkflowEngine",
        "WorkflowRecovery",
        "StateMachine",
        "ImageAgent",
        "EventBus",
        "FailureEvidence",
        "CredentialManager",
        "openai",
        "requests.",
        "httpx.",
        "sqlite3",
        "datetime.now",
    ):
        assert forbidden not in source
    production_init = (ROOT / "src/manga_director/production/__init__.py").read_text(
        encoding="utf-8"
    )
    root_init = (ROOT / "src/manga_director/__init__.py").read_text(encoding="utf-8")
    assert "next_generation_durable_evidence_workflow_binding" not in production_init
    assert "next_generation_durable_evidence_workflow_binding" not in root_init
