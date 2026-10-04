from __future__ import annotations

import copy
import sqlite3
import threading
import time
from pathlib import Path

import pytest

from manga_director.domain.state_machine import StateMachine
from manga_director.events import MemoryEventBus
from manga_director.production import next_generation_workflow_application_ledger as ledger
from manga_director.production.next_generation_workflow_application_ledger import (
    LocalWorkflowApplicationLedgerStore,
    WorkflowApplicationLedgerBindingDTO,
)
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.workflow import localfile_private_real_delivery_composition as private
from manga_director.workflow.localfile_external_generated_application import (
    build_localfile_external_generation_composition,
)


@pytest.fixture(autouse=True)
def _clear_private_registry() -> None:
    with private._REGISTRY_LOCK:
        private._ROOTS_BY_REPOSITORY.clear()
        private._REPOSITORY_BY_DURABLE_ROOT.clear()
    with ledger._R26_CAPABILITY_LOCK:
        ledger._R26_READY_ROOTS.clear()
        ledger._R26_PREPARATION_CAPABILITIES.clear()
        ledger._R26_OBSERVATION_CAPABILITIES.clear()


def _binding(suffix: str = "one") -> WorkflowApplicationLedgerBindingDTO:
    return WorkflowApplicationLedgerBindingDTO(
        attempt_id=f"attempt-{suffix}",
        authorization_id=f"authorization-{suffix}",
        project_id="project-1",
        page_id="page-1",
        target_page_reference="page-1",
        provider_reference=f"provider-{suffix}",
        output_asset_id=f"asset-{suffix}",
        source_state="PromptBuilt",
        target_state="Generated",
    )


def test_private_host_owns_exact_tuple_and_reuses_exact_ready_root(tmp_path: Path) -> None:
    host = private._create_private_real_delivery_workflow_host_v1(tmp_path)

    root = host._start_private_real_delivery_composition_v1()

    assert root._owner._repository is root._repository
    assert root._owner._state_machine is root._state_machine
    assert root._owner._event_bus is root._event_bus
    assert root._composition.external_application._page_store._repository is root._repository
    assert host._start_private_real_delivery_composition_v1() is root


def test_raw_entry_and_reconstructed_authorities_are_rejected(tmp_path: Path) -> None:
    host = private._create_private_real_delivery_workflow_host_v1(tmp_path)
    entry = object.__new__(private._PrivateRealDeliveryCompositionEntryV1)

    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        entry._create_owner_from_host_authorization_v1(object(), object())
    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        private._construct_private_r26_reconciliation_root_v1(object())
    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        private._PrivateRealDeliveryWorkflowHostV1(tmp_path)

    assert host._start_private_real_delivery_composition_v1()._repository is not None


def test_same_durable_root_different_repository_identity_is_rejected(tmp_path: Path) -> None:
    first = private._create_private_real_delivery_workflow_host_v1(tmp_path)
    first._start_private_real_delivery_composition_v1()
    second = private._create_private_real_delivery_workflow_host_v1(tmp_path)

    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        second._start_private_real_delivery_composition_v1()


def test_authorized_builder_failure_is_named_and_later_fresh_retry_is_allowed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    host = private._create_private_real_delivery_workflow_host_v1(tmp_path)

    def fail_once(*args: object) -> object:
        raise RuntimeError("builder unavailable")

    monkeypatch.setattr(
        private,
        "_build_private_real_delivery_canonical_external_generation_composition_from_owned_repository_v1",
        fail_once,
    )
    with pytest.raises(ValueError, match="R26_ROOT_CONSTRUCTION_FAILED"):
        host._start_private_real_delivery_composition_v1()

    monkeypatch.undo()
    assert host._start_private_real_delivery_composition_v1()._repository is not None


