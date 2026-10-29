"""Private LocalFile adapters for the frozen Page output proof resolver."""

from __future__ import annotations

import stat
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from manga_director.production.next_generation_deterministic_composite_asset_owner import (
    DeterministicCompositeAssetOwner,
)
from manga_director.production.next_generation_page_composition import (
    LocalPageCompositionAuthority,
    PageCompositionAuthorityResult,
)
from manga_director.production.next_generation_page_composition_application_ledger import (
    LocalPageCompositionApplicationLedger,
    PageCompositionApplicationLedgerResult,
    PageCompositionAppliedBindingLookupResult,
)
from manga_director.production.next_generation_page_output_proof import (
    PageOutputProofUnavailable,
    ProviderProofLookupResult,
    ResolvedPageOutput,
    build_local_page_output_proof_resolver,
)
from manga_director.production.next_generation_safe_local_generated_asset_presentation import (
    SafeLocalGeneratedAssetPresenter,
)
from manga_director.production.next_generation_workflow_application_ledger import (
    LocalWorkflowApplicationLedgerStore,
)
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.workflow.contracts import WorkflowContext
from manga_director.workflow.durable_execution import LogicalOutputAssetQualityGatePort


@dataclass(slots=True)
class _PageScope:
    project_id: str
    page_id: str


class _ProviderLookup:
    def __init__(self, root: Path, presenter: SafeLocalGeneratedAssetPresenter, scope: _PageScope) -> None:
        self._root = root
        self._presenter = presenter
        self._scope = scope

    def lookup(self, project_id: str, page_id: str, output_asset_id: str) -> ProviderProofLookupResult:
        if (project_id, page_id) != (self._scope.project_id, self._scope.page_id):
            return ProviderProofLookupResult("invalid")
        inventory = LocalWorkflowApplicationLedgerStore.observe_page(
            self._root, project_id, page_id
        )
        if inventory.outcome == "missing":
            return ProviderProofLookupResult("missing")
        if inventory.outcome != "found":
            return ProviderProofLookupResult("invalid")
        if not any(binding.output_asset_id == output_asset_id for binding in inventory.bindings):
            return ProviderProofLookupResult("invalid")
        try:
            proof = self._presenter._prove(project_id, page_id, output_asset_id)
            if proof.binding != inventory.bindings[0]:
                proof.release()
                return ProviderProofLookupResult("invalid")
            return ProviderProofLookupResult("found", proof)
        except Exception:
            return ProviderProofLookupResult("invalid")


class _CompositionAuthority:
    def __init__(self, root: Path, scope: _PageScope) -> None:
        self._root, self._scope = root, scope

    def lookup(self, composition_attempt_id: str) -> PageCompositionAuthorityResult:
        observed = LocalPageCompositionAuthority.observe_page_at(
            self._root, self._scope.project_id, self._scope.page_id
        )
        if observed.outcome == "missing":
            return PageCompositionAuthorityResult(composition_attempt_id, "missing")
        if observed.outcome != "found":
            return PageCompositionAuthorityResult(composition_attempt_id, "corrupt")
        matches = [item for item in observed.attempts if item.composition_attempt_id == composition_attempt_id]
        evidence = [item for item in observed.evidence if item.composition_attempt_id == composition_attempt_id]
        if len(matches) != 1 or len(evidence) != 1:
            return PageCompositionAuthorityResult(composition_attempt_id, "corrupt")
        return PageCompositionAuthorityResult(composition_attempt_id, "confirmed", matches[0], evidence[0])


class _CompositeOwner:
    def __init__(self, root: Path) -> None:
        self._root = root

    def read_verified(self, asset_id: str) -> Any:
        return DeterministicCompositeAssetOwner.read_verified_at(self._root, asset_id)


class _CompositionApplicationLedger:
    def __init__(self, root: Path, scope: _PageScope) -> None:
        self._root, self._scope = root, scope

    def lookup_exact(self, binding: Any) -> PageCompositionApplicationLedgerResult:
        observed = LocalPageCompositionApplicationLedger.observe_page_at(
            self._root, self._scope.project_id, self._scope.page_id
        )
        if observed.outcome == "missing":
            return PageCompositionApplicationLedgerResult(binding.application_id, "missing")
        if observed.outcome != "found" or len(observed.bindings) != 1:
            return PageCompositionApplicationLedgerResult(binding.application_id, "corrupt")
        found = observed.bindings[0]
        if found != binding:
            return PageCompositionApplicationLedgerResult(binding.application_id, "conflict")
        return PageCompositionApplicationLedgerResult(binding.application_id, "confirmed", "applied", found)

    def lookup_applied(self, project_id: str, page_id: str, output_asset_id: str) -> PageCompositionAppliedBindingLookupResult:
        observed = LocalPageCompositionApplicationLedger.observe_page_at(self._root, project_id, page_id)
        if observed.outcome == "missing":
            return PageCompositionAppliedBindingLookupResult("missing")
        if observed.outcome == "prepared":
            return PageCompositionAppliedBindingLookupResult("prepared")
        if observed.outcome != "found" or len(observed.bindings) != 1:
            return PageCompositionAppliedBindingLookupResult("corrupt")
        binding = observed.bindings[0]
        if binding.composite_asset_id != output_asset_id:
            return PageCompositionAppliedBindingLookupResult("missing")
        return PageCompositionAppliedBindingLookupResult("found", binding)


