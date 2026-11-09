from __future__ import annotations

import http.client
import importlib
import importlib.util
import json
import logging
import os
import re
import socket
import traceback
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from threading import Event, Lock, Thread
from time import monotonic, sleep
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response

from manga_director.adapters import ImageGeneratorFactory, LLMFactory
from manga_director.adapters.image_generator import ImageResult
from manga_director.adapters.llm_provider import LLMResult, PromptRequest
from manga_director.agents.registry import primary_agents, support_agents
from manga_director.api.composition import build_workflow_app
from manga_director.api.workflow import LOCAL_WEB_ORIGINS
from manga_director.domain.exceptions import ProjectNotFoundError, ValidationError
from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState, StateMachine
from manga_director.events import MemoryEventBus
from manga_director.observability import WorkflowObserver
from manga_director.production.explicit_storyboard_input import (
    create_authority,
    validate_confirmation,
    validate_panels,
)
from manga_director.prompting import PromptPipeline, PromptTemplateLoader
from manga_director.prompting.contracts import PromptTemplate
from manga_director.repositories import ProjectLoader
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.workflow import (
    ChapterWorkflowEngine,
    PageNumberWorkflowScheduler,
    ProjectWorkflowEngine,
    WorkflowContext,
    WorkflowCoordinator,
    WorkflowEngine,
)
from manga_director.workflow.contracts import AgentResult, WorkflowResult
from manga_director.workflow.durable_execution import (
    DurablePageStorePort,
    DurableWorkflowExecutionCoordinator,
    LogicalOutputAssetQualityGatePort,
)
from manga_director.workflow.page_execution_fence import (
    PageExecutionFenceError,
    PageExecutionFencePort,
    local_page_execution_fence,
)


@pytest.fixture(autouse=True)
def _use_platform_page_execution_fence() -> Iterator[None]:
    """Keep durable integration coverage executable on the host platform."""

    original_init = DurableWorkflowExecutionCoordinator.__init__

    def init_with_platform_fence(
        self: DurableWorkflowExecutionCoordinator,
        engine: WorkflowEngine,
        page_store: DurablePageStorePort,
        *,
        fence_factory: Callable[[str, str], PageExecutionFencePort] | None = None,
        logical_output_asset_quality_gate: LogicalOutputAssetQualityGatePort | None = None,
    ) -> None:
        original_init(
            self,
            engine,
            page_store,
            fence_factory=fence_factory or local_page_execution_fence,
            logical_output_asset_quality_gate=logical_output_asset_quality_gate,
        )

    patch = pytest.MonkeyPatch()
    patch.setattr(DurableWorkflowExecutionCoordinator, "__init__", init_with_platform_fence)
    yield
    patch.undo()


# Keep the approved source/panel `*_sha256` provenance fields out of this set.
_FORBIDDEN_CONFIRMATION_OUTPUT_KEYS = {
    "authorization",
    "capability",
    "confirmed",
    "cookie",
    "expectedsource",
    "explicitstoryboardinputauthority",
    "fingerprint",
    "aggregatesourcefingerprint",
    "sourcefingerprint",
    "rawrequest",
    "rawrequestbody",
    "rawrequestenvelope",
    "request",
    "requestbody",
    "requestenvelope",
    "requestenvelopemarker",
    "requestversion",
    "revision",
    "aggregatesourcerevision",
    "sourcerevision",
    "expectedrevision",
    "expectedaggregatefingerprint",
}


def _assert_confirmation_output_has_no_internal_values(
    value: Any, *sensitive_markers: str
) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized_key = "".join(character for character in str(key).casefold() if character.isalnum())
            assert normalized_key not in _FORBIDDEN_CONFIRMATION_OUTPUT_KEYS, key
            _assert_confirmation_output_has_no_internal_values(nested, *sensitive_markers)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            _assert_confirmation_output_has_no_internal_values(nested, *sensitive_markers)
    elif isinstance(value, str):
        for marker in sensitive_markers:
            assert marker not in value


# Do not scan for a bare integer revision: it can equal an allowed Page number
# or schema version. Structured output uses the forbidden-key check above;
# textual output is checked for labeled revision/fingerprint diagnostics.
_INTERNAL_REVISION_TEXT = re.compile(
    r"\b[a-z0-9_-]*revision\b[\"']?\s*[:=]\s*[\"']?-?\d+",
    re.IGNORECASE,
)
_INTERNAL_FINGERPRINT_TEXT = re.compile(
    r"\b[a-z0-9_-]*fingerprint\b[\"']?\s*[:=]",
    re.IGNORECASE,
)


def _assert_no_internal_revision_or_fingerprint_text(value: str) -> None:
    assert _INTERNAL_REVISION_TEXT.search(value) is None
    assert _INTERNAL_FINGERPRINT_TEXT.search(value) is None


def _assert_sanitized_confirmation_conflict(response: Any) -> None:
    assert response.status_code == 409
    assert response.json() == {
        "code": "confirmation_conflict",
        "message": "The Page changed. Reload and review it before confirming again.",
    }
    _assert_confirmation_output_has_no_internal_values(response.json())
    _assert_no_internal_revision_or_fingerprint_text(response.text)


def _assert_captured_streams_are_clean(
    streams: tuple[str, str], *sensitive_values: str
) -> None:
    for stream in streams:
        _assert_confirmation_output_has_no_internal_values(stream, *sensitive_values)
        _assert_no_internal_revision_or_fingerprint_text(stream)


@contextmanager
def _running_loopback_uvicorn(app: Any, uvicorn: Any) -> Iterator[int]:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server: Any | None = None
    thread: Thread | None = None
    port: int | None = None
    thread_started = False
    try:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        listener.setblocking(False)
        port = listener.getsockname()[1]
        server = uvicorn.Server(
            uvicorn.Config(
                app,
                host="127.0.0.1",
                port=port,
                access_log=True,
                log_config=None,
                log_level=None,
            )
        )
        thread = Thread(
            target=server.run,
            kwargs={"sockets": [listener]},
            name="v7-17-uvicorn-log-test",
            daemon=True,
        )
        thread.start()
        thread_started = True
        deadline = monotonic() + 10
        while not server.started and thread.is_alive() and monotonic() < deadline:
            sleep(0.01)
        assert thread.is_alive() and server.started, "Uvicorn did not start on loopback."
        yield port
    finally:
        try:
            if thread_started and server is not None and thread is not None:
                server.should_exit = True
                thread.join(timeout=10)
                if thread.is_alive():
                    server.force_exit = True
                    listener.close()
                    thread.join(timeout=5)
            listener.close()
            assert thread is None or not thread.is_alive(), (
                "Uvicorn thread remained alive after shutdown."
            )
            assert listener.fileno() == -1, "Uvicorn listening socket was not closed."
            if port is not None:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                    if os.name == "posix":
                        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    probe.bind(("127.0.0.1", port))
        finally:
            listener.close()


def _loopback_json_post(
    port: int,
    project_id: str,
    body: bytes,
    credential: str,
) -> tuple[int, str]:
    origin = LOCAL_WEB_ORIGINS[0]
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        connection.request(
            "POST",
            f"/projects/{project_id}/pages/1/storyboard/confirm",
            body=body,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Origin": origin,
                "Referer": f"{origin}/projects/{project_id}/pages/1",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Dest": "empty",
                "Authorization": credential,
            },
        )
        response = connection.getresponse()
        return response.status, response.read().decode("utf-8")
    finally:
        connection.close()


