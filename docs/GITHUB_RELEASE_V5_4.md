# GitHub Release Notes — v5.4.0

## Creative Quality Framework complete

v5.4.0 completes the optional Creative Quality Framework with quality, review, validation, metrics, readiness, intelligence, governance, audit, reliability, and lifecycle reporting.

This is a diagnostic, human-gated framework. It does not auto-approve work, mutate workflows, run CI/CD, enforce policies, or publish releases.

## Compatibility

v5.4.0 retains v5.0 LTS and v5.3 compatibility for the Python API, CLI, FastAPI/REST, MCP, Web UI, Repository, Workflow, Extension SDK, providers, and backends. No data migration is required.

## Upgrade

Upgrade normally, then optionally use the additive quality report APIs. See the [migration guide](MIGRATION_V5_3_TO_V5_4.md) and [release notes](../RELEASE_V5_4.md).

## Maintainer checklist

Before publishing, run the approved external CVE audit, protected CI, artifact signing, tag creation, and PyPI upload.
