# Platform Observability

## Scope

`observability()` produces an immutable observation DTO over the supplied
Unified Dashboard. It describes report visibility and explicitly requires
evidence; it does not inspect a running process or collect operational data.

## Boundary

All collection, probes, monitoring, alerts, persistence, and publication flags
remain false. The report is neither a telemetry client nor a monitoring
service, and it cannot take an operational action, change a Workflow, or alter
Runtime behavior.
