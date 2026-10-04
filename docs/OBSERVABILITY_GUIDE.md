# Observability Guide

The v2.4 production runtime builds on the in-process `MetricsRegistry` without
adding exporters or presentation dependencies. `ProductionMetrics` groups
existing metric names into stable DTO categories:

- startup and runtime;
- workflow and repository;
- provider and image backend;
- automation and notification;
- performance duration summaries.

Applications can increment or observe names in those namespaces, then render a
`ProductionMetricsReport` as JSON or Markdown. The registry stores counters and
bounded duration summaries only; it does not retain workflow payloads,
prompts, credentials, images, or complete event history.

`ProductionRuntimeReport` combines startup evidence, metrics, dependencies,
provider/backend discovery reports, and a redacted configuration mapping. Use
it for local operational diagnosis, not as a replacement for a metrics backend.

External monitoring, Prometheus, OpenTelemetry exporting, cloud monitoring,
alert routing, and continuous remote probes remain out of scope.