class _ReadOnlyPageOutputProof:
    def __init__(self, repository: LocalFileRepository) -> None:
        self._repository = repository

    def resolve(self, project_id: str, page_id: str, output_asset_id: str) -> ResolvedPageOutput:
        normal_root = self._repository._next_generation_normal_execution_owner_root()
        if not all(
            _readonly_sqlite_rollback_safe(root, filename)
            for root, filename in (
                (normal_root / "page-composition-authority", "page-composition-authority.sqlite3"),
                (normal_root / "page-composition-application", "page-composition-application-ledger.sqlite3"),
                (normal_root / "deterministic-composite-owner", "deterministic-composite-assets.sqlite3"),
            )
        ):
            raise PageOutputProofUnavailable("Page output proof is unavailable")
        composition = LocalPageCompositionAuthority.observe_page_at(
            normal_root / "page-composition-authority", project_id, page_id
        )
        application = LocalPageCompositionApplicationLedger.observe_page_at(
            normal_root / "page-composition-application", project_id, page_id
        )
        assets = DeterministicCompositeAssetOwner.observe_page_at(
            normal_root / "deterministic-composite-owner", project_id, page_id
        )
        if any(item.outcome in {"corrupt", "ambiguous"} for item in (composition, application, assets)):
            raise PageOutputProofUnavailable("Page output proof is unavailable")
        if composition.outcome == application.outcome == assets.outcome == "missing":
            pass
        elif not (
            composition.outcome == "found"
            and application.outcome == "found"
            and assets.outcome == "found"
            and len(composition.attempt_ids) == len(application.composition_attempt_ids) == len(assets.composition_attempt_ids) == 1
            and composition.attempt_ids == application.composition_attempt_ids == assets.composition_attempt_ids
        ):
            raise PageOutputProofUnavailable("Page output proof is unavailable")
        elif application.bindings[0].composite_asset_id != output_asset_id:
            raise PageOutputProofUnavailable("Page output proof is unavailable")
        scope = _PageScope(project_id, page_id)
        ledger_root = self._repository._workflow_application_ledger_owner_root()
        presenter = SafeLocalGeneratedAssetPresenter(
            ledger_root=ledger_root,
            evidence_root=normal_root / "evidence",
            asset_root=normal_root / "assets",
        )
        resolver = build_local_page_output_proof_resolver(
            provider_proof_lookup=_ProviderLookup(ledger_root, presenter, scope),
            composition_authority=_CompositionAuthority(
                normal_root / "page-composition-authority", scope
            ),
            composite_owner=_CompositeOwner(normal_root / "deterministic-composite-owner"),
            composition_application_ledger=_CompositionApplicationLedger(
                normal_root / "page-composition-application", scope
            ),
        )
        return resolver.resolve(project_id, page_id, output_asset_id)


class _PageOutputQualityGate:
    def __init__(self, resolver: _ReadOnlyPageOutputProof) -> None:
        self._resolver = resolver

    def require_applied(self, context: WorkflowContext) -> str | None:
        image = context.artifacts.get("Generated")
        project_id, page_id = context.page.get("project_id"), context.page.get("page_id")
        output_id = image.get("output_asset_id") if isinstance(image, Mapping) else None
        if not all(isinstance(value, str) for value in (project_id, page_id, output_id)):
            return "LOGICAL_OUTPUT_ASSET_QUALITY_PROOF_UNAVAILABLE"
        if (
            context.state.value != "Generated"
            or not isinstance(image, Mapping)
            or set(image) != {"artifact_kind", "output_asset_id"}
            or image.get("artifact_kind") != "logical_output_asset"
            or not output_id.strip()
        ):
            return "LOGICAL_OUTPUT_ASSET_QUALITY_PROOF_INVALID"
        output = None
        try:
            output = self._resolver.resolve(project_id, page_id, output_id)
            return None
        except PageOutputProofUnavailable:
            return "LOGICAL_OUTPUT_ASSET_QUALITY_PROOF_UNAVAILABLE"
        finally:
            if output is not None:
                output.release()


def build_localfile_page_output_proof_bridge(repository: LocalFileRepository) -> tuple[_ReadOnlyPageOutputProof, LogicalOutputAssetQualityGatePort]:
    """Compose legacy and deterministic-composition proofs without creating owners."""

    proof = _ReadOnlyPageOutputProof(repository)
    return proof, _PageOutputQualityGate(proof)


def _readonly_sqlite_rollback_safe(root: Path, filename: str) -> bool:
    database = root / filename
    sidecars = tuple(Path(f"{database}{suffix}") for suffix in ("-wal", "-shm", "-journal"))
    try:
        for sidecar in sidecars:
            try:
                sidecar.lstat()
            except FileNotFoundError:
                continue
            return False
        try:
            status = database.lstat()
        except FileNotFoundError:
            return True
        attributes = getattr(status, "st_file_attributes", 0)
        if (
            not stat.S_ISREG(status.st_mode)
            or stat.S_ISLNK(status.st_mode)
            or bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
        ):
            return False
        with database.open("rb") as stream:
            header = stream.read(20)
        return header[:16] == b"SQLite format 3\x00" and header[18:20] == b"\x01\x01"
    except OSError:
        return False
