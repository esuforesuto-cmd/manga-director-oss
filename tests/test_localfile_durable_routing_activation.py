from __future__ import annotations

import hashlib
import json
from pathlib import Path
from threading import Barrier, Event, Thread

import pytest
from typer.testing import CliRunner

import manga_director.cli.runtime as cli_runtime
import manga_director.mcp.composition as mcp_composition
import manga_director.workflow.localfile_durable_routing as durable_routing
from manga_director.adapters.factory import ImageGeneratorFactory
from manga_director.adapters.image_generator import ImageResult
from manga_director.adapters.llm_factory import LLMFactory
from manga_director.adapters.llm_provider import LLMResult, PromptRequest
from manga_director.cli.app import app
from manga_director.cli.config import AppConfig, RepositorySettings
from manga_director.cli.runtime import build_runtime
from manga_director.domain.events import EventType
from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState, StateMachine
from manga_director.events import MemoryEventBus
from manga_director.mcp import build_mcp_server
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.workflow.contracts import AgentResult, WorkflowContext, WorkflowStatus
from manga_director.workflow.durable_execution import _route_localfile_primary
from manga_director.workflow.engine import WorkflowEngine
from manga_director.workflow.hierarchy_contracts import ProjectWorkflowResult
from manga_director.workflow.localfile_durable_routing import (
    LocalFileDurableBatchWorkflowEngine,
    LocalFileDurableWorkflowCoordinator,
    LocalFileDurableWorkflowWorker,
    build_localfile_durable_workflow,
)
from manga_director.workflow.project_engine import ProjectWorkflowEngine


class _Agent:
    def __init__(self, state: PageState) -> None:
        self._state = state
        self.calls = 0

    def execute(self, context: WorkflowContext) -> AgentResult:
        self.calls += 1
        return AgentResult(success=True, state=self._state, payload={"state": self._state.value})


def _repository(tmp_path: Path, page: Page | None = None) -> LocalFileRepository:
    repository = LocalFileRepository(tmp_path)
    repository.save(Project(id="durable-routing", title="Durable", pages=[page or Page(page_number=1)]))
    return repository


def _tree_manifest(root: Path) -> tuple[tuple[str, str], ...]:
    entries: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*")):
        relative = str(path.relative_to(root))
        if path.is_dir():
            entries.append((relative, "directory"))
        elif path.is_file():
            entries.append((relative, hashlib.sha256(path.read_bytes()).hexdigest()))
    return tuple(entries)


def _engine(bus: MemoryEventBus) -> WorkflowEngine:
    agents = {state: _Agent(state) for state in list(PageState)[1:]}
    return WorkflowEngine(state_machine=StateMachine(), event_bus=bus, agents=agents)


def _forbid_raw_save(monkeypatch: pytest.MonkeyPatch, repository: LocalFileRepository) -> None:
    def fail_save(_project: Project) -> None:
        raise AssertionError("raw repository.save fallback reached")

    monkeypatch.setattr(repository, "save", fail_save)


