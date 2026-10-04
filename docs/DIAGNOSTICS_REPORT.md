# Diagnostic Reports

`RuntimeDiagnostics` emits a safe `RuntimeDiagnosticReport` with System,
Performance, Configuration, Plugin, Extension, Repository, and EventBus
sections. Reports support JSON and Markdown without a presentation dependency.

```bash
manga-director diagnostics run --config config.yaml
manga-director diagnostics export --config config.yaml --output diagnostics.json
manga-director diagnostics export --config config.yaml --output diagnostics.md
```

Diagnostics use counts, durations, state names, and configured-mode information.
Do not add secrets, tokens, complete configuration, raw exception traces, or
internal model instances to report sections.

MCP exposes `health_status`, `diagnostics_report`, and `system_summary` as DTO
tools. The existing stdio transport serializes these through `McpToolResult`.
There is no FastAPI runtime in this baseline; its future endpoints should reuse
these same DTOs.
