from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from manga_director.domain.state_machine import PageState
from manga_director.production.next_generation_page_composition_application_ledger import (
    LocalPageCompositionApplicationLedger,
    PageCompositionApplicationBinding,
)
from manga_director.production.next_generation_page_output_proof import (
    PageOutputProofUnavailable,
)
from manga_director.production.next_generation_safe_local_generated_asset_presentation import (
    SafeLocalGeneratedAssetPresenter,
)
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.workflow.localfile_page_output_proof_bridge import (
    _PageOutputQualityGate,
    _PageScope,
    _ProviderLookup,
    _readonly_sqlite_rollback_safe,
    build_localfile_page_output_proof_bridge,
)


def test_composition_observation_guard_rejects_wal_without_mutation(
    tmp_path: Path,
) -> None:
    root = tmp_path / "authority"
    root.mkdir()
    database = root / "authority.sqlite3"
    header = b"SQLite format 3\x00" + (b"\x00" * 2) + b"\x01\x01"
    database.write_bytes(header)

    assert _readonly_sqlite_rollback_safe(root, database.name)
    before = database.read_bytes()
    wal = Path(f"{database}-wal")
    wal.write_bytes(b"existing wal")

    assert not _readonly_sqlite_rollback_safe(root, database.name)
    assert database.read_bytes() == before
    assert wal.read_bytes() == b"existing wal"


def test_missing_page_proofs_are_read_only_for_concurrent_page_resolves(
    tmp_path: Path,
) -> None:
    repository = LocalFileRepository((tmp_path / "repository").resolve())
    resolver, _quality_gate = build_localfile_page_output_proof_bridge(repository)

    def unavailable(page_id: str) -> bool:
        with pytest.raises(PageOutputProofUnavailable):
            resolver.resolve("demo", page_id, "asset:missing")
        return True

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(unavailable, ("1", "2"))) == [True, True]

    assert not repository._root.exists()


def test_prepared_composition_application_is_rejected_without_read_side_effects(
    tmp_path: Path,
) -> None:
    repository = LocalFileRepository((tmp_path / "repository").resolve())
    normal_root = repository._next_generation_normal_execution_owner_root()
    application_root = normal_root / "page-composition-application"
    binding = PageCompositionApplicationBinding(
        application_id="application-one",
        project_id="demo",
        page_id="1",
        page_revision="revision-1",
        plan_id="plan-one",
        plan_fingerprint="a" * 64,
        composition_attempt_id="composition-one",
        composition_provenance_reference="provenance-one",
        request_fingerprint="b" * 64,
        evidence_id="evidence-one",
        evidence_sha256="c" * 64,
        composite_asset_id="asset-one",
        composite_sha256="d" * 64,
    )
    ledger = LocalPageCompositionApplicationLedger(application_root)
    assert ledger.prepare(binding).outcome == "prepared"
    before = tuple(
        sorted(
            (str(path.relative_to(normal_root)), path.read_bytes())
            for path in normal_root.rglob("*")
            if path.is_file()
        )
    )
    resolver, _quality_gate = build_localfile_page_output_proof_bridge(repository)

    with pytest.raises(PageOutputProofUnavailable):
        resolver.resolve("demo", "1", "asset-one")

    after = tuple(
        sorted(
            (str(path.relative_to(normal_root)), path.read_bytes())
            for path in normal_root.rglob("*")
            if path.is_file()
        )
    )
    assert after == before
    assert not (normal_root / "page-composition-authority").exists()
    assert not (normal_root / "deterministic-composite-owner").exists()


def test_provider_proof_lookup_rejects_cross_page_scope_without_reading(
    tmp_path: Path,
) -> None:
    ledger_root = tmp_path / "ledger"
    evidence_root = tmp_path / "evidence"
    asset_root = tmp_path / "assets"
    presenter = SafeLocalGeneratedAssetPresenter(
        ledger_root=ledger_root,
        evidence_root=evidence_root,
        asset_root=asset_root,
    )
    lookup = _ProviderLookup(ledger_root, presenter, _PageScope("demo", "1"))

    assert lookup.lookup("demo", "2", "asset:one").outcome == "invalid"
    assert not ledger_root.exists()
    assert not evidence_root.exists()
    assert not asset_root.exists()


def test_quality_gate_uses_proof_resolver_and_releases_exactly_once() -> None:
    class Proof:
        released = 0

        def release(self) -> None:
            self.released += 1

    class Resolver:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str, str]] = []
            self.proof = Proof()

        def resolve(self, project_id: str, page_id: str, output_asset_id: str) -> Proof:
            self.calls.append((project_id, page_id, output_asset_id))
            return self.proof

    resolver = Resolver()
    gate = _PageOutputQualityGate(resolver)  # type: ignore[arg-type]
    context: Any = SimpleNamespace(
        state=PageState.GENERATED,
        page={"project_id": "demo", "page_id": "1"},
        artifacts={
            "Generated": {
                "artifact_kind": "logical_output_asset",
                "output_asset_id": "composite-1",
            }
        },
    )

    assert gate.require_applied(context) is None
    assert resolver.calls == [("demo", "1", "composite-1")]
    assert resolver.proof.released == 1


def test_quality_gate_rejects_noncanonical_generated_descriptor() -> None:
    class Resolver:
        def resolve(self, *_args: str) -> Any:
            raise AssertionError("invalid descriptor must be rejected before proof")

    gate = _PageOutputQualityGate(Resolver())  # type: ignore[arg-type]
    context: Any = SimpleNamespace(
        state=PageState.GENERATED,
        page={"project_id": "demo", "page_id": "1"},
        artifacts={
            "Generated": {
                "artifact_kind": "logical_output_asset",
                "output_asset_id": "composite-1",
                "path": "not-allowed",
            }
        },
    )

    assert gate.require_applied(context) == "LOGICAL_OUTPUT_ASSET_QUALITY_PROOF_INVALID"
