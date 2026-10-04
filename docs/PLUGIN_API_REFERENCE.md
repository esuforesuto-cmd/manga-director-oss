# Plugin API v1

## Stable Plugin SDK surface

The existing Plugin API is frozen for v5.7: `Plugin`, `PluginType`,
`PluginManifest`, `PluginContribution`, `PluginRegistry`, `PluginLoader`,
`PluginManager`, `PluginStatus`, `PluginDiscovery`, and
`apply_agent_plugins` / `apply_llm_plugins` / `apply_image_generator_plugins`.

Plugin authors should import this stable surface from `manga_director.plugins`:

```python
from manga_director.plugins import Plugin, PluginRegistry, PluginType
```

`Plugin` supplies the lifecycle contract, `PluginRegistry` owns typed
contributions, and `PluginType` selects the supported contribution category.
The detailed manifest and lifecycle guidance remains in
[`docs/plugins/plugin_api.md`](plugins/plugin_api.md).

## v5.7 integration boundary

Production Platform accepts `PluginRuntimeSource` and
`PluginLifecycleDescriptorDTO` only to summarize caller-supplied information.
It never loads, enables, disables, starts, stops, installs, or removes a
Plugin. `PluginManager` remains the lifecycle authority.

## Compatibility promise

Existing manifests, registries, loading behavior, extension SDK contracts, CLI,
FastAPI/REST, MCP, and Web UI integration remain unchanged. Plugin authors do
not need a v5.7 migration.
