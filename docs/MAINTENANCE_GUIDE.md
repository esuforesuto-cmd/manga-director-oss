# Maintenance Guide

`ReleaseReadiness.maintenance_report()` combines declared dependency lifecycle
information, the technical-debt register, repository health, lifecycle context,
and diagnostic-only recommendations. It does not delete data, update packages,
or perform remote checks.

Run repository integrity checks before a workflow resume. Review cleanup
candidates manually because repository cleanup reports are intentionally
non-destructive. Record measured work in [Technical Debt](TECH_DEBT.md) and
keep provider, backend, and database changes behind their established ports.

For day-to-day checks, see [Repository Maintenance](REPOSITORY_MAINTENANCE.md)
and [Quality Pipeline](QUALITY_PIPELINE.md).
