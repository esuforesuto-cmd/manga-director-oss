from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from manga_director.api import composition as api_composition
from manga_director.api import workflow as workflow_api
from manga_director.api.composition import build_workflow_app
from manga_director.api.workflow import LOCAL_WEB_ORIGINS, create_workflow_app
from manga_director.application import build_workflow_application
from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState, StateMachine
from manga_director.events import MemoryEventBus
from manga_director.production.next_generation_comfyui_provider_adapter import (
    ComfyUIInMemoryGeneratedImageMaterial,
)
from manga_director.production.next_generation_deterministic_page_compositor import (
    encode_rgb_png,
)
from manga_director.production.next_generation_page_generation_mode_claim import (
    LocalPageGenerationModeClaimStore,
    PageGenerationModeClaim,
)
from manga_director.production.next_generation_page_generation_plan import PanelRectangle
from manga_director.production.next_generation_panel_generation_evidence import (
    LocalPanelGenerationAuthority,
)
from manga_director.production.next_generation_provider_adapter_composition import (
    ProviderPrivateTransportRequest,
    ProviderPrivateTransportResult,
)
from manga_director.repositories import InMemoryRepository, ProjectLoader
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.workflow import (
    ChapterWorkflowEngine,
    PageNumberWorkflowScheduler,
    ProjectWorkflowEngine,
    WorkflowCoordinator,
    WorkflowEngine,
)
from manga_director.workflow.localfile_page_generation_mode_admission import (
    LocalFilePageGenerationModeObservation,
)
from manga_director.workflow.localfile_panel_aware_generation_activation import (
    LocalFilePanelAwareActivationResult,
    execute_localfile_panel_aware_generation,
)


@pytest.fixture
def tmp_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("pa")


def _headers() -> dict[str, str]:
    origin = LOCAL_WEB_ORIGINS[0]
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": origin,
        "Referer": f"{origin}/projects/demo/pages/1",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
    }


def _body() -> dict[str, object]:
    return {
        "requestVersion": 1,
        "authorizedBy": "editor-17",
        "checkpointName": "checkpoint_test.safetensors",
        "layoutProfileId": "md-page-compositor-v1",
        "layoutProfileVersion": 1,
        "rectangles": [{"left": 50_000, "top": 40_000, "right": 950_000, "bottom": 960_000}],
    }


class _FakePanelTransport:
    def __init__(self, authority_root: Path, image_bytes: bytes) -> None:
        self.authority_root = authority_root
        self.image_bytes = image_bytes
        self.submit_count = 0
        self.attempt_id = ""
        self.fail_prepare = False
        self.prepare_count = 0

    def preflight(self) -> None:
        return None

    def prepare(self, request: ProviderPrivateTransportRequest):
        self.prepare_count += 1
        self.attempt_id = request.attempt_id
        authority = LocalPanelGenerationAuthority(self.authority_root)
        reserved = authority.lookup_attempt(self.attempt_id).record
        assert reserved is not None and reserved.state == "RESERVED"
        if self.fail_prepare:
            return None

        def submit() -> ProviderPrivateTransportResult:
            started = authority.lookup_attempt(self.attempt_id).record
            assert started is not None and started.state == "PROVIDER_STARTED"
            self.submit_count += 1
            return ProviderPrivateTransportResult(
                "succeeded",
                ComfyUIInMemoryGeneratedImageMaterial(self.image_bytes),
            )

        return submit


class _NeverRunAgent:
    def execute(self, context: object):
        del context
        raise AssertionError("only the proof-bound Generated agent may execute")


def test_dedicated_route_precedes_generic_action_and_fails_closed_without_localfile() -> None:
    repository = InMemoryRepository()
    loader = ProjectLoader(repository)
    events = MemoryEventBus()
    engine = WorkflowEngine(state_machine=StateMachine(), event_bus=events, agents={})
    coordinator = WorkflowCoordinator(
        ProjectWorkflowEngine(repository, events),
        ChapterWorkflowEngine(repository, events, PageNumberWorkflowScheduler()),
        engine,
        loader,
    )
    application = build_workflow_application(
        workflow_engine=engine,
        workflow_coordinator=coordinator,
        project_loader=loader,
        repository=repository,
    )
    calls = 0

    def activation(*_args: object) -> LocalFilePanelAwareActivationResult:
        nonlocal calls
        calls += 1
        return LocalFilePanelAwareActivationResult("generated", "generated", 0)

    app = create_workflow_app(application, panel_aware_activation=activation)
    paths = [route.path for route in app.routes]
    assert paths.index("/projects/{project_id}/pages/{page_number}/panel-aware-generation") < (
        paths.index("/projects/{project_id}/pages/{page_number}/{action}")
    )

    response = TestClient(app).post(
        "/projects/demo/pages/1/panel-aware-generation",
        headers=_headers(),
        json=_body(),
    )

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert calls == 0
    for private_field in ("authorization", "attempt", "provider", "endpoint", "credential"):
        assert private_field not in response.text.lower()


