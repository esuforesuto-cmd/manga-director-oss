"""Closed private proof for one authoritative generated Page output."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Literal, Protocol, TypeAlias

from pydantic import ConfigDict, Field, field_validator, model_validator

from manga_director.production.director import DirectorModel
from manga_director.production.next_generation_deterministic_composite_asset_owner import (
    DeterministicCompositeReadResult,
)
from manga_director.production.next_generation_page_composition import (
    AcceptedPanelSource,
    PageCompositeAsset,
    PageCompositionAuthorityResult,
    PageCompositionEvidence,
)
from manga_director.production.next_generation_page_composition_application_ledger import (
    LocalPageCompositionApplicationLedger,
    PageCompositionApplicationBinding,
    PageCompositionApplicationLedgerResult,
    PageCompositionAppliedBindingLookupResult,
)
from manga_director.production.next_generation_page_generation_plan import sha256_digest
from manga_director.production.next_generation_safe_local_generated_asset_presentation import (
    _SafeLocalGeneratedAssetProof,
)


class _PageOutputModel(DirectorModel):
    model_config = ConfigDict(
        frozen=True, extra="forbid", strict=True, validate_default=True
    )


class ProviderGenerationPageOutputProof(_PageOutputModel):
    """Normalized view of the unchanged legacy Provider proof chain."""

    kind: Literal["provider_generation"] = "provider_generation"
    project_id: str
    page_id: str
    target_page_reference: str
    attempt_id: str
    provenance_reference: str
    asset_id: str
    media_type: Literal["image/png"] = "image/png"
    content_sha256: str
    provider_reference: str

    @field_validator(
        "project_id",
        "page_id",
        "target_page_reference",
        "attempt_id",
        "provenance_reference",
        "asset_id",
        "provider_reference",
        mode="before",
    )
    @classmethod
    def _references(cls, value: object) -> str:
        return _page_output_reference(value)

    @field_validator("content_sha256")
    @classmethod
    def _digest(cls, value: str) -> str:
        return sha256_digest(value)


class DeterministicCompositionPageOutputProof(_PageOutputModel):
    """Exact composite proof including the complete ordered Panel manifest."""

    kind: Literal["deterministic_composition"] = "deterministic_composition"
    project_id: str
    page_id: str
    target_page_reference: str
    attempt_id: str
    provenance_reference: str
    asset_id: str
    media_type: Literal["image/png"] = "image/png"
    content_sha256: str
    plan_id: str
    plan_fingerprint: str
    request_fingerprint: str
    evidence_id: str
    evidence_sha256: str
    ordered_sources: tuple[AcceptedPanelSource, ...] = Field(min_length=1, max_length=16)

    @field_validator(
        "project_id",
        "page_id",
        "target_page_reference",
        "attempt_id",
        "provenance_reference",
        "asset_id",
        "plan_id",
        "evidence_id",
        mode="before",
    )
    @classmethod
    def _references(cls, value: object) -> str:
        return _page_output_reference(value)

    @field_validator(
        "content_sha256", "plan_fingerprint", "request_fingerprint", "evidence_sha256"
    )
    @classmethod
    def _digests(cls, value: str) -> str:
        return sha256_digest(value)

    @model_validator(mode="after")
    def _complete_manifest(self) -> DeterministicCompositionPageOutputProof:
        if tuple(source.panel_order for source in self.ordered_sources) != tuple(
            range(1, len(self.ordered_sources) + 1)
        ):
            raise ValueError("composition Page output requires canonical Panel order")
        for source in self.ordered_sources:
            if (
                source.plan_id != self.plan_id
                or source.plan_fingerprint != self.plan_fingerprint
                or source.project_id != self.project_id
                or source.page_id != self.page_id
            ):
                raise ValueError("composition source does not match the Page output")
        return self


PageOutputProof: TypeAlias = (
    ProviderGenerationPageOutputProof | DeterministicCompositionPageOutputProof
)


@dataclass(slots=True)
class ResolvedPageOutput:
    proof: PageOutputProof
    image_bytes: bytes = field(repr=False)
    _release: object = field(repr=False)
    legacy_evidence: object | None = field(default=None, repr=False)
    legacy_binding: object | None = field(default=None, repr=False)

    def release(self) -> None:
        release = getattr(self._release, "release", None)
        if callable(release):
            release()


class PageOutputResolverPort(Protocol):
    def resolve(
        self, project_id: str, page_id: str, output_asset_id: str
    ) -> ResolvedPageOutput: ...


class _CompositionAuthorityPort(Protocol):
    def lookup(self, composition_attempt_id: str) -> PageCompositionAuthorityResult: ...


class _CompositeOwnerPort(Protocol):
    def read_verified(self, asset_id: str) -> DeterministicCompositeReadResult: ...


class _CompositionApplicationLedgerPort(Protocol):
    def lookup_exact(
        self, binding: PageCompositionApplicationBinding
    ) -> PageCompositionApplicationLedgerResult: ...


class _ProviderProofLookupPort(Protocol):
    def lookup(
        self, project_id: str, page_id: str, output_asset_id: str
    ) -> ProviderProofLookupResult: ...


@dataclass(frozen=True, slots=True)
class ProviderProofLookupResult:
    outcome: Literal["found", "missing", "invalid"]
    proof: _SafeLocalGeneratedAssetProof | None = field(default=None, repr=False)


@dataclass(frozen=True, slots=True)
class CompositionApplicationBindingLookupResult:
    outcome: Literal["found", "missing", "invalid"]
    binding: PageCompositionApplicationBinding | None = field(
        default=None, repr=False
    )


class CompositionApplicationBindingResolverPort(Protocol):
    def lookup_applied(
        self, project_id: str, page_id: str, output_asset_id: str
    ) -> CompositionApplicationBindingLookupResult: ...


class _AppliedBindingLookupPort(Protocol):
    def lookup_applied(
        self, project_id: str, page_id: str, output_asset_id: str
    ) -> PageCompositionAppliedBindingLookupResult: ...


class LocalCompositionApplicationBindingResolver:
    """Adapt the Slice 2 ledger's public applied-binding lookup."""

    def __init__(self, ledger: _AppliedBindingLookupPort) -> None:
        self._ledger = ledger

    def lookup_applied(
        self, project_id: str, page_id: str, output_asset_id: str
    ) -> CompositionApplicationBindingLookupResult:
        try:
            result = self._ledger.lookup_applied(project_id, page_id, output_asset_id)
        except Exception:
            return CompositionApplicationBindingLookupResult("invalid")
        if result.outcome == "found" and result.binding is not None:
            return CompositionApplicationBindingLookupResult(
                "found", result.binding
            )
        if result.outcome == "missing" and result.binding is None:
            return CompositionApplicationBindingLookupResult("missing")
        return CompositionApplicationBindingLookupResult("invalid")


