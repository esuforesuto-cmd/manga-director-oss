# Operational Intelligence Foundation

## Scope

`OperationalIntelligenceFoundationReport` provides a transport-neutral,
read-only set of six domain signal placeholders: Workspace, Agent Platform,
Knowledge, Production, Enterprise, and Decision. It establishes a safe report
shape for later caller-supplied evidence without collecting that evidence.

## Signal semantics

Each `V48OperationalSignalDTO` starts with `status="unknown"`, no supplied
evidence, no freshness assessment, and no telemetry. The foundation reports
the absence of automatic action rather than claiming operational health.

## Boundaries

It cannot collect telemetry, probe a system, monitor, alert, persist, publish,
schedule, change capacity, enforce policy, select a recommendation, approve a
Page, mutate/execute a workflow, retry/recover, call an Agent/Provider, or
contact an external service. CLI, FastAPI, MCP, and Web UI can continue using
their current read-only reporting contracts unchanged.
