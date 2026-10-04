"""Read-only reliability, recovery, long-running, and readiness DTOs."""

from __future__ import annotations

import json
import tracemalloc
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from manga_director.domain.state_machine import PageState
from manga_director.observability.metrics import MetricsRegistry
from manga_director.observability.runtime import RuntimeDiagnostics
from manga_director.production.operations import (
    BackendManagement,
    OperationalDiagnostics,
    ProviderManagement,
    RuntimeConfiguration,
)
from manga_director.repositories.integrity import (
    IntegrityReport,
    ProjectIntegrityChecker,
    RepositoryCheckReport,
    RepositorySelfCheck,
)
from manga_director.repositories.project_loader import ProjectLoader
from manga_director.repositories.protocols import ProjectRepository
from manga_director.repositories.recovery import RepositoryRecovery
from manga_director.workflow.contracts import WorkflowStatus
from manga_director.workflow.engine import WorkflowEngine


class WorkflowConsistencyReport(BaseModel):
    """Read-only evidence that persisted page state and history agree."""

    project_id: str
    page_number: int = Field(ge=1)
    valid: bool
    current_state: PageState
    executable_step: str | None = None
    errors: list[str] = Field(default_factory=list)


class WorkflowResumeReport(BaseModel):
    """A resume admission decision that never invokes the next workflow step."""

    project_id: str
    page_number: int = Field(ge=1)
    resumable: bool
    consistency: WorkflowConsistencyReport
    integrity: IntegrityReport
    messages: list[str] = Field(default_factory=list)

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def to_markdown(self) -> str:
        return _markdown("Workflow Resume Validation", self.model_dump(mode="json"))


class RecoverySimulationReport(BaseModel):
    """Non-executing recovery plan; it never calls an Agent or persists a change."""

    project_id: str
    page_number: int = Field(ge=1)
    safe_to_resume: bool
    next_step: str | None = None
    persisted_unchanged: bool = True
    messages: list[str] = Field(default_factory=list)


class RecoveryReport(BaseModel):
    """Repository scan, resume validation, and simulation evidence."""

    repository: RepositoryCheckReport
    resume: WorkflowResumeReport
    simulation: RecoverySimulationReport

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def to_markdown(self) -> str:
        return _markdown("Recovery Report", self.model_dump(mode="json"))


class TaskLifecycleSummary(BaseModel):
    """Bounded in-process task counters derived from passive metrics."""

    captured_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    active_tasks: int = Field(ge=0)
    workflow_executions: int = Field(ge=0)
    workflow_errors: int = Field(ge=0)
    batch_executions: int = Field(ge=0)


class MemoryGrowthReport(BaseModel):
    """Optional tracemalloc evidence; tracing is never enabled by this module."""

    tracing_enabled: bool
    current_bytes: int = Field(ge=0)
    peak_bytes: int = Field(ge=0)
    growth_bytes: int = 0


class BatchStabilityReport(BaseModel):
    """Batch execution/error counters and duration summary without controlling Batch."""

    executions: int = Field(ge=0)
    failures: int = Field(ge=0)
    durations: dict[str, Any] = Field(default_factory=dict)


class RuntimeStabilityReport(BaseModel):
    """Long-running operational summary with JSON/Markdown support."""

    tasks: list[TaskLifecycleSummary] = Field(default_factory=list)
    memory: MemoryGrowthReport
    batch: BatchStabilityReport
    graceful_recovery: dict[str, Any] = Field(default_factory=dict)

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def to_markdown(self) -> str:
        return _markdown("Runtime Stability", self.model_dump(mode="json"))


class LongRunningDiagnostics:
    """Bounded, passive runtime stability recorder over existing MetricsRegistry data."""

    def __init__(self, metrics: MetricsRegistry, *, limit: int = 100) -> None:
        if limit < 1:
            raise ValueError("Long-running diagnostics limit must be at least one.")
        self._metrics = metrics
        self._limit = limit
        self._tasks: list[TaskLifecycleSummary] = []
        self._baseline_memory: int | None = None

    def capture(self, *, active_tasks: int = 0, graceful_recovery: Mapping[str, Any] | None = None) -> RuntimeStabilityReport:
        snapshot = self._metrics.snapshot()
        counters = _as_mapping(snapshot.get("counters"))
        task = TaskLifecycleSummary(
            active_tasks=active_tasks,
            workflow_executions=int(counters.get("workflow.executions", 0)),
            workflow_errors=int(counters.get("workflow.errors", 0)),
            batch_executions=int(counters.get("batch.executions", 0)),
        )
        self._tasks = [*self._tasks, task][-self._limit :]
        current, peak, tracing = _memory()
        if self._baseline_memory is None:
            self._baseline_memory = current
        return RuntimeStabilityReport(
            tasks=list(self._tasks),
            memory=MemoryGrowthReport(
                tracing_enabled=tracing,
                current_bytes=current,
                peak_bytes=peak,
                growth_bytes=current - self._baseline_memory,
            ),
            batch=BatchStabilityReport(
                executions=int(counters.get("batch.executions", 0)),
                failures=int(counters.get("batch.failures", 0)),
                durations=_as_mapping(snapshot.get("durations")),
            ),
            graceful_recovery=dict(graceful_recovery or {}),
        )


