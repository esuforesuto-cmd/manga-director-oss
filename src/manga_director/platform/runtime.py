"""Declarative v5 unified runtime foundation without dynamic runtime behavior."""

from __future__ import annotations

from pydantic import Field

from manga_director.production.director import DirectorModel


class UnifiedRuntimeModuleDTO(DirectorModel):
    module_id: str
    owner_layer: str
    dependency_module_ids: tuple[str, ...] = ()
    public_contract_preserved: bool = True
    dynamically_loaded: bool = False
    runtime_replaced: bool = False


class UnifiedRuntimeSummary(DirectorModel):
    module_count: int = Field(default=0, ge=0)
    routing_enabled: bool = False
    scheduling_enabled: bool = False
    automatic_action_taken: bool = False


class UnifiedRuntimeFoundationReport(DirectorModel):
    modules: tuple[UnifiedRuntimeModuleDTO, ...]
    summary: UnifiedRuntimeSummary
    planning_only: bool = True


class UnifiedRuntimeFoundationService:
    """Returns static dependency descriptors; it never activates a module."""

    def report(self) -> UnifiedRuntimeFoundationReport:
        modules = (
            UnifiedRuntimeModuleDTO(module_id="core", owner_layer="domain"),
            UnifiedRuntimeModuleDTO(
                module_id="workspace", owner_layer="application", dependency_module_ids=("core",)
            ),
            UnifiedRuntimeModuleDTO(
                module_id="knowledge", owner_layer="knowledge", dependency_module_ids=("core",)
            ),
            UnifiedRuntimeModuleDTO(
                module_id="agent-platform",
                owner_layer="application",
                dependency_module_ids=("core", "workspace"),
            ),
            UnifiedRuntimeModuleDTO(
                module_id="production",
                owner_layer="application",
                dependency_module_ids=("core", "knowledge"),
            ),
            UnifiedRuntimeModuleDTO(
                module_id="enterprise", owner_layer="application", dependency_module_ids=("production",)
            ),
            UnifiedRuntimeModuleDTO(
                module_id="decision",
                owner_layer="application",
                dependency_module_ids=("workspace", "knowledge", "production"),
            ),
            UnifiedRuntimeModuleDTO(
                module_id="ecosystem", owner_layer="application", dependency_module_ids=("enterprise",)
            ),
        )
        return UnifiedRuntimeFoundationReport(
            modules=modules, summary=UnifiedRuntimeSummary(module_count=len(modules))
        )

