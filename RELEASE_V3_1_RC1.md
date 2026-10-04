# manga-director v3.1.0 RC1

## Overview

`3.1.0rc1` is the v3.1 release candidate. It consolidates additive,
diagnostic-only foundations for Creative Collaboration, Knowledge Evolution,
Operations Platform, Developer Productivity, Creative Review, Knowledge
Analytics, Operations Intelligence, and Release Quality. It adds no autonomous
AI, automatic review/approval, workflow dispatch, Provider/Backend, cloud,
marketplace, distributed runtime, or breaking change.

## Highlights

- Human-owned collaboration workspaces, review assignments, and approval
  evidence remain advisory and one-Page scoped.
- Knowledge version/snapshot/timeline and analytics/reliability reports remain
  Repository-port-based, bounded, and metadata-value-redacted.
- Operations, developer, governance, readiness, compatibility, and release
  reports are transport-neutral DTOs that cannot operate, configure, deploy,
  publish, repair, or authorize.
- CLI, optional FastAPI, MCP, and Web UI seams render the shared DTOs without
  duplicating StateMachine rules.

## Production and performance

Provider-free benchmark smoke covers Creative Planning, Knowledge, Operations,
Developer Productivity, workflow, repository, diagnostics, reporting, and
health paths. Reliability, integrity, recovery, configuration, release, and
production reports remain local and read-only.

## Compatibility

v1.x through v3.0 Python API, CLI, FastAPI/REST DTO, MCP, Workflow,
Repository, Knowledge/Creative/Review/Operations/Diagnostics/Reporting APIs,
Plugin API, Extension SDK, Provider API, Image Backend API, Automation,
Notification, and Health contracts are retained. Python, MCP, optional OpenAPI,
and SBOM use `3.1.0rc1`; the frontend uses `3.1.0-rc.1`.

## Known issues

- Hosted CI, dependency/CVE audit, secret scan, and publication verification
  must run on the exact `v3.1.0rc1` tag before prerelease publication.
- Non-mock adapters, autonomous AI, automatic approval, cloud monitoring,
  distributed runtime, and marketplace capability remain out of scope.

## Before the stable release

1. Accept corrective RC feedback only; do not expand scope.
2. Confirm hosted backend, frontend, docs, package, security, release, nightly,
   benchmark, Creative, Knowledge, Operations, DX, diagnostics, production, and
   enterprise jobs.
3. Promote reviewed metadata to `3.1.0` only after RC feedback is resolved.

## GitHub Release body

Use this document as the GitHub prerelease body for tag `v3.1.0rc1` after hosted
checks and publication-time security scans succeed.