def test_concurrent_waiters_do_not_retry_a_failed_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    host = private._create_private_real_delivery_workflow_host_v1(tmp_path)
    entered = threading.Event()
    release = threading.Event()
    failures: list[Exception] = []

    def fail_after_wait(*args: object) -> object:
        entered.set()
        assert release.wait(timeout=10)
        raise RuntimeError("builder unavailable")

    monkeypatch.setattr(
        private,
        "_build_private_real_delivery_canonical_external_generation_composition_from_owned_repository_v1",
        fail_after_wait,
    )

    def construct() -> None:
        try:
            host._start_private_real_delivery_composition_v1()
        except Exception as error:  # pragma: no cover - assertion below keeps detail
            failures.append(error)

    first = threading.Thread(target=construct)
    second = threading.Thread(target=construct)
    first.start()
    assert entered.wait(timeout=10)
    second.start()
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        owner = host._owner
        if owner is not None and len(owner._bootstrap_issued) == 2:
            break
        time.sleep(0.01)
    assert host._owner is not None
    assert len(host._owner._bootstrap_issued) == 2
    release.set()
    first.join(timeout=10)
    second.join(timeout=10)

    assert len(failures) == 2
    assert all("R26_ROOT_CONSTRUCTION_FAILED" in str(error) for error in failures)

    monkeypatch.undo()
    assert host._start_private_real_delivery_composition_v1()._repository is not None


