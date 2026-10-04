# Developer Productivity

`DevelopmentDiagnostics` produces JSON and Markdown DTOs for a checkout without
reading environment secrets or executing build tools. It reports:

- development environment and workspace layout;
- declared runtime, optional, and build dependencies;
- build backend, dynamic version source, and source-distribution documentation
  inclusion; and
- workspace validation for source, tests, docs, examples, README, and metadata.

Use it with the normal Makefile/Taskfile quality commands. It is an evidence
report, not a replacement for Ruff, mypy, pytest, package build, or hosted CI.

## v3.1 template foundation

`V31FoundationService.developer_productivity()` adds read-only descriptors for
a Project brief, a one-Page planning outline, workflow-guard review checks, and
a human collaboration workspace. `TemplateSummary` and
`DeveloperProductivityReport` make those descriptors available without creating
files, validating a workflow, or persisting workspace data.

- CLI: `manga-director director developer-productivity`
- FastAPI: `GET /v3.1/developer-productivity`
- MCP: `developer_productivity`

See the [template example](../examples/developer_productivity/run.py). A future
template generator must be introduced as a separately reviewed, explicit user
action; this foundation has no filesystem authority.