@contextmanager
def _capture_uvicorn_access_logs() -> Iterator[list[logging.LogRecord]]:
    logger = logging.getLogger("uvicorn.access")
    original_handlers = logger.handlers[:]
    original_level = logger.level
    original_propagate = logger.propagate
    original_disabled = logger.disabled
    records: list[logging.LogRecord] = []

    class _CaptureHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter("%(message)s"))
    capture_handler = _CaptureHandler(logging.INFO)
    logger.handlers[:] = [stream_handler, capture_handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.disabled = False
    try:
        yield records
    finally:
        logger.handlers[:] = original_handlers
        logger.setLevel(original_level)
        logger.propagate = original_propagate
        logger.disabled = original_disabled
        stream_handler.close()
        capture_handler.close()


def _load_uvicorn_for_real_server_test() -> Any:
    if importlib.util.find_spec("uvicorn") is None:
        is_ci = (
            os.environ.get("CI", "").casefold() in {"true", "1", "yes"}
            or os.environ.get("GITHUB_ACTIONS", "").casefold() == "true"
        )
        if os.name == "nt" and not is_ci:
            pytest.skip("Uvicorn is not installed in this Windows environment.")
        pytest.fail("Uvicorn is required for real HTTP access-log verification.")
    return importlib.import_module("uvicorn")


def _panel(**overrides: object) -> dict[str, object]:
    return {
        "number": 1,
        "narrative_intent": "The courier reaches for the brass key",
        "characters": ["courier"],
        "continuity_bindings": ["red scarf remains tied"],
        "action": "Reaches across the desk",
        "background": "A stone archive room",
        "composition": "The key remains in the foreground",
        "constraints": ["keep the scarf visible"],
        **overrides,
    }


def test_panel_contract_rejects_unknown_or_noncontiguous_input() -> None:
    with pytest.raises(ValidationError):
        validate_panels([{**_panel(), "role": "setup"}])
    with pytest.raises(ValidationError):
        validate_panels([{**_panel(), "number": True}])
    with pytest.raises(ValidationError):
        validate_panels([{**_panel(), "characters": ["courier", "courier"]}])
    with pytest.raises(ValidationError):
        validate_panels([{**_panel(), "characters": ["display name"]}])
    with pytest.raises(ValidationError):
        validate_panels([{**_panel(), "action": "# Storyboard\n..."}])
    with pytest.raises(ValidationError):
        validate_panels([{**_panel(), "background": "```json\n{}"}])


def test_localfile_generic_action_error_responses_remain_legacy_500(
    tmp_path: Path,
) -> None:
    repository = LocalFileRepository(tmp_path / "repo")
    repository.save(
        Project(
            id="generic-errors",
            title="Generic errors",
            pages=[
                Page(page_number=1, metadata={"page_design": {"purpose": "saved"}}),
                Page(
                    page_number=2,
                    state=PageState.QUALITY_CHECKED,
                    page_design={},
                    review={},
                    storyboard={},
                    prompt={},
                    image={},
                    quality={},
                    metadata={"approved_by": "saved-editor"},
                ),
                Page(
                    page_number=3,
                    state=PageState.GENERATED,
                    page_design={},
                    review={},
                    storyboard={},
                    prompt={},
                    image={},
                ),
            ],
        )
    )
    loader = ProjectLoader(repository)
    events = MemoryEventBus()
    llm_provider = LLMFactory.create("mock")
    engine = WorkflowEngine(
        state_machine=StateMachine(),
        event_bus=events,
        agents=primary_agents(ImageGeneratorFactory.create("mock"), None, llm_provider, PromptPipeline()),
        support_agents=support_agents(llm_provider, None),
    )
    coordinator = WorkflowCoordinator(
        ProjectWorkflowEngine(repository, events),
        ChapterWorkflowEngine(repository, events, PageNumberWorkflowScheduler()),
        engine,
        loader,
    )
    client = TestClient(
        build_workflow_app(
            workflow_engine=engine,
            workflow_coordinator=coordinator,
            project_loader=loader,
            repository=repository,
        ),
        raise_server_exceptions=False,
    )

    invalid_metadata = client.post(
        "/projects/generic-errors/pages/1/design", json={"metadata": {"unknown": "value"}}
    )
    conflicting_metadata = client.post(
        "/projects/generic-errors/pages/1/design",
        json={"metadata": {"page_design": {"purpose": "replacement"}}},
    )
    reserved_authority = client.post(
        "/projects/generic-errors/pages/1/storyboard",
        json={"metadata": {"_explicit_storyboard_input_authority": {"forged": True}}},
    )
    review_evidence_on_generic_approval = client.post(
        "/projects/generic-errors/pages/2/approve",
        json={"approvedBy": "editor", "metadata": {"review_evidence_id": "review:001"}},
    )
    invalid_quality_metadata = client.post(
        "/projects/generic-errors/pages/3/quality",
        json={"metadata": {"quality_scores": {"unknown": 8}}},
    )

    for response in (
        invalid_metadata,
        conflicting_metadata,
        reserved_authority,
        review_evidence_on_generic_approval,
        invalid_quality_metadata,
    ):
        assert response.status_code == 500
        assert response.json() == {
            "code": "internal_error",
            "message": "An internal error occurred.",
        }
    assert repository.load("generic-errors").page(1).state is PageState.DRAFT
    assert repository.load("generic-errors").page(2).state is PageState.QUALITY_CHECKED
    assert repository.load("generic-errors").page(3).state is PageState.GENERATED


def test_confirmation_missing_project_page_and_damaged_durability_responses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = LocalFileRepository(tmp_path / "repo")
    page_design = {"purpose": "Find the brass key", "featured_character": "courier"}
    review = {"checks": {"character": True}}
    repository.save(
        Project(
            id="demo",
            title="Demo",
            pages=[
                Page(
                    page_number=1,
                    state=PageState.REVIEWED,
                    page_design=page_design,
                    review=review,
                )
            ],
        )
    )
    repository.save(Project(id="damaged", title="Damaged", pages=[Page(page_number=1)]))
    repository._load_revisioned("damaged")
    repository._path("damaged").unlink()
    repository.save(Project(id="badmetadata", title="Bad metadata", pages=[Page(page_number=1)]))
    repository._load_revisioned("badmetadata")
    repository._revision_store._committed_path("badmetadata").write_text(
        "{broken", encoding="utf-8"
    )
    repository._path("corrupt").parent.mkdir(parents=True, exist_ok=True)
    repository._path("corrupt").write_bytes(b"not-json")
    loader = ProjectLoader(repository)
    events = MemoryEventBus()
    image_provider = ImageGeneratorFactory.create("mock")
    llm_provider = LLMFactory.create("mock")
    provider_calls: list[str] = []
    monkeypatch.setattr(
        image_provider, "generate", lambda *_args, **_kwargs: provider_calls.append("image")
    )
    monkeypatch.setattr(
        llm_provider, "generate", lambda *_args, **_kwargs: provider_calls.append("llm")
    )
    engine = WorkflowEngine(
        state_machine=StateMachine(),
        event_bus=events,
        agents=primary_agents(
            image_provider,
            None,
            llm_provider,
            PromptPipeline(),
        ),
        support_agents=support_agents(llm_provider, None),
    )
    coordinator = WorkflowCoordinator(
        ProjectWorkflowEngine(repository, events),
        ChapterWorkflowEngine(repository, events, PageNumberWorkflowScheduler()),
        engine,
        loader,
    )
    client = TestClient(
        build_workflow_app(
            workflow_engine=engine,
            workflow_coordinator=coordinator,
            project_loader=loader,
            repository=repository,
        ),
        follow_redirects=True,
    )
    origin = LOCAL_WEB_ORIGINS[0]
    payload = {
        "requestVersion": 1,
        "expectedSource": {
            "state": "Reviewed",
            "page_design": page_design,
            "review": review,
        },
        "confirmed": True,
        "panels": [_panel()],
    }

    def confirm(project_id: str, page_number: int = 1) -> Response:
        return client.post(
            f"/projects/{project_id}/pages/{page_number}/storyboard/confirm",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Origin": origin,
                "Referer": f"{origin}/projects/{project_id}/pages/{page_number}",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Dest": "empty",
            },
            json=payload,
        )

    from manga_director.workflow.durable_execution import LocalFileDurablePageStore

    source_before = repository._load_revisioned("demo")
    alias_headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": origin,
        "Referer": f"{origin}/projects/demo/pages/1",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
    }
    for alias_client in (client, TestClient(client.app, follow_redirects=False)):
        alias_response = alias_client.post(
            "/projects/demo/pages/1/storyboard/confirm/",
            headers=alias_headers,
            json=payload,
        )
        assert alias_response.status_code == 422
        assert alias_response.json()["code"] == "invalid_input"
        assert "location" not in alias_response.headers
    assert repository._load_revisioned("demo") == source_before
    assert repository.load("demo").page(1).state is PageState.REVIEWED
    assert events.published == []

    with monkeypatch.context() as patch:
        patch.setattr(
            LocalFileDurablePageStore,
            "load_revisioned",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                ValidationError("safe-path diagnostic secret")
            ),
        )
        load_failure = confirm("demo")
    assert load_failure.status_code == 503
    assert load_failure.json()["code"] == "activation_unavailable"
    assert "safe-path diagnostic secret" not in load_failure.text
    assert repository._load_revisioned("demo") == source_before
    assert repository.load("demo").page(1).state is PageState.REVIEWED

    with monkeypatch.context() as patch:
        patch.setattr(
            LocalFileDurablePageStore,
            "load_revisioned",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                ProjectNotFoundError("load diagnostic secret")
            ),
        )
        ambiguous_load_failure = confirm("demo")
    assert ambiguous_load_failure.status_code == 503
    assert ambiguous_load_failure.json()["code"] == "activation_unavailable"
    assert "load diagnostic secret" not in ambiguous_load_failure.text
    assert repository._load_revisioned("demo") == source_before

    prompt_agent = engine._agents[PageState.PROMPT_BUILT]
    with monkeypatch.context() as patch:
        patch.setattr(
            prompt_agent,
            "preflight",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                ProjectNotFoundError("late dependency diagnostic secret")
            ),
        )
        dependency_failure = confirm("demo")
    assert dependency_failure.status_code == 503
    assert dependency_failure.json()["code"] == "activation_unavailable"
    assert "late dependency diagnostic secret" not in dependency_failure.text
    assert repository._load_revisioned("demo") == source_before
    assert repository.load("demo").page(1).state is PageState.REVIEWED
    assert events.published == []
    assert provider_calls == []

    missing = confirm("missing")
    assert missing.status_code == 404
    assert missing.json()["code"] == "not_found"
    assert repository._path("missing").exists() is False
    assert repository._revision_store._committed_path("missing").exists() is False
    assert repository._revision_store._prepared_path("missing").exists() is False
    assert repository._revision_store._activation_path("missing").exists() is False

    if os.name == "nt":
        from manga_director.repositories._windows_safe_filesystem import WindowsSafeFilesystem

        with monkeypatch.context() as patch:
            patch.setattr(
                WindowsSafeFilesystem,
                "exists",
                lambda *_args, **_kwargs: (_ for _ in ()).throw(ValidationError("unsafe path")),
            )
            unsafe_metadata_path = confirm("unsafe")
    else:
        unsafe_metadata = repository._revision_store._committed_path("unsafe")
        original_stat = os.stat

        def fail_metadata_stat(path: Any, *args: Any, **kwargs: Any) -> os.stat_result:
            if path == unsafe_metadata.name and kwargs.get("dir_fd") is not None:
                raise PermissionError("metadata path is not readable")
            return original_stat(path, *args, **kwargs)

        with monkeypatch.context() as patch:
            patch.setattr(os, "stat", fail_metadata_stat)
            unsafe_metadata_path = confirm("unsafe")
    assert unsafe_metadata_path.status_code == 503
    assert unsafe_metadata_path.json()["code"] == "activation_unavailable"

    unknown_page = confirm("demo", 2)
    assert unknown_page.status_code == 404
    assert unknown_page.json()["code"] == "not_found"
    for damaged_project in ("damaged", "badmetadata", "corrupt"):
        unavailable = confirm(damaged_project)
        assert unavailable.status_code == 503
        assert unavailable.json()["code"] == "activation_unavailable"
        assert "not-json" not in unavailable.text
    assert repository._revision_store._committed_path("corrupt").exists() is False

    assert repository._load_revisioned("demo").fingerprint == source_before.fingerprint
    assert repository.load("demo").page(1).state is PageState.REVIEWED
    assert events.published == []
    assert provider_calls == []

    for project_id, error in (
        ("verify-validation", ValidationError("post-commit validation secret")),
        (
            "verify-missing",
            ProjectNotFoundError("post-commit missing secret"),
        ),
    ):
        repository.save(
            Project(
                id=project_id,
                title=project_id,
                pages=[Page(page_number=1, state=PageState.REVIEWED, page_design=page_design, review=review)],
            )
        )
        before_commit = repository._load_revisioned(project_id)
        with monkeypatch.context() as patch:
            patch.setattr(
                LocalFileDurablePageStore,
                "verify_committed",
                lambda *_args, _error=error, **_kwargs: (_ for _ in ()).throw(_error),
            )
            post_commit_failure = confirm(project_id)
        after_commit = repository._load_revisioned(project_id)
        assert post_commit_failure.status_code == 503
        assert post_commit_failure.json()["code"] == "activation_unavailable"
        assert str(error) not in post_commit_failure.text
        assert after_commit.revision == before_commit.revision + 1
        assert after_commit.fingerprint != before_commit.fingerprint
        assert after_commit.project.page(1).state is PageState.STORYBOARDED
        assert events.published == []
        assert provider_calls == []
    assert events.published == []
    assert provider_calls == []


