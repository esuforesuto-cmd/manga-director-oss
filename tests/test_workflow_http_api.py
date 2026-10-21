from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from manga_director.api import workflow as workflow_api
from manga_director.api.composition import build_workflow_app as build_http_workflow_app
from manga_director.api.workflow import LOCAL_WEB_ORIGINS, create_workflow_app
from manga_director.application import WorkflowApplicationService, build_workflow_application
from manga_director.application.evidence_linked_approval import (
    EvidenceLinkedApprovalUnavailable,
)
from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState, StateMachine
from manga_director.events import MemoryEventBus
from manga_director.repositories import InMemoryRepository, ProjectLoader
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.workflow import (
    ChapterWorkflowEngine,
    PageNumberWorkflowScheduler,
    ProjectWorkflowEngine,
    WorkflowCoordinator,
    WorkflowEngine,
)
from manga_director.workflow.contracts import Agent, AgentResult, WorkflowContext


@dataclass
class _RecordingAgent:
    target: PageState | None
    calls: int = 0
    failure: str | None = None

    def execute(self, context: WorkflowContext) -> AgentResult:
        self.calls += 1
        if self.failure is not None:
            raise RuntimeError(self.failure)
        target = self.target or context.state
        payload = {"passed": True} if target is PageState.QUALITY_CHECKED else {"ok": True}
        if target is PageState.APPROVED:
            payload = {"approved_by": context.metadata.get("approved_by")}
        return AgentResult(success=True, state=target, payload=payload)


def _application(*, failure: str | None = None) -> tuple[WorkflowApplicationService, list[_RecordingAgent]]:
    repository = InMemoryRepository()
    loader = ProjectLoader(repository)
    events = MemoryEventBus()
    recording = {
        state: _RecordingAgent(state, failure=failure if state is PageState.DESIGNED else None)
        for state in (
            PageState.DESIGNED,
            PageState.REVIEWED,
            PageState.STORYBOARDED,
            PageState.PROMPT_BUILT,
            PageState.GENERATED,
            PageState.QUALITY_CHECKED,
            PageState.APPROVED,
        )
    }
    support = {
        "dialogue": _RecordingAgent(None),
        "continuity": _RecordingAgent(None),
    }
    engine = WorkflowEngine(
        state_machine=StateMachine(),
        event_bus=events,
        agents=recording,
        support_agents=cast_agents(support),
    )
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
    return application, [*recording.values(), *support.values()]


def cast_agents(agents: Mapping[str, _RecordingAgent]) -> Mapping[str, Agent]:
    return agents


def test_http_contract_uses_camel_case_dtos_and_keeps_get_requests_read_only() -> None:
    application, agents = _application()
    client = TestClient(create_workflow_app(application))

    health = client.get("/health")
    created = client.post("/projects", json={"id": "demo", "title": "Demo"})
    listed = client.get("/projects")
    project = client.get("/projects/demo")
    chapter = client.get("/projects/demo/chapters/chapter-1")
    page = client.get("/projects/demo/pages/1")

    assert health.json() == {"status": "ok"}
    assert created.status_code == 201
    assert created.json()["currentState"] == "Draft"
    assert "current_state" not in created.json()
    assert listed.json()[0]["updatedAt"]
    assert project.json()["currentPage"] == 1
    assert chapter.json()["pages"][0]["pageNumber"] == 1
    assert page.json()["workflow"]["availableActions"] == ["design"]
    assert sum(agent.calls for agent in agents) == 0


def test_http_routes_delegate_project_chapter_page_support_and_approval() -> None:
    application, _agents = _application()
    client = TestClient(create_workflow_app(application))

    client.post("/projects", json={"id": "project-run", "title": "Project run"})
    project_run = client.post("/projects/project-run/run")
    approval_missing = client.post(
        "/projects/project-run/pages/1/approve", json={"metadata": {}}
    )
    approved = client.post(
        "/projects/project-run/pages/1/approve", json={"approvedBy": "editor"}
    )

    client.post("/projects", json={"id": "chapter-run", "title": "Chapter run"})
    chapter_run = client.post("/projects/chapter-run/chapters/chapter-1/run")

    client.post("/projects", json={"id": "page-actions", "title": "Page actions"})
    designed = client.post(
        "/projects/page-actions/pages/1/design", json={"metadata": {"purpose": "hook"}}
    )
    dialogue = client.post(
        "/projects/page-actions/pages/1/dialogue", json={"metadata": {}}
    )

    assert project_run.json()["currentState"] == "QualityChecked"
    assert approval_missing.status_code == 422
    assert approved.json()["state"] == "Approved"
    assert chapter_run.json()["pages"][0]["state"] == "QualityChecked"
    assert designed.json()["state"] == "Designed"
    assert dialogue.json()["state"] == "Designed"
    assert dialogue.json()["artifacts"]["dialogue"] == {"ok": True}


