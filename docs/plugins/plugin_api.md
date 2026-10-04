# Plugin API

Plugins are local Python extensions. They add capabilities through `PluginRegistry`; they do not import `WorkflowEngine` internals or alter the page state machine.

## Lifecycle

```text
discover plugin.yaml → resolve dependencies → initialize() → register(registry)
→ use contributed capability → shutdown()
```

`PluginManager` invokes enabled plugins in dependency order and stops active plugins in reverse order. If initialization or registration fails, that plugin's partial contributions are removed and it is shut down. The workflow never advances because of a plugin lifecycle failure.

## Interface

```python
from manga_director.plugins import Plugin, PluginRegistry


class ExamplePlugin(Plugin):
    name = "example"
    version = "1.0.0"
    description = "An example local extension"

    def initialize(self) -> None:
        pass

    def register(self, registry: PluginRegistry) -> None:
        pass

    def shutdown(self) -> None:
        pass
```

The values of `name` and `version` must exactly match the manifest. Plugins must release only their own resources in `shutdown()`.

## Registry

`PluginRegistry` provides `register()`, `unregister()`, `find()`, and `list()`. Every contribution has a plugin type, a name unique within that type, an opaque value, the owner plugin name, and optional metadata.

Supported types are `agent`, `workflow`, `repository`, `image_generator`, `llm`, `prompt`, `cli`, and `event_bus`.

```python
from manga_director.plugins import PluginType

registry.register(
    PluginType.PROMPT,
    "studio-layout",
    template,
    plugin_name=self.name,
    metadata={"template_version": "1"},
)
```

The registry does not discover code, pick providers, invoke agents, or validate page transitions. It is deliberately an outer extension mechanism.

## Safe Agent contributions

Agent plugins are support agents by default. Register an agent instance or a zero-argument factory with `role: support` and an optional `command` metadata value. The CLI/runtime maps that command to `WorkflowEngine.execute_support()`.

Replacing a built-in primary agent is deliberately explicit: metadata must set `role: primary`, a valid existing `state`, and `replace: true`. The page StateMachine still validates every transition and the plugin cannot add, skip, or auto-approve workflow states.

## Image provider contributions

Register a zero-argument image-generator builder under `image_generator`. The composition root adds it to `ImageGeneratorFactory`; `ImageAgent` still calls only `generate(prompt)` and never branches on provider name.

LLM contributions are also applied to `LLMFactory` by the CLI composition root. Other contribution types are registered and inspectable now; their runtime composition belongs to later v2 features such as higher workflows and durable event buses.

## Compatibility and limits

- v1 public APIs and the existing Page `WorkflowEngine` stay unchanged.
- A duplicate `(type, name)` is rejected; plugins cannot silently replace one another.
- Remote installation, marketplace discovery, hot reload, and GUI management are intentionally not implemented.
- Plugins are local code. Treat them as trusted code until process isolation and capability restrictions are designed for a later release.
