"""Private D10 in-fence admission checks for a frozen D09-I02 result.

This module cannot apply ``Generated``.  It derives result evidence from the
owner-controlled D09 stores and supplies only a read-only guard to the
canonical LocalFile coordinator.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from typing import Literal

from pydantic import ConfigDict, Field, field_validator

from manga_director.domain.state_machine import PageState
from manga_director.production import future_fake_provider_receipt_journal as d09
from manga_director.production import future_provider_result_evidence_journal as i02
from manga_director.production.director import DirectorModel
from manga_director.production.next_generation_local_durable_asset_owner import (
    LocalDurableAssetOwner,
)
from manga_director.production.next_generation_workflow_application_ledger import (
    WorkflowApplicationLedgerBindingDTO,
)
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.repositories.local_file_durability import RevisionedProjectSnapshot
from manga_director.workflow.contracts import WorkflowContext
from manga_director.workflow.localfile_external_generated_application import (
    _ExternalApplicationFenceContext,
    _ExternalApplicationGuardDecision,
)

_DATABASE_NAME = "future-provider-result-evidence.sqlite3"
_FAKE_PROVIDER = "fake:deterministic"


class _D10Model(DirectorModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _logical(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or any(character.isspace() or ord(character) < 32 for character in value)
        or value.startswith(("/", "\\"))
        or "://" in value
        or ".." in value
    ):
        raise ValueError("D10 requires logical references")
    return value


def _sha256(value: object) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise ValueError("D10 requires SHA-256 identities")
    return value


class GeneratedApplicationExpectedStateV1(_D10Model):
    """Private immutable expectation; it has no application capability."""

    schema_id: Literal["manga_director.future_generated_application_expected_state"] = (
        "manga_director.future_generated_application_expected_state"
    )
    schema_version: Literal["1"] = "1"
    project_id: str
    page_id: str
    target_page_reference: str
    expected_state: Literal["PromptBuilt"] = "PromptBuilt"
    expected_revision: int = Field(ge=1)
    expected_fingerprint: str
    attempt_id: str
    manifest_digest: str
    dispatch_identity: str
    idempotency_identity: str
    attempt_binding_digest: str
    provider_binding_digest: str
    profile_identity: str
    provider_class: Literal["A", "B", "C"]
    receipt_identity: str
    receipt_digest: str
    receipt_sequence: int = Field(ge=1)
    evidence_identity: str
    evidence_digest: str
    logical_output_identity: str
    expected_asset_identity: str
    expected_asset_sha256: str
    expected_asset_volume_serial: int = Field(ge=1)
    expected_asset_file_index: int = Field(ge=1)
    expected_media_type: Literal["image/png"]
    provider_origin_assurance: Literal["UNVERIFIED"]
    storyboard_digest: str
    prompt_digest: str
    package_digest: str

    @field_validator(
        "project_id",
        "page_id",
        "target_page_reference",
        "attempt_id",
        "logical_output_identity",
        "expected_asset_identity",
    )
    @classmethod
    def _logical_reference(cls, value: str) -> str:
        return _logical(value)

    @field_validator(
        "expected_fingerprint",
        "manifest_digest",
        "dispatch_identity",
        "idempotency_identity",
        "attempt_binding_digest",
        "provider_binding_digest",
        "profile_identity",
        "receipt_identity",
        "receipt_digest",
        "evidence_identity",
        "evidence_digest",
        "expected_asset_sha256",
        "storyboard_digest",
        "prompt_digest",
        "package_digest",
    )
    @classmethod
    def _digest_value(cls, value: str) -> str:
        return _sha256(value)

    def model_post_init(self, __context: object) -> None:
        payload = self.model_dump(mode="json", exclude={"package_digest"})
        if self.package_digest != _digest(payload):
            raise ValueError("D10 expected-state digest is invalid")


@dataclass(frozen=True, slots=True)
class _D09Replay:
    binding: d09.D09DispatchBindingV1
    receipt: d09.ProviderSubmissionReceiptV1
    receipt_identity: str
    evidence: i02.ProviderResultEvidenceV1


class _D09ReadOnlyReplayReader:
    """Read frozen D09-I01/I02 only; never invoke their recovery APIs."""

    def __init__(self, repository: LocalFileRepository) -> None:
        root = repository._root
        if not root.is_absolute():
            raise ValueError("trusted LocalFile root is unavailable")
        self._i01 = i02._I01Reader(repository)
        self._database = (
            root.resolve()
            / "_durability"
            / "_future_durable_generation"
            / "provider_result_evidence"
            / _DATABASE_NAME
        )

    def read(self, attempt_id: str) -> _D09Replay:
        _logical(attempt_id)
        source = self._i01.accepted(attempt_id)
        if source is None or not self._database.is_file():
            raise ValueError("D09 accepted replay is unavailable")
        connection = sqlite3.connect(f"{self._database.as_uri()}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        try:
            i02._ResultJournal._validate_schema(connection)
            state = connection.execute(
                "SELECT * FROM d09i02_journal_state WHERE journal_identity = ?",
                (source.binding.binding_identity,),
            ).fetchone()
            if state is None or state["phase"] != "RESULT_CAPTURED" or state["availability_gate"] != "CLEAR":
                raise ValueError("D09 result replay is unavailable")
            replay = object.__new__(i02._ResultJournal)
            replay._replay(connection, source, state)
            evidence = replay._accepted(source, connection)
            if evidence is None:
                raise ValueError("D09 accepted result is unavailable")
            return _D09Replay(source.binding, source.receipt, source.receipt_identity, evidence)
        finally:
            connection.close()


def prepare_expected_state(
    repository: LocalFileRepository,
    asset_owner: LocalDurableAssetOwner,
    *,
    attempt_id: str,
    logical_output_identity: str,
    expected_asset_identity: str,
) -> GeneratedApplicationExpectedStateV1:
    """Build a non-authoritative D10 expectation from owner-read frozen evidence."""

    replay = _D09ReadOnlyReplayReader(repository).read(attempt_id)
    evidence = replay.evidence
    output = _selected_output(evidence, logical_output_identity)
    snapshot = repository._load_revisioned(evidence.project_id)
    page = snapshot.project.page(_page_number(evidence.page_id))
    target = page.metadata.get("future_generation_target_reference")
    if (
        page.state != PageState.PROMPT_BUILT
        or not isinstance(target, str)
        or target != evidence.execution_target_reference
        or page.storyboard is None
        or page.prompt is None
    ):
        raise ValueError("D10 current page is unavailable")
    lease = asset_owner._verify_for_generated_application(
        attempt_id=evidence.attempt_id,
        provider_reference=_FAKE_PROVIDER,
        output_asset_id=expected_asset_identity,
        expected_sha256=output.sha256,
        expected_media_type=output.media_type,
    )
    try:
        identity = lease._identity
    finally:
        lease.release()
    values: dict[str, object] = {
        "project_id": evidence.project_id,
        "page_id": evidence.page_id,
        "target_page_reference": evidence.execution_target_reference,
        "expected_state": "PromptBuilt",
        "expected_revision": snapshot.revision,
        "expected_fingerprint": snapshot.fingerprint,
        "attempt_id": evidence.attempt_id,
        "manifest_digest": evidence.manifest_digest,
        "dispatch_identity": evidence.dispatch_identity,
        "idempotency_identity": evidence.idempotency_identity,
        "attempt_binding_digest": evidence.attempt_binding_digest,
        "provider_binding_digest": evidence.provider_binding_digest,
        "profile_identity": evidence.profile_identity,
        "provider_class": evidence.provider_class,
        "receipt_identity": evidence.receipt_identity,
        "receipt_digest": evidence.receipt_digest,
        "receipt_sequence": evidence.receipt_sequence,
        "evidence_identity": evidence.evidence_identity,
        "evidence_digest": evidence.evidence_digest,
        "logical_output_identity": output.logical_output_id,
        "expected_asset_identity": expected_asset_identity,
        "expected_asset_sha256": output.sha256,
        "expected_asset_volume_serial": identity.volume_serial,
        "expected_asset_file_index": identity.file_index,
        "expected_media_type": output.media_type,
        "provider_origin_assurance": evidence.provider_origin_assurance,
        "storyboard_digest": _digest(page.storyboard),
        "prompt_digest": _digest(page.prompt),
    }
    with_schema = {
        "schema_id": "manga_director.future_generated_application_expected_state",
        "schema_version": "1",
        **values,
    }
    return GeneratedApplicationExpectedStateV1.model_validate(
        {**with_schema, "package_digest": _digest(with_schema)}
    )


class LocalFileGeneratedApplicationPreApplyGuard:
    """Private D10 guard: compare immutable expectation under the page fence."""

    def __init__(
        self,
        repository: LocalFileRepository,
        asset_owner: LocalDurableAssetOwner,
        expected_state: GeneratedApplicationExpectedStateV1,
    ) -> None:
        if not isinstance(repository, LocalFileRepository) or not isinstance(
            asset_owner, LocalDurableAssetOwner
        ):
            raise ValueError("trusted LocalFile D10 owners are required")
        if (
            GeneratedApplicationExpectedStateV1.model_validate(expected_state.model_dump())
            != expected_state
        ):
            raise ValueError("D10 expected state is invalid")
        self._reader = _D09ReadOnlyReplayReader(repository)
        self._asset_owner = asset_owner
        self._expected = expected_state

    def validate(
        self,
        binding: WorkflowApplicationLedgerBindingDTO,
        snapshot: object,
        context: WorkflowContext,
        fence_context: _ExternalApplicationFenceContext,
    ) -> _ExternalApplicationGuardDecision:
        try:
            if not isinstance(snapshot, RevisionedProjectSnapshot):
                return _reject("SNAPSHOT_INVALID")
            if (
                not isinstance(fence_context, _ExternalApplicationFenceContext)
                or not fence_context._matches(binding, snapshot, context)
            ):
                return _reject("FENCE_CONTEXT_INVALID")
            expected = self._expected
            if not _binding_matches(binding, expected):
                return _reject("BINDING_MISMATCH")
            if snapshot.revision != expected.expected_revision:
                return _reject("STALE_REVISION")
            if snapshot.fingerprint != expected.expected_fingerprint:
                return _reject("STALE_FINGERPRINT")
            page = snapshot.project.page(_page_number(expected.page_id))
            if (
                context.state != PageState.PROMPT_BUILT
                or page.state != PageState.PROMPT_BUILT
                or context.page.get("project_id") != expected.project_id
                or context.page.get("page_id") != expected.page_id
                or page.metadata.get("future_generation_target_reference")
                != expected.target_page_reference
                or page.storyboard is None
                or page.prompt is None
                or _digest(page.storyboard) != expected.storyboard_digest
                or _digest(page.prompt) != expected.prompt_digest
            ):
                return _reject("CURRENT_PAGE_MISMATCH")
            replay = self._reader.read(expected.attempt_id)
            if not _replay_matches(replay, expected):
                return _reject("D09_REPLAY_MISMATCH")
            lease = self._asset_owner._verify_for_generated_application(
                attempt_id=expected.attempt_id,
                provider_reference=_FAKE_PROVIDER,
                output_asset_id=expected.expected_asset_identity,
                expected_sha256=expected.expected_asset_sha256,
                expected_media_type=expected.expected_media_type,
            )
            if (
                lease._identity.volume_serial != expected.expected_asset_volume_serial
                or lease._identity.file_index != expected.expected_asset_file_index
            ):
                lease.release()
                return _reject("ASSET_IDENTITY_MISMATCH")
            return _ExternalApplicationGuardDecision(True, "ALLOW", lease)
        except Exception:
            return _reject("UNAVAILABLE")


def _binding_matches(
    binding: WorkflowApplicationLedgerBindingDTO, expected: GeneratedApplicationExpectedStateV1
) -> bool:
    return (
        binding.project_id == expected.project_id
        and binding.page_id == expected.page_id
        and binding.target_page_reference == expected.target_page_reference
        and binding.attempt_id == expected.attempt_id
        and binding.provider_reference == _FAKE_PROVIDER
        and binding.output_asset_id == expected.expected_asset_identity
        and binding.source_state == "PromptBuilt"
        and binding.target_state == "Generated"
    )


def _replay_matches(replay: _D09Replay, expected: GeneratedApplicationExpectedStateV1) -> bool:
    evidence = replay.evidence
    try:
        output = _selected_output(evidence, expected.logical_output_identity)
    except ValueError:
        return False
    return (
        replay.binding.attempt_id == expected.attempt_id
        and replay.binding.dispatch_identity == expected.dispatch_identity
        and replay.binding.manifest_digest == expected.manifest_digest
        and replay.binding.idempotency_identity == expected.idempotency_identity
        and replay.binding.attempt_binding_digest == expected.attempt_binding_digest
        and replay.binding.provider_binding_digest == expected.provider_binding_digest
        and replay.binding.profile_identity == expected.profile_identity
        and replay.binding.provider_class == expected.provider_class
        and replay.receipt_identity == expected.receipt_identity
        and replay.receipt.submission_evidence_digest == expected.receipt_digest
        and replay.receipt.sequence == expected.receipt_sequence
        and evidence.project_id == expected.project_id
        and evidence.page_id == expected.page_id
        and evidence.execution_target_reference == expected.target_page_reference
        and evidence.attempt_id == expected.attempt_id
        and evidence.manifest_digest == expected.manifest_digest
        and evidence.dispatch_identity == expected.dispatch_identity
        and evidence.idempotency_identity == expected.idempotency_identity
        and evidence.attempt_binding_digest == expected.attempt_binding_digest
        and evidence.provider_binding_digest == expected.provider_binding_digest
        and evidence.profile_identity == expected.profile_identity
        and evidence.provider_class == expected.provider_class
        and evidence.receipt_identity == expected.receipt_identity
        and evidence.receipt_digest == expected.receipt_digest
        and evidence.receipt_sequence == expected.receipt_sequence
        and evidence.evidence_identity == expected.evidence_identity
        and evidence.evidence_digest == expected.evidence_digest
        and evidence.provider_identifier == _FAKE_PROVIDER
        and evidence.capture_mode == "FAKE_OBSERVATION"
        and evidence.provider_origin_assurance == "UNVERIFIED"
        and output.sha256 == expected.expected_asset_sha256
        and output.media_type == expected.expected_media_type
    )


def _selected_output(
    evidence: i02.ProviderResultEvidenceV1, logical_output_identity: str
) -> i02.OutputEvidenceV1:
    _logical(logical_output_identity)
    matches = tuple(
        output for output in evidence.output_evidence if output.logical_output_id == logical_output_identity
    )
    if len(matches) != 1:
        raise ValueError("D10 logical output is unavailable")
    return matches[0]


def _page_number(value: str) -> int:
    _logical(value)
    if not value.isdecimal() or int(value) < 1:
        raise ValueError("D10 page identity is invalid")
    return int(value)


def _reject(code: str) -> _ExternalApplicationGuardDecision:
    return _ExternalApplicationGuardDecision(False, code)
