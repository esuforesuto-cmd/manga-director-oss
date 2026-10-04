# Plugin Manifest

Each plugin directory contains a UTF-8 YAML file named `plugin.yaml`.

```yaml
name: studio-agent
version: 1.0.0
description: Adds a support-only editorial check.
entry_point: studio_agent:StudioAgentPlugin
dependencies: []
enabled: true
```

## Fields

| Field | Required | Meaning |
| --- | --- | --- |
| `name` | yes | Unique plugin name. It starts with a letter and may contain letters, digits, `.`, `_`, and `-`. |
| `version` | yes | Non-empty plugin version; it must match the instantiated plugin. |
| `description` | no | Human-readable metadata shown by `plugin list` and `plugin info`. |
| `entry_point` | yes | `module:attribute` that resolves to a zero-argument plugin class or factory. |
| `dependencies` | yes | List of plugin names that must be installed and enabled. |
| `enabled` | yes | Whether the plugin is activated by a new runtime process. |

Discovery scans `plugins/plugin.yaml` and direct-child manifests such as `plugins/studio-agent/plugin.yaml`. Installable plugins must use the direct-child form so that `plugin remove` can validate its exact deletion target.

## Dependency rules

Dependencies are resolved before a plugin is imported. A missing dependency, a disabled dependency, or a cycle rejects startup. Dependency versions are not yet expressed in the manifest; version ranges require a separately reviewed plugin API versioning policy.

## Local CLI management

```text
manga-director plugin install --source ./my-plugin
manga-director plugin list
manga-director plugin info studio-agent
manga-director plugin disable studio-agent
manga-director plugin enable studio-agent
manga-director plugin remove studio-agent
```

`install` only copies a local directory containing `plugin.yaml`. It never downloads code. `enable` and `disable` modify only the manifest flag. A running process is unaffected; hot reload is intentionally unsupported.
