# AI Workflow Diagnostics

## v2.7 Director and Knowledge diagnostics

`DirectorReliabilityService` adds read-only Director, Knowledge, planning,
workflow, and architecture sections. The reports serialize with the common
DTO `to_json()` and `to_markdown()` methods and contain no internal repository
models, secret values, or hidden reasoning.

Use `manga-director director diagnostics --project <id> --page <number>`, the
optional FastAPI `/director/diagnostics` route, or MCP
`ai_workflow_diagnostics`. Each is a delivery adapter around the same
application DTO; none can execute, schedule, approve, or persist work.

AI workflow diagnostics provide DTO-only workflow health, planning, dependency,
execution-readiness, architecture, and executive-summary evidence. Executive
dashboard DTOs include workflow, Provider, enterprise, operations, and release
views without implementing a Web UI or presentation logic.

Delivery adapters receive callbacks rather than internal models:

- CLI: `manga-director assurance diagnostics` and `assurance dashboard`.
- FastAPI composition: `/assurance/workflow`, `/assurance/providers`, and
  `/assurance/dashboard`.
- MCP composition: `workflow_reliability`, `provider_governance`, and
  `executive_dashboard`.

All outputs support JSON and Markdown through their DTOs. They cannot launch a
workflow, enable automatic action, publish a release, or approve a Page.
