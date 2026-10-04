# Plugin Runtime Foundation

`PluginRuntimeFoundation` accepts the existing `PluginRegistry` through a
small read-only protocol and reports its already-registered contributions.

Use the public production boundary with a caller-owned registry:

```python
from manga_director.plugins import PluginRegistry
from manga_director.production import PluginRuntimeFoundation

report = PluginRuntimeFoundation(PluginRegistry()).report()
```

The report is an inventory only; plugin discovery and lifecycle operations
remain outside the Production layer.

The foundation never discovers, registers, enables, disables, loads, executes,
or removes a plugin. `PluginRegistry`, `PluginManager`, manifests, and the
Extension SDK retain all lifecycle ownership.

## Compatibility

No plugin manifest, capability, permission, lifecycle, CLI, FastAPI, MCP, or
SDK contract changes are required. Supplying no registry yields an empty,
read-only report.
