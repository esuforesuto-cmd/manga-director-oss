"""Focused contracts for secure internal execution-input resolution."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from manga_director.production.next_generation_authorized_execution_envelope import (
    AuthorizedGenerationExecutionEnvelopeDTO,
    AuthorizedGenerationExecutionEnvelopeValidationService,
)
from manga_director.production.next_generation_execution_authorization import (
    ExecutionAuthorizationRecordDTO,
    ExecutionAuthorizationValidationService,
)
from manga_director.production.next_generation_generation_evidence import (
    GenerationIdentityBindingDTO,
    GenerationInputEvidenceDTO,
)
from manga_director.production.next_generation_pre_execution_readiness import (
    PreExecutionReadinessInputDTO,
    PreExecutionReadinessService,
)
from manga_director.production.next_generation_provider_capability_negotiation import (
    GenerationCapabilityRequirementDTO,
    ProviderCapabilityDeclarationDTO,
    ProviderCapabilityNegotiationService,
    ProviderCapabilityStateDTO,
)
from manga_director.production.next_generation_secure_execution_input_resolution import (
    AuthoritativeExecutionInputSnapshot,
    OpaqueReferenceAssetHandle,
    SecureExecutionInputResolutionFindingDTO,
    SecureExecutionInputResolutionReport,
    SecureExecutionInputResolutionService,
)
from manga_director.production.next_generation_structured_generation_request import (
    GenerationProductionProfileDTO,
    StructuredGenerationRequestDTO,
    StructuredGenerationRequestValidationService,
)

ROOT = Path(__file__).resolve().parents[1]


class InMemoryGenerationInputResolver:
    """Test-only injected resolver with no external access."""

    def __init__(
        self,
        snapshots: dict[str, AuthoritativeExecutionInputSnapshot],
        failures: set[str] | None = None,
    ) -> None:
        self.snapshots = snapshots
        self.failures = failures or set()
        self.calls: list[str] = []

    def resolve(self, input_reference: str) -> AuthoritativeExecutionInputSnapshot | None:
        self.calls.append(input_reference)
        if input_reference in self.failures:
            raise RuntimeError("resolver-private-detail: do-not-report")
        return self.snapshots.get(input_reference)


class InMemoryReferenceAssetResolver:
    """Test-only injected opaque-handle resolver with no external access."""

    def __init__(
        self,
        handles: dict[str, OpaqueReferenceAssetHandle],
        failures: set[str] | None = None,
    ) -> None:
        self.handles = handles
        self.failures = failures or set()
        self.calls: list[str] = []

    def resolve(self, reference_asset_id: str) -> OpaqueReferenceAssetHandle | None:
        self.calls.append(reference_asset_id)
        if reference_asset_id in self.failures:
            raise RuntimeError("asset-private-detail: do-not-report")
        return self.handles.get(reference_asset_id)


def _requirement() -> GenerationCapabilityRequirementDTO:
    return GenerationCapabilityRequirementDTO(capability_id="text_prompt", requirement_level="required")


def _authorized_report():
    requirements = (_requirement(),)
    profile = GenerationProductionProfileDTO(
        profile_id="profile:manga",
        profile_version="v1",
        capability_requirements=requirements,
    )
    request = StructuredGenerationRequestDTO(
        request_id="request:001",
        target_page_reference="page:001",
        generation_intent_reference="intent:001",
        input=GenerationInputEvidenceDTO(input_reference="input:001"),
        capability_requirements=requirements,
        provenance_reference="provenance:001",
        profile_id="profile:manga",
        profile_version="v1",
        identity_bindings=(
            GenerationIdentityBindingDTO(
                character_id="character:001",
                identity_id="identity:001",
                identity_version="v1",
                reference_asset_ids=("asset:002", "asset:001"),
            ),
        ),
    )
    request_report = StructuredGenerationRequestValidationService().validate(request, profile)
    negotiation = ProviderCapabilityNegotiationService().validate(
        requirements,
        ProviderCapabilityDeclarationDTO(
            provider_reference="provider:local-a",
            capability_states=(
                ProviderCapabilityStateDTO(capability_id="text_prompt", state="supported"),
            ),
        ),
    )
    readiness = PreExecutionReadinessService().validate(
        PreExecutionReadinessInputDTO(
            request_validation_report=request_report,
            capability_negotiation_report=negotiation,
            provider_reference="provider:local-a",
        )
    )
    authorization = ExecutionAuthorizationValidationService().validate(
        readiness,
        (
            ExecutionAuthorizationRecordDTO(
                authorization_id="authorization:001",
                authorizer_id="human:editor-a",
                authorized_at=datetime(2026, 8, 22, 12, 0, tzinfo=UTC),
                request_id="request:001",
                provider_reference="provider:local-a",
            ),
        ),
    )
    return AuthorizedGenerationExecutionEnvelopeValidationService().validate(
        (
            AuthorizedGenerationExecutionEnvelopeDTO(
                attempt_id="attempt:001",
                request_id="request:001",
                provider_reference="provider:local-a",
                authorization_ids=("authorization:001",),
                profile_id="profile:manga",
                profile_version="v1",
                generation_intent_reference="intent:001",
                input_reference="input:001",
            ),
        ),
        authorization,
    )


def _snapshot(
    *,
    input_reference: str = "input:001",
    generation_intent_reference: str = "intent:001",
    required_reference_asset_ids: tuple[str, ...] = ("asset:002", "asset:001"),
    raw_prompt_material: object = "private prompt material",
) -> AuthoritativeExecutionInputSnapshot:
    return AuthoritativeExecutionInputSnapshot.from_prompt_material(
        input_reference=input_reference,
        generation_intent_reference=generation_intent_reference,
        required_reference_asset_ids=required_reference_asset_ids,
        raw_prompt_material=raw_prompt_material,
    )


def _asset_resolver() -> InMemoryReferenceAssetResolver:
    return InMemoryReferenceAssetResolver(
        {
            "asset:001": OpaqueReferenceAssetHandle("asset:001", object()),
            "asset:002": OpaqueReferenceAssetHandle("asset:002", object()),
        }
    )


def _resolve(
    report,
    input_resolver: InMemoryGenerationInputResolver,
    asset_resolver: InMemoryReferenceAssetResolver,
    attempt_id: str = "attempt:001",
):
    return SecureExecutionInputResolutionService().resolve(
        attempt_id,
        report,
        input_resolver,
        asset_resolver,
    )


def test_dtos_are_frozen_closed_and_reports_exclude_runtime_prompt() -> None:
    finding = SecureExecutionInputResolutionFindingDTO(
        code="TEST", status="blocked", message="test"
    )
    with pytest.raises(ValidationError):
        finding.code = "changed"
    with pytest.raises(ValidationError):
        SecureExecutionInputResolutionFindingDTO(
            code="TEST", status="blocked", message="test", raw_prompt="private"
        )

    outcome = _resolve(
        _authorized_report(),
        InMemoryGenerationInputResolver({"input:001": _snapshot(raw_prompt_material="TOP-SECRET-PROMPT")}),
        _asset_resolver(),
    )

    assert outcome.report.ready is True
    assert outcome.materialized_input is not None
    assert outcome.materialized_input.raw_prompt == "TOP-SECRET-PROMPT"
    assert "TOP-SECRET-PROMPT" not in outcome.report.model_dump_json()
    with pytest.raises(ValidationError):
        outcome.report.ready = False
    with pytest.raises(ValidationError):
        SecureExecutionInputResolutionReport(
            **outcome.report.model_dump(), raw_prompt="TOP-SECRET-PROMPT"
        )


def test_explicit_attempt_binding_requires_exact_authoritative_envelope() -> None:
    resolver = InMemoryGenerationInputResolver({"input:001": _snapshot()})
    outcome = _resolve(_authorized_report(), resolver, _asset_resolver(), "attempt:missing")

    assert outcome.report.status == "blocked"
    assert [finding.code for finding in outcome.report.findings] == ["EXECUTION_ATTEMPT_NOT_FOUND"]
    assert resolver.calls == []


@pytest.mark.parametrize(
    ("status", "ready", "code", "expected_status"),
    (
        ("needs_review", False, "AUTHORIZED_EXECUTION_ENVELOPE_NEEDS_REVIEW", "needs_review"),
        ("blocked", False, "AUTHORIZED_EXECUTION_ENVELOPE_BLOCKED", "blocked"),
    ),
)
def test_upstream_non_ready_report_stops_before_resolver_access(
    status: str, ready: bool, code: str, expected_status: str
) -> None:
    report = _authorized_report().model_copy(update={"status": status, "ready": ready})
    resolver = InMemoryGenerationInputResolver({"input:001": _snapshot()})

    outcome = _resolve(report, resolver, _asset_resolver())

    assert outcome.report.status == expected_status
    assert [finding.code for finding in outcome.report.findings] == [code]
    assert resolver.calls == []


def test_input_reference_and_intent_binding_fail_closed() -> None:
    input_mismatch = _resolve(
        _authorized_report(),
        InMemoryGenerationInputResolver({"input:001": _snapshot(input_reference="input:other")}),
        _asset_resolver(),
    )
    intent_mismatch = _resolve(
        _authorized_report(),
        InMemoryGenerationInputResolver(
            {"input:001": _snapshot(generation_intent_reference="intent:other")}
        ),
        _asset_resolver(),
    )

    assert [finding.code for finding in input_mismatch.report.findings] == [
        "INPUT_REFERENCE_UNRESOLVABLE"
    ]
    assert [finding.code for finding in intent_mismatch.report.findings] == [
        "GENERATION_INTENT_BINDING_MISMATCH"
    ]


@pytest.mark.parametrize(
    ("asset_ids", "code"),
    (
        (("asset:001",), "REQUIRED_REFERENCE_ASSET_SET_MISMATCH"),
        (("asset:001", "asset:002", "asset:extra"), "REQUIRED_REFERENCE_ASSET_SET_MISMATCH"),
        (("asset:001", "asset:001", "asset:002"), "DUPLICATE_REQUIRED_REFERENCE_ASSET_ID"),
    ),
)
def test_required_reference_asset_set_is_exact_and_duplicate_free(
    asset_ids: tuple[str, ...], code: str
) -> None:
    outcome = _resolve(
        _authorized_report(),
        InMemoryGenerationInputResolver(
            {"input:001": _snapshot(required_reference_asset_ids=asset_ids)}
        ),
        _asset_resolver(),
    )

    assert outcome.report.status == "blocked"
    assert code in {finding.code for finding in outcome.report.findings}


def test_unresolved_reference_asset_fails_closed_without_fallback() -> None:
    asset_resolver = InMemoryReferenceAssetResolver(
        {"asset:001": OpaqueReferenceAssetHandle("asset:001", object())}
    )
    outcome = _resolve(
        _authorized_report(),
        InMemoryGenerationInputResolver({"input:001": _snapshot()}),
        asset_resolver,
    )

    assert outcome.report.status == "blocked"
    assert [finding.reference_asset_id for finding in outcome.report.findings] == ["asset:002"]
    assert outcome.materialized_input is None
    assert asset_resolver.calls == ["asset:001", "asset:002"]


@pytest.mark.parametrize("raw_prompt_material", ("", None))
def test_empty_or_invalid_prompt_fails_closed(raw_prompt_material: object) -> None:
    outcome = _resolve(
        _authorized_report(),
        InMemoryGenerationInputResolver(
            {"input:001": _snapshot(raw_prompt_material=raw_prompt_material)}
        ),
        _asset_resolver(),
    )

    assert outcome.report.status == "blocked"
    assert [finding.code for finding in outcome.report.findings] == [
        "PROMPT_MATERIALIZATION_FAILED"
    ]
    assert outcome.report.reference_assets_resolved is True


def test_resolver_exceptions_are_redacted_from_findings_and_serialized_report() -> None:
    outcome = _resolve(
        _authorized_report(),
        InMemoryGenerationInputResolver(
            {"input:001": _snapshot()}, failures={"input:001"}
        ),
        _asset_resolver(),
    )

    serialized = outcome.report.model_dump_json()
    assert [finding.code for finding in outcome.report.findings] == ["INPUT_REFERENCE_UNRESOLVABLE"]
    assert "resolver-private-detail" not in serialized
    assert "private prompt material" not in serialized
    assert all("resolver-private-detail" not in finding.model_dump_json() for finding in outcome.report.findings)


def test_resolution_is_canonical_deterministic_and_non_mutating() -> None:
    report = _authorized_report()
    snapshot = _snapshot(required_reference_asset_ids=("asset:002", "asset:001"))
    input_resolver = InMemoryGenerationInputResolver({"input:001": snapshot})
    asset_resolver = _asset_resolver()
    before = (report.model_dump(mode="json"), snapshot.required_reference_asset_ids)

    first = _resolve(report, input_resolver, asset_resolver)
    second = _resolve(report, input_resolver, asset_resolver)

    assert (report.model_dump(mode="json"), snapshot.required_reference_asset_ids) == before
    assert first.report.model_dump(mode="json") == second.report.model_dump(mode="json")
    assert first.materialized_input is not None
    assert tuple(handle.reference_asset_id for handle in first.materialized_input.reference_asset_handles) == (
        "asset:001",
        "asset:002",
    )


def test_source_keeps_provider_execution_io_and_public_exports_out() -> None:
    source = (
        ROOT
        / "src/manga_director/production/next_generation_secure_execution_input_resolution.py"
    ).read_text(encoding="utf-8")
    for forbidden in (
        "manga_director.adapters",
        "manga_director.agents",
        "manga_director.prompting",
        "manga_director.workflow",
        "manga_director.domain.state_machine",
        "GenerationEvidenceEnvelopeDTO",
        ".generate(",
        ".retry(",
        "open(",
        "requests.",
        "httpx.",
        "logging",
    ):
        assert forbidden not in source
    production_init = (ROOT / "src/manga_director/production/__init__.py").read_text(
        encoding="utf-8"
    )
    root_init = (ROOT / "src/manga_director/__init__.py").read_text(encoding="utf-8")
    assert "next_generation_secure_execution_input_resolution" not in production_init
    assert "next_generation_secure_execution_input_resolution" not in root_init