class PageOutputProofUnavailable(ValueError):
    """Redacted fail-closed result for zero, multiple, or invalid variants."""


@dataclass(frozen=True, slots=True)
class PageOutputApplicationAdmissionResult:
    allowed: bool
    code: str


class PageOutputApplicationAdmission:
    """Common closed producer check before the existing generate command."""

    def admit(
        self,
        proof: PageOutputProof,
        *,
        provider_proof_validated: bool = False,
        composition_binding: PageCompositionApplicationBinding | None = None,
        composition_evidence: PageCompositionEvidence | None = None,
        composite_asset: PageCompositeAsset | None = None,
    ) -> PageOutputApplicationAdmissionResult:
        if isinstance(proof, ProviderGenerationPageOutputProof):
            return PageOutputApplicationAdmissionResult(
                provider_proof_validated,
                "provider_generation_admitted"
                if provider_proof_validated
                else "provider_generation_blocked",
            )
        if (
            composition_binding is None
            or composition_evidence is None
            or composite_asset is None
            or not _composition_chain_matches(
                composition_binding, composition_evidence, composite_asset
            )
            or proof.project_id != composition_binding.project_id
            or proof.page_id != composition_binding.page_id
            or proof.attempt_id != composition_binding.composition_attempt_id
            or proof.provenance_reference
            != composition_binding.composition_provenance_reference
            or proof.asset_id != composition_binding.composite_asset_id
            or proof.content_sha256 != composition_binding.composite_sha256
            or proof.plan_id != composition_binding.plan_id
            or proof.plan_fingerprint != composition_binding.plan_fingerprint
            or proof.request_fingerprint != composition_binding.request_fingerprint
            or proof.evidence_id != composition_binding.evidence_id
            or proof.evidence_sha256 != composition_binding.evidence_sha256
            or proof.ordered_sources != composite_asset.ordered_sources
        ):
            return PageOutputApplicationAdmissionResult(
                False, "deterministic_composition_blocked"
            )
        return PageOutputApplicationAdmissionResult(
            True, "deterministic_composition_admitted"
        )