def test_localfile_coordinator_routes_lifecycle_and_page_through_durable_primitives(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository(tmp_path)
    bus = MemoryEventBus()
    coordinator, _batch = build_localfile_durable_workflow(repository, _engine(bus), bus)
    _forbid_raw_save(monkeypatch, repository)

    result = coordinator.run_project("durable-routing")

    assert isinstance(coordinator, LocalFileDurableWorkflowCoordinator)
    assert result.chapter_result is not None
    assert result.chapter_result.page_context is not None
    assert result.chapter_result.page_context.state == PageState.QUALITY_CHECKED
    assert repository.load("durable-routing").page(1).state == PageState.QUALITY_CHECKED
    assert [event.event_type for event in bus.published[:2]] == [
        EventType.PROJECT_STARTED,
        EventType.CHAPTER_STARTED,
    ]
    assert [event.event_type for event in result.events[:2]] == [
        EventType.PROJECT_STARTED,
        EventType.CHAPTER_STARTED,
    ]


def test_localfile_worker_uses_only_caller_identity_and_reloads_authoritative_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository(tmp_path)
    bus = MemoryEventBus()
    worker = LocalFileDurableWorkflowWorker(repository, _engine(bus))
    _forbid_raw_save(monkeypatch, repository)
    untrusted = WorkflowContext(
        page={"project_id": "durable-routing", "page_id": "1"},
        state=PageState.APPROVED,
        artifacts={"untrusted": "must not be used"},
    )

    result = worker.run(untrusted)

    assert result.current_state == PageState.QUALITY_CHECKED
    assert repository.load("durable-routing").page(1).state == PageState.QUALITY_CHECKED


def test_localfile_worker_status_uses_one_authoritative_snapshot_without_side_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository(tmp_path)
    bus = MemoryEventBus()
    engine = _engine(bus)
    worker = LocalFileDurableWorkflowWorker(repository, engine)
    initial = repository.load("durable-routing").replace_page(
        Page(
            page_number=1,
            state=PageState.QUALITY_CHECKED,
            quality={"snapshot": "before"},
            metadata={"snapshot": "before"},
        )
    )
    replacement = initial.replace_page(
        Page(
            page_number=1,
            state=PageState.APPROVED,
            approval={"snapshot": "after"},
            metadata={"snapshot": "after"},
        )
    )
    load_count = 0

    def concurrent_replacement(_project_id: str) -> Project:
        nonlocal load_count
        load_count += 1
        return initial if load_count == 1 else replacement

    def fail_agent_execution(_context: WorkflowContext) -> AgentResult:
        raise AssertionError("status-only worker path executed an agent")

    def fail_cas(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("status-only worker path executed CAS")

    status = WorkflowStatus(
        current_state=PageState.QUALITY_CHECKED,
        current_step="quality",
        executable_step="approve",
    )
    monkeypatch.setattr(repository, "load", concurrent_replacement)
    monkeypatch.setattr(repository, "_conditional_commit", fail_cas)
    monkeypatch.setattr(engine, "execute", fail_agent_execution)
    monkeypatch.setattr(durable_routing, "_route_localfile_run", lambda *_args: status)

    result = worker.run(
        WorkflowContext(page={"project_id": "durable-routing", "page_id": "1"})
    )

    assert load_count == 1
    assert result.context.state == PageState.QUALITY_CHECKED
    assert result.context.artifacts[PageState.QUALITY_CHECKED.value] == {"snapshot": "before"}
    assert result.context.metadata["snapshot"] == "before"
    assert bus.published == []


def test_localfile_worker_status_rederives_state_from_single_replacement_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository(tmp_path)
    bus = MemoryEventBus()
    engine = _engine(bus)
    worker = LocalFileDurableWorkflowWorker(repository, engine)
    replacement = repository.load("durable-routing").replace_page(
        Page(
            page_number=1,
            state=PageState.APPROVED,
            approval={"snapshot": "after"},
            metadata={"snapshot": "after"},
        )
    )
    load_count = 0

    def load_replaced_snapshot(_project_id: str) -> Project:
        nonlocal load_count
        load_count += 1
        return replacement

    def fail_agent_execution(_context: WorkflowContext) -> AgentResult:
        raise AssertionError("status-only worker path executed an agent")

    def fail_cas(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("status-only worker path executed CAS")

    stale_status = WorkflowStatus(
        current_state=PageState.QUALITY_CHECKED,
        current_step="quality",
        executable_step="approve",
    )
    monkeypatch.setattr(repository, "load", load_replaced_snapshot)
    monkeypatch.setattr(repository, "_conditional_commit", fail_cas)
    monkeypatch.setattr(engine, "execute", fail_agent_execution)
    monkeypatch.setattr(durable_routing, "_route_localfile_run", lambda *_args: stale_status)

    result = worker.run(
        WorkflowContext(page={"project_id": "durable-routing", "page_id": "1"})
    )

    assert load_count == 1
    assert result.context.state == PageState.APPROVED
    assert result.current_state == PageState.APPROVED
    assert result.context.artifacts[PageState.APPROVED.value] == {"snapshot": "after"}
    assert result.context.metadata["snapshot"] == "after"
    assert bus.published == []


def test_localfile_coordinator_concurrent_lifecycle_capture_is_operation_isolated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = LocalFileRepository(tmp_path)
    repository.save(Project(id="durable-routing-a", title="A", pages=[Page(page_number=1)]))
    repository.save(Project(id="durable-routing-b", title="B", pages=[Page(page_number=1)]))
    bus = MemoryEventBus()
    coordinator, _batch = build_localfile_durable_workflow(repository, _engine(bus), bus)
    event_factory = coordinator._event_factory
    original_create = event_factory.create
    created_barrier = Barrier(2)
    results: dict[str, ProjectWorkflowResult] = {}
    failures: list[BaseException] = []

    def interleaved_create(event_type: EventType, data: dict[str, str]):
        event = original_create(event_type, data)
        if event_type == EventType.PROJECT_STARTED:
            created_barrier.wait(timeout=5)
        return event

    def run(project_id: str) -> None:
        try:
            results[project_id] = coordinator.run_project(project_id)
        except BaseException as exc:  # pragma: no cover - assertion reports the captured failure.
            failures.append(exc)

    monkeypatch.setattr(event_factory, "create", interleaved_create)
    threads = [
        Thread(target=run, args=(project_id,))
        for project_id in ("durable-routing-a", "durable-routing-b")
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert not any(thread.is_alive() for thread in threads)
    assert failures == []
    assert set(results) == {"durable-routing-a", "durable-routing-b"}
    for project_id, result in results.items():
        assert result.events
        assert {event.data["project_id"] for event in result.events} == {project_id}
    lifecycle_events = [
        event
        for event in bus.published
        if event.event_type in {EventType.PROJECT_STARTED, EventType.PROJECT_COMPLETED}
    ]
    assert sorted(event.data["project_id"] for event in lifecycle_events) == [
        "durable-routing-a",
        "durable-routing-b",
    ]


def test_localfile_batch_uses_fresh_aggregate_mutations_and_completed_resume_is_noop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository(tmp_path)
    bus = MemoryEventBus()
    _coordinator, batch = build_localfile_durable_workflow(repository, _engine(bus), bus)
    _forbid_raw_save(monkeypatch, repository)

    completed = batch.run("durable-routing", batch_id="batch-1")
    event_count = len(bus.published)
    resumed = batch.resume("durable-routing", "batch-1")

    assert isinstance(batch, LocalFileDurableBatchWorkflowEngine)
    assert completed.status.value == resumed.status.value == "completed"
    assert completed.completed == [1]
    assert resumed.completed == [1]
    assert len(bus.published) == event_count
    stored = repository.load("durable-routing").workflow["batches"]["batch-1"]
    assert stored["status"] == "completed"
    assert [event.event_type for event in bus.published if event.event_type == EventType.BATCH_COMPLETED]


def test_logical_output_asset_is_deferred_without_quality_or_batch_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository(tmp_path)
    bus = MemoryEventBus()
    engine = _engine(bus)
    for command in ("design", "review", "storyboard", "prompt", "generate"):
        _route_localfile_primary(engine, repository, "durable-routing", "1", command, {})
    snapshot = repository._load_revisioned("durable-routing")
    page = snapshot.project.page(1).model_copy(
        update={"image": {"artifact_kind": "logical_output_asset", "output_asset_id": "asset:001"}}
    )
    repository._conditional_commit(snapshot, snapshot.project.replace_page(page))
    _coordinator, batch = build_localfile_durable_workflow(repository, engine, bus)
    _forbid_raw_save(monkeypatch, repository)

    result = batch.run("durable-routing", batch_id="batch-deferred")

    assert result.status.value == "failed"
    assert result.failed == [1]
    assert repository.load("durable-routing").page(1).state == PageState.GENERATED
    record = repository.load("durable-routing").workflow["batches"]["batch-deferred"]
    assert record["queue"][0]["error"] == "LOGICAL_OUTPUT_ASSET_QUALITY_GATING_DEFERRED"
    assert not any(event.event_type == EventType.BATCH_COMPLETED for event in bus.published)


def test_cli_runtime_selects_localfile_private_durable_composition(tmp_path: Path) -> None:
    runtime = build_runtime(
        AppConfig(repository=RepositorySettings(driver="local_file", root=tmp_path)), tmp_path
    )

    assert isinstance(runtime.coordinator, LocalFileDurableWorkflowCoordinator)
    assert isinstance(runtime.batch, LocalFileDurableBatchWorkflowEngine)


def test_localfile_create_remains_explicit_non_durable_compatibility_path(tmp_path: Path) -> None:
    repository = LocalFileRepository(tmp_path)
    bus = MemoryEventBus()
    coordinator, _batch = build_localfile_durable_workflow(repository, _engine(bus), bus)

    created = coordinator.create_project("created", "Created")

    assert created.project.id == "created"
    assert repository.load("created").page(1).state == PageState.DRAFT


def test_localfile_project_status_delegates_to_read_only_project_engine(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository(tmp_path)
    bus = MemoryEventBus()
    coordinator, _batch = build_localfile_durable_workflow(repository, _engine(bus), bus)
    before = repository.load("durable-routing")

    def fail_mutation(*_args: object, **_kwargs: object) -> list[object]:
        raise AssertionError("project status must not use durable mutations")

    monkeypatch.setattr(coordinator, "_mutate", fail_mutation)
    status = coordinator.project_status("durable-routing")

    assert status.page_readiness[0].page_number == 1
    assert status.page_readiness[0].next_operation == "design"
    assert status.page_readiness[0].non_execution is True
    assert repository.load("durable-routing") == before
    assert bus.published == []


def test_localfile_and_generic_project_status_have_identical_readiness(tmp_path: Path) -> None:
    repository = _repository(
        tmp_path,
        Page(
            page_number=1,
            state=PageState.REVIEWED,
            page_design={"ready": True},
            review={"ready": True},
        ),
    )
    bus = MemoryEventBus()
    coordinator, _batch = build_localfile_durable_workflow(repository, _engine(bus), bus)
    generic = ProjectWorkflowEngine(repository, bus)

    localfile_status = coordinator.project_status("durable-routing")
    generic_status = generic.status("durable-routing")

    assert localfile_status.page_readiness == generic_status.page_readiness
    assert localfile_status.readiness_summary == generic_status.readiness_summary
    assert localfile_status.readiness_summary is not None
    assert localfile_status.readiness_summary.readiness_outcome == "ACTIONABLE"
    assert localfile_status.readiness_summary.next_actionable_page_number == 1
    assert localfile_status.readiness_summary.next_actionable_page == localfile_status.page_readiness[0]
    assert localfile_status.readiness_summary.readiness_focus_page is localfile_status.readiness_summary.next_actionable_page
    assert localfile_status.model_dump(mode="json") == generic_status.model_dump(mode="json")


@pytest.mark.parametrize(
    ("states", "outcome", "focus_number"),
    [
        ((), "EMPTY", None),
        ((PageState.APPROVED, PageState.APPROVED), "COMPLETE", None),
        ((PageState.DESIGNED, PageState.DESIGNED), "BLOCKED", 1),
        ((PageState.DESIGNED, PageState.APPROVED), "BLOCKED", 2),
        ((PageState.DRAFT, PageState.DRAFT), "ACTIONABLE", 1),
        ((PageState.DRAFT, PageState.DESIGNED), "ACTIONABLE", 2),
    ],
    ids=["empty", "all-terminal", "all-blocked", "terminal-blocked", "actionable", "actionable-blocked"],
)
def test_localfile_runtime_defers_adapter_construction_during_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    states: tuple[PageState, ...], outcome: str, focus_number: int | None,
) -> None:
    repository = LocalFileRepository(tmp_path)
    pages = [
        Page(
            page_number=len(states) - index,
            state=state,
            **(
                {field: {"persisted": True} for field in (
                    "page_design", "review", "storyboard", "prompt", "image", "quality", "approval"
                )}
                if state == PageState.APPROVED else {}
            ),
        )
        for index, state in enumerate(states)
    ]
    # Raw legacy input includes missing evidence that normal writes reject.
    repository._path("durable-routing").parent.mkdir(parents=True, exist_ok=True)
    repository._path("durable-routing").write_text(
        Project(id="durable-routing", title="Durable", pages=pages).model_dump_json(), encoding="utf-8"
    )
    config = tmp_path / "config.yaml"
    config.write_text(f"repository:\n  driver: local_file\n  root: {tmp_path.as_posix()}\n", encoding="utf-8")

    def fail_image_factory(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("status must not construct an image generator")

    def fail_llm_factory(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("status must not construct an LLM provider")

    def fail_external_generation_builder(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("status must not construct the external-generation composition")

    def fail_quality_ledger_builder(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("status must not construct the quality Ledger")

    def fail_mutation(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("status must not mutate the LocalFile repository")

    monkeypatch.setattr(ImageGeneratorFactory, "create", fail_image_factory)
    monkeypatch.setattr(LLMFactory, "create", fail_llm_factory)
    monkeypatch.setattr(
        cli_runtime,
        "build_localfile_external_generation_composition",
        fail_external_generation_builder,
    )
    monkeypatch.setattr(
        mcp_composition,
        "build_localfile_quality_ledger_gate",
        fail_quality_ledger_builder,
    )
    monkeypatch.setattr(LocalFileRepository, "save", fail_mutation)
    monkeypatch.setattr(LocalFileRepository, "delete", fail_mutation)
    monkeypatch.setattr(LocalFileRepository, "_conditional_commit", fail_mutation)
    monkeypatch.setattr(MemoryEventBus, "publish", fail_mutation)
    before = _tree_manifest(tmp_path)
    timestamps = {path: path.stat().st_mtime_ns for path in tmp_path.rglob("*") if path.is_file()}
    runtime = build_runtime(
        AppConfig(repository=RepositorySettings(driver="local_file", root=tmp_path)), tmp_path
    )
    monkeypatch.setattr(runtime.engine, "execute", fail_mutation)
    monkeypatch.setattr(StateMachine, "validate_transition", fail_mutation)
    assert _tree_manifest(tmp_path) == before

    status = runtime.coordinator.project_status("durable-routing")
    assert _tree_manifest(tmp_path) == before
    server = build_mcp_server(
        workflow_engine=runtime.engine,
        workflow_coordinator=runtime.coordinator,
        project_loader=runtime.loader,
        repository=runtime.loader.repository,
    )
    assert _tree_manifest(tmp_path) == before
    mcp_status = server.call_tool("get_project_status", {"project_id": "durable-routing"})
    generic_status = ProjectWorkflowEngine(repository, MemoryEventBus()).status("durable-routing")
    cli_status = CliRunner().invoke(
        app, ["project", "status", "durable-routing", "--config", str(config)]
    )

    assert mcp_status.success is True
    assert cli_status.exit_code == 0, cli_status.stdout
    assert json.loads(cli_status.stdout) == mcp_status.data == generic_status.model_dump(mode="json")
    assert status.readiness_summary is not None
    assert mcp_status.data["readiness_summary"] == status.readiness_summary.model_dump(mode="json")
    summary = status.readiness_summary
    assert summary.readiness_outcome == outcome
    if focus_number is None:
        assert summary.readiness_focus_page is None
    else:
        assert summary.readiness_focus_page is not None
        assert summary.readiness_focus_page.page_number == focus_number
        assert summary.readiness_focus_page is (
            summary.next_actionable_page if outcome == "ACTIONABLE" else summary.first_blocked_page
        )
    assert repository.load("durable-routing").pages == pages
    assert _tree_manifest(tmp_path) == before
    assert {path: path.stat().st_mtime_ns for path in timestamps} == timestamps


def test_localfile_external_generation_composition_resolves_once_at_first_quality_gate_use(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _repository(tmp_path)
    calls = 0
    builder = cli_runtime.build_localfile_external_generation_composition

    def record_builder(
        localfile_repository: LocalFileRepository,
        state_machine: StateMachine,
        event_bus: MemoryEventBus,
    ) -> object:
        nonlocal calls
        calls += 1
        return builder(localfile_repository, state_machine, event_bus)

    monkeypatch.setattr(cli_runtime, "build_localfile_external_generation_composition", record_builder)
    runtime = build_runtime(
        AppConfig(repository=RepositorySettings(driver="local_file", root=tmp_path)), tmp_path
    )
    composition = runtime.localfile_external_generation

    assert composition is not None
    assert calls == 0
    context = WorkflowContext(
        state=PageState.GENERATED,
        page={"project_id": "durable-routing", "page_id": "1"},
        artifacts={
            PageState.GENERATED.value: {
                "artifact_kind": "logical_output_asset",
                "output_asset_id": "output-1",
            }
        },
    )
    assert composition.quality_gate.require_applied(context) == "LOGICAL_OUTPUT_ASSET_QUALITY_PROOF_UNAVAILABLE"
    assert composition.quality_gate.require_applied(context) == "LOGICAL_OUTPUT_ASSET_QUALITY_PROOF_UNAVAILABLE"
    assert calls == 1


def test_mcp_quality_ledger_resolves_once_at_first_quality_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository(
        tmp_path,
        Page(
            page_number=1,
            state=PageState.GENERATED,
            page_design={},
            review={},
            storyboard={},
            prompt={},
            image={"artifact_kind": "logical_output_asset", "output_asset_id": "output-1"},
        ),
    )
    calls = 0
    builder = mcp_composition.build_localfile_quality_ledger_gate

    def record_builder(localfile_repository: LocalFileRepository) -> object:
        nonlocal calls
        calls += 1
        return builder(localfile_repository)

    monkeypatch.setattr(mcp_composition, "build_localfile_quality_ledger_gate", record_builder)
    runtime = build_runtime(
        AppConfig(repository=RepositorySettings(driver="local_file", root=tmp_path)), tmp_path
    )
    server = build_mcp_server(
        workflow_engine=runtime.engine,
        workflow_coordinator=runtime.coordinator,
        project_loader=runtime.loader,
        repository=repository,
    )

    assert server.call_tool("get_project_status", {"project_id": "durable-routing"}).success is True
    assert calls == 0
    assert server.call_tool("review_quality", {"project_id": "durable-routing", "page_number": 1}).success is False
    assert server.call_tool("review_quality", {"project_id": "durable-routing", "page_number": 1}).success is False
    assert calls == 1


def test_localfile_runtime_constructs_configured_adapters_only_on_first_use(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    image_creations = 0
    llm_creations = 0
    image_factory = ImageGeneratorFactory.create
    llm_factory = LLMFactory.create

    def create_image(provider: str, **options: object) -> object:
        nonlocal image_creations
        image_creations += 1
        return image_factory(provider, **options)

    def create_llm(provider: str, **options: object) -> object:
        nonlocal llm_creations
        llm_creations += 1
        return llm_factory(provider, **options)

    monkeypatch.setattr(ImageGeneratorFactory, "create", staticmethod(create_image))
    monkeypatch.setattr(LLMFactory, "create", staticmethod(create_llm))
    runtime = build_runtime(
        AppConfig(repository=RepositorySettings(driver="local_file", root=tmp_path)), tmp_path
    )

    assert (image_creations, llm_creations) == (0, 0)
    runtime.engine.execute(WorkflowContext())
    assert (image_creations, llm_creations) == (0, 1)
    runtime.engine.execute(
        WorkflowContext(
            state=PageState.PROMPT_BUILT,
            artifacts={"PromptBuilt": {"prompt_markdown": "a prompt"}},
        )
    )
    assert (image_creations, llm_creations) == (1, 1)


def test_lazy_adapters_construct_their_delegate_once_under_concurrent_first_use(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image_calls = 0
    image_entered = Event()
    image_second_entered = Event()
    image_release = Event()

    class ImageDelegate:
        def generate(self, prompt: str) -> ImageResult:
            return ImageResult(success=True, provider="test", elapsed_time=0, image_path=prompt)

    def image_factory(_provider: str) -> ImageDelegate:
        nonlocal image_calls
        image_calls += 1
        (image_entered if image_calls == 1 else image_second_entered).set()
        assert image_release.wait(timeout=2)
        return ImageDelegate()

    monkeypatch.setattr(ImageGeneratorFactory, "create", staticmethod(image_factory))
    lazy_image = cli_runtime._LazyImageGenerator("mock")
    image_first = Thread(target=lambda: lazy_image.generate("one"))
    image_second = Thread(target=lambda: lazy_image.generate("two"))
    image_first.start()
    assert image_entered.wait(timeout=2)
    image_second.start()
    assert not image_second_entered.wait(timeout=0.2)
    image_release.set()
    image_first.join(timeout=2)
    image_second.join(timeout=2)
    assert not image_first.is_alive()
    assert not image_second.is_alive()
    assert image_calls == 1

    llm_calls = 0
    llm_entered = Event()
    llm_second_entered = Event()
    llm_release = Event()

    class LLMDelegate:
        def generate(self, request: PromptRequest) -> LLMResult:
            return LLMResult(success=True, provider="test", elapsed_time=0, content=request.user_prompt)

    def llm_factory(_provider: str) -> LLMDelegate:
        nonlocal llm_calls
        llm_calls += 1
        (llm_entered if llm_calls == 1 else llm_second_entered).set()
        assert llm_release.wait(timeout=2)
        return LLMDelegate()

    monkeypatch.setattr(LLMFactory, "create", staticmethod(llm_factory))
    lazy_llm = cli_runtime._LazyLLMProvider("mock")
    request = PromptRequest(user_prompt="hello")
    llm_first = Thread(target=lambda: lazy_llm.generate(request))
    llm_second = Thread(target=lambda: lazy_llm.generate(request))
    llm_first.start()
    assert llm_entered.wait(timeout=2)
    llm_second.start()
    assert not llm_second_entered.wait(timeout=0.2)
    llm_release.set()
    llm_first.join(timeout=2)
    llm_second.join(timeout=2)
    assert not llm_first.is_alive()
    assert not llm_second.is_alive()
    assert llm_calls == 1
