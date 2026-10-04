# manga-director v2.6.0 RC1

## Overview

v2.6.0rc1 is the release candidate for the v2.6 stable line. It packages the
reviewed planning, analysis, governance, readiness, and diagnostic work without
altering the Core workflow, adding a provider or backend, or changing a
documented public contract.

## What's new

- Read-only Workflow Planning, execution previews, dependency graphs, and
  complexity estimates are available in the optional Application layer.
- Workflow Analysis adds critical-path, bottleneck, comparison, and trend DTOs
  without executing a workflow.
- Provider Orchestration and Governance provide metadata-only capability,
  cost/latency, lifecycle, policy, risk, and recommendation reports.
- Enterprise Readiness, workflow reliability, planning diagnostics, and
  executive dashboard DTOs provide local JSON and Markdown evidence.

## AI workflow and workflow analysis

The new v2.6 advisory services plan and analyze a single-page workflow; they
do not invoke Agents, select a live provider, schedule work, transition a
Page, approve work, or change persisted data. `WorkflowEngine` and the
StateMachine remain the sole workflow execution authorities.

## Provider governance and Enterprise operations

Provider and image-backend boundaries remain protocol and factory based.
Governance, capability, health, lifecycle, and Enterprise reports use local
metadata and mocks only. No cloud connection, fallback execution, marketplace,
or distributed runtime is introduced.

## Production, performance, and compatibility

Provider-free benchmark smoke covers workflow, repository, planning, analysis,
provider/backend runtime, automation, diagnostics, reporting, and health. The
v1.x and v2.0.x-v2.5.x Python API, CLI, FastAPI DTO, MCP, Workflow,
Repository, Plugin, Extension SDK, Provider, Image Backend, Automation,
Notification, Diagnostics, Reporting, and Health contracts are retained. See
the [compatibility audit](docs/COMPATIBILITY_V2_6_RC1.md).

Python, MCP, optional OpenAPI, and the SBOM use `2.6.0rc1`; the npm frontend
uses the equivalent `2.6.0-rc.1` prerelease form.

## Known issues

- Hosted CI, dependency/CVE audit, secret scan, and publication verification
  must run for the exact RC tag before publication.
- Non-mock adapters, autonomous AI, cloud monitoring, distributed execution,
  and marketplace work remain outside this RC scope.

## Before the stable release

1. Accept corrective RC feedback only; do not expand scope.
2. Confirm hosted backend, frontend, docs, package, security, release, nightly,
   benchmark, diagnostics, planning, production, and enterprise CI jobs.
3. Promote reviewed metadata to `2.6.0`, regenerate release assets, and publish
   the approved tag and artifacts.

## GitHub Release body

Use this document as the GitHub prerelease body for tag `v2.6.0rc1` after
hosted checks and publication-time security scans succeed.