class _NoopRelease:
    def release(self) -> None:
        return None


@dataclass(frozen=True, slots=True)
class _PageOutputCandidate:
    outcome: Literal["found", "missing", "invalid"]
    output: ResolvedPageOutput | None = field(default=None, repr=False)


class LocalPageOutputProofResolver:
    """Resolve exactly one legacy or composition output from local authorities."""

    def __init__(
        self,
        *,
        provider_proof_lookup: _ProviderProofLookupPort,
        composition_authority: _CompositionAuthorityPort,
        composite_owner: _CompositeOwnerPort,
        composition_application_ledger: _CompositionApplicationLedgerPort,
        composition_application_binding_resolver: (
            CompositionApplicationBindingResolverPort
        ),
    ) -> None:
        self._provider_proof_lookup = provider_proof_lookup
        self._composition_authority = composition_authority
        self._composite_owner = composite_owner
        self._composition_application_ledger = composition_application_ledger
        self._composition_application_binding_resolver = (
            composition_application_binding_resolver
        )

    def resolve(
        self, project_id: str, page_id: str, output_asset_id: str
    ) -> ResolvedPageOutput:
        provider = self._provider_candidate(project_id, page_id, output_asset_id)
        try:
            composition = self._composition_candidate(
                project_id, page_id, output_asset_id
            )
        except Exception as error:
            if provider.output is not None:
                provider.output.release()
            raise PageOutputProofUnavailable(
                "Page output proof is unavailable"
            ) from error
        if provider.outcome == "invalid" or composition.outcome == "invalid":
            for candidate in (provider, composition):
                if candidate.output is not None:
                    candidate.output.release()
            raise PageOutputProofUnavailable("Page output proof is unavailable")
        candidates: list[ResolvedPageOutput] = []
        for candidate_record in (provider, composition):
            if (
                candidate_record.outcome == "found"
                and candidate_record.output is not None
            ):
                candidates.append(candidate_record.output)
        if len(candidates) != 1:
            for output in candidates:
                output.release()
            raise PageOutputProofUnavailable("Page output proof is unavailable")
        return candidates[0]

    def _provider_candidate(
        self, project_id: str, page_id: str, output_asset_id: str
    ) -> _PageOutputCandidate:
        source: _SafeLocalGeneratedAssetProof | None = None
        try:
            lookup = self._provider_proof_lookup.lookup(
                project_id, page_id, output_asset_id
            )
            source = lookup.proof
            if lookup.outcome == "missing" and source is None:
                return _PageOutputCandidate("missing")
            if lookup.outcome != "found" or source is None:
                if source is not None:
                    source.release()
                return _PageOutputCandidate("invalid")
        except Exception:
            if source is not None:
                source.release()
            return _PageOutputCandidate("invalid")
        try:
            output_hash = source.evidence.output.output_content_hash
            digest = output_hash.value if output_hash is not None else None
            if not isinstance(digest, str):
                source.release()
                return _PageOutputCandidate("invalid")
            proof = ProviderGenerationPageOutputProof(
                project_id=source.binding.project_id,
                page_id=source.binding.page_id,
                target_page_reference=source.binding.target_page_reference,
                attempt_id=source.binding.attempt_id,
                provenance_reference=source.evidence.provenance_reference,
                asset_id=source.binding.output_asset_id,
                content_sha256=digest,
                provider_reference=source.binding.provider_reference,
            )
            return _PageOutputCandidate(
                "found",
                ResolvedPageOutput(
                    proof,
                    source._lease.image_bytes,
                    source,
                    source.evidence,
                    source.binding,
                ),
            )
        except Exception:
            source.release()
            return _PageOutputCandidate("invalid")

    def _composition_candidate(
        self, project_id: str, page_id: str, output_asset_id: str
    ) -> _PageOutputCandidate:
        read = self._composite_owner.read_verified(output_asset_id)
        binding_lookup = (
            self._composition_application_binding_resolver.lookup_applied(
                project_id, page_id, output_asset_id
            )
        )
        if read.outcome == "missing" and binding_lookup.outcome == "missing":
            return _PageOutputCandidate("missing")
        if (
            read.outcome != "found"
            or read.asset is None
            or read.image_bytes is None
            or binding_lookup.outcome != "found"
            or binding_lookup.binding is None
        ):
            return _PageOutputCandidate("invalid")
        asset = read.asset
        authority = self._composition_authority.lookup(asset.composition_attempt_id)
        if (
            authority.outcome != "confirmed"
            or authority.attempt is None
            or authority.evidence is None
            or authority.attempt.outcome != "completed"
            or authority.evidence.outcome != "completed"
        ):
            return _PageOutputCandidate("invalid")
        binding = binding_lookup.binding
        assert binding is not None
        ledger = self._composition_application_ledger.lookup_exact(binding)
        if ledger.outcome != "confirmed" or ledger.lifecycle != "applied":
            return _PageOutputCandidate("invalid")
        if not _composition_chain_matches(binding, authority.evidence, asset):
            return _PageOutputCandidate("invalid")
        proof = DeterministicCompositionPageOutputProof(
            project_id=binding.project_id,
            page_id=binding.page_id,
            target_page_reference=f"page.{binding.project_id}.{binding.page_id}",
            attempt_id=binding.composition_attempt_id,
            provenance_reference=binding.composition_provenance_reference,
            asset_id=binding.composite_asset_id,
            content_sha256=binding.composite_sha256,
            plan_id=binding.plan_id,
            plan_fingerprint=binding.plan_fingerprint,
            request_fingerprint=binding.request_fingerprint,
            evidence_id=binding.evidence_id,
            evidence_sha256=binding.evidence_sha256,
            ordered_sources=asset.ordered_sources,
        )
        return _PageOutputCandidate(
            "found", ResolvedPageOutput(proof, read.image_bytes, _NoopRelease())
        )