@pytest.mark.skipif(os.name != "posix", reason="POSIX directory descriptor behavior")
def test_missing_aggregate_with_replaced_durability_root_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from manga_director.repositories.local_file_durability import (
        LocalFileDurabilityError,
        LocalFileRevisionStore,
    )

    repository = LocalFileRepository(tmp_path / "repo")
    repository.save(Project(id="damaged", title="Damaged", pages=[Page(page_number=1)]))
    repository._load_revisioned("damaged")
    aggregate_path = repository._path("damaged")
    aggregate_path.unlink()

    durability_directory = repository._root / "_durability"
    moved_directory = repository._root / "_durability-original"
    empty_directory = tmp_path / "empty-durability"
    empty_directory.mkdir()
    original_read = LocalFileRevisionStore._read_aggregate

    def replace_durability_directory(path: Path) -> bytes:
        if path == aggregate_path:
            durability_directory.rename(moved_directory)
            durability_directory.symlink_to(empty_directory, target_is_directory=True)
            raise LocalFileDurabilityError("authoritative_aggregate_missing")
        return original_read(path)

    monkeypatch.setattr(
        LocalFileRevisionStore,
        "_read_aggregate",
        staticmethod(replace_durability_directory),
    )
    with pytest.raises(LocalFileDurabilityError) as raised:
        repository._load_revisioned("damaged")
    assert type(raised.value) is LocalFileDurabilityError


def test_confirmation_provenance_binds_exact_panels_and_reviewed_artifacts() -> None:
    source = {
        "state": "Reviewed",
        "page_design": {"purpose": "Recover the brass key", "featured_character": "courier"},
        "review": {"checks": {"story_beat": True}},
    }
    panels = [_panel()]
    authority = create_authority("demo", 1, 7, "f" * 64, source, panels)
    from manga_director.production.explicit_storyboard_input import confirmation_record

    storyboard = {"panels": panels, "confirmation": confirmation_record(authority)}
    validate_confirmation(storyboard, "demo", 1, {"Designed": source["page_design"], "Reviewed": source["review"]})
    changed = {**storyboard, "panels": [{**_panel(), "action": "Opens the door instead"}]}
    with pytest.raises(ValidationError):
        validate_confirmation(changed, "demo", 1, {"Designed": source["page_design"], "Reviewed": source["review"]})
    with pytest.raises(ValidationError):
        validate_confirmation(storyboard, "demo", 1, {"Designed": source["page_design"], "Reviewed": {"checks": {}}})


@pytest.mark.parametrize("missing_artifact", ("Designed", "Reviewed"))
def test_confirmation_provenance_rejects_missing_source_artifacts(
    missing_artifact: str,
) -> None:
    source = {
        "state": "Reviewed",
        "page_design": {"purpose": "Recover the brass key", "featured_character": "courier"},
        "review": {},
    }
    panels = [_panel()]
    authority = create_authority("demo", 1, 7, "f" * 64, source, panels)
    from manga_director.production.explicit_storyboard_input import confirmation_record

    storyboard = {"panels": panels, "confirmation": confirmation_record(authority)}
    artifacts = {"Designed": source["page_design"], "Reviewed": source["review"]}
    del artifacts[missing_artifact]

    with pytest.raises(ValidationError, match="source artifacts are missing or malformed"):
        validate_confirmation(storyboard, "demo", 1, artifacts)


def test_prior_prompt_pipeline_ignores_additive_storyboard_confirmation_key() -> None:
    page_design = {"purpose": "Recover the brass key", "featured_character": "courier"}
    storyboard = {
        "panels": [_panel()],
        "confirmation": {"schema_id": "manga_director.explicit_storyboard_input"},
    }
    prior_page = Page(
        page_number=1,
        state=PageState.STORYBOARDED,
        page_design=page_design,
        storyboard=storyboard,
    )
    loaded_page = Page.model_validate(prior_page.model_dump())
    assert loaded_page.storyboard == storyboard
    context = WorkflowContext(
        page={"project_id": "demo", "page_id": "legacy-page"},
        state=loaded_page.state,
        artifacts={"Designed": loaded_page.page_design, "Storyboarded": loaded_page.storyboard},
    )

    prompt = PromptPipeline().run(context).prompt

    assert "The courier reaches for the brass key" in prompt
    assert "manga_director.explicit_storyboard_input" not in prompt


