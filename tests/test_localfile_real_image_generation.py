"""Focused V7-03 tests for explicitly authorized LocalFile real generation."""

from __future__ import annotations

import base64
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState, StateMachine
from manga_director.events import MemoryEventBus
from manga_director.production.next_generation_normal_execution_attempt import (
    LocalNormalExecutionAttemptStore,
)
from manga_director.production.next_generation_panel_execution_attempt import (
    PanelAttemptReservation,
)
from manga_director.production.next_generation_panel_generation_evidence import (
    LocalPanelGenerationAuthority,
)
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.workflow import localfile_real_image_generation as real_generation_module
from manga_director.workflow.engine import WorkflowEngine
from manga_director.workflow.localfile_real_image_generation import (
    execute_localfile_real_image_generation,
)

_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)
_SECRET = "v7-03-test-credential-not-persisted"
_NOW = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)


class _Client:
    def __init__(self, image_bytes: bytes = _PNG_BYTES, *, failure: Exception | None = None) -> None:
        self._image_bytes = image_bytes
        self._failure = failure
        self.calls: list[dict[str, object]] = []
        self.closed = False

    def generate_image(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if self._failure is not None:
            raise self._failure
        encoded = base64.b64encode(self._image_bytes).decode("ascii")
        return SimpleNamespace(data=[SimpleNamespace(b64_json=encoded)])

    def close(self) -> None:
        self.closed = True


class _ClientFactory:
    def __init__(self, client: _Client) -> None:
        self.client = client
        self.create_calls = 0

    def create(
        self, credential: str, *, timeout_seconds: int, max_retries: int
    ) -> _Client:
        assert credential == _SECRET
        assert timeout_seconds == 120
        assert max_retries == 0
        self.create_calls += 1
        return self.client


class _Fence:
    def __init__(self, project_id: str, page_id: str) -> None:
        self._project_id = project_id
        self._page_id = page_id
        self._held = False

    def acquire(self) -> None:
        assert self._held is False
        self._held = True

    def release(self) -> None:
        self._held = False

    def _r26_is_held_for(self, project_id: str, page_id: str) -> bool:
        return self._held and (project_id, page_id) == (self._project_id, self._page_id)


def _repository(tmp_path: Path) -> LocalFileRepository:
    repository = LocalFileRepository(tmp_path)
    repository.save(
        Project(
            id="project-v7-03",
            title="V7-03",
            pages=[
                Page(
                    page_number=1,
                    state=PageState.PROMPT_BUILT,
                    page_design={},
                    review={},
                    storyboard={"panels": [{"panel": 1}]},
                    prompt={"prompt_markdown": "one monochrome manga panel"},
                )
            ],
        )
    )
    return repository


def _engine() -> WorkflowEngine:
    return WorkflowEngine(
        state_machine=StateMachine(),
        event_bus=MemoryEventBus(),
        agents={},
    )


def _execute(
    repository: LocalFileRepository,
    factory: _ClientFactory,
    *,
    token: str = "1" * 32,
    authorized_by: str = "human:editor",
):
    return execute_localfile_real_image_generation(
        repository,
        _engine(),
        "project-v7-03",
        "1",
        authorized_by,
        secret_lookup=lambda name: _SECRET if name == "OPENAI_API_KEY" else None,
        client_factory=factory,
        now=lambda: _NOW,
        token_factory=lambda: token,
    )


def test_real_path_runs_one_prompt_only_png_and_registers_one_asset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository(tmp_path)
    client = _Client()
    factory = _ClientFactory(client)
    composition_builder = real_generation_module._build_localfile_external_generation_composition_v1

    def build_with_test_fence(*args: object, **kwargs: object):
        composition = composition_builder(*args, **kwargs)
        composition.external_application._fence_factory = _Fence
        return composition

    monkeypatch.setattr(
        real_generation_module,
        "_build_localfile_external_generation_composition_v1",
        build_with_test_fence,
    )

    report = _execute(repository, factory)

    assert report.status == "completed" and report.completed is True, tuple(
        item.code for item in report.findings
    )
    assert report.provider_invocation_performed is True
    assert report.external_application_delegated is True
    assert factory.create_calls == 1
    assert client.calls == [
        {
            "model": "gpt-image-2-2026-04-21",
            "prompt": "one monochrome manga panel",
            "n": 1,
            "size": "1536x1024",
            "quality": "low",
        }
    ]
    assert client.closed is True
    page = repository.load("project-v7-03").page(1)
    assert page.state == PageState.GENERATED
    assert page.image is not None
    assert page.image["artifact_kind"] == "logical_output_asset"
    assert page.image["output_asset_id"].startswith("asset-generated-")
    assets = tuple(
        (repository._next_generation_normal_execution_owner_root() / "assets" / "assets").glob(
            "*.png"
        )
    )
    assert len(assets) == 1 and assets[0].read_bytes() == _PNG_BYTES


def test_generated_crash_window_replays_exact_application_without_provider_setup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository(tmp_path)
    factory = _ClientFactory(_Client())
    composition_builder = (
        real_generation_module._build_localfile_external_generation_composition_v1
    )

    def build_with_test_fence(*args: object, **kwargs: object):
        composition = composition_builder(*args, **kwargs)
        composition.external_application._fence_factory = _Fence
        return composition

    monkeypatch.setattr(
        real_generation_module,
        "_build_localfile_external_generation_composition_v1",
        build_with_test_fence,
    )
    token = "9" * 32
    assert _execute(repository, factory, token=token).completed
    attempt_id = f"attempt:v7-03:human:editor:{token}"
    database = (
        repository._next_generation_normal_execution_owner_root()
        / "attempts"
        / "normal_execution_attempts.sqlite3"
    )
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE normal_execution_attempts SET state = 'PROVIDER_COMPLETED', "
            "completion_kind = NULL WHERE attempt_id = ?",
            (attempt_id,),
        )

    def provider_setup_forbidden(_name: str) -> str | None:
        raise AssertionError("Generated replay must not resolve Provider credentials")

    replay = execute_localfile_real_image_generation(
        repository,
        _engine(),
        "project-v7-03",
        "1",
        "human:editor",
        secret_lookup=provider_setup_forbidden,
        client_factory=factory,
        now=lambda: _NOW,
        token_factory=lambda: token,
    )

    assert replay.completed and replay.provider_invocation_performed is False
    assert factory.create_calls == 1
    record = LocalNormalExecutionAttemptStore(database.parent).lookup(attempt_id)
    assert record is not None
    assert record.state == "COMPLETED"
    assert record.completion_kind == "application_event_published"


