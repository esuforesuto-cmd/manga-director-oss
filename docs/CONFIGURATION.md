# Configuration Runtime

`load_config(path)` keeps its existing API and validates `config.yaml` with
`AppConfig`. It now caches an immutable validated result while the file and any
referenced `${ENVIRONMENT_VARIABLE}` values are unchanged. A file or referenced
environment change creates a fresh validated result automatically.

Nested optional sections are merged with `AppConfig` defaults before validation,
so a partial `repository:` block retains its unspecified defaults.

```yaml
repository:
  root: ${MANGA_DIRECTOR_PROJECT_ROOT}
```

Use `clear_config_cache(path)` after a controlled reload, and
`configuration_diagnostics(path)` to inspect cache state without exposing
configuration values or secrets. Do not put credentials in `config.yaml`; use
the existing Secret Manager/environment-variable boundary.