@pytest.mark.parametrize(
    "failure_case",
    ("oversized_structured_prompt", "missing_character", "incompatible_template"),
)
def test_prompt_preflight_rejects_invalid_storyboard_without_side_effects(
    failure_case: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from manga_director.workflow.durable_execution import LocalFileDurablePageStore

    purpose = "Recover the brass key"
    page_design = {"purpose": purpose, "featured_character": "courier"}
    panel = _panel()
    pipeline = PromptPipeline()
    if failure_case == "oversized_structured_prompt":
        page_design["purpose"] = "p" * 4000
        panel = _panel(
            narrative_intent="n" * 4000,
            action="a" * 4000,
        )
    elif failure_case == "missing_character":
        page_design = {"purpose": purpose}
    else:
        template_loader = PromptTemplateLoader()
        template_loader.register(
            PromptTemplate(
                name="incompatible.md",
                content="{unsupported_section}",
                source="test",
                content_hash="test-template-hash",
            )
        )
        pipeline = PromptPipeline(
            template_loader=template_loader,
            default_template="incompatible.md",
        )

    repository = LocalFileRepository(tmp_path / "repo")
    review = {"checks": {"character": True}}
    repository.save(
        Project(
            id="demo",
            title="Demo",
            pages=[
                Page(
                    page_number=1,
                    state=PageState.REVIEWED,
                    page_design=page_design,
                    review=review,
                )
            ],
        )
    )
    project_loader = ProjectLoader(repository)
    events = MemoryEventBus()
    image_provider = ImageGeneratorFactory.create("mock")
    llm_provider = LLMFactory.create("mock")
    provider_calls: list[str] = []
    original_image_generate = image_provider.generate
    original_llm_generate = llm_provider.generate

    def count_image_call(prompt: str) -> ImageResult:
        provider_calls.append("image")
        return original_image_generate(prompt)

    def count_llm_call(request: PromptRequest) -> LLMResult:
        provider_calls.append("llm")
        return original_llm_generate(request)

    monkeypatch.setattr(image_provider, "generate", count_image_call)
    monkeypatch.setattr(llm_provider, "generate", count_llm_call)
    engine = WorkflowEngine(
        state_machine=StateMachine(),
        event_bus=events,
        agents=primary_agents(image_provider, None, llm_provider, pipeline),
        support_agents=support_agents(llm_provider, None),
    )
    coordinator = WorkflowCoordinator(
        ProjectWorkflowEngine(repository, events),
        ChapterWorkflowEngine(repository, events, PageNumberWorkflowScheduler()),
        engine,
        project_loader,
    )
    client = TestClient(
        build_workflow_app(
            workflow_engine=engine,
            workflow_coordinator=coordinator,
            project_loader=project_loader,
            repository=repository,
        )
    )
    origin = LOCAL_WEB_ORIGINS[0]
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": origin,
        "Referer": f"{origin}/projects/demo/pages/1",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
    }
    payload = {
        "requestVersion": 1,
        "expectedSource": {
            "state": "Reviewed",
            "page_design": page_design,
            "review": review,
        },
        "confirmed": True,
        "panels": [panel],
    }
    before = repository._load_revisioned("demo")
    save_calls: list[bool] = []
    original_save = repository.save

    def count_repository_save(project: Project) -> None:
        save_calls.append(True)
        original_save(project)

    monkeypatch.setattr(repository, "save", count_repository_save)
    conditional_commits: list[bool] = []
    original_conditional_commit = LocalFileDurablePageStore.conditional_commit

    def count_conditional_commit(self: Any, *args: Any, **kwargs: Any) -> Any:
        conditional_commits.append(True)
        return original_conditional_commit(self, *args, **kwargs)

    monkeypatch.setattr(
        LocalFileDurablePageStore,
        "conditional_commit",
        count_conditional_commit,
    )

    response = client.post(
        "/projects/demo/pages/1/storyboard/confirm",
        headers=headers,
        json=payload,
    )

    after = repository._load_revisioned("demo")
    assert response.status_code == 422, failure_case
    assert response.json() == {
        "code": "invalid_input",
        "message": "Request validation failed.",
    }
    assert after.revision == before.revision
    assert after.fingerprint == before.fingerprint
    assert after.project.page(1).state is PageState.REVIEWED
    assert after.project.page(1).storyboard == before.project.page(1).storyboard
    assert save_calls == []
    assert conditional_commits == []
    assert events.published == []
    assert provider_calls == []


