"""Focused V7-04 tests for explicitly authorized LocalFile ComfyUI generation."""

from __future__ import annotations

import base64
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import pytest

from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState, StateMachine
from manga_director.events import MemoryEventBus
from manga_director.production.next_generation_normal_execution_attempt import (
    LocalNormalExecutionAttemptStore,
)
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.workflow import localfile_comfyui_real_image_generation as comfy_module
from manga_director.workflow.engine import WorkflowEngine
from manga_director.workflow.localfile_comfyui_real_image_generation import (
    execute_localfile_comfyui_real_image_generation,
)

_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)
_CHECKPOINT = "local-model.safetensors"
_NOW = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)


class _HttpClient:
    origin = "http://127.0.0.1:8188"

    def __init__(
        self,
        mode: Literal["success", "submission-ambiguous", "malformed-png"] = "success",
        *,
        first_read_check: Callable[[], None] | None = None,
    ) -> None:
        self.mode = mode
        self.posts = 0
        self.reads = 0
        self._first_read_check = first_read_check

    def get_json(self, path: str) -> object:
        if self.reads == 0 and self._first_read_check is not None:
            self._first_read_check()
        self.reads += 1
        if path == "/system_stats":
            return {"system": {}}
        if path.startswith("/object_info/"):
            node_type = path.rsplit("/", 1)[-1]
            required: dict[str, object] = {}
            if node_type == "CheckpointLoaderSimple":
                required = {"ckpt_name": [[_CHECKPOINT]]}
            return {node_type: {"python_module": "nodes", "input": {"required": required}}}
        if path == "/history/prompt-1":
            return {
                "prompt-1": {
                    "status": {"status_str": "success", "completed": True},
                    "outputs": {
                        "7": {
                            "images": [
                                {
                                    "filename": "result.png",
                                    "subfolder": "",
                                    "type": "output",
                                }
                            ]
                        }
                    },
                }
            }
        raise AssertionError(path)

    def post_json(self, path: str, payload: object) -> object:
        assert path == "/prompt"
        assert isinstance(payload, dict) and set(payload) == {"prompt", "client_id"}
        self.posts += 1
        if self.mode == "submission-ambiguous":
            raise TimeoutError("outcome unknown")
        return {"prompt_id": "prompt-1", "node_errors": {}}

    def get_png(self, path: str, query: object) -> bytes:
        assert path == "/view"
        assert query == {"filename": "result.png", "subfolder": "", "type": "output"}
        if self.mode == "malformed-png":
            return b"\x89PNG\r\n\x1a\nmalformed"
        return _PNG_BYTES


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
            id="project-v7-04",
            title="V7-04",
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
    client: _HttpClient,
    *,
    token: str = "1" * 32,
    authorized_by: str = "human:editor",
):
    return execute_localfile_comfyui_real_image_generation(
        repository,
        _engine(),
        "project-v7-04",
        "1",
        authorized_by,
        checkpoint_name=_CHECKPOINT,
        http_client=client,
        now=lambda: _NOW,
        token_factory=lambda: token,
    )


def test_real_path_runs_one_fixed_prompt_png_and_registers_one_asset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository(tmp_path)
    client = _HttpClient()
    composition_builder = comfy_module._build_localfile_external_generation_composition_v1

    def build_with_test_fence(*args: object, **kwargs: object):
        composition = composition_builder(*args, **kwargs)
        composition.external_application._fence_factory = _Fence
        return composition

    monkeypatch.setattr(
        comfy_module,
        "_build_localfile_external_generation_composition_v1",
        build_with_test_fence,
    )

    report = _execute(repository, client)

    assert report.status == "completed" and report.completed is True, tuple(
        item.code for item in report.findings
    )
    assert report.provider_invocation_performed is True
    assert report.external_application_delegated is True
    assert client.posts == 1
    page = repository.load("project-v7-04").page(1)
    assert page.state == PageState.GENERATED
    assert page.image is not None
    assets = tuple(
        (repository._next_generation_normal_execution_owner_root() / "assets" / "assets").glob(
            "*.png"
        )
    )
    assert len(assets) == 1 and assets[0].read_bytes() == _PNG_BYTES


@pytest.mark.parametrize(
    "authorized_by",
    ("", "local user", "local-user", "local-user@example.com", "fixed-secret-user"),
)
def test_invalid_human_authorization_fails_before_preflight_or_submission(
    tmp_path: Path, authorized_by: str
) -> None:
    repository = _repository(tmp_path)
    client = _HttpClient()

    with pytest.raises(ValueError, match="authorized-by"):
        _execute(repository, client, authorized_by=authorized_by)

    assert client.reads == 0
    assert client.posts == 0
    assert not repository._next_generation_normal_execution_owner_root().exists()


def test_checkpoint_is_required_before_preflight_or_attempt(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    client = _HttpClient()

    with pytest.raises(ValueError, match="MANGA_DIRECTOR_COMFYUI_CHECKPOINT"):
        execute_localfile_comfyui_real_image_generation(
            repository,
            _engine(),
            "project-v7-04",
            "1",
            "human:editor",
            checkpoint_lookup=lambda _name: None,
            http_client=client,
        )

    assert client.reads == client.posts == 0


def test_durable_attempt_is_reserved_before_read_only_preflight(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    attempt_id = "attempt:v7-04:human:editor:" + "3" * 32

    def assert_reserved() -> None:
        store = LocalNormalExecutionAttemptStore(
            repository._next_generation_normal_execution_owner_root() / "attempts"
        )
        record = store.lookup(attempt_id)
        assert record is not None and record.state == "RESERVED"

    client = _HttpClient(first_read_check=assert_reserved)
    _execute(repository, client, token="3" * 32)

    assert client.posts == 1


@pytest.mark.parametrize("mode", ("submission-ambiguous", "malformed-png"))
def test_ambiguous_post_or_result_requires_recovery_and_blocks_replacement(
    tmp_path: Path,
    mode: Literal["submission-ambiguous", "malformed-png"],
) -> None:
    repository = _repository(tmp_path)
    client = _HttpClient(mode)

    first = _execute(repository, client, token="5" * 32)
    second = _execute(repository, client, token="6" * 32)

    assert first.status == "partial"
    assert tuple(item.code for item in first.findings) == ("RECOVERY_REQUIRED",)
    assert second.status == "blocked"
    assert tuple(item.code for item in second.findings) == ("ATTEMPT_RESERVATION_BLOCKED",)
    assert client.posts == 1
    store = LocalNormalExecutionAttemptStore(
        repository._next_generation_normal_execution_owner_root() / "attempts"
    )
    attempt_id = "attempt:v7-04:human:editor:" + "5" * 32
    record = store.lookup(attempt_id)
    assert record is not None and record.state == "PROVIDER_STARTED"
    assert repository.load("project-v7-04").page(1).state == PageState.PROMPT_BUILT


def test_v7_04_source_has_no_i02_or_legacy_stub_coupling() -> None:
    source = Path(comfy_module.__file__).read_text(encoding="utf-8")
    assert "future_real_delivery_i02" not in source
    assert "ComfyUIImageGenerator" not in source
    assert "OpenAIImageGenerator" not in source