class ReliabilityDiagnosticsReport(BaseModel):
    """Transport-neutral diagnostics across architecture and operational boundaries."""

    architecture: dict[str, Any] = Field(default_factory=dict)
    dependencies: dict[str, Any] = Field(default_factory=dict)
    plugins: dict[str, Any] = Field(default_factory=dict)
    extensions: dict[str, Any] = Field(default_factory=dict)
    providers: dict[str, Any] = Field(default_factory=dict)
    backends: dict[str, Any] = Field(default_factory=dict)
    configuration: dict[str, Any] = Field(default_factory=dict)
    workflow: dict[str, Any] = Field(default_factory=dict)
    repository: dict[str, Any] = Field(default_factory=dict)

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def to_markdown(self) -> str:
        return _markdown("Reliability Diagnostics", self.model_dump(mode="json"))


class ReliabilityDiagnostics:
    """Compose read-only architecture and runtime diagnostics without delivery dependencies."""

    def __init__(
        self,
        *,
        runtime: RuntimeDiagnostics,
        configuration: RuntimeConfiguration,
        providers: ProviderManagement,
        backends: BackendManagement,
        dependencies: Mapping[str, bool] | None = None,
        plugins: Mapping[str, Any] | None = None,
        extensions: Mapping[str, Any] | None = None,
    ) -> None:
        self._runtime = runtime
        self._configuration = configuration
        self._providers = providers
        self._backends = backends
        self._dependencies = dict(dependencies or {})
        self._plugins = dict(plugins or {})
        self._extensions = dict(extensions or {})

    def report(
        self, *, workflow: Mapping[str, Any] | None = None, repository: Mapping[str, Any] | None = None
    ) -> ReliabilityDiagnosticsReport:
        providers = self._providers.inventory()
        backends = self._backends.inventory()
        configuration = self._configuration.report()
        runtime_report = self._runtime.report(
            plugins=self._plugins,
            extensions=self._extensions,
            configuration=configuration.model_dump(mode="json"),
            repositories=repository,
            providers=providers.model_dump(mode="json"),
            backends=backends.model_dump(mode="json"),
            workflow=workflow,
        )
        return ReliabilityDiagnosticsReport(
            architecture={"core_modified": False, "workflow_scope": "one_page", "state_machine": "authoritative"},
            dependencies=dict(sorted(self._dependencies.items())),
            plugins=runtime_report.plugins,
            extensions=runtime_report.extensions,
            providers=runtime_report.providers,
            backends=runtime_report.backends,
            configuration=runtime_report.configuration,
            workflow=runtime_report.workflow,
            repository=runtime_report.repositories,
        )