def test_localfile_confirm_reloads_exact_storyboard_then_prompt_validates_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    capfd: pytest.CaptureFixture[str],
) -> None:
    caplog.set_level(logging.DEBUG)
    repository = LocalFileRepository(tmp_path / "repo")
    page_design = {
        "page_type": "manga", "purpose": "Recover the brass key", "reader_emotion": "tension",
        "featured_character": "courier", "big_moment": "The key is within reach", "hook": "A door opens",
        "panel_count": 1, "panel_roles": ["discovery"],
    }
    review = {"checks": {"character": True}, "improvements": []}
    repository.save(Project(id="demo", title="Demo", pages=[Page(
        page_number=1, state=PageState.REVIEWED, page_design=page_design, review=review,
        metadata={"trace_id": "v7-17-confirmation-observer-trace"},
    )]))
    loader = ProjectLoader(repository)
    events = MemoryEventBus()
    observer = WorkflowObserver()
    engine = WorkflowEngine(
        state_machine=StateMachine(), event_bus=events,
        agents=primary_agents(ImageGeneratorFactory.create("mock"), None, LLMFactory.create("mock"), PromptPipeline()),
        support_agents=support_agents(LLMFactory.create("mock"), None),
        observer=observer,
    )
    coordinator = WorkflowCoordinator(
        ProjectWorkflowEngine(repository, events),
        ChapterWorkflowEngine(repository, events, PageNumberWorkflowScheduler()),
        engine, loader,
    )
    from manga_director.application import workflow as application_module

    application_results: list[WorkflowResult] = []
    route_name = "_route_localfile_storyboard_confirmation"
    confirm_private: Callable[..., WorkflowResult] = getattr(application_module, route_name)

    def capture_confirmation_result(*args: Any, **kwargs: Any) -> WorkflowResult:
        result = confirm_private(*args, **kwargs)
        application_results.append(result)
        return result

    monkeypatch.setattr(
        application_module,
        "_route_localfile_storyboard_confirmation",
        capture_confirmation_result,
    )
    client = TestClient(
        build_workflow_app(
            workflow_engine=engine,
            workflow_coordinator=coordinator,
            project_loader=loader,
            repository=repository,
        ),
        raise_server_exceptions=False,
    )
    origin = LOCAL_WEB_ORIGINS[0]
    headers = {
        "Accept": "application/json", "Content-Type": "application/json", "Origin": origin,
        "Referer": f"{origin}/projects/demo/pages/1", "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors", "Sec-Fetch-Dest": "empty",
    }
    credential_marker = "Bearer v7-17-private-credential-marker"
    headers["Authorization"] = credential_marker
    payload = {
        "requestVersion": 1,
        "expectedSource": {"state": "Reviewed", "page_design": page_design, "review": review},
        "confirmed": True,
        "panels": [_panel()],
    }
    raw_request_body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    source_snapshot = repository._load_revisioned("demo")
    expected_source = payload["expectedSource"]
    assert isinstance(expected_source, dict)
    stale = {
        **payload,
        "expectedSource": {**expected_source, "page_design": {"purpose": "changed"}},
    }
    stale_response = client.post("/projects/demo/pages/1/storyboard/confirm", headers=headers, json=stale)
    _assert_sanitized_confirmation_conflict(stale_response)
    assert repository.load("demo").page(1).state is PageState.REVIEWED
    encoded_route = client.post(
        "/projects/%64emo/pages/1/storyboard/confirm", headers=headers, json=payload
    )
    assert encoded_route.status_code == 422
    assert encoded_route.json()["code"] == "invalid_input"
    assert repository.load("demo").page(1).state is PageState.REVIEWED
    first_inside_commit = Event()
    release_first_commit = Event()
    competing_fence_observed = Event()
    commit_guard = Lock()
    first_commit = True
    original_commit = DurableWorkflowExecutionCoordinator._commit_and_publish

    def hold_first_commit(
        self: DurableWorkflowExecutionCoordinator, *args: Any, **kwargs: Any
    ) -> Any:
        nonlocal first_commit
        with commit_guard:
            should_hold = first_commit
            first_commit = False
        if should_hold:
            first_inside_commit.set()
            assert release_first_commit.wait(timeout=10)
        return original_commit(self, *args, **kwargs)

    original_fence_factory = local_page_execution_fence

    def observed_fence_factory(
        project_id: str,
        page_id: str,
        *,
        timeout_ms: int | None = None,
    ) -> PageExecutionFencePort:
        if timeout_ms is None:
            fence = original_fence_factory(project_id, page_id)
        else:
            fence = original_fence_factory(project_id, page_id, timeout_ms=timeout_ms)

        class ObservedFence:
            def acquire(self) -> None:
                try:
                    fence.acquire()
                except PageExecutionFenceError as error:
                    if str(error) == "page_execution_fence_contended":
                        competing_fence_observed.set()
                    raise

            def release(self) -> None:
                fence.release()

        return ObservedFence()

    original_coordinator_init = DurableWorkflowExecutionCoordinator.__init__

    def init_with_observed_fence(
        self: DurableWorkflowExecutionCoordinator,
        engine: WorkflowEngine,
        page_store: DurablePageStorePort,
        *,
        fence_factory: Callable[[str, str], PageExecutionFencePort] | None = None,
        logical_output_asset_quality_gate: LogicalOutputAssetQualityGatePort | None = None,
    ) -> None:
        original_coordinator_init(
            self,
            engine,
            page_store,
            fence_factory=observed_fence_factory,
            logical_output_asset_quality_gate=logical_output_asset_quality_gate,
        )

    monkeypatch.setattr(
        DurableWorkflowExecutionCoordinator, "_commit_and_publish", hold_first_commit
    )
    monkeypatch.setattr(
        DurableWorkflowExecutionCoordinator, "__init__", init_with_observed_fence
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(
            client.post,
            "/projects/demo/pages/1/storyboard/confirm",
            headers=headers,
            content=raw_request_body,
        )
        assert first_inside_commit.wait(timeout=5)
        second = pool.submit(
            client.post,
            "/projects/demo/pages/1/storyboard/confirm",
            headers=headers,
            content=raw_request_body,
        )
        try:
            assert competing_fence_observed.wait(timeout=5)
            # Hold the winner beyond the old one-second Windows mutex timeout.
            sleep(1.1)
        finally:
            release_first_commit.set()
        duplicate_responses = [first.result(timeout=10), second.result(timeout=10)]
    confirmed = next(response for response in duplicate_responses if response.status_code == 200)
    conflict = next(response for response in duplicate_responses if response.status_code != 200)
    assert confirmed.status_code == 200
    assert confirmed.json() == {"status": "storyboarded"}
    assert len(application_results) == 1
    assert len(events.published) == 1
    assert repository._load_revisioned("demo").revision == source_snapshot.revision + 1
    page_detail = client.get("/projects/demo/pages/1")
    assert page_detail.status_code == 200
    published = json.dumps(
        [event.model_dump(mode="json") for event in events.published], sort_keys=True
    )
    result_json = application_results[0].model_dump_json()
    observer_json = json.dumps(
        {
            "timeline": observer.timeline("v7-17-confirmation-observer-trace"),
            "metrics": observer.metrics.snapshot(),
        },
        sort_keys=True,
    )
    state_json = repository.load("demo").model_dump_json()
    output_values = (
        confirmed.json(),
        page_detail.json(),
        [event.model_dump(mode="json") for event in events.published],
        application_results[0].model_dump(mode="json"),
        observer.timeline("v7-17-confirmation-observer-trace"),
        observer.metrics.snapshot(),
        repository.load("demo").model_dump(mode="json"),
        [record.__dict__ for record in caplog.records],
        conflict.json(),
    )
    for output_value in output_values:
        _assert_confirmation_output_has_no_internal_values(
            output_value,
            credential_marker,
            source_snapshot.fingerprint,
            raw_request_body.decode("utf-8"),
            "_explicit_storyboard_input_authority",
            "_ExplicitStoryboardInputAuthority",
        )
    exposed_channels = "\n".join(
        (
            confirmed.text,
            conflict.text,
            page_detail.text,
            published,
            result_json,
            observer_json,
            state_json,
            caplog.text,
        )
    )
    assert raw_request_body.decode("utf-8") not in exposed_channels
    assert credential_marker not in exposed_channels
    assert "_explicit_storyboard_input_authority" not in exposed_channels
    assert "_ExplicitStoryboardInputAuthority" not in exposed_channels
    assert source_snapshot.fingerprint not in exposed_channels
    assert "revision" not in published.lower()
    assert "fingerprint" not in published.lower()
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "confirmation_conflict"
    _assert_sanitized_confirmation_conflict(conflict)
    saved = repository.load("demo").page(1)
    assert isinstance(saved.storyboard, dict)
    assert isinstance(saved.storyboard.get("confirmation"), dict)
    assert saved.storyboard == {"panels": [_panel()], "confirmation": saved.storyboard["confirmation"]}
    assert set(saved.storyboard["confirmation"]) == {
        "schema_id", "schema_version", "source_project_id", "source_page_number", "source_sha256",
        "source_page_design_sha256", "source_review_sha256", "panel_input_sha256", "user_confirmed",
    }
    assert "_explicit_storyboard_input_authority" not in saved.metadata
    assert saved.storyboard["confirmation"]["user_confirmed"] is True
    prompted = client.post("/projects/demo/pages/1/prompt", headers=headers, json={})
    assert prompted.status_code == 200
    assert prompted.json()["state"] == "PromptBuilt"
    replay = client.post(
        "/projects/demo/pages/1/storyboard/confirm", headers=headers, content=raw_request_body
    )
    _assert_sanitized_confirmation_conflict(replay)
    _assert_confirmation_output_has_no_internal_values(
        replay.json(),
        credential_marker,
        source_snapshot.fingerprint,
        raw_request_body.decode("utf-8"),
        "_explicit_storyboard_input_authority",
        "_ExplicitStoryboardInputAuthority",
    )
    assert source_snapshot.fingerprint not in replay.text
    assert raw_request_body.decode("utf-8") not in replay.text
    state_before_forged = repository._load_revisioned("demo")
    events_before_forged = tuple(events.published)
    forged = client.post(
        "/projects/demo/pages/1/storyboard",
        headers=headers,
        json={"metadata": {"_explicit_storyboard_input_authority": {"forged": True}}},
    )
    assert forged.status_code == 500
    assert forged.json() == {
        "code": "internal_error",
        "message": "An internal error occurred.",
    }
    state_after_forged = repository._load_revisioned("demo")
    assert state_after_forged.revision == state_before_forged.revision
    assert state_after_forged.fingerprint == state_before_forged.fingerprint
    assert state_after_forged.project == state_before_forged.project
    assert tuple(events.published) == events_before_forged
    captured_process_streams = capfd.readouterr()
    # TestClient is in-process; this does not inspect an external server's access logs.
    _assert_captured_streams_are_clean(
        (captured_process_streams.out, captured_process_streams.err),
        credential_marker,
        source_snapshot.fingerprint,
        raw_request_body.decode("utf-8"),
        "_explicit_storyboard_input_authority",
        "_ExplicitStoryboardInputAuthority",
    )


def test_fenced_coordinator_rejects_changed_confirmation_before_replacement_prompt_agent(
    tmp_path: Path,
) -> None:
    repository = LocalFileRepository(tmp_path / "repo")
    page_design = {"purpose": "Recover the brass key", "featured_character": "courier"}
    review = {"checks": {"character": True}}
    repository.save(Project(id="demo", title="Demo", pages=[Page(
        page_number=1, state=PageState.REVIEWED, page_design=page_design, review=review
    )]))
    loader = ProjectLoader(repository)
    events = MemoryEventBus()
    engine = WorkflowEngine(
        state_machine=StateMachine(), event_bus=events,
        agents=primary_agents(ImageGeneratorFactory.create("mock"), None, LLMFactory.create("mock"), PromptPipeline()),
        support_agents=support_agents(LLMFactory.create("mock"), None),
    )
    coordinator = WorkflowCoordinator(
        ProjectWorkflowEngine(repository, events),
        ChapterWorkflowEngine(repository, events, PageNumberWorkflowScheduler()),
        engine, loader,
    )
    client = TestClient(build_workflow_app(
        workflow_engine=engine, workflow_coordinator=coordinator,
        project_loader=loader, repository=repository,
    ))
    origin = LOCAL_WEB_ORIGINS[0]
    headers = {
        "Accept": "application/json", "Content-Type": "application/json", "Origin": origin,
        "Referer": f"{origin}/projects/demo/pages/1", "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors", "Sec-Fetch-Dest": "empty",
    }
    panel = _panel()
    payload = {
        "requestVersion": 1,
        "expectedSource": {"state": "Reviewed", "page_design": page_design, "review": review},
        "confirmed": True,
        "panels": [panel],
    }
    response = client.post("/projects/demo/pages/1/storyboard/confirm", headers=headers, json=payload)
    assert response.status_code == 200

    class _ReplacementPromptAgent:
        calls = 0

        def execute(self, _context: WorkflowContext) -> AgentResult:
            self.calls += 1
            raise AssertionError("invalid provenance must stop before a replacement agent")

    replacement = _ReplacementPromptAgent()
    previous = engine._agents[PageState.PROMPT_BUILT]
    engine._agents[PageState.PROMPT_BUILT] = replacement
    snapshot = repository._load_revisioned("demo")
    page_with_forged_metadata = snapshot.project.page(1).model_copy(
        update={
            "metadata": {
                "nested": {"_explicit_storyboard_input_authority": {"forged": True}}
            }
        },
        deep=True,
    )
    repository._conditional_commit(
        snapshot, snapshot.project.replace_page(page_with_forged_metadata)
    )
    before_reserved_metadata_rejection = repository._load_revisioned("demo")
    events_before_reserved_metadata_rejection = tuple(events.published)
    rejection_client = TestClient(client.app, raise_server_exceptions=False)
    reserved_metadata_rejected = rejection_client.post(
        "/projects/demo/pages/1/prompt", headers=headers, json={}
    )
    after_reserved_metadata_rejection = repository._load_revisioned("demo")
    assert reserved_metadata_rejected.status_code == 500
    assert reserved_metadata_rejected.json() == {
        "code": "internal_error",
        "message": "An internal error occurred.",
    }
    assert after_reserved_metadata_rejection.revision == before_reserved_metadata_rejection.revision
    assert after_reserved_metadata_rejection.fingerprint == before_reserved_metadata_rejection.fingerprint
    assert after_reserved_metadata_rejection.project == before_reserved_metadata_rejection.project
    assert tuple(events.published) == events_before_reserved_metadata_rejection
    assert replacement.calls == 0

    clean_snapshot = repository._load_revisioned("demo")
    clean_page = clean_snapshot.project.page(1).model_copy(update={"metadata": {}}, deep=True)
    repository._conditional_commit(clean_snapshot, clean_snapshot.project.replace_page(clean_page))
    snapshot = repository._load_revisioned("demo")
    page = snapshot.project.page(1)
    assert isinstance(page.storyboard, dict)
    confirmation = page.storyboard.get("confirmation")
    assert isinstance(confirmation, dict)
    storyboard = {
        **page.storyboard,
        "confirmation": {
            **confirmation,
            "panel_input_sha256": "0" * 64,
        },
    }
    corrupted_page = page.model_copy(update={"storyboard": storyboard}, deep=True)
    repository._conditional_commit(snapshot, snapshot.project.replace_page(corrupted_page))
    before_prompt = repository._load_revisioned("demo")
    assert before_prompt.revision == snapshot.revision + 1
    rejected = client.post("/projects/demo/pages/1/prompt", headers=headers, json={})
    after_prompt = repository._load_revisioned("demo")
    assert rejected.status_code == 422
    assert rejected.json()["code"] == "invalid_input"
    assert replacement.calls == 0
    assert after_prompt.revision == before_prompt.revision
    assert after_prompt.project.page(1).state is PageState.STORYBOARDED
    engine._agents[PageState.PROMPT_BUILT] = previous


@pytest.mark.parametrize("changed_source", ("page_design", "review"))
def test_prompt_rejects_source_changed_after_storyboard_confirmation_without_side_effects(
    tmp_path: Path, changed_source: str
) -> None:
    repository = LocalFileRepository(tmp_path / "repo")
    page_design = {"purpose": "Recover the brass key", "featured_character": "courier"}
    review = {"checks": {"character": True}}
    repository.save(
        Project(
            id="demo",
            title="Demo",
            pages=[Page(page_number=1, state=PageState.REVIEWED, page_design=page_design, review=review)],
        )
    )
    loader = ProjectLoader(repository)
    events = MemoryEventBus()
    llm_provider = LLMFactory.create("mock")
    engine = WorkflowEngine(
        state_machine=StateMachine(),
        event_bus=events,
        agents=primary_agents(
            ImageGeneratorFactory.create("mock"), None, llm_provider, PromptPipeline()
        ),
        support_agents=support_agents(llm_provider, None),
    )
    coordinator = WorkflowCoordinator(
        ProjectWorkflowEngine(repository, events),
        ChapterWorkflowEngine(repository, events, PageNumberWorkflowScheduler()),
        engine,
        loader,
    )
    client = TestClient(
        build_workflow_app(
            workflow_engine=engine,
            workflow_coordinator=coordinator,
            project_loader=loader,
            repository=repository,
        )
    )
    origin = LOCAL_WEB_ORIGINS[0]
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": origin,
        "Referer": f"{origin}/projects/demo/pages/1",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
    }
    confirmed = client.post(
        "/projects/demo/pages/1/storyboard/confirm",
        headers=headers,
        json={
            "requestVersion": 1,
            "expectedSource": {"state": "Reviewed", "page_design": page_design, "review": review},
            "confirmed": True,
            "panels": [_panel()],
        },
    )
    assert confirmed.status_code == 200

    snapshot = repository._load_revisioned("demo")
    page = snapshot.project.page(1)
    update = (
        {"page_design": {**page_design, "purpose": "Find the hidden ledger"}}
        if changed_source == "page_design"
        else {"review": {"checks": {"character": True, "continuity": True}}}
    )
    repository._conditional_commit(
        snapshot, snapshot.project.replace_page(page.model_copy(update=update, deep=True))
    )

    class _PromptAgentSpy:
        calls = 0

        def execute(self, _context: WorkflowContext) -> AgentResult:
            self.calls += 1
            raise AssertionError("stale confirmation must stop before PromptAgent")

    prompt_agent = _PromptAgentSpy()
    engine._agents[PageState.PROMPT_BUILT] = prompt_agent
    before_rejection = repository._load_revisioned("demo")
    events_before_rejection = tuple(events.published)

    rejected = client.post("/projects/demo/pages/1/prompt", headers=headers, json={})

    after_rejection = repository._load_revisioned("demo")
    assert rejected.status_code == 422
    assert rejected.json()["code"] == "invalid_input"
    assert prompt_agent.calls == 0
    assert after_rejection == before_rejection
    assert after_rejection.project.page(1).state is PageState.STORYBOARDED
    assert tuple(events.published) == events_before_rejection


