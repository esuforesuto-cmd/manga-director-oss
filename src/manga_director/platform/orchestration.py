"""Declarative unified runtime orchestration without module activation."""

from __future__ import annotations

from pydantic import Field

from manga_director.platform.runtime import (
    UnifiedRuntimeFoundationReport,
    UnifiedRuntimeFoundationService,
    UnifiedRuntimeModuleDTO,
)
from manga_director.production.director import DirectorModel


class UnifiedRuntimeStageDTO(DirectorModel):
    stage_index: int = Field(ge=0)
    module_ids: tuple[str, ...]
    dependencies_satisfied: bool = True
    modules_activated: bool = False


class UnifiedRuntimeOrchestrationReport(DirectorModel):
    runtime: UnifiedRuntimeFoundationReport
    stages: tuple[UnifiedRuntimeStageDTO, ...]
    dependency_order_valid: bool = True
    runtime_entry_points_replaced: bool = False
    routing_performed: bool = False
    planning_only: bool = True


class UnifiedRuntimeOrchestrationService:
    """Produces dependency order only; it cannot start or route a module."""

    def __init__(self, runtime: UnifiedRuntimeFoundationService | None = None) -> None:
        self._runtime = runtime or UnifiedRuntimeFoundationService()

    def plan(
        self, runtime: UnifiedRuntimeFoundationReport | None = None
    ) -> UnifiedRuntimeOrchestrationReport:
        report = runtime or self._runtime.report()
        stages = _dependency_stages(report.modules)
        return UnifiedRuntimeOrchestrationReport(runtime=report, stages=stages)


def _dependency_stages(
    modules: tuple[UnifiedRuntimeModuleDTO, ...],
) -> tuple[UnifiedRuntimeStageDTO, ...]:
    pending = {module.module_id: module for module in modules}
    resolved: set[str] = set()
    stages: list[UnifiedRuntimeStageDTO] = []
    while pending:
        available = tuple(
            module_id
            for module_id, module in sorted(pending.items())
            if set(module.dependency_module_ids).issubset(resolved)
        )
        if not available:
            raise ValueError("unified runtime dependencies contain a cycle or an unknown module")
        stages.append(UnifiedRuntimeStageDTO(stage_index=len(stages), module_ids=available))
        resolved.update(available)
        for module_id in available:
            del pending[module_id]
    return tuple(stages)

