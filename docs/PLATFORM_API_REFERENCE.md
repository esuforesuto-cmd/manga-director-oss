# Platform API v1

## Stability commitment

The following additive v5.7 Application-layer services and DTO reports are
frozen for the v5.x maintenance line. They accept caller-supplied, exactly-one
page `WorkflowContext` evidence and return read-only Pydantic DTOs.

## Foundation

`V57ProductionPlatformFoundationService` exposes `workspace`, `project`,
`assets`, `automation`, `plugin_runtime`, and `foundation` reports.
`PluginRuntimeFoundation.report` provides the lower-level Plugin inventory
projection.

## Workspace

`V57ProductionWorkspaceService` exposes `asset_registry`, `project_workspace`,
`workflow_state`, `resources`, `templates`, `production_session`, and
`production_workspace` reports. `ResourceAllocationDTO` and
`ProductionTemplateDTO` are caller-supplied descriptors.

## Production orchestration

`V57ProductionOrchestrator` exposes `automation_pipeline`, `plugin_lifecycle`,
`event_bus`, `task_scheduler`, `workspace_snapshot`, `analytics`, and
`production_platform` reports. `PluginLifecycleDescriptorDTO` is an
observational input. `ProductionOrchestratorReport` is the composed final DTO.

## Compatibility boundary

These APIs do not replace workflow, repository, EventBus, scheduler, Plugin,
or delivery APIs. State transitions remain exclusively under the StateMachine.

## v6.0 Platform API v1.0

v6.0 freezes the additive `manga_director.production` Platform Kernel surface:
`V60CreativeProductionPlatformFoundationService`,
`V60CreativeProductionPlatformIntelligenceService`, and
`V60CreativeProductionPlatformCoreService`, together with their exported DTOs.
The core service exposes `unified_context_manager`, `extension_framework`,
`sdk_foundation`, `marketplace_framework`, `policy_engine`,
`governance_framework`, `observability_platform`, `platform_kernel`, and
`platform_core`.

All inputs are caller-supplied, one-Page `WorkflowContext` evidence or
immutable DTO descriptors. The surface returns read-only Pydantic reports; it
does not replace v5.x APIs or acquire ownership of workflow, repository,
runtime, Plugin, or Marketplace state. StateMachine transitions remain the
exclusive workflow authority.
