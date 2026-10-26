from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor

from manga_director.production.next_generation_normal_execution_attempt import (
    LocalNormalExecutionAttemptStore,
    NormalExecutionAttemptReservationDTO,
    NormalExecutionAttemptService,
    derive_execution_fingerprint,
)


def _reservation(attempt_id: str = "attempt-1", page_id: str = "page-1") -> NormalExecutionAttemptReservationDTO:
    return NormalExecutionAttemptReservationDTO(
        attempt_id=attempt_id,
        request_id="request-1",
        project_id="project-1",
        page_id=page_id,
        target_page_reference="target-1",
        provider_reference="provider-1",
        execution_fingerprint="a" * 64,
    )


def test_reservation_is_durable_and_exact_replay_is_confirmed(tmp_path) -> None:
    store = LocalNormalExecutionAttemptStore(tmp_path.resolve())
    service = NormalExecutionAttemptService()

    assert service.reserve(_reservation(), store).status == "reserved"
    replay = service.reserve(_reservation(), LocalNormalExecutionAttemptStore(tmp_path.resolve()))

    assert replay.status == "reserved"
    assert replay.reservation_confirmed is True
    assert replay.provider_invocation_permitted is False


def test_conflicting_attempt_and_active_target_fail_closed(tmp_path) -> None:
    store = LocalNormalExecutionAttemptStore(tmp_path.resolve())
    service = NormalExecutionAttemptService()
    assert service.reserve(_reservation(), store).status == "reserved"

    changed = _reservation()
    changed = changed.model_copy(update={"execution_fingerprint": "b" * 64})
    assert service.reserve(changed, store).status == "blocked"
    assert service.reserve(_reservation("attempt-2"), store).status == "blocked"
    assert service.reserve(_reservation("attempt-3", "page-2"), store).status == "reserved"


def test_provider_started_consumes_call_opportunity_across_reopen(tmp_path) -> None:
    store = LocalNormalExecutionAttemptStore(tmp_path.resolve())
    service = NormalExecutionAttemptService()
    reservation = _reservation()
    service.reserve(reservation, store)

    started = service.begin_provider(reservation, store)
    replay = service.begin_provider(reservation, LocalNormalExecutionAttemptStore(tmp_path.resolve()))

    assert started.provider_invocation_permitted is True
    assert replay.provider_invocation_permitted is False
    assert replay.state == "PROVIDER_STARTED"


def test_same_attempt_concurrency_allows_one_start_only(tmp_path) -> None:
    store = LocalNormalExecutionAttemptStore(tmp_path.resolve())
    service = NormalExecutionAttemptService()
    reservation = _reservation()
    service.reserve(reservation, store)

    with ThreadPoolExecutor(max_workers=2) as executor:
        reports = tuple(executor.map(lambda _: service.begin_provider(reservation, store), range(2)))

    assert sum(report.provider_invocation_permitted for report in reports) == 1


def test_provider_declared_failure_is_terminal_but_runtime_ambiguity_is_not(tmp_path) -> None:
    store = LocalNormalExecutionAttemptStore(tmp_path.resolve())
    service = NormalExecutionAttemptService()
    reservation = _reservation()
    service.reserve(reservation, store)
    service.begin_provider(reservation, store)

    complete = service.record_provider_declared_failure(reservation, store)

    assert complete.state == "COMPLETED"
    assert complete.completion_kind == "provider_declared_failure"


def test_canonical_fingerprint_is_order_independent_and_binds_logical_change() -> None:
    left = {"attempt_id": "attempt-1", "authorization_ids": ("b", "a"), "provider": {"model": "m"}}
    right = {"provider": {"model": "m"}, "authorization_ids": ("a", "b"), "attempt_id": "attempt-1"}

    assert derive_execution_fingerprint(left) == derive_execution_fingerprint(right)
    assert derive_execution_fingerprint(left) != derive_execution_fingerprint({**left, "attempt_id": "attempt-2"})


def test_page_observation_is_read_only_exact_and_fail_closed(tmp_path) -> None:
    root = tmp_path / "attempts"
    store = LocalNormalExecutionAttemptStore(root.resolve())
    assert store.observe_page("project-1", "page-1").outcome == "missing"
    assert not root.exists()
    root.mkdir()
    assert store.observe_page("project-1", "page-1").outcome == "corrupt"

    service = NormalExecutionAttemptService()
    first = _reservation()
    service.reserve(first, store)
    assert store.observe_page("project-1", "page-1").records[0].reservation == first
    service.begin_provider(first, store)
    service.record_provider_declared_failure(first, store)
    service.reserve(_reservation("attempt-2"), store)
    assert store.observe_page("project-1", "page-1").outcome == "ambiguous"

    with sqlite3.connect(store._database) as connection:
        connection.execute("UPDATE normal_execution_attempt_schema SET version = 99")
    assert store.observe_page("project-1", "page-1").outcome == "corrupt"


def test_page_observation_requires_exact_active_index_and_no_unknown_objects(
    tmp_path,
) -> None:
    missing_index = LocalNormalExecutionAttemptStore(
        (tmp_path / "missing-index").resolve()
    )
    missing_index.reserve(_reservation())
    with sqlite3.connect(missing_index._database) as connection:
        connection.execute("DROP INDEX active_normal_execution_target")
    assert missing_index.observe_page("project-1", "page-1").outcome == "corrupt"

    extra_object = LocalNormalExecutionAttemptStore(
        (tmp_path / "extra-object").resolve()
    )
    extra_object.reserve(_reservation())
    with sqlite3.connect(extra_object._database) as connection:
        connection.execute(
            "CREATE TRIGGER unexpected_trigger AFTER INSERT ON normal_execution_attempts "
            "BEGIN SELECT 1; END"
        )
    assert extra_object.observe_page("project-1", "page-1").outcome == "corrupt"
