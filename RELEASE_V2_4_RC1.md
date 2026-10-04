# manga-director v2.4.0 RC1

## Overview

v2.4.0rc1 is the release candidate for the v2.4 stable line. It packages the
reviewed Production Runtime, operations, reliability, observability, Provider/
Backend runtime, Enterprise configuration, and OSS quality work without adding
a workflow stage or changing an existing public contract.

## Improvements

- Production startup/readiness/liveness, graceful shutdown, and transport-safe
  runtime metrics/reports remain outside Core workflow execution.
- Runtime configuration supports redacted snapshots, comparison, fingerprint,
  export, and validation-only import review.
- Provider and Image Backend inventories expose metadata, capabilities, local
  construction health, presets, priority diagnostics, and compatibility evidence.
- Repository-backed bounded health history, recovery admission/simulation,
  long-running stability summaries, and Production Readiness checklists improve
  controlled operation.

## Production, observability, reliability, and diagnostics

All new operations are DTO-only diagnostic facades. They cannot execute an
Agent, transition a Page, approve work, generate an image, or repair persisted
data. The StateMachine remains authoritative for one-page workflow legality.

## Enterprise and performance

Configuration profiles/governance, repository scalability, provider/backend
lifecycle, integrity, health, diagnostics, and release readiness are covered by
mock/local tests. Provider-free benchmark smoke covers workflow, repository,
provider/backend runtime, configuration, production operations, recovery, and
long-running diagnostics.

## Compatibility

v1.x, v2.0.x, v2.1.x, v2.2.x, and v2.3.x Python API, CLI, FastAPI, REST DTO,
MCP, Workflow, Repository, Plugin API, Extension SDK, Provider API, Backend API,
Automation, Notification, Diagnostics, and Health contracts are retained. See
[the compatibility audit](docs/COMPATIBILITY_V2_4_RC1.md).

Python, MCP, optional OpenAPI, and SBOM use `2.4.0rc1`; the npm frontend uses
the equivalent `2.4.0-rc.1` prerelease form.

## Known issues

- Non-mock Provider and Image Backend adapters remain intentional API-boundary stubs.
- FastAPI remains an optional observability DTO adapter, not a workflow REST API.
- Cloud monitoring, remote health probes, live provider fallback, distributed
  runtime, remote plugin delivery, and marketplace capabilities are out of scope.

## Before stable release

1. Accept only corrective RC feedback; do not expand scope.
2. Confirm hosted backend, frontend, docs, package, security, release, nightly,
   benchmark, diagnostics, production, and enterprise CI jobs for the RC tag.
3. Promote reviewed metadata to `2.4.0`, regenerate release assets, then publish
   the approved tag and artifacts.

## GitHub Release body

Use this document as the GitHub prerelease body for tag `v2.4.0rc1` after hosted
checks and publication-time security scans succeed.
