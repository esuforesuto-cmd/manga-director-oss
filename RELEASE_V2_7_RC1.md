# manga-director v2.7.0 RC1

## Overview

v2.7.0rc1 is the release candidate for the v2.7 stable line. It packages the
reviewed AI Director, Knowledge Intelligence, Workflow Orchestration, and
Enterprise AI advisory facilities without changing the Core workflow,
introducing a provider/backend, or modifying a documented public contract.

## AI Director improvements

- Director planning provides a StateMachine-derived, one-page execution
  strategy, bounded public decision trace, dependency graph, and readiness
  analysis.
- Director Reliability adds integrity, consistency, trace, and readiness
  validation that cannot invoke an Agent or execute a command.

## Knowledge improvements

- Knowledge snapshots, summaries, searches, relationships, coverage,
  consistency, and governance reports are derived through `ProjectRepository`.
- Projections expose metadata keys only; metadata values, retention policy,
  persistence mutation, and semantic retrieval remain out of scope.

## Workflow Orchestration and Enterprise AI

- Workflow plans, execution previews, task grouping, analysis, optimization,
  diagnostics, and dashboards are visualization and recommendation DTOs only.
- Enterprise AI readiness evaluates knowledge, workflow, configuration,
  operations, and governance as a checklist; it cannot deploy, repair, resume,
  or schedule work.

## Production and performance

Provider-free benchmarks exercise Workflow, Repository, Knowledge search,
planning, analysis, runtime, diagnostics, reporting, and health boundaries.
No local regression was identified in retained workflow or repository smoke
paths. Results are local smoke evidence, not a cross-machine SLO.

## Compatibility

v1.x and v2.0.x-v2.6.x public Python API, CLI, optional FastAPI DTO, MCP,
Workflow, Repository, Plugin, Extension SDK, Provider, Image Backend,
Automation, Notification, Health, Diagnostics, and Reporting contracts are
retained. Python, MCP, optional OpenAPI, and the SBOM use `2.7.0rc1`; the npm
frontend uses `2.7.0-rc.1`.

## Known issues

- Hosted CI, dependency/CVE audit, secret scan, and publication verification
  must run for the exact RC tag before publication.
- Non-mock adapters, autonomous AI, cloud monitoring, distributed execution,
  and marketplace work remain outside this RC scope.

## Before the stable release

1. Accept corrective RC feedback only; do not expand scope.
2. Confirm hosted backend, frontend, docs, package, security, release, nightly,
   benchmark, planning, knowledge, diagnostics, production, and enterprise jobs.
3. Promote reviewed metadata to `2.7.0`, regenerate release assets, and publish
   the approved tag and artifacts.

## GitHub Release body

Use this document as the GitHub prerelease body for tag `v2.7.0rc1` after
hosted checks and publication-time security scans succeed.