def test_http_error_mapping_cors_and_delete_exclusion_are_safe() -> None:
    application, _agents = _application()
    client = TestClient(create_workflow_app(application))
    client.post("/projects", json={"id": "demo", "title": "Demo"})

    duplicate = client.post("/projects", json={"id": "demo", "title": "Demo"})
    missing = client.get("/projects/missing")
    conflict = client.post("/projects/demo/pages/1/review", json={})
    invalid = client.post("/projects/demo/pages/1/retry", json={})
    invalid_page = client.get("/projects/demo/pages/0")
    delete = client.delete("/projects/demo")
    allowed = client.options(
        "/projects",
        headers={
            "Origin": LOCAL_WEB_ORIGINS[0],
            "Access-Control-Request-Method": "POST",
        },
    )
    denied = client.options(
        "/projects",
        headers={
            "Origin": "http://example.com",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert duplicate.status_code == 409
    assert missing.status_code == 404
    assert conflict.status_code == 409
    assert invalid.status_code == 422
    assert invalid_page.status_code == 422
    assert delete.status_code == 405
    assert delete.json()["code"] == "method_not_allowed"
    assert allowed.headers["access-control-allow-origin"] == LOCAL_WEB_ORIGINS[0]
    assert "access-control-allow-origin" not in denied.headers


def test_unexpected_failures_return_no_internal_detail() -> None:
    application, _agents = _application(failure="secret path C:/private/token")
    client = TestClient(create_workflow_app(application), raise_server_exceptions=False)
    client.post("/projects", json={"id": "demo", "title": "Demo"})

    response = client.post("/projects/demo/pages/1/design", json={})

    assert response.status_code == 500
    assert response.json() == {
        "code": "internal_error",
        "message": "An internal error occurred.",
    }
    assert "secret" not in response.text


def test_generated_asset_route_has_fixed_binary_contract_and_rejects_extra_input(
    monkeypatch,
) -> None:
    application, agents = _application()
    png = b"\x89PNG\r\n\x1a\nverified"
    calls: list[tuple[str, int]] = []

    def get(project_id: str, page_number: int) -> SimpleNamespace:
        calls.append((project_id, page_number))
        return SimpleNamespace(image_bytes=png, release=lambda: None)

    monkeypatch.setattr(
        workflow_api,
        "generated_asset_presentation_for",
        lambda _application: SimpleNamespace(get=get),
    )
    client = TestClient(create_workflow_app(application))

    response = client.get("/projects/demo/pages/1/generated-asset")
    query = client.get("/projects/demo/pages/1/generated-asset?asset_id=other")
    body = client.request(
        "GET",
        "/projects/demo/pages/1/generated-asset",
        content=b'{"path":"C:/private/image.png"}',
    )
    ranged = client.get(
        "/projects/demo/pages/1/generated-asset",
        headers={"Range": "bytes=0-1"},
    )

    assert response.status_code == 200 and response.content == png
    assert response.headers["content-type"] == "image/png"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert {"etag", "last-modified", "location", "content-disposition"}.isdisjoint(
        response.headers
    )
    assert calls == [("demo", 1)]
    assert {query.status_code, body.status_code, ranged.status_code} == {422}
    assert all(
        item.headers["cache-control"] == "no-store" for item in (query, body, ranged)
    )
    assert sum(agent.calls for agent in agents) == 0


def test_localfile_http_composition_missing_sidecars_creates_nothing(tmp_path: Path) -> None:
    repository = LocalFileRepository(tmp_path / "repository")
    repository.save(
        Project(
            id="demo",
            title="Demo",
            pages=[
                Page(
                    page_number=1,
                    state=PageState.GENERATED,
                    page_design={},
                    review={},
                    storyboard={},
                    prompt={},
                    image={
                        "artifact_kind": "logical_output_asset",
                        "output_asset_id": "asset:missing",
                    },
                )
            ],
        )
    )
    loader = ProjectLoader(repository)
    events = MemoryEventBus()
    engine = WorkflowEngine(state_machine=StateMachine(), event_bus=events, agents={})
    coordinator = WorkflowCoordinator(
        ProjectWorkflowEngine(repository, events),
        ChapterWorkflowEngine(repository, events, PageNumberWorkflowScheduler()),
        engine,
        loader,
    )
    app = build_http_workflow_app(
        workflow_engine=engine,
        workflow_coordinator=coordinator,
        project_loader=loader,
        repository=repository,
    )
    before = tuple(sorted(path.relative_to(repository._root) for path in repository._root.rglob("*")))

    response = TestClient(app).get("/projects/demo/pages/1/generated-asset")

    after = tuple(sorted(path.relative_to(repository._root) for path in repository._root.rglob("*")))
    assert response.status_code == 404
    assert response.json() == {"code": "not_found", "message": "Not found."}
    assert response.headers["cache-control"] == "no-store"
    assert after == before


def _linked_approval_headers() -> dict[str, str]:
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": LOCAL_WEB_ORIGINS[0],
        "Referer": f"{LOCAL_WEB_ORIGINS[0]}/projects/demo/pages/1",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
    }


def test_evidence_linked_approval_route_requires_explicit_closed_local_request(
    monkeypatch,
) -> None:
    application, _agents = _application()
    application.create_project("demo", "Demo", 1, {})
    application.run_project("demo")
    calls: list[tuple[str, int, str, str]] = []

    class Service:
        def approve(
            self,
            project_id: str,
            page_number: int,
            *,
            approved_by: str,
            review_id: str,
        ) -> None:
            calls.append((project_id, page_number, approved_by, review_id))
            application.approve_page(project_id, page_number, approved_by, {})

    monkeypatch.setattr(
        workflow_api,
        "evidence_linked_approval_for",
        lambda _application: Service(),
    )
    client = TestClient(create_workflow_app(application))

    response = client.post(
        "/projects/demo/pages/1/evidence-linked-approval",
        headers=_linked_approval_headers(),
        json={"approvedBy": "editor:local", "reviewId": "review:exact:001"},
    )

    assert response.status_code == 200
    assert response.json()["state"] == "Approved"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert calls == [("demo", 1, "editor:local", "review:exact:001")]


def test_evidence_linked_approval_rejects_admission_body_and_path_variants_before_service(
    monkeypatch,
) -> None:
    application, _agents = _application()
    calls = 0

    class Service:
        def approve(self, *args, **kwargs) -> None:
            nonlocal calls
            calls += 1

    monkeypatch.setattr(
        workflow_api,
        "evidence_linked_approval_for",
        lambda _application: Service(),
    )
    client = TestClient(create_workflow_app(application))
    route = "/projects/demo/pages/1/evidence-linked-approval"
    body = '{"approvedBy":"editor","reviewId":"review:001"}'
    duplicate_content_length_headers = list(_linked_approval_headers().items()) + [
        ("Content-Length", str(len(body))),
        ("Content-Length", str(len(body))),
    ]
    invalid = [
        client.post(route, content=body, headers={"Content-Type": "application/json"}),
        client.post(
            f"{route}?reviewId=other",
            content=body,
            headers=_linked_approval_headers(),
        ),
        client.post(
            "/projects/demo/pages/01/evidence-linked-approval",
            content=body,
            headers=_linked_approval_headers(),
        ),
        client.post(
            route,
            content=body,
            headers={**_linked_approval_headers(), "Referer": "http://localhost:3000/"},
        ),
        client.post(
            route,
            content=(
                '{"approvedBy":"editor","reviewId":"review:001",'
                '"reviewId":"review:other"}'
            ),
            headers=_linked_approval_headers(),
        ),
        client.post(
            route,
            content=body,
            headers=duplicate_content_length_headers,
        ),
        client.post(
            route,
            headers=_linked_approval_headers(),
            json={
                "approvedBy": "editor",
                "reviewId": "review:001",
                "metadata": {},
            },
        ),
    ]

    assert all(response.status_code == 422 for response in invalid)
    assert all(response.headers["cache-control"] == "no-store" for response in invalid)
    assert calls == 0


def test_evidence_linked_approval_failure_is_redacted_and_does_not_claim_success(
    monkeypatch,
) -> None:
    application, _agents = _application()

    class Service:
        def approve(self, *args, **kwargs) -> None:
            raise EvidenceLinkedApprovalUnavailable("secret C:/private/evidence.sqlite3")

    monkeypatch.setattr(
        workflow_api,
        "evidence_linked_approval_for",
        lambda _application: Service(),
    )
    response = TestClient(create_workflow_app(application)).post(
        "/projects/demo/pages/1/evidence-linked-approval",
        headers=_linked_approval_headers(),
        json={"approvedBy": "editor:local", "reviewId": "review:exact:001"},
    )

    assert response.status_code == 409
    assert response.json() == {
        "code": "approval_unavailable",
        "message": "Request validation failed.",
    }
    assert "secret" not in response.text