class ReliabilityOperations:
    """Validate recovery and consistency through existing Engine/Repository ports only."""

    def __init__(
        self,
        *,
        engine: WorkflowEngine,
        loader: ProjectLoader,
        repository: ProjectRepository,
        checker: ProjectIntegrityChecker | None = None,
    ) -> None:
        self._engine = engine
        self._loader = loader
        self._repository = repository
        self._checker = checker or ProjectIntegrityChecker()
        self._recovery = RepositoryRecovery(repository, self._checker)

    def consistency(self, project_id: str, page_number: int) -> WorkflowConsistencyReport:
        context = self._loader.load(project_id, str(page_number))
        status = self._engine.status(context)
        errors = _history_errors(status, context.state)
        return WorkflowConsistencyReport(
            project_id=project_id,
            page_number=page_number,
            valid=not errors,
            current_state=context.state,
            executable_step=status.executable_step,
            errors=errors,
        )

    def validate_resume(self, project_id: str, page_number: int) -> WorkflowResumeReport:
        integrity = self._recovery.inspect(project_id)
        consistency = self.consistency(project_id, page_number)
        terminal = consistency.current_state == PageState.APPROVED
        resumable = integrity.valid and consistency.valid and not terminal
        messages = []
        if terminal:
            messages.append("Page is approved and has no resumable workflow step.")
        if not integrity.valid:
            messages.extend(integrity.errors)
        messages.extend(consistency.errors)
        return WorkflowResumeReport(
            project_id=project_id,
            page_number=page_number,
            resumable=resumable,
            consistency=consistency,
            integrity=integrity,
            messages=messages,
        )

    def simulate_recovery(self, project_id: str, page_number: int) -> RecoverySimulationReport:
        validation = self.validate_resume(project_id, page_number)
        return RecoverySimulationReport(
            project_id=project_id,
            page_number=page_number,
            safe_to_resume=validation.resumable,
            next_step=validation.consistency.executable_step if validation.resumable else None,
            messages=["Simulation only: no workflow step was executed.", *validation.messages],
        )

    def recovery_report(self, project_id: str, page_number: int) -> RecoveryReport:
        return RecoveryReport(
            repository=RepositorySelfCheck(self._repository, self._checker).check(project_id),
            resume=self.validate_resume(project_id, page_number),
            simulation=self.simulate_recovery(project_id, page_number),
        )


class ReadinessCheck(BaseModel):
    """A concrete production-readiness check and operator-facing remediation text."""

    name: str
    passed: bool
    guidance: str


class ProductionReadinessReport(BaseModel):
    """Readiness checklist for deployment, upgrade, backup, and recovery procedures."""

    ready: bool
    checks: list[ReadinessCheck] = Field(default_factory=list)
    deployment_checklist: list[str] = Field(default_factory=list)
    upgrade_checklist: list[str] = Field(default_factory=list)
    backup_checklist: list[str] = Field(default_factory=list)
    recovery_checklist: list[str] = Field(default_factory=list)

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def to_markdown(self) -> str:
        return _markdown("Production Readiness", self.model_dump(mode="json"))


class ProductionReadiness:
    """Build an operator checklist from validation evidence without changing deployment state."""

    def __init__(
        self,
        *,
        operations: OperationalDiagnostics,
        reliability: ReliabilityOperations,
    ) -> None:
        self._operations = operations
        self._reliability = reliability

    def report(self, project_id: str, page_number: int) -> ProductionReadinessReport:
        operations = self._operations.report(project_id)
        recovery = self._reliability.validate_resume(project_id, page_number)
        checks = [
            ReadinessCheck(
                name="runtime_operations",
                passed=bool(operations.runtime_summary.get("healthy", False)),
                guidance="Resolve configuration, dependency, provider, or backend diagnostics before deployment.",
            ),
            ReadinessCheck(
                name="repository_integrity",
                passed=recovery.integrity.valid,
                guidance="Run repository recovery validation before resuming production work.",
            ),
            ReadinessCheck(
                name="workflow_consistency",
                passed=recovery.consistency.valid,
                guidance="Resolve persisted workflow-history inconsistencies before resuming a page.",
            ),
        ]
        return ProductionReadinessReport(
            ready=all(check.passed for check in checks),
            checks=checks,
            deployment_checklist=["Validate configuration fingerprint.", "Run dependency and health checks."],
            upgrade_checklist=["Validate import compatibility.", "Back up Project data before upgrade."],
            backup_checklist=["Export or back up the Repository.", "Validate a sample Project integrity report."],
            recovery_checklist=["Run recovery simulation.", "Resume only one validated Page step."],
        )


def _history_errors(status: WorkflowStatus, state: PageState) -> list[str]:
    workflow_entries = [item for item in status.workflow_history if item.get("kind") == "workflow"]
    if not workflow_entries:
        return [] if state == PageState.DRAFT else ["Persisted state has no workflow transition history."]
    last_state = workflow_entries[-1].get("to")
    return [] if last_state == state.value else ["Workflow history does not end at the persisted page state."]


def _memory() -> tuple[int, int, bool]:
    if not tracemalloc.is_tracing():
        return 0, 0, False
    current, peak = tracemalloc.get_traced_memory()
    return current, peak, True


def _as_mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _markdown(title: str, values: dict[str, Any]) -> str:
    lines = [f"# {title}", ""]
    for key, value in values.items():
        lines.extend([f"## {key.replace('_', ' ').title()}", "", "```json"])
        lines.append(json.dumps(value, indent=2, default=str))
        lines.extend(["```", ""])
    return "\n".join(lines)
