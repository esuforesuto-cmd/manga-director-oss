"""Composition helpers shared by local MCP and HTTP delivery adapters."""

from __future__ import annotations

from collections.abc import Callable
from threading import Lock

from manga_director.application.workflow import WorkflowApplicationService
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.repositories.project_loader import ProjectLoader
from manga_director.repositories.protocols import ProjectRepository
from manga_director.workflow.contracts import WorkflowContext
from manga_director.workflow.coordinator import WorkflowCoordinator
from manga_director.workflow.durable_execution import LogicalOutputAssetQualityGatePort
from manga_director.workflow.engine import WorkflowEngine
from manga_director.workflow.localfile_external_generated_application import (
    build_localfile_quality_ledger_gate,
)


class _LazyLocalFileQualityGate:
    """Build the LocalFile quality ledger only when execution reaches Quality."""

    def __init__(
        self,
        repository: LocalFileRepository,
        factory: Callable[[LocalFileRepository], LogicalOutputAssetQualityGatePort],
    ) -> None:
        self._repository = repository
        self._factory = factory
        self._delegate: LogicalOutputAssetQualityGatePort | None = None
        self._lock = Lock()

    def require_applied(self, context: WorkflowContext) -> str | None:
        return self._resolve().require_applied(context)

    def _resolve(self) -> LogicalOutputAssetQualityGatePort:
        if self._delegate is None:
            with self._lock:
                if self._delegate is None:
                    self._delegate = self._factory(self._repository)
        return self._delegate


def build_workflow_application(
    *,
    workflow_engine: WorkflowEngine,
    workflow_coordinator: WorkflowCoordinator,
    project_loader: ProjectLoader,
    repository: ProjectRepository,
    localfile_quality_gate_factory: Callable[
        [LocalFileRepository], LogicalOutputAssetQualityGatePort
    ] = build_localfile_quality_ledger_gate,
) -> WorkflowApplicationService:
    """Compose the shared use cases without importing a delivery transport."""

    localfile_quality_gate = (
        _LazyLocalFileQualityGate(repository, localfile_quality_gate_factory)
        if isinstance(repository, LocalFileRepository)
        else None
    )
    return WorkflowApplicationService(
        workflow_engine,
        workflow_coordinator,
        project_loader,
        repository,
        localfile_quality_gate=localfile_quality_gate,
    )