def test_secret_and_human_authorization_are_not_persisted(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    report = _execute(repository, _ClientFactory(_Client()), authorized_by="human:reviewer-7")

    persisted = b"".join(
        path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()
    )
    serialized = report.model_dump_json()
    assert _SECRET.encode() not in persisted
    assert _SECRET not in serialized
    assert b"human:reviewer-7" in persisted


@pytest.mark.parametrize(
    "authorized_by",
    ("", "local user", "local-user", "local-user@example.com", "fixed-secret-user"),
)
def test_invalid_human_authorization_fails_before_provider_attempt(
    tmp_path: Path, authorized_by: str
) -> None:
    repository = _repository(tmp_path)
    factory = _ClientFactory(_Client())

    with pytest.raises(ValueError, match="authorized-by"):
        _execute(repository, factory, authorized_by=authorized_by)

    assert factory.create_calls == 0
    root = repository._next_generation_normal_execution_owner_root()
    assert not (root / "attempts" / "normal_execution_attempts.sqlite3").exists()


def test_missing_secret_fails_before_attempt_and_network(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    factory = _ClientFactory(_Client())

    with pytest.raises(ValueError, match="OPENAI_API_KEY is unavailable"):
        execute_localfile_real_image_generation(
            repository,
            _engine(),
            "project-v7-03",
            "1",
            "human:editor",
            secret_lookup=lambda _name: None,
            client_factory=factory,
            now=lambda: _NOW,
            token_factory=lambda: "2" * 32,
        )

    assert factory.create_calls == 0
    root = repository._next_generation_normal_execution_owner_root()
    assert not (root / "attempts" / "normal_execution_attempts.sqlite3").exists()


def test_missing_optional_package_fails_before_attempt_and_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository(tmp_path)

    def missing(name: str) -> object:
        assert name == "openai"
        raise ImportError

    monkeypatch.setattr(
        "manga_director.workflow.localfile_real_image_generation.import_module",
        missing,
    )
    with pytest.raises(ValueError, match="OpenAI support is unavailable"):
        execute_localfile_real_image_generation(
            repository,
            _engine(),
            "project-v7-03",
            "1",
            "human:editor",
            secret_lookup=lambda _name: _SECRET,
            now=lambda: _NOW,
            token_factory=lambda: "3" * 32,
        )

    root = repository._next_generation_normal_execution_owner_root()
    assert not (root / "attempts" / "normal_execution_attempts.sqlite3").exists()


def test_malformed_png_is_not_registered_or_applied(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    factory = _ClientFactory(_Client(b"\x89PNG\r\n\x1a\nnot-a-structural-png"))

    report = _execute(repository, factory, token="4" * 32)

    assert report.status == "partial"
    assert tuple(item.code for item in report.findings) == ("ASSET_REGISTRATION_PARTIAL",)
    assert repository.load("project-v7-03").page(1).state == PageState.PROMPT_BUILT
    assets = repository._next_generation_normal_execution_owner_root() / "assets" / "assets"
    assert tuple(assets.glob("*.png")) == ()


def test_ambiguous_provider_failure_consumes_attempt_and_blocks_replacement(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    client = _Client(failure=TimeoutError("provider outcome unknown"))
    factory = _ClientFactory(client)

    first = _execute(repository, factory, token="5" * 32)
    second = _execute(repository, factory, token="6" * 32)

    assert first.status == "partial"
    assert tuple(item.code for item in first.findings) == ("PROVIDER_OUTCOME_AMBIGUOUS",)
    assert second.status == "blocked"
    assert tuple(item.code for item in second.findings) == ("ATTEMPT_RESERVATION_BLOCKED",)
    assert factory.create_calls == 1
    store = LocalNormalExecutionAttemptStore(
        repository._next_generation_normal_execution_owner_root() / "attempts"
    )
    attempt_id = "attempt:v7-03:human:editor:" + "5" * 32
    record = store.lookup(attempt_id)
    assert record is not None and record.state == "PROVIDER_STARTED"
    assert "human:editor" in record.reservation.attempt_id
    assert b"human:editor" in store._database.read_bytes()
    assert repository.load("project-v7-03").page(1).state == PageState.PROMPT_BUILT


def test_panel_authority_conflict_blocks_before_client_or_workflow_side_effect(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    root = repository._next_generation_normal_execution_owner_root()
    panel = LocalPanelGenerationAuthority(root / "panel-generation-authority")
    panel.reserve(
        PanelAttemptReservation(
            attempt_id="panel-attempt-1",
            plan_id="plan-1",
            plan_fingerprint="a" * 64,
            project_id="project-v7-03",
            page_id="1",
            panel_id="panel-1",
            panel_order=1,
            request_id="panel-request-1",
            request_fingerprint="b" * 64,
            provider_reference="provider-1",
            authorization_reference="authorization-1",
            execution_fingerprint="c" * 64,
        )
    )
    factory = _ClientFactory(_Client())

    report = _execute(repository, factory, token="7" * 32)

    assert report.status == "blocked"
    assert tuple(item.code for item in report.findings) == (
        "GENERATION_MODE_ADMISSION_BLOCKED",
    )
    assert factory.create_calls == 0
    assert repository.load("project-v7-03").page(1).state == PageState.PROMPT_BUILT
    assert not (root / "attempts" / "normal_execution_attempts.sqlite3").exists()
