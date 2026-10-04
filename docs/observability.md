# Observability

The optional `WorkflowObserver` records metrics, trace/correlation IDs, and a
state timeline without making workflow decisions. `Diagnostics` produces a
portable report; no external telemetry exporter is required.

## v4.1 multi-agent foundation

`V41PlatformAssuranceService.observability()` adds immutable Agent Metrics,
Execution Trace, Event Timeline, Collaboration Metrics, and Runtime Dashboard
DTOs. They inspect only the local registry and supplied one-page
`WorkflowContext`.

Collection, remote export, trace persistence, event dispatch, monitoring, and
agent execution observation are disabled. These DTOs cannot initiate agents,
transport events, modify workflow state, or retain telemetry.
