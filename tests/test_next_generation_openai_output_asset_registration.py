"""Focused fake-only contracts for OpenAI output asset-owner registration."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Literal, cast

import pytest

from manga_director.production.next_generation_asset_registration import (
    AssetRegistrationRequest,
    AssetRegistrationRuntimeResult,
    OutputAssetRegistrationService,
)
from manga_director.production.next_generation_generation_evidence import (
    EvidenceValueDTO,
    GenerationOutputEvidenceDTO,
)
from manga_director.production.next_generation_openai_output_asset_registration import (
    AssetOwnerSink,
    OpenAIOutputAssetRegistrationAdapter,
    OpenAIOutputAssetRegistrationRequest,
)
from manga_director.production.next_generation_openai_provider_adapter import (
    OpenAIInMemoryGeneratedImageMaterial,
)
from manga_director.production.next_generation_provider_invocation import (
    OpaqueGeneratedOutputHandle,
    ProviderInvocationOutcome,
    ProviderInvocationReport,
)

ROOT = Path(__file__).resolve().parents[1]
_ATTEMPT_ID = "attempt:openai:001"
_PROVIDER_REFERENCE = "provider:openai"
_PRIVATE_BYTES = b"PRIVATE-OPENAI-IMAGE-BYTES"


@dataclass(frozen=True)
class _StoredRegistration:
    provider_reference: str
    digest: str
    output: GenerationOutputEvidenceDTO


@dataclass(frozen=True)
class _OwnerCall:
    attempt_id: str
    provider_reference: str
    media_type_hint: str


class InMemoryAssetOwnerSink(AssetOwnerSink):
    """Owner-controlled fake with private digest equivalence and staged cleanup."""

    def __init__(
        self,
        *,
        mode: Literal[
            "registered",
            "storage_failed",
            "registry_failed",
            "registry_failed_cleanup_failed",
            "unconfirmed",
            "malformed",
            "unprovable",
            "attempt_mismatch",
            "provider_mismatch",
            "raises",
        ] = "registered",
        confirmed_media_type: str | None = "image/png",
        output_content_hash: EvidenceValueDTO | None = None,
    ) -> None:
        self.mode = mode
        self.confirmed_media_type = confirmed_media_type
        self.output_content_hash = output_content_hash
        self.calls: list[_OwnerCall] = []
        self.storage_stage_calls = 0
        self.registry_stage_calls = 0
        self.cleanup_calls = 0
        self.cleanup_failed = False
        self._registrations: dict[str, _StoredRegistration] = {}

    def register(
        self, request: OpenAIOutputAssetRegistrationRequest
    ) -> AssetRegistrationRuntimeResult | object:
        self.calls.append(
            _OwnerCall(
                attempt_id=request.attempt_id,
                provider_reference=request.provider_reference,
                media_type_hint=request.media_type_hint,
            )
        )
        existing = self._registrations.get(request.attempt_id)
        if existing is not None:
            if self.mode == "unprovable":
                return _conflict(request)
            digest = sha256(request.image_bytes).hexdigest()
            if (
                existing.provider_reference != request.provider_reference
                or existing.digest != digest
            ):
                return _conflict(request)
            return _registered(request, existing.output)

        if self.mode == "raises":
            raise RuntimeError("owner-native-private-detail")
        if self.mode == "malformed":
            return object()
        self.storage_stage_calls += 1
        if self.mode == "storage_failed":
            return _failed(request)
        if self.mode in {"registry_failed", "registry_failed_cleanup_failed"}:
            self.registry_stage_calls += 1
            self.cleanup_calls += 1
            self.cleanup_failed = self.mode == "registry_failed_cleanup_failed"
            return _failed(request)

        self.registry_stage_calls += 1
        output = GenerationOutputEvidenceDTO(
            output_asset_id=f"asset:generated:owner:{len(self._registrations) + 1:03d}",
            output_content_hash=self.output_content_hash,
            media_type=self.confirmed_media_type,
        )
        self._registrations[request.attempt_id] = _StoredRegistration(
            provider_reference=request.provider_reference,
            digest=sha256(request.image_bytes).hexdigest(),
            output=output,
        )
        if self.mode == "unconfirmed":
            return AssetRegistrationRuntimeResult(
                attempt_id=request.attempt_id,
                provider_reference=request.provider_reference,
                outcome="registered",
                output=output,
                durable_registration_confirmed=False,
            )
        if self.mode == "attempt_mismatch":
            return AssetRegistrationRuntimeResult(
                attempt_id="attempt:other",
                provider_reference=request.provider_reference,
                outcome="registered",
                output=output,
                durable_registration_confirmed=True,
            )
        if self.mode == "provider_mismatch":
            return AssetRegistrationRuntimeResult(
                attempt_id=request.attempt_id,
                provider_reference="provider:other",
                outcome="registered",
                output=output,
                durable_registration_confirmed=True,
            )
        return _registered(request, output)


def _registered(
    request: OpenAIOutputAssetRegistrationRequest, output: GenerationOutputEvidenceDTO
) -> AssetRegistrationRuntimeResult:
    return AssetRegistrationRuntimeResult(
        attempt_id=request.attempt_id,
        provider_reference=request.provider_reference,
        outcome="registered",
        output=output,
        durable_registration_confirmed=True,
    )


def _failed(request: OpenAIOutputAssetRegistrationRequest) -> AssetRegistrationRuntimeResult:
    return AssetRegistrationRuntimeResult(
        attempt_id=request.attempt_id,
        provider_reference=request.provider_reference,
        outcome="failed",
    )


def _conflict(request: OpenAIOutputAssetRegistrationRequest) -> AssetRegistrationRuntimeResult:
    return AssetRegistrationRuntimeResult(
        attempt_id=request.attempt_id,
        provider_reference=request.provider_reference,
        outcome="idempotency_conflict",
    )


def _outcome(
    *,
    attempt_id: str = _ATTEMPT_ID,
    provider_reference: str = _PROVIDER_REFERENCE,
    output: object = _PRIVATE_BYTES,
) -> ProviderInvocationOutcome:
    report = ProviderInvocationReport.model_construct(
        secure_execution_input_resolution_report=None,
        attempt_id=attempt_id,
        provider_reference=provider_reference,
        findings=(),
        status="succeeded",
        succeeded=True,
        invocation_performed=True,
    )
    return ProviderInvocationOutcome(
        report=report,
        output_handle=OpaqueGeneratedOutputHandle(output),
    )


def _openai_outcome(
    *,
    attempt_id: str = _ATTEMPT_ID,
    provider_reference: str = _PROVIDER_REFERENCE,
    image_bytes: object = _PRIVATE_BYTES,
    media_type: str = "image/png",
) -> ProviderInvocationOutcome:
    return _outcome(
        attempt_id=attempt_id,
        provider_reference=provider_reference,
        output=OpenAIInMemoryGeneratedImageMaterial(
            image_bytes=cast(bytes, image_bytes), media_type=media_type
        ),
    )


def _register(
    outcome: ProviderInvocationOutcome,
    sink: InMemoryAssetOwnerSink,
    *,
    attempt_id: str = _ATTEMPT_ID,
):
    return OutputAssetRegistrationService().register(
        attempt_id,
        outcome,
        OpenAIOutputAssetRegistrationAdapter(sink),
    )


def test_confirmed_two_phase_commit_exposes_owner_issued_logical_asset_only() -> None:
    sink = InMemoryAssetOwnerSink()
    report = _register(_openai_outcome(), sink)

    assert report.status == "registered"
    assert report.registered is True
    assert report.registered_output is not None
    assert report.registered_output.output.output_asset_id == "asset:generated:owner:001"
    assert sink.storage_stage_calls == 1
    assert sink.registry_stage_calls == 1
    assert sink.calls[0].media_type_hint == "image/png"


def test_same_attempt_and_private_digest_replays_the_same_owner_asset() -> None:
    sink = InMemoryAssetOwnerSink()
    first = _register(_openai_outcome(), sink)
    second = _register(_openai_outcome(), sink)

    assert first.registered_output is not None
    assert second.registered_output is not None
    assert first.registered_output.output.output_asset_id == second.registered_output.output.output_asset_id
    assert sink.storage_stage_calls == 1
    assert sink.registry_stage_calls == 1


def test_same_attempt_different_or_unprovable_private_material_conflicts() -> None:
    sink = InMemoryAssetOwnerSink()
    assert _register(_openai_outcome(), sink).registered is True
    different = _register(_openai_outcome(image_bytes=b"DIFFERENT-PRIVATE-BYTES"), sink)
    unprovable_sink = InMemoryAssetOwnerSink(mode="unprovable")
    assert _register(_openai_outcome(), unprovable_sink).registered is True
    unprovable = _register(_openai_outcome(), unprovable_sink)

    assert [item.code for item in different.findings] == [
        "OUTPUT_REGISTRATION_IDEMPOTENCY_CONFLICT"
    ]
    assert [item.code for item in unprovable.findings] == [
        "OUTPUT_REGISTRATION_IDEMPOTENCY_CONFLICT"
    ]


def test_different_attempts_are_independent_owner_registrations() -> None:
    sink = InMemoryAssetOwnerSink()
    first = _register(_openai_outcome(), sink)
    second = _register(
        _openai_outcome(attempt_id="attempt:openai:002"), sink, attempt_id="attempt:openai:002"
    )

    assert first.registered_output is not None
    assert second.registered_output is not None
    assert first.registered_output.output.output_asset_id != second.registered_output.output.output_asset_id


@pytest.mark.parametrize(
    ("mode", "cleanup_calls", "cleanup_failed"),
    (
        ("storage_failed", 0, False),
        ("registry_failed", 1, False),
        ("registry_failed_cleanup_failed", 1, True),
    ),
)
def test_stage_failures_and_private_cleanup_remain_redacted(
    mode: Literal["storage_failed", "registry_failed", "registry_failed_cleanup_failed"],
    cleanup_calls: int,
    cleanup_failed: bool,
) -> None:
    sink = InMemoryAssetOwnerSink(mode=mode)
    report = _register(_openai_outcome(), sink)

    assert report.status == "blocked"
    assert report.registered_output is None
    assert [item.code for item in report.findings] == ["OUTPUT_REGISTRATION_FAILED"]
    assert sink.cleanup_calls == cleanup_calls
    assert sink.cleanup_failed is cleanup_failed
    assert "cleanup" not in report.model_dump_json()


@pytest.mark.parametrize(
    ("mode", "expected_code"),
    (
        ("unconfirmed", "OUTPUT_REGISTRATION_RESULT_INVALID"),
        ("malformed", "OUTPUT_REGISTRATION_RESULT_INVALID"),
        ("attempt_mismatch", "REGISTRATION_ATTEMPT_MISMATCH"),
        ("provider_mismatch", "REGISTRATION_PROVIDER_MISMATCH"),
        ("raises", "OUTPUT_REGISTRATION_FAILED"),
    ),
)
def test_unconfirmed_malformed_and_mismatched_owner_results_fail_closed(
    mode: Literal["unconfirmed", "malformed", "attempt_mismatch", "provider_mismatch", "raises"],
    expected_code: str,
) -> None:
    report = _register(_openai_outcome(), InMemoryAssetOwnerSink(mode=mode))

    assert report.status == "blocked"
    assert report.registered is False
    assert report.registered_output is None
    assert [item.code for item in report.findings] == [expected_code]


@pytest.mark.parametrize(
    "outcome",
    (
        _outcome(output=None),
        _outcome(output=object()),
        _openai_outcome(image_bytes=b""),
        _openai_outcome(image_bytes=_PRIVATE_BYTES, media_type="image/jpeg"),
    ),
)
def test_missing_wrong_or_malformed_opaque_material_fails_closed(
    outcome: ProviderInvocationOutcome,
) -> None:
    sink = InMemoryAssetOwnerSink()
    report = _register(outcome, sink)

    assert report.status == "blocked"
    assert report.registered_output is None
    assert [item.code for item in report.findings] == ["OUTPUT_REGISTRATION_FAILED"]
    assert sink.calls == []


def test_owner_confirmed_media_type_and_optional_factual_hash_are_preserved() -> None:
    hash_evidence = EvidenceValueDTO(availability="known", value="owner-factual-hash")
    report = _register(
        _openai_outcome(),
        InMemoryAssetOwnerSink(
            confirmed_media_type="image/png", output_content_hash=hash_evidence
        ),
    )

    assert report.registered_output is not None
    output = report.registered_output.output
    assert output.media_type == "image/png"
    assert output.output_content_hash == hash_evidence


def test_caller_input_is_unchanged_and_reports_are_deterministic_and_redacted() -> None:
    outcome = _openai_outcome()
    before = outcome.report.model_dump(mode="json")
    sink = InMemoryAssetOwnerSink()
    first = _register(outcome, sink)
    second = _register(outcome, sink)

    assert outcome.report.model_dump(mode="json") == before
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    serialized = first.model_dump_json()
    for private_value in (
        "PRIVATE-OPENAI-IMAGE-BYTES",
        "owner-native-private-detail",
        "asset_owner_sink",
        "sha256",
        "storage_path",
    ):
        assert private_value not in serialized


def test_adapter_does_not_retain_private_material_after_register_returns() -> None:
    sink = InMemoryAssetOwnerSink()
    adapter = OpenAIOutputAssetRegistrationAdapter(sink)
    request = AssetRegistrationRequest(
        attempt_id=_ATTEMPT_ID,
        provider_reference=_PROVIDER_REFERENCE,
        output_handle=OpaqueGeneratedOutputHandle(
            OpenAIInMemoryGeneratedImageMaterial(image_bytes=_PRIVATE_BYTES)
        ),
    )

    result = adapter.register(request)

    assert result.durable_registration_confirmed is True
    assert not any("image" in name or "byte" in name for name in vars(adapter))


def test_source_keeps_real_io_evidence_and_public_exports_out() -> None:
    source = (
        ROOT
        / "src/manga_director/production/next_generation_openai_output_asset_registration.py"
    ).read_text(encoding="utf-8")
    for forbidden in (
        "open(",
        "requests.",
        "httpx.",
        "sqlite",
        "boto",
        "GenerationEvidenceEnvelopeDTO",
        "CredentialManager",
        "hashlib",
        "logging",
    ):
        assert forbidden not in source
    production_init = (ROOT / "src/manga_director/production/__init__.py").read_text(
        encoding="utf-8"
    )
    root_init = (ROOT / "src/manga_director/__init__.py").read_text(encoding="utf-8")
    assert "next_generation_openai_output_asset_registration" not in production_init
    assert "next_generation_openai_output_asset_registration" not in root_init
