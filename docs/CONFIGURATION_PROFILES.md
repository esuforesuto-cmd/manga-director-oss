# Configuration Profiles

Configuration profiles are resolved only by `manga_director.cli.config`; Core,
Workflow, Agents, and adapters do not branch on a profile.

## Built-in profiles

| Profile | Intended use | Safe defaults |
| --- | --- | --- |
| `development` | local development | `DEBUG` logging |
| `testing` | deterministic test environments | `WARNING` logging |
| `production` | standard deployed process | `INFO` logging |
| `enterprise` | controlled operator configuration | `INFO` logging and `read_only: true` |
| `offline` | no-provider local workflow | mock LLM and image generator |

Select a profile with `profile:` in YAML, `MANGA_DIRECTOR_PROFILE`, or the
optional `load_config(..., profile=...)` argument. The environment has
precedence over YAML. Per-profile YAML overrides live under `profiles:`.

Use `MANGA_DIRECTOR__SECTION__KEY=value` for safe environment overrides, for
example `MANGA_DIRECTOR__REPOSITORY__ROOT=projects`. Existing keys retain their
defaults. `ConfigurationSnapshot`, `configuration_diff`, and
`export_configuration` redact database URLs and secret-like values.

`read_only` is an operator guard for configuration writes; callers can enforce
it with `require_writable_configuration`. It never changes workflow behavior.
