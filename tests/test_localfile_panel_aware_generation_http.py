from __future__ import annotations

import hashlib
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from manga_director.agents import ApprovalAgent
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
from manga_director.workflow.contracts import AgentResult
from manga_director.workflow.durable_execution import _DurableRoutingError
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


def _human_visual_review_body(
    reviewed_at: str,
    *,
    outcome: str = "acceptable",
    overall_judgment: str = "acceptable_for_approval_consideration",
) -> dict[str, object]:
    return {
        "reviewerId": "reviewer:local",
        "reviewedAt": reviewed_at,
        "checklist": [
            {
                "criterion": criterion,
                "outcome": outcome,
                "rationale": "Reviewed the exact generated output.",
            }
            for criterion in (
                "character_identity", "face", "costume", "props", "pose", "gaze",
                "emotion", "screen_direction", "location", "time", "composition",
                "panel_intent", "visible_corruption", "truncation", "watermark",
                "unsafe_content", "unintended_text", "continuity_comparison",
            )
        ],
        "overallJudgment": overall_judgment,
        "rationale": "Complete local visual review.",
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


class _SuccessAgent:
    def __init__(self, state: PageState, payload: dict[str, object]) -> None:
        self._state = state
        self._payload = payload
        self.calls = 0

    def execute(self, _context: object) -> AgentResult:
        self.calls += 1
        return AgentResult(success=True, state=self._state, payload=self._payload)


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


@pytest.fixture
def generated_panel_page(
    tmp_path: Path,
    monkeypatch,
) -> SimpleNamespace:
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
        metadata={
            "previous_page": {
                "page_id": "1",
                "panel_id": "panel:before",
                "props": ["prop:book"],
                "location": "location:archive",
                "time": "time:dawn",
            },
            "current_page": {
                "page_id": "1",
                "panel_id": "panel:current",
                "props": ["prop:key"],
                "location": "location:archive",
                "time": "time:dawn",
            },
        },
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
    initial_revision = repository._load_revisioned("demo").revision
    events = MemoryEventBus()
    quality_agent = _SuccessAgent(PageState.QUALITY_CHECKED, {"passed": True})
    engine = WorkflowEngine(
        state_machine=StateMachine(),
        event_bus=events,
        agents={
            PageState.GENERATED: _NeverRunAgent(),
            PageState.QUALITY_CHECKED: quality_agent,
            PageState.APPROVED: ApprovalAgent(),
        },
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
    with ThreadPoolExecutor(max_workers=2) as pool:
        concurrent = list(
            pool.map(lambda _index: client.post(route, headers=_headers(), json=_body()), range(2))
        )
    successful = [response for response in concurrent if response.status_code == 200]
    assert successful, [(response.status_code, response.text) for response in concurrent]
    generated = successful[0]
    duplicate = next(response for response in concurrent if response.status_code != 200)
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
    assert duplicate.status_code in {409, 503}
    assert duplicate.json()["code"] in {
        "revision_conflict",
        "recovery_required",
        "activation_unavailable",
        "generation_blocked",
    }
    assert replay.status_code == 409
    assert replay.json()["code"] == "revision_conflict"
    assert changed_replay.status_code == 409
    assert changed_replay.json()["code"] == "revision_conflict"
    assert service_calls == 4
    assert transport.submit_count == 1
    assert after_replay.revision == revision_after_generation
    assert after_replay.revision == initial_revision + 1
    assert hashlib.sha256(after_replay.fingerprint.encode()).hexdigest() == (
        fingerprint_after_generation
    )
    assert after_replay.project.page(1).state == PageState.GENERATED
    generated_asset = client.get("/projects/demo/pages/1/generated-asset")
    assert generated_asset.status_code == 200

    return SimpleNamespace(
        client=client, repository=repository, transport=transport,
        generated_asset=generated_asset, events=events, quality_agent=quality_agent,
        engine=engine, coordinator=coordinator, loader=loader,
    )


def test_http_route_uses_slice1_fake_transport_and_generated_retry_is_read_only(
    generated_panel_page: SimpleNamespace,
) -> None:
    assert generated_panel_page.transport.submit_count == 1
    assert generated_panel_page.generated_asset.status_code == 200


@pytest.mark.skipif(os.name != "nt", reason="Windows durable Quality fence contract")
def test_windows_panel_page_completes_quality_review_approval_and_download(
    generated_panel_page: SimpleNamespace,
) -> None:
    client = generated_panel_page.client
    quality_client = TestClient(
        build_workflow_app(
            workflow_engine=generated_panel_page.engine,
            workflow_coordinator=generated_panel_page.coordinator,
            project_loader=generated_panel_page.loader,
            repository=generated_panel_page.repository,
        ),
        raise_server_exceptions=False,
    )
    repository = generated_panel_page.repository
    transport = generated_panel_page.transport
    generated_asset = generated_panel_page.generated_asset

    before_missing_review = generated_panel_page.repository._load_revisioned("demo")
    missing_review_quality = quality_client.post("/projects/demo/pages/1/quality", json={})
    after_missing_review = generated_panel_page.repository._load_revisioned("demo")
    assert missing_review_quality.status_code == 500
    assert missing_review_quality.json()["code"] == "internal_error"
    assert generated_panel_page.quality_agent.calls == 0
    assert after_missing_review.revision == before_missing_review.revision
    assert after_missing_review.fingerprint == before_missing_review.fingerprint

    pre_quality_review_body = _human_visual_review_body("2026-10-29T09:00:00Z")
    pre_quality_readiness = client.post(
        "/projects/demo/pages/1/visual-review-readiness", json=pre_quality_review_body
    )
    assert pre_quality_readiness.status_code == 200
    assert pre_quality_readiness.json()["status"] == "needs_review"
    assert pre_quality_readiness.json()["ready"] is False
    pre_quality_evidence = client.post(
        "/projects/demo/pages/1/visual-review-evidence",
        headers=_headers(),
        json=pre_quality_review_body,
    )
    assert pre_quality_evidence.status_code == 200
    assert pre_quality_evidence.json()["status"] == "needs_review"
    assert pre_quality_evidence.json()["ready"] is False
    pre_quality_history = client.get(
        "/projects/demo/pages/1/visual-review-evidence", headers=_headers()
    )
    assert pre_quality_history.status_code == 200
    pre_quality_record = next(
        item
        for item in pre_quality_history.json()["records"]
        if item["pageState"] == "Generated"
    )

    restarted_app = build_workflow_app(
        workflow_engine=generated_panel_page.engine,
        workflow_coordinator=generated_panel_page.coordinator,
        project_loader=generated_panel_page.loader,
        repository=repository,
    )
    restarted_client = TestClient(restarted_app, raise_server_exceptions=False)
    quality = restarted_client.post("/projects/demo/pages/1/quality", json={})
    assert quality.status_code == 200
    assert quality.json()["state"] == "QualityChecked"
    assert generated_panel_page.quality_agent.calls == 1

    review_body = _human_visual_review_body("2026-10-29T09:01:00Z")
    readiness = restarted_client.post(
        "/projects/demo/pages/1/visual-review-readiness", json=review_body
    )
    assert readiness.status_code == 200
    assert readiness.json()["ready"] is True
    review = restarted_client.post(
        "/projects/demo/pages/1/visual-review-evidence",
        headers=_headers(),
        json=review_body,
    )
    assert review.status_code == 200
    quality_page = repository._load_authoritative_page("demo", 1)
    assert quality_page.state is PageState.QUALITY_CHECKED
    assert quality_page.approval is None
    download_headers = {
        "Referer": f"{LOCAL_WEB_ORIGINS[0]}/projects/demo/pages/1",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-User": "?1",
    }
    before_approval_download = restarted_client.get(
        "/projects/demo/pages/1/approved-asset-download",
        headers=download_headers,
    )
    assert before_approval_download.status_code == 404
    history = restarted_client.get(
        "/projects/demo/pages/1/visual-review-evidence",
        headers=_headers(),
    )
    assert history.status_code == 200
    quality_checked_record = next(
        item
        for item in history.json()["records"]
        if item["pageState"] == "QualityChecked" and item["ready"]
    )
    assert quality_checked_record["reviewId"] != pre_quality_record["reviewId"]
    generated_review_approval = restarted_client.post(
        "/projects/demo/pages/1/evidence-linked-approval",
        headers=_headers(),
        json={"approvedBy": "editor-17", "reviewId": pre_quality_record["reviewId"]},
    )
    assert generated_review_approval.status_code != 200
    assert repository._load_authoritative_page("demo", 1).state is PageState.QUALITY_CHECKED
    approval = restarted_client.post(
        "/projects/demo/pages/1/evidence-linked-approval",
        headers=_headers(),
        json={"approvedBy": "editor-17", "reviewId": quality_checked_record["reviewId"]},
    )
    assert approval.status_code == 200
    assert approval.json()["state"] == "Approved"

    download = restarted_client.get(
        "/projects/demo/pages/1/approved-asset-download",
        headers=download_headers,
    )
    assert download.status_code == 200
    assert download.content
    assert generated_asset.content == download.content
    assert len(hashlib.sha256(download.content).hexdigest()) == 64

    from manga_director.workflow.localfile_page_output_proof_bridge import (
        build_localfile_page_output_proof_bridge,
    )

    page_output_proof, _quality_gate = build_localfile_page_output_proof_bridge(repository)
    approved_page = repository._load_authoritative_page("demo", 1)
    output_asset_id = approved_page.image["output_asset_id"]
    resolved = page_output_proof.resolve("demo", "1", output_asset_id)
    assert resolved.image_bytes == download.content
    assert resolved.proof.content_sha256 == hashlib.sha256(download.content).hexdigest()
    resolved.release()

    restarted_download = TestClient(restarted_app).get(
        "/projects/demo/pages/1/approved-asset-download",
        headers=download_headers,
    )
    assert restarted_download.status_code == 200
    assert restarted_download.content == download.content
    assert transport.submit_count == 1


@pytest.mark.skipif(os.name != "nt", reason="Windows durable Quality fence contract")
@pytest.mark.parametrize(
    ("review_count", "outcome", "overall_judgment"),
    [
        (1, "blocked", "blocked"),
        (2, "acceptable", "acceptable_for_approval_consideration"),
    ],
)
def test_windows_panel_quality_rejects_blocked_or_ambiguous_review_evidence(
    generated_panel_page: SimpleNamespace,
    review_count: int,
    outcome: str,
    overall_judgment: str,
) -> None:
    client = generated_panel_page.client
    quality_client = TestClient(
        build_workflow_app(
            workflow_engine=generated_panel_page.engine,
            workflow_coordinator=generated_panel_page.coordinator,
            project_loader=generated_panel_page.loader,
            repository=generated_panel_page.repository,
        ),
        raise_server_exceptions=False,
    )
    records_to_create = 1 if review_count == 2 else review_count
    for index in range(records_to_create):
        review_body = _human_visual_review_body(
            f"2026-10-29T09:0{index}:00Z",
            outcome=outcome,
            overall_judgment=overall_judgment,
        )
        recorded = client.post(
            "/projects/demo/pages/1/visual-review-evidence",
            headers=_headers(),
            json=review_body,
        )
        assert recorded.status_code == 200

    if review_count == 2:
        from manga_director.application.human_visual_review_evidence import (
            build_human_visual_review_evidence,
        )
        from manga_director.application.human_visual_review_readiness import (
            build_human_visual_review_readiness,
        )
        from manga_director.workflow.localfile_page_output_proof_bridge import (
            build_localfile_page_output_proof_bridge,
        )

        page_output_proof, _quality_gate = build_localfile_page_output_proof_bridge(
            generated_panel_page.repository
        )
        readiness = build_human_visual_review_readiness(
            generated_panel_page.repository, page_output_resolver=page_output_proof
        )
        evidence = build_human_visual_review_evidence(
            generated_panel_page.repository, readiness
        )
        stored_records = evidence._owner.read_page_history("demo", "1", 1)
        mismatched_qa_reference = stored_records[0].model_copy(
            update={
                "review_id": "review:qa-reference-mismatch",
                "qa_report_reference": "qa:another-report",
            }
        )
        evidence._owner.persist(mismatched_qa_reference)

    before = generated_panel_page.repository._load_revisioned("demo")
    events_before = tuple(generated_panel_page.events.published)
    quality = quality_client.post("/projects/demo/pages/1/quality", json={})
    after = generated_panel_page.repository._load_revisioned("demo")

    assert quality.status_code == 500
    assert quality.json()["code"] == "internal_error"
    assert generated_panel_page.quality_agent.calls == 0
    assert after.revision == before.revision
    assert after.fingerprint == before.fingerprint
    assert tuple(generated_panel_page.events.published) == events_before


@pytest.mark.skipif(os.name != "nt", reason="Windows durable Quality fence contract")
def test_windows_panel_quality_rejects_corrupt_review_store_without_mutation(
    generated_panel_page: SimpleNamespace,
) -> None:
    client = generated_panel_page.client
    quality_client = TestClient(
        build_workflow_app(
            workflow_engine=generated_panel_page.engine,
            workflow_coordinator=generated_panel_page.coordinator,
            project_loader=generated_panel_page.loader,
            repository=generated_panel_page.repository,
        ),
        raise_server_exceptions=False,
    )
    recorded = client.post(
        "/projects/demo/pages/1/visual-review-evidence",
        headers=_headers(),
        json=_human_visual_review_body("2026-10-29T09:00:00Z"),
    )
    assert recorded.status_code == 200
    owner_root = generated_panel_page.repository._next_generation_normal_execution_owner_root()
    database = owner_root / "review-evidence" / "human-visual-review-evidence.sqlite3"
    database.write_bytes(b"corrupt review evidence store")

    before = generated_panel_page.repository._load_revisioned("demo")
    events_before = tuple(generated_panel_page.events.published)
    quality = quality_client.post("/projects/demo/pages/1/quality", json={})
    after = generated_panel_page.repository._load_revisioned("demo")

    assert quality.status_code == 500
    assert quality.json()["code"] == "internal_error"
    assert generated_panel_page.quality_agent.calls == 0
    assert after.revision == before.revision
    assert after.fingerprint == before.fingerprint
    assert tuple(generated_panel_page.events.published) == events_before


@pytest.mark.skipif(os.name != "nt", reason="Windows durable Quality fence contract")
def test_windows_panel_quality_rejects_stale_attempt_review_evidence(
    generated_panel_page: SimpleNamespace,
) -> None:
    from manga_director.application.human_visual_review_evidence import (
        _payload,
        build_human_visual_review_evidence,
    )
    from manga_director.application.human_visual_review_readiness import (
        ReviewChecklistDecision,
        build_human_visual_review_readiness,
    )
    from manga_director.workflow.localfile_page_output_proof_bridge import (
        build_localfile_page_output_proof_bridge,
    )

    repository = generated_panel_page.repository
    quality_client = TestClient(
        build_workflow_app(
            workflow_engine=generated_panel_page.engine,
            workflow_coordinator=generated_panel_page.coordinator,
            project_loader=generated_panel_page.loader,
            repository=repository,
        ),
        raise_server_exceptions=False,
    )
    page_output_proof, _quality_gate = build_localfile_page_output_proof_bridge(repository)
    readiness = build_human_visual_review_readiness(
        repository, page_output_resolver=page_output_proof
    )
    evidence = build_human_visual_review_evidence(repository, readiness)
    criteria = (
        "character_identity", "face", "costume", "props", "pose", "gaze",
        "emotion", "screen_direction", "location", "time", "composition",
        "panel_intent", "visible_corruption", "truncation", "watermark",
        "unsafe_content", "unintended_text", "continuity_comparison",
    )
    proof = readiness._prove(
        "demo",
        1,
        reviewer_id="reviewer:local",
        reviewed_at=datetime(2026, 10, 29, 9, 0, tzinfo=UTC),
        checklist=tuple(
            ReviewChecklistDecision(
                criterion=criterion,
                outcome="acceptable",
                rationale="Reviewed the exact generated output.",
            )
            for criterion in criteria
        ),
        overall_judgment="acceptable_for_approval_consideration",
        rationale="Complete local visual review.",
    )
    try:
        stale = _payload(proof.report).model_copy(
            update={"attempt_id": "attempt:stale", "review_id": "review:stale"}
        )
    finally:
        proof.release()
    evidence._owner.persist(stale)

    before = repository._load_revisioned("demo")
    events_before = tuple(generated_panel_page.events.published)
    quality = quality_client.post("/projects/demo/pages/1/quality", json={})
    after = repository._load_revisioned("demo")

    assert quality.status_code == 500
    assert quality.json()["code"] == "internal_error"
    assert generated_panel_page.quality_agent.calls == 0
    assert after.revision == before.revision
    assert after.fingerprint == before.fingerprint
    assert tuple(generated_panel_page.events.published) == events_before


@pytest.mark.skipif(os.name != "nt", reason="Windows durable Quality fence contract")
@pytest.mark.parametrize("tamper", ("checklist", "state", "payload", "extra_finding"))
def test_windows_panel_quality_rejects_single_candidate_review_mismatch(
    generated_panel_page: SimpleNamespace,
    tamper: str,
) -> None:
    from manga_director.application.human_visual_review_evidence import (
        _payload,
        build_human_visual_review_evidence,
    )
    from manga_director.application.human_visual_review_readiness import (
        ReviewChecklistDecision,
        build_human_visual_review_readiness,
    )
    from manga_director.workflow.localfile_page_output_proof_bridge import (
        build_localfile_page_output_proof_bridge,
    )

    repository = generated_panel_page.repository
    page_output_proof, _quality_gate = build_localfile_page_output_proof_bridge(repository)
    readiness = build_human_visual_review_readiness(
        repository, page_output_resolver=page_output_proof
    )
    evidence = build_human_visual_review_evidence(repository, readiness)
    review_body = _human_visual_review_body("2026-10-29T09:02:00Z")
    checklist = tuple(
        ReviewChecklistDecision.model_validate(item)
        for item in review_body["checklist"]
    )
    judgment = (
        "further_review_required" if tamper == "extra_finding"
        else "acceptable_for_approval_consideration"
    )
    proof = readiness._prove(
        "demo",
        1,
        reviewer_id="reviewer:local",
        reviewed_at=datetime(2026, 10, 29, 9, 2, tzinfo=UTC),
        checklist=checklist,
        overall_judgment=judgment,
        rationale="Complete local visual review.",
    )
    try:
        stored = _payload(proof.report)
    finally:
        proof.release()

    if tamper == "checklist":
        changed_item = stored.checklist[0].model_copy(update={"outcome": "needs_review"})
        stored = stored.model_copy(
            update={"checklist": (changed_item, *stored.checklist[1:])}
        )
    elif tamper == "state":
        stored = stored.model_copy(update={"page_state": "QualityChecked"})
    elif tamper == "payload":
        stored = stored.model_copy(update={"qa_report_reference": "qa-report:other"})

    assert evidence._owner.persist(stored).outcome == "recorded"
    assert len(evidence._owner.read_page_history("demo", "1", 1)) == 1

    quality_client = TestClient(
        build_workflow_app(
            workflow_engine=generated_panel_page.engine,
            workflow_coordinator=generated_panel_page.coordinator,
            project_loader=generated_panel_page.loader,
            repository=repository,
        ),
        raise_server_exceptions=False,
    )
    before = repository._load_revisioned("demo")
    events_before = tuple(generated_panel_page.events.published)
    quality = quality_client.post("/projects/demo/pages/1/quality", json={})
    after = repository._load_revisioned("demo")

    assert quality.status_code == 500
    assert quality.json()["code"] == "internal_error"
    assert generated_panel_page.quality_agent.calls == 0
    assert after.revision == before.revision
    assert after.fingerprint == before.fingerprint
    assert tuple(generated_panel_page.events.published) == events_before


@pytest.mark.skipif(os.name != "nt", reason="Windows durable Quality fence contract")
def test_windows_panel_quality_rejects_missing_or_changed_ordered_panel_sources(
    generated_panel_page: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from manga_director.production.next_generation_page_output_proof import (
        DeterministicCompositionPageOutputProof,
    )
    from manga_director.workflow import localfile_page_output_proof_bridge as proof_bridge

    client = generated_panel_page.client
    repository = generated_panel_page.repository
    recorded = client.post(
        "/projects/demo/pages/1/visual-review-evidence",
        headers=_headers(),
        json=_human_visual_review_body("2026-10-29T09:03:00Z"),
    )
    assert recorded.status_code == 200
    assert recorded.json()["status"] == "needs_review"
    quality_client = TestClient(
        build_workflow_app(
            workflow_engine=generated_panel_page.engine,
            workflow_coordinator=generated_panel_page.coordinator,
            project_loader=generated_panel_page.loader,
            repository=repository,
        ),
        raise_server_exceptions=False,
    )

    original_resolve = proof_bridge._ReadOnlyPageOutputProof.resolve
    tamper_by_call = {2: "missing", 4: "order", 6: "hash"}
    resolve_calls = 0

    def resolve_with_changed_sources(
        resolver: object,
        project_id: str,
        page_id: str,
        output_asset_id: str,
    ):
        nonlocal resolve_calls
        resolved = original_resolve(resolver, project_id, page_id, output_asset_id)
        resolve_calls += 1
        tamper = tamper_by_call.get(resolve_calls)
        if tamper is None:
            return resolved
        assert isinstance(resolved.proof, DeterministicCompositionPageOutputProof)
        source = resolved.proof.ordered_sources[0]
        if tamper == "missing":
            changed_sources = ()
        elif tamper == "order":
            changed_sources = (source.model_copy(update={"panel_order": source.panel_order + 1}),)
        else:
            changed_sources = (
                source.model_copy(update={"content_sha256": "0" * 64}),
            )
        resolved.proof = resolved.proof.model_copy(
            update={"ordered_sources": changed_sources}
        )
        return resolved

    monkeypatch.setattr(
        proof_bridge._ReadOnlyPageOutputProof,
        "resolve",
        resolve_with_changed_sources,
    )
    before = repository._load_revisioned("demo")
    events_before = tuple(generated_panel_page.events.published)

    for expected_calls in (2, 4, 6):
        quality = quality_client.post("/projects/demo/pages/1/quality", json={})
        after = repository._load_revisioned("demo")
        assert quality.status_code == 500
        assert quality.json()["code"] == "internal_error"
        assert resolve_calls == expected_calls
        assert generated_panel_page.quality_agent.calls == 0
        assert after.revision == before.revision
        assert after.fingerprint == before.fingerprint
        assert tuple(generated_panel_page.events.published) == events_before


@pytest.mark.skipif(os.name == "nt", reason="Linux durable Quality fail-closed contract")
def test_linux_panel_page_quality_fails_closed_without_mutation(
    generated_panel_page: SimpleNamespace,
) -> None:
    repository = generated_panel_page.repository
    before = repository._load_revisioned("demo")
    events_before = tuple(generated_panel_page.events.published)

    def snapshot() -> tuple[tuple[str, str | None], ...]:
        return tuple(sorted(
            (str(path.relative_to(repository._root)),
             hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None)
            for path in repository._root.rglob("*")
        ))

    files_before = snapshot()
    with pytest.raises(_DurableRoutingError, match="^PAGE_EXECUTION_FENCE_UNAVAILABLE$"):
        generated_panel_page.client.post("/projects/demo/pages/1/quality", json={})

    after = repository._load_revisioned("demo")
    assert after.revision == before.revision
    assert after.fingerprint == before.fingerprint
    assert after.project == before.project
    assert after.project.page(1).state is PageState.GENERATED
    assert after.project.page(1).approval is None
    assert snapshot() == files_before
    assert tuple(generated_panel_page.events.published) == events_before
    assert generated_panel_page.quality_agent.calls == 0
    assert generated_panel_page.transport.submit_count == 1


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