def build_local_page_output_proof_resolver(
    *,
    provider_proof_lookup: _ProviderProofLookupPort,
    composition_authority: _CompositionAuthorityPort,
    composite_owner: _CompositeOwnerPort,
    composition_application_ledger: LocalPageCompositionApplicationLedger,
) -> LocalPageOutputProofResolver:
    """Compose Slice 2 authorities without exposing their persistence details."""

    return LocalPageOutputProofResolver(
        provider_proof_lookup=provider_proof_lookup,
        composition_authority=composition_authority,
        composite_owner=composite_owner,
        composition_application_ledger=composition_application_ledger,
        composition_application_binding_resolver=(
            LocalCompositionApplicationBindingResolver(
                composition_application_ledger
            )
        ),
    )


def composition_evidence_sha256(evidence: PageCompositionEvidence) -> str:
    payload = json.dumps(
        evidence.model_dump(mode="json"),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _page_output_reference(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > 256
        or value.startswith(("/", "\\"))
        or "://" in value
        or "@" in value
        or any(character.isspace() for character in value)
    ):
        raise ValueError("Page-output reference must be one safe logical value")
    return value


def _composition_chain_matches(
    binding: PageCompositionApplicationBinding,
    evidence: PageCompositionEvidence,
    asset: PageCompositeAsset,
) -> bool:
    return (
        binding.composition_attempt_id
        == evidence.composition_attempt_id
        == asset.composition_attempt_id
        and binding.plan_id == evidence.plan_id
        and binding.plan_fingerprint == evidence.plan_fingerprint
        and binding.project_id == evidence.project_id
        and binding.page_id == evidence.page_id
        and binding.request_fingerprint
        == evidence.request_fingerprint
        == asset.request_fingerprint
        and binding.composition_provenance_reference
        == evidence.composition_provenance_reference
        == asset.composition_provenance_reference
        and binding.evidence_id == evidence.evidence_id
        and binding.evidence_sha256 == composition_evidence_sha256(evidence)
        and binding.composite_asset_id
        == evidence.output_asset_id
        == asset.asset_id
        and binding.composite_sha256
        == evidence.output_sha256
        == asset.content_sha256
        and evidence.ordered_sources == asset.ordered_sources
    )
