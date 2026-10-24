from __future__ import annotations

from pathlib import Path

from manga_director.production.next_generation_page_generation_mode_claim import (
    LocalPageGenerationModeClaimStore,
    PageGenerationModeClaim,
)
from manga_director.workflow.localfile_page_generation_mode_admission import (
    LocalFilePageGenerationModeAdmission,
    PageGenerationModeObservation,
)


class _Fence:
    def __init__(self) -> None:
        self.acquired = 0
        self.released = 0
        self.active = False

    def acquire(self) -> None:
        self.acquired += 1
        self.active = True

    def release(self) -> None:
        self.released += 1
        self.active = False


class _Observations:
    def __init__(self, *values: PageGenerationModeObservation) -> None:
        self.values = list(values)

    def observe(self, project_id: str, page_id: str) -> PageGenerationModeObservation:
        del project_id, page_id
        return self.values.pop(0) if len(self.values) > 1 else self.values[0]


def _claim() -> PageGenerationModeClaim:
    return PageGenerationModeClaim(
        claim_id="claim-1",
        project_id="project-1",
        page_id="page-1",
        page_revision="revision-1",
        page_fingerprint="a" * 64,
        mode="panel_aware",
        mode_binding_reference="plan-1",
        authorizer_reference="authorizer-1",
    )


def _observation(**changes: object) -> PageGenerationModeObservation:
    values: dict[str, object] = {
        "project_id": "project-1",
        "page_id": "page-1",
        "page_revision": "revision-1",
        "page_fingerprint": "a" * 64,
        "page_state": "PromptBuilt",
    }
    values.update(changes)
    return PageGenerationModeObservation(**values)


def test_admission_commits_and_replays_one_exact_claim_under_fence(tmp_path: Path) -> None:
    store = LocalPageGenerationModeClaimStore(tmp_path / "claims")
    observation = _observation()
    service = LocalFilePageGenerationModeAdmission(
        store, _Observations(observation, observation)
    )
    fence = _Fence()

    assert service.admit(_claim(), fence).admitted
    assert fence.acquired == fence.released == 1
    replay = LocalFilePageGenerationModeAdmission(
        store, _Observations(observation, observation)
    ).admit(_claim(), fence)
    assert replay.admitted
    guarded = LocalFilePageGenerationModeAdmission(
        store, _Observations(observation, observation)
    )
    final, applied = guarded.run_admitted(
        _claim(), fence, lambda: fence.active
    )
    assert final.admitted
    assert applied is True
    assert not fence.active


def test_mixed_modes_and_changed_page_authority_fail_closed(tmp_path: Path) -> None:
    store = LocalPageGenerationModeClaimStore(tmp_path / "claims")
    mixed = _observation(
        legacy_record_references=("legacy-1",),
        panel_record_references=("plan-1",),
    )
    assert (
        LocalFilePageGenerationModeAdmission(store, _Observations(mixed))
        .admit(_claim(), _Fence())
        .code
        == "mixed_generation_modes"
    )

    before = _observation()
    after = _observation(page_fingerprint="b" * 64)
    changed = LocalFilePageGenerationModeAdmission(
        store, _Observations(before, after)
    ).admit(_claim(), _Fence())
    assert changed.code == "page_authority_changed"


def test_provider_start_rechecks_authority_and_runs_under_same_fence(
    tmp_path: Path,
) -> None:
    store = LocalPageGenerationModeClaimStore(tmp_path / "claims")
    observation = _observation()
    service = LocalFilePageGenerationModeAdmission(
        store,
        _Observations(observation, observation, observation, observation),
    )
    fence = _Fence()
    assert service.admit(_claim(), fence).admitted

    admission, active = service.run_provider_start_admitted(
        _claim(), fence, lambda: fence.active
    )

    assert admission.admitted
    assert active is True
    stale = LocalFilePageGenerationModeAdmission(
        store, _Observations(_observation(page_fingerprint="b" * 64))
    )
    called = False

    def start() -> bool:
        nonlocal called
        called = True
        return True

    blocked, result = stale.run_provider_start_admitted(_claim(), fence, start)
    assert not blocked.admitted
    assert blocked.code == "page_authority_mismatch"
    assert result is None
    assert not called


def test_generated_replay_requires_exact_claim_and_runs_under_same_fence(
    tmp_path: Path,
) -> None:
    store = LocalPageGenerationModeClaimStore(tmp_path / "claims")
    prompt_built = _observation()
    fence = _Fence()
    assert LocalFilePageGenerationModeAdmission(
        store, _Observations(prompt_built, prompt_built)
    ).admit(_claim(), fence).admitted
    generated = _observation(
        page_revision="revision-2",
        page_fingerprint="b" * 64,
        page_state="Generated",
        output_asset_id="composite-1",
    )
    service = LocalFilePageGenerationModeAdmission(
        store, _Observations(generated, generated)
    )

    admission, active = service.run_generated_replay_admitted(
        _claim(), fence, "composite-1", lambda: fence.active
    )

    assert admission.admitted
    assert admission.code == "generated_replay_admitted"
    assert active is True
    assert not fence.active


def test_generated_replay_without_the_exact_source_claim_fails_closed(
    tmp_path: Path,
) -> None:
    generated = _observation(
        page_revision="revision-2",
        page_fingerprint="b" * 64,
        page_state="Generated",
        output_asset_id="composite-1",
    )
    called = False

    def replay() -> bool:
        nonlocal called
        called = True
        return True

    admission, result = LocalFilePageGenerationModeAdmission(
        LocalPageGenerationModeClaimStore(tmp_path / "claims"),
        _Observations(generated),
    ).run_generated_replay_admitted(
        _claim(), _Fence(), "composite-1", replay
    )

    assert not admission.admitted
    assert admission.code == "generated_replay_claim_unavailable"
    assert result is None
    assert not called


def test_generated_replay_requires_exact_current_output_asset(
    tmp_path: Path,
) -> None:
    store = LocalPageGenerationModeClaimStore(tmp_path / "claims")
    prompt_built = _observation()
    assert LocalFilePageGenerationModeAdmission(
        store, _Observations(prompt_built, prompt_built)
    ).admit(_claim(), _Fence()).admitted

    for current_output_asset_id in (None, "composite-other"):
        generated = _observation(
            page_revision="revision-2",
            page_fingerprint="b" * 64,
            page_state="Generated",
            output_asset_id=current_output_asset_id,
        )
        called = False

        def replay() -> bool:
            nonlocal called
            called = True
            return True

        admission, result = LocalFilePageGenerationModeAdmission(
            store, _Observations(generated)
        ).run_generated_replay_admitted(
            _claim(), _Fence(), "composite-1", replay
        )

        assert not admission.admitted
        assert admission.code == "generated_replay_output_asset_mismatch"
        assert result is None
        assert not called