def test_confirmation_failure_paths_do_not_expose_capability_or_exception_details(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    capfd: pytest.CaptureFixture[str],
) -> None:
    caplog.set_level(logging.DEBUG)
    from manga_director.workflow.durable_execution import LocalFileDurablePageStore

    repository = LocalFileRepository(tmp_path / "repo")
    page_design = {"purpose": "Recover the brass key", "featured_character": "courier"}
    review = {"checks": {"character": True}}
    repository.save(Project(id="demo", title="Demo", pages=[Page(
        page_number=1, state=PageState.REVIEWED, page_design=page_design, review=review,
        metadata={"trace_id": "v7-17-failure-observer-trace"},
    )]))
    loader = ProjectLoader(repository)
    events = MemoryEventBus()
    observer = WorkflowObserver()
    engine = WorkflowEngine(
        state_machine=StateMachine(), event_bus=events,
        agents=primary_agents(ImageGeneratorFactory.create("mock"), None, LLMFactory.create("mock"), PromptPipeline()),
        support_agents=support_agents(LLMFactory.create("mock"), None),
        observer=observer,
    )
    coordinator = WorkflowCoordinator(
        ProjectWorkflowEngine(repository, events),
        ChapterWorkflowEngine(repository, events, PageNumberWorkflowScheduler()),
        engine, loader,
    )
    client = TestClient(build_workflow_app(
        workflow_engine=engine, workflow_coordinator=coordinator,
        project_loader=loader, repository=repository,
    ), raise_server_exceptions=False)
    origin = LOCAL_WEB_ORIGINS[0]
    headers = {
        "Accept": "application/json", "Content-Type": "application/json", "Origin": origin,
        "Referer": f"{origin}/projects/demo/pages/1", "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors", "Sec-Fetch-Dest": "empty",
    }
    credential_marker = "Bearer v7-17-private-failure-credential"
    headers["Authorization"] = credential_marker
    payload = {
        "requestVersion": 1,
        "expectedSource": {"state": "Reviewed", "page_design": page_design, "review": review},
        "confirmed": True,
        "panels": [_panel()],
    }
    raw_request_body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    source_fingerprint_snapshot = repository._load_revisioned("demo")
    source_fingerprint = source_fingerprint_snapshot.fingerprint
    secret = "private-confirmation-capability-secret"
    raw_request_marker = "private-confirmation-raw-envelope-marker"
    raw_invalid_request_body = json.dumps(
        {**payload, "requestEnvelopeMarker": raw_request_marker},
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    def captured_tracebacks() -> str:
        return "\n".join(
            "".join(traceback.format_exception(*record.exc_info))
            for record in caplog.records
            if record.exc_info is not None
        )

    conditional_commit_calls: list[bool] = []

    def fail_with_secret(*_args: Any, **_kwargs: Any) -> None:
        conditional_commit_calls.append(True)
        raise RuntimeError(secret)

    monkeypatch.setattr(LocalFileDurablePageStore, "conditional_commit", fail_with_secret)
    response = client.post(
        "/projects/demo/pages/1/storyboard/confirm", headers=headers, content=raw_request_body
    )
    assert response.status_code == 503
    assert conditional_commit_calls == [True]
    assert response.json()["code"] == "activation_unavailable"
    assert secret not in response.text
    assert "_ExplicitStoryboardInputAuthority" not in caplog.text
    assert secret not in caplog.text
    assert secret not in json.dumps(
        {"timeline": observer.timeline("v7-17-failure-observer-trace"), "metrics": observer.metrics.snapshot()},
        sort_keys=True,
    )
    raw_envelope_response = client.post(
        "/projects/demo/pages/1/storyboard/confirm",
        headers=headers,
        content=raw_invalid_request_body,
    )
    assert raw_envelope_response.status_code == 422
    assert conditional_commit_calls == [True]
    assert raw_request_marker not in raw_envelope_response.text
    assert repository._load_revisioned("demo").revision == source_fingerprint_snapshot.revision
    failed_page_detail = client.get("/projects/demo/pages/1")
    assert failed_page_detail.status_code == 200
    failed_output_values = (
        response.json(),
        raw_envelope_response.json(),
        failed_page_detail.json(),
        list(events.published),
        observer.timeline("v7-17-failure-observer-trace"),
        observer.metrics.snapshot(),
        repository.load("demo").model_dump(mode="json"),
        [record.__dict__ for record in caplog.records],
    )
    for output_value in failed_output_values:
        _assert_confirmation_output_has_no_internal_values(
            output_value,
            credential_marker,
            secret,
            raw_request_marker,
            raw_request_body.decode("utf-8"),
            raw_invalid_request_body.decode("utf-8"),
            source_fingerprint,
            "_explicit_storyboard_input_authority",
            "_ExplicitStoryboardInputAuthority",
        )
    _assert_confirmation_output_has_no_internal_values(
        captured_tracebacks(), credential_marker, secret, raw_request_marker,
        raw_request_body.decode("utf-8"), raw_invalid_request_body.decode("utf-8"), source_fingerprint
    )
    assert credential_marker not in caplog.text
    assert raw_request_marker not in caplog.text
    assert secret not in caplog.text
    assert repository.load("demo").page(1).state is PageState.REVIEWED

    monkeypatch.undo()
    publish_attempt_count = 0
    publish_attempts: list[Any] = []

    def capture_and_fail_publish(published_events: list[Any]) -> None:
        nonlocal publish_attempt_count
        publish_attempt_count += 1
        publish_attempts.extend(published_events)
        raise RuntimeError(secret)

    monkeypatch.setattr(events, "publish", capture_and_fail_publish)
    publish_response = client.post(
        "/projects/demo/pages/1/storyboard/confirm", headers=headers, content=raw_request_body
    )
    assert publish_response.status_code == 503
    assert publish_response.json()["code"] == "activation_unavailable"
    assert secret not in publish_response.text
    assert secret not in caplog.text
    assert events.published == []
    assert publish_attempt_count == 1
    assert len(publish_attempts) == 1
    serialized_after_publish_failure = repository.load("demo").model_dump_json()
    publish_page_detail = client.get("/projects/demo/pages/1")
    assert publish_page_detail.status_code == 200
    for output_value in (
        publish_response.json(),
        publish_page_detail.json(),
        list(events.published),
        [event.model_dump(mode="json") for event in publish_attempts],
        observer.timeline("v7-17-failure-observer-trace"),
        observer.metrics.snapshot(),
        repository.load("demo").model_dump(mode="json"),
        [record.__dict__ for record in caplog.records],
    ):
        _assert_confirmation_output_has_no_internal_values(
            output_value,
            credential_marker,
            secret,
            raw_request_body.decode("utf-8"),
            source_fingerprint,
            "_explicit_storyboard_input_authority",
            "_ExplicitStoryboardInputAuthority",
        )
    _assert_confirmation_output_has_no_internal_values(
        captured_tracebacks(), credential_marker, secret, raw_request_body.decode("utf-8"), source_fingerprint
    )
    assert credential_marker not in caplog.text
    assert secret not in publish_response.text + caplog.text + serialized_after_publish_failure
    publish_observer_json = json.dumps(
        {"timeline": observer.timeline("v7-17-failure-observer-trace"), "metrics": observer.metrics.snapshot()},
        sort_keys=True,
    )
    assert secret not in publish_observer_json
    assert source_fingerprint not in publish_observer_json
    assert repository.load("demo").page(1).state is PageState.STORYBOARDED

    verification_project_id = "verify-demo"
    repository.save(Project(id=verification_project_id, title="Verification", pages=[Page(
        page_number=1,
        state=PageState.REVIEWED,
        page_design=page_design,
        review=review,
        metadata={"trace_id": "v7-17-verification-observer-trace"},
    )]))
    verification_payload = {
        **payload,
        "expectedSource": {"state": "Reviewed", "page_design": page_design, "review": review},
    }
    verification_headers = {
        **headers,
        "Referer": f"{origin}/projects/{verification_project_id}/pages/1",
    }
    verification_request_body = json.dumps(
        verification_payload, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    verification_fingerprint = repository._load_revisioned(verification_project_id).fingerprint
    verification_calls = []
    publish_calls = []
    original_publish = events.publish

    def fail_verification(*_args: Any, **_kwargs: Any) -> None:
        verification_calls.append(True)
        raise RuntimeError(secret)

    def observe_publish(*args: Any, **kwargs: Any) -> Any:
        publish_calls.append(True)
        return original_publish(*args, **kwargs)

    monkeypatch.setattr(LocalFileDurablePageStore, "verify_committed", fail_verification)
    monkeypatch.setattr(events, "publish", observe_publish)
    verification_response = client.post(
        f"/projects/{verification_project_id}/pages/1/storyboard/confirm",
        headers=verification_headers,
        content=verification_request_body,
    )
    assert verification_response.status_code == 503
    assert verification_response.json()["code"] == "activation_unavailable"
    assert verification_calls == [True]
    assert publish_calls == []
    assert secret not in verification_response.text
    assert secret not in caplog.text
    verification_observer_json = json.dumps(
        {
            "timeline": observer.timeline("v7-17-verification-observer-trace"),
            "metrics": observer.metrics.snapshot(),
        },
        sort_keys=True,
    )
    assert secret not in verification_observer_json
    verification_state = repository.load(verification_project_id)
    verification_serialized = verification_state.model_dump_json()
    verification_page_detail = client.get(f"/projects/{verification_project_id}/pages/1")
    assert verification_page_detail.status_code == 200
    for output_value in (
        verification_response.json(),
        verification_page_detail.json(),
        list(events.published),
        observer.timeline("v7-17-verification-observer-trace"),
        observer.metrics.snapshot(),
        verification_state.model_dump(mode="json"),
        [record.__dict__ for record in caplog.records],
    ):
        _assert_confirmation_output_has_no_internal_values(
            output_value,
            credential_marker,
            secret,
            verification_request_body.decode("utf-8"),
            verification_fingerprint,
            "_explicit_storyboard_input_authority",
            "_ExplicitStoryboardInputAuthority",
        )
    _assert_confirmation_output_has_no_internal_values(
        captured_tracebacks(), credential_marker, secret,
        verification_request_body.decode("utf-8"), verification_fingerprint
    )
    assert credential_marker not in caplog.text
    assert verification_state.page(1).state is PageState.STORYBOARDED
    assert "_explicit_storyboard_input_authority" not in verification_serialized
    assert "_ExplicitStoryboardInputAuthority" not in verification_serialized
    assert secret not in verification_serialized
    assert verification_fingerprint not in caplog.text + verification_observer_json + verification_serialized
    captured_process_streams = capfd.readouterr()
    # TestClient is in-process; this does not inspect an external server's access logs.
    _assert_captured_streams_are_clean(
        (captured_process_streams.out, captured_process_streams.err),
        credential_marker,
        secret,
        raw_request_marker,
        raw_request_body.decode("utf-8"),
        raw_invalid_request_body.decode("utf-8"),
        verification_request_body.decode("utf-8"),
        source_fingerprint,
        verification_fingerprint,
        "_explicit_storyboard_input_authority",
        "_ExplicitStoryboardInputAuthority",
    )


def test_real_uvicorn_storyboard_confirmation_logs_do_not_disclose_internal_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    capfd: pytest.CaptureFixture[str],
) -> None:
    uvicorn = _load_uvicorn_for_real_server_test()

    from manga_director.repositories.local_file_aggregate_envelope import (
        _project_payload_from_aggregate,
    )
    from manga_director.workflow import durable_execution as durable_execution_module
    from manga_director.workflow.durable_execution import LocalFileDurablePageStore

    caplog.set_level(logging.DEBUG)
    repository = LocalFileRepository(tmp_path / "repository")
    page_design = {
        "page_type": "manga",
        "purpose": "Recover the brass key",
        "reader_emotion": "tension",
        "featured_character": "courier",
        "big_moment": "The key is within reach",
        "hook": "A door opens",
        "panel_count": 1,
        "panel_roles": ["discovery"],
    }
    review = {"checks": {"character": True}, "improvements": []}
    for project_id in ("demo", "failure-demo"):
        repository.save(
            Project(
                id=project_id,
                title="Disposable log verification",
                pages=[Page(
                    page_number=1,
                    state=PageState.REVIEWED,
                    page_design=page_design,
                    review=review,
                    metadata={"trace_id": f"v7-17-real-log-{project_id}"},
                )],
            )
        )

    loader = ProjectLoader(repository)
    events = MemoryEventBus()
    llm_provider = LLMFactory.create("mock")
    engine = WorkflowEngine(
        state_machine=StateMachine(),
        event_bus=events,
        agents=primary_agents(
            ImageGeneratorFactory.create("mock"),
            None,
            llm_provider,
            PromptPipeline(),
        ),
        support_agents=support_agents(llm_provider, None),
    )
    coordinator = WorkflowCoordinator(
        ProjectWorkflowEngine(repository, events),
        ChapterWorkflowEngine(repository, events, PageNumberWorkflowScheduler()),
        engine,
        loader,
    )
    app = build_workflow_app(
        workflow_engine=engine,
        workflow_coordinator=coordinator,
        project_loader=loader,
        repository=repository,
    )

    authority_by_project: dict[str, Any] = {}
    original_prepare = durable_execution_module._prepare_storyboard_confirmation

    def capture_private_authority(
        snapshot: Any,
        context: WorkflowContext,
        project_id: str,
        page_id: str,
        request: Any,
    ) -> Any:
        prepared_context, authority = original_prepare(
            snapshot, context, project_id, page_id, request
        )
        authority_by_project[project_id] = authority
        return prepared_context, authority

    monkeypatch.setattr(
        durable_execution_module,
        "_prepare_storyboard_confirmation",
        capture_private_authority,
    )
    original_conditional_commit = LocalFileDurablePageStore.conditional_commit
    injected_failures: list[str] = []
    exception_marker = "TEST_FAILURE_MARKER_ONLY"

    def fail_only_disposable_project(
        page_store: LocalFileDurablePageStore,
        snapshot: Any,
        project: Project,
    ) -> Any:
        if project.id == "failure-demo":
            injected_failures.append(project.id)
            raise RuntimeError(exception_marker)
        return original_conditional_commit(page_store, snapshot, project)

    monkeypatch.setattr(
        LocalFileDurablePageStore,
        "conditional_commit",
        fail_only_disposable_project,
    )
    credential = "Bearer v7-17-fake-http-credential"
    payload = {
        "requestVersion": 1,
        "expectedSource": {
            "state": "Reviewed",
            "page_design": page_design,
            "review": review,
        },
        "confirmed": True,
        "panels": [_panel()],
    }
    request_body = json.dumps(
        payload, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    monkeypatch.setattr(uvicorn.Config, "configure_logging", lambda _self: None)

    with _capture_uvicorn_access_logs() as access_records:
        with _running_loopback_uvicorn(app, uvicorn) as port:
            success_status, success_text = _loopback_json_post(
                port, "demo", request_body, credential
            )
            conflict_status, conflict_text = _loopback_json_post(
                port, "demo", request_body, credential
            )
            failure_status, failure_text = _loopback_json_post(
                port, "failure-demo", request_body, credential
            )

    assert success_status == 200
    assert json.loads(success_text) == {"status": "storyboarded"}
    assert conflict_status == 409
    assert json.loads(conflict_text) == {
        "code": "confirmation_conflict",
        "message": "The Page changed. Reload and review it before confirming again.",
    }
    assert failure_status == 503
    assert json.loads(failure_text) == {
        "code": "activation_unavailable",
        "message": "Storyboard confirmation is unavailable.",
    }
    assert injected_failures == ["failure-demo"]
    assert set(authority_by_project) == {"demo", "failure-demo"}

    successful_page = repository.load("demo").page(1)
    successful_storyboard = successful_page.storyboard
    assert isinstance(successful_storyboard, dict)
    confirmation = successful_storyboard.get("confirmation")
    assert isinstance(confirmation, dict)
    assert set(confirmation) == {
        "schema_id",
        "schema_version",
        "source_project_id",
        "source_page_number",
        "source_sha256",
        "source_page_design_sha256",
        "source_review_sha256",
        "panel_input_sha256",
        "user_confirmed",
    }
    failed_page = repository.load("failure-demo").page(1)
    assert failed_page.state is PageState.REVIEWED
    assert failed_page.storyboard is None

    authorities = tuple(authority_by_project.values())
    post_confirmation_fingerprint = repository._load_revisioned("demo").fingerprint
    successful_page_path = repository._page_path("demo", 1)
    failed_page_path = repository._page_path("failure-demo", 1)
    successful_project_path = repository._path("demo")
    failed_project_path = repository._path("failure-demo")
    successful_page_text = successful_page_path.read_text(encoding="utf-8")
    failed_page_text = failed_page_path.read_text(encoding="utf-8")
    successful_project_text = _project_payload_from_aggregate(
        successful_project_path.read_bytes()
    ).decode("utf-8")
    failed_project_text = _project_payload_from_aggregate(
        failed_project_path.read_bytes()
    ).decode("utf-8")
    successful_project_payload = json.loads(successful_project_text)
    failed_project_payload = json.loads(failed_project_text)
    successful_project_page = successful_project_payload["pages"][0]
    failed_project_page = failed_project_payload["pages"][0]
    assert isinstance(successful_project_page.get("storyboard"), dict)
    assert successful_project_page["storyboard"].get("confirmation") == confirmation
    assert failed_project_page["state"] == PageState.REVIEWED.value
    assert failed_project_page.get("storyboard") is None
    successful_page_data = json.loads(successful_page_text)
    failed_page_data = json.loads(failed_page_text)
    private_values = (
        credential,
        credential.removeprefix("Bearer "),
        request_body.decode("utf-8"),
        json.dumps(request_body.decode("utf-8"), ensure_ascii=False),
        exception_marker,
        *(repr(authority) for authority in authorities),
        *(authority.fingerprint for authority in authorities),
        post_confirmation_fingerprint,
        "_explicit_storyboard_input_authority",
        "_ExplicitStoryboardInputAuthority",
    )
    persisted_values = (
        repository.load("demo").model_dump(mode="json"),
        repository.load("failure-demo").model_dump(mode="json"),
        successful_project_payload,
        failed_project_payload,
        successful_page_data,
        failed_page_data,
    )
    for output_value in (
        json.loads(success_text),
        json.loads(conflict_text),
        json.loads(failure_text),
        *persisted_values,
    ):
        _assert_confirmation_output_has_no_internal_values(output_value, *private_values)

    captured_process_streams = capfd.readouterr()
    process_logs = captured_process_streams.out + "\n" + captured_process_streams.err
    application_logs = caplog.text
    for logs in (process_logs, application_logs):
        _assert_confirmation_output_has_no_internal_values(logs, *private_values)
        _assert_no_internal_revision_or_fingerprint_text(logs)
    for response_text in (success_text, conflict_text, failure_text):
        _assert_confirmation_output_has_no_internal_values(response_text, *private_values)
        _assert_no_internal_revision_or_fingerprint_text(response_text)
    for serialized in (
        successful_project_text,
        failed_project_text,
        successful_page_text,
        failed_page_text,
    ):
        _assert_confirmation_output_has_no_internal_values(serialized, *private_values)
        _assert_no_internal_revision_or_fingerprint_text(serialized)

    access_messages = [record.getMessage() for record in access_records]
    assert len(access_messages) == 3, "Uvicorn access log must contain all three HTTP requests."
    assert all(record.name == "uvicorn.access" for record in access_records)
    for message in access_messages:
        assert message in process_logs, "Uvicorn access record was not written to captured stderr."
    for project_id, status in (("demo", 200), ("demo", 409), ("failure-demo", 503)):
        expected_path = (
            f'"POST /projects/{project_id}/pages/1/storyboard/confirm HTTP/1.1"'
        )
        assert sum(
            expected_path in message
            and re.search(rf'"\s{status}(?:\s|$)', message) is not None
            for message in access_messages
        ) == 1