def test_closed_request_and_local_admission_reject_before_activation() -> None:
    repository = InMemoryRepository()
    loader = ProjectLoader(repository)
    events = MemoryEventBus()
    engine = WorkflowEngine(state_machine=StateMachine(), event_bus=events, agents={})
    coordinator = WorkflowCoordinator(
        ProjectWorkflowEngine(repository, events),
        ChapterWorkflowEngine(repository, events, PageNumberWorkflowScheduler()),
        engine,
        loader,
    )
    application = build_workflow_application(
        workflow_engine=engine,
        workflow_coordinator=coordinator,
        project_loader=loader,
        repository=repository,
    )
    client = TestClient(create_workflow_app(application))
    route = "/projects/demo/pages/1/panel-aware-generation"
    invalid = [
        client.post(
            route,
            headers=_headers(),
            json={**_body(), "providerEndpoint": "http://127.0.0.1:8188"},
        ),
        client.post(route, headers=_headers(), json={**_body(), "requestVersion": "1"}),
        client.post(route, headers=_headers(), json={**_body(), "layoutProfileVersion": 2}),
        client.post(route, headers=_headers(), json={**_body(), "rectangles": []}),
        client.post(f"{route}?checkpointName=other", headers=_headers(), json=_body()),
        client.post(
            "/projects/demo/pages/01/panel-aware-generation",
            headers=_headers(),
            json=_body(),
        ),
        client.post(route, headers={"Content-Type": "application/json"}, json=_body()),
        client.post(
            route,
            headers=_headers(),
            content=(
                '{"requestVersion":1,"requestVersion":1,"authorizedBy":"editor-17",'
                '"checkpointName":"checkpoint_test.safetensors",'
                '"layoutProfileId":"md-page-compositor-v1","layoutProfileVersion":1,'
                '"rectangles":[{"left":50000,"top":40000,"right":950000,"bottom":960000}]}'
            ),
        ),
    ]

    assert all(response.status_code == 422 for response in invalid)
    assert all(response.headers["cache-control"] == "no-store" for response in invalid)