def test_same_owner_concurrent_bootstraps_publish_one_exact_ready_root(tmp_path: Path) -> None:
    host = private._create_private_real_delivery_workflow_host_v1(tmp_path)
    roots: list[object] = []
    failures: list[Exception] = []

    def construct() -> None:
        try:
            roots.append(host._start_private_real_delivery_composition_v1())
        except Exception as error:  # pragma: no cover - assertion below keeps detail
            failures.append(error)

    threads = [threading.Thread(target=construct) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert not failures
    assert len(roots) == 2
    assert roots[0] is roots[1]


def test_registry_inconsistency_is_corrupt_not_an_identity_collision(tmp_path: Path) -> None:
    host = private._create_private_real_delivery_workflow_host_v1(tmp_path)
    root = host._start_private_real_delivery_composition_v1()
    owner = host._owner
    assert owner is not None
    authorization = owner._issue_bootstrap_authorization_v1()
    with private._REGISTRY_LOCK:
        private._ROOTS_BY_REPOSITORY[id(root._repository)] = object()  # type: ignore[assignment]

    with pytest.raises(ValueError, match="CORRUPT"):
        private._construct_private_r26_reconciliation_root_v1(authorization)


def test_copied_bootstrap_authorization_cannot_replace_issuer_identity(tmp_path: Path) -> None:
    host = private._create_private_real_delivery_workflow_host_v1(tmp_path)
    root = host._start_private_real_delivery_composition_v1()
    owner = host._owner
    assert owner is not None
    authorization = owner._issue_bootstrap_authorization_v1()

    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        private._construct_private_r26_reconciliation_root_v1(copy.copy(authorization))

    assert private._construct_private_r26_reconciliation_root_v1(authorization) is root


def test_marker_one_migrates_after_ready_and_observation_is_exact(tmp_path: Path) -> None:
    root = private._create_private_real_delivery_workflow_host_v1(
        tmp_path
    )._start_private_real_delivery_composition_v1()
    database = root._ledger_store._database_path
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (1,)

    binding = _binding()
    result = root._prepare_r26_protocol_marker_v1(binding)

    assert result.outcome == "prepared"
    observation = root._observe_r26_protocol_marker_v2(binding)
    assert observation.outcome == "PREPARED"
    assert observation.marker_version == 1
    assert observation.protocol_binding_digest is not None
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (2,)
        assert connection.execute(
            "SELECT post_cas_attestation_requirement_version FROM workflow_application_ledger"
        ).fetchone() == (1,)


def test_v1_records_migrate_to_marker_zero_without_rewriting_binding_bytes(tmp_path: Path) -> None:
    root = private._create_private_real_delivery_workflow_host_v1(
        tmp_path
    )._start_private_real_delivery_composition_v1()
    legacy = _binding("legacy")
    assert root._ledger_store.prepare(legacy).outcome == "prepared"
    with sqlite3.connect(root._ledger_store._database_path) as connection:
        before = connection.execute(
            "SELECT binding_json, binding_digest FROM workflow_application_ledger "
            "WHERE attempt_id = ?",
            (legacy.attempt_id,),
        ).fetchone()

    assert root._prepare_r26_protocol_marker_v1(_binding("marker-one")).outcome == "prepared"
    observation = root._observe_r26_protocol_marker_v2(legacy)

    assert observation.outcome == "PREPARED"
    assert observation.marker_version == 0
    with sqlite3.connect(root._ledger_store._database_path) as connection:
        after = connection.execute(
            "SELECT binding_json, binding_digest FROM workflow_application_ledger "
            "WHERE attempt_id = ?",
            (legacy.attempt_id,),
        ).fetchone()
    assert after == before


def test_generic_prepare_writes_marker_zero_after_private_v2_migration(tmp_path: Path) -> None:
    root = private._create_private_real_delivery_workflow_host_v1(
        tmp_path
    )._start_private_real_delivery_composition_v1()
    root._prepare_r26_protocol_marker_v1(_binding("marker-one"))
    zero = _binding("marker-zero")

    result = root._ledger_store.prepare(zero)

    assert result.outcome == "prepared"
    observation = root._observe_r26_protocol_marker_v2(zero)
    assert observation.outcome == "PREPARED"
    assert observation.marker_version == 0


def test_marker_one_exact_replay_is_idempotent_but_marker_zero_never_promotes(tmp_path: Path) -> None:
    root = private._create_private_real_delivery_workflow_host_v1(
        tmp_path
    )._start_private_real_delivery_composition_v1()
    one = _binding("one")

    assert root._prepare_r26_protocol_marker_v1(one).outcome == "prepared"
    assert root._prepare_r26_protocol_marker_v1(one).outcome == "confirmed_prepared"

    zero = _binding("zero")
    assert root._ledger_store.prepare(zero).outcome == "prepared"
    assert root._prepare_r26_protocol_marker_v1(zero).outcome == "conflict"
    assert root._observe_r26_protocol_marker_v2(zero).marker_version == 0


def test_marker_observation_is_read_only_and_missing_is_not_legacy(tmp_path: Path) -> None:
    root = private._create_private_real_delivery_workflow_host_v1(
        tmp_path
    )._start_private_real_delivery_composition_v1()
    root._prepare_r26_protocol_marker_v1(_binding("migrate"))
    missing = _binding("missing")

    with sqlite3.connect(root._ledger_store._database_path) as connection:
        before = connection.execute("SELECT COUNT(*) FROM workflow_application_ledger").fetchone()
    observation = root._observe_r26_protocol_marker_v2(missing)

    assert observation.outcome == "MISSING"
    with sqlite3.connect(root._ledger_store._database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM workflow_application_ledger").fetchone() == before


def test_malformed_marker_metadata_fails_closed(tmp_path: Path) -> None:
    root = private._create_private_real_delivery_workflow_host_v1(
        tmp_path
    )._start_private_real_delivery_composition_v1()
    binding = _binding("corrupt")
    assert root._prepare_r26_protocol_marker_v1(binding).outcome == "prepared"

    with sqlite3.connect(root._ledger_store._database_path) as connection:
        connection.execute(
            "UPDATE workflow_application_ledger SET r26_protocol_binding_digest = ? "
            "WHERE attempt_id = ?",
            ("not-the-canonical-digest", binding.attempt_id),
        )
        connection.commit()

    assert root._observe_r26_protocol_marker_v2(binding).outcome == "CORRUPT"


def test_public_builder_never_constructs_the_imp07a_private_owner_graph(tmp_path: Path) -> None:
    repository = LocalFileRepository(tmp_path)
    composition = build_localfile_external_generation_composition(
        repository, StateMachine(), MemoryEventBus()
    )

    assert composition.external_application._page_store._repository is repository
    with private._REGISTRY_LOCK:
        assert private._ROOTS_BY_REPOSITORY == {}
        assert private._REPOSITORY_BY_DURABLE_ROOT == {}
    with sqlite3.connect(composition.ledger_store._database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (1,)


def test_production_modules_do_not_import_workflow_private_composition() -> None:
    production_root = Path(__file__).parents[1] / "src" / "manga_director" / "production"
    for source in production_root.glob("*.py"):
        assert "localfile_private_real_delivery_composition" not in source.read_text(encoding="utf-8")


def test_excluded_cli_and_fake_only_modules_do_not_import_private_host() -> None:
    source_root = Path(__file__).parents[1] / "src" / "manga_director"
    excluded = (
        source_root / "cli" / "runtime.py",
        source_root / "workflow" / "localfile_next_generation_normal_execution_composition.py",
    )
    for source in excluded:
        assert "localfile_private_real_delivery_composition" not in source.read_text(encoding="utf-8")
    for source in (source_root / "mcp").rglob("*.py"):
        assert "localfile_private_real_delivery_composition" not in source.read_text(encoding="utf-8")


def test_reconstructed_launch_authorization_is_rejected(tmp_path: Path) -> None:
    host = private._create_private_real_delivery_workflow_host_v1(tmp_path)
    forged = object.__new__(private._PrivateRealDeliveryLaunchAuthorizationV1)
    object.__setattr__(forged, "_host", host)
    object.__setattr__(forged, "_issuer", private._LAUNCH_ISSUER)
    object.__setattr__(forged, "_used", False)
    entry = object.__new__(private._PrivateRealDeliveryCompositionEntryV1)

    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        entry._create_owner_from_host_authorization_v1(forged, host._configuration)


def test_copied_launch_authorization_is_rejected(tmp_path: Path) -> None:
    host = private._create_private_real_delivery_workflow_host_v1(tmp_path)
    authorization = host._issue_launch_authorization_v1()
    entry = object.__new__(private._PrivateRealDeliveryCompositionEntryV1)

    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        entry._create_owner_from_host_authorization_v1(
            copy.copy(authorization), host._configuration
        )

    assert entry._create_owner_from_host_authorization_v1(
        authorization, host._configuration
    )._repository is not None


def test_exact_host_configuration_accepts_its_exact_launch_authorization(
    tmp_path: Path,
) -> None:
    host = private._create_private_real_delivery_workflow_host_v1(tmp_path)
    authorization = host._issue_launch_authorization_v1()
    entry = object.__new__(private._PrivateRealDeliveryCompositionEntryV1)

    owner = entry._create_owner_from_host_authorization_v1(
        authorization, host._configuration
    )

    assert owner._host is host


def test_launch_authorization_rejects_foreign_host_configuration(tmp_path: Path) -> None:
    host_a = private._create_private_real_delivery_workflow_host_v1(tmp_path / "a")
    host_b = private._create_private_real_delivery_workflow_host_v1(tmp_path / "b")
    entry = object.__new__(private._PrivateRealDeliveryCompositionEntryV1)

    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        entry._create_owner_from_host_authorization_v1(
            host_a._issue_launch_authorization_v1(), host_b._configuration
        )


def test_launch_authorization_rejects_same_path_replacement_configuration(
    tmp_path: Path,
) -> None:
    host = private._create_private_real_delivery_workflow_host_v1(tmp_path)
    replacement = private._PrivateRealDeliveryLaunchConfigurationV1(tmp_path)
    entry = object.__new__(private._PrivateRealDeliveryCompositionEntryV1)

    assert replacement == host._configuration
    assert replacement is not host._configuration
    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        entry._create_owner_from_host_authorization_v1(
            host._issue_launch_authorization_v1(), replacement
        )


def test_launch_authorization_rejects_value_equal_lookalike_configuration(
    tmp_path: Path,
) -> None:
    host = private._create_private_real_delivery_workflow_host_v1(tmp_path)
    lookalike = private._PrivateRealDeliveryLaunchConfigurationV1(
        host._configuration.repository_root
    )
    entry = object.__new__(private._PrivateRealDeliveryCompositionEntryV1)

    assert lookalike == host._configuration
    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        entry._create_owner_from_host_authorization_v1(
            host._issue_launch_authorization_v1(), lookalike
        )


def test_launch_authorization_rejects_foreign_host_authorization(tmp_path: Path) -> None:
    host_a = private._create_private_real_delivery_workflow_host_v1(tmp_path / "a")
    host_b = private._create_private_real_delivery_workflow_host_v1(tmp_path / "b")
    entry = object.__new__(private._PrivateRealDeliveryCompositionEntryV1)

    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        entry._create_owner_from_host_authorization_v1(
            host_b._issue_launch_authorization_v1(), host_a._configuration
        )


def test_launch_registry_retains_only_the_exact_issued_object_and_tombstones_it(
    tmp_path: Path,
) -> None:
    host = private._create_private_real_delivery_workflow_host_v1(tmp_path)
    authorization = host._issue_launch_authorization_v1()
    entry = object.__new__(private._PrivateRealDeliveryCompositionEntryV1)

    assert len(host._launch_issued) == 1
    assert next(iter(host._launch_issued)) is authorization

    reconstructed = object.__new__(private._PrivateRealDeliveryLaunchAuthorizationV1)
    object.__setattr__(reconstructed, "_host", host)
    object.__setattr__(reconstructed, "_issuer", private._LAUNCH_ISSUER)
    object.__setattr__(reconstructed, "_used", False)
    candidates = (copy.copy(authorization), copy.deepcopy(authorization), reconstructed)
    for candidate in candidates:
        assert all(candidate is not issued for issued in host._launch_issued)
        with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
            entry._create_owner_from_host_authorization_v1(candidate, host._configuration)

    assert entry._create_owner_from_host_authorization_v1(
        authorization, host._configuration
    )._repository is not None
    assert not host._launch_issued
    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        entry._create_owner_from_host_authorization_v1(authorization, host._configuration)

    fresh = host._issue_launch_authorization_v1()
    assert len(host._launch_issued) == 1
    assert next(iter(host._launch_issued)) is fresh
    assert entry._create_owner_from_host_authorization_v1(
        fresh, host._configuration
    )._repository is not None


def test_bootstrap_registry_retains_only_the_exact_issued_object(tmp_path: Path) -> None:
    host = private._create_private_real_delivery_workflow_host_v1(tmp_path)
    root = host._start_private_real_delivery_composition_v1()
    owner = host._owner
    assert owner is not None
    authorization = owner._issue_bootstrap_authorization_v1()

    assert len(owner._bootstrap_issued) == 1
    assert next(iter(owner._bootstrap_issued)) is authorization
    copied = copy.copy(authorization)
    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        private._construct_private_r26_reconciliation_root_v1(copied)

    assert private._construct_private_r26_reconciliation_root_v1(authorization) is root
    assert not owner._bootstrap_issued
    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        private._construct_private_r26_reconciliation_root_v1(authorization)


def test_reconstructed_marker_capability_cannot_migrate_public_composition(
    tmp_path: Path,
) -> None:
    repository = LocalFileRepository(tmp_path)
    composition = build_localfile_external_generation_composition(
        repository, StateMachine(), MemoryEventBus()
    )
    forged = object.__new__(ledger._R26ProtocolV1PreparationCapability)
    forged_root = object()
    object.__setattr__(forged, "_issuer", ledger._R26_PREPARATION_ISSUER)
    object.__setattr__(forged, "_store", composition.ledger_store)
    object.__setattr__(forged, "_repository", repository)
    object.__setattr__(forged, "_root", forged_root)
    object.__setattr__(forged, "_used", False)

    result = composition.ledger_store._prepare_r26_protocol_v1_under_existing_transaction(
        _binding("forged"), forged, repository=repository, root=forged_root
    )

    assert result.outcome == "AUTHORITY_REJECTED"
    assert forged._used is False
    with sqlite3.connect(composition.ledger_store._database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (1,)
        assert connection.execute("SELECT COUNT(*) FROM workflow_application_ledger").fetchone() == (0,)


def test_copied_marker_capability_is_rejected_but_exact_capability_is_accepted(
    tmp_path: Path,
) -> None:
    root = private._create_private_real_delivery_workflow_host_v1(
        tmp_path
    )._start_private_real_delivery_composition_v1()
    capability = ledger._issue_r26_protocol_v1_preparation_capability(
        root._ledger_store,
        root._repository,
        root=root,
        _issuer=ledger._R26_PREPARATION_ISSUER,
    )

    rejected = root._ledger_store._prepare_r26_protocol_v1_under_existing_transaction(
        _binding("copied"), copy.copy(capability), repository=root._repository, root=root
    )
    accepted = root._ledger_store._prepare_r26_protocol_v1_under_existing_transaction(
        _binding("exact"), capability, repository=root._repository, root=root
    )

    assert rejected.outcome == "AUTHORITY_REJECTED"
    assert accepted.outcome == "prepared"


def test_same_path_replacement_ledger_cannot_observe_r26_marker(tmp_path: Path) -> None:
    root = private._create_private_real_delivery_workflow_host_v1(
        tmp_path
    )._start_private_real_delivery_composition_v1()
    binding = _binding("replacement")
    assert root._prepare_r26_protocol_marker_v1(binding).outcome == "prepared"
    replacement = LocalWorkflowApplicationLedgerStore(root._ledger_store._root)

    assert replacement._observe_r26_protocol_exact_readonly_v2(binding).outcome == "AUTHORITY_REJECTED"
    assert root._observe_r26_protocol_marker_v2(binding).outcome == "PREPARED"


def test_broken_registry_state_is_corrupt(tmp_path: Path) -> None:
    host = private._create_private_real_delivery_workflow_host_v1(tmp_path)
    root = host._start_private_real_delivery_composition_v1()
    owner = host._owner
    assert owner is not None
    authorization = owner._issue_bootstrap_authorization_v1()
    with private._REGISTRY_LOCK:
        entry = private._ROOTS_BY_REPOSITORY[id(root._repository)]
        entry.state = "BROKEN"  # type: ignore[assignment]

    with pytest.raises(ValueError, match="CORRUPT"):
        private._construct_private_r26_reconciliation_root_v1(authorization)


def test_failed_registry_state_is_corrupt(tmp_path: Path) -> None:
    host = private._create_private_real_delivery_workflow_host_v1(tmp_path)
    root = host._start_private_real_delivery_composition_v1()
    owner = host._owner
    assert owner is not None
    authorization = owner._issue_bootstrap_authorization_v1()
    with private._REGISTRY_LOCK:
        entry = private._ROOTS_BY_REPOSITORY[id(root._repository)]
        entry.state = "FAILED"  # type: ignore[assignment]

    with pytest.raises(ValueError, match="CORRUPT"):
        private._construct_private_r26_reconciliation_root_v1(authorization)


def test_authorized_value_error_text_is_construction_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    host = private._create_private_real_delivery_workflow_host_v1(tmp_path)

    def fail_after_authorization(*args: object) -> object:
        raise ValueError("AUTHORITY_REJECTED")

    monkeypatch.setattr(
        private,
        "_build_private_real_delivery_canonical_external_generation_composition_from_owned_repository_v1",
        fail_after_authorization,
    )

    with pytest.raises(ValueError, match="R26_ROOT_CONSTRUCTION_FAILED"):
        host._start_private_real_delivery_composition_v1()


def test_failed_generation_cannot_retire_before_joined_waiter_delivery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    host = private._create_private_real_delivery_workflow_host_v1(tmp_path)
    builder_entered = threading.Event()
    release_builder = threading.Event()
    waiter_delivery_started = threading.Event()
    release_waiter_delivery = threading.Event()
    builder_calls: list[str] = []
    outcomes: list[str] = []
    original_delivery = private._complete_joined_waiter_delivery

    def failing_builder(*args: object) -> object:
        del args
        builder_calls.append("failed-generation")
        builder_entered.set()
        assert release_builder.wait(timeout=10)
        raise RuntimeError("builder unavailable")

    def blocked_waiter_delivery(*args: object) -> None:
        waiter_delivery_started.set()
        assert release_waiter_delivery.wait(timeout=10)
        original_delivery(*args)

    monkeypatch.setattr(
        private,
        "_build_private_real_delivery_canonical_external_generation_composition_from_owned_repository_v1",
        failing_builder,
    )
    monkeypatch.setattr(private, "_complete_joined_waiter_delivery", blocked_waiter_delivery)

    def invoke(label: str) -> None:
        try:
            host._start_private_real_delivery_composition_v1()
        except ValueError as error:
            outcomes.append(f"{label}:{error}")

    constructor = threading.Thread(target=invoke, args=("constructor",))
    waiter = threading.Thread(target=invoke, args=("waiter",))
    constructor.start()
    assert builder_entered.wait(timeout=10)
    waiter.start()
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        with private._REGISTRY_LOCK:
            entries = tuple(private._ROOTS_BY_REPOSITORY.values())
            if entries and entries[0].joined_waiters == 1:
                break
        time.sleep(0.01)
    else:
        pytest.fail("joined waiter was not registered")

    release_builder.set()
    assert waiter_delivery_started.wait(timeout=10)
    with private._REGISTRY_LOCK:
        entry = private._ROOTS_BY_REPOSITORY[id(host._owner._repository)]  # type: ignore[union-attr]
        assert entry.state == "CONSTRUCTING"
        assert entry.failure == "R26_ROOT_CONSTRUCTION_FAILED"
    blocked_fresh = threading.Thread(target=invoke, args=("fresh-before-delivery",))
    blocked_fresh.start()
    blocked_fresh.join(timeout=10)
    assert builder_calls == ["failed-generation"]

    release_waiter_delivery.set()
    constructor.join(timeout=10)
    waiter.join(timeout=10)
    assert len(outcomes) == 3
    assert all("R26_ROOT_CONSTRUCTION_FAILED" in outcome for outcome in outcomes)

    monkeypatch.undo()
    assert host._start_private_real_delivery_composition_v1()._repository is not None


def test_corrupt_and_unavailable_marker_migrations_are_distinct(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    corrupt_root = private._create_private_real_delivery_workflow_host_v1(
        tmp_path / "corrupt"
    )._start_private_real_delivery_composition_v1()
    with sqlite3.connect(corrupt_root._ledger_store._database_path) as connection:
        connection.execute("PRAGMA user_version = 99")
        connection.commit()
    assert corrupt_root._prepare_r26_protocol_marker_v1(_binding("corrupt-migration")).outcome == "CORRUPT"

    unavailable_root = private._create_private_real_delivery_workflow_host_v1(
        tmp_path / "unavailable"
    )._start_private_real_delivery_composition_v1()

    def unavailable_connection(*args: object, **kwargs: object) -> sqlite3.Connection:
        del args, kwargs
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(ledger, "_open_ledger_connection", unavailable_connection)
    assert unavailable_root._prepare_r26_protocol_marker_v1(
        _binding("unavailable-migration")
    ).outcome == "UNAVAILABLE"
