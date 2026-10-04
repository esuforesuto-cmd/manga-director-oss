# Module Composition Engine Foundation

`ModuleCompositionEngineFoundation` composes a registry, Feature Packs, one
Platform Profile, and Solution Templates into a `ModuleCompositionReport`.
It reports validity and missing references without repairing metadata or
activating anything.

```python
from manga_director.platform import ModuleCompositionEngineFoundation

report = ModuleCompositionEngineFoundation().preview(request)
assert report.summary.workflow_mutated is False
assert report.summary.services_invoked is False
assert report.summary.state_machine_authoritative is True
```

The engine is available as `UnifiedSDKFoundation.composition_preview()` for
opt-in typed use. It does not add CLI, FastAPI/REST, MCP, or Web UI routes;
current routes and contracts remain unchanged.
