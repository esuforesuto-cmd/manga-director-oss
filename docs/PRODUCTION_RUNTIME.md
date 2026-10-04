# Production Runtime

`manga_director.production.ProductionRuntime` is an optional Application-layer
orchestrator for local startup and shutdown. It does not call a workflow,
agent, generator, or provider `generate` method, and it is not part of the
public Core API.

## Startup

`start()` runs deterministic, injected boundary checks, validates the supplied
configuration-governance mapping, warms the registered Provider and Image
Backend lifecycle facades, and returns an immutable `StartupReport`. The report
contains only DTO data and renders as JSON or Markdown.

Startup reaches readiness only when configuration reports `compatible` and
`integrity_valid`, all supplied dependency checks pass, and both local adapter
warmups are healthy. A failed check makes readiness false; it never changes a
Project or Page workflow state.

## Shutdown

`shutdown()` runs registered cleanup hooks in reverse registration order and
then closes backend and provider lifecycle handles. Cleanup failures are kept in
`ShutdownReport`; cleanup continues, so one optional boundary cannot prevent
other local handles from closing.

Graceful shutdown is intentionally process-local. Signals, service managers,
network probes, distributed coordination, and cloud monitoring are outside the
current boundary.

## Dependency injection

The runtime receives configuration and dependency probes as callables. It never
imports CLI configuration or a concrete Repository implementation. Applications
should inject only safe, bounded probes, for example a Repository self-check or
a database connection validation.

See [Startup Sequence](STARTUP_SEQUENCE.md), [Health Monitoring](HEALTH_MONITORING.md),
and [Observability Guide](OBSERVABILITY_GUIDE.md).
