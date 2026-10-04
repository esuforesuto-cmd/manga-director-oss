"""Private R18 durable binding authority (construction boundary)."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, cast

from manga_director.domain.state_machine import PageState
from manga_director.production import (
    future_real_delivery_i02_real_asset_delivery_journal as i02_journal,
)
from manga_director.production.future_real_delivery_r18_construction import (
    PrivateR18CompositionFactoryV1,
    _R18ConstructionGrantV1,
    _R18LockHeldInvocationV1,
)
from manga_director.production.next_generation_generation_evidence import (
    GenerationEvidenceEnvelopeDTO,
)
from manga_director.production.next_generation_local_durable_asset_owner import (
    LocalDurableAssetOwner,
    _AssetVerificationIntegrityFailure,
)
from manga_director.repositories.local_file import LocalFileRepository

_SCHEMA_ID: Final = "manga_director.real_delivery_binding_authority"
_SCHEMA_VERSION: Final = 1
_META_TABLE: Final = "real_delivery_binding_schema_meta"
_RECORD_TABLE: Final = "real_delivery_binding_records"
_EVIDENCE_TABLE: Final = "generation_evidence"
_EVIDENCE_FILENAME: Final = "generation-evidence.sqlite3"
_EVIDENCE_SCHEMA_VERSION: Final = 1
_EVIDENCE_STATUSES: Final = {"ready", "needs_evidence", "needs_review"}
_MAX_BINDING_JSON_BYTES: Final = 8 * 1024
_BINDING_KEYS: Final = frozenset(
    {
        "schema_id", "schema_version", "delivery_identity", "i02_binding_digest",
        "i02_completion_sequence", "i02_completion_event_digest", "canonical_result_identity",
        "attempt_id", "provider_reference", "logical_output_id", "asset_id",
        "asset_registration_digest", "asset_sha256", "expected_byte_length", "media_type",
        "project_id", "page_id", "target_page_reference", "dispatch_identity",
        "idempotency_identity", "submission_receipt_identity", "evidence_identity",
        "evidence_persistence_identity", "evidence_status", "workflow_source_state",
        "workflow_target_state", "storyboard_digest", "prompt_digest", "page_revision",
        "page_fingerprint", "application_binding_identity",
    }
)


@dataclass(frozen=True, slots=True)
class _EvidenceFactsV1:
    """Immutable facts read directly from the existing evidence store."""

    attempt_id: str
    provider_reference: str
    logical_output_id: str
    asset_sha256: str
    media_type: str
    evidence_identity: str
    evidence_persistence_identity: str
    evidence_status: str


@dataclass(frozen=True, slots=True)
class _CompletedI02FactsV1:
    """Immutable facts returned only by an exact completed I02 replay."""

    delivery_identity: str
    binding_digest: str
    completion_sequence: int
    completion_event_digest: str
    attempt_id: str
    project_id: str
    page_id: str
    target_page_reference: str
    provider_reference: str
    dispatch_identity: str
    idempotency_identity: str
    submission_receipt_identity: str
    logical_output_id: str
    canonical_result_identity: str
    asset_sha256: str
    expected_byte_length: int
    media_type: str
    asset_id: str
    asset_registration_digest: str


@dataclass(frozen=True, slots=True)
class _CurrentPageFactsV1:
    """Current pre-application facts read from the trusted LocalFile repository."""

    project_id: str
    page_id: str
    target_page_reference: str
    storyboard_digest: str
    prompt_digest: str
    revision: int
    fingerprint: str


@dataclass(frozen=True, slots=True)
class _BindingRecordV1:
    """Private immutable R18 record; it conveys facts, never application authority."""

    binding_identity: str
    binding_digest: str
    binding_json: str
    projection: dict[str, object]


@dataclass(frozen=True, slots=True)
class _HistoricalBindingFactsV1:
    """Private R20 facts; they convey no current-page or application authority."""

    binding_identity: str
    binding_digest: str
    application_binding_identity: str
    delivery_identity: str
    i02_binding_digest: str
    i02_completion_sequence: int
    i02_completion_event_digest: str
    canonical_result_identity: str
    attempt_id: str
    project_id: str
    page_id: str
    target_page_reference: str
    provider_reference: str
    dispatch_identity: str
    idempotency_identity: str
    submission_receipt_identity: str
    logical_output_id: str
    asset_id: str
    asset_registration_digest: str
    asset_sha256: str
    expected_byte_length: int
    media_type: str
    evidence_identity: str
    evidence_persistence_identity: str
    evidence_status: str
    historical_storyboard_digest: str
    historical_prompt_digest: str
    historical_page_revision: int
    historical_page_fingerprint: str


class _BindingReplayFailureV1(ValueError):
    """Private structured outcome for the read-only R18/R20 replay boundary."""

    __slots__ = ("outcome",)

    outcome: Literal["CORRUPT", "RECOVERY_REQUIRED", "NOT_FOUND"]

    def __init__(self, outcome: Literal["CORRUPT", "RECOVERY_REQUIRED", "NOT_FOUND"]) -> None:
        super().__init__(outcome)
        self.outcome = outcome


def _corrupt() -> _BindingReplayFailureV1:
    return _BindingReplayFailureV1("CORRUPT")


def _recovery_required() -> _BindingReplayFailureV1:
    return _BindingReplayFailureV1("RECOVERY_REQUIRED")


def _not_found() -> _BindingReplayFailureV1:
    return _BindingReplayFailureV1("NOT_FOUND")


def _regular_file(path: Path) -> bool:
    try:
        return stat.S_ISREG(path.stat().st_mode)
    except OSError:
        return False


def _is_sha256(value: object) -> bool:
    return type(value) is str and len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def _is_reparse_point(path: Path) -> bool:
    try:
        attributes = path.stat().st_file_attributes
    except OSError:
        return False
    marker = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(path.is_symlink() or marker and attributes & marker)


def _evidence_canonical_json(envelope: GenerationEvidenceEnvelopeDTO) -> str:
    return json.dumps(
        envelope.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )


def _digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_json(value: dict[str, object]) -> str:
    """Encode only the frozen R18 identity domain, without value normalization."""

    if set(value) - _BINDING_KEYS or any(type(item) not in (str, int) for item in value.values()):
        raise _corrupt()
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True, allow_nan=False
    )


def _binding_json_is_within_limit(binding_json: str) -> bool:
    try:
        return len(binding_json.encode("utf-8")) <= _MAX_BINDING_JSON_BYTES
    except UnicodeError:
        return False


def _binding_record_from_projection(
    facts: _CompletedI02FactsV1,
    evidence: _EvidenceFactsV1,
    page: _CurrentPageFactsV1,
) -> _BindingRecordV1:
    """Build the only frozen projection from independently reread facts."""

    if (
        facts.attempt_id != evidence.attempt_id
        or facts.provider_reference != evidence.provider_reference
        or facts.logical_output_id != evidence.logical_output_id
        or facts.asset_sha256 != evidence.asset_sha256
        or facts.media_type != evidence.media_type
        or facts.project_id != page.project_id
        or facts.page_id != page.page_id
        or facts.target_page_reference != page.target_page_reference
    ):
        raise _corrupt()
    preliminary: dict[str, object] = {
        "schema_id": _SCHEMA_ID,
        "schema_version": _SCHEMA_VERSION,
        "delivery_identity": facts.delivery_identity,
        "i02_binding_digest": facts.binding_digest,
        "i02_completion_sequence": facts.completion_sequence,
        "i02_completion_event_digest": facts.completion_event_digest,
        "canonical_result_identity": facts.canonical_result_identity,
        "attempt_id": facts.attempt_id,
        "provider_reference": facts.provider_reference,
        "logical_output_id": facts.logical_output_id,
        "asset_id": facts.asset_id,
        "asset_registration_digest": facts.asset_registration_digest,
        "asset_sha256": facts.asset_sha256,
        "expected_byte_length": facts.expected_byte_length,
        "media_type": facts.media_type,
        "project_id": facts.project_id,
        "page_id": facts.page_id,
        "target_page_reference": facts.target_page_reference,
        "dispatch_identity": facts.dispatch_identity,
        "idempotency_identity": facts.idempotency_identity,
        "submission_receipt_identity": facts.submission_receipt_identity,
        "evidence_identity": evidence.evidence_identity,
        "evidence_persistence_identity": evidence.evidence_persistence_identity,
        "evidence_status": evidence.evidence_status,
        "workflow_source_state": "PromptBuilt",
        "workflow_target_state": "Generated",
        "storyboard_digest": page.storyboard_digest,
        "prompt_digest": page.prompt_digest,
        "page_revision": page.revision,
        "page_fingerprint": page.fingerprint,
    }
    application_binding_identity = _digest_text(_canonical_json(preliminary))
    projection = {**preliminary, "application_binding_identity": application_binding_identity}
    binding_json = _canonical_json(projection)
    if not _binding_json_is_within_limit(binding_json):
        raise _corrupt()
    binding_identity = _digest_text(binding_json)
    return _BindingRecordV1(binding_identity, binding_identity, binding_json, projection)


def _evidence_persistence_identity(
    *,
    attempt_id: str,
    provider_reference: str,
    evidence_identity: str,
    payload_digest: str,
    binding_fingerprint: str,
    evidence_status: str,
) -> str:
    return _digest_text(
        json.dumps(
            {
                "attempt_id": attempt_id,
                "binding_fingerprint": binding_fingerprint,
                "evidence_identity": evidence_identity,
                "evidence_status": evidence_status,
                "payload_digest": payload_digest,
                "provider_reference": provider_reference,
                "schema_id": "manga_director.real_delivery_evidence_persistence",
                "schema_version": 1,
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            allow_nan=False,
        )
    )


def _validate_evidence_schema(connection: sqlite3.Connection) -> None:
    if _user_version(connection) != _EVIDENCE_SCHEMA_VERSION:
        raise _corrupt()
    if _user_objects(connection) != (("table", _EVIDENCE_TABLE),):
        raise _corrupt()
    _validate_table(
        connection,
        _EVIDENCE_TABLE,
        (
            (0, "attempt_id", "TEXT", 0, None, 1),
            (1, "payload_json", "TEXT", 1, None, 0),
            (2, "payload_digest", "TEXT", 1, None, 0),
            (3, "provider_reference", "TEXT", 1, None, 0),
            (4, "binding_fingerprint", "TEXT", 1, None, 0),
            (5, "evidence_status", "TEXT", 1, None, 0),
        ),
        (("sqlite_autoindex_generation_evidence_1", 1, "pk", 0, "attempt_id"),),
    )


def _evidence_facts_from_rows(
    rows: list[tuple[object, ...]], evidence_identity: str
) -> _EvidenceFactsV1:
    if len(rows) != 1 or len(rows[0]) != 6:
        raise _corrupt()
    attempt_id, payload_json, payload_digest, provider_reference, fingerprint, status = rows[0]
    if not all(type(value) is str for value in rows[0]):
        raise _corrupt()
    exact_attempt_id = cast(str, attempt_id)
    exact_payload_json = cast(str, payload_json)
    exact_payload_digest = cast(str, payload_digest)
    exact_provider_reference = cast(str, provider_reference)
    exact_fingerprint = cast(str, fingerprint)
    exact_status = cast(str, status)
    if (
        exact_payload_digest != evidence_identity
        or not _is_sha256(exact_payload_digest)
        or not _is_sha256(exact_fingerprint)
        or exact_status not in _EVIDENCE_STATUSES
        or _digest_text(exact_payload_json) != exact_payload_digest
    ):
        raise _corrupt()
    try:
        loaded = json.loads(exact_payload_json)
        envelope = GenerationEvidenceEnvelopeDTO.model_validate(loaded)
    except (TypeError, ValueError) as error:
        raise _corrupt() from error
    if _evidence_canonical_json(envelope) != exact_payload_json or envelope.attempt_id != exact_attempt_id:
        raise _corrupt()
    output = envelope.output
    asset_hash = getattr(output.output_content_hash, "value", None)
    if (
        type(output.output_asset_id) is not str
        or output.media_type != "image/png"
        or not _is_sha256(asset_hash)
        or _binding_fingerprint(exact_attempt_id, exact_provider_reference, output.output_asset_id)
        != exact_fingerprint
    ):
        raise _corrupt()
    return _EvidenceFactsV1(
        attempt_id=exact_attempt_id,
        provider_reference=exact_provider_reference,
        logical_output_id=output.output_asset_id,
        asset_sha256=cast(str, asset_hash),
        media_type=output.media_type,
        evidence_identity=evidence_identity,
        evidence_persistence_identity=_evidence_persistence_identity(
            attempt_id=exact_attempt_id,
            provider_reference=exact_provider_reference,
            evidence_identity=evidence_identity,
            payload_digest=exact_payload_digest,
            binding_fingerprint=exact_fingerprint,
            evidence_status=exact_status,
        ),
        evidence_status=exact_status,
    )


def _binding_fingerprint(attempt_id: str, provider_reference: str, output_asset_id: str) -> str:
    return hashlib.sha256(
        "\x00".join((attempt_id, provider_reference, output_asset_id)).encode("utf-8")
    ).hexdigest()


class RealDeliveryBindingAuthorityV1:
    """Private R18 owner; it owns only exact immutable binding records."""

    __slots__ = ("_database_path", "_journal", "_owner", "_repository")

    def __init__(
        self,
        factory: object,
        grant: object | None = None,
        invocation: object | None = None,
    ) -> None:
        if (
            type(factory) is not PrivateR18CompositionFactoryV1
            or type(grant) is not _R18ConstructionGrantV1
            or type(invocation) is not _R18LockHeldInvocationV1
        ):
            raise ValueError("AUTHORITY_REJECTED")
        repository, owner, journal = factory._consume_issued_grant_v1(grant, invocation)
        if (
            type(repository) is not LocalFileRepository
            or type(owner) is not LocalDurableAssetOwner
            or type(journal) is not i02_journal.PrivateRealAssetDeliveryJournal
        ):
            raise ValueError("AUTHORITY_REJECTED")
        try:
            normal_root = repository._next_generation_normal_execution_owner_root()
        except (OSError, ValueError) as error:
            raise ValueError("AUTHORITY_REJECTED") from error
        if (
            owner._root != normal_root / "assets"
            or journal._owner is not owner
            or journal._database_path
            != owner._root
            / "_durability"
            / "_post_lts_real_asset_delivery"
            / "real-asset-delivery.sqlite3"
        ):
            raise ValueError("AUTHORITY_REJECTED")
        self._repository = repository
        self._owner = owner
        self._journal = journal
        self._database_path = (
            owner._root
            / "_durability"
            / "_post_lts_real_delivery_binding"
            / "real-delivery-binding.sqlite3"
        )
        self._initialize_or_validate()

    def _replay_completed_i02_v1(self, delivery_identity: str) -> _CompletedI02FactsV1:
        """Use only the existing I02 replay boundary and require terminal completion."""

        if not _is_sha256(delivery_identity):
            raise ValueError("AUTHORITY_REJECTED")
        try:
            replay = self._journal._replay_v1(delivery_identity)
        except i02_journal._DurableJournalCorruptV1 as error:
            raise _corrupt() from error
        except ValueError as error:
            raise _recovery_required() from error
        if (
            replay.status is not i02_journal._DeliveryStatusV1.DELIVERY_COMPLETED
        ):
            raise _recovery_required()
        if (
            replay.asset_id is None
            or replay.asset_registration_digest is None
            or replay.binding.delivery_identity != delivery_identity
            or not _is_sha256(replay.last_event_digest)
        ):
            raise _corrupt()
        binding = replay.binding
        return _CompletedI02FactsV1(
            delivery_identity=binding.delivery_identity,
            binding_digest=binding.delivery_identity,
            completion_sequence=replay.sequence,
            completion_event_digest=replay.last_event_digest,
            attempt_id=binding.attempt_id,
            project_id=binding.project_id,
            page_id=binding.page_id,
            target_page_reference=binding.target_page_reference,
            provider_reference=binding.provider_reference,
            dispatch_identity=binding.dispatch_identity,
            idempotency_identity=binding.idempotency_identity,
            submission_receipt_identity=binding.submission_receipt_identity,
            logical_output_id=binding.logical_output_id,
            canonical_result_identity=binding.canonical_result_identity,
            asset_sha256=binding.asset_sha256,
            expected_byte_length=binding.expected_byte_length,
            media_type=binding.media_type,
            asset_id=replay.asset_id,
            asset_registration_digest=replay.asset_registration_digest,
        )

    def _i02_lineage_exists_v1(self, delivery_identity: str) -> bool:
        """Distinguish one absent selector from an incomplete or unavailable I02 lineage."""

        try:
            self._journal._replay_v1(delivery_identity)
        except i02_journal._UnknownDeliveryIdentityV1:
            return False
        except i02_journal._DurableJournalCorruptV1 as error:
            raise _corrupt() from error
        except ValueError as error:
            if type(error.__cause__) is i02_journal._UnknownDeliveryIdentityV1:
                return False
            raise _recovery_required() from error
        return True

    def _reread_owner_asset_exact_v1(self, facts: _CompletedI02FactsV1) -> None:
        """Validate one live owner lease; its path is never caller authority."""

        try:
            lease = self._owner._verify_for_generated_application(
                attempt_id=facts.attempt_id,
                provider_reference=facts.provider_reference,
                output_asset_id=facts.asset_id,
                expected_sha256=facts.asset_sha256,
                expected_media_type=facts.media_type,
            )
        except OSError as error:
            raise _recovery_required() from error
        except _AssetVerificationIntegrityFailure as error:
            raise _corrupt() from error
        except ValueError as error:
            raise _recovery_required() from error
        try:
            if type(lease._identity.size) is not int or lease._identity.size != facts.expected_byte_length:
                raise _corrupt()
        finally:
            lease.release()

    def _replay_evidence_record_exact_v1(self, evidence_identity: str) -> _EvidenceFactsV1:
        """Read exactly one existing evidence row without a writable fallback."""

        if not _is_sha256(evidence_identity):
            raise ValueError("AUTHORITY_REJECTED")
        database = self._evidence_database_path()
        if not _regular_file(database) or _is_reparse_point(database):
            raise _recovery_required()
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(
                f"{database.as_uri()}?mode=ro", uri=True, timeout=0.0, isolation_level=None
            )
            connection.execute("PRAGMA query_only=ON")
            query_only = connection.execute("PRAGMA query_only").fetchall()
            if query_only != [(1,)]:
                raise _recovery_required()
            connection.execute("BEGIN")
            _validate_evidence_schema(connection)
            rows = connection.execute(
                "SELECT attempt_id, payload_json, payload_digest, provider_reference, "
                "binding_fingerprint, evidence_status FROM generation_evidence "
                "WHERE payload_digest = ?",
                (evidence_identity,),
            ).fetchall()
            if not rows:
                raise _recovery_required()
            facts = _evidence_facts_from_rows(rows, evidence_identity)
            connection.rollback()
            return facts
        except ValueError:
            _rollback(connection)
            raise
        except (OSError, sqlite3.Error, TypeError) as error:
            _rollback(connection)
            raise _recovery_required() from error
        finally:
            if connection is not None:
                connection.close()

    def _replay_evidence_for_completed_i02_v1(
        self, facts: _CompletedI02FactsV1
    ) -> _EvidenceFactsV1:
        """Creation-only bootstrap; the I02 attempt is an internal row selector."""

        database = self._evidence_database_path()
        if not _regular_file(database) or _is_reparse_point(database):
            raise _recovery_required()
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(
                f"{database.as_uri()}?mode=ro", uri=True, timeout=0.0, isolation_level=None
            )
            connection.execute("PRAGMA query_only=ON")
            if connection.execute("PRAGMA query_only").fetchall() != [(1,)]:
                raise _recovery_required()
            connection.execute("BEGIN")
            _validate_evidence_schema(connection)
            rows = connection.execute(
                "SELECT attempt_id, payload_json, payload_digest, provider_reference, "
                "binding_fingerprint, evidence_status FROM generation_evidence WHERE attempt_id = ?",
                (facts.attempt_id,),
            ).fetchall()
            if not rows:
                raise _recovery_required()
            if len(rows) != 1 or len(rows[0]) != 6 or type(rows[0][2]) is not str:
                raise _corrupt()
            evidence = _evidence_facts_from_rows(rows, rows[0][2])
            if (
                evidence.attempt_id != facts.attempt_id
                or evidence.provider_reference != facts.provider_reference
                or evidence.logical_output_id != facts.logical_output_id
                or evidence.asset_sha256 != facts.asset_sha256
                or evidence.media_type != facts.media_type
            ):
                raise _corrupt()
            connection.rollback()
            return evidence
        except ValueError:
            _rollback(connection)
            raise
        except (OSError, sqlite3.Error, TypeError) as error:
            _rollback(connection)
            raise _recovery_required() from error
        finally:
            if connection is not None:
                connection.close()

    def _reread_current_page_exact_v1(
        self, facts: _CompletedI02FactsV1, *, for_replay: bool
    ) -> _CurrentPageFactsV1:
        """Read only the current PromptBuilt page candidate from the exact repository."""

        if not facts.page_id.isdecimal() or int(facts.page_id) < 1:
            raise _corrupt()
        try:
            snapshot = self._repository._load_revisioned(facts.project_id)
            page = snapshot.project.page(int(facts.page_id))
        except (OSError, ValueError) as error:
            raise _recovery_required() from error
        target = page.metadata.get("future_generation_target_reference")
        if (
            page.state is not PageState.PROMPT_BUILT
            or type(target) is not str
            or target != facts.target_page_reference
            or page.storyboard is None
            or page.prompt is None
            or type(snapshot.revision) is not int
            or snapshot.revision < 1
            or not _is_sha256(snapshot.fingerprint)
        ):
            if for_replay:
                raise _corrupt()
            raise _recovery_required()
        try:
            storyboard_digest = _digest_text(
                json.dumps(
                    page.storyboard,
                    ensure_ascii=True,
                    separators=(",", ":"),
                    sort_keys=True,
                    allow_nan=False,
                )
            )
            prompt_digest = _digest_text(
                json.dumps(
                    page.prompt,
                    ensure_ascii=True,
                    separators=(",", ":"),
                    sort_keys=True,
                    allow_nan=False,
                )
            )
        except (TypeError, ValueError) as error:
            raise _corrupt() from error
        return _CurrentPageFactsV1(
            project_id=facts.project_id,
            page_id=facts.page_id,
            target_page_reference=facts.target_page_reference,
            storyboard_digest=storyboard_digest,
            prompt_digest=prompt_digest,
            revision=snapshot.revision,
            fingerprint=snapshot.fingerprint,
        )

    def _authenticated_record_v1(
        self, delivery_identity: str, *, for_replay: bool
    ) -> _BindingRecordV1:
        """Read every external fact once; no caller fact joins this authority chain."""

        i02_facts = self._replay_completed_i02_v1(delivery_identity)
        evidence = self._replay_evidence_for_completed_i02_v1(i02_facts)
        page = self._reread_current_page_exact_v1(i02_facts, for_replay=for_replay)
        self._reread_owner_asset_exact_v1(i02_facts)
        return _binding_record_from_projection(i02_facts, evidence, page)

    def _historical_page_facts_from_record_v1(
        self, record: _BindingRecordV1
    ) -> _CurrentPageFactsV1:
        """Read creation-time page facts from the record, never from the live page."""

        projection = record.projection
        required_strings = (
            "project_id",
            "page_id",
            "target_page_reference",
            "storyboard_digest",
            "prompt_digest",
            "page_fingerprint",
        )
        if any(type(projection[key]) is not str for key in required_strings):
            raise _corrupt()
        revision = projection["page_revision"]
        if type(revision) is not int or revision < 1:
            raise _corrupt()
        storyboard_digest = cast(str, projection["storyboard_digest"])
        prompt_digest = cast(str, projection["prompt_digest"])
        fingerprint = cast(str, projection["page_fingerprint"])
        if not all(_is_sha256(value) for value in (storyboard_digest, prompt_digest, fingerprint)):
            raise _corrupt()
        return _CurrentPageFactsV1(
            project_id=cast(str, projection["project_id"]),
            page_id=cast(str, projection["page_id"]),
            target_page_reference=cast(str, projection["target_page_reference"]),
            storyboard_digest=storyboard_digest,
            prompt_digest=prompt_digest,
            revision=revision,
            fingerprint=fingerprint,
        )

    def _historical_facts_from_record_v1(
        self,
        record: _BindingRecordV1,
        i02_facts: _CompletedI02FactsV1,
        evidence: _EvidenceFactsV1,
    ) -> _HistoricalBindingFactsV1:
        """Require all stored history to rebuild the exact binding from authoritative reads."""

        historical_page = self._historical_page_facts_from_record_v1(record)
        rebuilt = _binding_record_from_projection(i02_facts, evidence, historical_page)
        if rebuilt != record:
            raise _corrupt()
        return _HistoricalBindingFactsV1(
            binding_identity=record.binding_identity,
            binding_digest=record.binding_digest,
            application_binding_identity=cast(str, record.projection["application_binding_identity"]),
            delivery_identity=i02_facts.delivery_identity,
            i02_binding_digest=i02_facts.binding_digest,
            i02_completion_sequence=i02_facts.completion_sequence,
            i02_completion_event_digest=i02_facts.completion_event_digest,
            canonical_result_identity=i02_facts.canonical_result_identity,
            attempt_id=i02_facts.attempt_id,
            project_id=i02_facts.project_id,
            page_id=i02_facts.page_id,
            target_page_reference=i02_facts.target_page_reference,
            provider_reference=i02_facts.provider_reference,
            dispatch_identity=i02_facts.dispatch_identity,
            idempotency_identity=i02_facts.idempotency_identity,
            submission_receipt_identity=i02_facts.submission_receipt_identity,
            logical_output_id=i02_facts.logical_output_id,
            asset_id=i02_facts.asset_id,
            asset_registration_digest=i02_facts.asset_registration_digest,
            asset_sha256=i02_facts.asset_sha256,
            expected_byte_length=i02_facts.expected_byte_length,
            media_type=i02_facts.media_type,
            evidence_identity=evidence.evidence_identity,
            evidence_persistence_identity=evidence.evidence_persistence_identity,
            evidence_status=evidence.evidence_status,
            historical_storyboard_digest=historical_page.storyboard_digest,
            historical_prompt_digest=historical_page.prompt_digest,
            historical_page_revision=historical_page.revision,
            historical_page_fingerprint=historical_page.fingerprint,
        )

    def _create_exact_v1(self, delivery_identity: str) -> _BindingRecordV1:
        """Create one immutable row after two independent exact fact reads."""

        if not _is_sha256(delivery_identity):
            raise ValueError("AUTHORITY_REJECTED")
        first = self._authenticated_record_v1(delivery_identity, for_replay=False)
        if not _binding_json_is_within_limit(first.binding_json):
            raise _corrupt()
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(str(self._database_path), timeout=0.0, isolation_level=None)
            _configure_connection(connection)
            connection.execute("BEGIN IMMEDIATE")
            _validate_schema(connection)
            second = self._authenticated_record_v1(delivery_identity, for_replay=False)
            if not _binding_json_is_within_limit(second.binding_json):
                raise _corrupt()
            if first != second:
                raise _corrupt()
            existing = _select_record_for_delivery(connection, delivery_identity)
            if existing is not None:
                connection.rollback()
                if existing == second:
                    return existing
                raise ValueError("CONFLICT")
            try:
                connection.execute(
                    "INSERT INTO real_delivery_binding_records "
                    "(binding_identity, delivery_identity, attempt_id, canonical_result_identity, asset_id, "
                    "application_binding_identity, binding_json, binding_digest) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        second.binding_identity,
                        second.projection["delivery_identity"],
                        second.projection["attempt_id"],
                        second.projection["canonical_result_identity"],
                        second.projection["asset_id"],
                        second.projection["application_binding_identity"],
                        second.binding_json,
                        second.binding_digest,
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise ValueError("CONFLICT") from error
            connection.commit()
            return second
        except ValueError:
            _rollback(connection)
            raise
        except (OSError, sqlite3.Error, TypeError) as error:
            _rollback(connection)
            raise _recovery_required() from error
        finally:
            if connection is not None:
                connection.close()

    def _replay_exact_v1(self, delivery_identity: str) -> _BindingRecordV1:
        """Read-only current-state R18 replay; it creates, repairs, and issues nothing."""

        if not _is_sha256(delivery_identity):
            raise ValueError("AUTHORITY_REJECTED")
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(
                f"{self._database_path.as_uri()}?mode=ro", uri=True, timeout=0.0, isolation_level=None
            )
            connection.execute("PRAGMA query_only=ON")
            if connection.execute("PRAGMA query_only").fetchall() != [(1,)]:
                raise _recovery_required()
            connection.execute("BEGIN")
            _validate_schema(connection)
            stored = _select_record_for_delivery(connection, delivery_identity)
            if stored is None:
                if not self._i02_lineage_exists_v1(delivery_identity):
                    raise _not_found()
                raise _recovery_required()
            current = self._authenticated_record_v1(delivery_identity, for_replay=True)
            if current != stored:
                raise _corrupt()
            connection.rollback()
            return stored
        except ValueError:
            _rollback(connection)
            raise
        except (OSError, sqlite3.Error, TypeError) as error:
            _rollback(connection)
            raise _recovery_required() from error
        finally:
            if connection is not None:
                connection.close()

    def _replay_historical_binding_exact_v1(
        self, delivery_identity: str
    ) -> _HistoricalBindingFactsV1:
        """Read-only R20 replay of immutable lineage, with no current-page read."""

        if not _is_sha256(delivery_identity):
            raise ValueError("AUTHORITY_REJECTED")
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(
                f"{self._database_path.as_uri()}?mode=ro", uri=True, timeout=0.0, isolation_level=None
            )
            connection.execute("PRAGMA query_only=ON")
            if connection.execute("PRAGMA query_only").fetchall() != [(1,)]:
                raise _recovery_required()
            connection.execute("BEGIN")
            _validate_schema(connection)
            stored = _select_record_for_delivery(connection, delivery_identity)
            if stored is None:
                if not self._i02_lineage_exists_v1(delivery_identity):
                    raise _not_found()
                raise _recovery_required()
            evidence_identity = stored.projection["evidence_identity"]
            if not _is_sha256(evidence_identity):
                raise _corrupt()
            i02_facts = self._replay_completed_i02_v1(delivery_identity)
            evidence = self._replay_evidence_record_exact_v1(cast(str, evidence_identity))
            self._reread_owner_asset_exact_v1(i02_facts)
            historical = self._historical_facts_from_record_v1(stored, i02_facts, evidence)
            connection.rollback()
            return historical
        except ValueError:
            _rollback(connection)
            raise
        except (OSError, sqlite3.Error, TypeError) as error:
            _rollback(connection)
            raise _recovery_required() from error
        finally:
            if connection is not None:
                connection.close()

    def _replay_historical_binding_for_attempt_v1(
        self, attempt_id: str
    ) -> _HistoricalBindingFactsV1:
        """Select one existing R20 replay by its immutable unique attempt only.

        This is an additive private companion selector for the canonical R25
        composition.  It neither changes the delivery-identity replay contract
        nor creates, repairs, or updates an R18 record.
        """

        if not isinstance(attempt_id, str) or not attempt_id:
            raise ValueError("AUTHORITY_REJECTED")
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(
                f"{self._database_path.as_uri()}?mode=ro", uri=True, timeout=0.0, isolation_level=None
            )
            connection.execute("PRAGMA query_only=ON")
            if connection.execute("PRAGMA query_only").fetchall() != [(1,)]:
                raise _recovery_required()
            connection.execute("BEGIN")
            _validate_schema(connection)
            stored = _select_record_for_attempt(connection, attempt_id)
            if stored is None:
                raise _not_found()
            connection.rollback()
            return self._replay_historical_binding_exact_v1(
                cast(str, stored.projection["delivery_identity"])
            )
        except ValueError:
            _rollback(connection)
            raise
        except (OSError, sqlite3.Error, TypeError) as error:
            _rollback(connection)
            raise _recovery_required() from error
        finally:
            if connection is not None:
                connection.close()

    def _evidence_database_path(self) -> Path:
        normal_root = self._repository._next_generation_normal_execution_owner_root()
        evidence_root = normal_root / "evidence"
        if (
            self._owner._root != normal_root / "assets"
            or _is_reparse_point(evidence_root)
            or not evidence_root.is_dir()
        ):
            raise _recovery_required()
        database = evidence_root / _EVIDENCE_FILENAME
        if database.parent != evidence_root:
            raise _recovery_required()
        return database

    def _initialize_or_validate(self) -> None:
        """Initialize exactly one empty v1 store or validate an existing one."""

        database = self._database_path
        directory = database.parent
        if database.exists():
            if not _regular_file(database) or database.stat().st_size == 0:
                raise _corrupt()
            self._validate_existing_store()
            return

        if not self._create_empty_directory(database, directory):
            return

        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(str(database), timeout=0.0, isolation_level=None)
            _configure_connection(connection)
            connection.execute("BEGIN IMMEDIATE")
            if _user_objects(connection) or _user_version(connection) != 0:
                raise _corrupt()
            _create_schema(connection)
            connection.commit()
            _validate_schema(connection)
        except ValueError:
            _rollback(connection)
            raise
        except (OSError, sqlite3.Error, TypeError) as error:
            _rollback(connection)
            raise _recovery_required() from error
        finally:
            if connection is not None:
                connection.close()

    def _create_empty_directory(self, database: Path, directory: Path) -> bool:
        """Create the sole initializer gate or validate the winning initializer."""

        try:
            directory.parent.mkdir(exist_ok=True)
            directory.mkdir()
        except FileExistsError as error:
            if not directory.is_dir():
                raise _corrupt() from error
            if database.exists():
                if not _regular_file(database) or database.stat().st_size == 0:
                    raise _corrupt() from error
                self._validate_existing_store()
                return False
            raise _recovery_required() from error
        except OSError as error:
            raise _recovery_required() from error
        try:
            if any(directory.iterdir()):
                raise _corrupt()
        except OSError as error:
            raise _recovery_required() from error
        return True

    def _validate_existing_store(self) -> None:
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(str(self._database_path), timeout=0.0, isolation_level=None)
            _configure_connection(connection)
            _validate_schema(connection)
        except ValueError:
            raise
        except (OSError, sqlite3.Error, TypeError) as error:
            raise _recovery_required() from error
        finally:
            if connection is not None:
                connection.close()


def _construct_from_factory_issued_grant_v1(
    factory: PrivateR18CompositionFactoryV1,
    grant: _R18ConstructionGrantV1,
    invocation: _R18LockHeldInvocationV1 | None = None,
) -> RealDeliveryBindingAuthorityV1:
    """The only factory-controlled inlet; raw grants and tuples are rejected."""

    if (
        type(factory) is not PrivateR18CompositionFactoryV1
        or type(grant) is not _R18ConstructionGrantV1
        or type(invocation) is not _R18LockHeldInvocationV1
    ):
        raise ValueError("AUTHORITY_REJECTED")
    return RealDeliveryBindingAuthorityV1(factory, grant, invocation)


def _configure_connection(connection: sqlite3.Connection) -> None:
    mode_row = connection.execute("PRAGMA journal_mode=DELETE").fetchone()
    if mode_row is None or len(mode_row) != 1 or str(mode_row[0]).lower() != "delete":
        raise _corrupt()
    connection.execute("PRAGMA synchronous=FULL")


def _create_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        "CREATE TABLE real_delivery_binding_schema_meta ("
        "schema_id TEXT PRIMARY KEY, schema_version INTEGER NOT NULL)"
    )
    connection.execute(
        "CREATE TABLE real_delivery_binding_records ("
        "binding_identity TEXT PRIMARY KEY, "
        "delivery_identity TEXT NOT NULL UNIQUE, "
        "attempt_id TEXT NOT NULL UNIQUE, "
        "canonical_result_identity TEXT NOT NULL, "
        "asset_id TEXT NOT NULL UNIQUE, "
        "application_binding_identity TEXT NOT NULL UNIQUE, "
        "binding_json TEXT NOT NULL, "
        "binding_digest TEXT NOT NULL UNIQUE)"
    )
    connection.execute(
        f"INSERT INTO {_META_TABLE} (schema_id, schema_version) VALUES (?, ?)",
        (_SCHEMA_ID, _SCHEMA_VERSION),
    )
    connection.execute(f"PRAGMA user_version={_SCHEMA_VERSION}")


def _validate_schema(connection: sqlite3.Connection) -> None:
    if _user_version(connection) != _SCHEMA_VERSION:
        raise _corrupt()
    if _user_objects(connection) != (("table", _RECORD_TABLE), ("table", _META_TABLE)):
        raise _corrupt()
    _validate_table(
        connection,
        _META_TABLE,
        (
            (0, "schema_id", "TEXT", 0, None, 1),
            (1, "schema_version", "INTEGER", 1, None, 0),
        ),
        (("sqlite_autoindex_real_delivery_binding_schema_meta_1", 1, "pk", 0, "schema_id"),),
    )
    _validate_table(
        connection,
        _RECORD_TABLE,
        (
            (0, "binding_identity", "TEXT", 0, None, 1),
            (1, "delivery_identity", "TEXT", 1, None, 0),
            (2, "attempt_id", "TEXT", 1, None, 0),
            (3, "canonical_result_identity", "TEXT", 1, None, 0),
            (4, "asset_id", "TEXT", 1, None, 0),
            (5, "application_binding_identity", "TEXT", 1, None, 0),
            (6, "binding_json", "TEXT", 1, None, 0),
            (7, "binding_digest", "TEXT", 1, None, 0),
        ),
        (
            ("sqlite_autoindex_real_delivery_binding_records_1", 1, "pk", 0, "binding_identity"),
            ("sqlite_autoindex_real_delivery_binding_records_2", 1, "u", 0, "delivery_identity"),
            ("sqlite_autoindex_real_delivery_binding_records_3", 1, "u", 0, "attempt_id"),
            ("sqlite_autoindex_real_delivery_binding_records_4", 1, "u", 0, "asset_id"),
            ("sqlite_autoindex_real_delivery_binding_records_5", 1, "u", 0, "application_binding_identity"),
            ("sqlite_autoindex_real_delivery_binding_records_6", 1, "u", 0, "binding_digest"),
        ),
    )
    rows = connection.execute(
        f"SELECT schema_id, schema_version FROM {_META_TABLE} ORDER BY schema_id"
    ).fetchall()
    if rows != [(_SCHEMA_ID, _SCHEMA_VERSION)]:
        raise _corrupt()


def _select_record_for_delivery(
    connection: sqlite3.Connection, delivery_identity: str
) -> _BindingRecordV1 | None:
    rows = connection.execute(
        "SELECT binding_identity, delivery_identity, attempt_id, canonical_result_identity, asset_id, "
        "application_binding_identity, binding_json, binding_digest "
        "FROM real_delivery_binding_records WHERE delivery_identity = ?",
        (delivery_identity,),
    ).fetchall()
    return _binding_record_from_rows(rows)


def _select_record_for_attempt(
    connection: sqlite3.Connection, attempt_id: str
) -> _BindingRecordV1 | None:
    rows = connection.execute(
        "SELECT binding_identity, delivery_identity, attempt_id, canonical_result_identity, asset_id, "
        "application_binding_identity, binding_json, binding_digest "
        "FROM real_delivery_binding_records WHERE attempt_id = ?",
        (attempt_id,),
    ).fetchall()
    return _binding_record_from_rows(rows)


def _binding_record_from_rows(rows: object) -> _BindingRecordV1 | None:
    if not isinstance(rows, list):
        raise _corrupt()
    if not rows:
        return None
    if len(rows) != 1 or not isinstance(rows[0], tuple) or len(rows[0]) != 8 or not all(
        type(item) is str for item in rows[0]
    ):
        raise _corrupt()
    identity, row_delivery, attempt, canonical_result, asset, application, binding_json, digest = cast(
        tuple[str, str, str, str, str, str, str, str], rows[0]
    )
    if (
        not _binding_json_is_within_limit(binding_json)
        or not all(_is_sha256(value) for value in (identity, digest, application))
    ):
        raise _corrupt()
    try:
        projection = json.loads(binding_json)
    except (TypeError, ValueError) as error:
        raise _corrupt() from error
    if (
        type(projection) is not dict
        or set(projection) != _BINDING_KEYS
        or _canonical_json(cast(dict[str, object], projection)) != binding_json
        or _digest_text(binding_json) != identity
        or identity != digest
        or projection["delivery_identity"] != row_delivery
        or projection["attempt_id"] != attempt
        or projection["canonical_result_identity"] != canonical_result
        or projection["asset_id"] != asset
        or projection["application_binding_identity"] != application
    ):
        raise _corrupt()
    without_application = dict(cast(dict[str, object], projection))
    embedded_application = without_application.pop("application_binding_identity")
    if _digest_text(_canonical_json(without_application)) != embedded_application:
        raise _corrupt()
    return _BindingRecordV1(identity, digest, binding_json, cast(dict[str, object], projection))


def _validate_table(
    connection: sqlite3.Connection,
    table: str,
    columns: tuple[tuple[object, ...], ...],
    indexes: tuple[tuple[str, int, str, int, str], ...],
) -> None:
    if tuple(connection.execute(f"PRAGMA table_info({table})").fetchall()) != columns:
        raise _corrupt()
    actual_indexes = tuple(
        sorted(
            (
                str(row[1]),
                int(row[2]),
                str(row[3]),
                int(row[4]),
                _index_column(connection, str(row[1])),
            )
            for row in connection.execute(f"PRAGMA index_list({table})").fetchall()
            if len(row) == 5
        )
    )
    if actual_indexes != indexes:
        raise _corrupt()


def _index_column(connection: sqlite3.Connection, name: str) -> str:
    rows = connection.execute(f"PRAGMA index_info({name})").fetchall()
    if len(rows) != 1 or rows[0][0] != 0 or rows[0][1] < 0 or rows[0][2] is None:
        raise _corrupt()
    return str(rows[0][2])


def _user_objects(connection: sqlite3.Connection) -> tuple[tuple[str, str], ...]:
    return tuple(
        (str(row[0]), str(row[1]))
        for row in connection.execute(
            "SELECT type, name FROM sqlite_master "
            "WHERE name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        if len(row) == 2
    )


def _user_version(connection: sqlite3.Connection) -> int:
    row = connection.execute("PRAGMA user_version").fetchone()
    if row is None or len(row) != 1 or type(row[0]) is not int:
        raise _corrupt()
    return row[0]


def _rollback(connection: sqlite3.Connection | None) -> None:
    if connection is None:
        return
    try:
        connection.rollback()
    except sqlite3.Error:
        pass
