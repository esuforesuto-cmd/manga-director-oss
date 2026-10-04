# Diagnostics

`RuntimeDiagnostics` and `EnterpriseDiagnostics` compose transport-neutral
reports for system, performance, providers, backends, configuration, workflow,
and repository boundaries. Both expose JSON and Markdown output without
logging secrets or exposing implementation objects.

Use `manga-director diagnostics run` or `diagnostics report` to inspect the
runtime, and `diagnostics export --output report.json` (or `.md`) to produce a
safe release artifact.
