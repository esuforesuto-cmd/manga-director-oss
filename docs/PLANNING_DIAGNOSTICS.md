# Planning Diagnostics

Planning diagnostics are portable Pydantic DTOs. A `PlanningSummary` includes:

- workflow planning and execution preview;
- workflow intelligence and the remaining transition graph;
- named dependency and capability reports;
- metadata-only Provider selection, relative latency, unknown cost, and a
  declarative fallback recommendation;
- redacted configuration shape and an architecture-boundary preview.

Each DTO supports `to_json()` and `to_markdown()`. Reports contain no provider
response, secret value, internal exception, or persisted mutation.

Delivery adapters expose only previews:

- CLI: `manga-director planning preview`, `planning provider`, `planning
  configuration`, and `planning architecture`.
- FastAPI composition: `GET /planning` and `GET /planning/providers` when the
  optional callbacks are injected.
- MCP composition: `planning_summary` and `provider_selection`.

These endpoints are deliberately independent from workflow execution commands.

