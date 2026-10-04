from __future__ import annotations

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