def test_only_localfile_composition_wires_the_activation_service(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repository = LocalFileRepository(tmp_path / "repository")
    repository.save(
        Project(
            id="demo",
            title="Demo",
            pages=[
                Page(
                    page_number=1,
                    state=PageState.PROMPT_BUILT,
                    page_design={},
                    review={},
                    storyboard={},
                    prompt={},
                )
            ],
            created_at=datetime(2026, 10, 28, tzinfo=UTC),
            updated_at=datetime(2026, 10, 28, tzinfo=UTC),
        )
    )
    calls: list[tuple[object, ...]] = []
    results = [
        LocalFilePanelAwareActivationResult("generated", "generated", 0),
        LocalFilePanelAwareActivationResult("blocked", "revision_conflict"),
    ]

    def execute(repository_arg, engine_arg, *args, **kwargs):
        calls.append((repository_arg, engine_arg, *args, kwargs))
        return results[len(calls) - 1]

    monkeypatch.setattr(api_composition, "execute_localfile_panel_aware_generation", execute)
    loader = ProjectLoader(repository)
    events = MemoryEventBus()
    engine = WorkflowEngine(state_machine=StateMachine(), event_bus=events, agents={})
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

    client = TestClient(app)
    response = client.post(
        "/projects/demo/pages/1/panel-aware-generation",
        headers=_headers(),
        json=_body(),
    )
    replay = client.post(
        "/projects/demo/pages/1/panel-aware-generation",
        headers=_headers(),
        json=_body(),
    )

    assert response.status_code == 200
    assert response.json() == {"status": "generated"}
    assert replay.status_code == 409
    assert replay.json()["code"] == "revision_conflict"
    assert len(calls) == 2
    assert calls[0][0] is repository
    assert calls[0][1] is engine
    assert calls[0][2:6] == (
        "demo",
        1,
        "editor-17",
        "checkpoint_test.safetensors",
    )
    assert calls[0][6] == (PanelRectangle(left=50_000, top=40_000, right=950_000, bottom=960_000),)
    assert calls[0][7] == {
        "layout_profile_id": "md-page-compositor-v1",
        "layout_profile_version": 1,
    }
    assert calls[1][2:] == calls[0][2:]


@pytest.mark.parametrize(
    ("result", "status_code", "public_code"),
    [
        (
            LocalFilePanelAwareActivationResult("generated", "generated"),
            200,
            "generated",
        ),
        (
            LocalFilePanelAwareActivationResult("generated", "unexpected_code"),
            503,
            "activation_unavailable",
        ),
        (
            LocalFilePanelAwareActivationResult("generated", "revision_conflict"),
            503,
            "activation_unavailable",
        ),
        (
            LocalFilePanelAwareActivationResult("blocked", "generated"),
            503,
            "activation_unavailable",
        ),
        (
            LocalFilePanelAwareActivationResult("partial", "generated"),
            503,
            "activation_unavailable",
        ),
        (
            LocalFilePanelAwareActivationResult("recovery_required", "generated"),
            503,
            "activation_unavailable",
        ),
        (
            LocalFilePanelAwareActivationResult("blocked", "activation_unavailable"),
            503,
            "activation_unavailable",
        ),
        (
            LocalFilePanelAwareActivationResult("blocked", "revision_conflict"),
            409,
            "revision_conflict",
        ),
        (
            LocalFilePanelAwareActivationResult("blocked", "unexpected_code"),
            409,
            "generation_blocked",
        ),
        (
            LocalFilePanelAwareActivationResult("partial", "revision_conflict"),
            409,
            "generation_incomplete",
        ),
        (
            LocalFilePanelAwareActivationResult("recovery_required", "activation_unavailable"),
            409,
            "recovery_required",
        ),
        (
            LocalFilePanelAwareActivationResult("unknown", "unexpected_code"),
            503,
            "activation_unavailable",
        ),
        (
            LocalFilePanelAwareActivationResult("unknown", "activation_input_invalid"),
            503,
            "activation_unavailable",
        ),
        (
            LocalFilePanelAwareActivationResult("recovery_required", "private-attempt"),
            409,
            "recovery_required",
        ),
        (
            LocalFilePanelAwareActivationResult("partial", "private-asset"),
            409,
            "generation_incomplete",
        ),
        (
            LocalFilePanelAwareActivationResult("blocked", "activation_input_invalid"),
            422,
            "invalid_input",
        ),
        (
            LocalFilePanelAwareActivationResult("blocked", "private-endpoint-secret"),
            409,
            "generation_blocked",
        ),
    ],
)
def test_activation_outcomes_map_to_bounded_http_errors(
    tmp_path: Path,
    result: LocalFilePanelAwareActivationResult,
    status_code: int,
    public_code: str,
) -> None:
    repository = LocalFileRepository(tmp_path / "repository")
    loader = ProjectLoader(repository)
    events = MemoryEventBus()
    engine = WorkflowEngine(state_machine=StateMachine(), event_bus=events, agents={})
    coordinator = WorkflowCoordinator(
        ProjectWorkflowEngine(repository, events),
        ChapterWorkflowEngine(repository, events, PageNumberWorkflowScheduler()),
        engine,
        loader,
    )
    application = build_workflow_application(
        workflow_engine=engine,
        workflow_coordinator=coordinator,
        project_loader=loader,
        repository=repository,
    )
    app = create_workflow_app(
        application,
        panel_aware_activation=lambda *_args: result,
    )

    response = TestClient(app).post(
        "/projects/demo/pages/1/panel-aware-generation",
        headers=_headers(),
        json=_body(),
    )

    assert response.status_code == status_code
    if status_code == 200:
        assert response.json() == {"status": "generated"}
    else:
        assert response.json() == {
            "code": public_code,
            "message": {
                "recovery_required": "Generation requires recovery before another attempt.",
                "generation_incomplete": "Generation did not complete.",
                "generation_blocked": "Generation is blocked.",
                "invalid_input": "Request validation failed.",
                "revision_conflict": "The Page changed and generation was not started.",
                "activation_unavailable": "Generation is unavailable.",
            }[public_code],
        }
    assert "private" not in response.text
    assert "secret" not in response.text


class _FailingActivationResult:
    def __init__(self, failing_attribute: str) -> None:
        self.failing_attribute = failing_attribute

    @property
    def status(self) -> str:
        if self.failing_attribute == "status":
            raise RuntimeError("private status detail")
        return "generated"

    @property
    def code(self) -> str:
        if self.failing_attribute == "code":
            raise RuntimeError("private code detail")
        return "generated"


@pytest.mark.parametrize(
    ("result", "raises"),
    [
        (None, False),
        (SimpleNamespace(status="generated"), False),
        (SimpleNamespace(status=1, code="generated"), False),
        (SimpleNamespace(status="blocked", code=None), False),
        (_FailingActivationResult("status"), False),
        (_FailingActivationResult("code"), False),
        (None, True),
    ],
)
def test_broken_activation_results_and_exceptions_fail_closed(
    tmp_path: Path,
    result: object,
    raises: bool,
) -> None:
    calls = 0
    repository = LocalFileRepository(tmp_path / "repository")
    loader = ProjectLoader(repository)
    events = MemoryEventBus()
    engine = WorkflowEngine(state_machine=StateMachine(), event_bus=events, agents={})
    coordinator = WorkflowCoordinator(
        ProjectWorkflowEngine(repository, events),
        ChapterWorkflowEngine(repository, events, PageNumberWorkflowScheduler()),
        engine,
        loader,
    )
    application = build_workflow_application(
        workflow_engine=engine,
        workflow_coordinator=coordinator,
        project_loader=loader,
        repository=repository,
    )

    def activation(*_args: object) -> object:
        nonlocal calls
        calls += 1
        if raises:
            raise RuntimeError("private endpoint secret")
        return result

    app = create_workflow_app(application, panel_aware_activation=activation)
    response = TestClient(app).post(
        "/projects/demo/pages/1/panel-aware-generation",
        headers=_headers(),
        json=_body(),
    )

    assert response.status_code == 503
    assert response.json() == {
        "code": "activation_unavailable",
        "message": "Generation is unavailable.",
    }
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert calls == 1
    assert "private" not in response.text
    assert "secret" not in response.text


def test_http_mode_conflict_stops_before_fake_provider_preparation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    page = Page(
        page_number=1,
        state=PageState.PROMPT_BUILT,
        page_design={},
        review={},
        storyboard={
            "panels": [
                {
                    "number": 1,
                    "narrative_intent": "Aki finds the archive key.",
                    "characters": ["character-aki-v1"],
                    "continuity_bindings": ["costume-aki-blue-coat-v2"],
                    "action": "Aki turns the brass key in the archive lock.",
                    "background": "The east archive corridor at dawn.",
                    "composition": "Medium shot, Aki left and the lock foreground.",
                    "constraints": ["Keep the key visible."],
                }
            ],
            "title": "Archive",
        },
        dialogue={},
        prompt={"prompt_markdown": "Aki finds the archive key.", "tokens": 7},
    )
    repository = LocalFileRepository((tmp_path / "r").resolve())
    repository.save(
        Project(
            id="demo",
            title="Demo",
            pages=[page],
            created_at=datetime(2026, 10, 28, tzinfo=UTC),
            updated_at=datetime(2026, 10, 28, tzinfo=UTC),
        )
    )
    observation = LocalFilePageGenerationModeObservation(repository)
    current = observation.observe("demo", "1")
    assert current is not None
    claim = PageGenerationModeClaim(
        claim_id="legacy-claim-demo-1",
        project_id="demo",
        page_id="1",
        page_revision=current.page_revision,
        page_fingerprint=current.page_fingerprint,
        mode="legacy_single_canvas",
        mode_binding_reference="legacy-page-demo-1",
        authorizer_reference="authorizer-editor-17",
    )
    assert (
        LocalPageGenerationModeClaimStore(observation.claim_root).create_or_confirm(claim).outcome
        == "created"
    )
    events = MemoryEventBus()
    engine = WorkflowEngine(state_machine=StateMachine(), event_bus=events, agents={})
    loader = ProjectLoader(repository)
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
    image_bytes = encode_rgb_png(1024, 1024, b"\xff" * (1024 * 1024 * 3))
    transport = _FakePanelTransport(
        repository._next_generation_normal_execution_owner_root() / "panel-generation-authority",
        image_bytes,
    )
    real_execute = execute_localfile_panel_aware_generation

    def execute_with_fake_transport(*args, **kwargs):
        return real_execute(
            *args,
            **kwargs,
            transport_factory=lambda _checkpoint, _configuration: transport,
        )

    monkeypatch.setattr(
        api_composition,
        "execute_localfile_panel_aware_generation",
        execute_with_fake_transport,
    )
    response = TestClient(app).post(
        "/projects/demo/pages/1/panel-aware-generation",
        headers=_headers(),
        json=_body(),
    )

    assert response.status_code == 409
    assert response.json() == {
        "code": "generation_blocked",
        "message": "Generation is blocked.",
    }
    assert transport.prepare_count == 0
    assert transport.submit_count == 0


def test_http_route_uses_slice1_fake_transport_and_generated_retry_is_read_only(
    tmp_path: Path,
    monkeypatch,
) -> None:
    page = Page(
        page_number=1,
        state=PageState.PROMPT_BUILT,
        page_design={},
        review={},
        storyboard={
            "panels": [
                {
                    "number": 1,
                    "narrative_intent": "Aki finds the archive key.",
                    "characters": ["character-aki-v1"],
                    "continuity_bindings": ["costume-aki-blue-coat-v2"],
                    "action": "Aki turns the brass key in the archive lock.",
                    "background": "The east archive corridor at dawn.",
                    "composition": "Medium shot, Aki left and the lock foreground.",
                    "constraints": ["Keep the key visible."],
                }
            ],
            "title": "Archive",
        },
        dialogue={},
        prompt={"prompt_markdown": "Aki finds the archive key.", "tokens": 7},
    )
    repository = LocalFileRepository((tmp_path / "r").resolve())
    repository.save(
        Project(
            id="demo",
            title="Demo",
            pages=[page],
            created_at=datetime(2026, 10, 28, tzinfo=UTC),
            updated_at=datetime(2026, 10, 28, tzinfo=UTC),
        )
    )
    events = MemoryEventBus()
    engine = WorkflowEngine(
        state_machine=StateMachine(),
        event_bus=events,
        agents={PageState.GENERATED: _NeverRunAgent()},
    )
    loader = ProjectLoader(repository)
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
    image_bytes = encode_rgb_png(1024, 1024, b"\xff" * (1024 * 1024 * 3))
    authority_root = (
        repository._next_generation_normal_execution_owner_root() / "panel-generation-authority"
    )
    transport = _FakePanelTransport(authority_root, image_bytes)
    real_execute = execute_localfile_panel_aware_generation
    service_calls = 0

    def execute_with_fake_transport(*args, **kwargs):
        nonlocal service_calls
        service_calls += 1
        return real_execute(
            *args,
            **kwargs,
            transport_factory=lambda _checkpoint, _configuration: transport,
        )

    monkeypatch.setattr(
        api_composition,
        "execute_localfile_panel_aware_generation",
        execute_with_fake_transport,
    )
    client = TestClient(app)
    route = "/projects/demo/pages/1/panel-aware-generation"
    generated = client.post(route, headers=_headers(), json=_body())
    after_generation = repository._load_revisioned("demo")
    revision_after_generation = after_generation.revision
    fingerprint_after_generation = hashlib.sha256(after_generation.fingerprint.encode()).hexdigest()
    replay = client.post(route, headers=_headers(), json=_body())
    changed_replay = client.post(
        route,
        headers=_headers(),
        json={**_body(), "authorizedBy": "editor-18"},
    )
    after_replay = repository._load_revisioned("demo")

    assert generated.status_code == 200
    assert generated.json() == {"status": "generated"}
    assert replay.status_code == 409
    assert replay.json()["code"] == "revision_conflict"
    assert changed_replay.status_code == 409
    assert changed_replay.json()["code"] == "revision_conflict"
    assert service_calls == 3
    assert transport.submit_count == 1
    assert after_replay.revision == revision_after_generation
    assert hashlib.sha256(after_replay.fingerprint.encode()).hexdigest() == (
        fingerprint_after_generation
    )
    assert after_replay.project.page(1).state == PageState.GENERATED


def test_generic_generate_still_uses_the_existing_action_dispatcher(monkeypatch) -> None:
    from manga_director.api.workflow import create_workflow_app

    repository = InMemoryRepository()
    loader = ProjectLoader(repository)
    events = MemoryEventBus()
    engine = WorkflowEngine(state_machine=StateMachine(), event_bus=events, agents={})
    coordinator = WorkflowCoordinator(
        ProjectWorkflowEngine(repository, events),
        ChapterWorkflowEngine(repository, events, PageNumberWorkflowScheduler()),
        engine,
        loader,
    )
    application = build_workflow_application(
        workflow_engine=engine,
        workflow_coordinator=coordinator,
        project_loader=loader,
        repository=repository,
    )
    application.create_project("demo", "Demo", 1, {})
    actions: list[object] = []

    def execute(_application, _project_id, _page_number, action, _body):
        actions.append(action)

    monkeypatch.setattr(workflow_api, "_execute_action", execute)
    response = TestClient(create_workflow_app(application)).post(
        "/projects/demo/pages/1/generate", json={}
    )

    assert response.status_code == 200
    assert actions == [workflow_api.WorkflowAction.GENERATE]
