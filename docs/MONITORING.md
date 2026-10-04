# Monitoring Backlog

Current observability is local and DTO-based: structured logs, metrics,
tracing/timelines, health reports, diagnostics, and performance summaries.
It observes workflow execution; it does not control it.

v2.4 candidates:

- MON-01: production-safe metric naming/cardinality review.
- MON-02: diagnostic export/retention and redaction policy.
- MON-03: workflow, repository, provider/backend, and configuration health
  operating thresholds using mock/local fixtures.
- MON-04: benchmark recording format with environment metadata and regression
  review.
- MON-05: logging correlation and incident-triage runbook.

Prometheus, Grafana, OpenTelemetry export, cloud monitoring, and real-time
dashboards remain out of scope until separately designed.
