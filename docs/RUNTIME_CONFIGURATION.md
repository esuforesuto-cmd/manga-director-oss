# Runtime Configuration

`RuntimeConfiguration` is an Application-layer facade over the stable
Configuration API. It adds no new configuration format and does not mutate
configuration. It provides safe configuration validation, a redacted snapshot,
comparison, stable fingerprint, JSON/YAML export, and import validation.

```python
from manga_director.cli.config import AppConfig
from manga_director.production import RuntimeConfiguration

runtime = RuntimeConfiguration(AppConfig(profile="production"))
snapshot = runtime.snapshot()
assert runtime.validate_import(runtime.export("json"), "json").valid
```

Exported snapshots redact sensitive values, including database URLs. Import
validation parses and validates a candidate only; it never writes a file,
changes environment variables, reloads a process, or applies a configuration.
Use `compare()` and `fingerprint()` as review evidence before a controlled
deployment change.
